"""Validacion del dataset v3.3 (T-122). Solo lectura: no modifica ningun archivo.

Uso (desde la raiz del repo):
    python dataset/validacion_v3_3/validar_v3_3.py

Compara v3.3 (entrenamiento_v3_3.jsonl, holdout_v3_3.jsonl) contra v3.2 (entrenamiento_v3_2.jsonl, holdout.jsonl).
Sale con codigo 1 si falla algun control BLOQUEANTE; los de "revisar" solo se listan.

Similitud = coseno TF-IDF con unigramas y bigramas sin tildes (simlib.py, Python puro: scipy/scikit-learn no hacen falta).
IDF ajustado siempre sobre v3.2 (entrenamiento + holdout) para que "antes" y "despues" sean comparables.

Controles bloqueantes:
  1  formato: cada linea es JSON con instruction/response (y source opcional), sin vacios; CRLF
  2  duplicados literales de instruction (entrenamiento + holdout)
  3  pares NUEVOS: similitud maxima contra todo el resto (texto completo y pregunta sola) <= 0,75
  4  pares CORREGIDOS: su similitud maxima contra el OTRO conjunto no sube respecto de v3.2
  5  disjuncion con las 100 preguntas de evaluacion (training/evaluacion_alucinacion): pregunta, pregunta+referencia y solape de terminos
  6  nomenclatura: ningun repositorio sin el prefijo techo360- en pares nuevos o corregidos
  7  sin montos en pesos ni emojis en pares nuevos o corregidos
  8  "Segun..." en <= 5 % de los pares nuevos
Informativos: cifras que podrian cambiar con el tiempo, y pares que mencionan RAG o pgvector.
"""
import io
import json
import os
import re
import sys
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(RAIZ, "training", "evaluacion_alucinacion"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from preguntas_generales import PREGUNTAS  # noqa: E402
from simlib import Tfidf, cos, norm  # noqa: E402

UMBRAL_SIMILITUD = 0.75
UMBRAL_EVAL_PREGUNTA = 0.50
UMBRAL_EVAL_COMPLETO = 0.30
UMBRAL_EVAL_SOLAPE = 0.35
MAX_SEGUN = 0.05


def cargar(nombre: str) -> list[dict]:
    with open(os.path.join(RAIZ, "dataset", nombre), encoding="utf-8", newline="") as f:
        crudo = f.read()
    return crudo, [json.loads(l) for l in crudo.split("\r\n") if l.strip()]


def completo(par: dict) -> str:
    return par["instruction"] + " " + par["response"]


def main() -> int:
    problemas: list[str] = []
    crudo_t, tr3 = cargar("entrenamiento_v3_3.jsonl")
    crudo_h, ho3 = cargar("holdout_v3_3.jsonl")
    _, tr2 = cargar("entrenamiento_v3_2.jsonl")
    _, ho2 = cargar("holdout.jsonl")
    n2 = len(tr2)
    print(f"v3.2: entrenamiento {len(tr2)}, holdout {len(ho2)} | v3.3: entrenamiento {len(tr3)}, holdout {len(ho3)}")

    # 1) formato
    for nombre, crudo, lista in (("entrenamiento_v3_3", crudo_t, tr3), ("holdout_v3_3", crudo_h, ho3)):
        if crudo.count("\n") != crudo.count("\r\n"):
            problemas.append(f"{nombre}: hay saltos de linea que no son CRLF")
        for i, p in enumerate(lista, 1):
            if not set(p) <= {"instruction", "response", "source"} or not p.get("instruction", "").strip() or not p.get("response", "").strip():
                problemas.append(f"{nombre} linea {i}: campos invalidos")
    # 2) duplicados literales
    cont = Counter(p["instruction"].strip().lower() for p in tr3 + ho3)
    dups = [q for q, c in cont.items() if c > 1]
    print(f"[2] instrucciones duplicadas: {len(dups)}")
    problemas += [f"instruccion duplicada: {q[:60]}" for q in dups]

    T = Tfidf([completo(p) for p in tr2 + ho2])
    Tq = Tfidf([p["instruction"] for p in tr2 + ho2])
    V = lambda p: T.vec(completo(p))  # noqa: E731
    Vq = lambda p: Tq.vec(p["instruction"])  # noqa: E731

    # pares tocados
    corr_t = [i for i in range(n2) if tr3[i] != tr2[i]]
    corr_h = [i for i in range(len(ho2)) if ho3[i] != ho2[i]]
    nuevos_t = list(range(n2, len(tr3)))
    nuevos_h = list(range(len(ho2), len(ho3)))
    print(f"[0] pares de entrenamiento de v3.2 corregidos: {len(corr_t)} | intactos: {n2 - len(corr_t)} | nuevos: {len(nuevos_t)}")
    print(f"    pares de holdout de v3.2 corregidos: {len(corr_h)} | intactos: {len(ho2) - len(corr_h)} | nuevos: {len(nuevos_h)}")
    for nombre, lista in (("entrenamiento", tr3), ("holdout", ho3)):
        c = Counter("con_fuente" if p.get("source") else "sin_fuente" for p in lista)
        print(f"    {nombre} v3.3: {dict(c)}")

    vt3, vh3 = [V(p) for p in tr3], [V(p) for p in ho3]
    qt3, qh3 = [Vq(p) for p in tr3], [Vq(p) for p in ho3]
    vt2, vh2 = [V(p) for p in tr2], [V(p) for p in ho2]

    # 3) nuevos contra todo lo demas
    print(f"\n[3] nuevos vs resto (umbral {UMBRAL_SIMILITUD})")
    todos_f = [(("T", i), vt3[i]) for i in range(len(tr3))] + [(("H", i), vh3[i]) for i in range(len(ho3))]
    todos_q = [(("T", i), qt3[i]) for i in range(len(tr3))] + [(("H", i), qh3[i]) for i in range(len(ho3))]
    maxf = maxq = 0.0
    for tipo, lista, idx, vf, vq in (("T", tr3, nuevos_t, vt3, qt3), ("H", ho3, nuevos_h, vh3, qh3)):
        for i in idx:
            sf = max(cos(vf[i], w) for k, w in todos_f if k != (tipo, i))
            sq = max(cos(vq[i], w) for k, w in todos_q if k != (tipo, i))
            maxf, maxq = max(maxf, sf), max(maxq, sq)
            if sf > UMBRAL_SIMILITUD or sq > UMBRAL_SIMILITUD:
                problemas.append(f"nuevo {tipo}{i + 1}: similitud texto {sf:.3f} / pregunta {sq:.3f}")
    print(f"    maximo texto completo {maxf:.3f} | maximo pregunta sola {maxq:.3f}")

    # 4) corregidos no suben contra el otro conjunto
    print("\n[4] corregidos: similitud maxima contra el OTRO conjunto, v3.2 -> v3.3 (no puede subir)")
    sube = 0
    for i in corr_t:
        antes = max(cos(vt2[i], w) for w in vh2)
        despues = max(cos(vt3[i], w) for w in vh3)
        if despues > antes + 1e-9:
            sube += 1
            problemas.append(f"corregido T{i + 1}: sube {antes:.3f} -> {despues:.3f}")
    for i in corr_h:
        antes = max(cos(vh2[i], w) for w in vt2)
        despues = max(cos(vh3[i], w) for w in vt3)
        if despues > antes + 1e-9:
            sube += 1
            problemas.append(f"corregido H{i + 1}: sube {antes:.3f} -> {despues:.3f}")
    print(f"    {len(corr_t)} de entrenamiento y {len(corr_h)} de holdout comprobados; que suben: {sube}")

    # 5) disjuncion con las 100 preguntas de evaluacion (todos los pares nuevos y corregidos)
    print("\n[5] disjuncion con las 100 preguntas de evaluacion")
    ev_q = [Tq.vec(q) for _, q, _, _ in PREGUNTAS]
    ev_c = [Tq.vec(q + " " + ref) for _, q, ref, _ in PREGUNTAS]
    ev_t = [set(w for w in norm(q) if len(w) > 3) for _, q, _, _ in PREGUNTAS]
    tocados = [("T", i) for i in corr_t + nuevos_t] + [("H", i) for i in corr_h + nuevos_h]
    mq = mc = mj = 0.0
    for tipo, i in tocados:
        p = (tr3 if tipo == "T" else ho3)[i]
        sq = max(cos(Tq.vec(p["instruction"]), w) for w in ev_q)
        sc = max(cos(Tq.vec(completo(p)), w) for w in ev_c)
        wi = set(w for w in norm(p["instruction"]) if len(w) > 3)
        sj = max((len(wi & wq) / len(wi | wq)) if (wi | wq) else 0.0 for wq in ev_t)
        mq, mc, mj = max(mq, sq), max(mc, sc), max(mj, sj)
        if sq > UMBRAL_EVAL_PREGUNTA or sc > UMBRAL_EVAL_COMPLETO or sj > UMBRAL_EVAL_SOLAPE:
            problemas.append(f"{tipo}{i + 1}: parecido a una pregunta de evaluacion (preg {sq:.2f}, completo {sc:.2f}, solape {sj:.2f})")
    print(f"    {len(tocados)} pares revisados | max pregunta {mq:.3f} | max pregunta+referencia {mc:.3f} | max solape de terminos {mj:.3f}")

    # 6-8) nomenclatura, pesos/emojis, "Segun"
    rx_sin = (r"repositorio[s]? (?:de |del )?(?:backend|frontend|chatbot|infra\w*|proyecci[oó]n|workers)\b|"
              r"\brepo (?:de |del )?(?:backend|frontend|chatbot|infra\w*|proyecci[oó]n)\b|repositorio de infraestructura|repositorio principal")
    rx_pesos = r"\$\s?\d|\bCOP\b|\bmillones de pesos|\bmil millones de pesos|\b\d[\d.,]*\s?pesos\b"
    rx_emoji = "[\U0001F300-\U0001FAFF☀-➿]"
    rx_cifra = r"\b\d{1,3}(?:[.,]\d{3})+\b|\b\d{4,}\b|\b\d+[.,]\d+\s?%|\b\d+\s?%"
    informativas = []
    for tipo, i in tocados:
        p = (tr3 if tipo == "T" else ho3)[i]
        t = completo(p)
        if re.search(rx_sin, t, re.I):
            problemas.append(f"{tipo}{i + 1}: repositorio sin prefijo techo360-")
        if re.search(rx_pesos, t, re.I) or re.search(rx_emoji, t):
            problemas.append(f"{tipo}{i + 1}: monto en pesos o emoji")
        cifras = [m.group(0) for m in re.finditer(rx_cifra, t) if not re.fullmatch(r"(19|20)\d\d", m.group(0))]
        if cifras:
            informativas.append(f"{tipo}{i + 1}: {cifras[:6]}")
    nuevos = [tr3[i] for i in nuevos_t] + [ho3[i] for i in nuevos_h]
    segun = sum(1 for p in nuevos if re.match(r"\s*seg[uú]n\b", p["response"], re.I))
    print(f"\n[6-8] nomenclatura y pesos revisados en {len(tocados)} pares | 'Segun...' en nuevos: {segun}/{len(nuevos)}")
    if nuevos and segun / len(nuevos) > MAX_SEGUN:
        problemas.append(f"'Segun...' supera el {MAX_SEGUN:.0%} de los nuevos")
    print("    cifras a revisar a mano (informativo):")
    for c in informativas:
        print("     ", c)

    # informativo: RAG / pgvector
    print("\n[info] pares que mencionan RAG o pgvector (el RAG NO esta implementado: ver app/ollama_client.py y app/main.py)")
    for tipo, lista in (("T", tr3), ("H", ho3)):
        for i, p in enumerate(lista):
            if re.search(r"\bRAG\b|pgvector", completo(p), re.I):
                print(f"      {tipo}{i + 1}: {p['instruction'][:100]}")

    print(f"\nPROBLEMAS BLOQUEANTES: {len(problemas)}")
    for p in problemas:
        print("  -", p)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
