"""Clasificacion de las 100 respuestas de v3.2, segun RUBRICA.md.
Mismo criterio y misma regla operativa de casos limite que puntajes_v2.py
y puntajes_v3.py. C=correcta  I=incorrecta  A=alucinacion  N=se_nego
M=confianza media (aparte)
"""
PUNTAJES = {
    1: "C", 2: "C", 3: "C", 4: "I", 5: "C", 6: "C", 7: "C", 8: "C", 9: "C", 10: "C",
    11: "C", 12: "C", 13: "I", 14: "I", 15: "C", 16: "C", 17: "C", 18: "C", 19: "C", 20: "C",
    21: "A", 22: "I", 23: "C", 24: "C", 25: "C", 26: "C", 27: "C", 28: "C", 29: "I", 30: "C",
    31: "C", 32: "M", 33: "C", 34: "C", 35: "C", 36: "C", 37: "C", 38: "M", 39: "M", 40: "C",
    41: "M", 42: "C", 43: "C", 44: "C", 45: "A", 46: "I", 47: "C", 48: "C", 49: "C", 50: "C",
    51: "C", 52: "C", 53: "C", 54: "C", 55: "C", 56: "C", 57: "C", 58: "C", 59: "C", 60: "C",
    61: "C", 62: "C", 63: "C", 64: "C", 65: "C", 66: "C", 67: "C", 68: "M", 69: "C", 70: "C",
    71: "C", 72: "C", 73: "C", 74: "C", 75: "C", 76: "C", 77: "C", 78: "C", 79: "C", 80: "C",
    81: "C", 82: "C", 83: "C", 84: "C", 85: "I", 86: "C", 87: "C", 88: "A", 89: "C", 90: "C",
    91: "C", 92: "C", 93: "C", 94: "C", 95: "C", 96: "I", 97: "C", 98: "C", 99: "C", 100: "C",
}

NOTAS = {
    4: "responde 'Ferro' en vez de 'hierro' -- calco del latin ferrum, no del espanol (v3 acertaba)",
    13: "granito 'metamorfica' en vez de ignea -- mismo error de v3",
    14: "unidad de herencia 'el cromosoma' en vez de 'el gen' -- mismo error de v3",
    21: "Bolivar: inventa 'estudio leyes en San Fernando', que Colombia fue 'el primer pais' "
        "en independizarse, y una cronologia falsa de su regreso a la politica en 1830 para "
        "Peru (la campana de Peru fue 1823-1826, no 1830) -- unico caso de alucinacion con "
        "respuesta larga, igual que v3",
    22: "confunde la fecha de la Batalla de Boyaca (7 agosto 1819) con una 'declaracion "
        "oficial', y luego dice que Boyaca fue el '7 de julio' (mes equivocado) -- confusion "
        "de fechas reales, no invencion de una entidad nueva",
    29: "Revolucion Industrial: siglo XIX en vez de XVIII -- mismo error de v3",
    45: "lago mas grande: inventa 'el Gran Lago Saimaa, ubicado en Finlandia' (Saimaa es un "
        "lago real pero ni de lejos el mas grande del mundo) -- unica alucinacion nueva "
        "respecto a v3, que en este item tambien fallaba (A) pero con L. Titicaca",
    46: "15x4 -> responde '3,75' (parece haber dividido en vez de multiplicar) -- error "
        "aritmetico simple, sin justificacion inventada (v3 tambien alucinaba aqui, con "
        "justificacion inventada)",
    85: "organo mas grande: 'el higado' en vez de 'la piel' -- mismo tipo de confusion que v3 (estomago)",
    88: "celula que transporta oxigeno: 'la hemocitina' (termino no estandar) -- mismo patron "
        "de fallo que v3 ('hemociana')",
    96: "alfabeto espanol: '26' en vez de 27 -- confusion razonable (26 sin contar la ñ), "
        "GRAN mejora sobre v3 que inventaba letras 'k (kappa)' y 'w (vega)'",
    # Casos donde v3.2 CORRIGE a v3 (los mas informativos -- el patron dominante)
    "corregidos_de_v3": [
        2, 3, 7, 9, 12,  # ciencia: v3 anadia justificacion inventada al nucleo correcto -> A; v3.2 responde corto y correcto
        30,  # Capilla Sixtina: v3 inventaba "Miguel Angel Sanchez Coello" y 3 pintores mas -> A; v3.2: "Michelangelo Buonarroti" -> C
        70,  # instrumento Louis Armstrong: v3 decia "el trombon" -> I; v3.2: "la trompeta" -> C
        82,  # protocolo de correo: v3 inventaba Flask-Mail/Google Workspace -> A; v3.2: "SMTP" -> C
        91,  # frecuencia JJOO: v3 decia "cada cinco anos" + inventaba una organizacion -> A; v3.2: "Cuatro anos" -> C
    ],
}
