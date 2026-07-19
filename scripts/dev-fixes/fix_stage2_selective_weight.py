import re
from pathlib import Path

path = Path("src/modeling/train_hierarchical.py")
content = path.read_text(encoding="utf-8")

old_block = '''def train_stage2(df_train, feature_cols):'''

new_block = '''def train_stage2(df_train, feature_cols, class_weight_stage2="balanced_subsample"):'''

content = content.replace(old_block, new_block)

old_clf = '''        clf = RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X, y)
        stage2_models[tactic] = {"type": "model", "value": clf}'''

new_clf = '''        weight = class_weight_stage2 if tactic == "TA0006" else None
        clf = RandomForestClassifier(
            n_estimators=200,
            class_weight=weight,
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X, y)
        stage2_models[tactic] = {"type": "model", "value": clf}'''

if old_clf not in content:
    print("[ERREUR] Bloc clf introuvable")
else:
    content = content.replace(old_clf, new_clf)
    path.write_text(content, encoding="utf-8")
    print("[OK] Stage2 TA0006 garde balanced_subsample, autres tactiques sans poids")
