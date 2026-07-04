"""
captioner.py
============
Sends base64-encoded JPEG frames to the OpenRouter chat-completions API and
returns a one-sentence natural-language caption for each frame.

Public API
----------
- get_caption(base64_image, timeout) -> str

Internal helpers
----------------
- _load_api_key()         - loads & caches OPENROUTER_API_KEY from .env
- _build_payload(base64_image) - constructs the OpenRouter request body
- _parse_caption(response_json) - extracts the caption string from the response

Configuration (.env)
--------------------
  OPENROUTER_API_KEY=<your-key>   (required)

The .env file is located at the project root (one directory above this file).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv
import os

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Path to the project-root .env file, resolved relative to this source file.
_ENV_PATH: Path = Path(__file__).resolve().parent.parent / ".env"

# OpenRouter chat-completions endpoint.
_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"

# Vision-capable free model available on OpenRouter.
_MODEL: str = "google/gemma-4-31b-it:free"

# Prompt sent alongside every frame image.
_PROMPT: str = (
    "Describe what is happening in this video frame in one concise sentence."
)

# Headers that identify this application to OpenRouter.
# OpenRouter recommends these for traffic analytics and abuse prevention.
_APP_HEADERS: dict[str, str] = {
    "X-Title": "Video Captioner",
    "HTTP-Referer": "https://github.com/amd-hackathon-2026",
}

# How many seconds to wait after receiving a 429 before the single retry.
_RATE_LIMIT_WAIT_SECONDS: int = 5

# ---------------------------------------------------------------------------
# Module-level API key cache
# ---------------------------------------------------------------------------

# Populated on first call to _load_api_key(); None means not yet loaded.
_cached_api_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_api_key() -> str:
    """Load and cache ``OPENROUTER_API_KEY`` from the project-root ``.env`` file.

    The key is resolved once and stored in the module-level ``_cached_api_key``
    variable.  Subsequent calls return the cached value without re-reading disk.

    Returns
    -------
    str
        The non-empty API key string.

    Raises
    ------
    ValueError
        If the ``.env`` file does not exist, or if ``OPENROUTER_API_KEY`` is
        absent or empty.
    """
    global _cached_api_key

    if _cached_api_key is not None:
        return _cached_api_key

    if not _ENV_PATH.exists():
        raise ValueError(
            f".env file not found at '{_ENV_PATH}'. "
            "Create it and set OPENROUTER_API_KEY=<your-key>."
        )

    # override=False so an already-set env-var is not clobbered.
    load_dotenv(dotenv_path=_ENV_PATH, override=False)
    logger.debug("Loaded .env from '%s'", _ENV_PATH)

    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "OPENROUTER_API_KEY is not set or is empty. "
            f"Add it to '{_ENV_PATH}'."
        )

    _cached_api_key = key
    logger.debug("OPENROUTER_API_KEY loaded and cached successfully.")
    return _cached_api_key


def _build_payload(base64_image: str) -> dict[str, Any]:
    """Construct the OpenRouter chat-completions request body.

    The image is sent as a multimodal message containing a text prompt and an
    inline base64 JPEG image using the OpenAI vision message format that
    OpenRouter accepts.

    Parameters
    ----------
    base64_image:
        Plain base64 string (no ``data:image/jpeg;base64,`` prefix).
        The data URI prefix is added internally here.

    Returns
    -------
    dict[str, Any]
        JSON-serialisable request body ready to pass to
        :func:`requests.post`.
    """
    data_uri = f"data:image/jpeg;base64,{base64_image}"

    payload: dict[str, Any] = {
        "model": _MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_uri,
                        },
                    },
                ],
            }
        ],
    }

    return payload


def _parse_caption(response_json: dict[str, Any]) -> str:
    """Extract the caption text from the OpenRouter response JSON.

    Navigates ``choices[0].message.content``.  If any expected key is absent
    or the value is empty, logs a warning and returns an empty string instead
    of raising — so the pipeline can continue with the remaining frames.

    Parameters
    ----------
    response_json:
        Parsed JSON body returned by the OpenRouter API.

    Returns
    -------
    str
        The caption string, or ``""`` if the response is malformed / empty.
    """
    try:
        choices = response_json["choices"]
    except KeyError:
        logger.warning(
            "Malformed API response: 'choices' key missing. Raw response: %s",
            response_json,
        )
        return ""

    if not choices:
        logger.warning(
            "Malformed API response: 'choices' list is empty. Raw response: %s",
            response_json,
        )
        return ""

    try:
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.warning(
            "Malformed API response: could not navigate choices[0].message.content "
            "(%s). Raw response: %s",
            exc,
            response_json,
        )
        return ""

    if not isinstance(content, str) or not content.strip():
        logger.warning(
            "Malformed API response: content is empty or not a string. "
            "Raw response: %s",
            response_json,
        )
        return ""

    return content.strip()


def _post_with_retry(
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> requests.Response:
    """Send the POST request to OpenRouter, retrying once on HTTP 429.

    Parameters
    ----------
    api_key:
        Bearer token for the Authorization header.
    payload:
        JSON-serialisable request body (from :func:`_build_payload`).
    timeout:
        Seconds before the request is aborted.  Applied separately to the
        connect phase and the read phase (i.e. ``timeout=(timeout, timeout)``).

    Returns
    -------
    requests.Response
        The HTTP response object with a successful (2xx) status code.

    Raises
    ------
    requests.HTTPError
        For any non-2xx status.  On 429, one retry is attempted after waiting
        ``_RATE_LIMIT_WAIT_SECONDS``; if the retry also returns 429 (or any
        other error), the exception is re-raised.
    requests.Timeout
        If the server does not respond within *timeout* seconds.
    requests.ConnectionError
        If a network-level error occurs.
    """
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **_APP_HEADERS,
    }

    def _do_post() -> requests.Response:
        return requests.post(
            _API_URL,
            json=payload,
            headers=headers,
            timeout=(timeout, timeout),
        )

    logger.debug("POST %s | model=%s", _API_URL, _MODEL)
    response = _do_post()

    if response.status_code == 429:
        logger.warning(
            "Rate limit hit (HTTP 429). Waiting %ds before retrying...",
            _RATE_LIMIT_WAIT_SECONDS,
        )
        time.sleep(_RATE_LIMIT_WAIT_SECONDS)
        logger.debug("Retrying POST %s after rate-limit wait.", _API_URL)
        response = _do_post()

    # Raises requests.HTTPError for 4xx and 5xx responses.
    response.raise_for_status()
    return response


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_caption(
    base64_image: str,
    timeout: float = 30.0,
) -> str:
    """Send a base64-encoded JPEG frame to OpenRouter and return a caption.

    The frame is sent to the ``google/gemini-flash-1.5`` model with the prompt:

        *"Describe what is happening in this video frame in one concise sentence."*

    **Rate limiting**: if the API responds with HTTP 429, the function waits
    ``5`` seconds and retries exactly once.  If the retry also fails,
    :class:`requests.HTTPError` is raised so the caller can decide how to
    proceed.

    **Malformed responses**: if the response JSON is missing expected keys or
    contains an empty caption, a warning is logged and an empty string ``""``
    is returned — the pipeline is not interrupted.

    **API key**: loaded from the project-root ``.env`` file on first call and
    cached in memory for all subsequent calls.  The expected variable name is
    ``OPENROUTER_API_KEY``.

    Parameters
    ----------
    base64_image:
        Plain base64 string representing a JPEG image.  Must **not** include
        the ``data:image/jpeg;base64,`` prefix; that is added internally when
        building the API payload.
    timeout:
        Seconds to wait for a server response before aborting.  Applied
        independently to both the TCP connect phase and the response-read
        phase.  Defaults to ``30.0``.

    Returns
    -------
    str
        The caption string extracted from the API response, or ``""`` if the
        response was malformed or the caption was empty.

    Raises
    ------
    ValueError
        If ``OPENROUTER_API_KEY`` is missing from ``.env`` or is empty.
    requests.HTTPError
        For HTTP 4xx/5xx errors, including a persisting 429 after one retry.
    requests.Timeout
        If the API does not respond within *timeout* seconds.
    requests.ConnectionError
        If a network-level connection failure occurs.

    Examples
    --------
    >>> caption = get_caption(some_base64_string)
    >>> print(caption)
    'A person walks across a crosswalk while looking at their phone.'

    >>> # Custom timeout for slow network conditions
    >>> caption = get_caption(some_base64_string, timeout=60.0)
    """
    # ------------------------------------------------------------------
    # 1. Resolve the API key (raises ValueError if missing).
    # ------------------------------------------------------------------
    api_key = _load_api_key()

    # ------------------------------------------------------------------
    # 2. Build the request payload.
    # ------------------------------------------------------------------
    payload = _build_payload(base64_image)

    # ------------------------------------------------------------------
    # 3. Send the request (with rate-limit retry logic).
    # ------------------------------------------------------------------
    try:
        response = _post_with_retry(api_key, payload, timeout)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "N/A"
        logger.error(
            "OpenRouter API returned HTTP %s. Error: %s",
            status,
            exc,
        )
        raise
    except requests.Timeout:
        logger.error(
            "Request to OpenRouter timed out after %.1fs.", timeout
        )
        raise
    except requests.ConnectionError as exc:
        logger.error(
            "Network error while connecting to OpenRouter: %s", exc
        )
        raise

    # ------------------------------------------------------------------
    # 4. Parse the caption from the response.
    # ------------------------------------------------------------------
    try:
        response_json: dict[str, Any] = response.json()
    except ValueError as exc:
        logger.warning(
            "Could not parse OpenRouter response as JSON: %s. "
            "Raw body: %s",
            exc,
            response.text[:500],
        )
        return ""

    caption = _parse_caption(response_json)

    if caption:
        logger.info("Caption generated successfully (%d chars).", len(caption))
        logger.debug("Caption: %s", caption)
    else:
        logger.warning("get_caption() returned an empty string for this frame.")

    return caption
