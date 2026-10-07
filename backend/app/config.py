import os
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv("DATA_DIR", BASE / "data"))
TEXTS = DATA / "texts"
DB_PATH = DATA / "precedent.db"
CHROMA_DIR = DATA / "chroma"
MODEL_PATH = DATA / "model.joblib"
METRICS_PATH = DATA / "metrics.json"
USER_AGENT = os.getenv("SEC_USER_AGENT", "PrecedentFinder research tool your.name@example.com")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
for d in (DATA, TEXTS): d.mkdir(parents=True, exist_ok=True)
