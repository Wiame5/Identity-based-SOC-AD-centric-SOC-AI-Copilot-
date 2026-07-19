import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

old_export = '''    with open(out_dir / "feature_columns.json", "w", encoding="utf-8") as f:
        json.dump({
            "feature_columns": feature_cols,
            "target_columns": TARGET_COLUMNS,
            "excluded_always": EXCLUDE_ALWAYS,
            "note_computer_kept_for_traceability_not_a_feature": True,
        }, f, indent=2, ensure_ascii=False)'''

new_export = '''    with open(out_dir / "feature_columns.json", "w", encoding="utf-8") as f:
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
    print(f"-> data/processed/inference_artifacts.json")'''

if old_export not in content:
    print("[ERREUR] Bloc export introuvable")
else:
    content = content.replace(old_export, new_export)
    path.write_text(content, encoding="utf-8")
    print("[OK] inference_artifacts.json ajoute a l'export")
