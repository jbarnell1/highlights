# Highlights: the PWA, the worker, ffmpeg with Intel Quick Sync and the Claude Code CLI.
#   docker build -t highlights .
# ffmpeg comes from Jellyfin's build (jellyfin-ffmpeg): it carries Quick Sync, the Intel media
# driver, zscale and tonemap, which the HDR-to-SDR step needs. Without a GPU it falls back to
# libx264 on the CPU.
FROM python:3.12-slim-bookworm

ARG CLAUDE_CODE_VERSION=stable
ARG UV_VERSION=0.11.2

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg fonts-dejavu-core \
 && curl -fsSL https://repo.jellyfin.org/jellyfin_team.gpg.key \
      | gpg --dearmor -o /usr/share/keyrings/jellyfin.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/jellyfin.gpg] https://repo.jellyfin.org/debian bookworm main" \
      > /etc/apt/sources.list.d/jellyfin.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends jellyfin-ffmpeg7 \
 && rm -rf /var/lib/apt/lists/*

# Claude Code, used in print mode to pick moments. The installer puts a versioned binary under
# the build user's home; copy the real file out so it does not depend on that home.
RUN curl -fsSL https://claude.ai/install.sh | bash -s -- "$CLAUDE_CODE_VERSION" \
 && cp "$(readlink -f /root/.local/bin/claude)" /usr/local/bin/claude \
 && rm -rf /root/.local /root/.claude* \
 && claude --version

RUN pip install --no-cache-dir "uv==$UV_VERSION"

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 1000 highlights
USER highlights

ENV PATH="/app/.venv/bin:$PATH" \
    HL_FFMPEG_DIR=/usr/lib/jellyfin-ffmpeg \
    HL_DATA_DIR=/data \
    HL_HOST=0.0.0.0 \
    HL_ENV_FILE=/nonexistent \
    DISABLE_AUTOUPDATER=1 \
    PYTHONUNBUFFERED=1

VOLUME /data
EXPOSE 8040
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8040/api/status', timeout=4)"
CMD ["hl", "serve", "--port", "8040"]
