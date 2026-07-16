# Server

## Run

From the repository root:

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

Open API docs at `http://localhost:8000/docs`.

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
