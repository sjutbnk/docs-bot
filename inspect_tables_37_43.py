import docx

doc = docx.Document('bot/templates/template_conclusion.docx')

def inspect(idx):
    print(f"\n=== Table {idx} ===")
    t = doc.tables[idx]
    print(f"Rows: {len(t.rows)}, Cells in Row 0: {len(t.rows[0].cells)}")
    for r_idx, row in enumerate(t.rows):
        cells_texts = []
        seen = set()
        for cell in row.cells:
            if cell._tc not in seen:
                seen.add(cell._tc)
                cells_texts.append(cell.text.strip().replace('\n', ' '))
        print(f"  Row {r_idx}: {cells_texts}")

for i in range(37, 44):
    inspect(i)
