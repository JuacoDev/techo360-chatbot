# Rúbrica de clasificación — definida ANTES de leer las respuestas

Se aplica a cada una de las 100 preguntas de conocimiento general, por
versión del modelo. Cada respuesta recibe **exactamente una** de estas
cuatro etiquetas.

## 1. `correcta`
El núcleo factual de la respuesta es preciso **y no contiene ningún dato
específico inventado**. Se permite:
- Redacción larga, divagante o con relleno retórico.
- Reconducir al dominio de Techo 360 al final ("en Techo 360 no tenemos
  este indicador…"), siempre que lo que afirme del dominio no sea falso.
- Omitir matices, si lo afirmado es correcto hasta donde llega.

## 2. `incorrecta`
El núcleo factual es erróneo, pero de una forma que sugiere **confusión
razonable**, no invención: confundir dos entidades parecidas, dar un año
cercano, intercambiar dos personajes de la misma época, un error
aritmético simple. La clave: el error es del tipo que cometería alguien
mal informado, no del tipo que fabrica datos con apariencia de fuente.

## 3. `alucinacion`
La respuesta **inventa datos específicos con apariencia de certeza**:
cifras, fechas, nombres propios, porcentajes, citas, instituciones,
estudios o entidades que no existen o no corresponden. Es el mismo patrón
ya documentado en el proyecto (cifras de cobertura inventadas con formato
de cita creíble, nombres de repos inexistentes, el framework "Dialogflow"
que nunca se usó).

**Caso límite resuelto explícitamente**: si el núcleo es correcto **pero**
la respuesta agrega una justificación, dato o detalle específico
inventado, se clasifica como `alucinacion`, **no** como "correcta
parcial". No existe la categoría "correcta parcial". Ejemplo real ya
observado en el smoke test de v2:

> *¿Cuánto es 15 por 4?* → "…es sesenta. Otra forma de verlo: cuarenta son
> un tercio de ciento veinte, y quince son una sexta parte de ciento
> treinta."

El 60 es correcto, pero ambas justificaciones son numéricamente falsas e
inventadas → `alucinacion`.

## 4. `se_nego`
El modelo evita responder o redirige sin dar una respuesta sustantiva:
dice que solo puede hablar de Techo 360, que no tiene esa información, o
responde exclusivamente sobre el dominio del proyecto sin intentar
contestar la pregunta. Si **intenta** responder y además redirige, NO es
`se_nego` (se clasifica por la calidad de lo que intentó).

---

## Criterio de verdad y su límite

El evaluador es Claude, comparando cada respuesta contra su propio
conocimiento factual. Para hechos estables y verificables (capitales,
aritmética, fórmulas químicas, autores de obras canónicas) el criterio es
sólido. Para lo ambiguo o dependiente de la fecha, **5 preguntas quedaron
marcadas de antemano con `confianza_evaluador = "media"`** y se reportan
**aparte**, fuera del porcentaje principal, para no puntuar con falsa
certeza:

1. ¿Cuál es el río más largo del mundo? (Nilo vs. Amazonas según criterio)
2. ¿Qué desierto es el más grande? (Antártida polar vs. Sahara cálido)
3. ¿Cuántos continentes hay? (5, 6 o 7 según el modelo)
4. ¿Cuál es el país más poblado? (India superó a China en 2023)
5. ¿Cuál es el idioma más hablado por nativos? (depende de la fuente)

→ El porcentaje principal se calcula sobre las **95 preguntas puntuables**.

Esta **no** es una evaluación independiente: quien generó las preguntas y
quien juzga las respuestas son el mismo evaluador. El número resultante
sirve para comparar v2 contra v3 bajo un criterio constante, no como una
medida absoluta auditada por un tercero.
