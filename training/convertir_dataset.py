"""Convierte un dataset de pares (jsonl) al formato de entrenamiento de Llama 3.2 (T-70, reconstruido en T-122).

Cada linea de la entrada es {"instruction", "response"[, "source"]}. La salida tiene una linea
{"text": "<prompt completo>"} por par, con el chat template oficial de meta-llama/Llama-3.2-3B-Instruct
(`apply_chat_template`, no una plantilla manual). El campo `source` NUNCA se pasa al prompt.

Decisiones que hacen la conversion reproducible (ver training/README.md):
  - system prompt fijo, identico al de app/ollama_client.py (399 caracteres; se comprueba al arrancar);
  - fecha fija en el template (`date_string="18 Sep 2026"`), para que volver a correr no reescriba todas las lineas;
  - salida UTF-8 literal (`ensure_ascii=False`) con saltos de linea CRLF, como el archivo original de v3.2.

Uso:
    python training/convertir_dataset.py dataset/entrenamiento_v3_3.jsonl dataset/entrenamiento_formateado_v3_3/train.jsonl
    python training/convertir_dataset.py --verificar     # regenera v3.2 y exige igualdad BYTE A BYTE con
                                                         # dataset/entrenamiento_formateado_v3_2/train.jsonl

Requiere `transformers` (no hace falta PyTorch) y acceso (o cache local) al tokenizer de
meta-llama/Llama-3.2-3B-Instruct. La comprobacion de T-122 se hizo con transformers 5.19.0.
"""
import ast
import hashlib
import json
import os
import sys

from transformers import AutoTokenizer

MODELO = "meta-llama/Llama-3.2-3B-Instruct"
FECHA_FIJA_TEMPLATE = "18 Sep 2026"
LONGITUD_SYSTEM_PROMPT = 399
SALTO_DE_LINEA = "\r\n"

SYSTEM_PROMPT = (
    "Eres el asistente virtual de Techo 360, una plataforma que analiza la "
    "pobreza y el deficit de vivienda en los municipios de Colombia. "
    "Respondes en espanol de forma clara y precisa sobre el Score de "
    "Privacion y los indicadores de Techo 360, y sobre la politica publica "
    "colombiana de vivienda y pobreza (IPM, deficit habitacional, cobertura "
    "de acueducto y alcantarillado) en la que se basa el sistema."
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _system_prompt_de_ollama_client() -> str:
    """Lee SYSTEM_PROMPT de app/ollama_client.py sin importarlo (evita depender de httpx)."""
    with open(os.path.join(RAIZ, "app", "ollama_client.py"), encoding="utf-8") as f:
        arbol = ast.parse(f.read())
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(getattr(t, "id", None) == "SYSTEM_PROMPT" for t in nodo.targets):
            return ast.literal_eval(nodo.value)
    raise RuntimeError("No se encontro SYSTEM_PROMPT en app/ollama_client.py")


def comprobar_system_prompt() -> None:
    assert len(SYSTEM_PROMPT) == LONGITUD_SYSTEM_PROMPT, f"SYSTEM_PROMPT mide {len(SYSTEM_PROMPT)}, se esperaban {LONGITUD_SYSTEM_PROMPT}"
    assert SYSTEM_PROMPT == _system_prompt_de_ollama_client(), "SYSTEM_PROMPT difiere del de app/ollama_client.py"


def construir_mensajes(par: dict) -> list[dict]:
    """`source` no se lee: nunca llega al prompt."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": par["instruction"]},
        {"role": "assistant", "content": par["response"]},
    ]


def convertir(entrada: str, salida: str) -> int:
    comprobar_system_prompt()
    tokenizer = AutoTokenizer.from_pretrained(MODELO)
    with open(entrada, encoding="utf-8") as f:
        pares = [json.loads(linea) for linea in f if linea.strip()]
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline=SALTO_DE_LINEA) as out:
        for par in pares:
            texto = tokenizer.apply_chat_template(
                construir_mensajes(par),
                tokenize=False,
                add_generation_prompt=False,
                date_string=FECHA_FIJA_TEMPLATE,
            )
            out.write(json.dumps({"text": texto}, ensure_ascii=False) + "\n")  # newline= lo traduce a CRLF
    return len(pares)


def _sha256(ruta: str) -> str:
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verificar() -> int:
    """Comprobacion de reproducibilidad: v3.2 -> train.jsonl debe salir identico byte a byte."""
    entrada = os.path.join(RAIZ, "dataset", "entrenamiento_v3_2.jsonl")
    esperado = os.path.join(RAIZ, "dataset", "entrenamiento_formateado_v3_2", "train.jsonl")
    temporal = os.path.join(RAIZ, "dataset", "_verificacion_v3_2_train.jsonl")
    try:
        n = convertir(entrada, temporal)
        a, b = _sha256(esperado), _sha256(temporal)
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)
    print(f"{n} pares convertidos | sha256 esperado {a[:16]}... | regenerado {b[:16]}...")
    if a != b:
        print("FALLO: la conversion NO reproduce train.jsonl de v3.2 byte a byte")
        return 1
    print("OK: la conversion reproduce train.jsonl de v3.2 byte a byte")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--verificar":
        sys.exit(verificar())
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(f"{convertir(sys.argv[1], sys.argv[2])} pares convertidos")
