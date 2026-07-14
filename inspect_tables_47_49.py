import docx

doc = docx.Document('bot/templates/template_conclusion.docx')

def inspect(idx):
    print(f"\n=== Table {idx} ===")
    t = doc.tables[idx]
    for r_idx, row in enumerate(t.rows):
        cells_texts = []
        seen = set()
        for cell in row.cells:
            if cell._tc not in seen:
                seen.add(cell._tc)
                cells_texts.append(cell.text.strip().replace('\n', ' '))
        print(f"  Row {r_idx} (cells: {len(row.cells)}): {cells_texts}")

inspect(47)
inspect(48)
inspect(49)
