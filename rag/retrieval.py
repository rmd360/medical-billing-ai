"""
RAG Retrieval — performs similarity search on the vector store.
"""

import logging

logger = logging.getLogger(__name__)


def retrieve_rules(db, query: str, k: int = 5) -> list:
    """
    Retrieve the top-k most relevant rule documents for a query.

    Args:
        db:    FAISS or FallbackDB instance
        query: Search query string (usually a stringified billing record)
        k:     Number of results to return (default 5)

    Returns:
        List of LangChain Document objects, or [] on failure
    """
    # ✅ Fix: Guard against empty queries
    if not query or not query.strip():
        logger.warning("retrieve_rules called with empty query — returning []")
        return []

    try:
        results = db.similarity_search(query, k=k)
        logger.debug(f"Retrieved {len(results)} rule document(s) for query")
        return results

    except Exception as e:
        logger.error(f"Similarity search failed: {e}")
        return []