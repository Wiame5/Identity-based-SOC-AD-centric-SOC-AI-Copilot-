import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

# 1. Ajouter les colonnes manquantes aux presence flags + exclure source_format
old_sparse = '''SPARSE_PRESENCE_COLUMNS = [
    "target_user_name", "target_user_sid", "logon_type",
    "ticket_encryption_type", "ticket_options", "failure_reason",
    "status", "sub_status", "authentication_package",
    "ip_address", "ip_port", "workstation_name",
    "object_name", "object_type", "object_server", "operation_type",
    "access_mask", "properties", "privilege_list",
    "subject_user_name", "subject_user_sid", "subject_domain_name",
]'''

new_sparse = '''SPARSE_PRESENCE_COLUMNS = [
    "target_user_name", "target_user_sid", "target_domain_name", "logon_type",
    "ticket_encryption_type", "ticket_options", "failure_reason",
    "status", "sub_status", "authentication_package",
    "ip_address", "ip_port", "workstation_name",
    "object_name", "object_type", "object_server", "operation_type",
    "access_mask", "properties", "privilege_list",
    "subject_user_name", "subject_user_sid", "subject_domain_name",
    "subject_logon_id",
]'''

old_exclude = '''EXCLUDE_ALWAYS = [
    "computer", "hostname_raw", "source_dataset", "source_file",
    "record_id", "raw",
]'''

new_exclude = '''EXCLUDE_ALWAYS = [
    "computer", "hostname_raw", "source_dataset", "source_file",
    "record_id", "raw", "source_format",
]'''

if old_sparse not in content or old_exclude not in content:
    print("[ERREUR] Un des blocs introuvable, verifie manuellement")
else:
    content = content.replace(old_sparse, new_sparse)
    content = content.replace(old_exclude, new_exclude)
    print("[OK] SPARSE_PRESENCE_COLUMNS et EXCLUDE_ALWAYS mis a jour")

# 2. Fix de la perte de lignes : ne dropper que pour le calcul rolling,
#    puis remerger sur l'index complet
old_causal = '''def add_causal_rolling_features(df, group_key=GROUP_KEY, window=ROLLING_WINDOW):
    """
    Features contextuelles par utilisateur, strictement causales : pour chaque
    evenement, on ne regarde que les evenements passes/presents du meme user
    dans la fenetre glissante. Calcule independamment sur train et test pour
    ne jamais laisser le contexte train fuiter vers le test.
    """
    df = df.copy()
    df = df.dropna(subset=[group_key, "timestamp"]).sort_values([group_key, "timestamp"])

    results = []
    for user, group in df.groupby(group_key, sort=False):
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

    return pd.concat(results, ignore_index=True)'''

new_causal = '''def add_causal_rolling_features(df, group_key=GROUP_KEY, window=ROLLING_WINDOW):
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
    return df_out'''

if old_causal not in content:
    print("[ERREUR] Bloc add_causal_rolling_features introuvable")
else:
    content = content.replace(old_causal, new_causal)
    print("[OK] add_causal_rolling_features corrige (plus de perte de lignes)")

path.write_text(content, encoding="utf-8")
print("\\n[OK] Fichier feature_engineering.py mis a jour")
