"""Formateo del dataset 0.4.1 para entrenar (NO entrena, no usa GPU, base de datos ni red). Adaptacion de 5.4 al multi-turno.

    python -m training.dataset_0_4_1.formatear_0_4_1 --dataset ../trabajo-dataset-0.4.1/dataset_0_4_1.jsonl \\
        --tokenizer-dir ../techo360-chatbot/training/adapters/techo360-v3.3 --salida ../trabajo-dataset-0.4.1/formateado

Por par: `mensajes` (system sp-0.4.1-1, historial como turnos de chat y ultimo user con el CONTEXTO fresco) + `response` como ULTIMO
turno del asistente, renderizados con `apply_chat_template` del tokenizer de v3.3 (`date_string` fijo «18 Sep 2026»). PERDIDA SOLO SOBRE
LA ULTIMA RESPUESTA DEL ASISTENTE: `labels = -100` hasta el encabezado del ULTIMO asistente (inclusive); las respuestas previas del
historial son contexto, no objetivo. Se aprende la respuesta y su `<|eot_id|>`. Nada se trunca: se listan los que superan `--max-length`.
Necesita transformers + jinja2 (venv-formateo-5-4, fuera del repo).
"""
import argparse
import hashlib
import json
import random
import statistics
import sys
from pathlib import Path

SHA_SYSTEM = "7e58d55bc020caa4f4fec204c72382cf905535954d64ea9db3d50d1da70ab921"
FECHA = "18 Sep 2026"
MARCADOR_ASSISTANT = "<|start_header_id|>assistant<|end_header_id|>\n\n"
SEMILLA = 42


def renderizar(tok, mensajes: list[dict], respuesta: str) -> str:
    chat = [{"role": m["rol"], "content": m["contenido"]} for m in mensajes] + [{"role": "assistant", "content": respuesta}]
    return tok.apply_chat_template(chat, tokenize=False, add_generation_prompt=False, date_string=FECHA)


def tokenizar(tok, texto: str) -> tuple[list[int], list[int]]:
    ids = tok(texto, add_special_tokens=False)["input_ids"]
    corte = texto.rindex(MARCADOR_ASSISTANT) + len(MARCADOR_ASSISTANT)  # el ULTIMO encabezado de asistente
    prefijo = tok(texto[:corte], add_special_tokens=False)["input_ids"]
    if ids[: len(prefijo)] != prefijo:
        raise SystemExit("ABORTO: el prefijo tokenizado por separado no coincide con el inicio del texto completo")
    n = len(prefijo)
    return ids, [-100] * n + ids[n:]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, type=Path)
    ap.add_argument("--tokenizer-dir", required=True, type=Path)
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--max-length", type=int, default=2048)
    ap.add_argument("--prompt", type=Path, default=Path(__file__).resolve().parents[2] / "prompts" / "sp-0.4.1-1.txt")
    args = ap.parse_args(argv)

    from transformers import AutoTokenizer

    crudo = args.prompt.read_bytes()
    if hashlib.sha256(crudo).hexdigest() != SHA_SYSTEM:
        raise SystemExit("ABORTO: el sha256 de sp-0.4.1-1.txt no es el esperado")
    tok = AutoTokenizer.from_pretrained(str(args.tokenizer_dir))
    filas = [json.loads(l) for l in args.dataset.read_text(encoding="utf-8").splitlines() if l.strip()]
    items, sin_system, historial_n = [], 0, 0
    for r in filas:
        if r["mensajes"][0]["contenido"] != crudo.decode("utf-8"):
            sin_system += 1
            continue
        texto = renderizar(tok, r["mensajes"], r["response"])
        ids, labels = tokenizar(tok, texto)
        previos = sum(1 for m in r["mensajes"] if m["rol"] == "assistant")
        historial_n += 1 if previos else 0
        # comprobacion: ninguna respuesta previa del historial es entrenable
        assert tok.decode(ids[: next(i for i, l in enumerate(labels) if l != -100)]).count(MARCADOR_ASSISTANT) == previos + 1
        items.append({"input_ids": ids, "attention_mask": [1] * len(ids), "labels": labels, "id": r["id"], "familia": r["familia"]})
    if sin_system:
        raise SystemExit(f"ABORTO: {sin_system} pares sin el system sp-0.4.1-1")
    orden = list(range(len(items)))
    random.Random(SEMILLA).shuffle(orden)
    args.salida.mkdir(parents=True, exist_ok=True)
    destino = args.salida / "train_tokenizado.jsonl"
    with destino.open("w", encoding="utf-8", newline="\n") as f:
        for i in orden:
            f.write(json.dumps(items[i], ensure_ascii=False, separators=(",", ":")) + "\n")
    largos = [len(x["input_ids"]) for x in items]
    excede = [{"id": x["id"], "tokens": len(x["input_ids"])} for x in items if len(x["input_ids"]) > args.max_length]
    entrenables = sum(sum(1 for l in x["labels"] if l != -100) for x in items)
    resumen = {
        "pares": len(items), "con_historial": historial_n, "max_tokens": max(largos), "mediana": int(statistics.median(largos)),
        "p95": sorted(largos)[int(0.95 * (len(largos) - 1))], "excede_max_length": len(excede), "max_length": args.max_length,
        "tokens_entrenables": entrenables, "tokens_totales": sum(largos), "sha256_train_tokenizado": hashlib.sha256(destino.read_bytes()).hexdigest(),
        "sha256_dataset": hashlib.sha256(args.dataset.read_bytes()).hexdigest(), "date_string": FECHA,
    }
    (args.salida / "resumen_formateo.json").write_text(json.dumps({**resumen, "excede": excede}, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(resumen, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
