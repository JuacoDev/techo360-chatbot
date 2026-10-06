"""
¿Cuantos de los 592 pares del dataset de v3 son conocimiento general PURO,
es decir, sin ninguna mencion ni redireccion al dominio de Techo 360?

Esto verifica (o refuta) la hipotesis que justificaria un v3.2: que el
modelo reconduce todo al proyecto porque practicamente todo lo que vio en
fine-tuning habla del proyecto.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

RUTA = Path(sys.argv[1] if len(sys.argv) > 1 else "dataset/entrenamiento_v3_solo_repos.jsonl")

# Vocabulario que delata que el par pertenece al dominio del proyecto o a
# su politica publica asociada. Se busca en instruction + response.
DOMINIO = [
    r"techo\s*360", r"score de privaci[oó]n", r"privaci[oó]n",
    r"d[eé]ficit habitacional", r"acueducto", r"alcantarillado",
    r"divipola", r"municipio", r"municipal", r"departamento",
    r"dane\b", r"igac\b", r"terridata", r"ipm\b", r"sisb[eé]n",
    r"pobreza", r"vivienda", r"hogares", r"catastro", r"upra",
    r"colombia", r"colombiano", r"panel de indicadores", r"mapa de calor",
    r"indicador", r"cobertura", r"tenencia informal", r"censo",
    r"pgvector", r"fastapi", r"postgres", r"rabbitmq", r"repositorio",
    r"backend", r"frontend", r"chatbot", r"lightgbm", r"ollama",
]
PATRON = re.compile("|".join(DOMINIO), re.IGNORECASE)

pares = [json.loads(l) for l in RUTA.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"Archivo: {RUTA}")
print(f"Pares totales: {len(pares)}\n")

print("=== Distribucion por campo 'source' ===")
for fuente, n in Counter(p.get("source", "(sin source)") for p in pares).most_common(15):
    print(f"  {n:>4}  {fuente[:95]}")
otras = len(Counter(p.get("source", "(sin source)") for p in pares)) - 15
if otras > 0:
    print(f"  ... y {otras} fuentes mas")

puros, mixtos = [], []
for p in pares:
    texto = f"{p.get('instruction','')} {p.get('response','')}"
    (puros if not PATRON.search(texto) else mixtos).append(p)

print(f"\n=== Conocimiento general PURO (sin ninguna palabra del dominio) ===")
print(f"  puros : {len(puros):>4}  ({100*len(puros)/len(pares):.1f}%)")
print(f"  dominio: {len(mixtos):>4}  ({100*len(mixtos)/len(pares):.1f}%)")

if puros:
    print(f"\n  Ejemplos de los 'puros' (para verificar que el filtro no miente):")
    for p in puros[:10]:
        print(f"    Q: {p['instruction'][:95]}")
        print(f"       A: {' '.join(p['response'].split())[:95]}")

# Segunda medida, mas estricta: menciona explicitamente Techo 360
PATRON_PROYECTO = re.compile(r"techo\s*360|score de privaci[oó]n|panel de indicadores", re.IGNORECASE)
solo_proyecto = sum(1 for p in pares
                    if PATRON_PROYECTO.search(f"{p.get('instruction','')} {p.get('response','')}"))
print(f"\n=== Mencion EXPLICITA de Techo 360 / Score de Privacion / panel ===")
print(f"  {solo_proyecto} de {len(pares)} pares ({100*solo_proyecto/len(pares):.1f}%)")

# ¿Hay algun par cuya respuesta sea corta y factual, sin contexto del proyecto?
print(f"\n=== Longitud de las respuestas ===")
largos = [len(p["response"].split()) for p in pares]
largos.sort()
print(f"  palabras por respuesta: mediana={largos[len(largos)//2]}, "
      f"p10={largos[len(largos)//10]}, p90={largos[9*len(largos)//10]}, max={largos[-1]}")
