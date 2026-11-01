"""
ARPABET to IPA conversion utilities.

This module handles the conversion from ARPABET phonetic notation (used by CMUdict and g2p-en)
to International Phonetic Alphabet (IPA) notation with proper stress handling.
"""

from .data.arpabet_ipa_map import (
    ARPABET_IPA_MAP, 
    VOWEL_PHONES, 
    STRESS_MARKERS, 
    SCHWA_VARIANTS
)
from .exceptions import ArpabetConversionError


class ArpabetToIpaConverter:
    """
    Converts ARPABET phonetic notation to IPA with stress markers.
    
    Handles:
    - Basic ARPABET to IPA symbol conversion
    - Primary stress (ˈ) and secondary stress (ˌ) markers
    - Special schwa handling (/ɚ vs ɝ/) based on stress
    - Proper stress marker placement before syllables
    """
    
    def __init__(self):
        self.mapping = ARPABET_IPA_MAP
        self.vowel_phones = VOWEL_PHONES
        self.stress_markers = STRESS_MARKERS
        self.schwa_variants = SCHWA_VARIANTS
    
    def convert(self, arpabet_string: str) -> str:
        """
        Convert ARPABET string to IPA with stress markers.
        
        Args:
            arpabet_string: Space-separated ARPABET phones with stress numbers
                          Example: "HH AH1 L OW0" -> "hʌˈloʊ"
        
        Returns:
            IPA string with stress markers
            
        Raises:
            ArpabetConversionError: If conversion fails
        """
        try:
            if not arpabet_string or not arpabet_string.strip():
                return ""
            
            phones = arpabet_string.strip().split()
            ipa_result = []
            
            for i, phone in enumerate(phones):
                # Extract stress information
                stress_level = self._extract_stress(phone)
                base_phone = self._remove_stress(phone)
                
                # Skip empty phones
                if not base_phone:
                    continue
                
                # Convert to IPA
                ipa_phone = self._convert_phone(base_phone, stress_level)
                
                # Add stress marker for vowels
                if stress_level and base_phone in self.vowel_phones:
                    stress_marker = self.stress_markers.get(stress_level, '')
                    if stress_marker:
                        ipa_result.append(stress_marker + ipa_phone)
                    else:
                        ipa_result.append(ipa_phone)
                else:
                    ipa_result.append(ipa_phone)
            
            return ''.join(ipa_result)
            
        except Exception as e:
            raise ArpabetConversionError(f"Failed to convert '{arpabet_string}': {str(e)}")
    
    def _extract_stress(self, phone: str) -> str:
        """
        Extract stress level from phone.
        
        Args:
            phone: ARPABET phone possibly with stress marker (e.g., "AH1")
            
        Returns:
            Stress level ('0', '1', '2') or empty string
        """
        if phone and phone[-1] in ('0', '1', '2'):
            return phone[-1]
        return ''
    
    def _remove_stress(self, phone: str) -> str:
        """
        Remove stress marker from phone.
        
        Args:
            phone: ARPABET phone possibly with stress marker
            
        Returns:
            Base phone without stress marker
        """
        if phone and phone[-1] in ('0', '1', '2'):
            return phone[:-1]
        return phone
    
    def _convert_phone(self, base_phone: str, stress_level: str) -> str:
        """
        Convert a single ARPABET phone to IPA.
        
        Args:
            base_phone: ARPABET phone without stress marker
            stress_level: Stress level ('0', '1', '2')
            
        Returns:
            IPA representation of the phone
        """
        # Handle special case of schwa (ER)
        if base_phone == 'ER':
            return self._handle_schwa(stress_level)
        
        # Regular conversion
        return self.mapping.get(base_phone, base_phone)
    
    def _handle_schwa(self, stress_level: str) -> str:
        """
        Handle schwa variants /ɚ vs ɝ/ based on stress.
        
        Args:
            stress_level: Stress level ('0', '1', '2')
            
        Returns:
            Appropriate schwa variant
        """
        if stress_level == '1':
            return self.schwa_variants['stressed']  # ɝ
        else:
            return self.schwa_variants['unstressed']  # ɚ
    
    def is_vowel(self, phone: str) -> bool:
        """
        Check if a phone (without stress) is a vowel.
        
        Args:
            phone: ARPABET phone without stress marker
            
        Returns:
            True if phone is a vowel
        """
        return phone in self.vowel_phones