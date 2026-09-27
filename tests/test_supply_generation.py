"""Offline smoke tests for document generation."""

import zipfile
from pathlib import Path

import supply_generator


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _party(prefix: str) -> dict:
    return {
        f"{prefix}_type": "ИП",
        f"{prefix}_name": f"ИП Иванов Иван Иванович",
        f"{prefix}_inn": "123456789012",
        f"{prefix}_ogrn": "123456789012345",
        f"{prefix}_address": "Астраханская область, г. Ахтубинск",
        f"{prefix}_rs": "40802810905000025734",
        f"{prefix}_ks": "30101810500000000602",
        f"{prefix}_bik": "041203602",
        f"{prefix}_bank": "Тестовый банк",
        f"{prefix}_passport_series": "1219",
        f"{prefix}_passport_number": "810165",
        f"{prefix}_passport_issued_by": "УМВД России",
        f"{prefix}_passport_issue_date": "26.03.2020",
    }


def _contract_data(contract_type: str) -> dict:
    data = {
        **_party("supplier"),
        **_party("buyer"),
        "contract_type": contract_type,
        "contract_start_date": "01.06.2026",
        "contract_end_date": "30.06.2026",
    }
    data["buyer_name"] = "ИП Петров Петр Петрович"
    return data


def test_supply_contract_templates_generate_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(supply_generator.config, "TEMPLATES_DIR", str(PROJECT_ROOT / "bot" / "templates"))

    for contract_type in ("vat", "no_vat"):
        output_path = Path(
            supply_generator.generate_supply_contract(
                _contract_data(contract_type), str(tmp_path / contract_type)
            )
        )

        assert output_path.is_file()
        assert output_path.stat().st_size > 0
        with zipfile.ZipFile(output_path) as document:
            assert "[Content_Types].xml" in document.namelist()
            assert "word/document.xml" in document.namelist()
