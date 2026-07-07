"""
captioner.py
============
Sends base64-encoded JPEG frames to the OpenRouter chat-completions API and
returns captions in four distinct tonal styles per frame.

Public API
----------
- get_all_captions(base64_image, timeout) -> dict[str, str]
    Returns a dict with keys: "formal", "sarcastic", "humorous_tech",
    "humorous_non_tech".  All four API calls are fired concurrently.

- get_caption(base64_image, style, timeout) -> str
    Backwards-compatible wrapper around get_all_captions().  Returns the
    caption for a single requested style (default: "formal").

Internal helpers
----------------
- _load_api_key()                     - loads & caches OPENROUTER_API_KEY from .env
- _build_payload(base64_image, style) - constructs the OpenRouter request body
- _parse_caption(response_json, style)- extracts the caption string from the response
- _fetch_caption(api_key, base64_image, style, timeout) - one full API round-trip
- _post_with_retry(api_key, payload, timeout)            - POST with 429 retry

Configuration (.env)
--------------------
  OPENROUTER_API_KEY=<your-key>   (required)

The .env file is located at the project root (one directory above this file).
"""

from __future__ import annotations

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal, Optional

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# The four supported caption style keys — used as TypedDict keys and as the
# literal type for the `style` parameter of get_caption().
CaptionStyle = Literal["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]

# The full return type of get_all_captions().
CaptionDict = dict[str, str]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Path to the project-root .env file, resolved relative to this source file.
_ENV_PATH: Path = Path(__file__).resolve().parent.parent / ".env"

# OpenRouter chat-completions endpoint (OpenAI-compatible).
_API_URL: str = "https://api.fireworks.ai/inference/v1/chat/completions"

# Vision-capable model used for all caption styles.
# Gemma 4 26B A4B (MoE): ~4B active params, fast inference, non-reasoning,
# supports inline base64 image_url content.
_MODEL: str = "accounts/fireworks/models/minimax-m3"

# Base user prompt appended to every request regardless of style.
# The system prompt shapes *how* the model answers; this says *what* to answer.
_USER_PROMPT: str = (
    "Describe what is happening in this video frame in one concise sentence."
)

# Per-style system prompts.  Each is injected as a "system" role message so
# the model understands the tonal persona before seeing the image.
_SYSTEM_PROMPTS: dict[str, str] = {
    "formal": (
        "You are a professional video analyst. "
        "Describe each video frame in a single, precise, neutral sentence. "
        "Use formal language with no slang, humour, or editorialising."
    ),
    "sarcastic": (
        "You are a deadpan, dry-witted commentator who finds everything "
        "mildly absurd. Describe each video frame in exactly one ironic, "
        "understated sentence. Never use exclamation marks or obvious jokes — "
        "the humour must come entirely from tone."
    ),
    "humorous_tech": (
        "You are a software engineer with a very online sense of humour. "
        "Describe each video frame in exactly one funny sentence packed with "
        "developer jargon, tech metaphors, or programming culture references "
        "(e.g. refactoring, merge conflicts, null pointers, infinite loops). "
        "Keep it witty and technically flavoured."
    ),
    "humorous_non_tech": (
        "You are a relatable everyday person describing things to a friend. "
        "Describe each video frame in exactly one funny sentence using "
        "ordinary, down-to-earth language — no jargon. "
        "Think observational comedy: what a normal person would say out loud "
        "while watching this video."
    ),
}

# All valid style keys in the order they are processed.
_ALL_STYLES: tuple[str, ...] = (
    "formal",
    "sarcastic",
    "humorous_tech",
    "humorous_non_tech",
)

# Placeholder written to the dict when a style's API call fails or returns
# an empty/malformed response.
_PLACEHOLDER_NO_CAPTION: str = "[no caption]"

# Headers that identify this application to OpenRouter.
_APP_HEADERS: dict[str, str] = {}


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
    """Load and cache ``OPENROUTER_API_KEY`` from the environment or ``.env``.

    Resolution order (first hit wins):
    1. Already-set environment variable (e.g. injected by Railway / Docker).
    2. ``.env`` file at the project root (local development).

    The key is cached after the first resolution so disk is read at most once.

    Returns
    -------
    str
        The non-empty API key string.

    Raises
    ------
    ValueError
        If ``OPENROUTER_API_KEY`` is absent or empty in both the environment
        and the ``.env`` file.
    """
    global _cached_api_key

    if _cached_api_key is not None:
        return _cached_api_key

    # 1. Try the environment directly (Railway / Docker inject it here).
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    # 2. Fall back to .env file for local development.
    if not key and _ENV_PATH.exists():
        # override=False so an already-set variable is never clobbered.
        load_dotenv(dotenv_path=_ENV_PATH, override=False)
        logger.debug("Loaded .env from '%s'", _ENV_PATH)
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    if not key:
        raise ValueError(
            "OPENROUTER_API_KEY is not set or is empty. "
            "Set it as an environment variable (Railway Variables dashboard) "
            f"or add it to '{_ENV_PATH}' for local development."
        )

    _cached_api_key = key
    logger.debug("OPENROUTER_API_KEY loaded and cached successfully.")
    return _cached_api_key


def _build_payload(base64_image: str, style: str) -> dict[str, Any]:
    """Construct the OpenRouter chat-completions request body for one style.

    The payload follows the OpenAI multimodal message format:

    * A ``"system"`` role message carries the per-style tonal instruction.
    * A ``"user"`` role message carries the fixed task prompt and the inline
      base64 JPEG image.

    Parameters
    ----------
    base64_image:
        Plain base64 string (no ``data:image/jpeg;base64,`` prefix).
        The data URI prefix is added internally here.
    style:
        One of the keys in ``_SYSTEM_PROMPTS``.  Determines which system
        prompt is injected.

    Returns
    -------
    dict[str, Any]
        JSON-serialisable request body ready to pass to
        :func:`requests.post`.

    Raises
    ------
    KeyError
        If *style* is not a recognised key in ``_SYSTEM_PROMPTS``.
    """
    system_prompt = _SYSTEM_PROMPTS[style]  # KeyError is intentional — bad style = bug
    data_uri = f"data:image/jpeg;base64,{base64_image}"

    payload: dict[str, Any] = {
        "model": _MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _USER_PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_uri,
                        },
                    },
                ],
            },
        ],
    }

    return payload


def _parse_caption(response_json: dict[str, Any], style: str) -> str:
    """Extract the caption text from an OpenRouter response JSON.

    Navigates ``choices[0].message.content``.  If any expected key is absent
    or the value is empty, logs a warning and returns an empty string — so a
    single malformed response never crashes the entire pipeline.

    Parameters
    ----------
    response_json:
        Parsed JSON body returned by the OpenRouter API.
    style:
        The style this response belongs to, used only for logging context.

    Returns
    -------
    str
        The caption string, or ``""`` if the response is malformed / empty.
    """
    try:
        choices = response_json["choices"]
    except KeyError:
        logger.warning(
            "[%s] Malformed API response: 'choices' key missing. "
            "Raw response: %s",
            style,
            response_json,
        )
        return ""

    if not choices:
        logger.warning(
            "[%s] Malformed API response: 'choices' list is empty. "
            "Raw response: %s",
            style,
            response_json,
        )
        return ""

    try:
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.warning(
            "[%s] Malformed API response: could not navigate "
            "choices[0].message.content (%s). Raw response: %s",
            style,
            exc,
            response_json,
        )
        return ""

    if not isinstance(content, str) or not content.strip():
        logger.warning(
            "[%s] Malformed API response: content is empty or not a string. "
            "Raw response: %s",
            style,
            response_json,
        )
        return ""

    # ------------------------------------------------------------------
    # Strip reasoning-model <think>...</think> blocks (fix X3).
    # Some models (e.g. reasoning variants) prefix their answer with an
    # internal chain-of-thought block.  We remove it so only the final
    # one-sentence caption reaches the caller.
    # The DOTALL flag is required because the block spans multiple lines.
    # ------------------------------------------------------------------
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if not cleaned:
        logger.warning(
            "[%s] Caption was empty after stripping <think> block — "
            "substituting placeholder.",
            style,
        )
        return ""

    return cleaned


def _post_with_retry(
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> requests.Response:
    """Send a POST request to the OpenRouter endpoint, retrying once on 429.

    Parameters
    ----------
    api_key:
        Bearer token for the Authorization header.
    payload:
        JSON-serialisable request body (from :func:`_build_payload`).
    timeout:
        Seconds before the request is aborted.  Applied separately to the
        TCP connect phase and the response-read phase.

    Returns
    -------
    requests.Response
        The HTTP response object with a successful (2xx) status code.

    Raises
    ------
    requests.HTTPError
        For any non-2xx status.  On HTTP 429, one retry is attempted after
        waiting ``_RATE_LIMIT_WAIT_SECONDS``; if the retry also fails,
        the exception is re-raised.
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

    # Raises requests.HTTPError for all remaining 4xx and 5xx responses.
    response.raise_for_status()
    return response


def _fetch_caption(
    api_key: str,
    base64_image: str,
    style: str,
    timeout: float,
) -> str:
    """Perform one complete API round-trip for a single caption style.

    This is the unit of work dispatched to each thread inside
    :func:`get_all_captions`.  It encapsulates building the payload, posting
    with retry, and parsing the response — all in one place.

    Parameters
    ----------
    api_key:
        Bearer token already resolved by :func:`_load_api_key`.
    base64_image:
        Plain base64 string (no data URI prefix).
    style:
        One of the keys in ``_SYSTEM_PROMPTS``.
    timeout:
        Per-request timeout in seconds, passed through to
        :func:`_post_with_retry`.

    Returns
    -------
    str
        The caption string, or ``_PLACEHOLDER_NO_CAPTION`` if the call fails
        or the response is malformed.  Never raises — all exceptions are caught
        and logged so one failing style does not abort the others.
    """
    logger.debug("Starting caption fetch | style='%s'", style)

    try:
        payload = _build_payload(base64_image, style)
        response = _post_with_retry(api_key, payload, timeout)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "N/A"
        logger.error(
            "[%s] OpenRouter returned HTTP %s: %s",
            style,
            status,
            exc,
        )
        return _PLACEHOLDER_NO_CAPTION
    except requests.Timeout:
        logger.error(
            "[%s] Request timed out after %.1fs.",
            style,
            timeout,
        )
        return _PLACEHOLDER_NO_CAPTION
    except requests.ConnectionError as exc:
        logger.error(
            "[%s] Network error: %s",
            style,
            exc,
        )
        return _PLACEHOLDER_NO_CAPTION
    except Exception as exc:  # noqa: BLE001 — broad catch by design
        logger.error(
            "[%s] Unexpected error during API call: %s",
            style,
            exc,
        )
        return _PLACEHOLDER_NO_CAPTION

    # ------------------------------------------------------------------
    # Parse the response JSON.
    # ------------------------------------------------------------------
    try:
        response_json: dict[str, Any] = response.json()
    except ValueError as exc:
        logger.warning(
            "[%s] Could not parse API response as JSON: %s. Raw body: %s",
            style,
            exc,
            response.text[:500],
        )
        return _PLACEHOLDER_NO_CAPTION

    caption = _parse_caption(response_json, style)

    if caption:
        logger.info(
            "[%s] Caption generated successfully (%d chars).",
            style,
            len(caption),
        )
        logger.debug("[%s] Caption: %s", style, caption)
    else:
        logger.warning(
            "[%s] API returned an empty or malformed caption — "
            "substituting placeholder.",
            style,
        )
        return _PLACEHOLDER_NO_CAPTION

    return caption


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_all_captions(
    base64_image: str,
    timeout: float = 30.0,
) -> CaptionDict:
    """Generate captions in all four tonal styles for one video frame.

    Fires four concurrent API calls — one per style — using a
    :class:`~concurrent.futures.ThreadPoolExecutor` with four workers.
    Each call is fully independent; a failure in one style returns the
    ``"[no caption]"`` placeholder for that key and does not affect the others.

    The four styles and their tonal instructions are:

    * **formal** — professional, neutral, precise one sentence.
    * **sarcastic** — dry, ironic, deadpan one sentence.
    * **humorous_tech** — funny using developer / technical jargon.
    * **humorous_non_tech** — funny using everyday relatable language.

    Parameters
    ----------
    base64_image:
        Plain base64 string representing a JPEG image.  Must **not** include
        the ``data:image/jpeg;base64,`` prefix; that is added internally.
    timeout:
        Seconds to wait for each individual API response before aborting.
        Applied independently to both the TCP connect and response-read phases.
        Defaults to ``30.0``.

    Returns
    -------
    dict[str, str]
        Always contains exactly the four keys ``"formal"``, ``"sarcastic"``,
        ``"humorous_tech"``, ``"humorous_non_tech"``.  Values are caption
        strings or ``"[no caption]"`` on failure.

    Raises
    ------
    ValueError
        If ``OPENROUTER_API_KEY`` is missing from ``.env`` or is empty.

    Examples
    --------
    >>> captions = get_all_captions(some_base64_string)
    >>> captions["formal"]
    'A technician inspects a server rack in a data centre.'
    >>> captions["sarcastic"]
    'Apparently someone decided this required an in-person visit.'
    >>> captions["humorous_tech"]
    'Production is down and he is trying to git blame the hardware.'
    >>> captions["humorous_non_tech"]
    'Me checking if I actually unplugged it after saying I did.'
    """
    # ------------------------------------------------------------------
    # Resolve the API key once; ValueError propagates immediately so the
    # caller knows before any threads are launched.
    # ------------------------------------------------------------------
    api_key = _load_api_key()

    logger.info(
        "Fetching %d caption styles concurrently | timeout=%.1fs | model=%s",
        len(_ALL_STYLES),
        timeout,
        _MODEL,
    )

    results: CaptionDict = {}

    # ------------------------------------------------------------------
    # Dispatch one thread per style.  max_workers=4 because there are
    # exactly 4 styles — all fire in parallel, no queuing.
    # ------------------------------------------------------------------
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Map each Future back to its style name so we can label results.
        future_to_style = {
            executor.submit(_fetch_caption, api_key, base64_image, style, timeout): style
            for style in _ALL_STYLES
        }

        for future in as_completed(future_to_style):
            style = future_to_style[future]
            try:
                caption = future.result()
            except Exception as exc:  # noqa: BLE001 — safety net
                # _fetch_caption() is designed never to raise, but guard
                # against unforeseen exceptions from the executor itself.
                logger.error(
                    "[%s] Unhandled exception in worker thread: %s", style, exc
                )
                caption = _PLACEHOLDER_NO_CAPTION

            results[style] = caption

    # ------------------------------------------------------------------
    # Guarantee all four keys are present even if a future was somehow
    # skipped (defensive programming).
    # ------------------------------------------------------------------
    for style in _ALL_STYLES:
        results.setdefault(style, _PLACEHOLDER_NO_CAPTION)

    logger.info(
        "All caption styles complete. Successful: %d / %d.",
        sum(1 for v in results.values() if v != _PLACEHOLDER_NO_CAPTION),
        len(_ALL_STYLES),
    )

    return results


def get_caption(
    base64_image: str,
    style: str = "formal",
    timeout: float = 30.0,
) -> str:
    """Return a caption for a single tonal style (backwards-compatible wrapper).

    Calls :func:`get_all_captions` internally, which fires all four API calls
    concurrently.  Use this function when you only need one style and want a
    plain string back; use :func:`get_all_captions` directly when you need all
    four styles.

    Parameters
    ----------
    base64_image:
        Plain base64 string representing a JPEG image.  Must **not** include
        the ``data:image/jpeg;base64,`` prefix.
    style:
        Which caption style to return.  Must be one of:
        ``"formal"``, ``"sarcastic"``, ``"humorous_tech"``,
        ``"humorous_non_tech"``.  Defaults to ``"formal"``.
    timeout:
        Seconds to wait for each API response before aborting.
        Defaults to ``30.0``.

    Returns
    -------
    str
        The caption string for the requested *style*, or ``"[no caption]"``
        if that style's API call failed or returned a malformed response.

    Raises
    ------
    ValueError
        If *style* is not one of the four valid style keys, or if
        ``OPENROUTER_API_KEY`` is missing from ``.env``.

    Examples
    --------
    >>> # Default style (formal) — drop-in replacement for the old get_caption()
    >>> caption = get_caption(some_base64_string)
    >>> print(caption)
    'A technician inspects a server rack in a data centre.'

    >>> # Fetch a specific style
    >>> caption = get_caption(some_base64_string, style="humorous_tech")
    >>> print(caption)
    'Production is down and he is trying to git blame the hardware.'
    """
    if style not in _ALL_STYLES:
        raise ValueError(
            f"Unknown caption style '{style}'. "
            f"Valid styles are: {', '.join(_ALL_STYLES)}."
        )

    captions = get_all_captions(base64_image, timeout=timeout)
    return captions[style]
