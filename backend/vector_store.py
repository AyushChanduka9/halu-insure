"""
Simple local RAG vector store for the auditor.

What this file does:
1) Load small trusted text files from backend/knowledge_base/
2) Split them into beginner-friendly text chunks
3) Build embeddings with sentence-transformers
4) Index vectors in FAISS
5) Retrieve top relevant chunks for a query
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np

_DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge_base"


@dataclass
class RetrievedChunk:
    text: str
    source: str
    score: float


class LocalVectorStore:
    def __init__(
        self,
        *,
        knowledge_dir: Path = _KNOWLEDGE_DIR,
        model_name: str = _DEFAULT_EMBEDDING_MODEL,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
    ) -> None:
        self.knowledge_dir = knowledge_dir
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._documents: list[tuple[str, str]] = []
        self._chunks: list[tuple[str, str]] = []
        self._index = None
        self._encoder = None

    def initialize(self) -> None:
        """Load docs and build FAISS index once."""
        if self._index is not None:
            return

        self._documents = self._load_documents()
        self._chunks = self._split_documents_into_chunks(self._documents)
        if not self._chunks:
            raise ValueError("No chunks found in knowledge base.")

        self._encoder = self._load_encoder()
        vectors = self._embed_texts([chunk for chunk, _source in self._chunks])
        self._index = self._build_faiss_index(vectors)

    def search(self, query: str, k: int = 3) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        self.initialize()
        assert self._index is not None

        query_vector = self._embed_texts([query])
        top_k = min(k, len(self._chunks))
        distances, indices = self._index.search(query_vector, top_k)

        results: list[RetrievedChunk] = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            text, source = self._chunks[idx]
            results.append(
                RetrievedChunk(
                    text=text,
                    source=source,
                    score=float(distance),
                )
            )
        return results

    def total_chunks_indexed(self) -> int:
        """
        Return how many text chunks are currently in the FAISS index.
        Helpful for debug endpoints and health checks.
        """
        self.initialize()
        return len(self._chunks)

    def _load_documents(self) -> list[tuple[str, str]]:
        if not self.knowledge_dir.is_dir():
            raise FileNotFoundError(f"Knowledge base folder not found: {self.knowledge_dir}")

        docs: list[tuple[str, str]] = []
        for path in sorted(self.knowledge_dir.glob("*.txt")):
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                docs.append((raw, path.name))
        if not docs:
            raise ValueError(f"No .txt files found in {self.knowledge_dir}")
        return docs

    def _split_documents_into_chunks(self, documents: list[tuple[str, str]]) -> list[tuple[str, str]]:
        chunks: list[tuple[str, str]] = []
        for text, source in documents:
            normalized = " ".join(text.split())
            start = 0
            text_len = len(normalized)
            while start < text_len:
                end = min(start + self.chunk_size, text_len)
                chunk = normalized[start:end].strip()
                if chunk:
                    chunks.append((chunk, source))
                if end >= text_len:
                    break
                start = max(0, end - self.chunk_overlap)
        return chunks

    def _load_encoder(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. Install with: pip install sentence-transformers"
            ) from exc
        return SentenceTransformer(self.model_name)

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        assert self._encoder is not None
        vectors = self._encoder.encode(texts, convert_to_numpy=True)
        vectors = np.asarray(vectors, dtype="float32")
        return vectors

    def _build_faiss_index(self, vectors: np.ndarray):
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("faiss-cpu is not installed. Install with: pip install faiss-cpu") from exc
        dimension = vectors.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(vectors)
        return index


_STORE: LocalVectorStore | None = None


def get_vector_store() -> LocalVectorStore:
    global _STORE
    if _STORE is None:
        _STORE = LocalVectorStore()
        _STORE.initialize()
    return _STORE


def retrieve_relevant_chunks(question: str, prover_answer: str, top_k: int = 3) -> list[RetrievedChunk]:
    """
    Search using combined query text (question + prover answer).
    This helps the auditor retrieve evidence connected to both.
    """
    combined = f"Question: {question.strip()}\nProver answer: {prover_answer.strip()}".strip()
    if not combined:
        return []
    store = get_vector_store()
    return store.search(combined, k=top_k)
