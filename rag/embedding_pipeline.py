"""
Embedding Pipeline — converts raw API response dicts into simple document objects
with meaningful page_content for semantic similarity search.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SimpleDocument:
    page_content: str
    metadata: dict


def convert_to_documents(api_data: list, source: str = "medical_api") -> list[SimpleDocument]:
    """
    Convert a list of API result dicts into simple documents for indexing.

    Each dict is expected to have 'code' and 'description' keys.
    Unrecognised formats are converted with a fallback.

    Args:
        api_data: List of dicts from ICD or CPT APIs
        source:   Label used in document metadata (e.g. "icd_api", "cpt_api")

    Returns:
        List of SimpleDocument objects
    """
    if not api_data:
        logger.debug(f"No data to convert for source={source}")
        return []

    documents = []
    for item in api_data:
        if isinstance(item, dict):
            code = item.get("code", "").strip()
            description = item.get("description", "").strip()

            if code and description:
                page_content = f"Code: {code}\nDescription: {description}"
            elif code:
                page_content = f"Code: {code}"
            elif description:
                page_content = description
            else:
                logger.warning(f"Empty item skipped from {source}: {item}")
                continue

            metadata = {"source": source, "code": code}
        else:
            page_content = str(item)
            metadata = {"source": source, "code": ""}

        documents.append(SimpleDocument(page_content=page_content, metadata=metadata))

    logger.debug(f"Converted {len(documents)} document(s) from source={source}")
    return documents