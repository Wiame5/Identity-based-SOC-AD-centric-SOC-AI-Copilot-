"""
KEEP API server — bridges the KEEP web frontend to the existing Python
detection pipeline (DetectionEngine) and the local Ollama LLM.

Run from the project root (same folder as main.py, src/, data/, models/):
    python api_server.py

Then open http://localhost:5000 in a browser — the frontend is served
directly by this server, so no separate web server or CORS setup is needed.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).parent))

from src.copilot.model_inference import DetectionEngine
from src.copilot.mitre_reference import enrich_prediction, ACTIONS
from src.copilot.ollama_client import generate_explanation, warmup_model

APP_ROOT = Path(__file__).parent
WEB_DIR = APP_ROOT / "web"
EVENTS_PATH = APP_ROOT / "data" / "processed" / "events_combined.parquet"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")

_engine: DetectionEngine | None = None
_events_df: pd.DataFrame | None = None
_ollama_ready = False


def get_engine() -> DetectionEngine:
    global _engine
    if _engine is None:
        print("[KEEP API] Loading detection models...")
        _engine = DetectionEngine()
        print("[KEEP API] Models loaded.")
    return _engine


def get_events_df() -> pd.DataFrame:
    global _events_df
    if _events_df is None:
        if not EVENTS_PATH.exists():
            raise FileNotFoundError(
                f"Dataset not found at {EVENTS_PATH}. "
                "Run src.cleaning.build_dataset first."
            )
        _events_df = pd.read_parquet(EVENTS_PATH)
    return _events_df


def clean_value(v):
    """Convert pandas/numpy scalars into plain JSON-safe Python values."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        val = float(v)
        return None if math.isnan(val) else val
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: clean_value(x) for k, x in v.items()}
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def row_to_clean_dict(row: pd.Series) -> dict:
    return {k: clean_value(v) for k, v in row.to_dict().items() if k != "raw"}


DISPLAY_FIELD_ORDER = [
    "event_id", "subject_user_name", "subject_domain_name", "subject_user_sid",
    "target_user_name", "target_domain_name", "logon_type",
    "ticket_encryption_type", "authentication_package",
    "object_name", "object_type", "access_mask", "properties",
    "computer",
]


def build_display_fields(clean_row: dict) -> dict:
    fields = {}
    for key in DISPLAY_FIELD_ORDER:
        val = clean_row.get(key)
        if val is not None:
            fields[key] = val
    if not fields:
        fields["event_id"] = clean_row.get("event_id")
        fields["computer"] = clean_row.get("computer")
    return fields


def dn_from_computer(computer: str | None) -> list[str]:
    if not computer:
        return ["DC=unknown"]
    parts = computer.split(".")
    if len(parts) < 2:
        return [f"CN={computer}"]
    host = parts[0]
    domain = ",".join(f"DC={p}" for p in parts[1:])
    return [domain, f"CN={host}"]


@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/api/health")
def health():
    ollama_ok = False
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        ollama_ok = r.ok
    except Exception:
        ollama_ok = False
    return jsonify({"status": "ok", "ollama_connected": ollama_ok})


@app.route("/api/events")
def api_events():
    limit = int(request.args.get("limit", 12))
    df = get_events_df()

    priority_labels = [
        "pass_the_hash", "mimikatz", "dcsync_empire", "dcsync_convenant",
        "kerberos_createnetonly", "ntds_dump_shadowcopy", "benign",
    ]
    parts = []
    for label in priority_labels:
        subset = df[df["label"] == label]
        if len(subset):
            parts.append(subset.sample(min(2, len(subset)), random_state=None))
    sample = pd.concat(parts).head(limit) if parts else df.sample(min(limit, len(df)))
    sample = sample.sort_values("timestamp", ascending=False)

    engine = get_engine()
    out = []
    for idx, row in sample.iterrows():
        clean_row = row_to_clean_dict(row)
        try:
            pred = enrich_prediction(engine.predict(clean_row))
        except Exception as exc:
            print(f"[KEEP API] Prediction failed for row {idx}: {exc}")
            continue

        ts = clean_row.get("timestamp")
        time_str = ts.split("T")[1][:8] if isinstance(ts, str) and "T" in ts else (ts or "")

        out.append({
            "id": str(idx),
            "time": time_str,
            "dn": dn_from_computer(clean_row.get("computer")),
            "host": clean_row.get("computer") or "UNKNOWN",
            "user": clean_row.get("subject_user_name") or "SYSTEM",
            "eventId": clean_row.get("event_id"),
            "technique": pred["predicted_label"],
            "tacticKey": pred["predicted_tactic"] or "BENIGN",
            "mitre": pred.get("predicted_technique"),
            "stage1": round(pred["stage1_confidence"] * 100, 1) if pred.get("stage1_confidence") is not None else None,
            "stage2": round(pred["stage2_confidence"] * 100, 1) if pred.get("stage2_confidence") is not None else None,
            "severity": "critical" if pred["is_attack"] else "info",
            "fields": build_display_fields(clean_row),
            "raw": clean_row,
        })

    return jsonify(out)


def build_soc_prompt(prediction: dict) -> str:
    stage1 = prediction.get("stage1_confidence")
    stage2 = prediction.get("stage2_confidence")
    stage1_str = f"{stage1:.2%}" if stage1 is not None else "N/A"
    stage2_str = f"{stage2:.2%}" if stage2 is not None else "N/A"

    return (
        "You are a senior SOC analyst assistant specialized in Active Directory.\n"
        "A detection system flagged the following event:\n\n"
        f"- Technique: {prediction.get('predicted_label')}\n"
        f"- Description: {prediction.get('description')}\n"
        f"- MITRE tactic: {prediction.get('predicted_tactic')} ({prediction.get('tactic_name')})\n"
        f"- MITRE technique: {prediction.get('predicted_technique')}\n"
        f"- Stage 1 (tactic) confidence: {stage1_str}\n"
        f"- Stage 2 (technique) confidence: {stage2_str}\n\n"
        "Write a short analyst-facing explanation in English (4-5 sentences):\n"
        "1. What this technique concretely means\n"
        "2. Why it matters in an Active Directory environment\n"
        "3. A concrete first triage action\n"
    )


@app.route("/api/related_events", methods=["POST"])
def api_related_events():
    body = request.get_json(force=True)
    event = body.get("event") or {}
    computer = event.get("computer")
    ts_raw = event.get("timestamp")
    current_eid = event.get("event_id")

    if not computer or not ts_raw:
        return jsonify({"related": []})

    try:
        center = pd.to_datetime(ts_raw)
    except Exception:
        return jsonify({"related": []})

    df = get_events_df()
    window = pd.Timedelta(minutes=5)
    ts_series = pd.to_datetime(df["timestamp"], errors="coerce")

    mask = (
        (df["computer"] == computer)
        & (ts_series >= center - window)
        & (ts_series <= center + window)
        & ~((ts_series == center) & (df["event_id"] == current_eid))
    )
    subset = df[mask].sort_values("timestamp").head(6)

    related = []
    for _, row in subset.iterrows():
        related.append({
            "time": clean_value(row.get("timestamp")),
            "event_id": clean_value(row.get("event_id")),
            "label": row.get("label"),
        })

    return jsonify({"related": related, "window_minutes": 5})


@app.route("/api/copilot/analyze", methods=["POST"])
def api_analyze():
    body = request.get_json(force=True)
    event = body.get("event")
    if not event:
        return jsonify({"error": "missing 'event'"}), 400

    engine = get_engine()
    prediction = enrich_prediction(engine.predict(event))

    if not prediction["is_attack"]:
        explanation = "Event classified as normal activity (benign). No further analysis required."
        actions = []
    else:
        prompt = build_soc_prompt(prediction)
        explanation = generate_explanation(prompt)
        actions = ACTIONS.get(prediction["predicted_label"], [])

    return jsonify({"prediction": prediction, "explanation": explanation, "actions": actions})


@app.route("/api/copilot/ask", methods=["POST"])
def api_ask():
    body = request.get_json(force=True)
    event = body.get("event") or {}
    question = body.get("question") or ""
    prediction = body.get("prediction")

    if not prediction:
        engine = get_engine()
        prediction = enrich_prediction(engine.predict(event))

    stage1 = prediction.get("stage1_confidence")
    stage2 = prediction.get("stage2_confidence")

    prompt = (
        "You are a senior SOC analyst assistant specialized in Active Directory. "
        "An analyst is reviewing this detection:\n"
        f"- Technique: {prediction.get('predicted_label')}\n"
        f"- MITRE tactic: {prediction.get('predicted_tactic')}\n"
        f"- MITRE technique: {prediction.get('predicted_technique')}\n"
    )
    if stage1 is not None:
        prompt += f"- Stage 1 confidence: {stage1:.2%}\n"
    if stage2 is not None:
        prompt += f"- Stage 2 confidence: {stage2:.2%}\n"
    prompt += (
        f"\nThe analyst asks: \"{question}\"\n\n"
        "Answer concisely (2-4 sentences), in English, as a SOC assistant would."
    )

    answer = generate_explanation(prompt)
    return jsonify({"answer": answer})


if __name__ == "__main__":
    import threading

    if not WEB_DIR.exists():
        print(f"[KEEP API] WARNING: {WEB_DIR} does not exist. "
              "Place the frontend index.html inside a 'web' folder next to this script.")

    print("[KEEP API] Starting Ollama warmup in the background (~1-2 min on first run)...")
    threading.Thread(target=warmup_model, daemon=True).start()

    print("[KEEP API] Starting on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
