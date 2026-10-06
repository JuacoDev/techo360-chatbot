"""T-93: metrica automatica -- ROUGE-L (F1) entre cada respuesta generada
y la `response` original del holdout.

Se eligio ROUGE-L en vez de similitud por embeddings porque no requiere
ninguna dependencia nueva (ni sentence-transformers, ni rouge-score) --
es una implementacion pura en Python del LCS (longest common subsequence)
sobre tokens en minuscula, sin puntuacion. Mide cuanto se solapa la
respuesta generada con la respuesta de referencia en orden (no exige
coincidencia exacta de frase, pero sí que las palabras compartidas
aparezcan en una secuencia comun).

No es una metrica semantica real (dos respuestas correctas con
vocabulario totalmente distinto puntuarian bajo) -- por eso el reporte
de T-93 la complementa con la rubrica manual 1-5, que sí puede juzgar
correccion aunque el fraseo cambie.
"""

import json
import re
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GENERACIONES_PATH = Path(__file__).resolve().parent / "eval_holdout_generaciones.json"


def tokenizar(texto):
    texto = texto.lower()
    return re.findall(r"[a-záéíóúñü0-9]+", texto)


def lcs_len(a, b):
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[n][m]


def rouge_l_f1(hipotesis, referencia):
    tok_hip = tokenizar(hipotesis)
    tok_ref = tokenizar(referencia)
    if not tok_hip or not tok_ref:
        return 0.0
    l = lcs_len(tok_hip, tok_ref)
    if l == 0:
        return 0.0
    precision = l / len(tok_hip)
    recall = l / len(tok_ref)
    return 2 * precision * recall / (precision + recall)


def main():
    with GENERACIONES_PATH.open("r", encoding="utf-8") as f:
        generaciones = json.load(f)

    resultados = []
    for g in generaciones:
        ref = g["referencia_holdout"]
        r_base = rouge_l_f1(g["respuesta_base"], ref)
        r_ft = rouge_l_f1(g["respuesta_finetuneado"], ref)
        resultados.append({
            "indice": g["indice"],
            "categoria": g["categoria"],
            "rouge_l_base": round(r_base, 4),
            "rouge_l_finetuneado": round(r_ft, 4),
            "delta": round(r_ft - r_base, 4),
        })

    print(f"{'idx':>3} {'categoria':>11} {'base':>7} {'finetune':>9} {'delta':>7}")
    for r in resultados:
        print(f"{r['indice']:>3} {r['categoria']:>11} {r['rouge_l_base']:>7.4f} "
              f"{r['rouge_l_finetuneado']:>9.4f} {r['delta']:>+7.4f}")

    def promedio(campo, filtro=None):
        vals = [r[campo] for r in resultados if filtro is None or r["categoria"] == filtro]
        return statistics.mean(vals) if vals else None

    print("\n=== Promedios ROUGE-L (F1) ===")
    print(f"General     -- base: {promedio('rouge_l_base'):.4f}  finetuneado: {promedio('rouge_l_finetuneado'):.4f}")
    print(f"Con fuente  -- base: {promedio('rouge_l_base', 'con_fuente'):.4f}  finetuneado: {promedio('rouge_l_finetuneado', 'con_fuente'):.4f}")
    print(f"Sin fuente  -- base: {promedio('rouge_l_base', 'sin_fuente'):.4f}  finetuneado: {promedio('rouge_l_finetuneado', 'sin_fuente'):.4f}")

    salida = {
        "por_par": resultados,
        "promedios": {
            "general": {"base": promedio("rouge_l_base"), "finetuneado": promedio("rouge_l_finetuneado")},
            "con_fuente": {"base": promedio("rouge_l_base", "con_fuente"), "finetuneado": promedio("rouge_l_finetuneado", "con_fuente")},
            "sin_fuente": {"base": promedio("rouge_l_base", "sin_fuente"), "finetuneado": promedio("rouge_l_finetuneado", "sin_fuente")},
        },
    }
    salida_path = Path(__file__).resolve().parent / "eval_holdout_rouge_l.json"
    with salida_path.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {salida_path}")


if __name__ == "__main__":
    main()
