import pandas as pd

df_train = pd.read_parquet("data/processed/features_train.parquet")
df_test = pd.read_parquet("data/processed/features_test.parquet")

print("=== TRAIN ===")
print(f"mitre_tactic manquant: {df_train['mitre_tactic'].isna().sum()} / {len(df_train)}")
labels_missing = df_train[df_train["mitre_tactic"].isna()]["label"].unique()
print(f"Labels concernes: {sorted(labels_missing)}")

print("\n=== TEST ===")
print(f"mitre_tactic manquant: {df_test['mitre_tactic'].isna().sum()} / {len(df_test)}")
labels_missing_test = df_test[df_test["mitre_tactic"].isna()]["label"].unique()
print(f"Labels concernes: {sorted(labels_missing_test)}")

print("\n=== Mapping label -> tactique final (verification) ===")
mapping_check = df_train.groupby("label")["mitre_tactic"].agg(lambda x: x.dropna().unique())
print(mapping_check)
