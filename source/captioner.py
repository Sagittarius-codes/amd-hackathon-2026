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

_SYSTEM_PROMPT: str = """You are an elite video caption writer and visual analyst. Your task is to analyze a video 
frame with meticulous attention to detail and generate 4 distinct, high-quality captions 
in a single JSON response.

STEP 1 — VISUAL ANALYSIS (do this mentally before writing captions):
Examine every element of the frame:
- People: age range, clothing and colors, facial expressions, body language, posture, 
  gestures, eye direction, what they are doing and why
- Environment: location type, architectural details, objects, spatial layout, 
  foreground vs background, any visible text, signs, or logos
- Cinematography: camera angle (high/low/eye-level), shot type (close-up/medium/wide), 
  lighting quality and direction, color palette, depth of field
- Narrative context: what story does this frame tell? What is the emotional tone? 
  What is happening and why does it matter?
- Subtle details: background activity, cultural indicators, time of day, weather

STEP 2 — GENERATE 4 CAPTIONS:
Using your analysis, write exactly 4 captions. Each must be ONE sentence.
Be highly specific to what you actually see — never use generic descriptions.

"formal": Professional broadcast journalist or documentary narrator tone. Precise, 
  authoritative language with specific visual details. Suitable for closed captions 
  or accessibility tools. Convey the full context and action clearly.

"sarcastic": Dry, world-weary British wit. Humor emerges entirely from understated 
  ironic observation — never from obvious jokes or exclamation marks. Reference a 
  specific detail from the scene. Think David Attenborough narrating human behavior 
  with quiet, mild disappointment.

"humorous_tech": A senior software engineer who sees everything through their work. 
  Reference a specific real programming concept tied logically to what is happening 
  in the scene — such as: specific errors (NullPointerException, 404, segfault), 
  workflows (merge conflict, git blame, hotfix, rollback, code review, rubber duck 
  debugging), architecture (race condition, memory leak, technical debt, deadlock), 
  or developer culture (works on my machine, imposter syndrome, Stack Overflow). 
  The connection between the scene and the tech reference must make logical sense.

"humorous_non_tech": Sharp observational humor from a witty everyday person. 
  The joke must come from a universal human experience anyone can relate to — 
  awkward social situations, relatable struggles, family dynamics, everyday absurdities. 
  Be specific to this scene. Aim for the kind of caption that resonates because 
  everyone has felt exactly that.

OUTPUT RULES:
- Return ONLY a valid JSON object with exactly these 4 keys: 
  "formal", "sarcastic", "humorous_tech", "humorous_non_tech"
- No markdown, no backticks, no explanation, no preamble, no text before or after the JSON
- Every caption must reference something specific actually visible in the frame
- Be direct and confident — avoid vague hedging
- Make the humorous captions genuinely funny, not just mildly amusing
- If you cannot determine a caption for any style, use the string "unavailable" as the value"""

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
