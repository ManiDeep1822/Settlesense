import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.retrieval import index_all_records

if __name__ == "__main__":
    count = index_all_records()
    print(f"Successfully indexed {count} documents into ChromaDB vector store.")
