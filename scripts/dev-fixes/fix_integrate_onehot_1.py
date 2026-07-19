import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

old_build = '''def build_features(df, freq_map, fit_group_features=True):
    df = add_time_features(df)
    df = add_presence_flags(df)
    df = apply_event_id_frequency(df, freq_map)
    df = add_causal_rolling_features(df)'''

new_build = '''def build_features(df, freq_map, top_event_ids, fit_group_features=True):
    df = add_time_features(df)
    df = add_presence_flags(df)
    df = apply_event_id_frequency(df, freq_map)
    df = apply_event_id_onehot(df, top_event_ids)
    df = add_causal_rolling_features(df)'''

if old_build not in content:
    print("[ERREUR] Bloc build_features introuvable")
else:
    content = content.replace(old_build, new_build)
    path.write_text(content, encoding="utf-8")
    print("[OK] build_features accepte maintenant top_event_ids")
