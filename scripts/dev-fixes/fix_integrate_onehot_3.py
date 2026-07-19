import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

old_exclude = '''    exclude = set(EXCLUDE_ALWAYS + TARGET_COLUMNS + [GROUP_KEY, "timestamp"])
    exclude |= set(SPARSE_PRESENCE_COLUMNS)  # colonnes brutes remplacees par has_*
    exclude.discard("event_id")  # on garde event_id et sa version freq'''

new_exclude = '''    exclude = set(EXCLUDE_ALWAYS + TARGET_COLUMNS + [GROUP_KEY, "timestamp"])
    exclude |= set(SPARSE_PRESENCE_COLUMNS)  # colonnes brutes remplacees par has_*
    exclude.add("event_id")  # remplace par event_id_freq + one-hot eid_*'''

if old_exclude not in content:
    print("[ERREUR] Bloc exclude introuvable")
else:
    content = content.replace(old_exclude, new_exclude)
    path.write_text(content, encoding="utf-8")
    print("[OK] event_id brut exclu des features finales")
