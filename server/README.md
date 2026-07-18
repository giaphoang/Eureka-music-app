# Server

## Run

From the repository root:

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

Open API docs at `http://localhost:8000/docs`.

Recommendation artifacts and model caches are not committed. Normal server startup keeps
recommendations disabled unless `EUREKA_RECOMMENDATION_ENABLED=true` is set.

To build an API image with CPU recommendation dependencies:

```bash
INSTALL_RECOMMENDATION_DEPS=true docker compose build api
```

## Seed FMA

The seed command needs access to the unzipped dataset. Mount it read-only into a one-off API container:

```bash
docker compose run --rm \
  -v "$HOME/data/fma:/fma:ro" \
  api python scripts/seed_fma.py /fma --limit 100
```

Remove `--limit 100` for all 8,000 tracks.

## Verify

```bash
curl 'http://localhost:8000/api/v1/tracks?limit=5'
docker compose logs -f api
```

Run server tests from the repository root:

```bash
docker compose run --rm api python -m pytest -q
```

## CPU CLAP recommendations

The default recommendation backend uses the larger LAION music-specialized CLAP
checkpoint on CPU:

```text
models/music_audioset_epoch_15_esc_90.14.pt
```

Download the music checkpoint from the
[LAION CLAP checkpoint repository](https://huggingface.co/lukewys/laion_clap)
and keep it outside Git:

```bash
mkdir -p models
curl -L --fail \
  -o models/music_audioset_epoch_15_esc_90.14.pt \
  https://huggingface.co/lukewys/laion_clap/resolve/main/music_audioset_epoch_15_esc_90.14.pt

echo "fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd  models/music_audioset_epoch_15_esc_90.14.pt" \
  | shasum -a 256 -c -
```

The [LAION CLAP project](https://github.com/LAION-AI/CLAP) documents this
checkpoint as the music model and loads it with
`CLAP_Module(enable_fusion=False, amodel="HTSAT-base")` plus
`model.load_ckpt("checkpoint_path")`.

Build the API image with recommendation dependencies and the optional LAION CLAP
layer:

```bash
INSTALL_RECOMMENDATION_DEPS=true \
INSTALL_LAION_CLAP_DEPS=true \
docker compose build api
```

Build a 100-track development index with the same LAION checkpoint used at
runtime:

```bash
docker compose run --rm \
  -v "$HOME/data/fma:/dataset/fma:ro" \
  api python -m scripts.build_recommendation_index \
    /dataset/fma \
    --output-dir /app/data/recommendation \
    --backend laion \
    --checkpoint /models/music_audioset_epoch_15_esc_90.14.pt \
    --audio-model HTSAT-base \
    --threads 4 \
    --batch-size 1 \
    --limit 100
```

Build the full FMA Small index by omitting `--limit 100`.

Validate the currently published artifact without loading CLAP:

```bash
docker compose run --rm api python -m scripts.validate_recommendation_index /app/data/recommendation
```

Enable the API after artifacts are present:

```bash
EUREKA_RECOMMENDATION_ENABLED=true \
EUREKA_CLAP_BACKEND=laion \
EUREKA_CLAP_CHECKPOINT=/models/music_audioset_epoch_15_esc_90.14.pt \
INSTALL_RECOMMENDATION_DEPS=true \
INSTALL_LAION_CLAP_DEPS=true \
docker compose up --build -d
```

Status and request examples:

```bash
curl http://localhost:8000/api/v1/recommendations/status
curl -X POST http://localhost:8000/api/v1/recommendations/playlists \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Dreamy electronic music for late-night coding","size":10}'
```

The first playlist request may be slower because CLAP loads lazily. Missing model
cache, missing artifacts, corrupt artifacts, stale catalog rows, or a configured
model that does not match the artifact manifest return recoverable 503 errors.

Do not mix CLAP models. Use the same `--backend` and model ID for offline audio
indexing and runtime prompt encoding. Switching from `laion` to `hf`, changing
`--hf-model-id`, or changing a checkpoint requires rebuilding all audio
embeddings and the FAISS index.

### CLAP backend tradeoff

The LAION checkpoint path is heavier infrastructure: the checkpoint is about
2.35 GB, the Docker image needs the optional `laion-clap` stack, and Docker memory
should be high enough to load the model. The benefit is recommendation quality:
this checkpoint is music-specialized and performed better on abstract playlist
prompts in this project.

The Hugging Face `laion/clap-htsat-unfused` option is lighter infrastructure: the
model repository is roughly 618 MB, setup is simpler, and CPU loading is more
manageable. The tradeoff is quality: it is a general audio CLAP model, so music
prompt relevance can be weaker.

### Optional Hugging Face CLAP backend

To use the smaller Hugging Face backend instead, build the base recommendation
dependencies:

```bash
INSTALL_RECOMMENDATION_DEPS=true docker compose build api
```

Optionally pre-download the Hugging Face model cache with the CLI:

```bash
docker compose run --rm api \
  huggingface-cli download laion/clap-htsat-unfused \
  --cache-dir /hf-cache
```

Build an HF index:

```bash
docker compose run --rm \
  -v "$HOME/data/fma:/dataset/fma:ro" \
  api python -m scripts.build_recommendation_index \
    /dataset/fma \
    --output-dir /app/data/recommendation \
    --backend hf \
    --hf-model-id laion/clap-htsat-unfused \
    --hf-cache-dir /hf-cache \
    --threads 4 \
    --batch-size 1
```

Run the API against an HF-built index by also setting:

```bash
EUREKA_CLAP_BACKEND=hf
EUREKA_HF_CLAP_MODEL_ID=laion/clap-htsat-unfused
EUREKA_HF_CLAP_CACHE_DIR=/hf-cache
```
