"""
Phonetic processors for English and Spanish text.

This module provides the main processing classes for converting text to IPA phonetic notation.
"""

import logging
from typing import Optional

from .converters import ArpabetToIpaConverter
from .exceptions import (
    PhoneticProcessingError, 
    SpanishProcessingError, 
    CMUDictError, 
    G2PError
)

logger = logging.getLogger(__name__)


class EnglishPhoneticProcessor:
    """
    Processes English text to generate IPA phonetic representations.
    
    Uses CMUdict as the primary source (gold standard for American English),
    with g2p-en as fallback for out-of-vocabulary words.
    """
    
    def __init__(self):
        self.cmudict = None
        self.g2p = None
        self.converter = ArpabetToIpaConverter()
        self._initialize_processors()
    
    def _initialize_processors(self):
        """Initialize CMUdict and g2p-en processors."""
        try:
            import cmudict
            self.cmudict = cmudict.dict()
            logger.info(f"CMUdict loaded with {len(self.cmudict)} entries")
        except ImportError as e:
            logger.error(f"Failed to import cmudict: {e}")
            raise CMUDictError("CMUdict not available")
        
        try:
            from g2p_en import G2p
            self.g2p = G2p()
            logger.info("G2P-EN processor initialized")
        except ImportError as e:
            logger.error(f"Failed to import g2p-en: {e}")
            raise G2PError("G2P-EN not available")
    
    def get_phonetic(self, word: str) -> str:
        """
        Get IPA phonetic representation for English word.
        
        Args:
            word: English word to process
            
        Returns:
            IPA phonetic string with stress markers, or empty string if processing fails
        """
        if not word or not word.strip():
            return ""
        
        try:
            # Clean and normalize input
            clean_word = self._clean_word(word)
            
            # Try CMUdict first (gold standard)
            arpabet = self._get_cmudict_pronunciation(clean_word)
            
            # Fall back to g2p-en if not in CMUdict
            if not arpabet:
                arpabet = self._get_g2p_pronunciation(clean_word)
            
            # Convert ARPABET to IPA
            if arpabet:
                return self.converter.convert(arpabet)
            
            logger.warning(f"No pronunciation found for '{word}'")
            return ""
            
        except Exception as e:
            logger.error(f"Failed to process English word '{word}': {str(e)}")
            return ""
    
    def _clean_word(self, word: str) -> str:
        """Clean and normalize word for processing."""
        # Convert to lowercase and strip whitespace
        clean = word.lower().strip()
        
        # Remove common punctuation that might interfere
        clean = clean.replace("'", "").replace("-", "").replace(".", "")
        
        return clean
    
    def _get_cmudict_pronunciation(self, word: str) -> str:
        """
        Get pronunciation from CMUdict.
        
        Args:
            word: Cleaned word to look up
            
        Returns:
            Space-separated ARPABET string or empty string
        """
        if not self.cmudict:
            return ""
        
        try:
            pronunciations = self.cmudict.get(word, [])
            if pronunciations:
                # Return first pronunciation (most common)
                return ' '.join(pronunciations[0])
        except Exception as e:
            logger.debug(f"CMUdict lookup failed for '{word}': {e}")
        
        return ""
    
    def _get_g2p_pronunciation(self, word: str) -> str:
        """
        Get pronunciation from g2p-en.
        
        Args:
            word: Word to process
            
        Returns:
            Space-separated ARPABET string or empty string
        """
        if not self.g2p:
            return ""
        
        try:
            phones = self.g2p(word)
            if phones:
                return ' '.join(phones)
        except Exception as e:
            logger.debug(f"G2P-EN processing failed for '{word}': {e}")
        
        return ""


class SpanishPhoneticProcessor:
    """
    Processes Spanish text to generate IPA phonetic representations.
    
    Uses epitran as the primary processor, with phonemizer as fallback.
    """
    
    def __init__(self):
        self.epitran = None
        self.phonemizer_available = False
        self.method = None
        self._initialize_processors()
    
    def _initialize_processors(self):
        """Initialize Spanish phonetic processors."""
        # Try epitran first (pure Python, no system dependencies)
        try:
            import epitran
            self.epitran = epitran.Epitran('spa-Latn')
            self.method = 'epitran'
            logger.info("Epitran Spanish processor initialized")
            return
        except ImportError as e:
            logger.warning(f"Epitran not available: {e}")
        
        # Try phonemizer as fallback
        try:
            from phonemizer import phonemize
            self.phonemize = phonemize
            self.phonemizer_available = True
            self.method = 'phonemizer'
            logger.info("Phonemizer Spanish processor initialized")
            return
        except ImportError as e:
            logger.warning(f"Phonemizer not available: {e}")
        
        # If neither is available, use basic fallback
        logger.warning("No Spanish phonetic processors available, using basic fallback")
        self.method = 'basic'
        self.epitran = None
        self.phonemizer_available = False
    
    def get_phonetic(self, word: str) -> str:
        """
        Get IPA phonetic representation for Spanish word.
        
        Args:
            word: Spanish word to process
            
        Returns:
            IPA phonetic string, or empty string if processing fails
        """
        if not word or not word.strip():
            return ""
        
        try:
            clean_word = self._clean_word(word)
            
            if self.method == 'epitran':
                return self._process_with_epitran(clean_word)
            elif self.method == 'phonemizer':
                return self._process_with_phonemizer(clean_word)
            elif self.method == 'basic':
                return self._process_with_basic_spanish(clean_word)
            
            logger.warning(f"No Spanish processor available for '{word}'")
            return ""
            
        except Exception as e:
            logger.error(f"Failed to process Spanish word '{word}': {str(e)}")
            return ""
    
    def _clean_word(self, word: str) -> str:
        """Clean and normalize Spanish word."""
        # Convert to lowercase and strip whitespace
        clean = word.lower().strip()
        
        # Remove common punctuation
        clean = clean.replace("'", "").replace("-", "").replace(".", "")
        
        return clean
    
    def _process_with_epitran(self, word: str) -> str:
        """
        Process using epitran.
        
        Args:
            word: Cleaned Spanish word
            
        Returns:
            IPA string
        """
        if not self.epitran:
            return ""
        
        try:
            result = self.epitran.transliterate(word)
            # Clean up the result (epitran sometimes adds extra characters)
            return result.strip()
        except Exception as e:
            logger.debug(f"Epitran processing failed for '{word}': {e}")
            return ""
    
    def _process_with_phonemizer(self, word: str) -> str:
        """
        Process using phonemizer.
        
        Args:
            word: Spanish word to process
            
        Returns:
            IPA string
        """
        if not self.phonemizer_available:
            return ""
        
        try:
            result = self.phonemize(
                word,
                language='es',
                backend='espeak',
                strip=True,
                preserve_punctuation=False,
                with_stress=True
            )
            return result.strip() if result else ""
        except Exception as e:
            logger.debug(f"Phonemizer processing failed for '{word}': {e}")
            return ""
    
    def _process_with_basic_spanish(self, word: str) -> str:
        """
        Basic Spanish phonetic approximation (fallback method).
        
        Args:
            word: Spanish word to process
            
        Returns:
            Basic IPA approximation
        """
        # This is a very basic approximation for Spanish phonetics
        # In production, you'd want to use epitran or phonemizer
        basic_mapping = {
            'ch': 'tʃ',
            'll': 'ʎ',
            'ñ': 'ɲ',
            'rr': 'r',
            'j': 'x',
            'g': 'ɡ',
            'c': 'k',  # simplified
            'qu': 'k',
            'z': 's',  # Latin American Spanish
            'v': 'b',  # Spanish b/v merger
        }
        
        result = word.lower()
        for spanish, ipa in basic_mapping.items():
            result = result.replace(spanish, ipa)
        
        return result


class PhoneticProcessorFactory:
    """Factory for creating phonetic processors."""
    
    _english_processor = None
    _spanish_processor = None
    
    @classmethod
    def get_english_processor(cls) -> EnglishPhoneticProcessor:
        """Get singleton English processor."""
        if cls._english_processor is None:
            cls._english_processor = EnglishPhoneticProcessor()
        return cls._english_processor
    
    @classmethod
    def get_spanish_processor(cls) -> SpanishPhoneticProcessor:
        """Get singleton Spanish processor."""
        if cls._spanish_processor is None:
            cls._spanish_processor = SpanishPhoneticProcessor()
        return cls._spanish_processor