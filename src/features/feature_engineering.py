from __future__ import annotations

import sys
import json
from pathlib import Path

import pandas as pd
import numpy as np

EXCLUDE_ALWAYS = [
    "computer", "hostname_raw", "source_dataset", "source_file",
    "record_id", "raw", "source_format",
]
TARGET_COLUMNS = ["label", "mitre_tactic", "mitre_technique"]

SPARSE_PRESENCE_COLUMNS = [
    "target_user_name", "target_user_sid", "target_domain_name", "logon_type",
    "ticket_encryption_type", "ticket_options", "failure_reason",
    "status", "sub_status", "authentication_package",
    "ip_address", "ip_port", "workstation_name",
    "object_name", "object_type", "object_server", "operation_type",
    "access_mask", "properties", "privilege_list",
    "subject_user_name", "subject_user_sid", "subject_domain_name",
    "subject_logon_id",
]

GROUP_KEY = "subject_user_name"
ROLLING_WINDOW = "5min"


def add_time_features(df):
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_business_hours"] = df["hour"].between(8, 18).astype(int)
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    return df


def add_presence_flags(df):
    df = df.copy()
    for col in SPARSE_PRESENCE_COLUMNS:
        if col in df.columns:
            df[f"has_{col}"] = df[col].notna().astype(int)
    return df


def fit_event_id_frequency(df_train):
    """Encodage frequentiel de event_id, calcule UNIQUEMENT sur train."""
    freq = df_train["event_id"].value_counts(normalize=True)
    return freq.to_dict()


def apply_event_id_frequency(df, freq_map):
    df = df.copy()
    df["event_id_freq"] = df["event_id"].map(freq_map).fillna(0.0)
    return df


def add_causal_rolling_features(df, group_key=GROUP_KEY, window=ROLLING_WINDOW):
    """
    Features contextuelles par utilisateur, strictement causales : pour chaque
    evenement, on ne regarde que les evenements passes/presents du meme user
    dans la fenetre glissante. Calcule independamment sur train et test pour
    ne jamais laisser le contexte train fuiter vers le test.

    IMPORTANT: les lignes sans group_key (subject_user_name absent, ~93% des
    evenements) sont conservees dans le resultat final avec des valeurs par
    defaut, plutot que d'etre supprimees. Sinon on perd la quasi-totalite des
    evenements d'attaque (beaucoup n'ont pas de SubjectUserName renseigne).
    """
    df = df.copy().reset_index(drop=True)
    df["_row_id"] = df.index

    has_group = df[group_key].notna() & df["timestamp"].notna()
    df_with_group = df[has_group].sort_values([group_key, "timestamp"])
    df_without_group = df[~has_group]

    results = []
    for user, group in df_with_group.groupby(group_key, sort=False):
        g = group.set_index("timestamp").sort_index()

        n_events = g["event_id"].rolling(window).count()

        eventid_codes = pd.Series(
            pd.factorize(g["event_id"])[0], index=g.index
        ).astype(float)
        n_distinct_eventid = eventid_codes.rolling(window).apply(
            lambda x: pd.Series(x).nunique(), raw=True
        )

        if "computer" in g.columns:
            computer_codes = pd.Series(
                pd.factorize(g["computer"])[0], index=g.index
            ).astype(float)
            n_distinct_computer = computer_codes.rolling(window).apply(
                lambda x: pd.Series(x).nunique(), raw=True
            )
        else:
            n_distinct_computer = pd.Series(0, index=g.index)

        seconds_since_prev = g.index.to_series().diff().dt.total_seconds()

        g = g.reset_index()
        g["events_last_5min_user"] = n_events.values
        g["distinct_eventid_last_5min_user"] = n_distinct_eventid.values
        g["distinct_computers_last_5min_user"] = n_distinct_computer.values
        g["seconds_since_prev_event_user"] = seconds_since_prev.values

        results.append(g)

    if results:
        df_with_group_feat = pd.concat(results, ignore_index=True)
    else:
        df_with_group_feat = df_with_group.copy()
        for col in ["events_last_5min_user", "distinct_eventid_last_5min_user",
                    "distinct_computers_last_5min_user", "seconds_since_prev_event_user"]:
            df_with_group_feat[col] = np.nan

    df_without_group = df_without_group.copy()
    df_without_group["events_last_5min_user"] = 1
    df_without_group["distinct_eventid_last_5min_user"] = 1
    df_without_group["distinct_computers_last_5min_user"] = 0
    df_without_group["seconds_since_prev_event_user"] = np.nan

    df_out = pd.concat([df_with_group_feat, df_without_group], ignore_index=True)
    df_out = df_out.sort_values("_row_id").drop(columns=["_row_id"]).reset_index(drop=True)
    return df_out


def backfill_mitre_from_label(df, label_to_tactic):
    """
    mitre_tactic/mitre_technique ne sont remplis que pour les evenements
    issus du manifest EVTX. Les datasets Mordor (dcsync_empire, pass_the_hash,
    mimikatz...) n'ont jamais eu ce mapping. Comme label determine la tactique
    de facon deterministe, on comble les trous via:
    1. un mapping label->tactique construit a partir des lignes EVTX qui ont deja l'info
    2. un mapping manuel pour les labels Mordor (MORDOR_MANUAL_MITRE_MAP)
    benign reste volontairement None (pas une technique d'attaque).
    """
    df = df.copy()
    missing_tactic = df["mitre_tactic"].isna()
    df.loc[missing_tactic, "mitre_tactic"] = df.loc[missing_tactic, "label"].map(
        label_to_tactic
    )

    missing_technique = df["mitre_technique"].isna()
    for label, (tactic, technique) in MORDOR_MANUAL_MITRE_MAP.items():
        mask = (df["label"] == label) & df["mitre_tactic"].isna()
        df.loc[mask, "mitre_tactic"] = tactic
        mask_tech = (df["label"] == label) & df["mitre_technique"].isna()
        df.loc[mask_tech, "mitre_technique"] = technique

    return df


MORDOR_MANUAL_MITRE_MAP = {
    "dcsync_convenant": ("TA0006", "T1003.006"),
    "dcsync_empire": ("TA0006", "T1003.006"),
    "mimikatz": ("TA0006", "T1003.001"),
    "kerberos_createnetonly": ("TA0008", "T1550.003"),
    "ntds_dump_ninjacopy": ("TA0006", "T1003.003"),
    "ntds_dump_ntdsutil": ("TA0006", "T1003.003"),
    "ntds_dump_shadowcopy": ("TA0006", "T1003.003"),
    # benign volontairement absent : pas de tactique MITRE, reste None
}


def build_label_to_tactic_map(df_train):
    known = df_train.dropna(subset=["mitre_tactic"])
    mapping = known.groupby("label")["mitre_tactic"].agg(lambda x: x.mode().iloc[0])
    return mapping.to_dict()


TOP_N_EVENT_IDS = 20


def fit_top_event_ids(df_train, n=TOP_N_EVENT_IDS):
    return df_train["event_id"].value_counts().head(n).index.tolist()


def apply_event_id_onehot(df, top_event_ids):
    df = df.copy()
    for eid in top_event_ids:
        df[f"eid_{eid}"] = (df["event_id"] == eid).astype(int)
    df["eid_other"] = (~df["event_id"].isin(top_event_ids)).astype(int)
    return df


def build_features(df, freq_map, top_event_ids, fit_group_features=True):
    df = add_time_features(df)
    df = add_presence_flags(df)
    df = apply_event_id_frequency(df, freq_map)
    df = apply_event_id_onehot(df, top_event_ids)
    df = add_causal_rolling_features(df)

    df["seconds_since_prev_event_user"] = df["seconds_since_prev_event_user"].fillna(-1)
    df["distinct_computers_last_5min_user"] = df["distinct_computers_last_5min_user"].fillna(0)

    return df


def get_feature_columns(df):
    """Liste des colonnes utilisables comme X (exclut cibles + leakage + brut)."""
    exclude = set(EXCLUDE_ALWAYS + TARGET_COLUMNS + [GROUP_KEY, "timestamp"])
    exclude |= set(SPARSE_PRESENCE_COLUMNS)  # colonnes brutes remplacees par has_*
    exclude.add("event_id")  # remplace par event_id_freq + one-hot eid_*

    feature_cols = [c for c in df.columns if c not in exclude]
    return sorted(feature_cols)


if __name__ == "__main__":
    train_path = sys.argv[1] if len(sys.argv) > 1 else "data/splits/train.parquet"
    test_path = sys.argv[2] if len(sys.argv) > 2 else "data/splits/test.parquet"

    df_train = pd.read_parquet(train_path)
    df_test = pd.read_parquet(test_path)

    print(f"Train brut: {len(df_train)} evenements")
    print(f"Test brut:  {len(df_test)} evenements")

    freq_map = fit_event_id_frequency(df_train)
    print(f"\n{len(freq_map)} event_id distincts fit sur train pour l'encodage frequentiel")

    label_to_tactic = build_label_to_tactic_map(df_train)
    print(f"{len(label_to_tactic)} label(s) mappes vers une tactique MITRE pour le backfill")
    missing_labels = set(df_train["label"].unique()) - set(label_to_tactic.keys())
    if missing_labels:
        print(f"[ATTENTION] {len(missing_labels)} label(s) sans tactique connue: {sorted(missing_labels)}")

    df_train = backfill_mitre_from_label(df_train, label_to_tactic)
    df_test = backfill_mitre_from_label(df_test, label_to_tactic)

    top_event_ids = fit_top_event_ids(df_train)
    print(f"{len(top_event_ids)} event_id encodes en one-hot: {top_event_ids}")

    print("\n=== Construction features TRAIN ===")
    df_train_feat = build_features(df_train, freq_map, top_event_ids)

    print("\n=== Construction features TEST ===")
    df_test_feat = build_features(df_test, freq_map, top_event_ids)

    feature_cols = get_feature_columns(df_train_feat)
    print(f"\n{len(feature_cols)} colonnes de features retenues:")
    for c in feature_cols:
        print(f"  - {c}")

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    keep_cols = feature_cols + TARGET_COLUMNS + [GROUP_KEY, "timestamp", "computer"]
    keep_cols = [c for c in dict.fromkeys(keep_cols) if c in df_train_feat.columns]

    df_train_feat[keep_cols].to_parquet(out_dir / "features_train.parquet", index=False)
    df_test_feat[keep_cols].to_parquet(out_dir / "features_test.parquet", index=False)

    with open(out_dir / "feature_columns.json", "w", encoding="utf-8") as f:
        json.dump({
            "feature_columns": feature_cols,
            "target_columns": TARGET_COLUMNS,
            "excluded_always": EXCLUDE_ALWAYS,
            "note_computer_kept_for_traceability_not_a_feature": True,
        }, f, indent=2, ensure_ascii=False)

    with open(out_dir / "inference_artifacts.json", "w", encoding="utf-8") as f:
        json.dump({
            "event_id_freq_map": {str(k): v for k, v in freq_map.items()},
            "top_event_ids": top_event_ids,
            "label_to_tactic": label_to_tactic,
            "mordor_manual_mitre_map": MORDOR_MANUAL_MITRE_MAP,
            "sparse_presence_columns": SPARSE_PRESENCE_COLUMNS,
        }, f, indent=2, ensure_ascii=False)
    print(f"-> data/processed/inference_artifacts.json")

    print(f"\n=== EXPORT ===")
    print(f"-> data/processed/features_train.parquet ({len(df_train_feat)} lignes)")
    print(f"-> data/processed/features_test.parquet ({len(df_test_feat)} lignes)")
    print(f"-> data/processed/feature_columns.json")
