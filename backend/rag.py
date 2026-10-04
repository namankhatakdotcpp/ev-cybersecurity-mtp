import json
import os
from typing import Any, Dict, List, Tuple

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None

INDEX_DIR = os.path.join(_THIS_DIR, "rag_index")
EMBED_MODEL_NAME = os.environ.get("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")


class RAGStore:
    """Simple RAG store using sentence-transformers + FAISS."""

    def __init__(self, index_dir: str = INDEX_DIR, embed_model_name: str = EMBED_MODEL_NAME):
        self.index_dir = index_dir
        os.makedirs(self.index_dir, exist_ok=True)
        self.meta_path = os.path.join(self.index_dir, "meta.json")
        self.index_path = os.path.join(self.index_dir, "index.faiss")
        self.model_name = embed_model_name

        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers is required for RAGStore. Install with `pip install sentence-transformers faiss-cpu`"
            )

        self.model = SentenceTransformer(self.model_name)
        self.embeddings = []
        self.metadatas = []
        self.index = None
        self._load()

    def _build_index(self) -> None:
        import numpy as np

        d = self.embeddings[0].shape[0] if self.embeddings else self.model.get_sentence_embedding_dimension()
        xb = np.vstack(self.embeddings).astype("float32") if self.embeddings else np.zeros((0, d), dtype="float32")
        if faiss is None:
            raise ImportError("faiss is required for RAGStore. Install with `pip install faiss-cpu`")

        index = faiss.IndexFlatIP(d)
        faiss.normalize_L2(xb)
        if xb.shape[0] > 0:
            index.add(xb)
        self.index = index

    def _load(self) -> None:
        try:
            if os.path.exists(self.meta_path):
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self.metadatas = meta.get("metadatas", [])
                    texts = [m.get("text", "") for m in self.metadatas]
                    if texts:
                        self.embeddings = [self.model.encode(t) for t in texts]
                    else:
                        self.embeddings = []
            else:
                self.metadatas = []
                self.embeddings = []
        except Exception:
            self.metadatas = []
            self.embeddings = []

        self._build_index()

    def save(self) -> None:
        meta = {"metadatas": self.metadatas, "model_name": self.model_name}
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        if self.index is not None and faiss is not None:
            try:
                faiss.write_index(self.index, self.index_path)
            except Exception:
                pass

    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        import numpy as np

        texts = [d.get("text", "") for d in docs]
        if not texts:
            return

        vecs = self.model.encode(texts)
        for i, d in enumerate(docs):
            meta = {
                "id": d.get("id"),
                "kiosk": d.get("kiosk"),
                "text": d.get("text"),
                "meta": d.get("meta", {}),
            }
            self.metadatas.append(meta)
            self.embeddings.append(vecs[i])

        self._build_index()
        if self.index is not None and len(self.embeddings) > 0:
            xb = np.vstack(self.embeddings).astype("float32")
            faiss.normalize_L2(xb)
            d = xb.shape[1]
            self.index = faiss.IndexFlatIP(d)
            self.index.add(xb)

        self.save()

    def search(self, query: str, top_k: int = 3, score_threshold: float = 0.3) -> List[Tuple[Dict[str, Any], float]]:
        if not self.metadatas:
            return []

        qv = self.model.encode([query])[0].astype("float32")
        faiss.normalize_L2(qv.reshape(1, -1))

        if self.index is None:
            self._build_index()

        dists, idxs = self.index.search(qv.reshape(1, -1), top_k)
        results = []
        for score, idx in zip(dists[0], idxs[0]):
            if idx < 0 or idx >= len(self.metadatas):
                continue
            sim = float(score)
            if sim >= score_threshold:
                results.append((self.metadatas[idx], sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def clear(self) -> None:
        """Remove all stored RAG context from memory and disk."""
        self.metadatas = []
        self.embeddings = []
        self._build_index()

        for path in (self.meta_path, self.index_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

        # Persist empty state so next session starts clean.
        self.save()
