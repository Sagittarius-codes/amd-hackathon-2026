# CaptionAI — AMD Developer Hackathon ACT II · Track 2

> **AI-powered video captioning pipeline with 4 distinct caption styles, real-time WebSocket updates, and a full React GUI.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway-blueviolet)](https://glorious-beauty-production-a674.up.railway.app)
[![Backend API](https://img.shields.io/badge/Backend%20API-Railway-blue)](https://amd-hackathon-2026-production.up.railway.app)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev)

---

## What It Does

CaptionAI takes any video file, automatically detects scene boundaries, extracts a representative frame per scene, and generates captions in **4 distinct styles** using a large language model — all in real time, streamed live to the browser via WebSockets.

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
    └── WS  /ws             → receives real-time scene + caption events
                                        │
                            FastAPI Backend (uvicorn)
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
            PySceneDetect          OpenCV               OpenRouter API
          (scene detection)    (frame extraction)     (LLM captioning)
                                                    model: gemma-4-26b-a4b-it
```

### Pipeline Flow

1. Video uploaded via drag-and-drop → saved to `/app/input/`
2. PySceneDetect splits video into scenes by detecting visual cuts
3. OpenCV extracts one representative frame per scene
4. Each frame is sent concurrently to the LLM with 4 style prompts
5. Captions stream back to the browser via WebSocket as they complete
6. Results saved to `/app/output/captions.txt`

---

## Tech Stack

### Backend
- **Python 3.11**
- **FastAPI** — REST API + WebSocket server
- **uvicorn** — ASGI server
- **PySceneDetect** — scene boundary detection
- **OpenCV** (`opencv-python-headless`) — frame extraction
- **OpenRouter API** — LLM access (switching to Fireworks July 7th)
- **python-dotenv** — environment variable management

### Frontend
- **React 18** + **Vite**
- **axios** — HTTP requests
- **lucide-react** — icons
- **recharts** — data visualization
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
│   └── api.py                  # FastAPI app — all routes + WebSocket + pipeline worker
│
├── source/
│   ├── captioner.py            # OpenRouter API client — 4 styles, concurrent requests
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
│           ├── VideoUpload.jsx     # Drag-and-drop upload → POST /upload
│           ├── ProcessControls.jsx # Run button, max scenes → POST /process
│           ├── ProgressPanel.jsx   # Circular progress ring
│           ├── Timeline.jsx        # Horizontal scene timeline bar
│           ├── SceneCard.jsx       # Per-scene caption card (4 style tabs)
│           └── StatusBar.jsx       # Bottom status + elapsed timer
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
| `GET` | `/health` | Health check. Returns `{ status: "ok" }` |

### WebSocket

**Connect:** `ws://<host>/ws`

**Events received (server → client):**

| Event | Payload | Description |
|---|---|---|
| `connected` | `{ message }` | WS handshake confirmed |
| `scenes_detected` | `{ count }` | Total scenes found |
| `scene_start` | `{ scene_index }` | Scene captioning started |
| `caption_ready` | `{ scene_index, style, caption }` | One caption style complete |
| `scene_complete` | `{ scene_index }` | All 4 styles done for a scene |
| `pipeline_complete` | `{ total_scenes }` | All scenes captioned |
| `error` | `{ message }` | Pipeline error |

---

## Local Development

### Prerequisites

- Docker Desktop
- An OpenRouter API key (free tier available at [openrouter.ai](https://openrouter.ai))

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/Sagittarius-codes/amd-hackathon-2026.git
cd amd-hackathon-2026

# 2. Create your .env file
cp .env.example .env
# Add your key:  OPENROUTER_API_KEY=sk-or-...

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
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
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

## Switching to Fireworks (July 7th)

When Fireworks credits activate, update `source/captioner.py`:

```python
# Replace OpenRouter config with:
API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
API_KEY = os.environ.get("FIREWORKS_API_KEY")
MODEL   = "accounts/fireworks/models/..."  # your chosen model
```

Then add `FIREWORKS_API_KEY` to the Railway backend service variables and push.

---

## Known Limitations

- **Free tier rate limits** on OpenRouter may cause `[no caption]` on some scenes — resolved with Fireworks credits
- **0.5 GB RAM** on Railway free tier — keep test videos under ~30 MB for reliable processing
- Uploaded videos are stored ephemerally on Railway — they do not persist across restarts
- Scene thumbnails are not yet exposed via API — coming in next iteration

---

## Hackathon Submission

- **Track:** AMD Developer Hackathon ACT II — Track 2 (Video Captioning)
- **Deadline:** July 11, 2026 on [lablab.ai](https://lablab.ai)
- **Live URL:** https://glorious-beauty-production-a674.up.railway.app
- **GitHub:** https://github.com/Sagittarius-codes/amd-hackathon-2026

---

## Built By

**Sagittarius Codes**
AMD Developer Hackathon ACT II · 2026