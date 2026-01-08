"""
This codes used to parse correspondence files uploaded by users. 
They are served to read the correspondence data and validate its format:
- Each line should have 2 or 3 columns separated by tabs, commas, semicolons, or multiple spaces.
- The first column is the identifier, the second is the display name, and the optional third
"""

import re


def parse_correspondence_text(raw_text: str):
    """    
    :param raw_text: Description
    :type raw_text: str
    """
    rows = []
    erroes = []
    seen = set()

    for lineno, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = re.split(r"[,\t;]+|\s{2,}", line)
        parts = [p.strip() for p in parts if p.strip()] 

        if len(parts) not in (2, 3):
            erroes.append(f"Line {lineno}: expected 2 or 3 columns, got {len(parts)} -> {line}")
            continue

        identifier, display_name = parts[0], parts[1]
        entry_type = parts[2] if len(parts) == 3 else ""

        if identifier in seen:
            erroes.append(f"Line {lineno}: duplicate identifier '{identifier}' in file.")
            continue
        seen.add(identifier)

        rows.append((identifier, display_name, entry_type))
    
    return rows, erroes