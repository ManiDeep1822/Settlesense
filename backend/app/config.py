import os
from pathlib import Path
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

load_dotenv(ROOT_DIR / ".env", override=True)
load_dotenv(BACKEND_DIR / ".env", override=True)

DB_PATH = os.getenv("DB_PATH", str(BACKEND_DIR / "settlesense.db"))
CHROMA_DIR = os.getenv("CHROMA_DIR", str(BACKEND_DIR / "chroma_db"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MERCHANT_ID = os.getenv("DEFAULT_MERCHANT_ID", "mer_rzp_live_884920")
