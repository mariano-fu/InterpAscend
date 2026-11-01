"""
ARPABET to IPA conversion mapping for American English.

This module contains the mapping from ARPABET phonetic symbols (used by CMUdict and g2p-en)
to International Phonetic Alphabet (IPA) symbols with proper stress handling.
"""

# Main ARPABET to IPA conversion mapping
ARPABET_IPA_MAP = {
    # Vowels
    'AA': 'ɑ',    # father, hot
    'AE': 'æ',    # cat, bat
    'AH': 'ʌ',    # cut, but
    'AO': 'ɔ',    # caught, saw
    'AW': 'aʊ',   # how, now
    'AY': 'aɪ',   # my, eye
    'EH': 'ɛ',    # red, bed
    'ER': 'ɝ',    # bird, hurt (will be handled specially for stress)
    'EY': 'eɪ',   # say, day
    'IH': 'ɪ',    # bit, sit
    'IY': 'i',    # beat, seat
    'OW': 'oʊ',   # go, show
    'OY': 'ɔɪ',   # boy, toy
    'UH': 'ʊ',    # book, good
    'UW': 'u',    # boot, food
    
    # Consonants
    'B': 'b',     # bat
    'CH': 'tʃ',   # church
    'D': 'd',     # dog
    'DH': 'ð',    # this, that
    'F': 'f',     # fish
    'G': 'ɡ',     # go
    'HH': 'h',    # house
    'JH': 'dʒ',   # judge
    'K': 'k',     # cat
    'L': 'l',     # love
    'M': 'm',     # man
    'N': 'n',     # no
    'NG': 'ŋ',    # sing
    'P': 'p',     # pen
    'R': 'ɹ',     # red
    'S': 's',     # sun
    'SH': 'ʃ',    # ship
    'T': 't',     # top
    'TH': 'θ',    # think
    'V': 'v',     # very
    'W': 'w',     # water
    'Y': 'j',     # yes
    'Z': 'z',     # zoo
    'ZH': 'ʒ',    # measure
}

# Set of vowel phones for stress handling
VOWEL_PHONES = {
    'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 
    'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 
    'OY', 'UH', 'UW'
}

# Stress markers
STRESS_MARKERS = {
    '0': '',      # No stress
    '1': 'ˈ',     # Primary stress
    '2': 'ˌ',     # Secondary stress
}

# Special handling for schwa variants
SCHWA_VARIANTS = {
    'stressed': 'ɝ',      # Stressed schwa (bird, hurt)
    'unstressed': 'ɚ',    # Unstressed schwa (butter, water)
}