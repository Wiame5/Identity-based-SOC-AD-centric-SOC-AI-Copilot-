import re
from pathlib import Path

path = Path("src/ingestion/schema.py")
content = path.read_text(encoding="utf-8")

old_formats = '''            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
            ):'''

new_formats = '''            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
            ):'''

if old_formats not in content:
    print("[ERREUR] Bloc de formats introuvable dans schema.py")
    print("Contenu actuel autour de _coerce_timestamp:")
    idx = content.find("_coerce_timestamp")
    print(content[idx:idx+600])
else:
    content = content.replace(old_formats, new_formats)
    path.write_text(content, encoding="utf-8")
    print("[OK] Format microsecondes ajoute dans schema.py")
