import docx

doc = docx.Document('bot/templates/template_conclusion.docx')

for idx in range(30, 46):
    print(f"\n=== Table {idx} ===")
    t = doc.tables[idx]
    if len(t.rows) > 0:
        for r_idx, r in enumerate(t.rows):
            # Print unique cells in row
            cells_texts = []
            seen = set()
            for cell in r.cells:
                if cell._tc not in seen:
                    seen.add(cell._tc)
                    cells_texts.append(cell.text.strip().replace('\n', ' '))
            print(f"  Row {r_idx}: {cells_texts}")
