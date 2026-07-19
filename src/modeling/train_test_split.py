from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import numpy as np


def make_group_key(df):
    return df["computer"].fillna(df["source_dataset"])


def identify_single_host_labels(df):
    grouping = df.groupby("label")["computer"].nunique()
    return set(grouping[grouping <= 1].index)


def get_fixed_train_hosts(df, single_host_labels):
    """Hosts utilises par les labels mono-host : ils DOIVENT rester en train
    integralement, meme s'ils apparaissent aussi dans un label multi-host."""
    df_forced = df[df["label"].isin(single_host_labels)]
    return set(make_group_key(df_forced).dropna().unique())


def assign_hosts_per_label(df_splittable, fixed_train_hosts, test_size=0.25, random_state=42):
    """
    Pour chaque label multi-host, assigne une fraction de ses hosts au test,
    en excluant tout host deja fixe en train (partage avec un label mono-host).
    """
    rng = np.random.default_rng(random_state)
    host_assignment = {h: "train" for h in fixed_train_hosts}

    labels = sorted(df_splittable["label"].unique())
    for label in labels:
        all_hosts = sorted(df_splittable.loc[df_splittable["label"] == label, "computer"].dropna().unique())
        candidate_hosts = [h for h in all_hosts if h not in fixed_train_hosts]

        for h in all_hosts:
            if h in fixed_train_hosts:
                host_assignment.setdefault(h, "train")

        if len(candidate_hosts) < 2:
            for h in candidate_hosts:
                host_assignment.setdefault(h, "train")
            continue

        n_test = max(1, round(len(candidate_hosts) * test_size))
        n_test = min(n_test, len(candidate_hosts) - 1)

        shuffled = list(candidate_hosts)
        rng.shuffle(shuffled)
        test_hosts = set(shuffled[:n_test])

        for h in candidate_hosts:
            desired = "test" if h in test_hosts else "train"
            if h not in host_assignment:
                host_assignment[h] = desired

    return host_assignment


def split_train_test(df, test_size=0.25, random_state=42):
    single_host_labels = identify_single_host_labels(df)
    print(f"{len(single_host_labels)} label(s) mono-host detectes -> forces entierement en train")

    fixed_train_hosts = get_fixed_train_hosts(df, single_host_labels)
    print(f"{len(fixed_train_hosts)} host(s) fixes en train (utilises par un label mono-host)")

    df_splittable = df[~df["label"].isin(single_host_labels)].copy()
    df_forced_train = df[df["label"].isin(single_host_labels)].copy()

    host_assignment = assign_hosts_per_label(df_splittable, fixed_train_hosts, test_size, random_state)

    groups_splittable = make_group_key(df_splittable)
    is_test = groups_splittable.map(host_assignment).eq("test")

    df_train_split = df_splittable[~is_test]
    df_test = df_splittable[is_test].reset_index(drop=True)

    df_train = pd.concat([df_train_split, df_forced_train], ignore_index=True)

    train_hosts = set(make_group_key(df_train))
    test_hosts = set(make_group_key(df_test))
    overlap = train_hosts & test_hosts

    print(f"\nChevauchement de groupes train/test: {len(overlap)} (doit etre 0 maintenant)")
    if overlap:
        print("[ATTENTION] Overlap residuel inattendu:")
        for h in overlap:
            labels_this_host = sorted(df[df["computer"] == h]["label"].unique())
            print(f"   - {h}: labels = {labels_this_host}")

    print(f"\nTrain: {len(df_train)} evenements")
    print(f"Test:  {len(df_test)} evenements")

    print("\n--- Comptage par label : train vs test ---")
    comparison = pd.DataFrame({
        "train": df_train["label"].value_counts(),
        "test": df_test["label"].value_counts(),
    }).fillna(0).astype(int)
    comparison["evaluable"] = (comparison["train"] > 0) & (comparison["test"] > 0)
    print(comparison.sort_values("train", ascending=False))

    n_evaluable = comparison["evaluable"].sum()
    print(f"\n{n_evaluable}/{len(comparison)} labels evaluables quantitativement (train ET test).")

    return df_train, df_test, single_host_labels


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/events_combined.parquet"
    df = pd.read_parquet(path)

    df_train, df_test, single_host_labels = split_train_test(df)

    out_dir = Path("data/splits")
    out_dir.mkdir(parents=True, exist_ok=True)
    df_train.to_parquet(out_dir / "train.parquet", index=False)
    df_test.to_parquet(out_dir / "test.parquet", index=False)

    with open(out_dir / "single_host_labels.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(single_host_labels)))

    print(f"\n-> data/splits/train.parquet")
    print(f"-> data/splits/test.parquet")
