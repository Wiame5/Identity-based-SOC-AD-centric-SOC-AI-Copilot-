from __future__ import annotations

import json
import sys
from pathlib import Path

from src.ingestion.schema import NormalizedEvent


def parse_benign_file(filepath):
    path = Path(filepath)
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                yield NormalizedEvent(**obj)
            except Exception as exc:
                print(f"[WARN] Ligne benign ignoree ({path.name}): {exc}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.ingestion.benign_parser <benign.json>")
        sys.exit(1)

    events = list(parse_benign_file(sys.argv[1]))
    print(f"{len(events)} evenements benins normalises depuis {sys.argv[1]}")
    if events:
        print("Exemple:", events[0].model_dump_json(indent=2)[:600])
