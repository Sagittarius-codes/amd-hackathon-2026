"""
captioner.py
============
Sends base64-encoded JPEG frames to the Fireworks API using a two-stage pipeline:
Stage 1: A vision model extracts a highly detailed scene description.
Stage 2: A fast text model generates 4 distinct caption styles (formal, sarcastic, 
humorous_tech, humorous_non_tech) based on the scene description.

Public API
----------
- get_all_captions(base64_image, timeout) -> dict[str, str]
    Returns a dict with keys: "formal", "sarcastic", "humorous_tech",
    "humorous_non_tech".

- get_caption(base64_image, style, timeout) -> str
    Backwards-compatible wrapper around get_all_captions().  Returns the
    caption for a single requested style (default: "formal").

Configuration (.env)
--------------------
  FIREWORKS_API_KEY=<your-key>   (required)

The .env file is located at the project root (one directory above this file).
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
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

CaptionStyle = Literal["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
CaptionDict = dict[str, str]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENV_PATH: Path = Path(__file__).resolve().parent.parent / ".env"
_API_URL: str = "https://api.fireworks.ai/inference/v1/chat/completions"

# Stage 1: Vision Model
_VISION_MODEL: str = "accounts/fireworks/models/minimax-m3"

# Stage 2: Fast Text Model
_TEXT_MODEL: str = "accounts/fireworks/models/llama-v3p1-8b-instruct"

_STAGE1_SYSTEM_PROMPT: str = (
    "You are an expert video analyst. Examine this video frame with extreme attention to detail. "
    "Describe everything you observe: the people present (their age, appearance, clothing, facial "
    "expressions, body language, actions), the environment (location, setting, objects, background), "
    "the lighting and mood, any visible text or signage, the camera angle and framing, and any "
    "notable details that convey context or story. Write at least 4-5 dense sentences. Be specific "
    "and precise — this description will be used to generate creative captions."
)

_STAGE2_SYSTEM_PROMPT: str = (
    "You are a creative caption writer. Given a detailed scene description, generate exactly 4 "
    "caption variants as a JSON object. Return ONLY valid JSON, no markdown, no explanation, "
    "no preamble. The JSON must have exactly these keys: \"formal\", \"sarcastic\", \"humorous_tech\", "
    "\"humorous_non_tech\".\n\n"
    "Style definitions:\n"
    "- formal: Professional, neutral, precise one sentence. Suitable for accessibility or documentation.\n"
    "- sarcastic: Dry, deadpan, ironic one sentence. Understated humor from tone, not obvious jokes.\n"
    "- humorous_tech: One funny sentence packed with developer/programming culture references "
    "(git, deployment, refactoring, null pointers, merge conflicts, stack traces, etc.)\n"
    "- humorous_non_tech: One funny relatable everyday sentence. Observational comedy a normal "
    "person would say while watching this video.\n\n"
    "Each caption must be exactly one sentence. Be creative and specific to the scene details provided."
)

_ALL_STYLES: tuple[str, ...] = (
    "formal",
    "sarcastic",
    "humorous_tech",
    "humorous_non_tech",
)

_PLACEHOLDER_NO_CAPTION: str = "[no caption]"
_APP_HEADERS: dict[str, str] = {}
_RATE_LIMIT_WAIT_SECONDS: int = 5

_cached_api_key: Optional[str] = None

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_api_key() -> str:
    global _cached_api_key

    if _cached_api_key is not None:
        return _cached_api_key

    key = os.environ.get("FIREWORKS_API_KEY", "").strip()

    if not key and _ENV_PATH.exists():
        load_dotenv(dotenv_path=_ENV_PATH, override=False)
        logger.debug("Loaded .env from '%s'", _ENV_PATH)
        key = os.environ.get("FIREWORKS_API_KEY", "").strip()

    if not key:
        raise ValueError(
            "FIREWORKS_API_KEY is not set or is empty. "
            "Set it as an environment variable (Railway Variables dashboard) "
            f"or add it to '{_ENV_PATH}' for local development."
        )

    _cached_api_key = key
    logger.debug("FIREWORKS_API_KEY loaded and cached successfully.")
    return _cached_api_key

def _post_with_retry(
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> requests.Response:
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

    model_name = payload.get("model", "unknown")
    logger.debug("POST %s | model=%s", _API_URL, model_name)
    response = _do_post()

    if response.status_code == 429:
        logger.warning(
            "Rate limit hit (HTTP 429). Waiting %ds before retrying...",
            _RATE_LIMIT_WAIT_SECONDS,
        )
        time.sleep(_RATE_LIMIT_WAIT_SECONDS)
        logger.debug("Retrying POST %s after rate-limit wait.", _API_URL)
        response = _do_post()

    response.raise_for_status()
    return response

def _fetch_vision_description(api_key: str, base64_image: str, timeout: float) -> str:
    logger.debug("Starting Stage 1: Vision analysis")
    
    data_uri = f"data:image/jpeg;base64,{base64_image}"
    payload: dict[str, Any] = {
        "model": _VISION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": _STAGE1_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image in detail.",
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

    try:
        response = _post_with_retry(api_key, payload, timeout)
    except Exception as exc:
        logger.error("[Stage 1] Fireworks API error: %s", exc)
        return ""

    try:
        response_json = response.json()
        content = response_json["choices"][0]["message"]["content"]
        # Strip reasoning blocks if any
        cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        logger.debug("[Stage 1] Description generated (%d chars)", len(cleaned))
        return cleaned
    except Exception as exc:
        logger.error("[Stage 1] Failed to parse Fireworks response: %s", exc)
        return ""

def _fetch_captions_json(api_key: str, description: str, timeout: float) -> CaptionDict:
    logger.debug("Starting Stage 2: JSON caption generation")
    
    user_message = f"Scene description: {description}\n\nGenerate the 4 caption variants as JSON."
    payload: dict[str, Any] = {
        "model": _TEXT_MODEL,
        # Llama 3.1 8B Instruct supports JSON mode if the prompt specifies it.
        # But Fireworks API might or might not enforce it with response_format.
        # It's usually safer to include it if supported, or omit if it crashes.
        # We'll include it.
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": _STAGE2_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
    }

    default_result: CaptionDict = {k: _PLACEHOLDER_NO_CAPTION for k in _ALL_STYLES}

    try:
        response = _post_with_retry(api_key, payload, timeout)
    except Exception as exc:
        logger.error("[Stage 2] Fireworks API error: %s", exc)
        return default_result

    try:
        response_json = response.json()
        content = response_json["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error("[Stage 2] Failed to parse Fireworks response: %s", exc)
        return default_result

    # Strip markdown code blocks
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        parsed = json.loads(content)
        # Ensure all keys exist
        result: CaptionDict = {}
        for style in _ALL_STYLES:
            val = parsed.get(style)
            result[style] = str(val).strip() if val else _PLACEHOLDER_NO_CAPTION
        
        logger.info("Stage 2 complete: 4 captions generated.")
        return result
    except json.JSONDecodeError as exc:
        logger.error("[Stage 2] JSON decoding failed: %s | Raw content: %s", exc, content)
        return default_result

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_captions(
    base64_image: str,
    timeout: float = 30.0,
) -> CaptionDict:
    """Generate captions in all four tonal styles for one video frame using a two-stage pipeline."""
    api_key = _load_api_key()

    logger.info("Executing 2-stage captioning pipeline...")

    # Stage 1: Vision Description
    description = _fetch_vision_description(api_key, base64_image, timeout)
    if not description:
        logger.warning("Stage 1 failed or returned empty. Returning placeholders.")
        return {k: _PLACEHOLDER_NO_CAPTION for k in _ALL_STYLES}

    # Sleep to avoid rate limiting
    logger.debug("Waiting 3s before Stage 2...")
    time.sleep(3)

    # Stage 2: Generate JSON Captions
    results = _fetch_captions_json(api_key, description, timeout)
    return results

def get_caption(
    base64_image: str,
    style: str = "formal",
    timeout: float = 30.0,
) -> str:
    """Return a caption for a single tonal style (backwards-compatible wrapper)."""
    if style not in _ALL_STYLES:
        raise ValueError(
            f"Unknown caption style '{style}'. "
            f"Valid styles are: {', '.join(_ALL_STYLES)}."
        )

    captions = get_all_captions(base64_image, timeout=timeout)
    return captions[style]
