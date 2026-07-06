def get_short_name(full_name):
    if not full_name:
        return ""
    # Capitalize parts just in case
    parts = [p.capitalize() for p in full_name.split()]
    if len(parts) == 0:
        return ""
    surname = parts[0]
    initials = ""
    if len(parts) > 1:
        initials += f" {parts[1][0]}."
    if len(parts) > 2:
        initials += f"{parts[2][0]}."
    return f"{surname}{initials}"

def compute_patent_expiry_date(issue_date_str):
    if not issue_date_str:
        return ""
    issue_date_str = str(issue_date_str).strip()
    try:
        parts = issue_date_str.split('.')
        if len(parts) == 3:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            # In Russia, patent is valid for 1 year from issue date.
            return f"{day:02d}.{month:02d}.{year + 1}"
    except Exception:
        pass
    return ""
