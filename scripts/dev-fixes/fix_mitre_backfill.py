import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

marker = "def build_features(df, freq_map, fit_group_features=True):"

new_function = '''def backfill_mitre_from_label(df, label_to_tactic):
    """
    mitre_tactic/mitre_technique ne sont remplis que pour les evenements
    issus du manifest EVTX. Les datasets Mordor (dcsync_empire, pass_the_hash,
    mimikatz...) n'ont jamais eu ce mapping. Comme label determine la tactique
    de facon deterministe, on comble les trous via un mapping label->tactique
    construit a partir des lignes qui ont deja l'info.
    """
    df = df.copy()
    missing_tactic = df["mitre_tactic"].isna()
    df.loc[missing_tactic, "mitre_tactic"] = df.loc[missing_tactic, "label"].map(
        label_to_tactic
    )
    return df


def build_label_to_tactic_map(df_train):
    known = df_train.dropna(subset=["mitre_tactic"])
    mapping = known.groupby("label")["mitre_tactic"].agg(lambda x: x.mode().iloc[0])
    return mapping.to_dict()


def build_features(df, freq_map, fit_group_features=True):'''

if marker not in content:
    print("[ERREUR] Marqueur introuvable")
elif "backfill_mitre_from_label" in content:
    print("[INFO] Fix deja applique, rien a faire")
else:
    content = content.replace(marker, new_function)
    path.write_text(content, encoding="utf-8")
    print("[OK] Fonctions de backfill ajoutees")
