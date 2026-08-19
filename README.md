# Eureka Music App

> **Recommended environment (especially on Apple Silicon)**
>
> Ubuntu 22.04 **ARM64** in a UTM **Virtualize** VM, with 8 GB RAM and a
> 40 GB disk recommended. Use Python 3.10, Docker Engine, and Ubuntu's native
> PySide2 5.15.2 packages. These memory and disk sizes are practical
> recommendations for Docker and CLAP, not hard minimums.
>
> If an exact PyPI `PySide2==5.15.2.1` wheel is required, use Ubuntu 22.04
> x86_64 in UTM **Emulate** mode instead. UTM can virtualize a guest only when
> its architecture matches the host; x86_64 on Apple Silicon is emulated.

Eureka is an Ubuntu music-management application with a FastAPI/PostgreSQL
server and a PySide2 desktop client. It supports catalog search, downloads,
uploads, local playlists, playback, and optional CLAP prompt-to-playlist
recommendations.

## Quick path

1. Create an Ubuntu 22.04 ARM64 VM (8 GB RAM / 40 GB disk recommended).
2. Copy this repository onto the VM's local filesystem.
3. Install Docker Engine from Docker's official apt repository.
4. Mount the FMA dataset at `/mnt/utm-share/FMA`.
5. Run `cd client && ./scripts/bootstrap_ubuntu_arm64.sh`.
6. Run `docker compose up --build -d` from the repository root.
7. Seed 1,000 tracks.
8. Run `python -m eureka_client.app` from the activated client environment.
9. Optionally configure AI Playlist only after the basic application works.

## 1. Create and check the Ubuntu VM

On an Apple Silicon Mac, create an **Ubuntu 22.04 ARM64** VM in UTM using
**Virtualize**, not Emulate. Before downloading datasets or building images,
run:

```bash
uname -m
python3.10 --version
free -h
df -h /
docker --version
docker compose version
```

A recommended setup reports `aarch64`, Python 3.10, working Docker and Compose,
about 8 GB RAM, and ample free space on a roughly 40 GB disk. Stop and enlarge
the VM disk before continuing if space is tight.

### Keep the repository on the Linux filesystem

**Do not create `.venv` or run Docker from a SPICE WebDAV/GVFS folder.** GVFS
can prevent Python from creating the `lib64 -> lib` symlink and is not visible
to root-owned Docker processes. Copy or clone the repository locally:

```bash
mkdir -p ~/eureka-workspace
cp -a /path/to/shared/Eureka-music-app ~/eureka-workspace/eureka-music-starter
cd ~/eureka-workspace/eureka-music-starter
```

Keep only the large, read-only FMA source dataset in the host share.

## 2. Install official Docker Engine

Use Docker's official Ubuntu apt repository rather than Snap Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in (or reboot) so the group change takes effect, then confirm
`docker run --rm hello-world` works without `sudo`.

## 3. Mount FMA from the host

Download and unzip `fma_metadata.zip` and `fma_small.zip` from the
[FMA project](https://github.com/mdeff/fma). The directory passed to the seed
scripts must be their parent and contain:

```text
FMA/
├── fma_metadata/tracks.csv
└── fma_small/000/000002.mp3
```

Prefer a UTM **VirtFS/virtiofs** share for Linux and mount its `share` tag at a
normal path:

```bash
sudo mkdir -p /mnt/utm-share
sudo mount -t virtiofs share /mnt/utm-share
```

If VirtFS is unavailable, use the SPICE WebDAV endpoint as a fallback (the
repository itself must still remain outside this mount):

```bash
sudo apt install -y davfs2
sudo mkdir -p /mnt/utm-share
sudo mount -t davfs http://127.0.0.1:9843/ /mnt/utm-share
```

Confirm `/mnt/utm-share/FMA/fma_metadata/tracks.csv` and `fma_small/` exist.
Treat this source directory as read-only.

## 4. Bootstrap the desktop client

Ubuntu 22.04 supplies native ARM64 PySide2 5.15.2, including QtWidgets and
QtMultimedia. The bootstrap installs those packages and GStreamer, creates a
virtual environment with `--system-site-packages`, and installs the common
Python dependencies:

```bash
cd ~/eureka-workspace/eureka-music-starter/client
./scripts/bootstrap_ubuntu_arm64.sh
source .venv/bin/activate
```

For Ubuntu x86_64, create a conventional environment and install the exact
PyPI pin instead:

```bash
cd client
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt
```

## 5. Start and seed the basic application

Start the API and PostgreSQL first:

```bash
cd ~/eureka-workspace/eureka-music-starter
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/health
```

The expected response is `{"status":"ok"}`. Seed **1,000 tracks** for normal
VM development. `--copy` is required because hard links cannot cross from the
shared mount into Docker's audio volume:

```bash
docker compose run --rm \
  -v /mnt/utm-share/FMA:/dataset/fma:ro \
  api python -m scripts.seed_fma /dataset/fma --copy --limit 1000

curl 'http://localhost:8000/api/v1/tracks?limit=3'
```

For a very quick smoke test, use `--limit 100`. Seeding all approximately 8,000
FMA Small tracks is optional; only after the smaller seed succeeds, rerun the
same idempotent command without `--limit`.

Launch the client:

```bash
cd client
source .venv/bin/activate
export EUREKA_API_URL=http://localhost:8000
python -m eureka_client.app
```

Verify catalog search, download and playback before proceeding. API docs are at
`http://localhost:8000/docs`.

## 6. Optional: AI Playlist

The basic client, API, PostgreSQL, and seeded catalog do **not** require PyTorch,
FAISS, LAION CLAP, or its model. Configure recommendations only after the basic
application works. The music checkpoint is roughly **2.35 GB**, and the
recommendation-enabled Docker image requires considerably more disk than the
basic API image.

Download and verify the checkpoint on Ubuntu:

```bash
mkdir -p models
curl -L --fail \
  -o models/music_audioset_epoch_15_esc_90.14.pt \
  https://huggingface.co/lukewys/laion_clap/resolve/main/music_audioset_epoch_15_esc_90.14.pt
echo "fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd  models/music_audioset_epoch_15_esc_90.14.pt" \
  | sha256sum -c -

INSTALL_RECOMMENDATION_DEPS=true \
INSTALL_LAION_CLAP_DEPS=true \
docker compose build api
```

Use conservative ARM VM settings. First build a 10-track smoke index:

```bash
docker compose run --rm \
  -v /mnt/utm-share/FMA:/dataset/fma:ro \
  api python -m scripts.build_recommendation_index \
    /dataset/fma \
    --output-dir /app/data/recommendation \
    --backend laion \
    --checkpoint /models/music_audioset_epoch_15_esc_90.14.pt \
    --audio-model HTSAT-base \
    --threads 1 \
    --batch-size 1 \
    --limit 10
```

When that succeeds, repeat with `--limit 1000`, then validate and enable it:

```bash
docker compose run --rm api \
  python -m scripts.validate_recommendation_index /app/data/recommendation

EUREKA_RECOMMENDATION_ENABLED=true \
EUREKA_CLAP_BACKEND=laion \
EUREKA_CLAP_CHECKPOINT=/models/music_audioset_epoch_15_esc_90.14.pt \
INSTALL_RECOMMENDATION_DEPS=true \
INSTALL_LAION_CLAP_DEPS=true \
docker compose up --build -d
```

See `server/README.md` for backend trade-offs and status/request examples.

## Development and verification

```bash
python -m pip install -r requirements-dev.txt
make lint
make type-check
make test
make api-docs
```

The UI refactor evidence is under `docs/ui-refactor/`. Detailed architecture is
in `DESIGN.md`; component-specific instructions are in `client/README.md` and
`server/README.md`.

## Troubleshooting and recovery

### A larger UTM disk still shows a small `/`

Increasing the virtual disk does not necessarily extend partitions, LVM, and
the filesystem. Back up important data, inspect names with `lsblk`, and replace
the example device and logical-volume paths below with the observed ones:

```bash
sudo growpart /dev/vda 3
sudo pvresize /dev/vda3
sudo lvextend -r -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
df -h /
```

Do not paste these storage commands blindly: device names and layouts vary.

### Reset local server state

> **DESTRUCTIVE:** `docker compose down -v` deletes the PostgreSQL and audio
> volumes, including every seeded and uploaded song, as well as recommendation
> artifacts. Use `docker compose down` without `-v` for an ordinary stop.
