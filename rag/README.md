# rag/ — corpus curado e ingesta (Fase 6, pasos 6.1 mecánico y 6.2)

| Archivo | Para qué |
|---|---|
| `corpus/*.md` | Fragmentos con cabecera (`fragmento`, `fuente`, `ruta`, `fecha`, `vigencia`, `version`, `tema`). `corpus/INDICE.md` lista conteos, sha256 y huecos. **Generados**, no se editan a mano. |
| `construir_corpus.py` | Extrae texto literal de las fuentes aprobadas (`claude/fase6-1-corpus.md`) entre dos marcadores. Solo lee; escribe solo en `corpus/`. El PDF del CONPES 150 no se versiona: `--conpes-pdf RUTA`. |
| `ingesta.py` | Lee el corpus, fragmenta, calcula embeddings (multilingual-e5-small) y escribe en `rag_documentos` / `rag_fragmentos`. Idempotente (hash por fragmento), con `--dry-run`. **Se niega a escribir fuera de localhost.** |
| `medir_embeddings.py` | Mide un modelo en CPU: disco, RAM, ms por fragmento y por consulta, dimensión, acierto indicativo. |
| `evaluar_recuperacion.py`, `recuperacion_6_5_fallos.csv` | **Evaluación 6.5**: recall@5/@2/@1 y MRR de tres recuperadores (vectores e5-small, búsqueda de texto de Postgres en español, híbrido RRF) sobre las 40 preguntas conceptuales de `claude/fase6-4-preguntas.jsonl`; lista los fallos. Solo lee, base local. Informe: `claude/fase6-5-6-6-rag.md`. |
| `evaluar_recuperador_produccion.py`, `preguntas_ciegas_6_7b.jsonl` | **Reevaluación C3**: importa el recuperador real del backend (`services/orquestador/rag.py`, `ts_rank`) y el enrutador, y mide recall@5/@2/@1 y MRR sobre las 50 preguntas del 6.4 más las 18 «ciegas» del 6.7b (etiquetas esperadas escritas por C3 mirando el corpus, no a ciegas). Solo lee, base local. |
| `PENDIENTES_JUAN.md` | Qué fragmentos no tienen fuente verificable y qué se necesita de Juan. |
| `probar_recuperacion.py`, `preguntas_prueba.json`, `recuperacion_prueba.md` | Prueba mínima de recuperación (10 preguntas, top-5 con distancia). **No es la evaluación 6.5.** |

Dependencias (venv fuera del repo): `sentence-transformers`, `torch` (CPU), `psycopg[binary]`, `pgvector`, `pypdf`, `psutil`.
Versiones con las que se probó: sentence-transformers 6.1.0, torch 2.14.1+cpu, transformers 5.20.1, psycopg 3.3.6, pgvector (Python) 0.5.1.
`requirements.txt` del servicio fija sentence-transformers 3.1.1: no se probó con esa versión.

```
# corpus (regenera todo; mismo resultado si las fuentes no cambian)
python rag/construir_corpus.py --conpes-pdf /ruta/conpes150_social.pdf

# ingesta en una base LOCAL desechable (con la migración 0005 aplicada)
RAG_DATABASE_URL=postgresql://usuario:clave@localhost:5433/techo360_vector_test python rag/ingesta.py --dry-run
RAG_DATABASE_URL=...                                                          python rag/ingesta.py
python rag/ingesta.py --solo-analizar        # sin base de datos
python rag/ingesta.py --aprobado-por claude-revision-18oct   # marca aprobado_por/aprobado_en de los documentos
python rag/evaluar_recuperacion.py --preguntas ../claude/fase6-4-preguntas.jsonl --csv rag/recuperacion_6_5_fallos.csv
```

Limpieza del 18-oct-2026 (`EXCLUIR` y `REEMPLAZOS` en `construir_corpus.py`): 38 fragmentos; se quitaron 7 (entre ellos la nota de discrepancias) y la frase «con el equipo» de `03-tenencia`.

Ampliación del 19-oct-2026: 42 fragmentos (37 + `05-resumen-municipios`, `06-mapa-semaforo`, `06-mapa-color-por-variable` y, aprobados por Juan, `06-prioridad` y `06-mapa-gris` en `APROBADOS`; ver `PENDIENTES_JUAN.md`). El modo `str` de `construir_corpus.py` extrae literales de cadena de una línea.

La carga en producción es el paso 6.8 y requiere autorización explícita; no hay camino en estos scripts para hacerlo.
