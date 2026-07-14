import docx

path = "/mnt/c/Users/razer/Downloads/Telegram Desktop/Уведомление  АБДИЕВ 2026.docx"
doc = docx.Document(path)

print("=== INSPECTING ALL TABLES OF THE NEW TEMPLATE ===")
for t_idx, t in enumerate(doc.tables):
    print(f"\n--- Table {t_idx} ---")
    print(f"Rows: {len(t.rows)}, Cells in Row 0: {len(t.rows[0].cells)}")
    for r_idx, row in enumerate(t.rows):
        cells_texts = []
        seen = set()
        for c_idx, cell in enumerate(row.cells):
            if cell._tc not in seen:
                seen.add(cell._tc)
                txt = cell.text.strip().replace('\n', ' ')
                if txt:
                    cells_texts.append(f"C{c_idx}: '{txt}'")
        if cells_texts:
            print(f"  Row {r_idx}: {', '.join(cells_texts)}")
