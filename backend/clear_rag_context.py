"""
Clear all persisted RAG context for the EV backend.

Usage:
  python clear_rag_context.py
"""

from rag import RAGStore


def main() -> None:
    store = RAGStore()
    store.clear()
    print("[RAG] Cleared persisted RAG context from rag_index/")


if __name__ == "__main__":
    main()
