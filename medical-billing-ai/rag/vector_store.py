"""
Vector Store — builds or retrieves a FAISS index for rule documents.
Falls back gracefully when OpenAI credentials are unavailable.
"""

import logging
import os
from functools import lru_cache

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


# ─── Fallback DB ──────────────────────────────────────────────────────────────

# ✅ Fix: Defined once at module level — not duplicated inside the function
class FallbackDB:
    """
    Simple in-memory store used when OpenAI embeddings are unavailable.
    Returns all documents for every query (no semantic ranking).
    """

    def __init__(self, docs: list[Document]):
        self.docs = docs

    def similarity_search(self, query: str, k: int = 5) -> list[Document]:
        logger.debug("FallbackDB: returning first %d documents (no embeddings)", k)
        return self.docs[:k]


# ─── Module-level cache ───────────────────────────────────────────────────────

_cached_db = None
_cached_docs_hash: int | None = None


def get_cached_store(documents: list[Document]):
    """
    Return a cached vector store, rebuilding only when documents change.

    ✅ Fix: Avoids rebuilding the FAISS index on every pipeline call.
    """
    global _cached_db, _cached_docs_hash

    # Use a hash of page contents to detect document changes
    docs_hash = hash(tuple(d.page_content for d in documents))

    if _cached_db is None or docs_hash != _cached_docs_hash:
        logger.info("Building new vector store (document set changed or first call)")
        _cached_db = build_vector_store(documents)
        _cached_docs_hash = docs_hash
    else:
        logger.debug("Reusing cached vector store")

    return _cached_db


# ─── Store builder ────────────────────────────────────────────────────────────

def build_vector_store(documents: list[Document]):
    """
    Create a FAISS vector store from the given documents.

    Uses OpenAI embeddings when OPENAI_API_KEY is set; otherwise
    falls back to FallbackDB (keyword retrieval only).

    Args:
        documents: LangChain Document objects to index

    Returns:
        FAISS instance or FallbackDB
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
        # Lazy import so the app still starts without these packages installed
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings()
        db = FAISS.from_documents(documents, embeddings)
        logger.info(f"FAISS index built with {len(documents)} document(s)")
        return db

    except ImportError as e:
        logger.error(f"Missing dependency for FAISS/OpenAI: {e}")
        return FallbackDB(documents)

    except Exception as e:
        logger.error(f"Failed to build FAISS index: {e} — falling back to FallbackDB")
        return FallbackDB(documents)