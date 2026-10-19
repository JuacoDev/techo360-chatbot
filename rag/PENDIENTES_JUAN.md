# Corpus RAG: lo que falta y necesita Juan

Ampliación C3 (19-oct-2026). Regla: cada fragmento es texto literal de un documento del repo o de `claude/`; no se escribe prosa nueva. Los documentos del *Project* de Claude no están en el disco de Code: solo se usó lo que hay en los repos y en `techo360/claude/`.

## Lo que sí quedó (4 fragmentos nuevos, 41 en total)
| Fragmento | Tema | Fuente literal |
|---|---|---|
| `05-resumen-municipios` | cuántos municipios y códigos DIVIPOLA hay (rag-34) | `claude/fase1-2-divipola-cruce.md`, conclusión 1 («1 122 códigos; 1 103 municipios, San Andrés y 18 áreas no municipalizadas») |
| `06-leyenda-escala` | qué significa prioridad / necesidad de intervención | leyenda del mapa en `MapView.jsx` («un valor de 1.0 indica la máxima prioridad o necesidad de intervención») |
| `06-mapa-semaforo` | color de un municipio en el mapa del Score | comentario de `MapView.jsx` (blanco en 0, amarillo en 0.5, rojo en 1; 0 = mejor, 1 = peor) |
| `06-mapa-color-por-variable` | qué significa «más rojo» en cada variable del mapa de proyección | comentario de `variablesProyeccion.js` (porcentaje, invertido, logarítmico) |

Se quitó del texto copiado solo la numeración y la etiqueta de auditoría «1. **COMPROBADO:**» del primero y la referencia a una ruta interna del backend en el tercero (regla 6.1 «sin rutas internas»).

## Lo que NO se pudo escribir con fuente verificable (pendiente)
1. **«Prioridad alta» como categoría.** Ningún archivo revisado define umbrales ni niveles (alta / media / baja). Solo existe la frase de la leyenda sobre el valor 1.0. **Necesito de Juan:** (a) si «prioridad alta» es un umbral del Score (¿qué valor?) o solo un modo de decir «Score alto»; (b) el documento de metodología del Score del Project (`01-variables` lo cita como «Score_privación en el documento de metodología»); no está en ningún repo. Sin eso el bot solo puede decir lo que dice la leyenda.
2. **Color gris del mapa.** «Sin dato / Área en litigio» (gris) solo existe como constante (`COLOR_SIN_DATO`) y como una etiqueta de dos palabras en JSX; no hay prosa que citar. **Necesito:** una frase aprobada (p. ej. de la guía de usuario o de la presentación) que explique el gris.
3. **Notas de la leyenda** («el déficit habitacional se mantiene constante (Censo 2018)»; «la fiabilidad se ve al pasar el cursor») están en JSX, sin comentario con prosa. **Necesito:** confirmar que se pueden incluir tal cual (hoy no se extraen).
4. **«Dato estimado» / insignia de fiabilidad en lenguaje de usuario.** El corpus tiene `03-fiabilidad` (técnico, 0–100) y `06-tarjeta-fiabilidad` (código). La pregunta «¿qué tan confiable es un valor proyectado?» no recupera `03-fiabilidad` (el texto dice «fiabilidad», la pregunta «confiable»). **Necesito:** un texto de guía de usuario sobre fiabilidad, o autorizar que se agregue un sinónimo al `tema` (hoy no se hizo para no ajustar el corpus a la prueba).
5. **Guía de uso** (mapa de calor, panel, qué puede responder TechoBot): no existe README de usuario. **Necesito:** el documento del Project que la describa, si existe.
6. **Aprobación del contenido** (`aprobado_por`). Los documentos se marcan hoy con `claude-revision-*`; Juan no ha revisado el contenido extraído. **Necesito:** decidir quién aprueba antes de cargar en producción (paso 6.8).
7. **Contradicción conocida de `rag-22`** (año del déficit): el modelo contestó 2020 aunque el fragmento dice que el dato real es de 2018 (la metodología se publicó en 2020). No se cambió el fragmento. **Necesito:** decidir si se reescribe la frase en la fuente (`dane_deficit_adapter.py`) o se acepta.
