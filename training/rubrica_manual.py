"""T-93: rubrica manual (1-5) de exactitud factual y relevancia a Techo
360, para cada uno de los 18 pares del holdout x 2 modelos (base y
fine-tuneado).

IMPORTANTE -- esto es una AUTO-EVALUACION DE IA, no una rubrica humana:
los puntajes de abajo fueron asignados por Claude (el asistente que
ejecuto T-93), leyendo cada respuesta generada contra la `response` real
del holdout y contra el propio dataset de entrenamiento (para verificar
si un error del modelo fine-tuneado ya estaba en los datos o es una
alucinacion nueva). No hay evaluador humano en este flujo. Los criterios
aplicados, de forma estricta segun lo pedido en la tarea:

- Exactitud factual (1-5): 1 = inventado/incorrecto sin relacion con la
  referencia; 3 = correcto en terminos generales pero impreciso o
  incompleto en los datos especificos; 5 = coincide con los hechos
  clave de la referencia.
- Relevancia a Techo 360 (1-5): 1 = no reconoce ni aplica el contexto
  especifico de Techo 360 (o inventa datos institucionales/tecnicos que
  no existen); 3 = se mantiene en tema sin alucinar activamente; 5 =
  responde con el conocimiento especifico y correcto del sistema real.

Justificacion resumida por par en `NOTAS` (no exhaustiva -- el detalle
completo del razonamiento esta en el reporte de T-93 en
training/README.md).
"""

import json
import statistics
from pathlib import Path

# indice, categoria, base_exactitud, base_relevancia, ft_exactitud, ft_relevancia
DATOS = [
    (0,  "con_fuente", 1, 2, 3, 3),
    (1,  "con_fuente", 2, 2, 4, 4),
    (2,  "con_fuente", 1, 2, 1, 3),
    (3,  "con_fuente", 1, 2, 1, 3),
    (4,  "sin_fuente", 1, 2, 4, 5),
    (5,  "sin_fuente", 1, 2, 3, 4),
    (6,  "con_fuente", 1, 2, 3, 3),
    (7,  "con_fuente", 1, 1, 2, 3),
    (8,  "con_fuente", 1, 1, 2, 3),
    (9,  "sin_fuente", 1, 1, 1, 3),
    (10, "sin_fuente", 2, 2, 4, 5),
    (11, "sin_fuente", 1, 1, 2, 4),
    (12, "sin_fuente", 1, 1, 3, 4),
    (13, "sin_fuente", 1, 2, 4, 5),
    (14, "sin_fuente", 1, 1, 2, 4),
    (15, "sin_fuente", 1, 2, 5, 5),
    (16, "con_fuente", 2, 3, 5, 5),
    (17, "con_fuente", 1, 2, 4, 5),
]

NOTAS = {
    0: "Base: atribuye el IPM al Banco Mundial/ONU e inventa 10 dimensiones sin relacion con la real. FT: cuenta correcta de 15 indicadores, dimensiones aproximadas pero no exactas, sin institucion/umbral.",
    1: "Base: definicion generica cuantidad/calidad, sin la regla real de no-doble-conteo, agrega tie-in a Techo 360 no pedido. FT: capta hacinamiento y mejoramiento correctamente, sin la regla de doble conteo.",
    2: "Ambos alucinan cifras -- base con formato obviamente inventado (lista de departamentos con cifras sueltas); FT con formato de cita 'Segun el DANE' mas convincente pero igual de incorrecto (99.1% vs 86.4% real, departamento top equivocado).",
    3: "Mismo patron que idx2: FT inventa cifras con formato de fuente creible ('Segun el DANE') pero incorrectas; base ademas confunde 'Score de Privacion' con 'Score de Pobreza' (nombre real del propio sistema, mal citado).",
    4: "Base: atribuye Techo 360 a una organizacion inventada ('Corvi') y describe mal el Score de Privacion (ingreso vs costo de vivienda). FT: describe correctamente las 3 variables reales del Score y el mapa interactivo.",
    5: "Base: formula completamente inventada basada en umbrales de ingreso. FT: 3 de las variables reales correctas, pero agrega una cuarta variable ('pobreza multidimensional') que no existe en el calculo real -- ver nota de alucinacion abajo.",
    6: "Base: inventa ministerio (MVUDES) y organismos (FONDERA, CORVIVI) que no existen. FT: correcto en espiritu (VIS como mecanismo de equidad de acceso) pero sin la cita legal (Ley 388/1997) ni el tope de 135 SMLMV.",
    7: "Base: dimensiones y los 15 indicadores totalmente inventados. FT: acierta los nombres de las 5 dimensiones reales pero se contradice (dice 'tres dimensiones' y luego lista cinco) y los indicadores/conteos por dimension no coinciden con los 15 reales.",
    8: "Base: confunde el umbral del IPM con una linea de pobreza por ingreso, inventa tres umbrales de Techo 360. FT: mecanismo de conteo de privaciones correcto en espiritu, pero umbral numerico (3 de 5, 50% por dimension) no coincide con el real (33.3% de 15).",
    9: "Base: inventa una organizacion desarrolladora y tres nombres de repositorio que no existen. FT: tambien inventa nombres de repositorio (data/models/services/routes/utils, estructura interna tipica de un proyecto FastAPI) -- verificado contra dataset/entrenamiento.jsonl: los nombres reales (backend/frontend/chatbot/proyeccion/infra) aparecen docenas de veces en el dataset de entrenamiento, asi que esto ES una alucinacion nueva del modelo, no un reflejo de datos de entrenamiento ambiguos.",
    10: "Base: admite explicitamente que no sabe y especula de forma generica (mejor que alucinar con confianza, pero no responde). FT: identifica correctamente JWT como mecanismo real, aunque dice 'cookie' en vez de header Authorization/localStorage (detalle impreciso) y no menciona bcrypt.",
    11: "Base: inventa 7 variables tipo 'Pobreza X' que no existen. FT: acierta acueducto y alcantarillado (2 de 7 reales) pero inventa 'acceso a vivienda' y 'calidad del agua', y omite densidad poblacional y tenencia informal.",
    12: "Base: metodologia de umbrales de ingreso totalmente inventada. FT: capta la estructura real (normalizacion + ponderacion), 3 de 4 variables citadas son reales, pero agrega una cuarta inexistente, pesos incorrectos (0.25 vs 0.333 real) y omite el paso de inversion de acueducto/alcantarillado.",
    13: "Base: interpretacion conceptualmente invertida -- confunde 'score nulo' (dato faltante) con 'score cero' (ausencia de pobreza), inventa una lista de que implicaria un score bajo. FT: correctamente identifica que nulo = fila/dato faltante, coincide con el mecanismo real (aunque sin el ejemplo especifico del Area en Litigio Cauca-Huila).",
    14: "Base: inventa cuatro encuestas/bases de datos que no existen (ENVP, ENS, ENP, BDV). FT: acierta DANE censal para deficit habitacional, pero atribuye acueducto/alcantarillado a SSPD/SUI en vez de TerriData/DNP (institucion real pero variable equivocada), y no menciona IGAC/catastro para tenencia informal.",
    15: "Base: reemplaza el proposito real (llenar datos faltantes) por una narrativa generica de 'pronostico/analisis espacial' con indicadores inventados. FT: coincide de forma precisa con el proposito real -- generar estimaciones estadisticas solo cuando falta el dato real, distinguiendolas de datos observados.",
    16: "Base: confunde la composicion del Score de Privacion con dimensiones del IPM (educacion, salud, seguridad social no son parte del Score real). FT: describe con precision la diferencia real -- 3 variables con peso igual vs 15+ indicadores del IPM con peso propio por dimension.",
    17: "Base: inventa el nombre de la institucion ('Subgerencia de Servicios Publicos Distritales' no existe, el nombre real es Superintendencia de Servicios Publicos Domiciliarios) y una razon de discrepancia inventada (potable vs no potable). FT: identifica correctamente TerriData como fuente de Techo 360 y que la cifra no es la oficial verificada de SSPD, aunque sin detallar las razones especificas de la diferencia (corte, agregacion, prestadores informales).",
}


def main():
    print(f"{'idx':>3} {'categoria':>11} {'base_ex':>8} {'base_rel':>9} {'ft_ex':>6} {'ft_rel':>7}")
    for idx, cat, be, br, fe, fr in DATOS:
        print(f"{idx:>3} {cat:>11} {be:>8} {br:>9} {fe:>6} {fr:>7}")

    def prom(campo_idx, filtro=None):
        vals = [d[campo_idx] for d in DATOS if filtro is None or d[1] == filtro]
        return statistics.mean(vals)

    print("\n=== Promedios rubrica (1-5) ===")
    for nombre, filtro in [("General", None), ("Con fuente", "con_fuente"), ("Sin fuente", "sin_fuente")]:
        print(f"{nombre:12} -- base exactitud: {prom(2, filtro):.3f}  base relevancia: {prom(3, filtro):.3f}  "
              f"|  ft exactitud: {prom(4, filtro):.3f}  ft relevancia: {prom(5, filtro):.3f}")

    salida = {
        "criterio": "Auto-evaluacion de IA (Claude), no rubrica humana. Escala 1-5 en exactitud factual y relevancia a Techo 360.",
        "por_par": [
            {"indice": idx, "categoria": cat, "base_exactitud": be, "base_relevancia": br,
             "ft_exactitud": fe, "ft_relevancia": fr, "nota": NOTAS[idx]}
            for idx, cat, be, br, fe, fr in DATOS
        ],
        "promedios": {
            nombre: {
                "base_exactitud": prom(2, filtro), "base_relevancia": prom(3, filtro),
                "ft_exactitud": prom(4, filtro), "ft_relevancia": prom(5, filtro),
            }
            for nombre, filtro in [("general", None), ("con_fuente", "con_fuente"), ("sin_fuente", "sin_fuente")]
        },
    }
    salida_path = Path(__file__).resolve().parent / "eval_holdout_rubrica.json"
    with salida_path.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {salida_path}")


if __name__ == "__main__":
    main()
