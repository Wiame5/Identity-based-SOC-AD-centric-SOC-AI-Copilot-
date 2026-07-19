import re
from pathlib import Path

path = Path("src/modeling/train_hierarchical.py")
content = path.read_text(encoding="utf-8")

old_train_stage1 = '''def train_stage1(df_train, feature_cols):
    X = df_train[feature_cols]
    y = df_train["stage1_target"]

    clf = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X, y)
    return clf'''

new_train_stage1 = '''def train_stage1(df_train, feature_cols, class_weight="balanced"):
    X = df_train[feature_cols]
    y = df_train["stage1_target"]

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_leaf=3,
        class_weight=class_weight,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X, y)

    importances = pd.Series(clf.feature_importances_, index=feature_cols).sort_values(ascending=False)
    print("\\n--- Top 10 features importantes (Stage 1) ---")
    print(importances.head(10))

    return clf'''

if old_train_stage1 not in content:
    print("[ERREUR] Bloc train_stage1 introuvable")
else:
    content = content.replace(old_train_stage1, new_train_stage1)
    path.write_text(content, encoding="utf-8")
    print("[OK] train_stage1 mis a jour (class_weight parametrable + feature importance)")
