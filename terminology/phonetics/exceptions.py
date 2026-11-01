"""
Custom exceptions for phonetic processing.
"""


class PhoneticProcessingError(Exception):
    """Base exception for phonetic processing errors."""
    pass


class ArpabetConversionError(PhoneticProcessingError):
    """Raised when ARPABET to IPA conversion fails."""
    pass


class SpanishProcessingError(PhoneticProcessingError):
    """Raised when Spanish phonetic processing fails."""
    pass


class CMUDictError(PhoneticProcessingError):
    """Raised when CMUDict lookup fails."""
    pass


class G2PError(PhoneticProcessingError):
    """Raised when G2P-EN processing fails."""
    pass