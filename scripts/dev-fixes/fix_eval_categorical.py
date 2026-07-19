import re
from pathlib import Path

path = Path("src/modeling/train_hierarchical.py")
content = path.read_text(encoding="utf-8")

old_block = '''    mask_evaluable = y_true.isin(evaluable_labels)
    if mask_evaluable.sum() > 0:
        print(f"\\n=== EVALUATION restreinte aux {len(evaluable_labels)} labels evaluables "
              f"(presents en train ET test): {evaluable_labels} ===")
        acc_eval = accuracy_score(y_true[mask_evaluable], final_pred[mask_evaluable])
        print(f"Accuracy (labels evaluables uniquement): {acc_eval:.4f}")
        print(classification_report(
            y_true[mask_evaluable], final_pred[mask_evaluable], zero_division=0
        ))

    return final_pred'''

new_block = '''    mask_evaluable = y_true.isin(evaluable_labels)
    if mask_evaluable.sum() > 0:
        print(f"\\n=== EVALUATION restreinte aux {len(evaluable_labels)} labels evaluables "
              f"(presents en train ET test): {evaluable_labels} ===")
        y_true_eval = y_true[mask_evaluable].astype(str)
        y_pred_eval = pd.Series(final_pred[mask_evaluable]).astype(str)
        acc_eval = accuracy_score(y_true_eval, y_pred_eval)
        print(f"Accuracy (labels evaluables uniquement): {acc_eval:.4f}")
        print(classification_report(y_true_eval, y_pred_eval, zero_division=0))

        print("\\n=== Matrice de confusion (labels evaluables) ===")
        from sklearn.metrics import confusion_matrix
        labels_sorted = sorted(evaluable_labels)
        cm = confusion_matrix(y_true_eval, y_pred_eval, labels=labels_sorted)
        cm_df = pd.DataFrame(cm, index=labels_sorted, columns=labels_sorted)
        print(cm_df)

        print("\\n=== Ou vont les erreurs (predictions incorrectes hors labels evaluables) ===")
        errors = y_pred_eval[y_true_eval != y_pred_eval]
        if len(errors) > 0:
            print(errors.value_counts())
        else:
            print("Aucune erreur.")

    return final_pred'''

if old_block not in content:
    print("[ERREUR] Bloc introuvable")
else:
    content = content.replace(old_block, new_block)
    path.write_text(content, encoding="utf-8")
    print("[OK] Fix categorical + matrice de confusion ajoutes")
