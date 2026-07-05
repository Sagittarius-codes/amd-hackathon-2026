"""
video_utils.py
==============
Utilities for opening video files, detecting scene boundaries, extracting the
representative middle frame of each scene, and encoding frames as base64 JPEG
strings ready for API transmission.

Public API
----------
- extract_frames(video_path, threshold, min_scene_len, jpeg_quality,
                 include_data_uri_prefix)
    -> list[FrameData]
- get_video_info(video_path)
    -> VideoInfo

Internal helpers
----------------
- _open_capture(video_path)  - opens and validates a cv2.VideoCapture
- _format_timestamp(seconds) - converts float seconds -> "HH:MM:SS.mmm"
- _encode_frame(frame, jpeg_quality, include_data_uri_prefix) - BGR array -> base64 str
- _uniform_fallback(video_path, jpeg_quality, include_data_uri_prefix)
    - fallback uniform 2-second sampler used when no scenes are detected

Scene detection
---------------
PySceneDetect (v0.6+) is used via the ``scenedetect.detect()`` /
``scenedetect.open_video()`` API.  The ``ContentDetector`` finds hard cuts by
comparing HSV histograms between consecutive frames.

For each detected scene, the *middle* frame is extracted as the representative
image:
    middle_frame = scene_start_frame + (scene_end_frame - scene_start_frame) // 2

If no scenes are detected (threshold too high, no cuts present, etc.), the
function falls back to uniform 2-second sampling and logs a warning.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional, TypedDict, Union

import cv2
import numpy as np

# PySceneDetect v0.6+ public API.
from scenedetect import ContentDetector, SceneManager, open_video
from scenedetect.scene_manager import SceneList

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
    scene_number : int
        1-based index of the scene this frame belongs to.
        Set to ``0`` for frames produced by the uniform fallback sampler.
    scene_start_str : str
        Scene start boundary in ``"HH:MM:SS.mmm"`` format.
        Empty string for frames produced by the uniform fallback sampler.
    scene_end_str : str
        Scene end boundary in ``"HH:MM:SS.mmm"`` format.
        Empty string for frames produced by the uniform fallback sampler.
    """

    frame_number: int
    timestamp_seconds: float
    timestamp_str: str
    base64_image: str
    scene_number: int
    scene_start_str: str
    scene_end_str: str


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


def _uniform_fallback(
    video_path: Union[str, Path],
    jpeg_quality: int,
    include_data_uri_prefix: bool,
    interval_seconds: float = 2.0,
) -> list[FrameData]:
    """Extract one frame every *interval_seconds* as a fallback.

    Called automatically by :func:`extract_frames` when PySceneDetect finds
    no scene boundaries.  Uses the same seek-based approach as the original
    uniform sampler.  All returned :class:`FrameData` dicts have
    ``scene_number=0`` and empty ``scene_start_str`` / ``scene_end_str`` to
    signal that they came from the fallback path.

    Parameters
    ----------
    video_path:
        Path to the video file.
    jpeg_quality:
        JPEG compression quality in the range ``[0, 100]``.
    include_data_uri_prefix:
        If ``True``, prepend the data URI prefix to each base64 string.
    interval_seconds:
        Seconds between sampled frames.  Defaults to ``2.0``.

    Returns
    -------
    list[FrameData]
        Frames in chronological order, or an empty list if the video cannot
        be read.
    """
    cap: Optional[cv2.VideoCapture] = None  # guard against UnboundLocalError (fix V4)
    try:
        cap = _open_capture(video_path)  # may raise FileNotFoundError / IOError
        fps: float = cap.get(cv2.CAP_PROP_FPS)
        total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0:
            logger.error(
                "Fallback sampler: video '%s' reports FPS=%s — cannot sample.",
                video_path,
                fps,
            )
            return []

        frames_per_interval: float = fps * interval_seconds
        results: list[FrameData] = []
        step = 0

        while True:
            target_frame_index = int(round(step * frames_per_interval))
            if target_frame_index >= total_frames:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, float(target_frame_index))
            success, frame = cap.read()

            if not success or frame is None or frame.size == 0:
                logger.warning(
                    "Fallback sampler: could not decode frame %d from '%s' — skipping.",
                    target_frame_index,
                    video_path,
                )
                step += 1
                continue

            reported_ms: float = cap.get(cv2.CAP_PROP_POS_MSEC)
            timestamp_seconds = (
                round(reported_ms / 1000.0, 3)
                if reported_ms >= 0
                else round(target_frame_index / fps, 3)
            )

            try:
                b64_image = _encode_frame(frame, jpeg_quality, include_data_uri_prefix)
            except RuntimeError as exc:
                logger.warning(
                    "Fallback sampler: failed to encode frame %d from '%s': %s — skipping.",
                    target_frame_index,
                    video_path,
                    exc,
                )
                step += 1
                continue

            # Fix V3: use 1-based scene_number derived from the sample index so
            # the frontend dedup check (r.scene === scene) treats every fallback
            # frame as a unique scene and displays all of them.
            frame_data: FrameData = {
                "frame_number": target_frame_index,
                "timestamp_seconds": timestamp_seconds,
                "timestamp_str": _format_timestamp(timestamp_seconds),
                "base64_image": b64_image,
                "scene_number": step + 1,  # 1-based; was 0 which caused dedup drop
                "scene_start_str": "",     # empty signals uniform-fallback origin
                "scene_end_str": "",
            }
            results.append(frame_data)
            step += 1

        return results

    finally:
        if cap is not None:  # only release if _open_capture actually succeeded
            cap.release()
            logger.debug(
                "Released VideoCapture for '%s' (uniform fallback)", video_path
            )


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
    threshold: float = 27.0,
    min_scene_len: int = 15,
    jpeg_quality: int = 85,
    include_data_uri_prefix: bool = False,
) -> list[FrameData]:
    """Detect scene boundaries and extract the middle frame of each scene.

    Uses PySceneDetect's :class:`~scenedetect.ContentDetector` to locate hard
    cuts in *video_path*.  For every detected scene the *middle* frame is
    chosen as the representative image:

    .. code-block:: text

        middle_frame = scene_start_frame + (scene_end_frame - scene_start_frame) // 2

    **Fallback behaviour**: if no scenes are detected (e.g. *threshold* is too
    high, or the video contains no cuts), the function automatically falls back
    to uniform 2-second sampling and logs a warning.  Fallback frames have
    ``scene_number=0`` and empty ``scene_start_str`` / ``scene_end_str``.

    **Two-handle design**: PySceneDetect opens the video through its own
    ``open_video()`` handle for detection; a separate :class:`cv2.VideoCapture`
    (opened via :func:`_open_capture`) is used exclusively for frame reading.
    The cv2 handle is always released in a ``finally`` block.

    Parameters
    ----------
    video_path:
        Absolute or relative path to the video file.  Accepts both
        :class:`str` and :class:`pathlib.Path` objects.
    threshold:
        Content-change score above which a frame is considered a scene cut.
        Lower values = more sensitive (more scenes detected).
        Defaults to ``27.0`` (PySceneDetect standard default for hard cuts).
    min_scene_len:
        Minimum number of frames a scene must contain to be kept.
        Shorter scenes are merged with their neighbour by PySceneDetect.
        Defaults to ``15``.
    jpeg_quality:
        JPEG compression quality in the range ``[0, 100]``.
        Higher values = better quality + larger base64 payload.
        Defaults to ``85``.
    include_data_uri_prefix:
        When ``True``, each ``base64_image`` value is prefixed with
        ``"data:image/jpeg;base64,"`` so it can be embedded directly in HTML
        or passed to APIs that expect a data URI.
        Defaults to ``False`` (plain base64 string).

    Returns
    -------
    list[FrameData]
        One entry per successfully extracted scene frame, in chronological
        order.  Each dict contains:

        * **frame_number** (``int``) - 0-based frame index within the video.
        * **timestamp_seconds** (``float``) - position in seconds, rounded to
          3 decimal places.
        * **timestamp_str** (``str``) - ``"HH:MM:SS.mmm"`` formatted timestamp
          of the extracted middle frame.
        * **base64_image** (``str``) - JPEG-encoded frame as a base64 string,
          optionally prefixed with the data URI scheme.
        * **scene_number** (``int``) - 1-based scene index.  ``0`` if this
          frame came from the uniform fallback sampler.
        * **scene_start_str** (``str``) - ``"HH:MM:SS.mmm"`` scene start time.
          Empty string for fallback frames.
        * **scene_end_str** (``str``) - ``"HH:MM:SS.mmm"`` scene end time.
          Empty string for fallback frames.

    Raises
    ------
    FileNotFoundError
        If *video_path* does not exist or is not a regular file.
    IOError
        If OpenCV cannot open the file for the frame-reading phase.
    ValueError
        If *jpeg_quality* is outside ``[0, 100]``.
    RuntimeError
        If PySceneDetect cannot open the video for scene detection.

    Examples
    --------
    >>> frames = extract_frames("input/sample.mp4")
    >>> frames[0]["scene_number"]
    1
    >>> frames[0]["scene_start_str"]
    '00:00:00.000'
    >>> frames[0]["timestamp_str"]  # middle frame of scene 1
    '00:00:03.240'

    >>> # More sensitive detection, higher JPEG quality
    >>> frames = extract_frames(
    ...     "input/sample.mp4",
    ...     threshold=20.0,
    ...     min_scene_len=10,
    ...     jpeg_quality=95,
    ... )
    """
    # ------------------------------------------------------------------
    # Validate parameters before touching the file system.
    # ------------------------------------------------------------------
    if not (0 <= jpeg_quality <= 100):
        raise ValueError(
            f"jpeg_quality must be in the range [0, 100]; got {jpeg_quality!r}"
        )

    path = Path(video_path)

    # ------------------------------------------------------------------
    # Phase 1: Scene detection via PySceneDetect.
    #
    # open_video() opens its own internal handle — entirely separate from
    # the cv2.VideoCapture used in Phase 2.  SceneManager.detect_scenes()
    # reads through the video and populates the scene list.
    # ------------------------------------------------------------------
    logger.info(
        "Running scene detection on '%s' | threshold=%.1f | min_scene_len=%d",
        path,
        threshold,
        min_scene_len,
    )

    try:
        sd_video = open_video(str(path))
    except Exception as exc:
        raise RuntimeError(
            f"PySceneDetect could not open '{path}' for scene detection: {exc}"
        ) from exc

    scene_manager = SceneManager()
    scene_manager.add_detector(
        ContentDetector(threshold=threshold, min_scene_len=min_scene_len)
    )

    scene_manager.detect_scenes(video=sd_video, show_progress=False)
    scene_list: SceneList = scene_manager.get_scene_list()

    logger.info(
        "Scene detection complete: %d scene(s) found in '%s'.",
        len(scene_list),
        path,
    )

    # ------------------------------------------------------------------
    # Fallback: no scenes detected → uniform 2-second sampling.
    # ------------------------------------------------------------------
    if not scene_list:
        logger.warning(
            "No scenes detected in '%s' (threshold=%.1f). "
            "Falling back to uniform 2-second frame sampling.",
            path,
            threshold,
        )
        return _uniform_fallback(path, jpeg_quality, include_data_uri_prefix)

    # ------------------------------------------------------------------
    # Phase 2: Frame extraction via a dedicated cv2.VideoCapture.
    #
    # A fresh handle is opened here so there is no shared state with the
    # PySceneDetect handle from Phase 1.  It is always released in the
    # finally block below.
    # ------------------------------------------------------------------
    cap = _open_capture(path)

    try:
        fps: float = cap.get(cv2.CAP_PROP_FPS)

        if fps <= 0:
            raise RuntimeError(
                f"Video '{path}' reports FPS={fps}. "
                "Cannot calculate middle-frame positions with non-positive FPS."
            )

        results: list[FrameData] = []

        for scene_idx, (scene_start, scene_end) in enumerate(scene_list):
            scene_number: int = scene_idx + 1  # 1-based

            # FrameTimecode.get_frames() returns the 0-based frame index.
            start_frame: int = scene_start.get_frames()
            end_frame: int = scene_end.get_frames()

            # Middle frame — explicit form avoids potential integer overflow on
            # very long videos compared to (start + end) // 2.
            middle_frame: int = start_frame + (end_frame - start_frame) // 2

            scene_start_seconds: float = round(
                scene_start.get_seconds(), 3
            )
            scene_end_seconds: float = round(
                scene_end.get_seconds(), 3
            )

            logger.debug(
                "Scene %d: frames [%d, %d) | middle=%d | "
                "start=%s | end=%s",
                scene_number,
                start_frame,
                end_frame,
                middle_frame,
                _format_timestamp(scene_start_seconds),
                _format_timestamp(scene_end_seconds),
            )

            # Seek directly to the middle frame for O(1) random access.
            cap.set(cv2.CAP_PROP_POS_FRAMES, float(middle_frame))
            success, frame = cap.read()

            if not success or frame is None or frame.size == 0:
                logger.warning(
                    "Scene %d: could not decode middle frame %d from '%s' — skipping.",
                    scene_number,
                    middle_frame,
                    path,
                )
                continue

            # Use the actual position reported by OpenCV after the seek for
            # maximum accuracy; fall back to calculated value if unavailable.
            reported_ms: float = cap.get(cv2.CAP_PROP_POS_MSEC)
            timestamp_seconds: float = (
                round(reported_ms / 1000.0, 3)
                if reported_ms >= 0
                else round(middle_frame / fps, 3)
            )

            try:
                b64_image = _encode_frame(frame, jpeg_quality, include_data_uri_prefix)
            except RuntimeError as exc:
                logger.warning(
                    "Scene %d: failed to encode middle frame %d from '%s': %s — skipping.",
                    scene_number,
                    middle_frame,
                    path,
                    exc,
                )
                continue

            frame_data: FrameData = {
                "frame_number": middle_frame,
                "timestamp_seconds": timestamp_seconds,
                "timestamp_str": _format_timestamp(timestamp_seconds),
                "base64_image": b64_image,
                "scene_number": scene_number,
                "scene_start_str": _format_timestamp(scene_start_seconds),
                "scene_end_str": _format_timestamp(scene_end_seconds),
            }
            results.append(frame_data)

            logger.debug(
                "Extracted scene %d middle frame %d | timestamp=%s",
                scene_number,
                middle_frame,
                frame_data["timestamp_str"],
            )

        logger.info(
            "Extraction complete: %d scene frame(s) extracted from '%s'.",
            len(results),
            path,
        )
        return results

    finally:
        # Guaranteed release regardless of success or exception.
        cap.release()
        logger.debug(
            "Released VideoCapture for '%s' (extract_frames)", path
        )
