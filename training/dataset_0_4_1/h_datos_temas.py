"""Mas formulaciones para H (tema x marco): redacciones que el enrutador real SI consulta (patrones «qué es», «qué significa»,
«explícame», «define», «descríbeme», «qué se entiende por») sobre sintagmas con palabra del dominio. Se suman a `q` de cada
intencion; la deduplicacion (< 0,75) y el tope por intencion filtran los casi iguales.
"""
MARCOS = ["¿Qué es {t}?", "¿Qué significa {t}?", "Explícame {t}.", "Define {t}.", "Descríbeme {t}.", "¿Qué se entiende por {t}?"]

TEMAS = {
    "score-formula": ["la fórmula del Score de privación", "el cálculo del score de privación"],
    "score-escala": ["un Score de privación alto", "la escala del score de privación"],
    "score-variables": ["las variables del score de privación", "los componentes del score de privación"],
    "densidad-fuera-score": ["la densidad poblacional dentro del score", "el papel de la densidad poblacional en el mapa"],
    "doble-conteo": ["el doble conteo del déficit en el score", "el déficit total frente al cuantitativo en el score"],
    "coberturas-en-score": ["las coberturas dentro del score de privación", "los datos reales del score de privación"],
    "limite-cuantitativo": ["el límite del déficit cuantitativo en el score", "lo que deja fuera el déficit cuantitativo del score"],
    "normalizacion": ["la normalización min-max del score", "el recorte entre 0 y 1 del score"],
    "universo-score": ["el universo de municipios del score", "los códigos huérfanos del score"],
    "ipm-que-es": ["el IPM", "el Índice de Pobreza Multidimensional"],
    "ipm-por-que": ["la adopción del IPM en Colombia", "la ventaja del IPM sobre la pobreza monetaria"],
    "ipm-dimensiones": ["las dimensiones del IPM", "los pesos de las dimensiones del IPM"],
    "ipm-unidad": ["la unidad de análisis del IPM", "las encuestas del IPM"],
    "ipm-umbral": ["el umbral de pobreza multidimensional del IPM", "el punto de corte del IPM"],
    "deficit-cuantitativo": ["el déficit habitacional cuantitativo", "los componentes del déficit cuantitativo"],
    "deficit-cualitativo": ["el déficit habitacional cualitativo", "los componentes del déficit cualitativo"],
    "deficit-anio": ["el año del déficit habitacional municipal", "el censo del déficit habitacional"],
    "densidad-formula": ["la densidad poblacional", "el cálculo de la densidad poblacional"],
    "tenencia-formula": ["la tenencia informal", "el cálculo de la tenencia informal"],
    "dato-real-vs-proyeccion": ["un dato real frente a una proyección", "el principio de los datos estimados"],
    "fiabilidad": ["la fiabilidad de un dato", "el intervalo de confianza de una proyección"],
    "fuente-deficit": ["la fuente del déficit habitacional municipal", "el origen del déficit habitacional"],
    "proyeccion-coberturas": ["la proyección de las coberturas", "el último valor observado en las proyecciones"],
    "proyeccion-densidad": ["la proyección de la densidad poblacional", "la regresión de la densidad proyectada"],
    "proyeccion-deficit": ["la estimación del déficit habitacional de 2024", "el déficit habitacional proyectado"],
    "metodos-proyeccion": ["los métodos de proyección de la plataforma", "el score de privación proyectado"],
    "divipola-total": ["el total de códigos del DIVIPOLA", "los municipios del DIVIPOLA"],
    "areas-no-municipalizadas": ["las áreas no municipalizadas", "los códigos del DIVIPOLA sin polígono"],
    "litigio-cauca-huila": ["el área en litigio Cauca-Huila", "el polígono del litigio Cauca-Huila en el DIVIPOLA"],
    "nombres-distintos": ["los nombres distintos de un municipio entre fuentes", "el nombre oficial y el nombre corto de un municipio"],
    "insignia-fiabilidad": ["la insignia de fiabilidad del panel", "las tarjetas de proyección del panel de indicadores"],
    "estados-mensaje": ["los estados de un mensaje del chat", "el estado de un mensaje del asistente"],
    "color-mapa-variable": ["el color rojo del mapa de proyección", "la escala de color de cada variable en el mapa"],
    "semaforo-mapa": ["el semáforo del score en el mapa", "el color amarillo del mapa"],
    "prioridad": ["la prioridad de intervención de un municipio", "la prioridad alta de un municipio"],
    "mapa-gris": ["el color gris del mapa", "un municipio gris en el mapa"],
}

# Segunda formulacion de HOLDOUT (se usa si la primera no recupera el fragmento esperado)
QH2 = {
    "dato-real-vs-proyeccion": "¿Qué significa que un dato sea una proyección y no un dato real?",
    "densidad-fuera-score": "¿Qué significa que la densidad poblacional quede fuera del score?",
    "doble-conteo": "¿Qué significa el doble conteo del déficit total en el score de privación?",
    "ipm-dimensiones": "¿Cuáles son las dimensiones del IPM de Colombia?",
    "score-formula": "Explícame cómo se obtiene el score de privación de un municipio.",
    "normalizacion": "¿Qué significa que el score de privación esté normalizado entre 0 y 1?",
    "deficit-anio": "¿A qué año corresponde el déficit habitacional que muestra la plataforma por municipio?",
    "proyeccion-coberturas": "¿Cómo se estima la cobertura de acueducto de los años proyectados?",
    "coberturas-en-score": "¿Qué significa que las coberturas sean los únicos datos reales del score?",
    "limite-cuantitativo": "¿Qué significa la limitación del déficit cuantitativo en el score de privación?",
    "fuente-deficit": "¿De dónde proviene el déficit habitacional municipal que usa el score?",
    "mapa-gris": "¿Por qué hay municipios en gris en el mapa?",
}

# Premisas falsas ADICIONALES (H5): (intencion, preguntas)
PREMISAS_EXTRA = [
    ("deficit-anio", ["¿Por qué el déficit habitacional municipal se midió en el censo de 2005?"]),
    ("ipm-umbral", ["¿Por qué el IPM exige privaciones en todas las variables para considerar pobre a un hogar?"]),
    ("ipm-dimensiones", ["¿Por qué las dimensiones del IPM son ocho?"]),
    ("score-variables", ["¿Por qué el score de privación se calcula con tres variables que se invierten?"]),
    ("divipola-total", ["¿Por qué el DIVIPOLA tiene solo 1.000 municipios?"]),
    ("tenencia-formula", ["¿Por qué la tenencia informal se calcula sobre el total de hogares del municipio?"]),
    ("proyeccion-densidad", ["¿Por qué la densidad proyectada se calcula con los 10 últimos puntos reales?"]),
    ("estados-mensaje", ["¿Por qué un mensaje del chat puede tener ocho estados?"]),
    ("semaforo-mapa", ["¿Por qué en el semáforo del score el verde es el valor más bajo?"]),
    ("prioridad", ["¿Por qué el score de privación de prioridad alta es mayor a cinco?"]),
    ("areas-no-municipalizadas", ["¿Por qué las áreas no municipalizadas son cuarenta y tienen polígono?"]),
    ("fuente-deficit", ["¿Por qué el déficit habitacional municipal lo publica la Superintendencia de Servicios Públicos?"]),
]
