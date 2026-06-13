"""
Embedding Pipeline — converts raw API response dicts into LangChain Documents
with meaningful page_content for semantic similarity search.
"""

import logging
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def convert_to_documents(api_data: list, source: str = "medical_api") -> list[Document]:
    """
    Convert a list of API result dicts into LangChain Documents.

    Each dict is expected to have 'code' and 'description' keys.
    Unrecognised formats are converted with a fallback.

    Args:
        api_data: List of dicts from ICD or CPT APIs
        source:   Label used in document metadata (e.g. "icd_api", "cpt_api")

    Returns:
        List of LangChain Document objects
    """
    if not api_data:
        logger.debug(f"No data to convert for source={source}")
        return []

    documents = []
    for item in api_data:
        if isinstance(item, dict):
            code = item.get("code", "").strip()
            description = item.get("description", "").strip()

            # ✅ Fix: Build a semantically rich page_content string
            # so similarity search can match against human-readable text
            if code and description:
                page_content = f"Code: {code}\nDescription: {description}"
            elif code:
                page_content = f"Code: {code}"
            elif description:
                page_content = description
            else:
                logger.warning(f"Empty item skipped from {source}: {item}")
                continue

            metadata = {
                "source": source,
                "code": code,
            }
        else:
            # Fallback for non-dict items
            page_content = str(item)
            metadata = {"source": source, "code": ""}

        documents.append(Document(page_content=page_content, metadata=metadata))

    logger.debug(f"Converted {len(documents)} document(s) from source={source}")
    return documents