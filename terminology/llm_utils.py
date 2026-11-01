# terminology/llm_utils.py

import os
import openai
import json
import re
import hashlib
import time
from functools import lru_cache
from typing import Optional, Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read your OpenAI API key from the environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# In-memory cache for translations (alternative to lru_cache for more control)
_translation_cache: Dict[str, List[str]] = {}
_cache_timestamps: Dict[str, float] = {}

# Cache settings
CACHE_TTL = 3600  # 1 hour in seconds
MAX_CACHE_SIZE = 1000

# Specialty acronym corrections mapping
SPECIALTY_CORRECTIONS = {
    "ent": {
        "en": ["otolaryngologist", "otolaryngology", "ENT"],
        "es": ["otorrinolaringólogo", "otorrinolaringología", "otorrino"]
    },
    "gi": {
        "en": ["gastroenterologist", "gastroenterology", "GI"],
        "es": ["gastroenterólogo", "gastroenterología", "GI"]
    }
}


def _get_cache_key(phrase: str, src_lang: str, dest_lang: str, model: str) -> str:
    """Generate a cache key for the translation request."""
    key_data = f"{phrase}:{src_lang}:{dest_lang}:{model}"
    return hashlib.md5(key_data.encode('utf-8')).hexdigest()


def _clean_cache():
    """Remove expired cache entries and limit cache size."""
    current_time = time.time()
    
    # Remove expired entries
    expired_keys = [
        key for key, timestamp in _cache_timestamps.items()
        if current_time - timestamp > CACHE_TTL
    ]
    
    for key in expired_keys:
        _translation_cache.pop(key, None)
        _cache_timestamps.pop(key, None)
    
    # If cache is still too large, remove oldest entries
    if len(_translation_cache) > MAX_CACHE_SIZE:
        # Sort by timestamp and remove oldest entries
        sorted_keys = sorted(_cache_timestamps.items(), key=lambda x: x[1])
        keys_to_remove = [key for key, _ in sorted_keys[:-MAX_CACHE_SIZE]]
        
        for key in keys_to_remove:
            _translation_cache.pop(key, None)
            _cache_timestamps.pop(key, None)


def _get_from_cache(cache_key: str) -> Optional[List[str]]:
    """Get translation from cache if available and not expired."""
    if cache_key not in _translation_cache:
        return None
    
    # Check if cache entry is expired
    if time.time() - _cache_timestamps[cache_key] > CACHE_TTL:
        _translation_cache.pop(cache_key, None)
        _cache_timestamps.pop(cache_key, None)
        return None
    
    logger.info(f"Cache hit for key: {cache_key[:8]}...")
    return _translation_cache[cache_key]


def _store_in_cache(cache_key: str, result: List[str]):
    """Store translation result in cache."""
    _clean_cache()  # Clean before adding new entry
    _translation_cache[cache_key] = result
    _cache_timestamps[cache_key] = time.time()
    logger.info(f"Cached result for key: {cache_key[:8]}...")


def translate_with_llm(
    phrase: str,
    local_translations: Optional[Dict[str, str]] = None,
    src_lang: str = "en",
    dest_lang: str = "es",
    model: str = "gpt-3.5-turbo",
    timeout: int = 30,
    max_retries: int = 2
) -> List[str]:
    """
    Translate phrase from src_lang → dest_lang using a few-shot prompt.
    Returns up to 3 formal/legal/medical/financial/insurance translations.
    Always returns a list of strings (empty on error).
    
    Args:
        phrase: Text to translate
        local_translations: Unused legacy parameter (kept for backward compatibility)
        src_lang: Source language code
        dest_lang: Destination language code
        model: OpenAI model to use
        timeout: Timeout in seconds for the API call
        max_retries: Maximum number of retry attempts on failure
    
    Returns:
        List of translation strings (empty list on error)
    """
    
    # Input validation
    if not phrase or not phrase.strip():
        logger.warning("Empty phrase provided for translation")
        return []
    
    phrase = phrase.strip()
    
    # Check cache first
    cache_key = _get_cache_key(phrase, src_lang, dest_lang, model)
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result

    # Create full language names for clarity in the prompt
    lang_map = {"en": "English", "es": "Spanish"}
    src_lang_full = lang_map.get(src_lang, src_lang)
    dest_lang_full = lang_map.get(dest_lang, dest_lang)

    # Debug print to see what languages we're using
    logger.info(f"Translating '{phrase}' from {src_lang_full} to {dest_lang_full}")

    # --- Improved Prompt with More Explicit Instructions ---
    prompt = f'''You are a professional translator specializing in medical, legal, and insurance terminology. 

CRITICAL: You must translate FROM {src_lang_full} TO {dest_lang_full}. Do not translate to the same language as the input.

Your task: Translate the given phrase from {src_lang_full} into {dest_lang_full}. Provide up to 3 professional translations as a JSON array.

Examples:
- Input: "knee replacement" (English) → Output: ["reemplazo de rodilla", "artroplastia de rodilla"] (Spanish)
- Input: "presión arterial alta" (Spanish) → Output: ["high blood pressure", "hypertension"] (English)
- Input: "insurance broker" (English) → Output: ["corredor de seguros", "agente de seguros"] (Spanish)
- Input: "corredor de seguros" (Spanish) → Output: ["insurance broker", "insurance agent"] (English)
- Input: "subpoena" (English) → Output: ["citatorio", "citación judicial"] (Spanish)

Now translate this phrase:
Input: "{phrase}" ({src_lang_full})
Output (in {dest_lang_full}):'''

    # Retry loop with exponential backoff
    for attempt in range(max_retries + 1):
        try:
            # Configure timeout for the API call
            client = openai.OpenAI(
                api_key=openai.api_key,
                timeout=timeout
            )
            
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a professional translator. You ONLY respond with JSON arrays. You translate FROM {src_lang_full} TO {dest_lang_full}. Never translate to the same language as the input."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Slightly higher for variety, but still deterministic
                max_tokens=150,
            )

            raw = resp.choices[0].message.content.strip()
            logger.debug(f"Raw response: {repr(raw)}")

            # Clean up the response - remove any markdown formatting
            raw = raw.replace('```json', '').replace('```', '').strip()
            
            # Try to extract JSON array
            match = re.search(r'(\[.*?\])', raw, flags=re.DOTALL)
            if match:
                json_text = match.group(1)
            else:
                # If no brackets found, assume the whole response is the array
                json_text = raw

            logger.debug(f"Extracted JSON: {repr(json_text)}")
            
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON decode error: {json_err}. Raw text: {repr(json_text)}")
                raise ValueError(f"Invalid JSON response: {json_err}")
            
            # Validate that we got translations in the target language
            result = [t for t in data if isinstance(t, str) and t.strip()]
            
            if not result:
                logger.warning("No valid translations found in response")
                if attempt < max_retries:
                    continue
                else:
                    return []
            
            # Additional validation: check if results look like they're in the wrong language
            if dest_lang == "en" and result:
                # Quick check: if translating to English, result shouldn't contain Spanish characters
                for translation in result:
                    if any(char in translation.lower() for char in ['ñ', 'á', 'é', 'í', 'ó', 'ú']):
                        logger.warning(f"Translation '{translation}' appears to be in Spanish, not English")
            elif dest_lang == "es" and result:
                # Quick check: if translating to Spanish, should contain Spanish characteristics
                has_spanish_chars = any(
                    any(char in translation.lower() for char in ['ñ', 'á', 'é', 'í', 'ó', 'ú'])
                    for translation in result
                )
                if not has_spanish_chars:
                    logger.warning(f"Translations {result} may not be in Spanish")
            
            logger.info(f"Translation successful: {result}")
            
            # Apply specialty corrections before caching
            result = _apply_specialty_corrections(phrase, src_lang, dest_lang, result)
            
            # Store in cache before returning
            _store_in_cache(cache_key, result)
            
            return result

        except openai.APITimeoutError as timeout_err:
            logger.error(f"OpenAI API timeout (attempt {attempt + 1}/{max_retries + 1}): {timeout_err}")
            if attempt < max_retries:
                wait_time = (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s...
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
                
        except openai.APIError as api_err:
            logger.error(f"OpenAI API error (attempt {attempt + 1}/{max_retries + 1}): {api_err}")
            if attempt < max_retries:
                wait_time = (2 ** attempt)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
                
        except openai.RateLimitError as rate_err:
            logger.error(f"OpenAI rate limit error (attempt {attempt + 1}/{max_retries + 1}): {rate_err}")
            if attempt < max_retries:
                # Longer wait for rate limit errors
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s...
                logger.info(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
                
        except Exception as e:
            logger.error(f"Unexpected error (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if 'raw' in locals():
                logger.debug(f"Raw response was: {repr(raw)}")
            if attempt < max_retries:
                wait_time = (2 ** attempt)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
    
    # All retries exhausted
    logger.error("All retry attempts failed for translation")
    return []


def clear_translation_cache():
    """Clear the translation cache (useful for testing or memory management)."""
    global _translation_cache, _cache_timestamps
    _translation_cache.clear()
    _cache_timestamps.clear()
    logger.info("Translation cache cleared")


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    return {
        "cache_size": len(_translation_cache),
        "max_cache_size": MAX_CACHE_SIZE,
        "cache_ttl": CACHE_TTL
    }


def _apply_specialty_corrections(user_text: str,
                                src_lang: str,
                                dest_lang: str,
                                suggestions: List[str]) -> List[str]:
    """
    If user_text contains known specialty acronyms as whole words (case-insensitive),
    prepend the canonical target-language terms, then append original suggestions.
    De-duplicate (case-insensitive) while preserving order. Log once when applied.
    Never allow the string 'odontologist' in ENT cases.
    Use word-boundary regex (e.g., r'\bENT\b', r'\bGI\b') so Spanish words like
    'entonces' do NOT trigger. Return suggestions unchanged when no correction applies.
    """
    if not user_text or not suggestions:
        return suggestions
    
    corrected_terms = []
    correction_applied = False
    
    # Check each specialty acronym in our corrections mapping
    for acronym_key, lang_mappings in SPECIALTY_CORRECTIONS.items():
        # Create word-boundary regex pattern for the acronym (case-insensitive)
        pattern = rf'\b{re.escape(acronym_key)}\b'
        
        # Check if the acronym appears in user_text (case-insensitive)
        if re.search(pattern, user_text, re.IGNORECASE):
            # Get the correction terms for the destination language
            if dest_lang in lang_mappings:
                correction_terms = lang_mappings[dest_lang]
                corrected_terms.extend(correction_terms)
                correction_applied = True
                logger.info("Specialty correction applied for token '%s' → %s", acronym_key.upper(), correction_terms)
    
    if not correction_applied:
        return suggestions
    
    # Merge corrected terms with original suggestions, removing duplicates
    final_result = []
    seen_lower = set()
    
    # Add corrected terms first (in mapping order)
    for term in corrected_terms:
        term_lower = term.lower()
        if term_lower not in seen_lower:
            final_result.append(term)
            seen_lower.add(term_lower)
    
    # Add original suggestions, excluding duplicates
    for suggestion in suggestions:
        suggestion_lower = suggestion.lower()
        if suggestion_lower not in seen_lower:
            final_result.append(suggestion)
            seen_lower.add(suggestion_lower)
    
    # Special handling for ENT: remove 'odontologist' if present
    if any(re.search(r'\bent\b', user_text, re.IGNORECASE) for _ in [None]):
        final_result = [term for term in final_result if term.lower() != 'odontologist']
    
    return final_result