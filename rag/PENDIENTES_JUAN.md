# Corpus RAG: decisiones de Juan y lo que sigue pendiente

Corpus de **42 fragmentos**. Juan aprobó el contenido el 19-oct-2026 (`aprobado_por = 'juan-2026-10-19'` al ingerir: `python rag/ingesta.py --aprobado-por juan-2026-10-19`). Regla: cada fragmento es texto literal de un archivo del repo o de `claude/`, salvo los dos de `APROBADOS` en `construir_corpus.py`, cuya redacción confirmó Juan. Los documentos del *Project* de Claude no están en el disco de Code.

## Fragmentos de la ampliación C3
| Fragmento | Origen |
|---|---|
| `05-resumen-municipios` | literal de `claude/fase1-2-divipola-cruce.md`, conclusión 1 (rag-34) |
| `06-mapa-semaforo` | literal del comentario de `MapView.jsx` (blanco 0, amarillo 0.5, rojo 1) |
| `06-mapa-color-por-variable` | literal del comentario de `variablesProyeccion.js` |
| `06-prioridad` | **aprobado por Juan**: no hay categorías alta/media/baja ni punto de corte; prioridad alta = Score cercano a 1; cita la leyenda del mapa y la fórmula (`01-formula`). Reemplaza a `06-leyenda-escala` |
| `06-mapa-gris` | **frase aprobada por Juan**: «Los municipios en gris no tienen dato para la variable y el año seleccionados.» |

## Resuelto con Juan
1. «Prioridad alta»: no existe umbral; el Score es continuo en [0, 1] (metodología de Techo 360, pares train_v3_3 revisados).
2. Gris del mapa: frase aprobada.
3. Aprobación del contenido: `juan-2026-10-19`.

## Sigue pendiente
1. **Notas de la leyenda** («el déficit habitacional se mantiene constante (Censo 2018)»; «la fiabilidad se ve al pasar el cursor»): solo existen en JSX; confirmar si se incluyen.
2. **Fiabilidad en lenguaje de usuario.** «¿Qué tan confiable es un valor proyectado?» no recupera `03-fiabilidad` (la pregunta dice «confiable», el texto «fiabilidad»). Falta un texto de guía de usuario o autorizar un sinónimo en el `tema`.
3. **Guía de uso** (panel, qué puede responder TechoBot): no hay README de usuario.
4. **Contradicción de `rag-22`** (el modelo dijo 2020; el dato real del déficit es de 2018, la metodología se publicó en 2020): decidir si se reescribe la frase en la fuente o se acepta.
5. `06-prioridad` y `06-mapa-gris` quedan redactados en `construir_corpus.py`: si cambia la metodología (p. ej. un corte oficial), hay que editarlos allí.
