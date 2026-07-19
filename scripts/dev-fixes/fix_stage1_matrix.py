import re
from pathlib import Path

path = Path("src/modeling/train_hierarchical.py")
content = path.read_text(encoding="utf-8")

old_block = '''def evaluate_stage1(clf, df_test, feature_cols):
    X = df_test[feature_cols]
    y_true = df_test["stage1_target"]
    y_pred = clf.predict(X)

    print("=== STAGE 1 : Classification par tactique MITRE ===")
    print(classification_report(y_true, y_pred, zero_division=0))
    return y_pred'''

new_block = '''def evaluate_stage1(clf, df_test, feature_cols):
    X = df_test[feature_cols]
    y_true = df_test["stage1_target"].astype(str)
    y_pred = pd.Series(clf.predict(X)).astype(str)

    print("=== STAGE 1 : Classification par tactique MITRE ===")
    print(classification_report(y_true, y_pred, zero_division=0))

    from sklearn.metrics import confusion_matrix
    present_labels = sorted(set(y_true.unique()) | set(y_pred.unique()))
    cm = confusion_matrix(y_true, y_pred, labels=present_labels)
    cm_df = pd.DataFrame(cm, index=present_labels, columns=present_labels)
    print("\\n=== Matrice de confusion STAGE 1 ===")
    print(cm_df)

    return y_pred'''

if old_block not in content:
    print("[ERREUR] Bloc introuvable")
else:
    content = content.replace(old_block, new_block)
    path.write_text(content, encoding="utf-8")
    print("[OK] Matrice de confusion Stage 1 ajoutee")
