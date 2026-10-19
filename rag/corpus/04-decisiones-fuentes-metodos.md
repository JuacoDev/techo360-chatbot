---
fragmento: 04-principio-procedencia
fuente: Proyecto Techo 360 - db.py
ruta: techo360-backend/ingestion/db.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@321de04
tema: Principio: ningun dato estimado se confunde con un dato real
---
procedencia de datos, para las 3 piezas de relleno de MapCalorDB
(cobertura de acueducto/alcantarillado, tenencia informal, deficit
habitacional) que necesitan datos 2025-2026 sin serie historica real
completa. Principio rector: ningun dato estimado puede confundirse
con un dato real -- por eso originVar deja de ser solo "de que fuente
vino" y pasa a ser tambien "es un dato observado o un relleno, y con
que metodo". intervaloConfianza queda NULL siempre que originVar sea
una fuente real (un dato observado no tiene intervalo de confianza,
por definicion); solo se llena en filas de relleno, como proxy del
error historico del metodo usado (no es un intervalo de prediccion
estadisticamente riguroso -- se documenta como tal en cada caso).

---
fragmento: 04-fuente-cnpv
fuente: Proyecto Techo 360 - dane_deficit_adapter.py
ruta: techo360-backend/ingestion/dane_deficit_adapter.py
fecha: 2026-09-26
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@91d62a1
tema: Fuente del deficit habitacional municipal: DANE, CNPV 2018
---
Confirmado en vivo (descarga real + inspeccion con pandas/openpyxl,
sesion previa a este adapter) que el anexo oficial del DANE SI trae el
dato desagregado a nivel MUNICIPAL, con codigo DIVIPOLA directo -- no
hace falta ninguna estimacion (SAE) para esto, es ingesta de dato real,
igual que TerriData/IGAC:

https://www.dane.gov.co/files/investigaciones/deficit-habitacional/
deficit-hab-2020-anexo-nueva-metodologia.xlsx

---
fragmento: 04-metodo-ultimo-valor-1
fuente: Proyecto Techo 360 - db.py
ruta: techo360-backend/ingestion/db.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@321de04
tema: Metodo de las coberturas proyectadas: ultimo valor observado
---
"proyeccion-ultimo-valor-observado-{anio}" (renombrado 22-sep-2026,
    ver ingestion/reetiquetar_ultimo_valor_observado.py -- ANTES
    "ultimo-valor-observado" sin prefijo, inconsistente con el
    resto del esquema y sin el prefijo "proyeccion-" que el
    frontend usa para clasificar la tarjeta como proyeccion en vez
    de fuente confirmada) -- baseline ingenuo (repetir el ultimo
    valor real conocido, sin ajuste). Usado para cobertura_acueducto/
    cobertura_alcantarillado 2025-2026, ambos anclados a {anio}=2024
    (decision del 30-ago-2026: el LightGBM entrenado para estas dos
    variables especificas queda PEOR que este mismo baseline en el
    set de test real ya documentado -- no es defendible usar a
    proposito el metodo que ya se sabe que es peor solo porque
    tambien es "un modelo"). Fiabilidad DINAMICA segun antiguedad
    (no un numero fijo como las otras dos proyecciones de abajo):
    fiabilidad = max(30, 60 - 10*(antiguedad-1)), antiguedad =
    yearm - anio_del_dato_real. Hoy: 60% para yearm=2025, 50% para
    yearm=2026 -- ver el docstring completo de

---
fragmento: 04-metodo-ultimo-valor-2
fuente: Proyecto Techo 360 - db.py
ruta: techo360-backend/ingestion/db.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@321de04
tema: Metodo de las coberturas proyectadas: ultimo valor observado
---
ingestion/reetiquetar_ultimo_valor_observado.py para la
    justificacion de cada parametro de la formula (incluye RMSE
    real medido a distintas antiguedades, no un numero inventado).

---
fragmento: 04-metodo-regresion-densidad
fuente: Proyecto Techo 360 - db.py
ruta: techo360-backend/ingestion/db.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@321de04
tema: Metodo de la densidad proyectada: regresion lineal de 4 puntos
---
"proyeccion-regresion-lineal-4puntos" (agregado 23-sep-2026)
    -- densidad_poblacional hacia el futuro, calculado por
    techo360-proyeccion (GET /api/proyecciones). Regresion lineal
    por minimos cuadrados sobre los 4 ultimos puntos REALES del
    municipio (ventana elegida con un backtesting de 4 cortes, ver
    ese modulo), ajustada contra el año real de cada punto y con
    recorte en 0. La primera version uso solo 2 puntos, pero el
    ultimo par podia no representar la tendencia (Medellin,
    Barranquilla y Cali proyectaban caida teniendo serie al alza).
    Reemplazo a
    LightGBM para esta variable tras un backtesting contra los años
    reales 2019-2024 (RMSE 28.07 vs 223.89 del LightGBM recursivo,
    que ademas correlacionaba NEGATIVAMENTE, -0.212, con la
    tendencia real). Ver el docstring de app/services/proyeccion.py
    en techo360-proyeccion para la tabla completa y la limitacion
    conocida del backtesting (los "reales" son a su vez
    proyecciones DANE/TerriData, no mediciones independientes).

---
fragmento: 04-metodo-deficit-2024
fuente: Proyecto Techo 360 - db.py
ruta: techo360-backend/ingestion/db.py
fecha: 2026-10-16
vigencia: vigente en el codigo de la rama revisada
version: techo360-backend@321de04
tema: Metodo del deficit 2024: tendencia nacional 2018-2024
nota: Ver 01-nota-discrepancias: la carga M4 pendiente cambia este metodo (saturacion suave).
---
"proyeccion-tendencia-nacional-2018-2024" (agregado 2026-09-09,
    ver ingestion/proyeccion_2024.py) -- deficit_habitacional_
    cuantitativo/cualitativo/total no tienen ninguna fuente
    municipal real para 2024 (DANE solo actualiza el deficit via la
    ECV, que no baja de nivel departamental/regional -- confirmado,
    no asumido). Se extrapola el valor municipal REAL de 2018 (el
    de DaneDeficitAdapter) aplicando la tasa de cambio NACIONAL
    2018->2024 de cada componente (CNPV 2018 vs ECV 2024, ambos
    DANE) de forma proporcional. Fiabilidad media-alta (parte de un
    dato municipal real, solo extrapola la tendencia) -- ver el
    modulo de proyeccion para la formula exacta y el aviso sobre
    por que el componente cuantitativo sube en vez de bajar
    (CNPV censo vs ECV encuesta no son perfectamente comparables).

---
fragmento: 04-metodos-implementados
fuente: Proyecto Techo 360 - fase3-diagnostico.md
ruta: claude/fase3-diagnostico.md
fecha: 2026-10-17
vigencia: informe del 17-oct-2026; el estado de la nota sobre Score (limites fijos de 2024) rige solo para proyecciones
version: sin-control-de-versiones (mtime)
tema: Metodos de proyeccion implementados y score al vuelo
---
- Métodos implementados: último valor real (coberturas; backtest 2026-10-10, mejor que la regresión en RMSE/MAE, salvo h=1 en acueducto) y regresión lineal de 4 puntos (densidad). «Tendencia lineal» solo existe en scripts de backtest. Déficit y tenencia se generan por scripts a CSV y se leen materializados.
- Score de privación: sin filas; se calcula al vuelo (1/3 de acueducto invertido, alcantarillado invertido y déficit cuantitativo; límites min-max fijos de 2024).
