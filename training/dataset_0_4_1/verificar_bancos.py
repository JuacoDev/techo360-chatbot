"""Verifica los bancos de 0.4.1 (7.3 Fase A) y escribe el informe.

    python -m training.dataset_0_4_1.verificar_bancos [--salida informe_fase_a.md]

Sale con codigo 1 si algun control falla. No usa BD, red ni modelos.
"""
import argparse
import hashlib
import sys
from pathlib import Path

from . import catalogo as cat
from . import controles as ct
from . import preguntas as pq
from . import respuestas as rp

RAIZ_CHATBOT = Path(__file__).resolve().parents[2]
RAIZ_MONOREPO = RAIZ_CHATBOT.parent


def sha(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(Path(__file__).with_name("informe_fase_a.md")))
    ap.add_argument("--raiz-monorepo", default=str(RAIZ_MONOREPO))
    args = ap.parse_args(argv)

    fallos: list[str] = []
    cp = ct.controlar_preguntas()
    cr = ct.controlar_respuestas()
    for sub, lista in {**{f"preguntas/{k}": v for k, v in cp.items()}, **{f"respuestas/{k}": v for k, v in cr.items()}}.items():
        fallos += [f"{sub}: {x}" for x in lista]
    fallos += [f"notas: {x}" for x in ct.controlar_notas()]
    fallos += [f"listas: {x}" for x in ct.controlar_listas()]
    fallos += [f"turno previo: {x}" for x in ct.controlar_turno_previo()]
    fallos += [f"diversidad: {x}" for x in ct.controlar_diversidad()]
    fallos += [f"cuotas: {x}" for x in ct.controlar_cuotas()]
    conjuntos, faltantes = ct.cargar_conjuntos_evaluacion(RAIZ_CHATBOT, Path(args.raiz_monorepo))
    dedup, maximos = ct.controlar_dedup(conjuntos)
    fallos += [f"dedup: {x}" for x in dedup]

    cnt_p, tot_p = ct.distribucion_aperturas(pq.BANCOS)
    cnt_r, tot_r = ct.distribucion_aperturas(rp.PLANTILLAS)
    lineas = [
        "# Fase A de 7.3: bancos de preguntas y plantillas de respuesta (G1–G6, F+, HS y listas)", "",
        f"Resultado: {'**sin fallos**' if not fallos else f'**{len(fallos)} fallos**'}. Generado por `python -m training.dataset_0_4_1.verificar_bancos`.", "",
        "## Conteos por subfamilia", "",
        "| Subfamilia | Cuota | Preguntas | Plantillas de respuesta | Con bloque |", "|---|---:|---:|---:|:--:|",
    ]
    for sub, c in cat.CUOTAS.items():
        lineas.append(f"| {sub} | {c} | {len(pq.BANCOS[sub])} | {len(rp.PLANTILLAS[sub])} | {'sí' if sub in rp.CON_BLOQUE else 'no'} |")
    lineas += [
        f"| **Total** | **{sum(cat.CUOTAS.values())}** | **{sum(len(v) for v in pq.BANCOS.values())}** | **{sum(len(v) for v in rp.PLANTILLAS.values())}** | |", "",
        "Por familia: " + ", ".join(f"{k} {v}" for k, v in cat.CUOTAS_FAMILIA.items()) + " (G 410 + F+ 60 + HS 220 = 690; H 400 queda para la Fase B).", "",
        "Listas (adenda 7.1b §2), plantillas que regeneran A3/A4/A5 con ≥ 3 elementos: " + ", ".join(f"{k} {len(v[0])} introducciones" for k, v in __import__("training.dataset_0_4_1.listas", fromlist=["x"]).TIPOS.items()) + ".", "",
        "## Diversidad (ponderada por cuota; dos primeras palabras)", "",
        "| Medida | Preguntas | Respuestas |", "|---|---:|---:|",
        f"| Apertura más frecuente | {cnt_p.most_common(1)[0][0]} ({cnt_p.most_common(1)[0][1] / tot_p:.1%}) | {cnt_r.most_common(1)[0][0]} ({cnt_r.most_common(1)[0][1] / tot_r:.1%}) |",
        f"| «Según…» | {sum(w for a, w in cnt_p.items() if a.startswith('segun')) / tot_p:.1%} | {sum(w for a, w in cnt_r.items() if a.startswith('segun')) / tot_r:.1%} |",
        f"| Aperturas distintas | {len(cnt_p)} | {len(cnt_r)} |", "",
        "Límites: ninguna apertura > 8 %, «Según…» ≤ 3 %.", "",
        "## Deduplicación (similitud < 0,75, TF-IDF de simlib)", "",
        "Máximo coseno de cualquier formulación (renderizada con 3 muestras de huecos) contra cada conjunto de evaluación:", "",
        "| Conjunto | Preguntas cargadas | Máximo coseno |", "|---|---:|---:|",
    ]
    for n, qs in conjuntos.items():
        lineas.append(f"| {n} | {len(qs)} | {maximos[n]:.3f} |")
    if faltantes:
        lineas += ["", "No cargados o parciales:", ""] + [f"- {f}" for f in faltantes]
    lineas += ["", "## Alcance de los controles", "",
               "Estos controles son de **banco** (plantillas con huecos de muestra). Los controles por **par** (prueba dorada contra el ensamblador, validador 4.5, tokens medidos, dedup contra el dataset real) corren en la Fase B con el generador completo.", ""]
    if fallos:
        lineas += ["## Fallos", ""] + [f"- {f}" for f in fallos]
    Path(args.salida).write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(fallos)} fallos; informe en {args.salida}")
    for f in fallos[:60]:
        print(" -", f)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
