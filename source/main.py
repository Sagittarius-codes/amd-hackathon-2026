"""
main.py
=======
Entry point for the video captioning pipeline.

Workflow
--------
1. Log video metadata via get_video_info().
2. Extract one frame every 2 seconds via extract_frames().
3. Send each frame to the OpenRouter API via get_caption().
4. Print each result to the terminal.
5. Write all results to output/captions.txt.
6. Print a final summary of how many frames were captioned.

Paths (both resolved relative to the project root)
---------------------------------------------------
  Input  : input/sample.mp4
  Output : output/captions.txt

Configuration
-------------
  OPENROUTER_API_KEY must be set in the project-root .env file.
  See captioner.py for details.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_utils import extract_frames, get_video_info
from captioner import get_caption
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

# Placeholder strings written to the output file when a frame cannot be
# captioned, so the output file always has one line per attempted frame.
_PLACEHOLDER_NO_CAPTION: str = "[no caption]"
_PLACEHOLDER_ERROR: str = "[ERROR: caption failed]"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_line(timestamp_str: str, caption: str) -> str:
    """Format one output line in the canonical pipeline format.

    Parameters
    ----------
    timestamp_str:
        ``"HH:MM:SS.mmm"`` string from :class:`~video_utils.FrameData`.
    caption:
        The caption text, or a placeholder string.

    Returns
    -------
    str
        A single line like ``"[00:00:02.000] A person walks across a street."``.
    """
    return f"[{timestamp_str}] {caption}"


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
    # Step 2: Extract one frame every 2 seconds.
    # ------------------------------------------------------------------
    logger.info("Extracting frames (1 per 2 s)...")

    try:
        frames = extract_frames(_INPUT_PATH)
    except (FileNotFoundError, IOError, RuntimeError, ValueError) as exc:
        logger.error("Frame extraction failed: %s", exc)
        sys.exit(1)

    total_frames: int = len(frames)
    logger.info("Extracted %d frame(s). Starting captioning...", total_frames)

    # ------------------------------------------------------------------
    # Step 3: Ensure the output directory exists, then open the output
    #         file for writing (overwrite any previous run).
    # ------------------------------------------------------------------
    _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    successful: int = 0
    lines: list[str] = []

    # ------------------------------------------------------------------
    # Step 4: Caption each frame, collect results.
    # ------------------------------------------------------------------
    for frame in frames:
        frame_number: int = frame["frame_number"]
        timestamp_str: str = frame["timestamp_str"]
        base64_image: str = frame["base64_image"]

        logger.info(
            "Captioning frame %d / %d  [%s]...",
            frame_number,
            total_frames - 1,  # 0-based last index
            timestamp_str,
        )

        try:
            caption = get_caption(base64_image)
        except Exception as exc:
            # Non-fatal: log the error, write an error placeholder, and move on.
            logger.error(
                "Frame %d [%s] — caption failed: %s",
                frame_number,
                timestamp_str,
                exc,
            )
            line = _format_line(timestamp_str, _PLACEHOLDER_ERROR)
            lines.append(line)
            print(line)
            continue

        # An empty string means a malformed/empty API response (already warned
        # inside captioner.py). Write the no-caption placeholder.
        if not caption:
            line = _format_line(timestamp_str, _PLACEHOLDER_NO_CAPTION)
        else:
            line = _format_line(timestamp_str, caption)
            successful += 1

        lines.append(line)
        # Print to terminal as specified.
        print(line)

    # ------------------------------------------------------------------
    # Step 5: Write all collected lines to the output file atomically.
    # ------------------------------------------------------------------
    try:
        with _OUTPUT_PATH.open("w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
            # Write the summary as the final line of the file.
            summary_line = f"Done. {successful}/{total_frames} frames captioned successfully."
            f.write("\n" + summary_line + "\n")
    except OSError as exc:
        logger.error("Failed to write output file '%s': %s", _OUTPUT_PATH, exc)
        sys.exit(1)

    logger.info("Results written to '%s'.", _OUTPUT_PATH)

    # ------------------------------------------------------------------
    # Step 6: Print the summary to the terminal.
    # ------------------------------------------------------------------
    summary = f"Done. {successful}/{total_frames} frames captioned successfully."
    print()
    print(summary)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
