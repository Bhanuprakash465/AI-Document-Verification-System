"""
Context-aware OCR error correction utilities.

Provides functions to correct common OCR mistakes based on
the expected data type and document context.
"""

import re
from typing import Optional


# =========================================================
# CHARACTER MAPPING
# =========================================================

# Common OCR confusions
OCR_CHAR_MAP = {
    'O': '0',  # Letter O to digit 0
    'o': '0',
    'I': '1',  # Letter I to digit 1
    'l': '1',  # Lowercase L to digit 1
    'L': '1',
    'S': '5',  # Letter S to digit 5
    's': '5',
    'B': '8',  # Letter B to digit 8
    'Z': '2',  # Letter Z to digit 2
    'z': '2',
    'G': '6',  # Letter G to digit 6
    'g': '9',
}

# Reverse mapping for letters
DIGIT_TO_LETTER_MAP = {
    '0': 'O',
    '1': 'I',
    '5': 'S',
    '8': 'B',
    '2': 'Z',
}


# =========================================================
# AADHAAR NUMBER CORRECTION
# =========================================================

def correct_aadhaar_number(text: str) -> Optional[str]:
    """
    Correct OCR errors in Aadhaar number.
    
    Aadhaar format: 12 digits, often shown as XXXX XXXX XXXX
    """
    
    if not text:
        return None
    
    # Remove all non-alphanumeric characters
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
    
    # Convert common OCR errors to digits
    corrected = []
    for char in cleaned:
        if char in OCR_CHAR_MAP:
            corrected.append(OCR_CHAR_MAP[char])
        elif char.isdigit():
            corrected.append(char)
        # Skip letters that don't map to digits
    
    result = ''.join(corrected)
    
    # Must be exactly 12 digits
    if len(result) != 12:
        return None
    
    if not result.isdigit():
        return None
    
    # Format as XXXX XXXX XXXX
    return f"{result[:4]} {result[4:8]} {result[8:]}"


# =========================================================
# PAN NUMBER CORRECTION
# =========================================================

def correct_pan_number(text: str) -> Optional[str]:
    """
    Correct OCR errors in PAN number.
    
    PAN format: AAAAA9999A
    - First 5 characters: Letters
    - Next 4 characters: Digits
    - Last character: Letter
    """
    
    if not text:
        return None
    
    # Remove spaces and special characters
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text).upper()
    
    if len(cleaned) != 10:
        return None
    
    # Correct first 5 positions (should be letters)
    corrected = []
    
    for i in range(5):
        if i >= len(cleaned):
            return None
        
        char = cleaned[i]
        
        if char.isalpha():
            corrected.append(char)
        elif char.isdigit() and char in DIGIT_TO_LETTER_MAP:
            # Convert digit to likely letter
            corrected.append(DIGIT_TO_LETTER_MAP[char])
        else:
            corrected.append(char)
    
    # Correct positions 6-9 (should be digits)
    for i in range(5, 9):
        if i >= len(cleaned):
            return None
        
        char = cleaned[i]
        
        if char.isdigit():
            corrected.append(char)
        elif char.upper() in OCR_CHAR_MAP:
            # Convert letter to digit
            corrected.append(OCR_CHAR_MAP[char.upper()])
        else:
            corrected.append(char)
    
    # Last position (should be letter)
    if len(cleaned) >= 10:
        char = cleaned[9]
        
        if char.isalpha():
            corrected.append(char)
        elif char.isdigit() and char in DIGIT_TO_LETTER_MAP:
            corrected.append(DIGIT_TO_LETTER_MAP[char])
        else:
            corrected.append(char)
    
    result = ''.join(corrected)
    
    # Validate final format
    if not re.match(r'^[A-Z]{5}\d{4}[A-Z]$', result):
        return None
    
    return result


# =========================================================
# PASSPORT NUMBER CORRECTION
# =========================================================

def correct_passport_number(text: str) -> Optional[str]:
    """
    Correct OCR errors in Indian passport number.
    
    Format: A1234567
    - First character: Letter
    - Next 7 characters: Digits
    """
    
    if not text:
        return None
    
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text).upper()
    
    if len(cleaned) != 8:
        return None
    
    # First character should be letter
    first_char = cleaned[0]
    if first_char.isdigit() and first_char in DIGIT_TO_LETTER_MAP:
        first_char = DIGIT_TO_LETTER_MAP[first_char]
    elif not first_char.isalpha():
        return None
    
    # Next 7 should be digits
    remaining = []
    for char in cleaned[1:]:
        if char.isdigit():
            remaining.append(char)
        elif char.upper() in OCR_CHAR_MAP:
            remaining.append(OCR_CHAR_MAP[char.upper()])
        else:
            remaining.append(char)
    
    result = first_char + ''.join(remaining)
    
    # Validate format
    if not re.match(r'^[A-Z]\d{7}$', result):
        return None
    
    return result


# =========================================================
# EPIC/VOTER ID NUMBER CORRECTION
# =========================================================

def correct_epic_number(text: str) -> Optional[str]:
    """
    Correct OCR errors in EPIC/Voter ID number.
    
    Format: AAA1234567
    - First 3 characters: Letters
    - Next 7 characters: Digits
    """
    
    if not text:
        return None
    
    # Remove spaces and hyphens
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text).upper()
    
    if len(cleaned) != 10:
        return None
    
    # First 3 should be letters
    prefix = []
    for i in range(3):
        char = cleaned[i]
        
        if char.isalpha():
            prefix.append(char)
        elif char.isdigit() and char in DIGIT_TO_LETTER_MAP:
            prefix.append(DIGIT_TO_LETTER_MAP[char])
        else:
            prefix.append(char)
    
    # Next 7 should be digits
    suffix = []
    for i in range(3, 10):
        char = cleaned[i]
        
        if char.isdigit():
            suffix.append(char)
        elif char.upper() in OCR_CHAR_MAP:
            suffix.append(OCR_CHAR_MAP[char.upper()])
        else:
            suffix.append(char)
    
    result = ''.join(prefix) + ''.join(suffix)
    
    # Validate format
    if not re.match(r'^[A-Z]{3}\d{7}$', result):
        return None
    
    return result


# =========================================================
# PIN CODE CORRECTION
# =========================================================

def correct_pin_code(text: str) -> Optional[str]:
    """
    Correct OCR errors in PIN code.
    
    Format: 6 digits, first digit cannot be 0
    """
    
    if not text:
        return None
    
    # Extract only alphanumeric
    cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
    
    # Convert letters that look like digits
    corrected = []
    for char in cleaned:
        if char.isdigit():
            corrected.append(char)
        elif char.upper() in OCR_CHAR_MAP:
            corrected.append(OCR_CHAR_MAP[char.upper()])
    
    result = ''.join(corrected)
    
    # Must be exactly 6 digits
    if len(result) != 6:
        return None
    
    if not result.isdigit():
        return None
    
    # First digit cannot be 0
    if result[0] == '0':
        return None
    
    return result


# =========================================================
# DATE CORRECTION
# =========================================================

def correct_date(text: str) -> Optional[str]:
    """
    Correct OCR errors in date.
    
    Expected formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    """
    
    if not text:
        return None
    
    # Normalize separators
    normalized = text.replace('.', '/').replace('-', '/')
    
    # Extract parts
    parts = normalized.split('/')
    
    if len(parts) != 3:
        return None
    
    # Correct each part
    corrected_parts = []
    
    for part in parts:
        # Remove non-alphanumeric
        cleaned = re.sub(r'[^A-Za-z0-9]', '', part)
        
        # Convert letters to digits
        digits = []
        for char in cleaned:
            if char.isdigit():
                digits.append(char)
            elif char.upper() in OCR_CHAR_MAP:
                digits.append(OCR_CHAR_MAP[char.upper()])
        
        corrected_parts.append(''.join(digits))
    
    # Validate lengths
    day, month, year = corrected_parts
    
    if len(day) != 2 or len(month) != 2:
        return None
    
    if len(year) != 4 and len(year) != 2:
        return None
    
    # Basic validation
    try:
        day_val = int(day)
        month_val = int(month)
        year_val = int(year)
        
        if not (1 <= day_val <= 31):
            return None
        
        if not (1 <= month_val <= 12):
            return None
        
        if len(year) == 2:
            # Assume 20xx for years 00-30, 19xx for 31-99
            if year_val <= 30:
                year = f"20{year}"
            else:
                year = f"19{year}"
        
    except ValueError:
        return None
    
    return f"{day}/{month}/{year}"


# =========================================================
# NAME CORRECTION
# =========================================================

def correct_name(text: str) -> Optional[str]:
    """
    Clean and correct OCR errors in names.
    
    Removes digits and special characters,
    fixes common OCR mistakes in names.
    """
    
    if not text:
        return None
    
    # Remove digits
    text = re.sub(r'\d+', ' ', text)
    
    # Common OCR corrections for names
    text = text.replace('|', 'I')
    text = text.replace('¦', 'I')
    text = text.replace('1', 'I')
    text = text.replace('0', 'O')
    
    # Keep only letters, spaces, apostrophes, dots, hyphens
    text = re.sub(r"[^A-Za-z.\s'\-]", ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text:
        return None
    
    # Must have at least 2 words for a full name
    words = text.split()
    
    if len(words) < 2:
        return None
    
    # Reject if too many single-character words
    single_char_words = sum(1 for word in words if len(word) == 1)
    if single_char_words > 1:
        return None
    
    # Filter out words that are too short
    valid_words = [word for word in words if len(word) >= 2 or word.upper() in ['A', 'S', 'D', 'W', 'C', 'O']]
    
    if len(valid_words) < 2:
        return None
    
    return ' '.join(valid_words).upper()


# =========================================================
# GENERAL TEXT CLEANING
# =========================================================

def clean_ocr_text(text: str) -> str:
    """
    General OCR text cleaning.
    
    Removes control characters, normalizes whitespace.
    """
    
    if not text:
        return ""
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    
    # Normalize common separators
    text = text.replace('|', ' ')
    text = text.replace('_', ' ')
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


# =========================================================
# CONTEXT-AWARE CORRECTION
# =========================================================

def correct_by_context(text: str, field_type: str) -> Optional[str]:
    """
    Apply context-aware OCR correction based on field type.
    
    Args:
        text: Raw OCR text
        field_type: Type of field (aadhaar, pan, passport, etc.)
    
    Returns:
        Corrected text or None if correction fails
    """
    
    if not text:
        return None
    
    field_type = field_type.lower()
    
    if field_type in ['aadhaar', 'aadhaar_number']:
        return correct_aadhaar_number(text)
    
    elif field_type in ['pan', 'pan_number']:
        return correct_pan_number(text)
    
    elif field_type in ['passport', 'passport_number']:
        return correct_passport_number(text)
    
    elif field_type in ['epic', 'voter_id', 'epic_number']:
        return correct_epic_number(text)
    
    elif field_type in ['pin', 'pin_code', 'pincode']:
        return correct_pin_code(text)
    
    elif field_type in ['date', 'dob', 'date_of_birth']:
        return correct_date(text)
    
    elif field_type in ['name']:
        return correct_name(text)
    
    else:
        # No specific correction, just clean
        return clean_ocr_text(text)
