import re
from pathlib import Path

path = Path("src/copilot/langgraph_pipeline.py")
content = path.read_text(encoding="utf-8")

old_report = '''def node_format_report(state: CopilotState) -> CopilotState:
    pred = state["prediction"]
    severity = "CRITIQUE" if pred["is_attack"] else "INFO"

    report = f"""=== RAPPORT SOC ===
Severite       : {severity}
Technique      : {pred['predicted_label']}
Tactique MITRE : {pred['predicted_tactic'] or '-'} ({pred.get('tactic_name') or '-'})
Technique MITRE: {pred['predicted_technique'] or '-'}
Confiance      : stage1={pred['stage1_confidence']:.2%}, stage2={pred['stage2_confidence']:.2% if pred['stage2_confidence'] else 'N/A'}

Explication analyste :
{state['explanation']}
"""
    return {**state, "report": report}'''

new_report = '''def node_format_report(state: CopilotState) -> CopilotState:
    pred = state["prediction"]
    severity = "CRITIQUE" if pred["is_attack"] else "INFO"

    stage1_conf_str = f"{pred[\\'stage1_confidence\\']:.2%}"
    stage2_conf_str = f"{pred[\\'stage2_confidence\\']:.2%}" if pred.get("stage2_confidence") is not None else "N/A"

    report = f"""=== RAPPORT SOC ===
Severite       : {severity}
Technique      : {pred[\\'predicted_label\\']}
Tactique MITRE : {pred[\\'predicted_tactic\\'] or \\'-\\'} ({pred.get(\\'tactic_name\\') or \\'-\\'})
Technique MITRE: {pred[\\'predicted_technique\\'] or \\'-\\'}
Confiance      : stage1={stage1_conf_str}, stage2={stage2_conf_str}

Explication analyste :
{state[\\'explanation\\']}
"""
    return {**state, "report": report}'''

if old_report not in content:
    print("[ERREUR] Bloc node_format_report introuvable")
else:
    content = content.replace(old_report, new_report)
    path.write_text(content, encoding="utf-8")
    print("[OK] node_format_report corrige")
