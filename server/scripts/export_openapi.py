from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.main import app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI schema.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi.json"),
        help="Path where the OpenAPI JSON document should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
