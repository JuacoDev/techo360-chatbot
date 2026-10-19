"""Datos curados de las familias H (RAG, `[dN]`): intenciones con extractos LITERALES del corpus final (42 fragmentos).

Reglas (fase7-1 §4): las respuestas de H salen por extraccion y plantilla; un LLM solo revisa. Aqui cada intencion trae:
  esperados  fragmentos que responden (ids del corpus)
  piezas     trozos LITERALES del fragmento (tras la limpieza cosmetica de `gen_h.limpiar`: espacios, «**», «`», « -- » -> «, »,
             «_» -> « »); `test_extractos` comprueba que cada pieza esta en el fragmento
  forma      plantilla de la respuesta con {p1}, {p2}... (solo conectores neutros) o lista de elementos
  q          formulaciones de ENTRENAMIENTO (>= 6); qh: una formulacion de HOLDOUT (nunca entra al train)
Ninguna pieza menciona LightGBM. Sin cifras que no esten en la pieza.
"""

# Cada intencion: dict(id, esperados, piezas, forma, q, qh). `forma` = ("texto", plantilla) o ("lista", intro, [indices de pieza])
INTENCIONES = [
    dict(
        id="score-formula", esperados=["01-formula"],
        piezas=["Score compuesto de privacion (0=mejor, 1=peor), promedio simple 1/3 + 1/3 + 1/3 de acueducto invertido, alcantarillado invertido, y deficit habitacional CUANTITATIVO"],
        forma=("texto", "{p1}."),
        q=["¿Cómo se obtiene el Score de privación?", "Explícame la fórmula del score de privación.",
           "¿Qué promedio se usa para calcular el score de privación?", "¿Cómo se construye el índice de privación de la plataforma?",
           "¿Qué entra en el cálculo del Score y con qué peso?", "¿Cómo se define el Score de privación de un municipio?",
           "Dime de qué está hecho el score de privación."],
        qh="¿De qué manera se calcula el índice de privación que muestra Techo 360?",
    ),
    dict(
        id="score-escala", esperados=["01-formula", "06-prioridad"],
        piezas=["Score compuesto de privacion (0=mejor, 1=peor)"],
        forma=("texto", "{p1}."),
        q=["¿Qué significa un Score de privación alto?", "¿Un score de privación bajo es bueno o malo?",
           "¿Qué indica que el score de un municipio sea cercano a 1?", "¿Qué quiere decir que el score de un municipio sea 0?",
           "¿Cuál es la escala del Score de privación?", "¿Cómo se interpreta el valor del score de privación?",
           "¿Qué es mejor, un score de privación de 0 o de 1?"],
        qh="¿Qué nivel de privación refleja un índice cercano a uno?",
    ),
    dict(
        id="score-variables", esperados=["01-variables"],
        piezas=["Acueducto y alcantarillado se INVIERTEN (1 - normalizado) porque mas cobertura = menos privacion",
                "el deficit ya viene en la direccion correcta (mas deficit = mas privacion), no se invierte",
                "Alkire-Foster / IPM adaptado, sin el umbral k=33% oficial -- aqui es un promedio simple de 3 componentes con peso igual 1/3 cada uno"],
        forma=("texto", "{p3}. {p1}; {p2}."),
        q=["¿Qué variables entran en el Score de privación?", "¿Cuáles son los componentes del score?",
           "¿Por qué el acueducto se invierte en el score?", "¿Qué variables se invierten en el cálculo del score?",
           "¿Cuántos componentes tiene el índice de privación?", "¿Por qué el déficit no se invierte en el score?",
           "¿Cómo pesan los componentes dentro del score?"],
        qh="¿Cuáles datos alimentan el índice de privación y cómo se combinan?",
    ),
    dict(
        id="densidad-fuera-score", esperados=["01-variables"],
        piezas=["queda fuera a proposito -- es ponderador visual de tamaño/opacidad en el frontend, no se mezcla en el color del mapa"],
        forma=("texto", "La densidad poblacional {p1}."),
        q=["¿Por qué la densidad poblacional no entra en el Score?", "¿La densidad poblacional forma parte del score de privación?",
           "¿Para qué se usa la densidad poblacional en el mapa?", "¿Por qué el score no incluye la densidad?",
           "¿Qué papel cumple la densidad poblacional en la plataforma?", "¿Influye la densidad en el color de un municipio en el mapa?"],
        qh="¿Se mezcla la densidad de población en el color del mapa?",
    ),
    dict(
        id="doble-conteo", esperados=["01-doble-conteo"],
        piezas=["Hasta este cambio, el tercer componente era deficit habitacional total. Eso contaba acueducto y alcantarillado DOS VECES: una como variables independientes (los dos primeros terminos) y otra dentro del propio deficit."],
        forma=("texto", "{p1}"),
        q=["¿Por qué el Score usa el déficit cuantitativo y no el total?", "¿Qué problema de doble conteo había en el score?",
           "¿Por qué se cambió el componente de déficit del score?", "¿Por qué el déficit total contaba dos veces el acueducto?",
           "¿Qué diferencia hay entre usar el déficit total y el cuantitativo en el score?", "¿Qué se corrigió en el tercer componente del score?"],
        qh="¿Por qué se dejó de usar el déficit habitacional total en el índice de privación?",
    ),
    dict(
        id="coberturas-en-score", esperados=["01-decision-cuantitativo"],
        piezas=["las coberturas son las UNICAS entradas del score con dato real observado (TerriData), mientras que el deficit de 2024 es una proyeccion con fiabilidad 70%"],
        forma=("texto", "Se mantienen las coberturas porque {p1}."),
        q=["¿Por qué se mantienen las coberturas en el Score?", "¿Por qué no se quitaron las coberturas del score?",
           "¿Qué dato real tiene el score de privación?", "¿Qué fiabilidad tiene el déficit de 2024 que usa el score?",
           "¿Las coberturas del score son datos observados?", "¿Por qué el Score conserva acueducto y alcantarillado?"],
        qh="¿Cuál es la razón para dejar las coberturas dentro del índice de privación?",
    ),
    dict(
        id="limite-cuantitativo", esperados=["01-limite-cuantitativo"],
        piezas=["LIMITE HONESTO de esta correccion: usar solo el cuantitativo descarta la parte del deficit cualitativo que NO son servicios (hacinamiento mitigable, pisos, cocina)"],
        forma=("texto", "{p1}."),
        q=["¿Qué limitación tiene usar solo el déficit cuantitativo?", "¿Qué parte del déficit queda fuera del score?",
           "¿El score deja por fuera el hacinamiento mitigable?", "¿Qué descarta el score al usar solo el déficit cuantitativo?",
           "¿Cuál es el límite de la corrección del déficit en el score?", "¿Qué no captura el componente de déficit del Score?"],
        qh="¿Qué aspectos de la vivienda no cuenta el índice por usar el déficit cuantitativo?",
    ),
    dict(
        id="normalizacion", esperados=["01-normalizacion"],
        piezas=["Normalizacion min-max, RECORTADA a [0, 1]",
                "El recorte (2026-10-10) importa en el camino de proyeccion: los limites son los FIJOS de 2024 y un valor de otro año puede caer fuera de ese rango"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Cómo se normalizan las variables del Score?", "¿El score puede dar un valor negativo?",
           "¿Qué pasa si un valor se sale del rango en la normalización?", "¿Qué es la normalización min-max del score?",
           "¿Por qué el score nunca pasa de 1?", "¿Entre qué valores queda el score normalizado?"],
        qh="¿Puede el índice de privación quedar por debajo de cero?",
    ),
    dict(
        id="universo-score", esperados=["01-universo"],
        piezas=["Excluye los 18-19 codigos huerfanos de areas no municipalizadas (91263, 94883, 97511...), que tienen filas de deficit en mapcalordb pero ningun poligono"],
        forma=("texto", "{p1}."),
        q=["¿Qué códigos se excluyen del universo de municipios del score?", "¿Por qué las áreas no municipalizadas no cuentan para la escala del score?",
           "¿Qué municipios se tienen en cuenta para fijar la escala del score?", "¿Qué son los códigos huérfanos del universo del score?",
           "¿Qué códigos tienen filas de déficit pero ningún polígono?", "¿Cuáles códigos quedan fuera del universo de municipios?"],
        qh="¿Qué territorios no se consideran al definir la escala del índice?",
    ),
    dict(
        id="ipm-que-es", esperados=["02-ipm-definicion", "02-ipm-origen"],
        piezas=["El Índice de Pobreza Multidimensional (IPM), desarrollado por el Oxford Poverty & Human Development Initiative (OPHI) es un indicador que refleja la privación de los hogares en distintas dimensiones",
                "El IPM Colombia es un indicador de carácter multidimensional que incorpora diferentes variables de calidad de vida en cinco grupos o dimensiones"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Qué es el IPM?", "¿Qué es el IPM-Colombia?", "Explícame qué es el Índice de Pobreza Multidimensional.",
           "¿Qué tipo de indicador es el IPM?", "¿Qué mide el IPM de Colombia?", "Define el IPM en pocas palabras.", "¿A qué se refiere el IPM?"],
        qh="Cuéntame en qué consiste el Índice de Pobreza Multidimensional.",
    ),
    dict(
        id="ipm-por-que", esperados=["02-ipm-definicion"],
        piezas=["La posibilidad de analizar múltiples dimensiones de la pobreza es una de las razones para adoptar un índice de pobreza multidimensional para Colombia",
                "En este sentido, el IPM permite observar patrones de pobreza distintos a los de la pobreza monetaria"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Por qué Colombia adoptó un índice de pobreza multidimensional?", "¿Para qué sirve el IPM en la política pública?",
           "¿Qué ventaja tiene el IPM frente a la pobreza monetaria?", "¿En qué se diferencia el IPM de la pobreza monetaria?",
           "¿Por qué se usa el IPM para medir la pobreza?", "¿Qué patrones de pobreza permite ver el IPM?"],
        qh="¿Qué razones hubo para usar un índice multidimensional en el país?",
    ),
    dict(
        id="ipm-dimensiones", esperados=["02-ipm-dimensiones", "02-ipm-tabla"],
        piezas=["El IPM Colombia está conformado por cinco dimensiones: i) condiciones educativas del hogar; ii) condiciones de la niñez y la juventud; iii) trabajo; iv) salud y acceso a servicios públicos domiciliarios y, v) condiciones de la vivienda",
                "cada dimensión tiene el mismo peso y cada variable tiene el mismo peso al interior de cada dimensión"],
        forma=("texto", "{p1}. Además, {p2}."),
        q=["¿Cuántas dimensiones tiene el IPM?", "¿Qué dimensiones incluye el IPM de Colombia?", "¿Cuáles son los grupos de variables del IPM?",
           "¿Qué peso tiene cada dimensión del IPM?", "¿Las dimensiones del IPM pesan lo mismo?", "Enumera las dimensiones del IPM."],
        qh="¿En cuántos grupos se organizan las variables del Índice de Pobreza Multidimensional?",
    ),
    dict(
        id="ipm-trabajo", esperados=["02-ipm-tabla"],
        piezas=["Trabajo (0.2)", "Desempleo de larga duración (0.1)", "Empleo informal (0.1)"],
        forma=("texto", "En el IPM, {p1}: {p2} y {p3}."),
        q=["¿Qué indicadores mide la dimensión de trabajo del IPM?", "¿Qué variables tiene la dimensión de trabajo en el IPM?",
           "¿Cuánto pesa el trabajo dentro del IPM?", "¿Qué mide el IPM sobre empleo?", "¿Qué incluye la dimensión laboral del IPM?",
           "¿Cuáles son los indicadores de trabajo del IPM?"],
        qh="¿Con qué variables se mide el empleo en el Índice de Pobreza Multidimensional?",
    ),
    dict(
        id="ipm-salud", esperados=["02-ipm-tabla"],
        piezas=["Salud (0.2)", "Sin aseguramiento en salud (0.1)", "Barreras de acceso a servicio de salud (0.1)"],
        forma=("texto", "En el IPM, {p1}: {p2} y {p3}."),
        q=["¿Qué indicadores mide la dimensión de salud del IPM?", "¿Cuánto pesa la salud dentro del IPM?",
           "¿Qué variables de salud incluye el IPM?", "¿Qué mide el IPM sobre aseguramiento en salud?",
           "¿Cuáles son los indicadores de salud del IPM?", "¿Qué incluye la dimensión de salud del IPM?"],
        qh="¿Qué carencias de salud contempla el Índice de Pobreza Multidimensional?",
    ),
    dict(
        id="ipm-educacion", esperados=["02-ipm-tabla"],
        piezas=["Condiciones educativas del hogar (0.2)", "Bajo logro educativo (0.1)", "Analfabetismo (0.1)"],
        forma=("texto", "En el IPM, {p1}: {p2} y {p3}."),
        q=["¿Qué indicadores mide la dimensión de educación del IPM?", "¿Cuánto pesan las condiciones educativas en el IPM?",
           "¿Qué variables de educación incluye el IPM?", "¿Qué mide el IPM sobre analfabetismo?",
           "¿Cuáles son los indicadores educativos del IPM?", "¿Qué incluye la dimensión educativa del IPM?"],
        qh="¿Cómo mide el índice multidimensional la situación educativa del hogar?",
    ),
    dict(
        id="ipm-vivienda", esperados=["02-ipm-tabla"],
        piezas=["Servicios públicos domiciliarios y condiciones de la vivienda (0.2)", "Sin acceso a fuente de agua mejorada (0.04)",
                "Inadecuada eliminación de excretas (0.04)", "Pisos inadecuados (0.04)", "Paredes exteriores inadecuadas (0.04)",
                "Hacinamiento crítico (0.04)"],
        forma=("lista", "Estos son los indicadores de la dimensión {p1} del IPM:", [2, 3, 4, 5, 6]),
        q=["¿Qué indicadores de vivienda incluye el IPM?", "¿Qué variables tiene la dimensión de servicios públicos y vivienda del IPM?",
           "¿Qué mide el IPM sobre las condiciones de la vivienda?", "¿Cuáles son los indicadores de vivienda del IPM?",
           "¿Qué incluye la dimensión de vivienda del IPM?", "¿Cuántos indicadores de vivienda tiene el IPM y cuáles son?"],
        qh="¿Qué carencias de la vivienda mide el Índice de Pobreza Multidimensional?",
    ),
    dict(
        id="ipm-unidad", esperados=["02-ipm-unidad"],
        piezas=["Para el cálculo del IPM se utiliza al hogar como unidad de análisis",
                "En el caso del IPM de Colombia, la estimación se realizó con datos de las Encuestas de Calidad de Vida (ECV) del DANE para los años 1997, 2003, 2008 y 2010"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Cuál es la unidad de análisis del IPM?", "¿Con qué encuestas se calculó el IPM?", "¿El IPM se mide por persona o por hogar?",
           "¿Qué fuente de datos usa el IPM de Colombia?", "¿De qué años son las encuestas del IPM?", "¿Qué encuesta del DANE usa el IPM?"],
        qh="¿Sobre qué se hace el cálculo del índice multidimensional: personas u hogares?",
    ),
    dict(
        id="ipm-umbral", esperados=["02-ipm-umbral"],
        piezas=["Se considera que un hogar, y todas las personas que lo componen, es multidimensionalmente pobre si tiene privaciones en al menos el 33% de las 15 variables seleccionadas, teniendo en cuenta la ponderación asignada a cada una de ellas"],
        forma=("texto", "{p1}."),
        q=["¿Cuál es el umbral de pobreza multidimensional?", "¿Qué porcentaje de privaciones hace pobre a un hogar según el IPM?",
           "¿Cuándo un hogar es multidimensionalmente pobre?", "¿Cómo se identifica a un hogar pobre en el IPM?",
           "¿A partir de cuántas privaciones un hogar se considera pobre en el IPM?", "¿Cuántas variables cuentan para decidir si un hogar es pobre en el IPM?"],
        qh="¿Qué condición debe cumplir un hogar para ser considerado pobre por el IPM?",
    ),
    dict(
        id="deficit-cuantitativo", esperados=["03-deficit-componentes"],
        piezas=["Tipo de vivienda", "Material de Paredes", "Cohabitacion", "Hacinamiento no mitigable", "NINGUN componente de servicios publicos"],
        forma=("lista", "Estos son los componentes del déficit cuantitativo según los documentos:", [1, 2, 3, 4], "{p5}."),
        q=["¿Qué componentes tiene el déficit cuantitativo?", "¿Qué incluye el déficit habitacional cuantitativo?",
           "¿El déficit cuantitativo incluye servicios públicos?", "¿Qué variables forman el déficit cuantitativo de vivienda?",
           "¿De qué está compuesto el déficit cuantitativo?", "¿Qué mide el déficit cuantitativo?"],
        qh="¿Cuáles factores se cuentan dentro del déficit cuantitativo de vivienda?",
    ),
    dict(
        id="deficit-cualitativo", esperados=["03-deficit-componentes"],
        piezas=["incluye explicitamente \"Agua para cocinar\" (col 21) y \"Alcantarillado\" (col 23), ademas de Cocina, Energia y Recoleccion de basuras"],
        forma=("texto", "El déficit cualitativo {p1}."),
        q=["¿Qué incluye el déficit cualitativo?", "¿El déficit cualitativo incluye acueducto y alcantarillado?",
           "¿Qué componentes tiene el déficit habitacional cualitativo?", "¿Qué diferencia hay entre el déficit cuantitativo y el cualitativo en servicios?",
           "¿De qué está compuesto el déficit cualitativo?", "¿El déficit cualitativo cuenta la recolección de basuras?"],
        qh="¿Qué aspectos de servicios se cuentan en el déficit cualitativo?",
    ),
    dict(
        id="deficit-anio", esperados=["03-deficit-anio", "04-fuente-cnpv"],
        piezas=["el censo (CNPV) es de 2018 -- ese es el año real del dato, aunque la metodologia se PUBLICO en 2020"],
        forma=("texto", "Según los documentos, {p1}."),
        q=["¿De qué año es el dato de déficit habitacional por municipio?", "¿A qué año corresponde el déficit habitacional municipal?",
           "¿Cuál es el año real del déficit habitacional?", "¿El déficit habitacional municipal es de 2020?",
           "¿Qué censo es la base del déficit habitacional?", "¿En qué año se midió el déficit habitacional de los municipios?"],
        qh="¿Cuál es el año del censo del que sale el déficit habitacional de cada municipio?",
    ),
    dict(
        id="densidad-formula", esperados=["03-densidad"],
        piezas=["como poblacion municipal DANE (anexo oficial PPED 2018-2042, publicado 08-ago-2025) / area_km2"],
        forma=("texto", "La densidad poblacional se calcula {p1}."),
        q=["¿Cómo se calcula la densidad poblacional?", "¿De dónde viene la densidad poblacional?", "¿Qué fórmula usa la densidad poblacional?",
           "¿Qué población usa la plataforma para la densidad?", "¿Cómo se mide la densidad de población de un municipio?",
           "¿De dónde salen los datos de densidad?"],
        qh="¿Qué cálculo está detrás de la densidad de población que se muestra?",
    ),
    dict(
        id="tenencia-formula", esperados=["03-tenencia"],
        piezas=["esta fuente mide PREDIOS (unidades de terreno), no hogares",
                "% Tenencia Informal = (Predios con condicion_predio='Informal' en el municipio / Total de predios del municipio) x 100"],
        forma=("texto", "Se mide así: {p1}. La formula final: {p2}."),
        q=["¿Cómo se mide la tenencia informal?", "¿Qué unidad usa la tenencia informal, predios u hogares?", "¿Cuál es la fórmula de la tenencia informal?",
           "¿De qué fuente sale la tenencia informal?", "¿Cómo se calcula el porcentaje de tenencia informal?", "¿Qué mide la tenencia informal?"],
        qh="¿De qué manera se obtiene el porcentaje de tenencia informal de un municipio?",
    ),
    dict(
        id="dato-real-vs-proyeccion", esperados=["04-principio-procedencia", "03-dato-real-proyeccion", "03-dato-real"],
        piezas=["Principio rector: ningun dato estimado puede confundirse con un dato real"],
        forma=("texto", "{p1}."),
        q=["¿Cómo sé si un dato es real o una proyección?", "¿Por qué un dato estimado no se presenta como real?",
           "¿Cómo distingue la plataforma un dato real de uno estimado?", "¿Qué principio se sigue con los datos estimados?",
           "¿Se pueden confundir los datos estimados con los reales?", "¿Qué diferencia hay entre dato real y proyección?"],
        qh="¿Cómo evita la plataforma que una estimación pase por dato observado?",
    ),
    dict(
        id="fiabilidad", esperados=["03-fiabilidad", "06-tarjeta-fiabilidad"],
        piezas=["Un dato real vale 100 por convencion (no es una estimacion; la columna intervaloConfianza es NULL en los datos reales)",
                "El backend reusa intervalo_confianza como % de fiabilidad"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Qué significa la fiabilidad de un dato?", "¿Cuánto vale la fiabilidad de un dato real?", "¿Cómo se define la fiabilidad de una proyección?",
           "¿Qué es el intervalo de confianza en la plataforma?", "¿De dónde sale la fiabilidad de un dato?", "¿Qué indica la insignia de fiabilidad de una tarjeta?"],
        qh="¿Qué quiere decir el porcentaje de fiabilidad que acompaña a una estimación?",
    ),
    dict(
        id="fuente-deficit", esperados=["04-fuente-cnpv"],
        piezas=["el anexo oficial del DANE SI trae el dato desagregado a nivel MUNICIPAL, con codigo DIVIPOLA directo -- no hace falta ninguna estimacion (SAE) para esto, es ingesta de dato real, igual que TerriData/IGAC"],
        forma=("texto", "Según los documentos, {p1}."),
        q=["¿De dónde sale el déficit habitacional de cada municipio?", "¿Quién publica el déficit habitacional municipal?",
           "¿El déficit habitacional municipal es un dato real o estimado?", "¿Qué fuente tiene el déficit habitacional por municipio?",
           "¿Hay datos municipales de déficit habitacional del DANE?", "¿Cómo se obtiene el déficit habitacional municipal?"],
        qh="¿Cuál es el origen de las cifras de déficit de vivienda por municipio?",
    ),
    dict(
        id="proyeccion-coberturas", esperados=["04-metodo-ultimo-valor-1"],
        piezas=["baseline ingenuo (repetir el ultimo valor real conocido, sin ajuste)",
                "Fiabilidad DINAMICA segun antiguedad (no un numero fijo como las otras dos proyecciones de abajo)"],
        forma=("texto", "Las coberturas proyectadas usan un {p1}. {p2}."),
        q=["¿Cómo se proyectan las coberturas de acueducto y alcantarillado?", "¿Por qué se proyecta el acueducto repitiendo el último valor?",
           "¿Qué método de proyección usan las coberturas?", "¿Qué es el último valor observado en las proyecciones?",
           "¿Cómo se estima la cobertura de alcantarillado para años futuros?", "¿La fiabilidad de las coberturas proyectadas es fija?"],
        qh="¿Qué método se emplea para estimar las coberturas de servicios en años sin dato?",
    ),
    dict(
        id="proyeccion-densidad", esperados=["04-metodo-regresion-densidad"],
        piezas=["Regresion lineal por minimos cuadrados sobre los 4 ultimos puntos REALES del municipio (ventana elegida con un backtesting de 4 cortes, ver ese modulo), ajustada contra el año real de cada punto y con recorte en 0"],
        forma=("texto", "La densidad poblacional proyectada usa una {p1}."),
        q=["¿Cómo se proyecta la densidad poblacional?", "¿Qué método usa la densidad proyectada?", "¿En qué se basa la proyección de la densidad?",
           "¿Cuántos puntos reales usa la proyección de densidad?", "¿Qué regresión se usa para la densidad hacia el futuro?",
           "¿Cómo se estima la densidad poblacional de años futuros?"],
        qh="¿Con qué técnica se calcula la densidad de población de años que aún no ocurren?",
    ),
    dict(
        id="proyeccion-deficit", esperados=["04-metodo-deficit-2024"],
        piezas=["no tienen ninguna fuente municipal real para 2024", "DANE solo actualiza el deficit via la ECV, que no baja de nivel departamental/regional"],
        forma=("texto", "El déficit habitacional {p1}. {p2}."),
        q=["¿Cómo se estima el déficit habitacional de 2024?", "¿Por qué el déficit de 2024 es una estimación?",
           "¿Hay datos municipales reales de déficit para 2024?", "¿De dónde sale el déficit habitacional proyectado?",
           "¿Por qué el déficit de 2024 no es un dato real?", "¿Qué fuente tiene el déficit de 2024?"],
        qh="¿Existe una cifra municipal observada de déficit para 2024?",
    ),
    dict(
        id="metodos-proyeccion", esperados=["04-metodos-implementados"],
        piezas=["Métodos implementados: último valor real (coberturas; backtest 2026-10-10, mejor que la regresión en RMSE/MAE, salvo h=1 en acueducto) y regresión lineal de 4 puntos (densidad)",
                "Score de privación: sin filas; se calcula al vuelo (1/3 de acueducto invertido, alcantarillado invertido y déficit cuantitativo; límites min-max fijos de 2024)"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Qué métodos de proyección usa la plataforma?", "¿Cómo se proyecta el score de privación?", "¿Qué métodos de proyección están implementados?",
           "¿El score de privación se guarda o se calcula al vuelo?", "¿Qué método se usa para las coberturas y cuál para la densidad?",
           "¿Cómo se calcula el score cuando el año es futuro?"],
        qh="¿Cuáles técnicas de estimación hay disponibles en la plataforma?",
    ),
    dict(
        id="divipola-total", esperados=["05-codigos-oficiales", "05-resumen-municipios"],
        piezas=["La lista oficial vigente (30-jun-2026) tiene 1 122 códigos; 1 103 municipios, San Andrés y 18 áreas no municipalizadas"],
        forma=("texto", "{p1}."),
        q=["¿Cuántos municipios hay en Colombia según el DANE?", "¿Cuántos códigos DIVIPOLA hay?", "¿Cuántos municipios y áreas no municipalizadas hay?",
           "¿Qué es el DIVIPOLA y cuántos códigos tiene?", "¿Cuántos códigos de municipios tiene la lista oficial?", "¿Cuántos municipios cuenta la plataforma?"],
        qh="¿Cuál es el total de códigos que trae la lista oficial de divisiones político-administrativas?",
    ),
    dict(
        id="areas-no-municipalizadas", esperados=["05-areas-no-municipalizadas"],
        piezas=["18 códigos en DIVIPOLA sin geometría en el geojson. Son exactamente las 18 «áreas no municipalizadas»",
                "Amazonas (9)", "Guainía (6)", "Vaupés (3)"],
        forma=("lista", "{p1}. Están repartidas así:", [2, 3, 4]),
        q=["¿Qué son las áreas no municipalizadas?", "¿Por qué algunos códigos no tienen polígono en el mapa?",
           "¿Cuántas áreas no municipalizadas hay y dónde están?", "¿En qué departamentos hay áreas no municipalizadas?",
           "¿Qué pasa con los códigos DIVIPOLA sin geometría?", "¿Qué municipios no aparecen dibujados en el mapa?"],
        qh="¿Qué territorios del DIVIPOLA no tienen forma dibujada en el mapa?",
    ),
    dict(
        id="litigio-cauca-huila", esperados=["05-caso-00000"],
        piezas=["\"Area En Litigio Cauca - Huila\": existe como poligono en zonas_municipio (codigo '00000') y en zonas_departamento (codigo '00'), pero no es un municipio ni un departamento reales -- DANE no le asigna codigo propio y mapcalordb no tiene ninguna fila para ella"],
        forma=("texto", "{p1}."),
        q=["¿Qué es el área en litigio Cauca-Huila?", "¿Qué es el código 00000?", "¿Por qué hay un polígono del litigio Cauca-Huila?",
           "¿El área en litigio es un municipio?", "¿Tiene datos el área en litigio entre Cauca y Huila?", "¿Qué pasa con el código 00000 en el mapa?"],
        qh="¿Qué representa el polígono que no es ni municipio ni departamento entre Cauca y Huila?",
    ),
    dict(
        id="nombres-distintos", esperados=["05-nombres-distintos"],
        piezas=["En los 1 104 códigos comunes hay 22 pares con nombre distinto tras normalizar mayúsculas y tildes, por ejemplo 05148 «EL CARMEN DE VIBORAL» (DANE) vs «Carmen De Viboral» (IGAC)",
                "Son diferencias de nombre oficial vs nombre corto, no de código"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Por qué un municipio tiene un nombre distinto en el mapa que en el DANE?", "¿Por qué algunos nombres de municipios no coinciden?",
           "¿Qué diferencia hay entre el nombre oficial y el nombre corto de un municipio?", "¿Cuántos municipios tienen nombres distintos entre fuentes?",
           "¿Cambian los códigos cuando el nombre del municipio es distinto?", "¿Por qué Carmen de Viboral aparece con otro nombre?"],
        qh="¿A qué se debe que un mismo municipio se escriba distinto según la fuente?",
    ),
    dict(
        id="insignia-fiabilidad", esperados=["06-tarjeta-fiabilidad"],
        piezas=["Cualquier otro origen es dato confirmado y no lleva badge", "El backend reusa intervalo_confianza como % de fiabilidad"],
        forma=("texto", "En el panel de indicadores, {p1}. {p2}."),
        q=["¿Qué significa la insignia de fiabilidad del panel de indicadores?", "¿Cuándo una tarjeta lleva insignia de fiabilidad?",
           "¿Por qué algunas tarjetas del panel no tienen insignia?", "¿Qué tarjetas del panel son proyección?",
           "¿Cómo se muestra la fiabilidad en las tarjetas del panel?", "¿Un dato confirmado lleva insignia de fiabilidad?"],
        qh="¿Cuándo aparece el distintivo de fiabilidad en una tarjeta del panel?",
    ),
    dict(
        id="estados-mensaje", esperados=["06-estado-mensajes"],
        piezas=["Cada mensaje de usuario tiene estado: pendiente, procesando, respondido, error o cancelado"],
        forma=("texto", "{p1}."),
        q=["¿Qué estados puede tener un mensaje del chat?", "¿Cuáles son los estados de un mensaje en TechoBot?",
           "¿Qué significa que un mensaje esté pendiente?", "¿Qué estados tiene un mensaje del asistente?",
           "¿En qué estados puede estar mi mensaje?", "¿Un mensaje puede quedar cancelado?"],
        qh="¿Por qué estados pasa lo que escribo en el chat?",
    ),
    dict(
        id="color-mapa-variable", esperados=["06-mapa-color-por-variable"],
        piezas=["\"directo\" el valor ya esta en [0, 1] (score)", "\"porcentaje\" valor/100: mas = mas rojo (deficit, tenencia informal)",
                "\"invertido\" 1 - valor/100: menos cobertura = mas rojo", "\"log\" escala logaritmica entre el minimo y el maximo POSITIVOS del año mostrado (densidad)"],
        forma=("lista", "Así se colorea el mapa de proyección según la variable:", [1, 2, 3, 4]),
        q=["¿Qué significa más rojo en el mapa de proyección?", "¿Cómo se colorea el mapa según la variable?", "¿Por qué la cobertura se muestra invertida en el mapa?",
           "¿Qué escala de color usa la densidad en el mapa?", "¿Más rojo significa mejor o peor en el mapa?", "¿Cómo se pinta el mapa para el déficit?"],
        qh="¿Qué quiere decir el color rojo según la variable que se esté viendo?",
    ),
    dict(
        id="semaforo-mapa", esperados=["06-mapa-semaforo"],
        piezas=["Semaforo del score de privacion (0=mejor, 1=peor): interpolacion lineal por tramos entre tres puntos, blanco en 0, amarillo en 0.5, rojo en 1 (decision de producto, no buckets absolutos como antes)"],
        forma=("texto", "{p1}."),
        q=["¿Cómo interpreto el color de un municipio en el mapa?", "¿Qué significan el blanco, el amarillo y el rojo del mapa?",
           "¿Cómo se colorea el score en el mapa?", "¿Qué color tiene un municipio con score de 0.5?", "¿Cómo funciona el semáforo del mapa?",
           "¿Qué significa que un municipio esté en rojo en el mapa?"],
        qh="¿Por qué un municipio se ve amarillo en el mapa?",
    ),
    dict(
        id="prioridad", esperados=["06-prioridad"],
        piezas=["No existen categorias de prioridad (alta, media o baja) ni un punto de corte oficial",
                "Que un municipio tenga prioridad alta, o la maxima prioridad, significa un valor cercano a 1: segun la leyenda del mapa, 1.0 indica la maxima prioridad o necesidad de intervencion"],
        forma=("texto", "{p1}. {p2}."),
        q=["¿Existen categorías de prioridad alta, media y baja?", "¿Qué significa prioridad alta de un municipio?", "¿Hay un punto de corte para la prioridad?",
           "¿Qué es la prioridad de intervención?", "¿Cuándo un municipio tiene la máxima prioridad?", "¿Cómo se define la necesidad de intervención de un municipio?"],
        qh="¿Cómo se decide si un municipio es de prioridad máxima?",
    ),
    dict(
        id="mapa-gris", esperados=["06-mapa-gris"],
        piezas=["Los municipios en gris no tienen dato para la variable y el año seleccionados"],
        forma=("texto", "{p1}."),
        q=["¿Qué significa el color gris en el mapa?", "¿Por qué hay municipios en gris?", "¿Qué quiere decir que un municipio esté gris?",
           "¿Un municipio gris tiene datos?", "¿Por qué algunos municipios no tienen color en el mapa?", "¿Qué pasa con los municipios sin dato en el mapa?"],
        qh="¿A qué se debe que ciertos municipios aparezcan grises?",
    ),
    dict(  # solo para H5: la respuesta dice EXPLICITAMENTE que no tienen poligono
        id="areas-sin-poligono", esperados=["05-areas-no-municipalizadas"],
        piezas=["18 códigos en DIVIPOLA sin geometría en el geojson. Son exactamente las 18 «áreas no municipalizadas»",
                "Amazonas (9)", "Guainía (6)", "Vaupés (3)"],
        forma=("lista", "No tienen polígono en el mapa. {p1}. Están repartidas así:", [2, 3, 4]),
        q=[], qh=None,
    ),
]

# Premisas contrarias al fragmento (H5): (id de intencion, preguntas con la premisa falsa, apertura que corrige = plantilla de respuesta)
PREMISAS = [
    ("deficit-anio", ["Entiendo que el déficit habitacional municipal es de 2020, ¿cierto?", "El déficit habitacional de cada municipio es de 2022, ¿verdad?",
                      "¿Por qué el déficit habitacional municipal es del censo de 2024?"], "dato real de 2018"),
    ("ipm-umbral", ["¿Es cierto que un hogar es pobre en el IPM con privaciones en el 50% de las variables?", "Un hogar es multidimensionalmente pobre con el 20% de privaciones, ¿no?",
                    "¿Por qué el umbral del IPM es del 10% de las variables?"], "umbral del 33%"),
    ("ipm-dimensiones", ["¿Por qué el IPM tiene seis dimensiones?", "El IPM mide cuatro dimensiones, ¿verdad?", "¿Es cierto que cada dimensión del IPM pesa distinto?"], "cinco dimensiones"),
    ("ipm-unidad", ["¿El IPM se calcula por persona y no por hogar?", "¿Es cierto que el IPM usa los censos de 2005 y 2018?", "El IPM se estimó con la Gran Encuesta Integrada de Hogares, ¿no?"], "unidad de análisis"),
    ("score-variables", ["¿Es cierto que el Score de privación incluye la densidad poblacional?", "El score es un promedio de cuatro variables, ¿verdad?",
                         "¿Por qué el déficit cuantitativo se invierte en el score?"], "tres componentes"),
    ("coberturas-en-score", ["¿Por qué el déficit de 2024 del score es un dato real observado?", "¿Es cierto que el score solo usa datos proyectados?"], "coberturas con dato real"),
    ("divipola-total", ["¿Es cierto que Colombia tiene 1.200 municipios según el DIVIPOLA?", "¿Por qué hay 20 áreas no municipalizadas en Colombia?",
                        "Entiendo que el DIVIPOLA trae mil códigos exactos, ¿no?"], "1 122 códigos"),
    ("tenencia-formula", ["¿La tenencia informal se mide en hogares?", "¿Es cierto que la tenencia informal se calcula con el Censo del DANE?"], "mide predios"),
    ("proyeccion-densidad", ["¿La densidad se proyecta con una regresión de 10 puntos?", "¿Es cierto que la densidad proyectada usa un modelo de árboles?"], "regresión de 4 puntos"),
    ("estados-mensaje", ["¿Un mensaje del chat puede tener tres estados?", "¿Es cierto que los mensajes solo pueden estar pendientes o respondidos?"], "cinco estados"),
    ("semaforo-mapa", ["¿Por qué el mapa usa verde para el score de 0?", "¿El rojo del mapa significa el valor 0 del score?"], "blanco en 0"),
    ("mapa-gris", ["¿El gris del mapa significa que el valor es cero?", "¿Por qué los municipios grises tienen el dato más bajo?"], "sin dato"),
    ("prioridad", ["¿Es cierto que hay tres categorías oficiales de prioridad: alta, media y baja?", "¿La prioridad alta empieza en un Score de 0.7?"], "no existen categorías"),
    ("areas-no-municipalizadas", ["¿Por qué las áreas no municipalizadas tienen polígono en el mapa?", "¿Es cierto que las áreas no municipalizadas están en Boyacá?"], "sin geometría"),
    ("fuente-deficit", ["¿El déficit habitacional municipal es una estimación estadística (SAE)?", "¿Por qué el déficit municipal sale de una encuesta y no del censo?"], "dato real municipal"),
]

# Preguntas SIN cobertura en el corpus (H3): la plataforma no tiene un documento que las responda.
H3_PREGUNTAS = [
    # definiciones oficiales ausentes
    "¿Cómo define la Superservicios la cobertura de acueducto?", "¿Cuál es la definición oficial de cobertura de alcantarillado?",
    "¿Qué es la cobertura de acueducto según el DANE?", "¿Qué es el índice de privación según la OCDE?", "¿Qué significa la cobertura de acueducto en términos legales?", "¿Qué es el saneamiento básico según la plataforma?",
    "¿Qué es el mínimo vital según la plataforma?",
    # IPM no cubierto
    "¿Cuál es el IPM de Colombia más reciente?", "¿Cómo se calcula el IPM departamental?", "¿Qué actualizaciones tuvo el IPM después de 2012?",
    "¿Qué pesos tiene el IPM de 2018?", "¿Cuántos hogares son pobres según el IPM?", "¿Cómo se calcula el IPM rural?", "¿Qué es el IPM-Bogotá?", "¿Cómo se calcula el IPM de Venezuela?",
    # plataforma operativa y alcance
    "¿Quién financia la plataforma Techo 360?", "¿Qué licencia tiene el código de la plataforma?", "¿Cuánto cuesta usar la plataforma?",
    "¿Cómo puedo exportar los datos de la plataforma?", "¿Tiene la plataforma una API pública?", "¿Cómo creo una cuenta en la plataforma?",
    "¿Qué navegadores soporta la plataforma?", "¿Cada cuánto se actualizan los datos de la plataforma?", "¿Quién mantiene los servidores de la plataforma?",
    "¿Qué municipios nuevos se agregarán a la plataforma?", "¿La plataforma funciona sin internet?", "¿Qué idiomas soporta la plataforma?",
    "¿Cómo reporto un error de la plataforma?", "¿Qué versión de la plataforma estoy usando?", "¿Dónde está alojada la plataforma?",
    # metodología no cubierta
    "¿Qué peso tiene cada componente del déficit cualitativo?", "¿Qué error tiene la proyección de la cobertura de acueducto a diez años?",
    "¿Cómo se valida el score de privación frente a otras mediciones?", "¿Qué municipios tienen mayor prioridad de intervención?", "¿Cómo se ponderan los municipios para el promedio nacional?",
    "¿Cómo se calcula el hacinamiento crítico?",
    "¿Cuál es el umbral de fiabilidad aceptable para un dato proyectado?",
    # fuera del alcance con vocabulario de la plataforma
    "¿Qué es el IPM en México?", "¿Cómo mide la pobreza el Banco Mundial?", "¿Qué dice el DANE sobre el empleo en Colombia?",
    "¿Cuál es el dato de pobreza monetaria de Colombia en 2023?", "¿Qué indica el índice de desarrollo humano de Colombia?",
    "¿Cómo se calcula el índice de Gini de los municipios?", "¿Cuántas personas viven en la zona rural según la plataforma?", "¿Qué porcentaje de hogares tiene internet según los datos de la plataforma?",
    "¿Cómo se calcula la cobertura de energía eléctrica?", "¿Cuál es la fuente de la cobertura de gas natural?", "¿Cómo se mide el acceso a internet en el IPM?",
    "¿Cómo se estima la población de un municipio por barrio?", "¿Qué proyecciones hace la plataforma sobre desplazamiento?",
    "¿Qué es la pobreza extrema según la plataforma?", "¿Cómo calcula la plataforma el crecimiento de la población?",
    "¿Cómo se define un municipio rural en la plataforma?", "¿Qué estima la plataforma sobre el déficit de 2035 por departamento?",
    "¿Cómo se calculan las líneas de pobreza?",
    "¿Qué indicadores de salud tiene la plataforma por municipio?", "¿Qué porcentaje del déficit cualitativo se debe a la cocina?",
    "¿Qué es el estrato socioeconómico en la plataforma?", "¿Cómo se calcula el valor catastral en la plataforma?",
    # ---- revision 7.3b: solo preguntas cuyo tema NO esta en los 42 fragmentos
    "¿Cómo define la CEPAL la pobreza multidimensional?",
    "¿Cómo define la OCDE la cobertura de acueducto?",
    "¿Cómo calcula el DANE la pobreza monetaria?",
    "¿Qué dice el Ministerio de Vivienda sobre el déficit cualitativo en su último informe?",
    "¿Cómo define el DNP la prioridad de inversión de un municipio?",
    "¿Qué es la cobertura de alcantarillado según la Superintendencia de Servicios Públicos?",
    "¿Cuál es la fórmula del IPM departamental del DANE?",
    "¿Qué entiende ONU-Hábitat por vivienda adecuada en sus informes?",
    "¿Cuál es el IPM de Perú?",
    "¿Cómo calcula México el IPM?",
    "¿Cuál es el déficit habitacional de Chile?",
    "¿Qué cobertura de acueducto tiene Argentina?",
    "¿Cómo mide Brasil la pobreza multidimensional?",
    "¿Qué es el IPM de Ecuador?",
    "¿Cómo calcula España la tasa de pobreza?",
    "¿Cómo se calcula el IPM de la zona rural dispersa?",
    "¿Qué diferencia hay entre el IPM urbano y el IPM rural?",
    "¿Cuál es el IPM de las cabeceras municipales?",
    "¿Qué pesos tiene el IPM rural?",
    "¿Cómo se calcula el IPM de los centros poblados?",
    "¿Cómo se calcula la cobertura de internet de un municipio?",
    "¿Qué es la cobertura de energía eléctrica en la plataforma?",
    "¿Cuál es la tasa de desempleo por municipio que usa la plataforma?",
    "¿Qué variable de ingresos de los hogares tiene la plataforma?",
    "¿Cómo se calcula la mortalidad infantil que muestra la plataforma?",
    "¿Cuál es la variable de matrícula escolar que usa la plataforma?",
    "¿Qué es la variable de pobreza monetaria de la plataforma?",
    "¿Qué es el indicador de acceso a la salud en la plataforma?",
    "¿Cómo se calcula la cobertura de telefonía móvil en la plataforma?",
    "¿Quiénes son los desarrolladores de la plataforma?",
    "¿Qué tecnologías usa la plataforma?",
    "¿Cuántos usuarios tiene la plataforma?",
    "¿Cómo recupero mi contraseña de la plataforma?",
    "¿Hay una versión móvil de la plataforma?",
    "¿Puedo descargar el mapa de la plataforma como imagen?",
    "¿Cómo contacto al equipo de la plataforma?",
    "¿La plataforma guarda mi historial de consultas?",
    "¿Cuál es la política de privacidad de la plataforma?",
    "¿Qué datos personales recoge la plataforma?",
    "¿Cómo se calcula el error de la proyección de la cobertura de alcantarillado?",
    "¿Qué criterio decide qué municipios entran a una intervención?",
]

# Preguntas H3 del HOLDOUT (10; nunca entran al train)
H3_HOLDOUT = [
    "¿Cómo define el DNP la cobertura de acueducto?", "¿Cuál es el IPM más reciente de Santander?", "¿Quién es el dueño de la plataforma?",
    "¿Cuántos usuarios tiene la plataforma?", "¿Qué peso tiene el hacinamiento en el déficit cualitativo?", "¿Cómo se calcula el IPM de las ciudades capitales?",
    "¿Qué pasó con el IPM después de 2012?", "¿Cómo se proyecta la tenencia informal?", "¿La plataforma tiene una aplicación móvil?",
    "¿Qué método estadístico estima la fiabilidad de la densidad?",
]

# Conceptos generales de politica publica SIN documentos (H6): (concepto, preguntas, respuesta en 1-2 frases, SIN cifras). Las preguntas no
# usan vocabulario del dominio del enrutador (score, ipm, pobreza, deficit, censo...), para que no consulten el RAG.
CONCEPTOS = [
    ("hacinamiento", ["¿Qué es el hacinamiento?", "¿Qué significa que una vivienda tenga hacinamiento?", "Explícame el hacinamiento en una vivienda."],
     "El hacinamiento es la situación en la que demasiadas personas comparten una vivienda o un dormitorio para el espacio disponible. Afecta la salud, la privacidad y la convivencia de quienes la habitan."),
    ("focalización", ["¿Qué es la focalización de subsidios?", "¿Qué significa focalizar el gasto público?", "Explícame qué es focalizar un subsidio."],
     "La focalización consiste en dirigir los recursos y subsidios públicos a la población que más los necesita, según criterios definidos de antemano. Busca que la ayuda llegue a quienes tienen mayores carencias."),
    ("política pública", ["¿Qué es una política pública?", "¿Qué se entiende por política pública?", "Explícame qué es una política pública."],
     "Una política pública es el conjunto de decisiones y acciones con las que el Estado busca resolver un problema de interés colectivo. Incluye objetivos, instrumentos y recursos definidos."),
    ("vivienda de interés social", ["¿Qué es la vivienda de interés social?", "¿Qué significa vivienda de interés social?", "Explícame qué es una vivienda de interés social."],
     "La vivienda de interés social está dirigida a hogares de menores ingresos y su precio tiene un tope definido por la normativa. Su fin es facilitar el acceso a una vivienda digna."),
    ("subsidio de vivienda", ["¿Qué es un subsidio familiar de vivienda?", "¿Para qué sirve un subsidio de vivienda?", "Explícame cómo funciona un subsidio de vivienda."],
     "Un subsidio de vivienda es un aporte del Estado que ayuda a hogares de menores ingresos a acceder a una vivienda, ya sea para comprarla, construirla o mejorarla. Se otorga cuando el hogar cumple las condiciones establecidas."),
    ("servicios públicos domiciliarios", ["¿Qué son los servicios públicos domiciliarios?", "¿Qué se considera un servicio público domiciliario?", "Explícame qué son los servicios públicos de una vivienda."],
     "Son los servicios básicos que llegan a las viviendas, como el agua potable, el alcantarillado, el aseo, la energía y el gas. Son fundamentales para la salud y la calidad de vida."),
    ("saneamiento básico", ["¿Qué es el saneamiento básico?", "¿Qué significa saneamiento básico en una comunidad?", "Explícame qué abarca el saneamiento básico."],
     "El saneamiento básico se refiere a contar con sistemas seguros para manejar las aguas residuales y los desechos. Ayuda a prevenir enfermedades y a proteger el ambiente."),
    ("equidad territorial", ["¿Qué es la equidad territorial?", "¿Qué significa equidad territorial?", "Explícame qué busca la equidad territorial."],
     "La equidad territorial busca que los habitantes de todas las regiones tengan oportunidades y acceso a servicios comparables, sin importar dónde vivan."),
    ("ordenamiento territorial", ["¿Qué es el ordenamiento territorial?", "¿Qué significa ordenar el territorio de un municipio?", "Explícame para qué sirve el ordenamiento territorial."],
     "El ordenamiento territorial es el conjunto de decisiones con las que se define cómo se usa y se ocupa el suelo de un municipio o una región. Orienta dónde se construye, dónde se protege y dónde se desarrollan actividades."),
    ("segregación socioespacial", ["¿Qué es la segregación socioespacial?", "¿Qué significa segregación en una ciudad?", "Explícame qué es la segregación socioespacial."],
     "La segregación socioespacial es la separación de grupos sociales en zonas distintas de una ciudad. Hace que unos barrios concentren ventajas y otros acumulen carencias."),
    ("coeficiente de Gini", ["¿Qué es el coeficiente de Gini?", "¿Qué mide el índice de Gini?", "Explícame el coeficiente de Gini."],
     "El coeficiente de Gini mide la desigualdad en la distribución de un recurso, como el ingreso. Va de cero, que es igualdad total, a uno, que es la máxima desigualdad."),
    ("desarrollo humano", ["¿Qué es el desarrollo humano?", "¿Qué mide el índice de desarrollo humano?", "Explícame qué es el desarrollo humano."],
     "El desarrollo humano es el proceso de ampliar las oportunidades de las personas. Su índice combina salud, educación e ingresos para valorar el bienestar de una población."),
    ("vivienda adecuada", ["¿Qué es una vivienda adecuada?", "¿Qué hace que una vivienda sea adecuada?", "Explícame qué significa vivienda digna."],
     "Una vivienda adecuada ofrece seguridad en la tenencia, servicios, habitabilidad, accesibilidad, ubicación y adecuación cultural. No basta con un techo: debe permitir vivir con dignidad."),
    ("asentamiento informal", ["¿Qué es un asentamiento informal?", "¿Qué significa asentamiento informal?", "Explícame qué es un barrio informal."],
     "Un asentamiento informal es un conjunto de viviendas construidas sin cumplir los requisitos legales de propiedad o urbanización. Suele carecer de servicios y de seguridad jurídica."),
    ("mejoramiento de vivienda", ["¿Qué es el mejoramiento de vivienda?", "¿En qué consiste mejorar una vivienda?", "Explícame qué es un programa de mejoramiento de vivienda."],
     "El mejoramiento de vivienda reúne las obras que corrigen carencias de una casa que ya existe, como los pisos, los muros, la cocina o el baño. Busca que la vivienda sea más segura y habitable sin construir una nueva."),
    ("calidad de vida", ["¿Qué es la calidad de vida?", "¿Qué se entiende por calidad de vida de una población?", "Explícame qué significa calidad de vida."],
     "La calidad de vida es el nivel de bienestar de las personas, que depende de factores como la salud, la educación, la vivienda, los servicios y el entorno."),
    ("brecha territorial", ["¿Qué es una brecha territorial?", "¿Qué significa brecha entre regiones?", "Explícame qué es una brecha entre municipios."],
     "Una brecha territorial es la diferencia en el acceso a bienes y servicios entre regiones o municipios. Medirla ayuda a decidir hacia dónde dirigir las inversiones."),
    ("indicador social", ["¿Qué es un indicador social?", "¿Para qué sirve un indicador social?", "Explícame qué es un indicador en política pública."],
     "Un indicador social es una medida que resume una condición de la población, como la educación o el acceso a servicios. Permite comparar lugares y seguir cambios en el tiempo."),
    ("acceso a servicios", ["¿Qué significa tener acceso a servicios básicos?", "¿Qué es el acceso a servicios básicos?", "Explícame qué quiere decir acceso a servicios."],
     "Tener acceso a servicios básicos significa que las personas pueden usar de forma regular servicios como agua, saneamiento, energía y salud. El acceso depende de que existan, lleguen y sean asequibles."),
    ("habitabilidad", ["¿Qué es la habitabilidad de una vivienda?", "¿Qué significa que una vivienda sea habitable?", "Explícame la habitabilidad."],
     "La habitabilidad es la condición de una vivienda que protege a sus ocupantes del frío, la humedad, el calor y otros riesgos. Incluye espacio suficiente y una estructura segura."),
    ("tenencia segura", ["¿Qué es la seguridad jurídica de la vivienda?", "¿Qué significa tener título de propiedad de una vivienda?", "Explícame la seguridad de la tenencia de una casa."],
     "La seguridad en la tenencia es la protección legal que tiene un hogar para vivir en su vivienda sin temor a ser desalojado. Puede darse por propiedad, arriendo u otras formas reconocidas."),
    ("inversión social", ["¿Qué es la inversión social?", "¿Qué significa invertir en lo social?", "Explícame qué es el gasto social."],
     "La inversión social es el gasto público destinado a mejorar las condiciones de vida de la población, por ejemplo en educación, salud, vivienda y servicios."),
]

# Preguntas H6 del HOLDOUT (no entran al train): conceptos distintos de los de arriba o formulaciones distintas.
H6_HOLDOUT = []

# Apertura / cierre neutros para las respuestas de H (conectores sin contenido): {e} = el extracto o la lista ya armados
H_APERTURAS = [
    "Esto es lo que explican los documentos de la plataforma. {e}",
    "Los documentos lo explican así. {e}",
    "De acuerdo con los documentos, esto es lo que se sabe. {e}",
    "{e} Eso es lo que dicen los documentos.",
    "Te cuento lo que dicen los documentos. {e}",
    "Sobre eso, los documentos dicen lo siguiente. {e}",
    "Así lo describen los documentos de la plataforma. {e}",
    "Esto es lo que encuentro en los documentos. {e}",
    "Los documentos de la plataforma señalan lo siguiente. {e}",
    "{e} Esa es la explicación que traen los documentos.",
    "En los documentos de la plataforma se indica esto. {e}",
    "Claro. Esto es lo que hay en los documentos. {e}",
    "Esto dicen los documentos al respecto. {e}",
    "Con base en los documentos de la plataforma, esto es lo que puedo decirte. {e}",
]
# Cuando el extracto es una LISTA el texto de la lista ya trae su introduccion: se antepone solo una frase corta
H_APERTURAS_LISTA = [
    "Esto es lo que explican los documentos de la plataforma.", "Los documentos lo explican así.", "Te cuento lo que dicen los documentos.",
    "Así lo describen los documentos de la plataforma.", "Esto es lo que encuentro en los documentos.", "Esto dicen los documentos al respecto.",
    "Los documentos de la plataforma señalan lo siguiente.", "Claro. Esto es lo que hay en los documentos.",
]

# Correccion de una premisa falsa (H5): {e} = el extracto que la desmiente
H5_APERTURAS_LISTA = [
    "No es así.", "Esa premisa no es correcta.", "Los documentos dicen otra cosa.", "No coincide con lo que indican los documentos.",
    "Hay que corregir ese dato.", "No exactamente.",
]

H5_APERTURAS = [
    "No exactamente. {e}",
    "Eso no es así según los documentos. {e}",
    "Hay que corregir ese dato. {e}",
    "No es lo que dicen los documentos. {e}",
    "Ojo con ese punto, porque no coincide con los documentos. {e}",
    "Los documentos dicen otra cosa. {e}",
    "Esa premisa no es correcta. {e}",
    "{e} Por eso lo que planteas no coincide con los documentos.",
    "Los documentos indican lo contrario de lo que planteas. {e}",
    "Conviene precisarlo. {e}",
    "No coincide con lo que indican los documentos. {e}",
    "Según los documentos, la respuesta es distinta. {e}",
]

# Abstencion (H3): no hay documento que responda
H3_RESPUESTAS = [
    "No tengo esa información en mis documentos.",
    "Los documentos que tengo no responden esa pregunta, y prefiero no inventar una respuesta.",
    "No cuento con esa información en mis documentos, así que no puedo responderla.",
    "Esa información no aparece en mis documentos. No quiero darte una respuesta sin sustento.",
    "En mis documentos no hay nada que responda eso, por lo que no lo voy a inventar.",
    "No encuentro esa información en los documentos de la plataforma.",
    "Mis documentos no cubren ese tema, y no voy a suponer una respuesta.",
    "No tengo documentos que expliquen eso; prefiero decírtelo antes que inventar.",
    "Eso no está en mis documentos, así que no puedo darte una respuesta fiable.",
    "No dispongo de esa información en los documentos de la plataforma.",
    "No puedo responder eso: los documentos que tengo no lo tratan.",
    "Lo que preguntas no está en mis documentos, y no quiero responder de memoria.",
]
# Sugerencia opcional tras la abstencion (temas que SI cubren los documentos; sin cifras ni afirmaciones nuevas)
H3_SUGERENCIAS = [
    " Sí puedo explicarte cómo se calcula el Score de privación, qué es el IPM o de dónde salen los datos de la plataforma.",
    " Puedo ayudarte con preguntas sobre el Score de privación, el IPM, los datos reales y las proyecciones.",
    " Si quieres, te explico cómo se calcula el Score, qué significan los colores del mapa o cómo se distinguen los datos reales de las proyecciones.",
    " Puedo contarte sobre la metodología del Score, el IPM y las fuentes de los datos.",
    "",
    "",
    "",
]

# Aperturas de las respuestas H6 (concepto general, sin documentos): {e} = la explicacion
H6_APERTURAS = [
    "En términos generales, esto es lo que significa. {e}",
    "Te lo explico de forma general. {e}",
    "Como concepto general, funciona así. {e}",
    "Claro, en pocas palabras. {e}",
    "Es un concepto general de política pública. {e}",
    "{e} Es una explicación general, no específica de la plataforma.",
    "Te doy una explicación general. {e}",
    "De forma general, esto es lo que se entiende. {e}",
    "En política pública, se entiende así. {e}",
    "{e} Eso es lo que significa en términos generales.",
]


from .h_datos_extra import Q_EXTRA  # noqa: E402

for _i in INTENCIONES:
    _i["q"] = _i["q"] + [x for x in Q_EXTRA.get(_i["id"], []) if x not in _i["q"]]

from . import h_datos_ajustes as _aj  # noqa: E402

for _i in INTENCIONES:
    _i["qh"] = _aj.QH.get(_i["id"])
PREMISAS = _aj.PREMISAS


from . import h_datos_temas as _tm  # noqa: E402

for _i in INTENCIONES:
    for _t in _tm.TEMAS.get(_i["id"], []):
        for _m in _tm.MARCOS:
            _q = _m.format(t=_t)
            if _q not in _i["q"]:
                _i["q"].append(_q)
    _i["qh2"] = _tm.QH2.get(_i["id"])
_extra = dict(_tm.PREMISAS_EXTRA)
PREMISAS = [(iid, qs + _extra.get(iid, []), c) for iid, qs, c in PREMISAS]


_H6_EXTRA = ["Háblame de {c}.", "¿Puedes explicarme {c}?"]
CONCEPTOS = [(c, qs + [m.format(c=c) for m in _H6_EXTRA], r) for c, qs, r in CONCEPTOS]
