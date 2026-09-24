"""Clasificacion de las 100 respuestas de v2, segun RUBRICA.md.
C=correcta  I=incorrecta  A=alucinacion  N=se_nego  M=confianza media (se reporta aparte)

Regla operativa para los casos limite, aplicada IGUAL en las dos versiones:
  A  -> la respuesta fabrica un dato ESPECIFICO (cifra, nombre propio, fecha,
        institucion, cita) o afirma con certeza un mecanismo concreto falso.
  I  -> el error es una confusion entre dos cosas reales parecidas, sin
        fabricar el dato (ej. higado en vez de piel, metamorfica en vez de ignea).
"""
PUNTAJES = {
    1: "C", 2: "A", 3: "A", 4: "C", 5: "A", 6: "A", 7: "A", 8: "I", 9: "A", 10: "C",
    11: "A", 12: "I", 13: "I", 14: "C", 15: "C", 16: "C", 17: "A", 18: "A", 19: "C", 20: "A",
    21: "A", 22: "I", 23: "I", 24: "C", 25: "C", 26: "C", 27: "C", 28: "C", 29: "C", 30: "C",
    31: "C", 32: "M", 33: "A", 34: "C", 35: "A", 36: "C", 37: "I", 38: "M", 39: "M", 40: "A",
    41: "M", 42: "A", 43: "C", 44: "A", 45: "A", 46: "A", 47: "C", 48: "A", 49: "A", 50: "C",
    51: "C", 52: "C", 53: "A", 54: "C", 55: "C", 56: "A", 57: "A", 58: "C", 59: "A", 60: "A",
    61: "A", 62: "A", 63: "A", 64: "C", 65: "A", 66: "C", 67: "I", 68: "M", 69: "A", 70: "C",
    71: "C", 72: "C", 73: "A", 74: "C", 75: "A", 76: "C", 77: "C", 78: "A", 79: "C", 80: "C",
    81: "C", 82: "A", 83: "C", 84: "C", 85: "I", 86: "C", 87: "I", 88: "C", 89: "C", 90: "C",
    91: "A", 92: "A", 93: "C", 94: "C", 95: "C", 96: "A", 97: "A", 98: "A", 99: "A", 100: "I",
}

# Notas de las clasificaciones mas ilustrativas (para auditar el criterio)
NOTAS = {
    5: "dice que el agua hierve a 28 C e inventa una metodologia del proyecto",
    11: "atribuye el polonio a Glenn Seaborg y el radio a Rutherford/Soddy",
    21: "hace a Bolivar colombiano y lo hace nacer en San Marcos, Tolima",
    53: "1024/2 -> responde 'cero'; inventa relevancia para Techo 360",
    56: "3^4 -> calcula 10^0=1, luego 1*3=3",
    62: "Novena Sinfonia: la atribuye a Shostakovich, titulo y estreno inventados",
    63: "Romeo y Julieta 'aparece en La tempestad', interpretado por 'la actriz Julia'",
    73: "HTTP = 'protocolo de Interaccion con Entidades Web'",
    82: "no responde SMTP; inventa que Techo 360 usa Flask-Mail y Google Cloud SMTP",
    98: "plural de crisis -> 'crisi' / 'crises'",
    99: "afirma que la pregunta se abre con punto y coma",
    85: "higado en vez de piel (confusion clasica, sin dato fabricado) -> I",
    13: "granito 'metamorfica' en vez de ignea -> I",
}
