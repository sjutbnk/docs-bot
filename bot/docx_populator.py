import docx
import mappings

def set_cell_text_preserve_format(cell, text):
    if text is None:
        text = ""
    else:
        text = str(text)
        
    # Physically remove any extra paragraphs in the cell
    while len(cell.paragraphs) > 1:
        p_element = cell.paragraphs[-1]._element
        p_element.getparent().remove(p_element)
        
    if len(cell.paragraphs) == 0:
        cell.add_paragraph()
        
    p = cell.paragraphs[0]
    # Clear and physically remove all runs except the first one
    if len(p.runs) > 0:
        p.runs[0].text = text
        for r in p.runs[1:]:
            p._element.remove(r._element)
    else:
        p.text = text

def fill_grid_cells(table, row_idx, start_col, num_cells, text_value):
    if not table or row_idx >= len(table.rows):
        return
    row = table.rows[row_idx]
    if not text_value or not isinstance(text_value, str):
        text_value = ""
    chars = list(text_value.upper())
    for i in range(num_cells):
        cell_idx = i + start_col
        if cell_idx < len(row.cells):
            char = chars[i] if i < len(chars) else ""
            set_cell_text_preserve_format(row.cells[cell_idx], char)

def fill_date_cells(table, row_idx, date_str, day_indices, month_indices, year_indices, spacer_indices=None):
    if not table or row_idx >= len(table.rows):
        return
    row = table.rows[row_idx]
    
    if not date_str or not isinstance(date_str, str):
        date_str = ""
        
    parts = date_str.split('.')
    day = parts[0] if len(parts) > 0 else ""
    month = parts[1] if len(parts) > 1 else ""
    year = parts[2] if len(parts) > 2 else ""
    
    # Clear all date cells first to prevent formatting leftovers
    for idx in day_indices + month_indices + year_indices:
        if idx < len(row.cells):
            set_cell_text_preserve_format(row.cells[idx], "")
            
    # Clear spacers
    if spacer_indices:
        for idx in spacer_indices:
            if idx < len(row.cells):
                set_cell_text_preserve_format(row.cells[idx], "")
                
    # Fill Day
    for i, idx in enumerate(day_indices):
        if idx < len(row.cells):
            char = day[i] if i < len(day) else ""
            set_cell_text_preserve_format(row.cells[idx], char)
            
    # Fill Month
    for i, idx in enumerate(month_indices):
        if idx < len(row.cells):
            char = month[i] if i < len(month) else ""
            set_cell_text_preserve_format(row.cells[idx], char)
            
    # Fill Year
    for i, idx in enumerate(year_indices):
        if idx < len(row.cells):
            char = year[i] if i < len(year) else ""
            set_cell_text_preserve_format(row.cells[idx], char)

def fill_passport_issued_by(doc, text):
    if not text or not isinstance(text, str):
        text = ""
    text_upper = text.upper()
    # Line 1 (28 chars) -> Table 29, starts at cell 1
    line1 = text_upper[:28]
    # Line 2 (28 chars) -> Table 30, starts at cell 0
    line2 = text_upper[28:56]
    # Line 3 (13 chars) -> Table 31, starts at cell 0
    line3 = text_upper[56:69]
    
    fill_grid_cells(doc.tables[mappings.PASSPORT_ISSUED_T1], 0, 1, 28, line1)
    fill_grid_cells(doc.tables[mappings.PASSPORT_ISSUED_T2], 0, 0, 28, line2)
    fill_grid_cells(doc.tables[mappings.PASSPORT_ISSUED_T3], 0, 0, 13, line3)

def fill_common_fields(doc, data):
    full_name = data.get('full_name', '')
    if not full_name:
        full_name = ""
    name_parts = full_name.split()
    surname = name_parts[0] if len(name_parts) > 0 else ""
    name = name_parts[1] if len(name_parts) > 1 else ""
    patronymic = " ".join(name_parts[2:]) if len(name_parts) > 2 else ""
    
    # 1. Name fields
    fill_grid_cells(doc.tables[mappings.SURNAME_TABLE], 0, 1, 28, surname)
    fill_grid_cells(doc.tables[mappings.NAME_TABLE], 0, 1, 28, name)
    fill_grid_cells(doc.tables[mappings.PATRONYMIC_TABLE], 0, 1, 28, patronymic)
    fill_grid_cells(doc.tables[mappings.PATRONYMIC_TABLE], 1, 1, 28, "") # Clear second patronymic line
    
    # 2. Citizenship
    fill_grid_cells(doc.tables[mappings.CITIZENSHIP_TABLE], 0, 1, 27, data.get('citizenship', ''))
    
    # 3. DOB
    fill_date_cells(doc.tables[mappings.DOB_TABLE], 0, data.get('birth_date', ''), *mappings.DOB_CELLS)
    
    # 4. Passport Series / Number / Issue Date
    fill_grid_cells(doc.tables[mappings.PASSPORT_TABLE], 0, 1, 7, data.get('passport_series', ''))
    fill_grid_cells(doc.tables[mappings.PASSPORT_TABLE], 0, 9, 9, data.get('passport_number', ''))
    fill_date_cells(doc.tables[mappings.PASSPORT_TABLE], 0, data.get('passport_issue_date', ''), *mappings.PASSPORT_DATE_CELLS)
    
    # 5. Passport Issued By
    fill_passport_issued_by(doc, data.get('passport_issued_by', ''))
    
    # 6. Patent Series / Number / Issue Date
    fill_grid_cells(doc.tables[mappings.PATENT_TABLE], 1, 1, 7, data.get('patent_series', ''))
    fill_grid_cells(doc.tables[mappings.PATENT_TABLE], 1, 9, 10, data.get('patent_number', ''))
    fill_date_cells(doc.tables[mappings.PATENT_TABLE], 1, data.get('patent_issue_date', ''), *mappings.PATENT_DATE_CELLS)
    
    # 7. Patent Validity
    fill_date_cells(doc.tables[mappings.PATENT_VALIDITY_TABLE], 0, data.get('patent_issue_date', ''), *mappings.PATENT_VALIDITY_START_CELLS)
    fill_date_cells(doc.tables[mappings.PATENT_VALIDITY_TABLE], 0, data.get('patent_expiry_date', ''), *mappings.PATENT_VALIDITY_END_CELLS)
    
    # 8. Profession
    fill_grid_cells(doc.tables[mappings.PROFESSION_TABLE], 0, 0, 28, data.get('profession', 'Овощевод'))

def fill_conclusion_document(doc, data):
    fill_common_fields(doc, data)
    # Contract conclusion date (Table 46)
    fill_date_cells(doc.tables[mappings.CONTRACT_DATE_TABLE], 1, "14.05.2026", *mappings.CONTRACT_DATE_CELLS)

def fill_termination_document(doc, data):
    fill_common_fields(doc, data)
    # Contract termination date (Table 46)
    fill_date_cells(doc.tables[mappings.CONTRACT_DATE_TABLE], 1, "30.11.2026", *mappings.CONTRACT_DATE_CELLS)
