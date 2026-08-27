"""CPT Code Lookup — returns procedure descriptions from a remote API."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

CPT_API_URL = os.getenv("CPT_API_URL")
DEFAULT_TIMEOUT = 5


def fetch_cpt_code(code: str) -> list[dict]:
    """
    Look up a CPT procedure code description.

    Args:
        code: 5-digit CPT code string (e.g. "99213")

    Returns:
        List with a single dict: [{"code": ..., "description": ...}]
        Returns [] when the code is unavailable or the request fails.
    """
    if not code or not code.strip():
        logger.warning("fetch_cpt_code called with empty code")
        return []

    code = code.strip().upper()
    if not CPT_API_URL:
        logger.warning("CPT_API_URL is not configured")
        return []

    try:
        response = requests.get(
            CPT_API_URL,
            params={"terms": code, "maxList": 10},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        results = data[3] if len(data) > 3 and isinstance(data[3], list) else []

        for result in results:
            if not isinstance(result, (list, tuple)) or len(result) < 2:
                continue
            result_code, description = str(result[0]).upper(), str(result[1]).strip()
            if result_code == code and description:
                logger.info(f"CPT code {code} found via remote lookup")
                return [{"code": code, "description": description}]

        logger.warning(f"CPT code {code} was not found by remote lookup")
        return []
    except requests.Timeout:
        logger.warning(f"CPT API timed out for code: {code}")
        return []
    except requests.HTTPError as error:
        logger.error(f"CPT API HTTP error: {error}")
        return []
    except (ValueError, TypeError, IndexError) as error:
        logger.error(f"CPT API response parsing error: {error}")
        return []
    except requests.RequestException as error:
        logger.error(f"CPT API request failed: {error}")
        return []