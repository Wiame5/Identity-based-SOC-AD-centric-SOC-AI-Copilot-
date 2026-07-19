from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score


def load_data():
    with open("data/processed/feature_columns.json", encoding="utf-8") as f:
        meta = json.load(f)
    feature_cols = meta["feature_columns"]

    df_train = pd.read_parquet("data/processed/features_train.parquet")
    df_test = pd.read_parquet("data/processed/features_test.parquet")

    for df in (df_train, df_test):
        df["stage1_target"] = df["mitre_tactic"].fillna("BENIGN")

    return df_train, df_test, feature_cols


def train_stage1(df_train, feature_cols, class_weight=None):
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
    print("\n--- Top 10 features importantes (Stage 1) ---")
    print(importances.head(10))

    return clf


def evaluate_stage1(clf, df_test, feature_cols):
    X = df_test[feature_cols]
    y_true = df_test["stage1_target"].astype(str)
    y_pred = pd.Series(clf.predict(X)).astype(str)

    print("=== STAGE 1 : Classification par tactique MITRE ===")
    print(classification_report(y_true, y_pred, zero_division=0))

    from sklearn.metrics import confusion_matrix
    present_labels = sorted(set(y_true.unique()) | set(y_pred.unique()))
    cm = confusion_matrix(y_true, y_pred, labels=present_labels)
    cm_df = pd.DataFrame(cm, index=present_labels, columns=present_labels)
    print("\n=== Matrice de confusion STAGE 1 ===")
    print(cm_df)

    return y_pred


def train_stage2(df_train, feature_cols, class_weight_stage2="balanced_subsample"):
    """
    Un classifieur par tactique (hors BENIGN), qui predit le label precis
    (technique) parmi les labels appartenant a cette tactique.
    """
    stage2_models = {}
    tactics = sorted(df_train.loc[df_train["stage1_target"] != "BENIGN", "stage1_target"].unique())

    print("\n=== STAGE 2 : Entrainement par tactique ===")
    for tactic in tactics:
        subset = df_train[df_train["stage1_target"] == tactic]
        n_labels = subset["label"].nunique()
        print(f"{tactic}: {len(subset)} evenements, {n_labels} label(s) distinct(s) -> "
              f"{sorted(subset['label'].unique())}")

        X = subset[feature_cols]
        y = subset["label"]

        if n_labels < 2:
            # Un seul label pour cette tactique : pas besoin de modele,
            # on stocke simplement le label constant.
            stage2_models[tactic] = {"type": "constant", "value": y.iloc[0]}
            continue

        weight = class_weight_stage2 if tactic == "TA0006" else None
        clf = RandomForestClassifier(
            n_estimators=200,
            class_weight=weight,
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X, y)
        stage2_models[tactic] = {"type": "model", "value": clf}

    return stage2_models


def predict_hierarchical(stage1_clf, stage2_models, X, stage1_pred=None):
    """Predit le label final en combinant stage1 (tactique) et stage2 (technique)."""
    if stage1_pred is None:
        stage1_pred = stage1_clf.predict(X)

    final_pred = np.empty(len(X), dtype=object)
    stage1_pred = np.asarray(stage1_pred)

    for tactic in np.unique(stage1_pred):
        mask = stage1_pred == tactic

        if tactic == "BENIGN":
            final_pred[mask] = "benign"
            continue

        entry = stage2_models.get(tactic)
        if entry is None:
            # Tactique predite au stage1 mais jamais vue au stage2 (ne devrait
            # pas arriver puisque stage2 est entraine sur les memes tactiques
            # que stage1, mais on se protege quand meme).
            final_pred[mask] = "UNKNOWN"
            continue

        if entry["type"] == "constant":
            final_pred[mask] = entry["value"]
        else:
            X_subset = X[mask]
            final_pred[mask] = entry["value"].predict(X_subset)

    return final_pred


def evaluate_hierarchical(stage1_clf, stage2_models, df_test, feature_cols):
    X_test = df_test[feature_cols]
    y_true = df_test["label"]

    stage1_pred = stage1_clf.predict(X_test)
    final_pred = predict_hierarchical(stage1_clf, stage2_models, X_test, stage1_pred)

    print("\n=== EVALUATION HIERARCHIQUE COMPLETE (tous labels du test) ===")
    acc_all = accuracy_score(y_true, final_pred)
    print(f"Accuracy globale (tous labels presents en test): {acc_all:.4f}")
    print(classification_report(y_true, final_pred, zero_division=0))

    train_labels = set(df_test.attrs.get("train_labels", []))
    evaluable_labels = sorted(set(y_true.unique()) & train_labels) if train_labels else sorted(y_true.unique())

    mask_evaluable = y_true.isin(evaluable_labels)
    if mask_evaluable.sum() > 0:
        print(f"\n=== EVALUATION restreinte aux {len(evaluable_labels)} labels evaluables "
              f"(presents en train ET test): {evaluable_labels} ===")
        y_true_eval = y_true[mask_evaluable].astype(str)
        y_pred_eval = pd.Series(final_pred[mask_evaluable]).astype(str)
        acc_eval = accuracy_score(y_true_eval, y_pred_eval)
        print(f"Accuracy (labels evaluables uniquement): {acc_eval:.4f}")
        print(classification_report(y_true_eval, y_pred_eval, zero_division=0))

        print("\n=== Matrice de confusion (labels evaluables) ===")
        from sklearn.metrics import confusion_matrix
        labels_sorted = sorted(evaluable_labels)
        cm = confusion_matrix(y_true_eval, y_pred_eval, labels=labels_sorted)
        cm_df = pd.DataFrame(cm, index=labels_sorted, columns=labels_sorted)
        print(cm_df)

        print("\n=== Ou vont les erreurs (predictions incorrectes hors labels evaluables) ===")
        errors = y_pred_eval[y_true_eval != y_pred_eval]
        if len(errors) > 0:
            print(errors.value_counts())
        else:
            print("Aucune erreur.")

    return final_pred


if __name__ == "__main__":
    df_train, df_test, feature_cols = load_data()

    evaluable_labels = sorted(set(df_train["label"].unique()) & set(df_test["label"].unique()))
    df_test.attrs["train_labels"] = set(df_train["label"].unique())

    print(f"Features utilisees ({len(feature_cols)}): {feature_cols}")
    print(f"\nLabels evaluables (train ET test): {evaluable_labels}")

    stage1_clf = train_stage1(df_train, feature_cols)
    evaluate_stage1(stage1_clf, df_test, feature_cols)

    stage2_models = train_stage2(df_train, feature_cols)

    final_pred = evaluate_hierarchical(stage1_clf, stage2_models, df_test, feature_cols)

    out_dir = Path("models")
    out_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(stage1_clf, out_dir / "hierarchical_stage1.pkl")
    joblib.dump(stage2_models, out_dir / "hierarchical_stage2.pkl")

    with open(out_dir / "hierarchical_meta.json", "w", encoding="utf-8") as f:
        json.dump({
            "feature_columns": feature_cols,
            "evaluable_labels": evaluable_labels,
            "tactics": sorted(df_train["stage1_target"].unique().tolist()),
        }, f, indent=2, ensure_ascii=False)

    print(f"\n=== EXPORT ===")
    print(f"-> models/hierarchical_stage1.pkl")
    print(f"-> models/hierarchical_stage2.pkl")
    print(f"-> models/hierarchical_meta.json")
