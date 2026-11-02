import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def path(env: str, default: str) -> Path:
    return Path(os.getenv(env, str(ROOT / default))).expanduser().resolve()

DB = path("CERTFLOW_DB_PATH", "runtime/documents.sqlite3")
STORAGE = path("CERTFLOW_STORAGE_PATH", "runtime/uploads")
API_KEY = os.getenv("CERTFLOW_API_KEY", "")
MAX_BYTES = int(os.getenv("CERTFLOW_MAX_UPLOAD_BYTES", str(4 * 1024 * 1024)))
MAX_PAGES = int(os.getenv("CERTFLOW_MAX_PAGES", "20"))
EMBEDDINGS = os.getenv("CERTFLOW_EMBEDDINGS", "hash") # hash | sentence_transformers
LLM_URL = os.getenv("CERTFLOW_OLLAMA_URL", "") # optional, localhost only by operator setup
LLM_MODEL = os.getenv("CERTFLOW_OLLAMA_MODEL", "gemma3:1b")
