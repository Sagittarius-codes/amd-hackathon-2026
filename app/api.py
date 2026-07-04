"""
api.py
======
FastAPI backend for the video captioning pipeline GUI.

Endpoints
---------
POST   /upload      - Accept a video file, save to input/uploaded_video.mp4
GET    /video-info  - Return VideoInfo for the currently uploaded video
POST   /process     - Start the captioning pipeline in a background thread
GET    /status      - Return current job status, progress, and results
WS     /ws          - Stream real-time pipeline progress to all connected clients

Pipeline execution
------------------
The pipeline (scene detection + 4-style captioning) is blocking I/O.
It runs inside a daemon threading.Thread.  WebSocket messages are pushed
back to the asyncio event loop via loop.call_soon_threadsafe(), which
enqueues a coroutine that broadcasts to all active WebSocket connections.

WebSocket message types
-----------------------
{"type": "scene_detected",   "total": int,  "scenes": [...]}
{"type": "captioning_start", "scene": int,  "timestamp": str}
{"type": "caption_result",   "scene": int,  "captions": {...}, "frame_info": {...}}
{"type": "complete",         "summary": {...}}
{"type": "error",            "message": str}

Run
---
    uvicorn app.api:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# sys.path — make source/ importable from app/api.py
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SOURCE_DIR = _PROJECT_ROOT / "source"
if str(_SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(_SOURCE_DIR))

from video_utils import extract_frames, get_video_info  # noqa: E402
from captioner import get_all_captions  # noqa: E402

# ---------------------------------------------------------------------------
# Module-level logger — same pattern as source/ modules
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_INPUT_DIR: Path = _PROJECT_ROOT / "input"
_OUTPUT_DIR: Path = _PROJECT_ROOT / "output"
_UPLOAD_PATH: Path = _INPUT_DIR / "uploaded_video.mp4"
_CAPTIONS_PATH: Path = _OUTPUT_DIR / "captions.txt"

# Ensure directories exist at startup
_INPUT_DIR.mkdir(parents=True, exist_ok=True)
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Global pipeline state
# ---------------------------------------------------------------------------
# All mutations happen inside the background thread; reads happen from
# FastAPI route handlers.  Python's GIL protects simple attribute reads/
# writes on built-in types, so a threading.Lock is used for the results list.

_state_lock = threading.Lock()

_job_status: str = "idle"          # idle | processing | complete | error
_progress_pct: float = 0.0         # 0.0 – 100.0
_current_scene: int = 0            # 1-based index of the scene being processed
_total_scenes: int = 0             # set once scene detection finishes
_results: list[dict[str, Any]] = []  # accumulated caption_result payloads
_error_message: Optional[str] = None

# The asyncio event loop that uvicorn is running on.  Set once during startup.
_event_loop: Optional[asyncio.AbstractEventLoop] = None

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Tracks all active WebSocket connections and provides broadcast."""

    def __init__(self) -> None:
        self._active: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._active.append(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self._active))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._active = [ws for ws in self._active if ws is not websocket]
        logger.info("WebSocket client disconnected. Total: %d", len(self._active))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send *message* as JSON to every connected client.

        Clients that have disconnected mid-send are silently removed.
        """
        payload = json.dumps(message)
        dead: list[WebSocket] = []

        async with self._lock:
            targets = list(self._active)

        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)

        if dead:
            async with self._lock:
                self._active = [ws for ws in self._active if ws not in dead]


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Video Captioning Pipeline API",
    description="Backend for the AMD Hackathon 2026 video captioning GUI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _capture_event_loop() -> None:
    """Cache the running asyncio event loop for use by the background thread."""
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    logger.info("Event loop captured. API ready on http://localhost:8000")


# ---------------------------------------------------------------------------
# Helper: push a message from any thread
# ---------------------------------------------------------------------------


def _push(message: dict[str, Any]) -> None:
    """Schedule a WebSocket broadcast from a non-async context (background thread).

    Uses :func:`asyncio.AbstractEventLoop.call_soon_threadsafe` to safely
    hand the coroutine to the running event loop without blocking.
    """
    if _event_loop is None:
        logger.warning("Event loop not ready — dropping WebSocket message: %s", message)
        return

    async def _do_broadcast() -> None:
        await manager.broadcast(message)

    _event_loop.call_soon_threadsafe(
        _event_loop.create_task,
        _do_broadcast(),
    )


# ---------------------------------------------------------------------------
# Helper: reset global state before a new job
# ---------------------------------------------------------------------------


def _reset_state() -> None:
    global _job_status, _progress_pct, _current_scene, _total_scenes
    global _results, _error_message

    with _state_lock:
        _job_status = "idle"
        _progress_pct = 0.0
        _current_scene = 0
        _total_scenes = 0
        _results = []
        _error_message = None


# ---------------------------------------------------------------------------
# Helper: clean up files from the previous run
# ---------------------------------------------------------------------------


def _cleanup_previous_run() -> None:
    """Delete the previously uploaded video and captions output, if they exist."""
    for path in (_UPLOAD_PATH, _CAPTIONS_PATH):
        if path.exists():
            try:
                path.unlink()
                logger.info("Cleaned up previous run file: %s", path)
            except OSError as exc:
                logger.warning("Could not delete '%s': %s", path, exc)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ProcessRequest(BaseModel):
    """Body for POST /process."""
    max_scenes: Optional[int] = None  # None = full pipeline; int = cap for testing


class StatusResponse(BaseModel):
    """Body returned by GET /status."""
    status: str
    progress_pct: float
    current_scene: int
    total_scenes: int
    results: list[dict[str, Any]]
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# Background pipeline worker
# ---------------------------------------------------------------------------


def _run_pipeline(max_scenes: Optional[int]) -> None:
    """Execute the full captioning pipeline in a background thread.

    Reads from ``_UPLOAD_PATH``, runs scene detection via
    :func:`extract_frames`, then calls :func:`get_all_captions` for each
    scene.  Progress is broadcast to all WebSocket clients via :func:`_push`.

    Parameters
    ----------
    max_scenes:
        If not ``None``, only the first *max_scenes* scenes are captioned.
        ``None`` runs the full pipeline.
    """
    global _job_status, _progress_pct, _current_scene, _total_scenes, _results

    # ------------------------------------------------------------------
    # Phase 1: Scene detection
    # ------------------------------------------------------------------
    try:
        logger.info("Pipeline starting. Detecting scenes in '%s'...", _UPLOAD_PATH)
        frames = extract_frames(_UPLOAD_PATH)
    except Exception as exc:
        logger.error("Scene detection failed: %s", exc)
        with _state_lock:
            _job_status = "error"
            _error_message = str(exc)
        _push({"type": "error", "message": str(exc)})
        return

    # Apply the scene cap *after* detection so total count is accurate.
    if max_scenes is not None:
        frames = frames[:max_scenes]

    total = len(frames)

    with _state_lock:
        _total_scenes = total

    # Collect lightweight scene descriptors (no base64) for the initial message.
    scene_descriptors = [
        {
            "scene_number": f.get("scene_number", 0),
            "timestamp_str": f["timestamp_str"],
            "scene_start_str": f.get("scene_start_str", ""),
            "scene_end_str": f.get("scene_end_str", ""),
        }
        for f in frames
    ]

    _push({
        "type": "scene_detected",
        "total": total,
        "scenes": scene_descriptors,
    })

    logger.info("Scene detection complete: %d scene(s). Starting captioning...", total)

    # ------------------------------------------------------------------
    # Phase 2: Captioning — one scene at a time
    # ------------------------------------------------------------------
    captions_lines: list[str] = []

    for idx, frame in enumerate(frames):
        scene_num: int = frame.get("scene_number", idx + 1)
        timestamp_str: str = frame["timestamp_str"]
        base64_image: str = frame["base64_image"]

        with _state_lock:
            _current_scene = scene_num

        # Progress: scene detection done = 10%, captioning = 10–100%.
        pct = 10.0 + (idx / total) * 90.0
        with _state_lock:
            _progress_pct = round(pct, 1)

        _push({
            "type": "captioning_start",
            "scene": scene_num,
            "timestamp": timestamp_str,
        })

        logger.info(
            "Captioning scene %d/%d  [%s]...",
            idx + 1,
            total,
            timestamp_str,
        )

        # Call the captioner — skip the scene on any exception.
        try:
            captions = get_all_captions(base64_image)
        except Exception as exc:
            logger.error(
                "Scene %d [%s] — get_all_captions() failed: %s — using placeholders.",
                scene_num,
                timestamp_str,
                exc,
            )
            captions = {
                "formal": "[no caption]",
                "sarcastic": "[no caption]",
                "humorous_tech": "[no caption]",
                "humorous_non_tech": "[no caption]",
            }

        frame_info = {
            "scene_number": scene_num,
            "frame_number": frame["frame_number"],
            "timestamp_seconds": frame["timestamp_seconds"],
            "timestamp_str": timestamp_str,
            "scene_start_str": frame.get("scene_start_str", ""),
            "scene_end_str": frame.get("scene_end_str", ""),
        }

        result_payload: dict[str, Any] = {
            "type": "caption_result",
            "scene": scene_num,
            "captions": captions,
            "frame_info": frame_info,
        }

        _push(result_payload)

        with _state_lock:
            _results.append({
                "scene": scene_num,
                "captions": captions,
                "frame_info": frame_info,
            })

        # Accumulate captions.txt lines (formal style only for the text file).
        captions_lines.append(
            f"[{timestamp_str}] (Scene {scene_num})\n"
            f"  FORMAL        : {captions.get('formal', '[no caption]')}\n"
            f"  SARCASTIC     : {captions.get('sarcastic', '[no caption]')}\n"
            f"  HUMOR-TECH    : {captions.get('humorous_tech', '[no caption]')}\n"
            f"  HUMOR-NON-TECH: {captions.get('humorous_non_tech', '[no caption]')}"
        )

    # ------------------------------------------------------------------
    # Phase 3: Write captions.txt, finalise state
    # ------------------------------------------------------------------
    with _state_lock:
        final_results = list(_results)

    successful = sum(
        1 for r in final_results
        if any(v != "[no caption]" for v in r["captions"].values())
    )

    summary = {
        "total_scenes": total,
        "successful": successful,
        "failed": total - successful,
    }

    try:
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with _CAPTIONS_PATH.open("w", encoding="utf-8") as f:
            f.write("\n\n".join(captions_lines))
            f.write(f"\n\nDone. {successful}/{total} scenes captioned successfully.\n")
        logger.info("Captions written to '%s'.", _CAPTIONS_PATH)
    except OSError as exc:
        logger.error("Failed to write captions.txt: %s", exc)

    with _state_lock:
        _job_status = "complete"
        _progress_pct = 100.0

    _push({"type": "complete", "summary": summary})
    logger.info("Pipeline complete. %d/%d scenes captioned.", successful, total)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/upload", summary="Upload a video file")
async def upload_video(file: UploadFile = File(...)) -> dict[str, str]:
    """Accept a video file and save it to ``input/uploaded_video.mp4``.

    - Rejects the upload with **HTTP 409** if the pipeline is currently running.
    - Cleans up the previous upload and captions output before saving.

    Returns
    -------
    dict
        ``{"message": "...", "filename": "uploaded_video.mp4"}``
    """
    if _job_status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Cannot upload while a captioning job is running. Wait for it to complete.",
        )

    _cleanup_previous_run()
    _reset_state()

    content = await file.read()
    _UPLOAD_PATH.write_bytes(content)

    logger.info(
        "Video uploaded: original='%s', saved as '%s' (%d bytes)",
        file.filename,
        _UPLOAD_PATH.name,
        len(content),
    )

    return {"message": "Upload successful.", "filename": _UPLOAD_PATH.name}


@app.get("/video-info", summary="Get metadata for the uploaded video")
async def video_info() -> dict[str, Any]:
    """Return :class:`~video_utils.VideoInfo` for the currently uploaded video.

    Raises
    ------
    HTTP 404
        If no video has been uploaded yet.
    HTTP 500
        If OpenCV cannot read the video.
    """
    if not _UPLOAD_PATH.exists():
        raise HTTPException(status_code=404, detail="No video uploaded yet.")

    try:
        info = get_video_info(_UPLOAD_PATH)
    except (FileNotFoundError, IOError) as exc:
        logger.error("get_video_info() failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return dict(info)


@app.post("/process", summary="Start the captioning pipeline")
async def process_video(body: ProcessRequest) -> dict[str, str]:
    """Launch the scene detection + captioning pipeline in a background thread.

    - Rejects with **HTTP 409** if a job is already running.
    - Rejects with **HTTP 404** if no video has been uploaded.

    Parameters
    ----------
    body.max_scenes:
        ``null`` to run the full pipeline, or a positive integer to cap the
        number of scenes (useful for testing without waiting for a full run).

    Returns
    -------
    dict
        ``{"message": "Processing started."}``
    """
    global _job_status

    if _job_status == "processing":
        raise HTTPException(
            status_code=409,
            detail="A captioning job is already running.",
        )

    if not _UPLOAD_PATH.exists():
        raise HTTPException(status_code=404, detail="No video uploaded yet.")

    _reset_state()

    with _state_lock:
        _job_status = "processing"

    thread = threading.Thread(
        target=_run_pipeline,
        args=(body.max_scenes,),
        daemon=True,
        name="pipeline-worker",
    )
    thread.start()

    logger.info(
        "Pipeline thread started. max_scenes=%s",
        body.max_scenes if body.max_scenes is not None else "unlimited",
    )
    return {"message": "Processing started."}


@app.get("/status", summary="Get current pipeline status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """Return the current state of the captioning pipeline.

    Fields
    ------
    status : str
        One of ``"idle"``, ``"processing"``, ``"complete"``, ``"error"``.
    progress_pct : float
        Completion percentage (0.0 – 100.0).
    current_scene : int
        1-based index of the scene currently being captioned (0 when idle).
    total_scenes : int
        Total number of scenes detected in the video (0 until detection runs).
    results : list
        Accumulated list of ``caption_result`` payloads produced so far.
    error_message : str | None
        Set only when ``status == "error"``.
    """
    with _state_lock:
        return StatusResponse(
            status=_job_status,
            progress_pct=_progress_pct,
            current_scene=_current_scene,
            total_scenes=_total_scenes,
            results=list(_results),
            error_message=_error_message,
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Persistent WebSocket connection for real-time pipeline progress.

    The server broadcasts JSON messages to **all** connected clients whenever
    the pipeline emits an event.  No replay of past messages is sent to
    late-joining clients — connect before calling ``POST /process`` to
    receive the full stream.

    Message types
    -------------
    ``scene_detected``  — emitted once after scene detection finishes.
    ``captioning_start``— emitted before each scene's API call begins.
    ``caption_result``  — emitted after each scene's captions arrive.
    ``complete``        — emitted when the full pipeline finishes.
    ``error``           — emitted if a fatal pipeline error occurs.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive; the server is the sender here.
            # We still need to await to avoid blocking the event loop.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)
