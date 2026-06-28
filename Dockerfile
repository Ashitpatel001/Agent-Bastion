# ============================================================
# ABSs v2.0 — Multi-Tenant AI Browser Security Proxy
# Production Dockerfile
# ============================================================

##############################
# Base Image
##############################
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git \
        curl \
        wget \
        tini \
        libpq-dev \
        libnss3 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        libdrm2 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libxshmfence1 \
        libxcomposite1 \
        libxfixes3 \
        libx11-xcb1 \
        libxcb1 \
        libxext6 \
        libxrender1 \
        fonts-liberation \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r abs && \
    useradd -r -g abs -m abs

WORKDIR /app

##############################
# Dependencies
##############################
FROM base AS deps

COPY pyproject.toml README.md ./

RUN python -m pip install --upgrade pip setuptools wheel

COPY --chown=abs:abs . .

RUN pip install .

RUN python -m playwright install chromium

RUN mkdir -p \
    logs \
    src/security/dashboard/screenshots \
    src/security/dashboard/diffs && \
    chown -R abs:abs logs src/security/dashboard

##############################
# API
##############################
FROM deps AS api

USER abs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
CMD curl -fs http://localhost:8000/health || exit 1

ENTRYPOINT ["tini","--"]

CMD ["uvicorn","src.api.main:app","--host","0.0.0.0","--port","8000","--workers","2"]

##############################
# Agent Worker
##############################
FROM deps AS worker-agent

USER abs

ENTRYPOINT ["tini","--"]

CMD ["celery","-A","src.workers.celery_app","worker","-Q","agents","--loglevel=info","--concurrency=1"]

##############################
# XAI Worker
##############################
FROM deps AS worker-xai

USER abs

ENTRYPOINT ["tini","--"]

CMD ["celery","-A","src.workers.celery_app","worker","-Q","xai","--loglevel=info","--concurrency=4"]

##############################
# Dashboard
##############################
FROM deps AS dashboard

USER abs

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
CMD curl -fs http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["tini","--"]

CMD ["streamlit","run","src/security/dashboard_app.py","--server.address=0.0.0.0","--server.port=8501","--server.headless=true","--browser.gatherUsageStats=false"]

##############################
# Flower
##############################
FROM deps AS flower

RUN pip install flower

USER abs

EXPOSE 5555

ENTRYPOINT ["tini","--"]

CMD ["celery","-A","src.workers.celery_app","flower","--port=5555","--persistent=True"]