import re
from pathlib import Path

path = Path("src/copilot/ollama_client.py")
content = path.read_text(encoding="utf-8")

old_func = '''def generate_explanation(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 120) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return (
            "[Ollama indisponible] Verifiez que le service tourne (ollama serve) "
            f"et que le modele '{model}' est installe (ollama pull {model})."
        )
    except requests.exceptions.ReadTimeout:
        return "[Ollama timeout] La generation a pris trop de temps, reessayez."
    except Exception as exc:
        return f"[Erreur Ollama] {exc}"'''

new_func = '''def generate_explanation(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 180) -> str:
    import json as json_lib
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {"num_predict": 200},
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
        return f"[Erreur Ollama] {exc}"'''

if old_func not in content:
    print("[ERREUR] Bloc introuvable")
else:
    content = content.replace(old_func, new_func)
    path.write_text(content, encoding="utf-8")
    print("[OK] generate_explanation passe en mode streaming, num_predict=200, timeout=180")
