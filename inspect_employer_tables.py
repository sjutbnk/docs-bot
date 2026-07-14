import docx

doc = docx.Document('bot/templates/template_conclusion.docx')

def inspect(idx):
    t = doc.tables[idx]
    cells_texts = []
    seen = set()
    for r in t.rows:
        for cell in r.cells:
            if cell._tc not in seen:
                seen.add(cell._tc)
                txt = cell.text.strip().replace('\n', ' ')
                if txt:
                    cells_texts.append(txt)
    print(f"Table {idx}: {cells_texts}")

# Inspect tables 0 to 20
for i in range(21):
    inspect(i)
