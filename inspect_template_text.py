import docx

def inspect_file(path):
    print(f"\n=== Inspecting {path} ===")
    doc = docx.Document(path)
    
    keywords = ['телефон', 'страхо', 'полис', 'дмс', 'омс', 'инн']
    
    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                cell_text = cell.text.lower()
                for kw in keywords:
                    if kw in cell_text:
                        print(f"Table {t_idx}, Row {r_idx}, Cell {c_idx}: '{cell.text.strip().replace('\n', ' ')}'")
                        break

inspect_file('bot/templates/template_conclusion.docx')
inspect_file('bot/templates/template_termination.docx')
