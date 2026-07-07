"""
captioner.py
============
Sends base64-encoded JPEG frames to the Fireworks API using a single-stage multimodal pipeline.
A single vision model (minimax-m3) is prompted to analyze the scene and directly output 
4 distinct caption styles (formal, sarcastic, humorous_tech, humorous_non_tech) in JSON format.

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

# Vision Model
_VISION_MODEL: str = "accounts/fireworks/models/minimax-m3"

_SYSTEM_PROMPT: str = (
    "You are an expert video caption writer. Analyze the provided video frame image carefully.\n"
    "Examine everything: people present (appearance, expressions, body language, clothing, actions),\n"
    "the environment (location, setting, objects, background), lighting, mood, any visible text,\n"
    "camera angle and composition.\n\n"
    "Then generate exactly 4 caption styles based on your analysis. Return ONLY a valid JSON object\n"
    "with no markdown, no backticks, no explanation. The JSON must have exactly these 4 keys:\n\n"
    '"formal": Professional, neutral, precise one sentence suitable for accessibility or documentation.\n'
    '"sarcastic": Dry, deadpan, ironic one sentence. Understated humor from tone only.\n'
    '"humorous_tech": One funny sentence with developer/programming culture references (git, deployments, null pointers, merge conflicts, stack traces, refactoring, etc.)\n'
    '"humorous_non_tech": One funny relatable everyday sentence. Observational comedy a normal person would say watching this video.\n\n'
    "Each value must be exactly one sentence. Be specific and creative based on what you actually see.\n"
    "Return only the JSON object, nothing else."
)

_USER_PROMPT: str = "Analyze this video frame and generate the 4 captions as JSON."

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

def _fetch_captions_json(api_key: str, base64_image: str, timeout: float) -> CaptionDict:
    logger.debug("Starting single-stage multimodal caption generation")
    
    data_uri = f"data:image/jpeg;base64,{base64_image}"
    payload: dict[str, Any] = {
        "model": _VISION_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": _SYSTEM_PROMPT,
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

    default_result: CaptionDict = {k: _PLACEHOLDER_NO_CAPTION for k in _ALL_STYLES}

    try:
        response = _post_with_retry(api_key, payload, timeout)
    except Exception as exc:
        logger.error("Fireworks API error: %s", exc)
        return default_result

    try:
        response_json = response.json()
        content = response_json["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.error("Failed to parse Fireworks response structure: %s", exc)
        return default_result

    # Strip reasoning blocks if any
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    # Strip markdown code blocks
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
        
        logger.info("4 captions generated successfully.")
        return result
    except json.JSONDecodeError as exc:
        logger.error("JSON decoding failed: %s | Raw content: %s", exc, content)
        return default_result

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_captions(
    base64_image: str,
    timeout: float = 30.0,
) -> CaptionDict:
    """Generate captions in all four tonal styles for one video frame using a single-stage pipeline."""
    api_key = _load_api_key()

    logger.info("Executing single-stage captioning pipeline...")
    logger.info("Using VISION_MODEL: '%s'", _VISION_MODEL)

    results = _fetch_captions_json(api_key, base64_image, timeout)
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
