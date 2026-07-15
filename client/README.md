# Desktop client

## Important for Apple Silicon Macs

PySide2 5.15.2.1 only publishes an Intel macOS wheel. Use Python 3.10 in an x86_64/Rosetta shell. The server may continue running natively in Docker Desktop.

Install the official Python 3.10.11 **macOS universal2** package. Its default binary is:

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10
```

Then verify the Intel side of the universal binary:


```bash
PY310=/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10
arch -x86_64 "$PY310" -c 'import platform; print(platform.machine())'
# Expected: x86_64
```

Create and run the client environment:

```bash
cd client
./scripts/bootstrap_macos.sh
./scripts/run_macos.sh
```

For an Intel Mac, the same scripts create a normal native environment. To use a different Python 3.10 binary:

```bash
PYTHON_BIN=/path/to/python3.10 ./scripts/bootstrap_macos.sh
```

Optional settings:

```bash
export EUREKA_API_URL=http://localhost:8000
export EUREKA_DATA_DIR="$PWD/.local-data"
```

## Seed the local store

```bash
python scripts/seed_fma.py "$HOME/data/fma" --limit 100
```

Remove `--limit 100` to seed all 8,000 tracks.

## Ubuntu 22.04 verification

```bash
sudo apt update
sudo apt install -y python3.10-venv libgl1 libxkbcommon-x11-0 libxcb-xinerama0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m eureka_client.app
```
