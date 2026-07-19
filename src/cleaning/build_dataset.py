from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.ingestion.evtx_xml_parser import parse_all_from_manifest
from src.ingestion.mordor_parser import parse_mordor_file
from src.ingestion.benign_parser import parse_benign_file
from src.ingestion.schema import NormalizedEvent

MORDOR_FILES = [
    "dcsync_convenant.json",
    "dcsync_empire.json",
    "kerberos_createnetonly.json",
    "mimikatz.json",
    "ntds_dump_ninjacopy.json",
    "ntds_dump_ntdsutil.json",
    "ntds_dump_shadowcopy.json",
    "pass_the_hash.json",
]


def events_to_dataframe(events):
    rows = [e.model_dump(exclude={"raw"}) for e in events]
    df = pd.DataFrame(rows)
    return df


def deduplicate(df):
    before = len(df)

    has_id = df["record_id"].notna()
    df_with_id = df[has_id].drop_duplicates(subset=["source_file", "record_id"], keep="first")
    df_without_id = df[~has_id]
    df = pd.concat([df_with_id, df_without_id], ignore_index=True)

    after = len(df)
    print(f"[Cleaning] Doublons supprimes: {before - after} ({before} -> {after})")
    print(f"[Cleaning] Evenements sans record_id (non dedupliques, conserves): {(~has_id).sum()}")
    return df


def audit_leakage_risk(df):
    print("\n=== AUDIT ANTI-DATA-LEAKAGE ===")
    grouping = df.groupby("label")["computer"].nunique()
    single_host_labels = grouping[grouping <= 1]
    if len(single_host_labels) > 0:
        print(f"[RISQUE] {len(single_host_labels)} label(s) associe(s) a UNE SEULE machine :")
        for label in single_host_labels.index:
            hosts = df[df["label"] == label]["computer"].unique()
            print(f"   - {label}: {list(hosts)}")
        print(
            "   -> Limite a documenter dans le rapport : le modele pourrait "
            "apprendre a reconnaitre le nom de machine plutot que le "
            "comportement. Recommandation : exclure computer/hostname_raw "
            "des features d'entree du modele (Couche 5), ou les anonymiser."
        )
    else:
        print("[OK] Aucun label n'est associe a une seule machine unique.")

    print(f"\nNombre de labels distincts : {df['label'].nunique()}")
    print(df["label"].value_counts())


def build_full_dataset(manifest_path, evtx_root, mordor_dir=None, benign_path=None):
    print("=== Parsing EVTX-ATTACK-SAMPLES ===")
    evtx_events = parse_all_from_manifest(manifest_path, evtx_root)
    df_evtx = events_to_dataframe(evtx_events)

    dfs = [df_evtx]

    if mordor_dir and Path(mordor_dir).exists():
        print("\n=== Parsing datasets Mordor (JSON) ===")
        for filename in MORDOR_FILES:
            json_file = Path(mordor_dir) / filename
            if not json_file.exists():
                print(f"[WARN] Fichier Mordor manquant, ignore: {json_file}", file=sys.stderr)
                continue
            dataset_name = json_file.stem
            mordor_events = list(parse_mordor_file(str(json_file), dataset_name))
            df_mordor = events_to_dataframe(mordor_events)
            df_mordor["label"] = dataset_name
            print(f"{json_file.name}: {len(df_mordor)} evenements")
            dfs.append(df_mordor)

    if benign_path:
        benign_file = Path(benign_path)
        if benign_file.exists():
            print("\n=== Parsing donnees benignes synthetiques ===")
            benign_events = list(parse_benign_file(str(benign_file)))
            df_benign = events_to_dataframe(benign_events)
            print(f"{benign_file.name}: {len(df_benign)} evenements (benign)")
            dfs.append(df_benign)
        else:
            print(f"[WARN] Fichier benin manquant, ignore: {benign_file}", file=sys.stderr)

    df_all = pd.concat(dfs, ignore_index=True)
    df_all = deduplicate(df_all)
    audit_leakage_risk(df_all)
    return df_all


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m src.cleaning.build_dataset <manifest.yaml> <evtx_root> [mordor_dir] [benign_path]")
        sys.exit(1)

    manifest_path = sys.argv[1]
    evtx_root = sys.argv[2]
    mordor_dir = sys.argv[3] if len(sys.argv) > 3 else "data/raw"
    benign_path = sys.argv[4] if len(sys.argv) > 4 else "data/raw/benign_synthetic.json"

    df = build_full_dataset(manifest_path, evtx_root, mordor_dir, benign_path)

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "events_combined.parquet", index=False)
    df.to_csv(out_dir / "events_combined.csv", index=False, encoding="utf-8")

    print(f"\n=== EXPORT ===")
    print(f"Total evenements finaux : {len(df)}")
    print(f"-> data/processed/events_combined.parquet")
    print(f"-> data/processed/events_combined.csv")
