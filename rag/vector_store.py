"""
Vector Store — builds or retrieves a FAISS index for rule documents.
Falls back gracefully when OpenAI credentials are unavailable.
"""

import logging
import os
from typing import Any

import faiss
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class FallbackDB:
    """
    Simple in-memory store used when OpenAI embeddings are unavailable.
    Returns the first k documents for every query.
    """

    def __init__(self, docs: list):
        self.docs = docs

    def similarity_search(self, query: str, k: int = 5) -> list:
        logger.debug("FallbackDB: returning first %d documents (no embeddings)", k)
        return self.docs[:k]


class OpenAIEmbeddings:
    """OpenAI embedding wrapper for custom FAISS index."""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.client = OpenAI()
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding


class FaissDB:
    """Custom FAISS-backed vector store for SimpleDocument search."""

    def __init__(self, documents: list, index: Any, dims: int, embedder: OpenAIEmbeddings):
        self.documents = documents
        self.index = index
        self.dims = dims
        self.embedder = embedder

    @classmethod
    def from_documents(cls, documents: list, embedder: OpenAIEmbeddings):
        texts = [doc.page_content for doc in documents]
        vectors = embedder.embed_documents(texts)
        if not vectors:
            raise ValueError("No embeddings produced for documents")

        matrix = np.array(vectors, dtype=np.float32)
        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return cls(documents=documents, index=index, dims=matrix.shape[1], embedder=embedder)

    def similarity_search(self, query: str, k: int = 5) -> list:
        query_vector = self.embedder.embed_query(query)
        qvec = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(qvec)
        _, indices = self.index.search(qvec, k)
        return [self.documents[idx] for idx in indices[0] if idx != -1]


def build_vector_store(documents: list):
    """
    Create a FAISS vector store from the given documents.

    Uses OpenAI embeddings when OPENAI_API_KEY is set; otherwise falls back to FallbackDB.
    """
    if not documents:
        logger.warning("build_vector_store called with empty document list")
        return FallbackDB([])

    if not os.getenv("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY not set — using FallbackDB. "
            "Set the key in .env for full semantic search."
        )
        return FallbackDB(documents)

    try:
        embeddings = OpenAIEmbeddings()
        db = FaissDB.from_documents(documents, embeddings)
        logger.info(f"FAISS index built with {len(documents)} document(s)")
        return db
    except Exception as e:
        logger.error(f"Failed to build FAISS index: {e} — falling back to FallbackDB")
        return FallbackDB(documents)


_cached_store = None
_cached_signature = None


def _document_signature(documents: list) -> tuple:
    return tuple(
        (doc.page_content, tuple(sorted(doc.metadata.items())))
        for doc in documents
    )


def get_cached_store(documents: list):
    """Return a cached store when the same documents are requested again."""
    global _cached_store, _cached_signature
    signature = _document_signature(documents)
    if _cached_store is not None and signature == _cached_signature:
        logger.debug("Reusing cached vector store")
        return _cached_store

    _cached_store = build_vector_store(documents)
    _cached_signature = signature
    return _cached_store