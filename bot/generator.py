from docxtpl import DocxTemplate
import docx
import os
from docx_populator import fill_conclusion_document, fill_termination_document

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_documents(data, output_dir):
    # Automatically compute patent expiry date (1 year after issue date) if missing or empty
    if data.get('patent_issue_date'):
        issue_date = str(data['patent_issue_date']).strip()
        if not data.get('patent_expiry_date') or str(data['patent_expiry_date']).strip() == "":
            try:
                parts = issue_date.split('.')
                if len(parts) == 3:
                    day = int(parts[0])
                    month = int(parts[1])
                    year = int(parts[2])
                    # Patents are valid for exactly 1 year
                    data['patent_expiry_date'] = f"{day:02d}.{month:02d}.{year + 1}"
            except Exception:
                pass
                
    safe_name = data.get('full_name', 'Сотрудник').replace(' ', '_')
    
    # 1. DOCX Договор (через Jinja docxtpl)
    doc_data = data.copy()
    doc_data['contract_start_date'] = "14.05.2026"
    doc_data['contract_end_date'] = "30.11.2026"
    
    template_contract = os.path.join(BASE_DIR, "templates", "template_contract.docx")
    doc_c = DocxTemplate(template_contract)
    doc_c.render(doc_data)
    
    docx_path = os.path.join(output_dir, f"Договор_прием_{safe_name}.docx")
    doc_c.save(docx_path)
    
    # 2. DOCX Уведомление о приеме (через посимвольный docx_populator)
    template_conclusion = os.path.join(BASE_DIR, "templates", "template_conclusion.docx")
    doc_concl = docx.Document(template_conclusion)
    fill_conclusion_document(doc_concl, data)
    
    conclusion_path = os.path.join(output_dir, f"Уведомление_прием_{safe_name}.docx")
    doc_concl.save(conclusion_path)
    
    # 3. DOCX Уведомление о расторжении (через посимвольный docx_populator)
    template_termination = os.path.join(BASE_DIR, "templates", "template_termination.docx")
    doc_term = docx.Document(template_termination)
    fill_termination_document(doc_term, data)
    
    termination_path = os.path.join(output_dir, f"Уведомление_расторжение_{safe_name}.docx")
    doc_term.save(termination_path)
    
    return docx_path, conclusion_path, termination_path
