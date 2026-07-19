from __future__ import annotations

from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from src.copilot.model_inference import DetectionEngine
from src.copilot.mitre_reference import enrich_prediction
from src.copilot.ollama_client import generate_explanation


class CopilotState(TypedDict):
    event: dict
    prediction: Optional[dict]
    explanation: Optional[str]
    report: Optional[str]


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = DetectionEngine()
    return _engine


def node_predict(state: CopilotState) -> CopilotState:
    engine = get_engine()
    prediction = engine.predict(state["event"])
    prediction = enrich_prediction(prediction)
    return {**state, "prediction": prediction}


def format_confidence(value):
    if value is None:
        return "N/A"
    return f"{value:.2%}"


def node_explain(state: CopilotState) -> CopilotState:
    pred = state["prediction"]

    if not pred["is_attack"]:
        return {**state, "explanation": "Evenement classe comme activite normale (benign)."}

    stage1_conf_str = format_confidence(pred.get("stage1_confidence"))
    stage2_conf_str = format_confidence(pred.get("stage2_confidence"))

    prompt = (
        "Tu es un analyste SOC senior specialise en Active Directory.\n"
        "Un systeme de detection a identifie l'evenement suivant :\n\n"
        f"- Technique detectee : {pred['predicted_label']}\n"
        f"- Description : {pred['description']}\n"
        f"- Tactique MITRE ATT&CK : {pred['predicted_tactic']} ({pred['tactic_name']})\n"
        f"- Technique MITRE ATT&CK : {pred['predicted_technique']}\n"
        f"- Confiance stage 1 (tactique) : {stage1_conf_str}\n"
        f"- Confiance stage 2 (technique) : {stage2_conf_str}\n\n"
        "Redige en francais une explication courte (4-5 phrases) pour un analyste SOC :\n"
        "1. Ce que represente cette technique concretement\n"
        "2. Pourquoi elle est dangereuse dans un environnement Active Directory\n"
        "3. Une premiere action de triage recommandee\n"
    )
    explanation = generate_explanation(prompt)
    return {**state, "explanation": explanation}


def node_format_report(state: CopilotState) -> CopilotState:
    pred = state["prediction"]
    severity = "CRITIQUE" if pred["is_attack"] else "INFO"

    stage1_conf_str = format_confidence(pred.get("stage1_confidence"))
    stage2_conf_str = format_confidence(pred.get("stage2_confidence"))

    report = (
        "=== RAPPORT SOC ===\n"
        f"Severite       : {severity}\n"
        f"Technique      : {pred['predicted_label']}\n"
        f"Tactique MITRE : {pred.get('predicted_tactic') or '-'} ({pred.get('tactic_name') or '-'})\n"
        f"Technique MITRE: {pred.get('predicted_technique') or '-'}\n"
        f"Confiance      : stage1={stage1_conf_str}, stage2={stage2_conf_str}\n\n"
        "Explication analyste :\n"
        f"{state['explanation']}\n"
    )
    return {**state, "report": report}


def build_graph():
    graph = StateGraph(CopilotState)
    graph.add_node("predict", node_predict)
    graph.add_node("explain", node_explain)
    graph.add_node("format_report", node_format_report)

    graph.set_entry_point("predict")
    graph.add_edge("predict", "explain")
    graph.add_edge("explain", "format_report")
    graph.add_edge("format_report", END)

    return graph.compile()


def run_copilot(event: dict) -> str:
    graph = build_graph()
    result = graph.invoke({"event": event, "prediction": None, "explanation": None, "report": None})
    return result["report"]
