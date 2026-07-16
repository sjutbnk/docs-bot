import re
import datetime


def get_short_name(full_name: str) -> str:
    """Return surname + initials, e.g. 'Жобборов Х.И.'"""
    if not full_name or not full_name.strip():
        return ""
    parts = [p.capitalize() for p in full_name.split()]
    if not parts:
        return ""
    result = parts[0]
    if len(parts) > 1:
        result += f" {parts[1][0]}."
    if len(parts) > 2:
        result += f"{parts[2][0]}."
    return result


def extract_employer_fio(employer_name: str) -> str:
    """
    Extract the pure name/FIO by stripping legal prefixes (ИП, ГКФХ, ООО, etc.).
    This is used before passing the name to get_short_name() for signatures.
    """
    if not employer_name:
        return ""
    text = str(employer_name).strip()
    
    # Prefixes to strip (longest first to avoid partial matches)
    prefixes = [
        r'индивидуальный\s+предприниматель\s+глава\s+крестьянского\s*\(?фермерского\)?\s*хозяйства',
        r'индивидуальный\s+предприниматель',
        r'глава\s+крестьянского\s*\(?фермерского\)?\s*хозяйства',
        r'общество\s+с\s+ограниченной\s+ответственностью',
        r'\bгкфх\b',
        r'\bип\b',   # word boundary: don't strip 'ип' inside names like 'Ипатьев'
        r'\bооо\b',
        r'\bао\b',
        r'\bпао\b',
        r'\bзао\b',
    ]
    for p in prefixes:
        text = re.sub(p, '', text, flags=re.IGNORECASE).strip()
    
    # Strip any leading/trailing quotes or punctuation
    text = re.sub(r'^[\"\'«»\-\.,]+', '', text)
    text = re.sub(r'[\"\'«»\-\.,]+$', '', text)
    return text.strip()


def clean_employer_name(name: str) -> str:
    """
    Remove duplicated or mangled legal entity prefixes from employer_name by 
    extracting the pure FIO and rebuilding the legal prefix perfectly.
    """
    if not name:
        return ""
    
    pure_fio = extract_employer_fio(name)
    name_lower = name.lower()
    
    if "ооо" in name_lower or "общество" in name_lower:
        return f'ООО "{pure_fio}"'
    elif "гкфх" in name_lower or "крестьянск" in name_lower or "фермерск" in name_lower:
        return f"Индивидуальный предприниматель Глава крестьянского (фермерского) хозяйства {pure_fio}"
    elif "ип " in name_lower or "индивидуальный предп" in name_lower or name_lower.startswith("ип"):
        return f"Индивидуальный предприниматель {pure_fio}"
    else:
        return pure_fio


def normalize_date(date_str: str) -> str:
    """
    Normalize a date string to DD.MM.YYYY format.
    Handles missing leading zeros (3.5.2025 -> 03.05.2025),
    slash/dash separators (13/05/2025 -> 13.05.2025), and
    returns the original string unchanged if format is unrecognised.
    """
    if not date_str:
        return ""
    s = str(date_str).strip()
    # Already correct
    if re.fullmatch(r'\d{2}\.\d{2}\.\d{4}', s):
        return s
    # D.M.YYYY, DD.M.YYYY, D.MM.YYYY (dot separator, possibly missing leading zeros)
    m = re.fullmatch(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', s)
    if m:
        return f'{int(m.group(1)):02d}.{int(m.group(2)):02d}.{m.group(3)}'
    # DD/MM/YYYY, D/M/YYYY, DD-MM-YYYY, etc.
    m = re.fullmatch(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', s)
    if m:
        return f'{int(m.group(1)):02d}.{int(m.group(2)):02d}.{m.group(3)}'
    return s  # unrecognised — return as-is


def compute_patent_expiry_date(issue_date_str: str) -> str:
    """
    Compute patent expiry date as exactly 1 year after the issue date.
    Input/output format: DD.MM.YYYY
    """
    if not issue_date_str:
        return ""
    try:
        normalized = normalize_date(str(issue_date_str).strip())
        parts = normalized.split('.')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            try:
                # Validate date
                d = datetime.date(year, month, day)
                # Compute expiry safely
                exp_year = year + 1
                if month == 2 and day == 29:
                    # check if exp_year is leap
                    is_leap = (exp_year % 4 == 0 and (exp_year % 100 != 0 or exp_year % 400 == 0))
                    d_day = 29 if is_leap else 28
                else:
                    d_day = day
                return f"{d_day:02d}.{month:02d}.{exp_year}"
            except ValueError:
                pass
    except Exception:
        pass
    return ""


def compute_patent_issue_date(expiry_date_str: str) -> str:
    """
    Compute patent issue date as exactly 1 year before the expiry date.
    Input/output format: DD.MM.YYYY
    """
    if not expiry_date_str:
        return ""
    try:
        normalized = normalize_date(str(expiry_date_str).strip())
        parts = normalized.split('.')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            try:
                # Validate date
                d = datetime.date(year, month, day)
                # Compute issue safely
                iss_year = year - 1
                if month == 2 and day == 29:
                    # check if iss_year is leap
                    is_leap = (iss_year % 4 == 0 and (iss_year % 100 != 0 or iss_year % 400 == 0))
                    d_day = 29 if is_leap else 28
                else:
                    d_day = day
                return f"{d_day:02d}.{month:02d}.{iss_year}"
            except ValueError:
                pass
    except Exception:
        pass
    return ""


def split_dms_number(dms_str: str) -> tuple:
    """
    Split a DMS string into a tuple of (series, number).
    If it starts with alphabetical characters, splits them.
    If it is '-' or empty, returns ('', '').
    Otherwise defaults to ('MRF', digits).
    """
    s = str(dms_str).strip()
    if not s or s in ("-", "—"):
        return "", ""
    # Search for series (letters) and number (digits)
    match = re.search(r'([A-Za-zА-Яа-яЁё]+)\s*(\d+)', s)
    if match:
        return match.group(1).upper(), match.group(2)
    # If only digits are found
    digits = "".join(c for c in s if c.isdigit())
    if digits:
        return "MRF", digits
    return "", ""


def clean_passport_issued_by(issued_by: str) -> str:
    """
    Return the passport issued-by text, cleaned of extra whitespace.
    """
    if not issued_by:
        return ""
    # Just clean up extra spaces and return the full string
    return " ".join(str(issued_by).split())
