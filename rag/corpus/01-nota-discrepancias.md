---
fragmento: 01-nota-discrepancias
fuente: Nota del corpus (revision de discrepancias)
ruta: rag/construir_corpus.py
fecha: 2026-10-18
vigencia: hasta aplicar la carga M4
version: corpus-0.1
tema: Diferencias detectadas entre codigo y README sobre el Score y el deficit
---
Revision de discrepancias entre fuentes (hecha al construir el corpus, 2026-10-18):
1. No se encontro README del backend ni del frontend que describa la formula del Score; la unica fuente son los comentarios de routers/zonas.py y los docstrings de services/score_privacion.py. No hay version de README con la que contrastar.
2. El comentario de zonas.py dice que el deficit de 2024 es una proyeccion con fiabilidad 70 %; el README del backend advierte que la carga M4 (pendiente de aplicar) reemplazara 102 anclas del deficit cuantitativo 2024 por una variante con saturacion suave. Mientras no se aplique, manda el codigo y el comentario; despues de aplicarla, los fragmentos de 04-decisiones-fuentes-metodos (deficit 2024) y 01-metodologia-score deben revisarse.
3. Los limites min-max del Score son los del propio anio en el camino de datos reales y los fijos de 2024 en el camino de proyeccion (ver 01-metodologia-score); no es una contradiccion, pero una respuesta no debe mezclarlos.
