---
fragmento: 01-formula
fuente: Proyecto Techo 360 - score_privacion.py
ruta: techo360-backend/services/score_privacion.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Formula del Score de privacion y que significan 0 y 1
---
Score compuesto de privacion (0=mejor, 1=peor), promedio simple
1/3 + 1/3 + 1/3 de acueducto invertido, alcantarillado invertido, y
deficit habitacional CUANTITATIVO (sin invertir -- ver el aviso de
doble conteo en el routers/zonas.py original: el cuantitativo, a
diferencia del total, no contiene componentes de acueducto/
alcantarillado). None si falta cualquiera de los 3 insumos -- incluye
el caso MpCodigo=00000 (Area en Litigio Cauca-Huila), que no tiene
fila real en mapcalordb para ninguna variable, asi que cae aqui de
forma natural sin caso especial.

---
fragmento: 01-variables
fuente: Proyecto Techo 360 - zonas.py
ruta: techo360-backend/routers/zonas.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Variables del Score y direccion de cada una
---
Las 3 variables que entran al score compuesto de privacion (expuesto
como score_privacion -- "Score_privación" en el documento de
metodologia, sin tilde/mayuscula aqui por consistencia con el resto
de nombres de campo de la API). Alkire-Foster / IPM adaptado, sin el
umbral k=33% oficial -- aqui es un promedio simple de 3 componentes
con peso igual 1/3 cada uno.
Acueducto y alcantarillado se INVIERTEN (1 - normalizado) porque mas
cobertura = menos privacion; el deficit ya viene en la direccion
correcta (mas deficit = mas privacion), no se invierte.
densidad_poblacional queda fuera a proposito -- es ponderador visual
de tamaño/opacidad en el frontend, no se mezcla en el color del mapa.

---
fragmento: 01-doble-conteo
fuente: Proyecto Techo 360 - zonas.py
ruta: techo360-backend/routers/zonas.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Por que el componente de deficit es el cuantitativo y no el total
---
>>> AVISO: por que el componente de deficit es el CUANTITATIVO y no el
>>> TOTAL (corregido 23-sep-2026) -- doble conteo confirmado <<<
Hasta este cambio, el tercer componente era deficit_habitacional_total.
Eso contaba acueducto y alcantarillado DOS VECES: una como variables
independientes (los dos primeros terminos) y otra dentro del propio
deficit. Confirmado en la fuente oficial, no asumido -- se descargo el
anexo real del DANE que ya ingiere ingestion/dane_deficit_adapter.py
(deficit-hab-2020-anexo-nueva-metodologia.xlsx, hoja "Total
Municipios") y se leyeron las columnas de componentes que ese adapter
NO usa (11-28):

---
fragmento: 01-doble-conteo-magnitud
fuente: Proyecto Techo 360 - zonas.py
ruta: techo360-backend/routers/zonas.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Magnitud del solapamiento entre deficit total y coberturas
---
MAGNITUD del solapamiento: el cociente (Agua para cocinar jerarquizado
+ Alcantarillado jerarquizado) / hogares en deficit cualitativo tiene
mediana 0.677 sobre 1.121 municipios del anexo, y supera 0.5 en el
68,8% de ellos. Los componentes NO son mutuamente excluyentes entre si
(un hogar puede tener varias carencias a la vez), asi que ese cociente
mide PESO, no una descomposicion exacta -- puede pasar de 1.

CONFIRMACION EMPIRICA INDEPENDIENTE (mapcalordb, yearm=2024), que
coincide con lo que predice la estructura de componentes del anexo:
  corr(deficit_cualitativo,  cobertura_alcantarillado) = -0.358
  corr(deficit_total,        cobertura_alcantarillado) = -0.307
  corr(deficit_CUANTITATIVO, cobertura_alcantarillado) = -0.022
  corr(deficit_CUANTITATIVO, cobertura_acueducto)      = -0.073
El cuantitativo es practicamente ortogonal a las coberturas -- justo
lo que se espera de una variable que no las contiene.

---
fragmento: 01-decision-cuantitativo
fuente: Proyecto Techo 360 - zonas.py
ruta: techo360-backend/routers/zonas.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Por que se mantienen las coberturas en el Score
---
POR QUE ESTA OPCION Y NO LA CONTRARIA (quitar las coberturas y dejar
el deficit total): (1) mantiene la estructura Alkire-Foster de 3
componentes con peso 1/3, sin rediseñar el score; (2) las coberturas
son las UNICAS entradas del score con dato real observado (TerriData),
mientras que el deficit de 2024 es una proyeccion con fiabilidad 70%
(ver ingestion/proyeccion_2024.py) -- quitarlas dejaria el compuesto
reducido a una sola variable proyectada.

---
fragmento: 01-limite-cuantitativo
fuente: Proyecto Techo 360 - zonas.py
ruta: techo360-backend/routers/zonas.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Limite de usar solo el deficit cuantitativo
---
LIMITE HONESTO de esta correccion: usar solo el cuantitativo descarta
la parte del deficit cualitativo que NO son servicios (hacinamiento
mitigable, pisos, cocina). La opcion mas fiel seria reconstruir un
"cualitativo sin servicios" a partir de las columnas de componentes
del anexo (que ya existen en la fuente, solo falta ingerirlas) y usar
cuantitativo + ese residuo. No se hizo aqui porque requiere extender
dane_deficit_adapter.py con variables nuevas; queda como mejora
pendiente, no como algo ya resuelto.

IMPORTANTE: esto cambia solo QUE ENTRA AL SCORE COMPUESTO.
deficit_habitacional_total sigue siendo una de las 7 variables que se
exponen en properties.indicadores y se muestran en el panel -- no se
oculta ni se deja de calcular.

---
fragmento: 01-normalizacion
fuente: Proyecto Techo 360 - score_privacion.py
ruta: techo360-backend/services/score_privacion.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Normalizacion min-max recortada a [0, 1]
---
Normalizacion min-max, RECORTADA a [0, 1]. None si falta cualquier insumo o
si el rango es degenerado (todas las filas con el mismo valor -- no
hay forma de normalizar sin inventar un 0 u 1 arbitrario).

El recorte (2026-10-10) importa en el camino de proyeccion: los limites son los
FIJOS de 2024 y un valor de otro año puede caer fuera de ese rango (p. ej. un
deficit proyectado por debajo del minimo de 2024 daba un normalizado < 0 y un
score < 0 en Sabaneta). En el camino real (limites del propio año) no cambia nada.

---
fragmento: 01-limites-por-anio
fuente: Proyecto Techo 360 - score_privacion.py
ruta: techo360-backend/services/score_privacion.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Limites min-max: del propio anio en datos reales, fijos de 2024 en proyeccion
---
Notese que calcular_score_privacion() NO recibe limites como parametro:
solo consume un `score_normalizado` ya calculado por variable. Quien
decide que limites usar es quien arma `indicadores_zona` ANTES de
llamarla -- routers/zonas.py sigue llamando normalizar_minmax() con el
min/max del propio año (comportamiento identico a antes); el camino de
proyeccion (routers/proyecciones.py) llama normalizar_minmax() con los
limites FIJOS del año base 2024 (ver calcular_limites_base() mas abajo)
antes de pasarle el resultado a esta misma funcion. La formula en si no
sabe ni le importa de donde salieron esos limites -- asi se evita
cambiar su contrato/comportamiento para el camino real.

---
fragmento: 01-limites-base
fuente: Proyecto Techo 360 - score_privacion.py
ruta: techo360-backend/services/score_privacion.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Limites fijos del anio base 2024 para el Score proyectado
---
Min/max de cada una de las 3 variables del score, sobre las filas de
`anio_base` (de cualquier origen) de los MUNICIPIOS del universo -- los de
zonas_municipio sin 00000/01001; los codigos huerfanos de areas no municipalizadas
NO fijan la escala (16 de ellos tenian el deficit cuantitativo saturado en 100 y
mantenian el maximo en 100 aunque ningun municipio llegara a ese valor). Mismo patron
que el min-max dinamico de routers/zonas.py, pero fijado a un solo
año en vez de recalcularse por request. Se llama una sola vez (ver
services/proyeccion_cache.py::obtener_limites_base/guardar_limites_base
para el cacheo) y el resultado se reutiliza para normalizar TODOS los
años proyectados, de forma que el score proyectado y el score real
del año base queden en la MISMA escala.

---
fragmento: 01-universo
fuente: Proyecto Techo 360 - score_privacion.py
ruta: techo360-backend/services/score_privacion.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Universo de municipios que fija la escala del Score
---
Codigos de los municipios REALES del mapa: los de zonas_municipio sin 00000/01001
(1,104 hoy). Excluye los 18-19 codigos huerfanos de areas no municipalizadas
(91263, 94883, 97511...), que tienen filas de deficit en mapcalordb pero ningun poligono.
