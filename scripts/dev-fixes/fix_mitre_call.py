import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

old_call = '''    freq_map = fit_event_id_frequency(df_train)
    print(f"\\n{len(freq_map)} event_id distincts fit sur train pour l'encodage frequentiel")

    print("\\n=== Construction features TRAIN ===")
    df_train_feat = build_features(df_train, freq_map)

    print("\\n=== Construction features TEST ===")
    df_test_feat = build_features(df_test, freq_map)'''

new_call = '''    freq_map = fit_event_id_frequency(df_train)
    print(f"\\n{len(freq_map)} event_id distincts fit sur train pour l'encodage frequentiel")

    label_to_tactic = build_label_to_tactic_map(df_train)
    print(f"{len(label_to_tactic)} label(s) mappes vers une tactique MITRE pour le backfill")
    missing_labels = set(df_train["label"].unique()) - set(label_to_tactic.keys())
    if missing_labels:
        print(f"[ATTENTION] {len(missing_labels)} label(s) sans tactique connue: {sorted(missing_labels)}")

    df_train = backfill_mitre_from_label(df_train, label_to_tactic)
    df_test = backfill_mitre_from_label(df_test, label_to_tactic)

    print("\\n=== Construction features TRAIN ===")
    df_train_feat = build_features(df_train, freq_map)

    print("\\n=== Construction features TEST ===")
    df_test_feat = build_features(df_test, freq_map)'''

if old_call not in content:
    print("[ERREUR] Bloc d'appel introuvable")
elif "backfill_mitre_from_label(df_train" in content:
    print("[INFO] Deja applique")
else:
    content = content.replace(old_call, new_call)
    path.write_text(content, encoding="utf-8")
    print("[OK] Appel backfill integre dans le main")
