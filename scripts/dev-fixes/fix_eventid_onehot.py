import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

marker = "def build_features(df, freq_map, fit_group_features=True):"

new_funcs = '''TOP_N_EVENT_IDS = 20


def fit_top_event_ids(df_train, n=TOP_N_EVENT_IDS):
    return df_train["event_id"].value_counts().head(n).index.tolist()


def apply_event_id_onehot(df, top_event_ids):
    df = df.copy()
    for eid in top_event_ids:
        df[f"eid_{eid}"] = (df["event_id"] == eid).astype(int)
    df["eid_other"] = (~df["event_id"].isin(top_event_ids)).astype(int)
    return df


def build_features(df, freq_map, fit_group_features=True):'''

if marker not in content:
    print("[ERREUR] Marqueur introuvable")
elif "TOP_N_EVENT_IDS" in content:
    print("[INFO] Deja applique")
else:
    content = content.replace(marker, new_funcs)
    path.write_text(content, encoding="utf-8")
    print("[OK] Fonctions one-hot event_id ajoutees")
