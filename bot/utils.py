import re


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
    
    # Prefixes to strip (longest first)
    prefixes = [
        r'индивидуальный\s+предприниматель\s+глава\s+крестьянского\s*\(?фермерского\)?\s*хозяйства',
        r'индивидуальный\s+предприниматель',
        r'глава\s+крестьянского\s*\(?фермерского\)?\s*хозяйства',
        r'общество\s+с\s+ограниченной\s+ответственностью',
        r'гкфх',
        r'ип',
        r'ооо',
        r'ао',
        r'пао',
        r'зао'
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


def compute_patent_expiry_date(issue_date_str: str) -> str:
    """
    Compute patent expiry date as exactly 1 year after the issue date.
    Input/output format: DD.MM.YYYY
    """
    if not issue_date_str:
        return ""
    try:
        parts = str(issue_date_str).strip().split('.')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{day:02d}.{month:02d}.{year + 1}"
    except Exception:
        pass
    return ""


def clean_passport_issued_by(issued_by: str) -> str:
    """
    Return the passport issued-by text, cleaned of extra whitespace.
    """
    if not issued_by:
        return ""
    # Just clean up extra spaces and return the full string
    return " ".join(str(issued_by).split())
