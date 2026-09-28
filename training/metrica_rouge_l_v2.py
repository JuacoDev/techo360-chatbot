"""T-93 (repetido): ROUGE-L (F1) para base, v1 y v2 contra la
`referencia_holdout`, usando las generaciones de evaluar_holdout_v2.py.
Misma implementacion de ROUGE-L (LCS puro, sin dependencias nuevas) que
la corrida anterior -- ver metrica_rouge_l.py para la justificacion
completa de por que ROUGE-L en vez de embeddings.
"""

import json
import statistics
from pathlib import Path

from metrica_rouge_l import rouge_l_f1

DIR_TRAINING = Path(__file__).resolve().parent
GENERACIONES_PATH = DIR_TRAINING / "eval_holdout_generaciones_v2.json"


def main():
    with GENERACIONES_PATH.open("r", encoding="utf-8") as f:
        generaciones = json.load(f)

    resultados = []
    for g in generaciones:
        ref = g["referencia_holdout"]
        r_base = rouge_l_f1(g["respuesta_base"], ref)
        r_v1 = rouge_l_f1(g["respuesta_v1"], ref)
        r_v2 = rouge_l_f1(g["respuesta_v2"], ref)
        resultados.append({
            "indice": g["indice"],
            "categoria": g["categoria"],
            "rouge_l_base": round(r_base, 4),
            "rouge_l_v1": round(r_v1, 4),
            "rouge_l_v2": round(r_v2, 4),
            "delta_v2_vs_v1": round(r_v2 - r_v1, 4),
            "delta_v2_vs_base": round(r_v2 - r_base, 4),
        })

    print(f"{'idx':>3} {'categoria':>11} {'base':>7} {'v1':>7} {'v2':>7} {'v2-v1':>7}")
    for r in resultados:
        print(f"{r['indice']:>3} {r['categoria']:>11} {r['rouge_l_base']:>7.4f} "
              f"{r['rouge_l_v1']:>7.4f} {r['rouge_l_v2']:>7.4f} {r['delta_v2_vs_v1']:>+7.4f}")

    def promedio(campo, filtro=None):
        vals = [r[campo] for r in resultados if filtro is None or r["categoria"] == filtro]
        return statistics.mean(vals) if vals else None

    print("\n=== Promedios ROUGE-L (F1) ===")
    for nombre, filtro in [("General", None), ("Con fuente", "con_fuente"), ("Sin fuente", "sin_fuente")]:
        print(f"{nombre:12} -- base: {promedio('rouge_l_base', filtro):.4f}  "
              f"v1: {promedio('rouge_l_v1', filtro):.4f}  "
              f"v2: {promedio('rouge_l_v2', filtro):.4f}")

    # deltas por par para detectar regresiones puntuales v2 vs v1
    empeoraron = [r for r in resultados if r["delta_v2_vs_v1"] < -0.01]
    print(f"\nPares donde v2 empeoro respecto a v1 (delta < -0.01): {len(empeoraron)}")
    for r in empeoraron:
        print(f"  idx {r['indice']} ({r['categoria']}): v1={r['rouge_l_v1']:.4f} -> v2={r['rouge_l_v2']:.4f}")

    salida = {
        "por_par": resultados,
        "promedios": {
            nombre: {
                "base": promedio("rouge_l_base", filtro),
                "v1": promedio("rouge_l_v1", filtro),
                "v2": promedio("rouge_l_v2", filtro),
            }
            for nombre, filtro in [("general", None), ("con_fuente", "con_fuente"), ("sin_fuente", "sin_fuente")]
        },
    }
    salida_path = DIR_TRAINING / "eval_holdout_rouge_l_v2.json"
    with salida_path.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {salida_path}")


if __name__ == "__main__":
    main()
