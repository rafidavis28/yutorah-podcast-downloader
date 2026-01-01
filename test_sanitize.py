#!/usr/bin/env python3
"""
Test the sanitize_filename function with problematic filenames
"""

import re

def sanitize_filename(filename):
    """
    Sanitize filename to remove invalid characters for Windows/Unix filesystems.
    Handles Hebrew characters, special punctuation, and ensures cross-platform compatibility.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for all filesystems
    """
    # First, replace all types of quotation marks with single quotes
    # This includes: ASCII quotes, smart quotes, Hebrew quotes, etc.
    quote_chars = [
        '"',   # ASCII double quote (U+0022)
        '"',   # Left double quotation mark (U+201C)
        '"',   # Right double quotation mark (U+201D)
        '״',   # Hebrew punctuation gershayim (U+05F4) - looks like quotes
        '‟',   # Double high-reversed-9 quotation mark (U+201F)
        '„',   # Double low-9 quotation mark (U+201E)
        '«',   # Left-pointing double angle quotation mark (U+00AB)
        '»',   # Right-pointing double angle quotation mark (U+00BB)
    ]
    for quote in quote_chars:
        filename = filename.replace(quote, "'")

    # Replace colons with dashes (including special Unicode colons)
    filename = filename.replace(':', '-')  # ASCII colon
    filename = filename.replace('׃', '-')  # Hebrew punctuation sof pasuq (looks like colon)

    # Remove Windows-invalid characters: < > / \ | ? *
    # Use a more comprehensive regex that catches all variations
    filename = re.sub(r'[<>/\\|?*]', '', filename)

    # Replace multiple spaces/dashes with single ones
    filename = re.sub(r'\s+', ' ', filename)
    filename = re.sub(r'-+', '-', filename)

    # Remove leading/trailing spaces, periods, and dashes (Windows doesn't allow these)
    filename = filename.strip('. -')

    # Trim to reasonable length (Windows has 260 char path limit)
    # Leave room for directory path
    if len(filename) > 180:
        # Keep extension if present
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            filename = name[:180-len(ext)-1] + '.' + ext
        else:
            filename = filename[:180]

    # Ensure we have a valid filename
    if not filename or filename == '.':
        filename = 'untitled'

    return filename


# Test cases from your errors
test_filenames = [
    'שיעור-יומי-מסכת-פסחים-פ"ב-2-בענין-מחלוקת-ב"ש-וב"ה-במכירת-חמץ-לנכרי.mp3',
    '10-minute-rashi-for-vayigash-speaking-hebrew-and-ahavat-yisrael-the-"blame-game"-jewish-success-in-egypt-and-in-the-usa-jewish-roles-in-local-economies-.mp3',
    'שיעור-יומי-מסכת-פסחים-פ"ב-1-בענין-חמץ-בשעה-חמישית-ושעה-שישית-לר\'-יהודה-ההיתר-להאכיל-לבהמה-וחיה-.mp3',
    'a-neziv-for-vayigash-preserving-cultural-insularity-while-fulfilling-jewish-mission--the-first-jewish-"enclave"--were-yosef\'s-brothers-popular-in-egypt-or-despised-.mp3',
    'שיעור-יומי-מסכת-פסחים-פ"א-40-חזרה-בענין-ביב"י--עברית-.mp3',
    'a-ramban-for-vayigash--was-ya\'akov-incredulous-or-did-he-faint-restoring-the-name-"ya\'akov"-how-old-was-yocheved-when-moshe-was-born-is-life-in-tanach-rational-or-supernatural.mp3',
]

print("Testing filename sanitization:")
print("=" * 80)

for original in test_filenames:
    sanitized = sanitize_filename(original)
    print(f"\nOriginal:  {original}")
    print(f"Sanitized: {sanitized}")

    # Try to check if it would work on Windows
    invalid_chars = set('<>:"/\\|?*')
    has_invalid = any(char in sanitized for char in invalid_chars)

    if has_invalid:
        print(f"❌ STILL HAS INVALID CHARACTERS!")
    else:
        print(f"✅ Safe for Windows")

print("\n" + "=" * 80)
