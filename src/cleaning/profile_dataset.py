from __future__ import annotations

import sys

import pandas as pd

RARE_THRESHOLD = 5


def profile(df):
    print("=" * 70)
    print("PROFILAGE DU DATASET - Couche 1.3")
    print("=" * 70)

    print(f"\nDimensions : {df.shape[0]} lignes x {df.shape[1]} colonnes")

    print("\n--- Taux de valeurs manquantes par colonne (%) ---")
    null_rates = (df.isna().mean() * 100).sort_values(ascending=False)
    for col, rate in null_rates.items():
        if rate > 0:
            print(f"  {col:30s} {rate:6.2f}%")

    print("\n--- Distribution Event ID x label (top 3 event_id par label) ---")
    for label in sorted(df["label"].unique()):
        sub = df[df["label"] == label]
        top_ids = sub["event_id"].value_counts().head(3)
        ids_str = ", ".join(f"{eid}({cnt})" for eid, cnt in top_ids.items())
        print(f"  {label:35s} n={len(sub):6d}  event_ids: {ids_str}")

    print("\n--- Etendue temporelle par label ---")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    span = df.groupby("label")["timestamp"].agg(["min", "max"])
    span["duree"] = span["max"] - span["min"]
    print(span[["duree"]].sort_values("duree"))

    print(f"\n--- Classes rares (< {RARE_THRESHOLD} echantillons) ---")
    counts = df["label"].value_counts()
    rare = counts[counts < RARE_THRESHOLD]
    print(f"{len(rare)} classe(s) concernee(s), total {rare.sum()} echantillons :")
    print(rare)
    print(
        "\n[Decision Couche 1.4] Ces classes seront fusionnees en "
        "rare_technique_<tactic> pour l'entrainement du modele multi-classe "
        "fin, mais restent identifiables individuellement pour l'analyse "
        "qualitative et les regles baseline."
    )

    print("\n--- Repartition par tactique MITRE (niveau grossier) ---")
    print(df["mitre_tactic"].value_counts())


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/events_combined.parquet"
    df = pd.read_parquet(path)
    profile(df)
