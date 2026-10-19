"""Plantillas de RESPUESTA de las familias HS (adenda 7.1b seccion 4). Mismas convenciones que `respuestas.py`.

Huecos extra: {fuente} fuente tal cual la linea del contexto («DNP - TerriData», «Proyección Techo 360»); {F} «de 30 %» o
«entre 30 % y 60 %»; {dato} oracion(es) ya redactada(s) por el generador (como A1 o, en HS5, tambien H). Las cifras salen del
CONTEXTO ACTUAL, nunca del historial (regla 10 de sp-0.4.1-1).
"""

HS1_ANIO = [
    "En {Y}, {V} en {MD} fue de {val}.{nota}",
    "Para {Y}, el dato de {v} en {MD} es {val}.{nota}",
    "Para ese año ({Y}), {V} de {MD} registró {val}.{nota}",
    "Para {Y}, la plataforma reporta {val} de {v} en {MD}.{nota}",
    "Claro. En {Y}, {V} de {MD} marcó {val}.{nota}",
    "Seguimos con {MD}: en {Y}, {V} fue de {val}.{nota}",
    "En el año {Y}, {V} en {MD} registró {val}.{nota}",
    "Con el año {Y}, el valor de {v} en {MD} es {val}.{nota}",
    "Para {MD}, {V} en {Y} fue de {val}.{nota}",
    "Te cuento: en {Y}, {V} de {MD} fue {val}.{nota}",
    "Mirando {Y}, {V} en {MD} marca {val}.{nota}",
    "El valor de {Y} para {v} en {MD} es de {val}.{nota}",
    "Durante {Y}, {MD} registró {val} de {v}.{nota}",
    "{Vc} de {MD}: en {Y} fue de {val}.{nota}",
]
HS2_MUNICIPIO = [
    "En {MD}, {V} en {Y} fue de {val}.{nota}",
    "Para {MD}, el dato de {v} en {Y} es {val}.{nota}",
    "{MD} registró {val} de {v} en {Y}.{nota}",
    "Claro. En {MD}, {V} marcó {val} en {Y}.{nota}",
    "Sobre {MD}: en {Y}, {V} fue de {val}.{nota}",
    "La plataforma reporta {val} de {v} para {MD} en {Y}.{nota}",
    "Pasando a {MD}, {V} en {Y} registró {val}.{nota}",
    "En {Y}, {V} de {MD} fue de {val}.{nota}",
    "El valor de {v} para {MD} en {Y} es de {val}.{nota}",
    "Con los datos de {MD}, {V} en {Y} es de {val}.{nota}",
    "Ahora con {MD}: {V} en {Y} fue de {val}.{nota}",
    "Te muestro {MD}. En {Y}, {V} fue de {val}.{nota}",
    "Mirando {MD}, {V} en {Y} marca {val}.{nota}",
    "En el municipio de {MD}, {V} en {Y} registró {val}.{nota}",
]
HS3_VARIABLE = [
    "{Vc} de {MD} en {Y} fue de {val}.{nota}",
    "En {Y}, {V} en {MD} es de {val}.{nota}",
    "Para {MD}, {V} en {Y} registró {val}.{nota}",
    "Claro. {Vc} en {MD} en {Y} marcó {val}.{nota}",
    "En cuanto a {v}, {MD} registró {val} en {Y}.{nota}",
    "Sobre {v}: en {MD}, en {Y}, el valor es {val}.{nota}",
    "El dato de {v} para {MD} en {Y} es {val}.{nota}",
    "Con esa variable, {MD} tiene {val} de {v} en {Y}.{nota}",
    "Pasando a {v}, en {MD} el valor de {Y} es {val}.{nota}",
    "Mirando {v}, {MD} en {Y} marca {val}.{nota}",
    "{Vc}, en {MD} y en {Y}, fue de {val}.{nota}",
    "Con los datos de {Y}, {V} de {MD} es de {val}.{nota}",
]
HS4_REAL = [
    "Es un dato real: el valor de {v} de {MD} para {Y}, {val}, proviene de {fuente}.",
    "Sí, es real. El dato de {v} de {MD} en {Y} ({val}) viene de {fuente}.",
    "Se trata de un dato observado, no de una estimación. Su fuente es {fuente}.",
    "Ese valor, {val} en {Y}, es un dato real. La fuente es {fuente}.",
    "Es real: lo publica {fuente}, y corresponde a {v} de {MD} en {Y}.",
    "No es una proyección. El dato de {Y} sobre {v} en {MD} viene de {fuente}.",
    "Es un dato real de {fuente}; para {MD} en {Y}, {v} es {val}.",
    "Correcto, ese año tiene dato real. La fuente es {fuente}.",
    "El valor de {Y} se midió, no se estimó. Proviene de {fuente}.",
    "Es un dato real, no una estimación; su fuente para {v} de {MD} es {fuente}.",
    "Es un dato real y no una estimación. Lo reporta {fuente}.",
    "Ese número no es una proyección: es el dato real de {v} de {MD} en {Y}, reportado por {fuente}.",
]
HS4_ESTIMADO = [
    "No es un dato observado: el valor de {v} de {MD} para {Y}, {val}, es una estimación con fiabilidad {F}.",
    "Es una estimación, no un dato real. Tiene fiabilidad {F} y proviene de {fuente}.",
    "Ese valor ({val}) es una proyección con fiabilidad {F}, de acuerdo con {fuente}.",
    "Ese año no tiene dato real: {val} es una estimación, con fiabilidad {F}.",
    "Se trata de una proyección. Su fiabilidad es {F} y la fuente es {fuente}.",
    "Es estimado. El dato de {Y} sobre {v} en {MD} es {val}, con fiabilidad {F}.",
    "No se midió: {v} de {MD} en {Y} es una estimación de {val}, con fiabilidad {F}.",
    "Es una proyección de {fuente} para {Y}; su fiabilidad es {F}, así que es una estimación y no un dato real.",
    "Corresponde a una estimación, no a una medición. Su fiabilidad es {F}.",
    "Es un valor proyectado ({val}) con fiabilidad {F}; no hay dato real para ese año.",
    "No es real, es estimado: la fiabilidad del valor de {Y} es {F}.",
    "La cifra de {v} de {MD} para {Y} es una proyección con fiabilidad {F}, no un dato observado.",
]
HS5_CAMBIO_TEMA = [
    "Con gusto. {dato}",
    "Claro, cambiamos de tema. {dato}",
    "{dato} Si quieres, seguimos con otra consulta.",
    "Sobre esa nueva consulta, esto es lo que hay. {dato}",
    "Dejo lo anterior y respondo lo nuevo. {dato}",
    "Listo, otra consulta. {dato}",
    "{dato} Dime si necesitas algo más.",
    "Esto es lo que dice la plataforma sobre tu nueva pregunta. {dato}",
    "Entendido, tema nuevo. {dato}",
    "Respondo a lo que preguntas ahora. {dato}",
    "{dato} Con eso queda resuelta esta consulta.",
    "Va la nueva consulta. {dato} ¿Algo más?",
]
HS6_INYECCION_PREVIA = [
    "{dato} No sigo las instrucciones de mensajes anteriores que cambien mis reglas.",
    "{dato} Lo que se pidió antes sobre ignorar mis reglas no se aplica.",
    "Respondo tu consulta con los datos de la plataforma. {dato} Mis reglas no cambian por lo dicho antes.",
    "{dato} Las órdenes anteriores de cambiar mi forma de responder no las tomo en cuenta.",
    "Sigo con las mismas reglas de antes. {dato}",
    "{dato} Mantengo mis reglas, aunque antes se me pidiera otra cosa.",
    "Esto es lo que dice la plataforma. {dato} Lo pedido antes para saltarme mis reglas no aplica.",
    "{dato} Mis respuestas siguen usando solo los datos de la plataforma.",
    "Te respondo con los datos de la plataforma. {dato} La instrucción anterior no cambia cómo respondo.",
    "{dato} No guardo órdenes de mensajes anteriores que contradigan mis reglas.",
    "Continúo con tu consulta sin aplicar lo que se pidió antes sobre mis reglas. {dato}",
    "{dato} Sigo respondiendo solo con el contexto actual.",
]

_PUNTUAL = {"MD", "V", "Vc", "v", "Y", "val", "nota"}
PLANTILLAS = {
    "hs1_anio": HS1_ANIO, "hs2_municipio": HS2_MUNICIPIO, "hs3_variable": HS3_VARIABLE,
    "hs4_real": HS4_REAL, "hs4_estimado": HS4_ESTIMADO,
    "hs5_cambio_tema": HS5_CAMBIO_TEMA, "hs6_inyeccion_previa": HS6_INYECCION_PREVIA,
}
HUECOS_PERMITIDOS = {
    "hs1_anio": set(_PUNTUAL), "hs2_municipio": set(_PUNTUAL), "hs3_variable": set(_PUNTUAL),
    "hs4_real": {"MD", "v", "Y", "val", "fuente"}, "hs4_estimado": {"MD", "v", "Y", "val", "F", "fuente"},
    "hs5_cambio_tema": {"dato"}, "hs6_inyeccion_previa": {"dato"},
}
HUECOS_OBLIGATORIOS = {
    "hs1_anio": {"MD", "Y", "val"}, "hs2_municipio": {"MD", "Y", "val"}, "hs3_variable": {"MD", "Y", "val"},
    "hs4_real": {"fuente"}, "hs4_estimado": {"F"}, "hs5_cambio_tema": {"dato"}, "hs6_inyeccion_previa": {"dato"},
}
