"""
main.py
=======
Entry point for the video captioning pipeline.

Workflow
--------
1. Log video metadata via get_video_info().
2. Extract one frame per detected scene via extract_frames().
3. For each frame, call get_all_captions() to get 4 tonal styles concurrently.
4. Print each frame's results to the terminal in a grouped, aligned format.
5. Write all results to output/captions.txt in the same grouped format.
6. Print a final summary of how many frames had at least one successful caption.

Paths (both resolved relative to the project root)
---------------------------------------------------
  Input  : input/sample.mp4
  Output : output/captions.txt

Configuration
-------------
  FIREWORKS_API_KEY must be set in the project-root .env file.
  See captioner.py for details.
"""
from __future__ import annotations

import logging
import sys
import time

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_utils import extract_frames, get_video_info
from captioner import get_all_captions
# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
# Configure the root logger so that all child loggers (video_utils, captioner,
# and this module) emit to stderr with a consistent timestamp + level format.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

# Module-level logger — same pattern as video_utils.py and captioner.py.
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants — resolved relative to the project root.
# Path(__file__) is source/main.py, so .parent.parent is the project root.
# ---------------------------------------------------------------------------
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
_INPUT_PATH: Path = _PROJECT_ROOT / "input" / "sample.mp4"
_OUTPUT_PATH: Path = _PROJECT_ROOT / "output" / "captions.txt"

# Placeholder written by captioner.py when a style's API call fails.
_PLACEHOLDER_NO_CAPTION: str = "[no caption]"

# Display labels for each caption style, in the order they are printed.
# The colon column is aligned to the width of the longest label.
_STYLE_LABELS: dict[str, str] = {
    "formal":           "FORMAL",
    "sarcastic":        "SARCASTIC",
    "humorous_tech":    "HUMOR-TECH",
    "humorous_non_tech": "HUMOR-NON-TECH",
}

# Seconds to wait before firing each frame's concurrent API burst.
# Must match _INTER_FRAME_SLEEP_SECONDS in app/api.py.
_INTER_FRAME_SLEEP: int = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Column width for label padding — computed once from the longest display label
# so all colons align regardless of future style additions.
_LABEL_WIDTH: int = max(len(label) for label in _STYLE_LABELS.values())

def _format_frame_block(timestamp_str: str, captions: dict[str, str], frame: dict) -> list[str]:
    """Format one frame's grouped output block as a list of lines.

    The block looks like::

        [00:00:04.000]
          FORMAL        : A performer stands on stage.
          SARCASTIC     : Oh wow, a person standing. Revolutionary.
          HUMOR-TECH    : Artist executing stage.presence() with O(1) complexity.
          HUMOR-NON-TECH: This guy really said "watch this" and meant it.

    All colons are aligned to the width of the longest label.

    Parameters
    ----------
    timestamp_str:
        ``"HH:MM:SS.mmm"`` string from :class:`~video_utils.FrameData`.
    captions:
        Dict returned by :func:`~captioner.get_all_captions` with keys
        ``"formal"``, ``"sarcastic"``, ``"humorous_tech"``,
        ``"humorous_non_tech"``.

    Returns
    -------
    list[str]
        Lines of the block, without a trailing blank line.
    """
    scene_number = frame.get("scene_number", 0)
    scene_start = frame.get("scene_start_str", "")
    scene_end = frame.get("scene_end_str", "")

    if scene_number > 0:
        header = f"[Scene {scene_number}] {scene_start} → {scene_end} | Frame at {timestamp_str}"
    else:
        header = f"[Uniform sample] {timestamp_str}"

    lines: list[str] = [header]
    for style_key, label in _STYLE_LABELS.items():
        caption = captions.get(style_key, _PLACEHOLDER_NO_CAPTION)
        padded_label = label.ljust(_LABEL_WIDTH)
        lines.append(f"  {padded_label}: {caption}")
    return lines


def _log_video_info(info: dict) -> None:  # type: ignore[type-arg]
    """Log the VideoInfo dict returned by get_video_info() at INFO level.

    Parameters
    ----------
    info:
        A :class:`~video_utils.VideoInfo` TypedDict.
    """
    logger.info("Video details:")
    logger.info("  File        : %s", _INPUT_PATH)
    logger.info("  Resolution  : %dx%d", info["width"], info["height"])
    logger.info("  FPS         : %.3f", info["fps"])
    logger.info("  Frame count : %d", info["frame_count"])
    logger.info("  Duration    : %.3f s", info["duration_seconds"])
    logger.info("  Codec       : %s", info["codec"] or "unknown")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the end-to-end video captioning pipeline.

    Raises
    ------
    SystemExit
        With exit code 1 if a fatal error occurs (missing input file,
        unreadable video, missing API key, etc.).
    """
    # ------------------------------------------------------------------
    # Step 1: Inspect the video and log its metadata.
    # ------------------------------------------------------------------
    logger.info("=== Video Captioning Pipeline starting ===")
    logger.info("Input  : %s", _INPUT_PATH)
    logger.info("Output : %s", _OUTPUT_PATH)

    try:
        info = get_video_info(_INPUT_PATH)
    except (FileNotFoundError, IOError) as exc:
        logger.error("Failed to open video: %s", exc)
        sys.exit(1)

    _log_video_info(info)

    # ------------------------------------------------------------------
    # Step 2: Extract one frame every 2 seconds, cap at first 10 for testing.
    # ------------------------------------------------------------------
    logger.info("Extracting frames (1 per 2 s)...")

    try:
        frames = extract_frames(_INPUT_PATH)
    except (FileNotFoundError, IOError, RuntimeError, ValueError) as exc:
        logger.error("Frame extraction failed: %s", exc)
        sys.exit(1)

    total_frames: int = len(frames)
    logger.info("Extracted %d scene frame(s). Starting captioning...", total_frames)

    # ------------------------------------------------------------------
    # Step 3: Ensure the output directory exists, then open the output
    #         file for writing (overwrite any previous run).
    # ------------------------------------------------------------------
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # successful = frames where at least 1 of the 4 styles returned a caption.
    successful: int = 0
    # Each entry is a list of strings (one block per frame).
    all_blocks: list[list[str]] = []

    # ------------------------------------------------------------------
    # Step 4: Caption each frame, collect results.
    # ------------------------------------------------------------------
    for i, frame in enumerate(frames):
        frame_number: int = frame["frame_number"]
        timestamp_str: str = frame["timestamp_str"]
        base64_image: str = frame["base64_image"]

        # Pause before each burst to avoid hammering the rate limiter.
        # Skip the sleep before the very first frame.
        if i > 0:
            logger.debug(
                "Sleeping %ds before next frame burst...",
                _INTER_FRAME_SLEEP,
            )
            time.sleep(_INTER_FRAME_SLEEP)

        logger.info(
            "Captioning frame %d/%d  [%s]  (4 styles concurrently)...",
            i + 1,
            total_frames,
            timestamp_str,
        )

        try:
            captions = get_all_captions(base64_image) #hashed out temporarily for testing
            #captions = { #dummy captions for testing
             #   "formal": f"A frame from the video at {timestamp_str}.",
              #  "sarcastic": f"Wow, another frame. Groundbreaking stuff at {timestamp_str}.",
              #  "humorous_tech": f"Frame rendered successfully. No null pointers at {timestamp_str}.",
               # "humorous_non_tech": f"Nobody asked but here we are at {timestamp_str}.",
#}
        except ValueError as exc:
            # Missing API key — fatal: nothing will work for any frame.
            logger.error("Fatal configuration error: %s", exc)
            sys.exit(1)
        except Exception as exc:
            # Any other unexpected error — non-fatal: log and write placeholders.
            logger.error(
                "Frame %d [%s] — get_all_captions() raised unexpectedly: %s",
                frame_number,
                timestamp_str,
                exc,
            )
            # Build a placeholder block so the output file stays complete.
            captions = {key: _PLACEHOLDER_NO_CAPTION for key in _STYLE_LABELS}

        # A frame is successful if at least one style returned a real caption.
        if any(
            captions.get(key, _PLACEHOLDER_NO_CAPTION) != _PLACEHOLDER_NO_CAPTION
            for key in _STYLE_LABELS
        ):
            successful += 1

        block = _format_frame_block(timestamp_str, captions, frame)
        all_blocks.append(block)

        # Print this frame's block to the terminal immediately.
        for line in block:
            print(line)
        print()  # blank line after each frame in the terminal

    # ------------------------------------------------------------------
    # Step 5: Write all collected blocks to the output file.
    #         Blocks are separated by a blank line; no trailing blank line.
    # ------------------------------------------------------------------
    summary_line = (
        f"Done. {successful}/{total_frames} frames captioned successfully."
    )
    try:
        with _OUTPUT_PATH.open("w", encoding="utf-8") as f:
            for idx, block in enumerate(all_blocks):
                for line in block:
                    f.write(line + "\n")
                # Blank line between frames only — not after the last one.
                if idx < len(all_blocks) - 1:
                    f.write("\n")
            # Summary as the final content, separated by a blank line.
            f.write("\n" + summary_line + "\n")
    except OSError as exc:
        logger.error("Failed to write output file '%s': %s", _OUTPUT_PATH, exc)
        sys.exit(1)

    logger.info("Results written to '%s'.", _OUTPUT_PATH)

    # ------------------------------------------------------------------
    # Step 6: Print the summary to the terminal.
    # ------------------------------------------------------------------
    print(summary_line)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
