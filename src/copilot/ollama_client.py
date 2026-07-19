from __future__ import annotations

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"

NO_MARKDOWN_INSTRUCTION = (
    "Do not use markdown formatting: no asterisks, no bullet points, no headers. "
    "Write in plain conversational prose only."
)


def warmup_model(model: str = DEFAULT_MODEL, timeout: int = 180):
    """Premier appel pour charger le modele en memoire avant la vraie demo."""
    try:
        print(f"[Ollama] Chargement du modele '{model}' en memoire (peut prendre 1-2 min)...")
        requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": "test", "stream": False},
            timeout=timeout,
        )
        print("[Ollama] Modele charge.")
    except Exception as exc:
        print(f"[Ollama] Warmup echoue: {exc}")


def generate_explanation(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 240) -> str:
    import json as json_lib
    full_prompt = f"{prompt}\n\n{NO_MARKDOWN_INSTRUCTION}"
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": True,
                "options": {"num_predict": 220},
            },
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()

        chunks = []
        for line in response.iter_lines():
            if not line:
                continue
            data = json_lib.loads(line)
            chunks.append(data.get("response", ""))
            if data.get("done"):
                break

        return "".join(chunks).strip()
    except requests.exceptions.ConnectionError:
        return (
            "[Ollama indisponible] Verifiez que le service tourne (ollama serve) "
            f"et que le modele '{model}' est installe (ollama pull {model})."
        )
    except requests.exceptions.ReadTimeout:
        return "[Ollama timeout] La generation a pris trop de temps, reessayez."
    except Exception as exc:
        return f"[Erreur Ollama] {exc}"
