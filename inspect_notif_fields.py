import docx

doc = docx.Document("bot/templates/template_patent_notification.docx")

def inspect_table(idx):
    t = doc.tables[idx]
    print(f"\nTable {idx} (rows={len(t.rows)}, cells_in_row_0={len(t.rows[0].cells)}):")
    for r_idx, row in enumerate(t.rows):
        cells_texts = []
        seen = set()
        for c_idx, cell in enumerate(row.cells):
            if cell._tc not in seen:
                seen.add(cell._tc)
                txt = cell.text.strip().replace('\n', ' ')
                cells_texts.append(f"C{c_idx}: '{txt}'")
        print(f"  Row {r_idx}: {cells_texts}")

indices = [3, 4, 5, 6, 7, 9, 10, 11, 13, 14, 17, 18, 19, 20, 22, 23, 27, 28, 29, 31, 32, 33, 34, 36, 38, 39, 40, 41, 43, 44]
for idx in indices:
    inspect_table(idx)
