# CaptionAI — AMD Developer Hackathon ACT II · Track 2

> **AI-powered video captioning pipeline with 4 distinct caption styles, real-time WebSocket updates, and a full modern React GUI.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-blueviolet)](https://glorious-beauty-production-a674.up.railway.app)
[![Backend API](https://img.shields.io/badge/Backend%20API-Railway-blue)](https://amd-hackathon-2026-production.up.railway.app)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev)

---

## What It Does

CaptionAI takes any video file, automatically detects scene boundaries, extracts a representative frame per scene, and generates captions in **4 distinct styles** using a cutting-edge multimodal AI model — all in real time, streamed live to the browser via WebSockets.

### Caption Styles

| Style | Description |
|---|---|
| **Formal** | Professional, neutral description suitable for accessibility or documentation |
| **Sarcastic** | Dry, deadpan commentary on the scene |
| **Humorous (Tech)** | Jokes and references aimed at software developers |
| **Humorous (Non-Tech)** | Everyday humor accessible to any audience |

---

## Architecture

```
Browser (React + Vite)
    │
    ├── POST /upload        → uploads video file
    ├── POST /process       → starts pipeline
    ├── POST /stop          → aborts running pipeline
    └── WS  /ws             → receives real-time scene + caption events
                                        │
                            FastAPI Backend (uvicorn)
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
            PySceneDetect          OpenCV             Fireworks API
          (scene detection)    (frame extraction)    (Multimodal LLM)
                                                    model: minimax-m3
```

### Pipeline Flow

1. Video uploaded via drag-and-drop → saved to `/app/input/`
2. PySceneDetect splits video into scenes by detecting visual cuts
3. OpenCV extracts one representative frame per scene
4. Frames are sent sequentially to Fireworks AI (MiniMax M3), which analyzes the image and returns all 4 caption styles in a single JSON block.
5. Captions stream back to the browser via WebSocket as they complete.
6. The user can abort the pipeline safely at any time via the "Stop Pipeline" feature.

---

## Tech Stack

### Backend
- **Python 3.11**
- **FastAPI** — REST API + WebSocket server
- **uvicorn** — ASGI server
- **PySceneDetect** — scene boundary detection
- **OpenCV** (`opencv-python-headless`) — frame extraction
- **Fireworks API** — High-performance multimodal AI access (MiniMax M3)
- **python-dotenv** — environment variable management

### Frontend
- **React 18** + **Vite**
- **Tailwind CSS** — Modern, glassmorphic UI design
- **axios** — HTTP requests
- **lucide-react** — icons
- **WebSocket (native)** — real-time pipeline updates
- **nginx** — serves static build in production

### Infrastructure
- **Docker** + **Docker Compose** — local development
- **Railway.app** — production deployment
  - Backend service: FastAPI on port 8000
  - Frontend service: nginx on port 80

---

## Project Structure

```
amd-hackathon-2026/
│
├── app/
│   └── api.py                  # FastAPI app — REST + WebSocket + Threaded pipeline worker
│
├── source/
│   ├── captioner.py            # Fireworks AI multimodal client — JSON output processing
│   ├── video_utils.py          # PySceneDetect + OpenCV frame extraction
│   └── main.py                 # CLI entry point for standalone runs
│
├── frontend/
│   ├── Dockerfile              # Multi-stage: Node builds, nginx serves
│   ├── nginx.conf              # Static nginx config (port 80, SPA routing)
│   ├── package.json
│   └── src/
│       ├── App.jsx             # Root layout, dark mode, WebSocket wiring
│       ├── hooks/
│       │   └── useWebSocket.js # WS connection, all pipeline event handlers
│       └── components/
│           ├── Dashboard.jsx       # Main pipeline tracking and UI grid
│           ├── SceneCard.jsx       # Premium glassmorphic card for 4 style tabs
│           ├── LeftPanel.jsx       # Progress ring, global stats, and Stop UI
│           └── SceneTimeline.jsx   # Visual horizontal progress indicator
│
├── tests/
│   └── test_captioner.py
│
├── Dockerfile.backend          # Railway-compatible FastAPI container
├── docker-compose.yml          # Local two-service stack
├── requirements.txt
└── .env.example
```

---

## API Reference

### REST Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Upload a video file. Returns `{ filename, size }` |
| `POST` | `/process` | Start the captioning pipeline. Body: `{ max_scenes?: int }` |
| `POST` | `/stop`    | Abort the currently running pipeline |
| `GET` | `/status` | Retrieve current status and progress |
| `GET` | `/health` | Health check. Returns `{ status: "ok" }` |

### WebSocket

**Connect:** `ws://<host>/ws`

**Events received (server → client):**

| Event | Payload | Description |
|---|---|---|
| `connected` | `{ message }` | WS handshake confirmed |
| `scenes_detected` | `{ count }` | Total scenes found |
| `scene_start` | `{ scene_index }` | Scene captioning started |
| `caption_result`| `{ scene_index, result }` | Processed captions for a single scene |
| `stopped` | `{ summary }` | Pipeline safely aborted by user |
| `complete` | `{ summary }` | All scenes captioned successfully |
| `error` | `{ message }` | Pipeline error |

---

## Local Development

### Prerequisites

- Docker Desktop
- A Fireworks AI API key (get one at [fireworks.ai](https://fireworks.ai))

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/Sagittarius-codes/amd-hackathon-2026.git
cd amd-hackathon-2026

# 2. Create your .env file
cp .env.example .env
# Add your key:  FIREWORKS_API_KEY=your_key_here

# 3. Start both services
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Without Docker

```bash
# Backend
pip install -r requirements.txt
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Production Deployment (Railway)

Both services are deployed independently on Railway, connected via environment variables.

### Environment Variables

**Backend service:**

| Variable | Description |
|---|---|
| `FIREWORKS_API_KEY` | Your Fireworks AI API key |
| `PORT` | `8000` |

**Frontend service (build arg):**

| Variable | Description |
|---|---|
| `VITE_API_URL` | Full public URL of the backend, e.g. `https://amd-hackathon-2026-production.up.railway.app` |

### Deploying Updates

```bash
git add .
git commit -m "your message"
git push
# Railway auto-redeploys on push
```

---

## Built By

**Sagittarius Codes**
AMD Developer Hackathon ACT II · 2026