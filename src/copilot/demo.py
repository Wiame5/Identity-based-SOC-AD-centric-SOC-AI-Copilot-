import pandas as pd
from src.copilot.langgraph_pipeline import run_copilot
from src.copilot.ollama_client import warmup_model

warmup_model()

df = pd.read_parquet("data/processed/events_combined.parquet")


def pick_representative_event(df, label):
    """
    Choisit un evenement dont l'event_id correspond au plus frequent pour ce
    label, et qui a idealement subject_user_name rempli (plus de contexte),
    plutot que le premier trouve au hasard.
    """
    subset = df[df["label"] == label]
    top_eid = subset["event_id"].value_counts().idxmax()
    candidates = subset[subset["event_id"] == top_eid]

    with_user = candidates[candidates["subject_user_name"].notna()]
    chosen = with_user.iloc[0] if len(with_user) > 0 else candidates.iloc[0]
    return chosen.to_dict()


for label in ["pass_the_hash", "mimikatz", "benign", "dcsync_empire"]:
    sample = pick_representative_event(df, label)
    print(f"\n{'='*60}\nEvenement reel: label={label}, event_id={sample.get('event_id')}\n{'='*60}")
    report = run_copilot(sample)
    print(report)
