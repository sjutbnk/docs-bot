import os
import logging

# ---------------------------------------------------------------------------
# .env loader (no external dependency)
# ---------------------------------------------------------------------------

def _load_env():
    for path in (".env", "../.env", "bot/.env"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(
                            key.strip(),
                            val.strip().strip("'").strip('"'),
                        )
            break

_load_env()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger("auto-docs-bot")

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Default employer fallback (ИП ГКФХ Генералов А.В.)
# Used when no Partner Card is uploaded.
# ---------------------------------------------------------------------------

DEFAULT_EMPLOYER = {
    "employer_type": "ИП",
    "employer_name": (
        "ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ ГЛАВА КРЕСТЬЯНСКОГО "
        "(ФЕРМЕРСКОГО) ХОЗЯЙСТВА ГЕНЕРАЛОВ АЛЕКСАНДР ВАЛЕРИЕВИЧ"
    ),
    "employer_inn": "312009347140",
    "employer_ogrn": "319302500024366",
    "employer_address": (
        "416511, АСТРАХАНСКАЯ ОБЛАСТЬ, АХТУБИНСКИЙ РАЙОН, "
        "С. ПОКРОВКА, УЛ. СОВЕТСКАЯ, Д. 41"
    ),
    "employer_passport_series": "1219",
    "employer_passport_number": "810165",
    "employer_passport_issue_date": "26.03.2020",
    "employer_passport_issued_by": "УМВД РОССИИ ПО АСТРАХАНСКОЙ ОБЛАСТИ",
    "work_address": "416511 Астрахань область Ахтубинский район село Покровка",
    "foreigner_registration_address": (
        "Астраханская область, Ахтубинский муниципальный район, "
        "городское поселение город Ахтубинск, территория №5, д.2"
    ),
}
