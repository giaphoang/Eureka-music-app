#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3.10 was not found at: $PYTHON_BIN"
  echo "Install the Python 3.10.11 macOS universal2 package, or run:"
  echo "  PYTHON_BIN=/path/to/python3.10 ./scripts/bootstrap_macos.sh"
  exit 1
fi

if [[ "$(uname -m)" == "arm64" ]]; then
  if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
    echo "Rosetta is required for the Intel-only PySide2 wheel."
    echo "Install Rosetta by opening an Intel app or using macOS Software Update."
    exit 1
  fi
  arch -x86_64 "$PYTHON_BIN" -m venv .venv
else
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt
python - <<'PY'
import platform
import PySide2
print("Python architecture:", platform.machine())
print("PySide2 version:", PySide2.__version__)
PY

echo "Client environment is ready. Run:"
echo "  source .venv/bin/activate"
echo "  python -m eureka_client.app"
