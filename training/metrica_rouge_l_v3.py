"""T-93 (tercera corrida): ROUGE-L (F1) para base, v1, v2 y v3 contra la
`referencia_holdout`, usando las generaciones de evaluar_holdout_v3.py.
Misma implementacion de ROUGE-L (LCS puro) que las corridas anteriores.
"""

import json
import statistics
from pathlib import Path

from metrica_rouge_l import rouge_l_f1

DIR_TRAINING = Path(__file__).resolve().parent
GENERACIONES_PATH = DIR_TRAINING / "eval_holdout_generaciones_v3.json"


def main():
    with GENERACIONES_PATH.open("r", encoding="utf-8") as f:
        generaciones = json.load(f)

    resultados = []
    for g in generaciones:
        ref = g["referencia_holdout"]
        r_base = rouge_l_f1(g["respuesta_base"], ref)
        r_v1 = rouge_l_f1(g["respuesta_v1"], ref)
        r_v2 = rouge_l_f1(g["respuesta_v2"], ref)
        r_v3 = rouge_l_f1(g["respuesta_v3"], ref)
        resultados.append({
            "indice": g["indice"],
            "categoria": g["categoria"],
            "rouge_l_base": round(r_base, 4),
            "rouge_l_v1": round(r_v1, 4),
            "rouge_l_v2": round(r_v2, 4),
            "rouge_l_v3": round(r_v3, 4),
            "delta_v3_vs_v1": round(r_v3 - r_v1, 4),
            "delta_v3_vs_v2": round(r_v3 - r_v2, 4),
        })

    print(f"{'idx':>3} {'categoria':>11} {'base':>7} {'v1':>7} {'v2':>7} {'v3':>7} {'v3-v1':>7}")
    for r in resultados:
        print(f"{r['indice']:>3} {r['categoria']:>11} {r['rouge_l_base']:>7.4f} "
              f"{r['rouge_l_v1']:>7.4f} {r['rouge_l_v2']:>7.4f} {r['rouge_l_v3']:>7.4f} {r['delta_v3_vs_v1']:>+7.4f}")

    def promedio(campo, filtro=None):
        vals = [r[campo] for r in resultados if filtro is None or r["categoria"] == filtro]
        return statistics.mean(vals) if vals else None

    print("\n=== Promedios ROUGE-L (F1) ===")
    for nombre, filtro in [("General", None), ("Con fuente", "con_fuente"), ("Sin fuente", "sin_fuente")]:
        print(f"{nombre:12} -- base: {promedio('rouge_l_base', filtro):.4f}  "
              f"v1: {promedio('rouge_l_v1', filtro):.4f}  "
              f"v2: {promedio('rouge_l_v2', filtro):.4f}  "
              f"v3: {promedio('rouge_l_v3', filtro):.4f}")

    mejoraron = [r for r in resultados if r["delta_v3_vs_v1"] > 0.01]
    empeoraron = [r for r in resultados if r["delta_v3_vs_v1"] < -0.01]
    print(f"\nv3 vs v1 -- mejoraron: {len(mejoraron)}, empeoraron: {len(empeoraron)}, similar: {18-len(mejoraron)-len(empeoraron)}")

    salida = {
        "por_par": resultados,
        "promedios": {
            nombre: {
                "base": promedio("rouge_l_base", filtro),
                "v1": promedio("rouge_l_v1", filtro),
                "v2": promedio("rouge_l_v2", filtro),
                "v3": promedio("rouge_l_v3", filtro),
            }
            for nombre, filtro in [("general", None), ("con_fuente", "con_fuente"), ("sin_fuente", "sin_fuente")]
        },
    }
    salida_path = DIR_TRAINING / "eval_holdout_rouge_l_v3.json"
    with salida_path.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {salida_path}")


if __name__ == "__main__":
    main()
