import pandas as pd

df = pd.read_parquet("data/processed/features_train.parquet")

print("=== Apercu ===")
print(df.shape)
print(df["label"].value_counts().head(10))

print("\n=== event_id_freq par label (les 6 evaluables) ===")
evaluable_labels = ["benign", "dcsync_empire", "pass_the_hash", "mimikatz",
                     "kerberos_createnetonly", "dcsync_convenant"]
print(df[df["label"].isin(evaluable_labels)].groupby("label")["event_id_freq"].describe())

print("\n=== has_access_mask par label (devrait etre eleve pour dcsync) ===")
print(df.groupby("label")["has_access_mask"].mean().sort_values(ascending=False).head(10))

print("\n=== distinct_computers_last_5min_user (signal mouvement lateral) ===")
print(df.groupby("label")["distinct_computers_last_5min_user"].mean().sort_values(ascending=False).head(10))

print("\n=== Valeurs manquantes restantes ===")
print(df.isna().sum()[df.isna().sum() > 0])
