import os
import docx
from docxtpl import DocxTemplate

import config
import utils
from docx_populator import fill_conclusion_document, fill_termination_document

def generate_documents(data, output_dir):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Automatically compute patent expiry date if missing
    if data.get('patent_issue_date'):
        issue_date = str(data['patent_issue_date']).strip()
        if not data.get('patent_expiry_date') or str(data['patent_expiry_date']).strip() == "":
            data['patent_expiry_date'] = utils.compute_patent_expiry_date(issue_date)
                
    safe_name = data.get('full_name', 'Сотрудник').replace(' ', '_')
    
    # 2. DOCX Contract (Jinja docxtpl)
    doc_data = data.copy()
    doc_data['contract_start_date'] = "14.05.2026"
    doc_data['contract_end_date'] = "30.11.2026"
    doc_data['short_name'] = utils.get_short_name(data.get('full_name', ''))
    
    template_contract = os.path.join(config.TEMPLATES_DIR, "template_contract.docx")
    doc_c = DocxTemplate(template_contract)
    doc_c.render(doc_data)
    
    docx_path = os.path.join(output_dir, f"Договор_прием_{safe_name}.docx")
    doc_c.save(docx_path)
    
    # 3. DOCX Conclusion Notification (fill character-by-character)
    template_conclusion = os.path.join(config.TEMPLATES_DIR, "template_conclusion.docx")
    doc_concl = docx.Document(template_conclusion)
    fill_conclusion_document(doc_concl, data)
    
    conclusion_path = os.path.join(output_dir, f"Уведомление_прием_{safe_name}.docx")
    doc_concl.save(conclusion_path)
    
    # 4. DOCX Termination Notification (fill character-by-character)
    template_termination = os.path.join(config.TEMPLATES_DIR, "template_termination.docx")
    doc_term = docx.Document(template_termination)
    fill_termination_document(doc_term, data)
    
    termination_path = os.path.join(output_dir, f"Уведомление_расторжение_{safe_name}.docx")
    doc_term.save(termination_path)
    
    return docx_path, conclusion_path, termination_path
