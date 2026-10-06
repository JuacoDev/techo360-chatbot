"""Clasificacion de las 100 respuestas de v3, segun RUBRICA.md.
Mismo criterio y misma regla operativa de casos limite que puntajes_v2.py.
C=correcta  I=incorrecta  A=alucinacion  N=se_nego  M=confianza media (aparte)
"""
PUNTAJES = {
    1: "C", 2: "A", 3: "A", 4: "C", 5: "I", 6: "C", 7: "A", 8: "C", 9: "A", 10: "C",
    11: "I", 12: "A", 13: "I", 14: "I", 15: "I", 16: "C", 17: "C", 18: "I", 19: "I", 20: "A",
    21: "A", 22: "A", 23: "I", 24: "C", 25: "I", 26: "A", 27: "I", 28: "C", 29: "A", 30: "A",
    31: "C", 32: "M", 33: "A", 34: "C", 35: "C", 36: "C", 37: "I", 38: "M", 39: "M", 40: "C",
    41: "M", 42: "I", 43: "C", 44: "A", 45: "A", 46: "A", 47: "I", 48: "I", 49: "C", 50: "C",
    51: "C", 52: "C", 53: "C", 54: "C", 55: "C", 56: "C", 57: "C", 58: "A", 59: "I", 60: "I",
    61: "A", 62: "A", 63: "A", 64: "C", 65: "I", 66: "C", 67: "C", 68: "M", 69: "C", 70: "I",
    71: "A", 72: "C", 73: "C", 74: "A", 75: "A", 76: "I", 77: "C", 78: "C", 79: "C", 80: "C",
    81: "C", 82: "A", 83: "C", 84: "I", 85: "I", 86: "C", 87: "I", 88: "A", 89: "C", 90: "I",
    91: "A", 92: "C", 93: "I", 94: "A", 95: "C", 96: "A", 97: "C", 98: "I", 99: "C", 100: "C",
}

NOTAS = {
    12: "responde 'plomo' e inventa tres temperaturas de estado para el",
    21: "Bolivar OK en lugar/fechas, pero inventa a 'Jose Antonio Paramo' como cofundador",
    22: "inventa el 'tratado de Neutrality Proclamation' firmado en 1826",
    30: "Capilla Sixtina: inventa 'Miguel Angel Sanchez Coello' y tres pintores mas",
    62: "Novena Sinfonia: la atribuye a Shostakovich (mismo fallo que v2)",
    63: "Romeo y Julieta 'aparece en La vida es sueno' de Calderon",
    82: "no responde SMTP; inventa que Techo 360 usa Flask-Mail y Google Workspace",
    88: "inventa 'la hemociana' como componente de la sangre humana",
    91: "Juegos Olimpicos 'cada cinco anos' + inventa la 'Organizacion Internacional del Deporte'",
    96: "27 letras OK, pero inventa los nombres 'k (kappa)' y 'w (vega)'",
    # Casos donde v3 CORRIGE a v2 (los mas informativos)
    53: "1024/2 -> 512 correcto (v2 respondia 'cero')",
    73: "HTTP = Hypertext Transfer Protocol (v2 lo inventaba)",
    11: "Marie Curie correcta (v2 se lo atribuia a Seaborg y Rutherford)",
    5: "100 C correcto (v2 respondia 28 C)",
    56: "3^4 = 81 correcto (v2 calculaba 3)",
    # Casos donde v3 EMPEORA respecto a v2
    70: "responde 'el trombon' para Louis Armstrong (v2 acertaba la trompeta)",
    14: "dice que la unidad de herencia es el cromosoma (v2 acertaba el gen)",
    85: "estomago como organo mas grande (v2 decia higado; ambos incorrectos)",
}
