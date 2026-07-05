# 1. Define the base operating system image first
FROM python:3.11-slim

# 2. Pull the high-speed uv installer tools into the container
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. Set your project work directory
WORKDIR /app

# 4. Copy requirements.txt by itself to protect the cache
COPY requirements.txt .

# 5. Run the high-speed parallel installer with cache mounting
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# 6. Copy the rest of your application code into the image
COPY . .

# 7. Define the default startup command
CMD ["python", "src/main.py"]
