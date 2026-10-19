---
fragmento: 03-deficit-componentes
fuente: Proyecto Techo 360 - zonas.py
ruta: techo360-backend/routers/zonas.py
fecha: 2026-10-10
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@f10a0e0
tema: Deficit cuantitativo y cualitativo: componentes segun el anexo DANE
---
- Deficit CUANTITATIVO (cols 11-14): Tipo de vivienda, Material de
    Paredes, Cohabitacion, Hacinamiento no mitigable. NINGUN
    componente de servicios publicos.
  - Deficit CUALITATIVO (cols 15-28): incluye explicitamente "Agua
    para cocinar" (col 21) y "Alcantarillado" (col 23), ademas de
    Cocina, Energia y Recoleccion de basuras.
Como deficit_habitacional_total = cuantitativo + cualitativo, el total
arrastra ese solapamiento; el cuantitativo no.

---
fragmento: 03-deficit-columnas
fuente: Proyecto Techo 360 - dane_deficit_adapter.py
ruta: techo360-backend/ingestion/dane_deficit_adapter.py
fecha: 2026-09-26
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@91d62a1
tema: Deficit habitacional municipal DANE: hogares y porcentajes
nota: Lista de columnas del anexo del DANE tal como la documenta el adaptador de ingesta.
---
4: Total de hogares
5: Hogares en deficit cuantitativo   6: Hogares en deficit cualitativo
7: Hogares en deficit habitacional
8: Deficit cuantitativo (%)      9: Deficit cualitativo (%)
10: Deficit habitacional (%)

---
fragmento: 03-deficit-anio
fuente: Proyecto Techo 360 - dane_deficit_adapter.py
ruta: techo360-backend/ingestion/dane_deficit_adapter.py
fecha: 2026-09-26
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@91d62a1
tema: Anio real del deficit municipal (CNPV 2018)
---
AÑO: el censo (CNPV) es de 2018 -- ese es el año real del dato, aunque
la metodologia se PUBLICO en 2020.

---
fragmento: 03-densidad
fuente: Proyecto Techo 360 - db.py
ruta: techo360-backend/ingestion/db.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@321de04
tema: Densidad poblacional: poblacion DANE sobre area
---
para densidad_poblacional, calculado como poblacion municipal
    DANE (anexo oficial PPED 2018-2042, publicado 08-ago-2025) /
    area_km2 (PostGIS sobre zonas_municipio.geom, capa canonica
    IGAC).

---
fragmento: 03-tenencia
fuente: Proyecto Techo 360 - igac_catastro_adapter.py
ruta: techo360-backend/ingestion/igac_catastro_adapter.py
fecha: 2026-09-23
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@5716e20
tema: Tenencia informal: unidad de medida y formula
---
UNIDAD DE MEDIDA: a diferencia del diseño original (que fue pensado en
base al Censo del DANE, midiendo HOGARES), esta fuente mide PREDIOS
(unidades de terreno), no hogares. Esto se decidio conscientemente
-- son conceptos relacionados pero no identicos (un
predio puede tener varios hogares o estar vacio). La formula final:

% Tenencia Informal = (Predios con condicion_predio='Informal'
                        en el municipio / Total de predios del
                        municipio) x 100

VENTAJA DE RENDIMIENTO: se usa agregacion del lado del servidor
(outStatistics + groupByFieldsForStatistics de la API de ArcGIS) para
pedir CONTEOS ya calculados por municipio, en vez de descargar millones
de predios individuales -- confirmado en vivo: Medellin (05001) tiene
1.150.797 predios totales, y la consulta agregada devuelve el conteo
al instante, sin descargar cada fila.

---
fragmento: 03-tenencia-limitacion-1
fuente: Proyecto Techo 360 - igac_catastro_adapter.py
ruta: techo360-backend/ingestion/igac_catastro_adapter.py
fecha: 2026-09-23
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@5716e20
tema: Tenencia informal: limitacion conocida de la fuente
---
El 73% de los municipios con fila real (816 de 1.118, verificado en
vivo contra produccion) tienen valuevar=0.0 exacto para
tenencia_informal_terrenos. La causa tecnica esta en fetch() (linea
~122 mas abajo): `informales.get(cod_divipola, (nombre, 0))` trata la
AUSENCIA de cualquier predio con condicion_predio='Informal' en un
municipio como "0% de informalidad real", sin poder distinguir eso de
"el catastro multiproposito todavia no ha llegado a clasificar la
condicion de tenencia en este municipio" -- el campo `total` (linea
119) SI viene poblado (por eso el municipio no se descarta por completo
en la linea 120), pero eso solo confirma que existen predios
catastrados, no que su condicion_predio ya fue evaluada.

---
fragmento: 03-dato-real-proyeccion
fuente: Proyecto Techo 360 - origen.py
ruta: techo360-backend/services/origen.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@0635337
tema: Dato real frente a proyeccion: regla de clasificacion
---
es_proyeccion(origen) = origen EMPIEZA por "proyeccion-"
                     o TERMINA en "-proyeccion"  (caso TerriData-proyeccion)

---
fragmento: 03-dato-real
fuente: Proyecto Techo 360 - origen.py
ruta: techo360-backend/services/origen.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@0635337
tema: Dato real: definicion operativa y fila sin origen
---
es_real = not es_proyeccion. Una fila sin originVar (None) no cae en ninguno de los
patrones y se trata como real.

---
fragmento: 03-fiabilidad
fuente: Proyecto Techo 360 - origen.py
ruta: techo360-backend/services/origen.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@0635337
tema: Fiabilidad de un dato (0 a 100)
---
fiabilidad_de_origen(): fiabilidad 0-100 de una fila que YA existe en BD. Un dato
real vale 100 por convencion (no es una estimacion; la columna intervaloConfianza
es NULL en los datos reales). Una proyeccion usa su intervaloConfianza (reusado como
% 0-100, ver ingestion/db.py) y, si faltara, el minimo por defecto.
