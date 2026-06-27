from docxtpl import DocxTemplate
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_documents(data, output_dir):
    # DOCX
    template_docx = os.path.join(BASE_DIR, "templates", "template_contract.docx")
    doc = DocxTemplate(template_docx)
    doc.render(data)
    
    safe_name = data.get('full_name', 'Сотрудник').replace(' ', '_')
    docx_path = os.path.join(output_dir, f"Договор_прием_{safe_name}.docx")
    doc.save(docx_path)
    
    # RTF
    template_rtf = os.path.join(BASE_DIR, "templates", "template_termination.rtf")
    with open(template_rtf, "r", encoding="cp1251", errors='ignore') as f:
        rtf_text = f.read()
    
    # Simple RTF string replacement
    for key, val in data.items():
        placeholder = f"{{{{{key}}}}}"
        rtf_text = rtf_text.replace(placeholder, str(val))
        
    rtf_path = os.path.join(output_dir, f"Уведомление_расторжение_{safe_name}.rtf")
    with open(rtf_path, "w", encoding="cp1251", errors='ignore') as f:
        f.write(rtf_text)
        
    return docx_path, rtf_path
