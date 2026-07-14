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
