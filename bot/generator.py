import os
import docx
from docxtpl import DocxTemplate

import config
import utils
from docx_populator import (
    fill_conclusion_document,
    fill_termination_document,
    fill_patent_notification_document,
)


def generate_documents(data: dict, output_dir: str) -> tuple:
    """
    Generate all four employment documents for a single employee.

    Returns:
        Tuple of (contract_path, conclusion_path, termination_path, patent_notif_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Merge default employer if no Partner Card was uploaded
    if not data.get("employer_name") or not str(data.get("employer_name")).strip():
        for key, val in config.DEFAULT_EMPLOYER.items():
            data.setdefault(key, val)

    # 2. Compute patent expiry date if missing
    if data.get("patent_issue_date") and not str(data.get("patent_expiry_date", "")).strip():
        data["patent_expiry_date"] = utils.compute_patent_expiry_date(
            str(data["patent_issue_date"]).strip()
        )

    # 3. Clean passport issued-by to МВД unit code
    if data.get("passport_issued_by"):
        data["passport_issued_by"] = utils.clean_passport_issued_by(
            data["passport_issued_by"]
        )

    safe_name = (data.get("full_name") or "Сотрудник").replace(" ", "_")

    # ── Contract (Jinja2 template) ──────────────────────────────────────────
    contract_data = data.copy()
    contract_data["contract_start_date"] = "14.05.2026"
    contract_data["contract_end_date"]   = "30.11.2026"
    contract_data["short_name"]          = utils.get_short_name(data.get("full_name") or "")
    
    # Extract clean FIO for short name (e.g. "Ким В.Р.")
    pure_fio = utils.extract_employer_fio(data.get("employer_name") or "")
    contract_data["short_employer_name"] = utils.get_short_name(pure_fio)

    # Foreigner address in the contract comes from the Partner Card registration field
    contract_data["address"] = (
        data.get("foreigner_registration_address")
        or data.get("work_address")
        or data.get("employer_address")
        or data.get("address")
        or ""
    )

    tpl_contract = os.path.join(config.TEMPLATES_DIR, "template_contract.docx")
    doc_c = DocxTemplate(tpl_contract)
    doc_c.render(contract_data)
    contract_path = os.path.join(output_dir, f"Договор_прием_{safe_name}.docx")
    doc_c.save(contract_path)

    # ── Conclusion notification (grid-fill) ─────────────────────────────────
    tpl_concl = os.path.join(config.TEMPLATES_DIR, "template_conclusion.docx")
    doc_concl = docx.Document(tpl_concl)
    fill_conclusion_document(doc_concl, data)
    conclusion_path = os.path.join(output_dir, f"Уведомление_прием_{safe_name}.docx")
    doc_concl.save(conclusion_path)

    # ── Termination notification (grid-fill) ────────────────────────────────
    tpl_term = os.path.join(config.TEMPLATES_DIR, "template_termination.docx")
    doc_term = docx.Document(tpl_term)
    fill_termination_document(doc_term, data)
    termination_path = os.path.join(output_dir, f"Уведомление_расторжение_{safe_name}.docx")
    doc_term.save(termination_path)

    # ── Patent notification (grid-fill) ─────────────────────────────────────
    tpl_patent = os.path.join(config.TEMPLATES_DIR, "template_patent_notification.docx")
    doc_pn = docx.Document(tpl_patent)
    fill_patent_notification_document(doc_pn, data)
    
    citizen = str(data.get("citizenship") or "").strip().lower()
    if "узбек" in citizen:
        cit_str = "от_узбека"
    elif "таджик" in citizen:
        cit_str = "от_таджика"
    elif citizen:
        cit_str = f"от_{citizen}"
    else:
        cit_str = "от_иностранца"
        
    patent_path = os.path.join(output_dir, f"Уведомление_{cit_str}_{safe_name}.docx")
    doc_pn.save(patent_path)

    return contract_path, conclusion_path, termination_path, patent_path
