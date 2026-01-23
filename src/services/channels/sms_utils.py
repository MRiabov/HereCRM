
"""
Utilities for GSM-7 character set normalization.
Standard SMS uses GSM-7 encoding. Non-GSM-7 characters force the message to UCS-2,
significantly increasing costs (160 chars vs 70 chars per segment).
"""
import unicodedata

# GSM 03.38 Basic Character Set (plus LF/CR)
# Note: ASCII 0x00-0x7F is NOT fully GSM-7 compliant.
# Specifically:
# @ is 0x00 in GSM
# $ is 0x02 in GSM
# etc.
# But for python string check, we just need to know which python characters map to GSM-7.

GSM7_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./"
    "0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)

# GSM 03.38 Extension Table characters (escape + char)
# These are valid in GSM-7 but take 2 characters/septets.
GSM7_EXTENDED = set(
    "^{}\\[~]|€"
)

GSM7_ALL = GSM7_BASIC.union(GSM7_EXTENDED)

# Common replacements for non-GSM-7 characters
REPLACEMENTS = {
    # Smart quotes and apostrophes
    '\u2018': "'",  # Left single quote
    '\u2019': "'",  # Right single quote
    '\u201c': '"',  # Left double quote
    '\u201d': '"',  # Right double quote
    '\u201a': "'",  # Single low-9 quotation mark
    '\u201e': '"',  # Double low-9 quotation mark
    '`': "'",       # Backtick often causes issues or is just mapped to '
    
    # Dashes
    '\u2013': '-',  # En dash
    '\u2014': '-',  # Em dash
    '\u2015': '-',  # Horizontal bar
    
    # Spaces
    '\u00a0': ' ',  # Non-breaking space
    '\u2009': ' ',  # Thin space
    '\u202f': ' ',  # Narrow no-break space
    
    # Ellipsis
    '\u2026': '...', 
    
    # Bullets
    '\u2022': '*',
    
    # Others
    '\u00a9': '(c)', # Copyright
    '\u00ae': '(r)', # Registered
    '\u2122': 'TM',  # Trademark
}

def is_gsm7(text: str) -> bool:
    """Check if the text contains only GSM-7 compliant characters."""
    return all(char in GSM7_ALL for char in text)

def normalize_to_gsm7(text: str) -> str:
    """
    Normalize text to GSM-7 compatible characters.
    
    - Replaces common fancy characters with ASCII/GSM equivalents.
    - Strips accents if not in GSM set.
    - Replaces unknown characters with '?'.
    """
    if not text:
        return ""

    result = []
    
    # 1. Normalize unicode (NFKD) to decompose accented characters where possible
    # This helps turning "á" into "a" + "´". But we might want to keep "á" if it is in GSM7.
    # However, standard GSM7 DOES imply some accented chars exist (à, é, etc.)
    # So blindly decomposing might lose them if we strip the combining mark.
    
    # Strategy: 
    # Iterate through characters.
    # If in GSM7, keep.
    # If in REPLACEMENTS, replace.
    # If decomposable (e.g. á -> a + ´), check if base is GSM7.
    # Else replace with ?
    
    for char in text:
        if char in GSM7_ALL:
            result.append(char)
            continue
            
        # Check explicit replacements
        if char in REPLACEMENTS:
            normalized = REPLACEMENTS[char]
            # Verify the replacement logic produces GSM7 chars (it should)
            for n_char in normalized:
                if n_char in GSM7_ALL:
                    result.append(n_char)
                else:
                    result.append('?') # Should not happen with our hardcoded list
            continue
            
        # Try normalizing unicode (NFKD) to strip accents UNLESS the char itself was in GSM7 (checked above)
        normalized_form = unicodedata.normalize('NFKD', char)
        # Filter for non-spacing mark (accents)
        stripped = "".join([c for c in normalized_form if not unicodedata.combining(c)])
        
        # If stripped is different from original, it means we removed an accent.
        # Check if the stripped version is in GSM7
        if stripped and all(c in GSM7_ALL for c in stripped):
            result.append(stripped)
            continue
            
        # Fallback
        result.append('?')
        
    return "".join(result)
