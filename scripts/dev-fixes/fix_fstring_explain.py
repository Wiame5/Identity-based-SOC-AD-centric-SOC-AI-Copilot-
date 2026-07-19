import re
from pathlib import Path

path = Path("src/copilot/langgraph_pipeline.py")
content = path.read_text(encoding="utf-8")

old_node_explain = '''def node_explain(state: CopilotState) -> CopilotState:
    pred = state["prediction"]

    if not pred["is_attack"]:
        return {**state, "explanation": "Evenement classe comme activite normale (benign)."}

    prompt = f"""Tu es un analyste SOC senior specialise en Active Directory.
Un systeme de detection a identifie l'evenement suivant :

- Technique detectee : {pred['predicted_label']}
- Description : {pred['description']}
- Tactique MITRE ATT&CK : {pred['predicted_tactic']} ({pred['tactic_name']})
- Technique MITRE ATT&CK : {pred['predicted_technique']}
- Confiance stage 1 (tactique) : {pred['stage1_confidence']:.2%}
- Confiance stage 2 (technique) : {pred['stage2_confidence']:.2% if pred['stage2_confidence'] else 'N/A'}

Redige en francais une explication courte (4-5 phrases) pour un analyste SOC :
1. Ce que represente cette technique concretement
2. Pourquoi elle est dangereuse dans un environnement Active Directory
3. Une premiere action de triage recommandee
"""
    explanation = generate_explanation(prompt)
    return {**state, "explanation": explanation}'''

new_node_explain = '''def node_explain(state: CopilotState) -> CopilotState:
    pred = state["prediction"]

    if not pred["is_attack"]:
        return {**state, "explanation": "Evenement classe comme activite normale (benign)."}

    stage1_conf_str = f"{pred[\\'stage1_confidence\\']:.2%}"
    stage2_conf_str = f"{pred[\\'stage2_confidence\\']:.2%}" if pred.get("stage2_confidence") is not None else "N/A"

    prompt = f"""Tu es un analyste SOC senior specialise en Active Directory.
Un systeme de detection a identifie l\\'evenement suivant :

- Technique detectee : {pred[\\'predicted_label\\']}
- Description : {pred[\\'description\\']}
- Tactique MITRE ATT&CK : {pred[\\'predicted_tactic\\']} ({pred[\\'tactic_name\\']})
- Technique MITRE ATT&CK : {pred[\\'predicted_technique\\']}
- Confiance stage 1 (tactique) : {stage1_conf_str}
- Confiance stage 2 (technique) : {stage2_conf_str}

Redige en francais une explication courte (4-5 phrases) pour un analyste SOC :
1. Ce que represente cette technique concretement
2. Pourquoi elle est dangereuse dans un environnement Active Directory
3. Une premiere action de triage recommandee
"""
    explanation = generate_explanation(prompt)
    return {**state, "explanation": explanation}'''

if old_node_explain not in content:
    print("[ERREUR] Bloc node_explain introuvable")
else:
    content = content.replace(old_node_explain, new_node_explain)
    path.write_text(content, encoding="utf-8")
    print("[OK] node_explain corrige")
