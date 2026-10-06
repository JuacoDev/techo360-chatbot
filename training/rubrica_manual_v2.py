"""T-93 (repetido): rubrica manual (1-5) comparando base, v1 y v2.
Misma metodologia y criterios estrictos que rubrica_manual.py -- ver ese
archivo para el detalle de los criterios de exactitud/relevancia.
AUTO-EVALUACION DE IA (Claude), no rubrica humana -- ver aviso completo
en rubrica_manual.py y en training/README.md.

Las columnas base_* se reutilizan tal cual de rubrica_manual.py: la
generacion base es deterministica (greedy, mismo prompt) y ya se
verifico identica entre ambas corridas de evaluacion.
"""

import json
import statistics
from pathlib import Path

from rubrica_manual import DATOS as DATOS_V1

# indice, categoria, v2_exactitud, v2_relevancia
DATOS_V2 = [
    (0,  "con_fuente", 3, 3),
    (1,  "con_fuente", 4, 4),
    (2,  "con_fuente", 1, 3),
    (3,  "con_fuente", 1, 3),
    (4,  "sin_fuente", 2, 3),
    (5,  "sin_fuente", 2, 4),
    (6,  "con_fuente", 2, 3),
    (7,  "con_fuente", 1, 2),
    (8,  "con_fuente", 2, 3),
    (9,  "sin_fuente", 3, 4),
    (10, "sin_fuente", 2, 3),
    (11, "sin_fuente", 1, 2),
    (12, "sin_fuente", 3, 4),
    (13, "sin_fuente", 3, 4),
    (14, "sin_fuente", 2, 3),
    (15, "sin_fuente", 5, 5),
    (16, "con_fuente", 3, 4),
    (17, "con_fuente", 3, 4),
]

NOTAS_V2 = {
    0: "Dimensiones y conteo de 15 indicadores correctos, pero introduce un criterio de clasificacion erroneo ('al menos un indicador en una dimension' en vez de 33.3% ponderado). Nivel similar a v1.",
    1: "Practicamente igual a v1: capta bien la distincion cuantitativo/cualitativo, sin la regla de no-doble-conteo.",
    2: "MISMA falla que v1: cifra nacional inventada (99.1%) con cita 'Segun el DANE' convincente, ahora con el año 2020 (mas parecido a la fecha de los pares nuevos) pero la cifra sigue sin corresponder a la real (86.4%). Acierta que Guainia es el extremo bajo pero con numero distinto al real.",
    3: "MISMA falla que v1: cifra nacional distinta pero igual de inventada (95.1% vs real 76.6%).",
    4: "REGRESION vs v1: v1 daba las 3 variables reales exactas del Score (acueducto/alcantarillado/deficit). v2 pierde esa precision y agrega alcance falso (cobertura de internet, acceso a salud) que Techo 360 no mide.",
    5: "Sigue afirmando 'cuatro variables' (real: tres) igual que v1, ahora con una cuarta variable distinta (tenencia informal) y una inconsistencia interna nueva (dice 25% cada una y luego 'un tercio').",
    6: "REGRESION vs v1: introduce una cita legal especifica y erronea (Ley 142 de 1994, la ley de servicios publicos que SI aparece en los pares nuevos de acueducto/alcantarillado) en vez de la real (Ley 388/1997) -- contaminacion cruzada plausible con los pares nuevos.",
    7: "REGRESION vs v1: v1 acertaba los 5 nombres reales de las dimensiones del IPM aunque fallaba los indicadores exactos. v2 inventa nombres de dimension completamente distintos y ademas se contradice entre 'tres' y 'cinco' dimensiones.",
    8: "Nivel similar a v1: mecanismo de conteo de privaciones sigue sin corresponder al real (33.3% de 15 indicadores), con una formulacion mas confusa/autocontradictoria.",
    9: "MEJORA real vs v1: acierta 4 de 5 nombres reales (backend, frontend, chatbot, proyeccion) -- v1 no acertaba ninguno. El quinto lo inventa ('chatbot-visualizacion') en vez de 'infra'.",
    10: "REGRESION vs v1: v1 identificaba correctamente JWT como mecanismo real. v2 lo reemplaza por un esquema inventado (HMAC SHA256, verificacion de IP) que no aparece en ningun par de entrenamiento.",
    11: "REGRESION vs v1: v1 acertaba 2 de 7 variables reales (acueducto, alcantarillado). v2 inventa una estructura de '3 bloques de 3' (9 items, no 7) sin ninguna coincidencia con las 7 variables reales.",
    12: "Mejora parcial vs v1 en un aspecto (acierta que son TRES variables, no cuatro) pero sigue con pesos incorrectos (40/30/30 en vez de 33/33/33) y trata acueducto+alcantarillado como una sola variable combinada. Nivel neto similar a v1.",
    13: "El concepto central (nulo = dato faltante) se mantiene correcto igual que v1, pero agrega una confusion nueva ('siete componentes', mezclando las 7 variables del panel con las 3 del Score).",
    14: "Nivel similar o levemente peor que v1: v1 al menos citaba instituciones reales (SSPD/SUI) aunque mal atribuidas; v2 inventa un 'portal de datos abiertos del Ministerio de Vivienda' que no aparece en ningun par de entrenamiento.",
    15: "Igual de bien que v1 -- capta con precision el proposito real del servicio de proyeccion (generar estimaciones cuando falta el dato real).",
    16: "REGRESION vs v1: acierta la distincion de variables (3 vs 5+) pero le atribuye erroneamente a Techo 360 un 'umbral de corte del 33.3%' que la referencia dice explicitamente que NO tiene (ese umbral es exclusivo del IPM/Alkire-Foster).",
    17: "Leve regresion vs v1: pierde la mencion explicita y precisa de 'TerriData' como fuente de Techo 360 (dice 'anexo censal del DANE' en su lugar), aunque mantiene la idea correcta de que hay que verificar ambos valores por separado.",
}


def main():
    v1_por_idx = {d[0]: d for d in DATOS_V1}

    print(f"{'idx':>3} {'cat':>11} {'base_ex':>7} {'v1_ex':>5} {'v2_ex':>5} {'base_rel':>8} {'v1_rel':>6} {'v2_rel':>6}")
    filas = []
    for idx, cat, v2e, v2r in DATOS_V2:
        _, _, be, br, v1e, v1r = v1_por_idx[idx]
        filas.append((idx, cat, be, br, v1e, v1r, v2e, v2r))
        print(f"{idx:>3} {cat:>11} {be:>7} {v1e:>5} {v2e:>5} {br:>8} {v1r:>6} {v2r:>6}")

    def prom(campo_idx, filtro=None):
        vals = [f[campo_idx] for f in filas if filtro is None or f[1] == filtro]
        return statistics.mean(vals)

    print("\n=== Promedios rubrica (1-5): exactitud ===")
    for nombre, filtro in [("General", None), ("Con fuente", "con_fuente"), ("Sin fuente", "sin_fuente")]:
        print(f"{nombre:12} -- base: {prom(2, filtro):.3f}  v1: {prom(4, filtro):.3f}  v2: {prom(6, filtro):.3f}")

    print("\n=== Promedios rubrica (1-5): relevancia ===")
    for nombre, filtro in [("General", None), ("Con fuente", "con_fuente"), ("Sin fuente", "sin_fuente")]:
        print(f"{nombre:12} -- base: {prom(3, filtro):.3f}  v1: {prom(5, filtro):.3f}  v2: {prom(7, filtro):.3f}")

    mejoraron = [f for f in filas if f[6] > f[4]]
    empeoraron = [f for f in filas if f[6] < f[4]]
    iguales = [f for f in filas if f[6] == f[4]]
    print(f"\nExactitud v2 vs v1 -- mejoraron: {len(mejoraron)}, empeoraron: {len(empeoraron)}, igual: {len(iguales)}")
    print("Pares donde v2 empeoro en exactitud:", [f[0] for f in empeoraron])

    salida = {
        "criterio": "Auto-evaluacion de IA (Claude), no rubrica humana. Comparacion base/v1/v2.",
        "por_par": [
            {"indice": idx, "categoria": cat, "base_exactitud": be, "base_relevancia": br,
             "v1_exactitud": v1e, "v1_relevancia": v1r, "v2_exactitud": v2e, "v2_relevancia": v2r,
             "nota_v2": NOTAS_V2[idx]}
            for idx, cat, be, br, v1e, v1r, v2e, v2r in filas
        ],
        "promedios_exactitud": {
            nombre: {"base": prom(2, filtro), "v1": prom(4, filtro), "v2": prom(6, filtro)}
            for nombre, filtro in [("general", None), ("con_fuente", "con_fuente"), ("sin_fuente", "sin_fuente")]
        },
        "promedios_relevancia": {
            nombre: {"base": prom(3, filtro), "v1": prom(5, filtro), "v2": prom(7, filtro)}
            for nombre, filtro in [("general", None), ("con_fuente", "con_fuente"), ("sin_fuente", "sin_fuente")]
        },
    }
    salida_path = Path(__file__).resolve().parent / "eval_holdout_rubrica_v2.json"
    with salida_path.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {salida_path}")


if __name__ == "__main__":
    main()
