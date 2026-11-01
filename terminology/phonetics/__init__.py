"""
Phonetic processing module for InterpAscend terminology system.

This module provides IPA (International Phonetic Alphabet) phonetic spelling
generation for both English and Spanish terms across all glossary types.
"""

from .processors import EnglishPhoneticProcessor, SpanishPhoneticProcessor
from .converters import ArpabetToIpaConverter
from .exceptions import PhoneticProcessingError, ArpabetConversionError, SpanishProcessingError

__version__ = '1.0.0'
__all__ = [
    'EnglishPhoneticProcessor',
    'SpanishPhoneticProcessor', 
    'ArpabetToIpaConverter',
    'PhoneticProcessingError',
    'ArpabetConversionError',
    'SpanishProcessingError'
]