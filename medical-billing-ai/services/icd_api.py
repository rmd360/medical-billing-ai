"""
ICD-10 API — fetches diagnosis code descriptions from the NLM Clinical Tables API.
"""

import logging
import requests

logger = logging.getLogger(__name__)

ICD_API_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"
DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_MAX_RESULTS = 10


def fetch_icd_data(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> list[dict]:
    """
    Search for ICD-10-CM codes matching the query string.

    NLM API response format:
        [total_count, [codes], extra, [[code, description], ...]]

    Args:
        query:       ICD-10 code or search term (e.g. "J06.9", "diabetes")
        max_results: Max number of results to return

    Returns:
        List of dicts: [{"code": "J06.9", "description": "Acute URI"}, ...]
        Returns [] on error.
    """
    if not query or not query.strip():
        logger.warning("fetch_icd_data called with empty query")
        return []

    params = {"terms": query.strip(), "maxList": max_results}

    try:
        response = requests.get(ICD_API_URL, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # ✅ Fix: Correct API response parsing
        # data[1] → list of code strings e.g. ["J06.9", "J00"]
        # data[3] → list of [code, description] pairs e.g. [["J06.9", "Acute URI"], ...]
        codes = data[1] if len(data) > 1 else []
        descriptions_raw = data[3] if len(data) > 3 else []

        if not codes:
            logger.info(f"No ICD results found for query: {query!r}")
            return []

        structured = []
        for code, desc_pair in zip(codes, descriptions_raw):
            # desc_pair is [code, description] from the API
            description = (
                desc_pair[1]
                if isinstance(desc_pair, (list, tuple)) and len(desc_pair) > 1
                else str(desc_pair)
            )
            structured.append({"code": code, "description": description})

        logger.info(f"Fetched {len(structured)} ICD result(s) for query: {query!r}")
        return structured

    except requests.Timeout:
        logger.warning(f"ICD API timed out for query: {query!r}")
        return []
    except requests.HTTPError as e:
        logger.error(f"ICD API HTTP error: {e}")
        return []
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"ICD API response parsing error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching ICD data: {e}")
        return []