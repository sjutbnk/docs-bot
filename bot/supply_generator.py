"""
supply_generator.py — generates a supply contract from two partner card data dicts.
Uses Jinja2 (docxtpl) to fill template_supply_contract.docx.
"""

import os
import re
from docxtpl import DocxTemplate
import config
import utils


def _acting_basis(entity_type: str, director: str,
                  passport_series: str, passport_number: str,
                  passport_issued_by: str, passport_issue_date: str,
                  ogrn: str) -> str:
    """Build the 'действующего на основании' clause."""
    t = (entity_type or "ИП").strip().upper()
    if t == "ЮрЛицо".upper() or t == "ЮРЛИЦО":
        return "действующего на основании Устава"
    else:
        parts = []
        if passport_series or passport_number:
            parts.append(
                f"паспорт {passport_series} {passport_number}".strip()
            )
        if passport_issued_by:
            parts.append(f"выдан {passport_issued_by}")
        if passport_issue_date:
            parts.append(passport_issue_date)
        if ogrn:
            parts.append(f"ОГРНИП {ogrn}")
        return ", ".join(parts) if parts else "действующего на основании ОГРНИП"


def _short(full_name: str) -> str:
    return utils.get_short_name(full_name)


def generate_supply_contract(data: dict, output_dir: str) -> str:
    """
    Fill template_supply_contract.docx with supplier/buyer data and save to output_dir.
    Returns the path to the generated file.
    """
    tpl_path = os.path.join(config.TEMPLATES_DIR, "template_supply_contract.docx")
    if not os.path.exists(tpl_path):
        raise FileNotFoundError(
            "Шаблон договора поставки не найден. Пожалуйста, отправьте файл через бота."
        )

    doc = DocxTemplate(tpl_path)

    s_type = str(data.get("supplier_type") or "ИП").strip().upper()
    b_type = str(data.get("buyer_type") or "ИП").strip().upper()

    s_name = utils.clean_employer_name(str(data.get("supplier_name") or ""))
    b_name = utils.clean_employer_name(str(data.get("buyer_name") or ""))

    s_fio = utils.extract_employer_fio(s_name)
    b_fio = utils.extract_employer_fio(b_name)

    if s_type in ("ЮРЛИЦО", "ЮрЛицо".upper()):
        s_title = f'ООО "{s_fio}"'
        s_rep = str(data.get("supplier_director") or "").strip()
        s_basis = "действующего на основании Устава"
        s_sign_title = "Директор"
        s_sign_name = _short(s_rep)
        s_ogrn_label = "ОГРН"
    else:
        s_title = f"ИП {s_fio}"
        s_rep = s_fio
        s_basis = _acting_basis(
            s_type,
            s_fio,
            str(data.get("supplier_passport_series") or ""),
            str(data.get("supplier_passport_number") or ""),
            str(data.get("supplier_passport_issued_by") or ""),
            str(data.get("supplier_passport_issue_date") or ""),
            str(data.get("supplier_ogrn") or ""),
        )
        s_sign_title = "ИП"
        s_sign_name = _short(s_fio)
        s_ogrn_label = "ОГРНИП"

    if b_type in ("ЮРЛИЦО", "ЮрЛицо".upper()):
        b_title = f'ООО "{b_fio}"'
        b_rep = str(data.get("buyer_director") or "").strip()
        b_basis = "действующего на основании Устава"
        b_sign_title = "Директор"
        b_sign_name = _short(b_rep)
        b_ogrn_label = "ОГРН"
    else:
        b_title = f"ИП {b_fio}"
        b_rep = b_fio
        b_basis = _acting_basis(
            b_type,
            b_fio,
            str(data.get("buyer_passport_series") or ""),
            str(data.get("buyer_passport_number") or ""),
            str(data.get("buyer_passport_issued_by") or ""),
            str(data.get("buyer_passport_issue_date") or ""),
            str(data.get("buyer_ogrn") or ""),
        )
        b_sign_title = "ИП"
        b_sign_name = _short(b_fio)
        b_ogrn_label = "ОГРНИП"

    context = {
        # Вводный абзац (шапка договора)
        "supplier_intro":       str(data.get("supplier_name") or s_title).strip(),
        "supplier_basis":       s_basis,
        "buyer_intro":          str(data.get("buyer_name") or b_title).strip(),

        # Сроки (из FSM)
        "contract_end_date":    str(data.get("contract_end_date") or ""),
        "delivery_days":        str(data.get("delivery_days") or ""),

        # Поставщик — реквизиты
        "supplier_title":       s_title,
        "supplier_rep":         s_rep,
        "supplier_name":        s_name,
        "supplier_inn":         str(data.get("supplier_inn") or ""),
        "supplier_ogrn":        str(data.get("supplier_ogrn") or ""),
        "supplier_ogrn_label":  s_ogrn_label,
        "supplier_address":     str(data.get("supplier_address") or ""),
        "supplier_rs":          str(data.get("supplier_rs") or ""),
        "supplier_ks":          str(data.get("supplier_ks") or ""),
        "supplier_bik":         str(data.get("supplier_bik") or ""),
        "supplier_bank":        str(data.get("supplier_bank") or ""),
        "supplier_sign_title":  s_sign_title,
        "supplier_sign_name":   s_sign_name,

        # Покупатель — реквизиты
        "buyer_title":          b_title,
        "buyer_rep":            b_rep,
        "buyer_basis":          b_basis,
        "buyer_name":           b_name,
        "buyer_inn":            str(data.get("buyer_inn") or ""),
        "buyer_ogrn":           str(data.get("buyer_ogrn") or ""),
        "buyer_ogrn_label":     b_ogrn_label,
        "buyer_address":        str(data.get("buyer_address") or ""),
        "buyer_rs":             str(data.get("buyer_rs") or ""),
        "buyer_ks":             str(data.get("buyer_ks") or ""),
        "buyer_bik":            str(data.get("buyer_bik") or ""),
        "buyer_bank":           str(data.get("buyer_bank") or ""),
        "buyer_sign_title":     b_sign_title,
        "buyer_sign_name":      b_sign_name,
    }

    doc.render(context)

    safe_s = re.sub(r"[^\w\s-]", "", s_fio).replace(" ", "_")
    safe_b = re.sub(r"[^\w\s-]", "", b_fio).replace(" ", "_")
    output_path = os.path.join(output_dir, f"Договор_поставки_{safe_s}_{safe_b}.docx")
    doc.save(output_path)
    return output_path
