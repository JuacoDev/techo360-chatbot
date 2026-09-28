"""T-93 (tercera corrida): rubrica manual (1-5) comparando base, v1, v2
y v3. Mismos criterios estrictos que las corridas anteriores -- ver
rubrica_manual.py. AUTO-EVALUACION DE IA (Claude), no rubrica humana.

Las columnas base/v1/v2 se reutilizan de rubrica_manual_v2.py (las
generaciones base/v1/v2 son deterministicas -- greedy, mismo prompt --
y ya se verificaron identicas entre corridas).
"""

import json
import statistics
from pathlib import Path

from rubrica_manual import DATOS as DATOS_V1
from rubrica_manual_v2 import DATOS_V2

# indice, categoria, v3_exactitud, v3_relevancia
DATOS_V3 = [
    (0,  "con_fuente", 2, 3),
    (1,  "con_fuente", 4, 4),
    (2,  "con_fuente", 1, 3),
    (3,  "con_fuente", 1, 3),
    (4,  "sin_fuente", 3, 4),
    (5,  "sin_fuente", 2, 4),
    (6,  "con_fuente", 3, 3),
    (7,  "con_fuente", 3, 3),
    (8,  "con_fuente", 2, 3),
    (9,  "sin_fuente", 4, 4),
    (10, "sin_fuente", 4, 5),
    (11, "sin_fuente", 3, 4),
    (12, "sin_fuente", 4, 4),
    (13, "sin_fuente", 4, 4),
    (14, "sin_fuente", 2, 3),
    (15, "sin_fuente", 5, 5),
    (16, "con_fuente", 3, 4),
    (17, "con_fuente", 3, 4),
]

NOTAS_V3 = {
    0: "Introduce una atribucion nueva y erronea (PNUD como disenador original, deberia ser DNP) y se autocontradice entre 'cinco dimensiones' y 'seis dimensiones' -- peor que v1.",
    1: "Nivel practicamente identico a v1: distincion cuantitativo/cualitativo correcta en espiritu, sin la regla de doble conteo.",
    2: "Persiste la misma falla de cobertura (fuera del alcance de este experimento, deliberadamente no tocada): cifra nacional inventada (97.1%) con cita confiada, distinta a la real (86.4%).",
    3: "Misma falla persistente de cobertura: cifra inventada (73.1% en 2025, casi identica a la propia alucinacion de v1) sin corresponder a la real (76.6%).",
    4: "RECUPERADO parcialmente vs v2: ya no inventa alcance falso (internet, salud) como v2, aunque pierde la precision de v1 sobre las 3 variables exactas del Score.",
    5: "Mismo problema de 'cuatro variables' que YA estaba presente en v1 (no es una regresion de T-95 -- preexistente desde el T-92 original).",
    6: "REGRESION DE V2 CORREGIDA: ya NO cita la Ley 142 de 1994 (el error especifico que introdujo v2). Nivel de precision comparable a v1 (generico pero sin cita legal falsa).",
    7: "MEJOR que v1 y v2: los nombres de dimension que si menciona (ninez y juventud, trabajo) son reales, y los indicadores especificos citados son mas cercanos a los reales que los de ambas versiones anteriores, aunque sigue sin listar las 5 dimensiones completas.",
    8: "Nivel similar a v1/v2: mecanismo de conteo simplificado ('mayoria simple') pero sigue sin corresponder al real 33.3% ponderado de 15 indicadores.",
    9: "MEJOR resultado de las tres versiones: nombra 4 de 5 repos reales con el prefijo correcto (techo360-backend/frontend/chatbot/proyeccion) y, a diferencia de v2, NO inventa un quinto repositorio falso -- simplemente no lo menciona. Sigue sin ser perfecto (falta techo360-infra) pero es el patron de falla mas seguro de los tres.",
    10: "REGRESION DE V2 CORREGIDA: vuelve a identificar correctamente JWT como mecanismo de autenticacion (v2 lo habia reemplazado por un esquema HMAC/IP inventado). Nivel comparable a v1.",
    11: "MEJORA vs v2: mantiene el patron vago de v1 pero fundamenta las 2 variables reales que menciona (acueducto, alcantarillado) con fuentes reales (TerriData, DANE, Censo) en vez de la estructura de '3 bloques de 9 items' que fabrico v2.",
    12: "MEJOR que v1 y v2 en identidad de variables: nombra las 3 variables REALES exactas (deficit habitacional, cobertura acueducto, cobertura alcantarillado) -- v1 tenia 4 (una de mas), v2 tenia 3 pero con una equivocada (tenencia informal en vez de una de las reales). Pesos (40/30/30) siguen sin ser los reales (33/33/33).",
    13: "Concepto central (nulo = dato faltante) correcto, igual que v1 -- sin la confusion de 'siete componentes' que introdujo v2. Agrega un detalle no verificado (municipios agregados/desagregados) que no esta en la referencia.",
    14: "NUEVA fabricacion no vista en v1 ni v2: inventa una variable 'cobertura de internet' que no existe en el panel real de Techo 360. Nivel de exactitud similar o levemente peor que v1/v2.",
    15: "Igual de preciso que v1 -- capta el proposito real del servicio de proyeccion con precision.",
    16: "Mismo problema que v2, NO corregido por este experimento: sigue atribuyendole a Techo 360 un umbral de 33.33% que la referencia dice explicitamente que Techo 360 NO tiene -- sugiere que este error especifico no viene del bloque de cobertura aislado en este experimento.",
    17: "Nivel similar a v2: pierde la mencion precisa de 'TerriData' como fuente de Techo 360 (usa 'anexo censal del DANE' en su lugar), a diferencia de v1 que si la nombraba correctamente.",
}


def main():
    v1_por_idx = {d[0]: d for d in DATOS_V1}
    v2_por_idx = {d[0]: (d[2], d[3]) for d in DATOS_V2}

    filas = []
    for idx, cat, v3e, v3r in DATOS_V3:
        _, _, be, br, v1e, v1r = v1_por_idx[idx]
        v2e, v2r = v2_por_idx[idx]
        filas.append((idx, cat, be, br, v1e, v1r, v2e, v2r, v3e, v3r))

    print(f"{'idx':>3} {'cat':>11} {'base_ex':>7} {'v1_ex':>5} {'v2_ex':>5} {'v3_ex':>5} {'base_rel':>8} {'v1_rel':>6} {'v2_rel':>6} {'v3_rel':>6}")
    for f in filas:
        idx, cat, be, br, v1e, v1r, v2e, v2r, v3e, v3r = f
        print(f"{idx:>3} {cat:>11} {be:>7} {v1e:>5} {v2e:>5} {v3e:>5} {br:>8} {v1r:>6} {v2r:>6} {v3r:>6}")

    def prom(campo_idx, filtro=None):
        vals = [f[campo_idx] for f in filas if filtro is None or f[1] == filtro]
        return statistics.mean(vals)

    print("\n=== Promedios rubrica (1-5): EXACTITUD ===")
    for nombre, filtro in [("General", None), ("Con fuente", "con_fuente"), ("Sin fuente", "sin_fuente")]:
        print(f"{nombre:12} -- base: {prom(2, filtro):.3f}  v1: {prom(4, filtro):.3f}  v2: {prom(6, filtro):.3f}  v3: {prom(8, filtro):.3f}")

    print("\n=== Promedios rubrica (1-5): RELEVANCIA ===")
    for nombre, filtro in [("General", None), ("Con fuente", "con_fuente"), ("Sin fuente", "sin_fuente")]:
        print(f"{nombre:12} -- base: {prom(3, filtro):.3f}  v1: {prom(5, filtro):.3f}  v2: {prom(7, filtro):.3f}  v3: {prom(9, filtro):.3f}")

    mejoraron_v1 = [f for f in filas if f[8] > f[4]]
    empeoraron_v1 = [f for f in filas if f[8] < f[4]]
    iguales_v1 = [f for f in filas if f[8] == f[4]]
    print(f"\nExactitud v3 vs v1 -- mejoraron: {len(mejoraron_v1)}, empeoraron: {len(empeoraron_v1)}, igual: {len(iguales_v1)}")
    print("Pares donde v3 empeoro vs v1:", [f[0] for f in empeoraron_v1])
    print("Pares donde v3 mejoro vs v1:", [f[0] for f in mejoraron_v1])

    mejoraron_v2 = [f for f in filas if f[8] > f[6]]
    empeoraron_v2 = [f for f in filas if f[8] < f[6]]
    print(f"\nExactitud v3 vs v2 -- mejoraron: {len(mejoraron_v2)}, empeoraron: {len(empeoraron_v2)}, igual: {18-len(mejoraron_v2)-len(empeoraron_v2)}")

    salida = {
        "criterio": "Auto-evaluacion de IA (Claude), no rubrica humana. Comparacion base/v1/v2/v3.",
        "por_par": [
            {"indice": idx, "categoria": cat, "base_exactitud": be, "base_relevancia": br,
             "v1_exactitud": v1e, "v1_relevancia": v1r, "v2_exactitud": v2e, "v2_relevancia": v2r,
             "v3_exactitud": v3e, "v3_relevancia": v3r, "nota_v3": NOTAS_V3[idx]}
            for idx, cat, be, br, v1e, v1r, v2e, v2r, v3e, v3r in filas
        ],
        "promedios_exactitud": {
            nombre: {"base": prom(2, filtro), "v1": prom(4, filtro), "v2": prom(6, filtro), "v3": prom(8, filtro)}
            for nombre, filtro in [("general", None), ("con_fuente", "con_fuente"), ("sin_fuente", "sin_fuente")]
        },
        "promedios_relevancia": {
            nombre: {"base": prom(3, filtro), "v1": prom(5, filtro), "v2": prom(7, filtro), "v3": prom(9, filtro)}
            for nombre, filtro in [("general", None), ("con_fuente", "con_fuente"), ("sin_fuente", "sin_fuente")]
        },
    }
    salida_path = Path(__file__).resolve().parent / "eval_holdout_rubrica_v3.json"
    with salida_path.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {salida_path}")


if __name__ == "__main__":
    main()
