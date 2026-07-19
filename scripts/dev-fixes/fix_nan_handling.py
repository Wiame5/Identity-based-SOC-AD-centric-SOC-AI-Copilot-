import re
from pathlib import Path

path = Path("src/copilot/model_inference.py")
content = path.read_text(encoding="utf-8")

old_line = '''        for col in self.sparse_cols:
            row[f"has_{col}"] = int(event.get(col) not in (None, ""))'''

new_line = '''        import math

        def is_missing(v):
            if v is None:
                return True
            if isinstance(v, str) and v == "":
                return True
            if isinstance(v, float) and math.isnan(v):
                return True
            return False

        for col in self.sparse_cols:
            row[f"has_{col}"] = int(not is_missing(event.get(col)))'''

if old_line not in content:
    print("[ERREUR] Bloc introuvable")
else:
    content = content.replace(old_line, new_line)
    path.write_text(content, encoding="utf-8")
    print("[OK] Fix NaN handling applique dans model_inference.py")
