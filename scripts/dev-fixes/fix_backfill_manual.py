import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

old_func = '''def backfill_mitre_from_label(df, label_to_tactic):
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
    return df'''

new_func = '''def backfill_mitre_from_label(df, label_to_tactic):
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

    return df'''

if old_func not in content:
    print("[ERREUR] Fonction backfill_mitre_from_label introuvable ou deja modifiee")
else:
    content = content.replace(old_func, new_func)
    path.write_text(content, encoding="utf-8")
    print("[OK] backfill_mitre_from_label mis a jour avec le mapping manuel")
