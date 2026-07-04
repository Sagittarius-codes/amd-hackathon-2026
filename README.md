# Video Captioning Pipeline — AMD Developer Hackathon ACT II

> Track 2 — Video Captioning | Built with Python, OpenCV, and Fireworks AI

## What it does

This pipeline automatically generates natural-language captions for every scene in a video file. It extracts one frame every 2 seconds, sends each frame to a vision-capable AI model, and produces a timestamped caption file describing what is happening at each moment in the video.

**Example output from Karan Aujla's "Low Fade" music video:**
[00:00:00.000] The image is completely black.
[00:00:04.000] A black drift car is sliding across a track, kicking up a large cloud of tire smoke.
[00:00:08.000] A black sports car is drifting on a track, creating a large cloud of white tire smoke.

## How it works
Video file → Frame extraction (OpenCV) → Base64 encoding → Fireworks AI API → Timestamped captions → output/captions.txt

1. **video_utils.py** — opens the video, extracts one frame every 2 seconds using OpenCV, encodes each frame as a base64 JPEG for API transmission
2. **captioner.py** — sends each frame to the Fireworks AI API with a vision-capable model, returns a one-sentence caption per frame
3. **main.py** — orchestrates the pipeline, handles errors gracefully, writes results to `output/captions.txt`

## Tech stack

- **Python 3.11**
- **OpenCV** — video processing and frame extraction
- **Fireworks AI API** — vision-language model for captioning
- **python-dotenv** — secure API key management
- **Docker** — containerized for consistent deployment

## Project structure
amd-hackathon-2026/
├── source/
│   ├── main.py           # pipeline entry point
│   ├── captioner.py      # Fireworks AI API integration
│   └── video_utils.py    # video processing and frame extraction
├── input/
│   └── sample.mp4        # place your video file here
├── output/
│   └── captions.txt      # generated captions (auto-created)
├── tests/
│   └── test_captioner.py
├── .env                  # API keys (not committed)
├── .gitignore
├── Dockerfile
└── requirements.txt

## Setup and installation

### 1. Clone the repository

```bash
git clone https://github.com/Sagittarius-codes/amd-hackathon-2026.git
cd amd-hackathon-2026
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

Create a `.env` file in the project root:
FIREWORKS_API_KEY=your_fireworks_api_key_here

### 4. Add your video

Place any `.mp4` file in the `input/` folder and name it `sample.mp4`.

### 5. Run the pipeline

```bash
python source/main.py
```

Results are saved to `output/captions.txt` and printed to the terminal in real time.

## Run with Docker

```bash
docker build -t amd-hackathon .
docker run --env-file .env amd-hackathon
```

## Sample output
[00:00:00.000] The image is completely black.
[00:00:04.000] A black drift car is sliding across a track, kicking up a large cloud of tire smoke.
[00:00:08.000] A black sports car is drifting on a track, creating a large cloud of white tire smoke.
Done. 10/10 frames captioned successfully.

## Design decisions

- **Frame interval of 2 seconds** — balances caption granularity against API cost. Configurable via the `interval_seconds` parameter in `extract_frames()`.
- **JPEG quality 85** — high quality with reasonable payload size for API transmission. Configurable.
- **Graceful error handling** — if one frame fails (rate limit, corrupted frame), the pipeline logs the error, writes a placeholder, and continues to the next frame. One bad frame never kills the whole pipeline.
- **Separation of concerns** — video logic, API logic, and orchestration are in separate files. Swap the AI provider by changing one line in `captioner.py`.

## What I would improve with more time

- Add a simple web UI to upload videos and view captions in the browser
- Support batch processing of multiple video files
- Add subtitle file export (.srt format) alongside the plain text output
- Implement smarter rate limit handling using the `Retry-After` response header
- Add confidence scores to captions where the model supports it

## Author

Built by [@Sagittarius-codes](https://github.com/Sagittarius-codes) for the AMD Developer Hackathon ACT II — July 2026.