#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

case "$(uname -m)" in
  aarch64|arm64) ;;
  *)
    echo "This bootstrap is for Ubuntu ARM64 (aarch64), not $(uname -m)." >&2
    echo "On x86_64, create .venv normally and install requirements.txt." >&2
    exit 1
    ;;
esac

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get was not found; this script requires Ubuntu." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  python3.10 python3.10-venv \
  python3-pyside2.qtwidgets python3-pyside2.qtmultimedia \
  libgl1 libxkbcommon-x11-0 libxcb-xinerama0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-ugly gstreamer1.0-libav

python3.10 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements-common.txt

python - <<'PY'
import platform

import PySide2
from PySide2 import QtMultimedia, QtWidgets

print("Python architecture:", platform.machine())
print("PySide2 version:", PySide2.__version__)
print("QtWidgets:", QtWidgets.__name__)
print("QtMultimedia:", QtMultimedia.__name__)
PY

echo "Client environment is ready. Run:"
echo "  source .venv/bin/activate"
echo "  python -m eureka_client.app"
