FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN python -m pip install --require-hashes -r requirements.lock

COPY src ./src
COPY services/api ./services/api
COPY demo ./demo
RUN python -m pip install --no-deps --no-build-isolation . \
    && addgroup --system framefoley \
    && adduser --system --ingroup framefoley framefoley \
    && mkdir -p /app/.data \
    && chown -R framefoley:framefoley /app/.data

USER framefoley
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=3)"
CMD ["uvicorn", "framefoley_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
