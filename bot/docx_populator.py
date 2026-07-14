import docx
import mappings
import utils


# ---------------------------------------------------------------------------
# Low-level cell helpers
# ---------------------------------------------------------------------------

def _set_cell_text(cell, text: str):
    """
    Write text into a table cell while preserving the original run formatting.
    Extra runs beyond the first are blanked (not deleted) to keep formatting intact.
    Extra paragraphs are also blanked rather than removed to avoid layout shifts.
    """
    text = str(text) if text is not None else ""

    # Blank extra paragraphs (keep them for layout)
    for p in cell.paragraphs[1:]:
        for r in p.runs:
            r.text = ""

    if not cell.paragraphs:
        cell.add_paragraph()

    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.text = text


def _fill_grid(table, row_idx: int, start_col: int, num_cells: int, value: str):
    """Write value character-by-character into consecutive grid cells."""
    if not table or row_idx >= len(table.rows):
        return
    row = table.rows[row_idx]
    chars = list((value or "").upper())
    for i in range(num_cells):
        col = start_col + i
        if col < len(row.cells):
            _set_cell_text(row.cells[col], chars[i] if i < len(chars) else "")


def _fill_date(table, row_idx: int, date_str: str,
               day_idx, month_idx, year_idx, spacer_idx=None):
    """
    Write a DD.MM.YYYY date into separate day/month/year grid cells.
    Accepts index lists for each component.
    """
    if not table or row_idx >= len(table.rows):
        return
    row = table.rows[row_idx]

    parts = (date_str or "").split(".")
    day   = parts[0] if len(parts) > 0 else ""
    month = parts[1] if len(parts) > 1 else ""
    year  = parts[2] if len(parts) > 2 else ""

    # Clear all target cells first
    for idx in list(day_idx) + list(month_idx) + list(year_idx) + list(spacer_idx or []):
        if idx < len(row.cells):
            _set_cell_text(row.cells[idx], "")

    for i, idx in enumerate(day_idx):
        if idx < len(row.cells):
            _set_cell_text(row.cells[idx], day[i] if i < len(day) else "")
    for i, idx in enumerate(month_idx):
        if idx < len(row.cells):
            _set_cell_text(row.cells[idx], month[i] if i < len(month) else "")
    for i, idx in enumerate(year_idx):
        if idx < len(row.cells):
            _set_cell_text(row.cells[idx], year[i] if i < len(year) else "")


# ---------------------------------------------------------------------------
# Shared employee fields (used by both conclusion & termination notifications)
# ---------------------------------------------------------------------------

def _fill_employee_fields(doc, data: dict):
    """Fill all employee-side fields in the МВД notification template."""
    full_name = str(data.get("full_name") or "")
    name_parts = full_name.split()
    surname    = name_parts[0] if len(name_parts) > 0 else ""
    first_name = name_parts[1] if len(name_parts) > 1 else ""
    patronymic = " ".join(name_parts[2:]) if len(name_parts) > 2 else ""

    # Phone (digits only, up to 11)
    phone = "".join(c for c in str(data.get("phone") or "") if c.isdigit())
    _fill_grid(doc.tables[mappings.PHONE_TABLE], 0, 1, 11, phone)

    # Name fields
    _fill_grid(doc.tables[mappings.SURNAME_TABLE],    0, 1, 28, surname)
    _fill_grid(doc.tables[mappings.NAME_TABLE],       0, 1, 28, first_name)
    _fill_grid(doc.tables[mappings.PATRONYMIC_TABLE], 0, 1, 28, patronymic)
    _fill_grid(doc.tables[mappings.PATRONYMIC_TABLE], 1, 1, 28, "")  # clear line 2

    # Citizenship
    _fill_grid(doc.tables[mappings.CITIZENSHIP_TABLE], 0, 1, 27, data.get("citizenship") or "")

    # Date of birth
    _fill_date(doc.tables[mappings.DOB_TABLE], 0,
               data.get("birth_date") or "", *mappings.DOB_CELLS)

    # Passport series / number / issue date
    _fill_grid(doc.tables[mappings.PASSPORT_TABLE], 0, 1,  7, data.get("passport_series") or "")
    _fill_grid(doc.tables[mappings.PASSPORT_TABLE], 0, 9,  9, data.get("passport_number") or "")
    _fill_date(doc.tables[mappings.PASSPORT_TABLE], 0,
               data.get("passport_issue_date") or "", *mappings.PASSPORT_DATE_CELLS)

    # Passport issued-by (МВД unit code only, split across 3 tables)
    issued = utils.clean_passport_issued_by(data.get("passport_issued_by") or "")
    issued_upper = issued.upper()
    _fill_grid(doc.tables[mappings.PASSPORT_ISSUED_T1], 0, 1, 28, issued_upper[:28])
    _fill_grid(doc.tables[mappings.PASSPORT_ISSUED_T2], 0, 0, 28, issued_upper[28:56])
    _fill_grid(doc.tables[mappings.PASSPORT_ISSUED_T3], 0, 0, 13, issued_upper[56:69])

    # Patent series / number / issue date
    _fill_grid(doc.tables[mappings.PATENT_TABLE], 1, 1,  7, data.get("patent_series") or "")
    _fill_grid(doc.tables[mappings.PATENT_TABLE], 1, 9, 10, data.get("patent_number") or "")
    _fill_date(doc.tables[mappings.PATENT_TABLE], 1,
               data.get("patent_issue_date") or "", *mappings.PATENT_DATE_CELLS)

    # Patent validity period
    _fill_date(doc.tables[mappings.PATENT_VALIDITY_TABLE], 0,
               data.get("patent_issue_date") or "", *mappings.PATENT_VALIDITY_START_CELLS)
    _fill_date(doc.tables[mappings.PATENT_VALIDITY_TABLE], 0,
               data.get("patent_expiry_date") or "", *mappings.PATENT_VALIDITY_END_CELLS)

    # Profession — always cleared (left blank per client request)
    _fill_grid(doc.tables[mappings.PROFESSION_TABLE], 0, 0, 34, "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fill_conclusion_document(doc, data: dict):
    """Populate МВД notification of contract conclusion."""
    _fill_employee_fields(doc, data)
    _fill_date(doc.tables[mappings.CONTRACT_DATE_TABLE], 1,
               "14.05.2026", *mappings.CONTRACT_DATE_CELLS)


def fill_termination_document(doc, data: dict):
    """Populate МВД notification of contract termination."""
    _fill_employee_fields(doc, data)
    _fill_date(doc.tables[mappings.CONTRACT_DATE_TABLE], 1,
               "30.11.2026", *mappings.CONTRACT_DATE_CELLS)


def fill_patent_notification_document(doc, data: dict):
    """
    Populate the patent labour-activity notification (Приказ МВД № 655).
    Employer section is skipped when the default employer (Generalov A.V.) is
    detected — his details are pre-filled in the template to preserve alignment.
    """
    emp_inn = str(data.get("employer_inn") or "").strip()
    is_default_employer = (emp_inn == "312009347140" or not data.get("employer_name"))

    # ── Employer block ──────────────────────────────────────────────────────
    if not is_default_employer:
        emp_type = str(data.get("employer_type") or "ИП").strip().upper()
        emp_name = str(data.get("employer_name") or "").upper()
        emp_addr = str(data.get("employer_address") or "").upper()

        # Name split across 5 rows × 31 chars
        for row_offset, t_idx in enumerate(range(31, 36)):
            _fill_grid(doc.tables[t_idx], 0, 0, 31,
                       emp_name[row_offset * 31 : (row_offset + 1) * 31])

        _fill_grid(doc.tables[36], 0, 0, 31, str(data.get("employer_ogrn") or ""))

        if emp_type == "ИП":
            series     = str(data.get("employer_passport_series") or "")
            number     = str(data.get("employer_passport_number") or "")
            issued_by  = str(data.get("employer_passport_issued_by") or "")
            issue_date = str(data.get("employer_passport_issue_date") or "")
            pass_str   = f"ПАСПОРТ {series} {number} {issued_by}".upper()
            _fill_grid(doc.tables[38], 0, 0, 31, pass_str[:31])
            _fill_grid(doc.tables[38], 1, 0, 31, pass_str[31:62])
            rest = f"{pass_str[62:]} {issue_date}Г.".strip().upper()
            _fill_grid(doc.tables[38], 2, 0, 31, rest[:31])
        else:
            for r in range(4):
                _fill_grid(doc.tables[38], r, 0, 31, "")

        # Employer address (tables 39, 40, 41)
        _fill_grid(doc.tables[39], 0, 0, 31, emp_addr[:31])
        _fill_grid(doc.tables[40], 0, 0, 31, emp_addr[31:62])
        _fill_grid(doc.tables[41], 0, 0, 31, emp_addr[62:93])

        # Employer contact phone (hardcoded per partner card)
        _fill_grid(doc.tables[43], 0, 1, 11, "89608626599")

    # ── Employee block ──────────────────────────────────────────────────────
    full_name  = str(data.get("full_name") or "")
    name_parts = full_name.split()
    surname    = name_parts[0] if len(name_parts) > 0 else ""
    first_name = name_parts[1] if len(name_parts) > 1 else ""
    patronymic = " ".join(name_parts[2:]) if len(name_parts) > 2 else ""

    _fill_grid(doc.tables[3], 0, 1, 28, surname)
    _fill_grid(doc.tables[4], 0, 1, 28, first_name)
    _fill_grid(doc.tables[5], 0, 1, 28, patronymic)
    _fill_grid(doc.tables[5], 1, 1, 28, "")  # clear line 2

    _fill_grid(doc.tables[6], 0, 1, 28, data.get("citizenship") or "")

    _fill_date(doc.tables[7], 0, data.get("birth_date") or "",
               [2, 3], [6, 7], [10, 11, 12, 13], [4, 5, 8, 9])

    # Passport series / number
    _fill_grid(doc.tables[9], 0, 1, 4, data.get("passport_series") or "")
    _fill_grid(doc.tables[9], 0, 9, 9, data.get("passport_number") or "")

    # Passport issue date
    _fill_date(doc.tables[10], 0, data.get("passport_issue_date") or "",
               [2, 3], [6, 7], [10, 11, 12, 13], [4, 5, 8, 9])

    # Passport issued-by (МВД code only, across tables 11 and 12)
    issued = utils.clean_passport_issued_by(data.get("passport_issued_by") or "").upper()
    _fill_grid(doc.tables[11], 0, 1, 25, issued[:25])
    _fill_grid(doc.tables[12], 0, 0, 26, issued[25:51])

    # Patent details
    _fill_grid(doc.tables[13], 0, 1,  7, data.get("patent_series") or "")
    _fill_grid(doc.tables[13], 0, 9, 10, data.get("patent_number") or "")
    _fill_date(doc.tables[13], 0, data.get("patent_issue_date") or "",
               [21, 22], [25, 26], [29, 30, 31, 32], [23, 24, 27, 28])

    # Profession — always blank
    _fill_grid(doc.tables[14], 0, 0, 31, "")
    _fill_grid(doc.tables[15], 0, 0, 31, "")
    _fill_grid(doc.tables[16], 0, 0, 31, "")

    # Place of work
    work_addr = str(data.get("work_address") or data.get("employer_address") or "").upper()
    _fill_grid(doc.tables[17], 0, 0, 31, work_addr[:31])
    _fill_grid(doc.tables[18], 0, 0, 31, work_addr[31:62])

    # Contract type checkbox (GPH ✓)
    _set_cell_text(doc.tables[20].rows[0].cells[2], "V")

    # Contract date
    _fill_date(doc.tables[22], 1, "14.05.2026",
               [2, 3], [6, 7], [10, 11, 12, 13], [4, 5, 8, 9])

    # Employee INN
    _fill_grid(doc.tables[23], 0, 1, 12, str(data.get("inn") or ""))

    # DMS policy series + number
    _fill_grid(doc.tables[27], 0, 1,  5, "MRF")
    _fill_grid(doc.tables[27], 0, 7, 12, str(data.get("dms_number") or ""))

    # DMS issue date (uses contract start date as proxy)
    _fill_date(doc.tables[28], 0, "14.05.2026",
               [2, 3], [6, 7], [10, 11, 12, 13], [4, 5, 8, 9])

    # Employee contact phone
    emp_phone = "".join(c for c in str(data.get("phone") or "") if c.isdigit())
    _fill_grid(doc.tables[29], 0, 1, 11, emp_phone)

    # Signature full name and submission date
    _set_cell_text(doc.tables[44].rows[0].cells[1], full_name.upper())
    _set_cell_text(doc.tables[45].rows[0].cells[1], "14")
    _set_cell_text(doc.tables[45].rows[0].cells[3], "05")
    _set_cell_text(doc.tables[45].rows[0].cells[5], "26")
