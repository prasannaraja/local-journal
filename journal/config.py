from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
STATIC_DIR = Path(__file__).resolve().parent / "static"
DB_PATH = DATA_DIR / "journal.db"
CHROMA_DIR = DATA_DIR / "chroma"

# Ollama models
CHAT_MODEL = "llama3.2:3b"
EMBED_MODEL = "nomic-embed-text"

# ChromaDB
CHROMA_COLLECTION = "journal_entries"

# Brain dump settings
MAX_DIALOGUE_TURNS = 5
