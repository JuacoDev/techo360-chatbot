"""Catalogo de 0.4.1 (paso 7.3, Fase A): cuotas, subconjunto de graficas que el modelo emite y reglas del bloque.

Fuente: claude/fase7-1-especificacion.md (secciones 3 y 4) y claude/fase2-3-contrato-grafica.md.
Las reglas de combinacion de `tipos_validos` son una COPIA REDUCIDA de `validar_combinacion()` del backend
(services/reportes_graficas_catalogo.py) para el subconjunto que el modelo emite; la Fase B usa la funcion real
del backend y `test_paridad_backend` (tests_bancos.py) compara ambas cuando el backend esta disponible.
"""

VARIABLES = (
    "score_privacion",
    "cobertura_acueducto",
    "cobertura_alcantarillado",
    "deficit_habitacional_cuantitativo",
    "deficit_habitacional_cualitativo",
    "densidad_poblacional",
)
GRUPO_UNIDAD = {
    "score_privacion": "indice",
    "cobertura_acueducto": "porcentaje",
    "cobertura_alcantarillado": "porcentaje",
    "deficit_habitacional_cuantitativo": "porcentaje",
    "deficit_habitacional_cualitativo": "porcentaje",
    "densidad_poblacional": "densidad",
}
# Subconjunto que el modelo emite en 0.4.1 (decision 7.1: gauge, no bullet).
TIPOS_MODELO = ("lineas", "barras_ranking", "barras_agrupadas", "gauge")
MAX_ANIOS = 25
ANIO_MIN, ANIO_MAX = 2018, 2042
CLAVES_BLOQUE = ("v", "tipo", "modo", "variables", "zonas", "anios")  # esquema cerrado; sin `titulo`

# Tipos que el catalogo del backend acepta pero el modelo NO emite (G4): nombre desnudo para «de tipo {t}».
TIPOS_NO_SOPORTADOS = (
    "radar", "dispersión", "treemap", "mapa coroplético", "histograma", "diagrama de caja", "pastel",
    "dumbbell", "bullet", "barras apiladas", "paneles", "correlaciones",
)

# Subfamilias y cuotas (7.1 seccion 4). Total nuevo de G + F+ = 470; H (400) se genera en la Fase B/DS con el corpus final.
# Reparticiones internas (marcadas PROPUESTA): barras_agrupadas 24 individual / 16 comparar; G2 40/20/20; G3 20/20; G5 15/15;
# G6 10/10; F+ 15 por categoria.
CUOTAS = {
    "g1_lineas_individual": 60,
    "g1_lineas_comparar": 40,
    "g1_barras_ranking": 40,
    "g1_barras_agrupadas_ind": 24,
    "g1_barras_agrupadas_cmp": 16,
    "g1_gauge": 30,
    "g2_serie": 40,
    "g2_comparacion": 20,
    "g2_puntual": 20,
    "g3_un_anio": 20,
    "g3_sin_dato": 20,
    "g4_tipo_no_soportado": 30,
    "g5_sin_municipio": 15,
    "g5_sin_variable": 15,
    "g6_valores": 10,
    "g6_codigo": 10,
    "fp_revelar": 15,
    "fp_ignorar": 15,
    "fp_falsos": 15,
    "fp_estimar": 15,
}
CUOTAS_FAMILIA = {"G1": 210, "G2": 80, "G3": 40, "G4": 30, "G5": 30, "G6": 20, "F+": 60}
MINIMO_PREGUNTAS = 25  # formulaciones por subfamilia
MAX_APERTURA = 0.08  # ninguna apertura > 8 % de lo nuevo
MAX_SEGUN = 0.03  # «Según…» <= 3 %


def familia(subfamilia: str) -> str:
    p = subfamilia.split("_")[0]
    return "F+" if p == "fp" else p.upper()


def tipos_validos(tipo: str, modo: str, variables: list[str], n_zonas: int, n_anios: int) -> str | None:
    """Mensaje de error o None. Reglas de la tabla de 7.1 seccion 3 (subconjunto del modelo)."""
    if tipo not in TIPOS_MODELO:
        return f"tipo fuera del subconjunto del modelo: {tipo}"
    if any(v not in VARIABLES for v in variables):
        return "variable desconocida"
    if len(set(variables)) != len(variables):
        return "variables repetidas"
    if n_anios > MAX_ANIOS:
        return "mas de 25 anios"
    if tipo == "lineas":
        if len(variables) != 1 or n_anios < 2:
            return "lineas: 1 variable y al menos 2 anios"
        if modo == "individual" and n_zonas == 1:
            return None
        if modo == "comparar" and 2 <= n_zonas <= 5:
            return None
        return "lineas: individual con 1 zona o comparar con 2 a 5"
    if tipo == "barras_ranking":
        if len(variables) != 1 or n_anios != 1 or modo != "comparar" or not 2 <= n_zonas <= 5:
            return "barras_ranking: comparar, 1 variable, 2 a 5 zonas, 1 anio"
        return None
    if tipo == "barras_agrupadas":
        if not 2 <= len(variables) <= 4 or n_anios != 1 or len({GRUPO_UNIDAD[v] for v in variables}) != 1:
            return "barras_agrupadas: 2 a 4 variables de la misma unidad y 1 anio"
        if (modo, n_zonas) == ("individual", 1) or (modo == "comparar" and 2 <= n_zonas <= 5):
            return None
        return "barras_agrupadas: individual con 1 zona o comparar con 2 a 5"
    if tipo == "gauge":
        if len(variables) != 1 or variables[0] == "densidad_poblacional" or modo != "individual" or n_zonas != 1 or n_anios != 1:
            return "gauge: individual, 1 variable distinta de densidad, 1 zona, 1 anio"
        return None
    return "tipo no cubierto"
