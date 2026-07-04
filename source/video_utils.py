"""
video_utils.py
==============
Utilities for opening video files, extracting frames at a configurable interval,
and encoding them as base64 JPEG strings ready for API transmission.

Public API
----------
- extract_frames(video_path, interval_seconds, jpeg_quality, include_data_uri_prefix)
    -> list[FrameData]
- get_video_info(video_path)
    -> VideoInfo

Internal helpers
----------------
- _open_capture(video_path)  - opens and validates a cv2.VideoCapture
- _format_timestamp(seconds) - converts float seconds -> "HH:MM:SS.mmm"
- _encode_frame(frame, jpeg_quality, include_data_uri_prefix) - BGR array -> base64 str
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import TypedDict, Union

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public TypedDicts - define the shape of every returned dict explicitly so
# callers get IDE auto-complete and static-analysis support.
# ---------------------------------------------------------------------------


class FrameData(TypedDict):
    """One extracted frame, ready for API transmission.

    Fields
    ------
    frame_number : int
        0-based index of the frame inside the source video file.
    timestamp_seconds : float
        Position of the frame in the video, expressed as seconds from the start.
        Rounded to 3 decimal places (millisecond precision).
    timestamp_str : str
        Human-readable timestamp in ``"HH:MM:SS.mmm"`` format.
    base64_image : str
        JPEG-encoded frame as a base64 string.  When *include_data_uri_prefix*
        is ``True`` the string is prefixed with ``"data:image/jpeg;base64,"``.
    """

    frame_number: int
    timestamp_seconds: float
    timestamp_str: str
    base64_image: str


class VideoInfo(TypedDict):
    """Metadata returned by :func:`get_video_info`.

    Fields
    ------
    fps : float
        Frames per second reported by the codec.
    frame_count : int
        Total number of frames in the video.
    duration_seconds : float
        Total duration in seconds (``frame_count / fps``).
        ``0.0`` if *fps* is zero or unknown.
    width : int
        Frame width in pixels.
    height : int
        Frame height in pixels.
    codec : str
        Four-character codec identifier string (e.g. ``"avc1"``).
        Empty string if the codec cannot be determined.
    """

    fps: float
    frame_count: int
    duration_seconds: float
    width: int
    height: int
    codec: str


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _open_capture(video_path: Union[str, Path]) -> cv2.VideoCapture:
    """Open a video file and return a validated :class:`cv2.VideoCapture` object.

    Parameters
    ----------
    video_path:
        Absolute or relative path to the video file.  Accepts both
        :class:`str` and :class:`pathlib.Path` objects.

    Returns
    -------
    cv2.VideoCapture
        An opened capture object.  The caller is responsible for releasing it.

    Raises
    ------
    FileNotFoundError
        If *video_path* does not point to an existing file.
    IOError
        If OpenCV cannot open the file (e.g. unsupported format, corrupted
        header, missing codec).
    """
    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(f"Video file not found: '{path}'")
    if not path.is_file():
        raise FileNotFoundError(f"Path exists but is not a file: '{path}'")

    logger.debug("Opening video capture for '%s'", path)
    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        raise IOError(
            f"OpenCV could not open '{path}'. "
            "The file may be corrupted, use an unsupported codec, or the "
            "required codec library may be missing."
        )

    return cap


def _format_timestamp(seconds: float) -> str:
    """Convert a float number of seconds into a ``"HH:MM:SS.mmm"`` string.

    Parameters
    ----------
    seconds:
        Non-negative number of seconds.

    Returns
    -------
    str
        Formatted timestamp, e.g. ``"00:01:23.456"``.

    Examples
    --------
    >>> _format_timestamp(83.456)
    '00:01:23.456'
    >>> _format_timestamp(3661.001)
    '01:01:01.001'
    """
    seconds = max(0.0, seconds)
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_secs = total_ms // 1000
    secs = total_secs % 60
    total_mins = total_secs // 60
    mins = total_mins % 60
    hours = total_mins // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}.{ms:03d}"


def _encode_frame(
    frame: np.ndarray,
    jpeg_quality: int,
    include_data_uri_prefix: bool,
) -> str:
    """Encode a BGR NumPy frame as a base64 JPEG string.

    Parameters
    ----------
    frame:
        A BGR image array as returned by :meth:`cv2.VideoCapture.read`.
    jpeg_quality:
        JPEG compression quality in the range ``[0, 100]``.
        Higher values produce larger but sharper images.
    include_data_uri_prefix:
        If ``True``, prepend ``"data:image/jpeg;base64,"`` to the result so
        the string can be used directly in an HTML ``<img src="...">`` or passed
        to APIs that expect a data URI.

    Returns
    -------
    str
        Base64-encoded JPEG string, optionally prefixed with the data URI
        scheme.

    Raises
    ------
    RuntimeError
        If OpenCV fails to encode the frame to JPEG (e.g. unsupported
        pixel format).
    """
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    success, buffer = cv2.imencode(".jpg", frame, encode_params)

    if not success:
        raise RuntimeError(
            "cv2.imencode failed to encode the frame to JPEG. "
            "The frame may have an unsupported pixel format or be empty."
        )

    b64_bytes = base64.b64encode(buffer.tobytes())
    b64_str = b64_bytes.decode("utf-8")

    if include_data_uri_prefix:
        return f"data:image/jpeg;base64,{b64_str}"
    return b64_str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_video_info(video_path: Union[str, Path]) -> VideoInfo:
    """Return metadata about a video file without extracting any frames.

    Parameters
    ----------
    video_path:
        Absolute or relative path to the video file.  Accepts both
        :class:`str` and :class:`pathlib.Path` objects.

    Returns
    -------
    VideoInfo
        A typed dict containing:

        * **fps** - frames per second (``float``).
        * **frame_count** - total number of frames (``int``).
        * **duration_seconds** - total duration in seconds (``float``).
          Returns ``0.0`` when *fps* is zero or unknown.
        * **width** - frame width in pixels (``int``).
        * **height** - frame height in pixels (``int``).
        * **codec** - four-character codec identifier string (``str``),
          e.g. ``"avc1"``.  Empty string if unavailable.

    Raises
    ------
    FileNotFoundError
        If *video_path* does not exist or is not a regular file.
    IOError
        If OpenCV cannot open the file.

    Examples
    --------
    >>> info = get_video_info("input/sample.mp4")
    >>> print(info["duration_seconds"])
    42.0
    """
    cap = _open_capture(video_path)
    try:
        fps: float = cap.get(cv2.CAP_PROP_FPS)
        frame_count: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width: int = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height: int = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # CAP_PROP_FOURCC stores the codec as a packed 32-bit integer.
        # Decode each byte to its ASCII character; filter out null bytes.
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec_chars = [chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4)]
        codec: str = "".join(c for c in codec_chars if c != "\x00").strip()

        duration_seconds: float = (
            round(frame_count / fps, 3) if fps > 0 else 0.0
        )

        info: VideoInfo = {
            "fps": fps,
            "frame_count": frame_count,
            "duration_seconds": duration_seconds,
            "width": width,
            "height": height,
            "codec": codec,
        }

        logger.debug("Video info for '%s': %s", video_path, info)
        return info

    finally:
        cap.release()
        logger.debug(
            "Released VideoCapture for '%s' (get_video_info)", video_path
        )


def extract_frames(
    video_path: Union[str, Path],
    interval_seconds: float = 2.0,
    jpeg_quality: int = 85,
    include_data_uri_prefix: bool = False,
) -> list[FrameData]:
    """Extract one frame every *interval_seconds* from a video file.

    The first extracted frame is always the very first frame of the video
    (frame 0, timestamp 0.0 s).  Subsequent frames are sampled at multiples
    of *interval_seconds*.

    If a particular frame cannot be decoded (e.g. corrupted packet mid-video),
    a warning is logged and that frame is skipped; extraction continues with
    the next target timestamp.

    The :class:`cv2.VideoCapture` is **always** released before this function
    returns, even if an exception is raised.

    Parameters
    ----------
    video_path:
        Absolute or relative path to the video file.  Accepts both
        :class:`str` and :class:`pathlib.Path` objects.
    interval_seconds:
        Time gap between consecutive extracted frames, in seconds.
        Must be greater than zero.  Defaults to ``2.0``.
    jpeg_quality:
        JPEG compression quality in the range ``[0, 100]``.
        Higher values = better quality + larger base64 payload.
        Defaults to ``85`` (high quality, reasonable size).
    include_data_uri_prefix:
        When ``True``, each ``base64_image`` value is prefixed with
        ``"data:image/jpeg;base64,"`` so it can be embedded directly in HTML
        or passed to APIs that expect a data URI.
        Defaults to ``False`` (plain base64 string).

    Returns
    -------
    list[FrameData]
        A list of dicts, one per successfully extracted frame, in chronological
        order.  Each dict contains:

        * **frame_number** (``int``) - 0-based index within the video file.
        * **timestamp_seconds** (``float``) - position in seconds,
          rounded to 3 decimal places.
        * **timestamp_str** (``str``) - ``"HH:MM:SS.mmm"`` formatted timestamp.
        * **base64_image** (``str``) - JPEG-encoded frame as a base64 string,
          optionally prefixed with the data URI scheme.

    Raises
    ------
    FileNotFoundError
        If *video_path* does not exist or is not a regular file.
    IOError
        If OpenCV cannot open the file.
    ValueError
        If *interval_seconds* is not a positive number, or if *jpeg_quality*
        is outside ``[0, 100]``.
    RuntimeError
        If the video reports zero or negative FPS, making frame calculation
        impossible.

    Examples
    --------
    >>> frames = extract_frames("input/sample.mp4")
    >>> len(frames)
    21
    >>> frames[0]["timestamp_str"]
    '00:00:00.000'
    >>> frames[1]["timestamp_str"]
    '00:00:02.000'

    >>> # Higher quality, with data URI prefix, every 5 seconds
    >>> frames = extract_frames(
    ...     "input/sample.mp4",
    ...     interval_seconds=5.0,
    ...     jpeg_quality=95,
    ...     include_data_uri_prefix=True,
    ... )
    >>> frames[0]["base64_image"].startswith("data:image/jpeg;base64,")
    True
    """
    # ------------------------------------------------------------------
    # Validate parameters before touching the file system.
    # ------------------------------------------------------------------
    if interval_seconds <= 0:
        raise ValueError(
            f"interval_seconds must be a positive number; got {interval_seconds!r}"
        )
    if not (0 <= jpeg_quality <= 100):
        raise ValueError(
            f"jpeg_quality must be in the range [0, 100]; got {jpeg_quality!r}"
        )

    # ------------------------------------------------------------------
    # Open the capture; it is always released in the finally block below.
    # ------------------------------------------------------------------
    cap = _open_capture(video_path)

    try:
        fps: float = cap.get(cv2.CAP_PROP_FPS)
        total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0:
            raise RuntimeError(
                f"Video '{video_path}' reports FPS={fps}. "
                "Cannot calculate frame positions with non-positive FPS."
            )

        # Number of source frames that correspond to one interval step.
        frames_per_interval: float = fps * interval_seconds

        logger.info(
            "Extracting frames from '%s' | FPS=%.3f | total_frames=%d | "
            "interval=%.2fs (~%.1f frames/step) | quality=%d",
            video_path,
            fps,
            total_frames,
            interval_seconds,
            frames_per_interval,
            jpeg_quality,
        )

        results: list[FrameData] = []

        # ------------------------------------------------------------------
        # Build the list of target frame indices to sample.
        #
        # Iterate: 0, round(1 * frames_per_interval),
        #          round(2 * frames_per_interval), ...
        # until the index would exceed the last valid frame.
        #
        # Using floating-point accumulation (step * frames_per_interval) instead
        # of integer addition avoids cumulative rounding drift across many steps.
        # ------------------------------------------------------------------
        step = 0
        while True:
            target_frame_index = int(round(step * frames_per_interval))

            # total_frames is exclusive; last valid index = total_frames - 1.
            if target_frame_index >= total_frames:
                break

            # Seek directly to the target frame for O(1) random access.
            cap.set(cv2.CAP_PROP_POS_FRAMES, float(target_frame_index))

            success, frame = cap.read()

            if not success or frame is None or frame.size == 0:
                logger.warning(
                    "Could not decode frame %d (step %d) from '%s' — skipping.",
                    target_frame_index,
                    step,
                    video_path,
                )
                step += 1
                continue

            # Use the actual position reported by OpenCV after the seek for
            # maximum accuracy; fall back to calculated value if unavailable.
            reported_ms: float = cap.get(cv2.CAP_PROP_POS_MSEC)
            if reported_ms >= 0:
                timestamp_seconds = round(reported_ms / 1000.0, 3)
            else:
                timestamp_seconds = round(target_frame_index / fps, 3)

            try:
                b64_image = _encode_frame(
                    frame, jpeg_quality, include_data_uri_prefix
                )
            except RuntimeError as exc:
                logger.warning(
                    "Failed to encode frame %d from '%s': %s — skipping.",
                    target_frame_index,
                    video_path,
                    exc,
                )
                step += 1
                continue

            frame_data: FrameData = {
                "frame_number": target_frame_index,
                "timestamp_seconds": timestamp_seconds,
                "timestamp_str": _format_timestamp(timestamp_seconds),
                "base64_image": b64_image,
            }
            results.append(frame_data)

            logger.debug(
                "Extracted frame %d | timestamp=%s",
                target_frame_index,
                frame_data["timestamp_str"],
            )

            step += 1

        logger.info(
            "Extraction complete: %d frame(s) extracted from '%s'.",
            len(results),
            video_path,
        )
        return results

    finally:
        # Guaranteed release regardless of success or exception.
        cap.release()
        logger.debug(
            "Released VideoCapture for '%s' (extract_frames)", video_path
        )
