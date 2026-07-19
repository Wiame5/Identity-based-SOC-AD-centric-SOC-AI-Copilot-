from __future__ import annotations

import sys
import pandas as pd


def investigate_label(df, label, top_n=15):
    sub = df[df["label"] == label].copy()
    sub["timestamp"] = pd.to_datetime(sub["timestamp"], errors="coerce")
    sub = sub.sort_values("timestamp")

    print(f"\n{'='*70}")
    print(f"Label: {label}  (n={len(sub)})")
    print(f"{'='*70}")

    print("\n--- Repartition par source_file ---")
    print(sub["source_file"].value_counts())

    print("\n--- Repartition par jour ---")
    daily = sub["timestamp"].dt.date.value_counts().sort_index()
    print(daily)

    print(f"\n--- Premiers {top_n} timestamps ---")
    print(sub[["timestamp", "source_file", "computer"]].head(top_n).to_string(index=False))

    print(f"\n--- Derniers {top_n} timestamps ---")
    print(sub[["timestamp", "source_file", "computer"]].tail(top_n).to_string(index=False))

    gaps = sub["timestamp"].diff().dropna()
    print("\n--- Plus gros ecarts entre 2 evenements consecutifs ---")
    top_gaps = gaps.sort_values(ascending=False).head(5)
    for idx in top_gaps.index:
        print(f"  {gaps[idx]}  entre positions {sub.index.get_loc(idx)-1} et {sub.index.get_loc(idx)}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/events_combined.parquet"
    df = pd.read_parquet(path)

    for label in ["pass_the_hash", "scheduled_task_lateral_movement"]:
        investigate_label(df, label)
