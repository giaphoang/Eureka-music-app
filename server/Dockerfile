FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-recommendation.txt .
COPY requirements-recommendation-laion.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

ARG INSTALL_RECOMMENDATION_DEPS=false
ARG INSTALL_LAION_CLAP_DEPS=false
RUN if [ "$INSTALL_RECOMMENDATION_DEPS" = "true" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu torch && \
      pip install -r requirements-recommendation.txt ; \
    fi
RUN if [ "$INSTALL_LAION_CLAP_DEPS" = "true" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu torchaudio torchvision && \
      pip install -r requirements-recommendation-laion.txt ; \
    fi

COPY app ./app
COPY scripts ./scripts
COPY tests ./tests

RUN mkdir -p /data/audio

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
