import re
from pathlib import Path

path = Path("src/ingestion/evtx_xml_parser.py")
content = path.read_text(encoding="utf-8")

old_block = '''    time_el = system.find("e:TimeCreated", NS)
    timestamp_raw = time_el.get("SystemTime") if time_el is not None else None
    if timestamp_raw is None:
        return None
    timestamp_clean = timestamp_raw.split(".")[0].split("+")[0].replace(" ", "T")'''

new_block = '''    time_el = system.find("e:TimeCreated", NS)
    timestamp_raw = time_el.get("SystemTime") if time_el is not None else None
    if timestamp_raw is None:
        return None

    ts_normalized = timestamp_raw.replace(" ", "T")
    try:
        dt = datetime.fromisoformat(ts_normalized)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        timestamp_clean = dt.isoformat()
    except ValueError:
        timestamp_clean = timestamp_raw.split(".")[0].split("+")[0].replace(" ", "T")'''

if old_block not in content:
    print("[ERREUR] Bloc original introuvable - le fichier a peut-etre deja ete modifie.")
    print("Verifie manuellement src/ingestion/evtx_xml_parser.py")
else:
    content = content.replace(old_block, new_block)
    # Ajouter les imports necessaires en haut du fichier si absents
    if "from datetime import datetime, timezone" not in content:
        content = content.replace(
            "import sys\nfrom pathlib import Path",
            "import sys\nfrom pathlib import Path\nfrom datetime import datetime, timezone",
            1
        )
    path.write_text(content, encoding="utf-8")
    print("[OK] Fix timezone applique dans evtx_xml_parser.py")
