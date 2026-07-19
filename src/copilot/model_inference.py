from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import joblib
import numpy as np
import pandas as pd


class DetectionEngine:
    """
    Charge les modeles entraines et les artefacts d'encodage pour predire
    label/tactique/technique sur un evenement AD normalise, sans historique
    de session (features de rolling utilisateur mises a des valeurs par
    defaut, comme pour un evenement isole non rattache a une fenetre).
    """

    def __init__(self, models_dir="models", artifacts_path="data/processed/inference_artifacts.json",
                 columns_path="data/processed/feature_columns.json"):
        self.stage1_clf = joblib.load(Path(models_dir) / "hierarchical_stage1.pkl")
        self.stage2_models = joblib.load(Path(models_dir) / "hierarchical_stage2.pkl")

        with open(artifacts_path, encoding="utf-8") as f:
            artifacts = json.load(f)
        self.freq_map = {int(k): v for k, v in artifacts["event_id_freq_map"].items()}
        self.top_event_ids = artifacts["top_event_ids"]
        self.sparse_cols = artifacts["sparse_presence_columns"]

        with open(columns_path, encoding="utf-8") as f:
            meta = json.load(f)
        self.feature_cols = meta["feature_columns"]

    def _build_feature_row(self, event: dict) -> dict:
        row = {}

        ts = event.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", ""))
        ts = ts or datetime.utcnow()
        row["hour"] = ts.hour
        row["day_of_week"] = ts.weekday()
        row["is_business_hours"] = int(8 <= ts.hour <= 18)
        row["is_weekend"] = int(ts.weekday() >= 5)

        import math

        def is_missing(v):
            if v is None:
                return True
            if isinstance(v, str) and v == "":
                return True
            if isinstance(v, float) and math.isnan(v):
                return True
            return False

        for col in self.sparse_cols:
            row[f"has_{col}"] = int(not is_missing(event.get(col)))

        eid = event.get("event_id")
        eid = int(eid) if eid is not None else None
        row["event_id_freq"] = self.freq_map.get(eid, 0.0)
        for top_eid in self.top_event_ids:
            row[f"eid_{top_eid}"] = int(eid == top_eid)
        row["eid_other"] = int(eid not in self.top_event_ids)

        # Pas d'historique de session disponible pour un evenement isole :
        # valeurs par defaut coherentes avec le comportement du pipeline
        # d'entrainement pour les evenements sans subject_user_name.
        row["events_last_5min_user"] = event.get("events_last_5min_user", 1)
        row["distinct_eventid_last_5min_user"] = event.get("distinct_eventid_last_5min_user", 1)
        row["distinct_computers_last_5min_user"] = event.get("distinct_computers_last_5min_user", 0)
        row["seconds_since_prev_event_user"] = event.get("seconds_since_prev_event_user", -1)

        return row

    def predict(self, event: dict) -> dict:
        row = self._build_feature_row(event)
        X = pd.DataFrame([row])[self.feature_cols]

        stage1_proba = self.stage1_clf.predict_proba(X)[0]
        stage1_classes = self.stage1_clf.classes_
        stage1_pred = stage1_classes[np.argmax(stage1_proba)]
        stage1_confidence = float(np.max(stage1_proba))

        if stage1_pred == "BENIGN":
            return {
                "predicted_label": "benign",
                "predicted_tactic": None,
                "predicted_technique": None,
                "stage1_confidence": stage1_confidence,
                "stage2_confidence": None,
                "is_attack": False,
            }

        entry = self.stage2_models.get(stage1_pred)
        if entry is None:
            label = "UNKNOWN"
            stage2_confidence = None
        elif entry["type"] == "constant":
            label = entry["value"]
            stage2_confidence = 1.0
        else:
            clf2 = entry["value"]
            proba2 = clf2.predict_proba(X)[0]
            label = clf2.classes_[np.argmax(proba2)]
            stage2_confidence = float(np.max(proba2))

        return {
            "predicted_label": label,
            "predicted_tactic": stage1_pred,
            "predicted_technique": None,  # rempli via mitre_reference
            "stage1_confidence": stage1_confidence,
            "stage2_confidence": stage2_confidence,
            "is_attack": True,
        }
