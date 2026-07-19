import re
from pathlib import Path

path = Path("src/modeling/train_hierarchical.py")
content = path.read_text(encoding="utf-8")

old_line = 'def train_stage1(df_train, feature_cols, class_weight="balanced"):'
new_line = 'def train_stage1(df_train, feature_cols, class_weight=None):'

if old_line not in content:
    print("[ERREUR] Ligne introuvable")
else:
    content = content.replace(old_line, new_line)
    path.write_text(content, encoding="utf-8")
    print("[OK] class_weight par defaut passe a None")
