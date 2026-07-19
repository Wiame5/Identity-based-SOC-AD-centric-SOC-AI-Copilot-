import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

old_call = '''    df_train = backfill_mitre_from_label(df_train, label_to_tactic)
    df_test = backfill_mitre_from_label(df_test, label_to_tactic)

    print("\\n=== Construction features TRAIN ===")
    df_train_feat = build_features(df_train, freq_map)

    print("\\n=== Construction features TEST ===")
    df_test_feat = build_features(df_test, freq_map)'''

new_call = '''    df_train = backfill_mitre_from_label(df_train, label_to_tactic)
    df_test = backfill_mitre_from_label(df_test, label_to_tactic)

    top_event_ids = fit_top_event_ids(df_train)
    print(f"{len(top_event_ids)} event_id encodes en one-hot: {top_event_ids}")

    print("\\n=== Construction features TRAIN ===")
    df_train_feat = build_features(df_train, freq_map, top_event_ids)

    print("\\n=== Construction features TEST ===")
    df_test_feat = build_features(df_test, freq_map, top_event_ids)'''

if old_call not in content:
    print("[ERREUR] Bloc d'appel introuvable")
else:
    content = content.replace(old_call, new_call)
    path.write_text(content, encoding="utf-8")
    print("[OK] Appels mis a jour avec top_event_ids")
