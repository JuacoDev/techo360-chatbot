"""Plantillas de RESPUESTA de 0.4.1, G1-G6 y F+ (paso 7.3, Fase A). H se escribe en la Fase B con el corpus final.

Las plantillas son texto con huecos; el generador inserta las cifras (nunca un LLM) y, en G1/G6, agrega el bloque con
`bloque.armar_respuesta`. Ninguna plantilla trae digitos. Huecos (el generador los llena desde el CONTEXTO ya renderizado):

  MD     «Municipio (Departamento)» tal cual la linea del contexto · MDs  lista «A (X), B (Y) y C (Z)»
  V      variable con articulo y minuscula («la cobertura de acueducto») · Vc  igual, con mayuscula inicial · v  sin articulo
  Vde    «de la cobertura de acueducto» / «del déficit habitacional cuantitativo» (la contraccion ya hecha: nunca «de {V}»)
  Vs_txt variables con articulo unidas por comas y «y» · Y, Y1, Y2  anios · V1, V2  valores de Y1 / Y2 con su formato real
  val    un valor · tendencia  «subió» | «bajó» | «se mantuvo» (el generador excluye las plantillas con este hueco si falta
         una de las dos lecturas) · serie  «94,2 % en 2019, 94,6 % en 2020 y 95,0 % en 2021» (todos los valores de las lineas)
  lista  «A (X) con 94,2 % y B (Y) con 91,0 %» · lista_vars  «la cobertura de acueducto, con 94,2 %, y la de alcantarillado, con 88,1 %»
  top, topv, bot, botv   extremos del ranking entre los municipios del contexto (nunca de otros)
  nota   cadena vacia o « Texto.» (con espacio inicial y mayuscula): ver NOTAS_SERIE / NOTAS_PUNTUAL
  motivo literal de la linea «Sin dato…» · alterno  cadena vacia o « Texto.» (ver ALTERNOS) · t  tipo no soportado
  dato   oracion(es) ya redactada(s) que responde(n) lo legitimo, terminada(s) en punto (la arma el generador como A1/A3)

Convenciones para el lint de 5.2b D1: ninguna oracion empieza con minuscula tras «. »; ningun hueco en minuscula abre oracion
(se usa Vc); nunca mayuscula tras «: ».
"""

# ------------------------------------------------------------------------------------- notas de proyeccion (hueco {nota})
# Fiabilidad tal cual esta en cada linea (regla 3 de fase5-1): {F} = «de 30 %» o «entre 30 % y 60 %». Nunca se promedia.
NOTAS_SERIE = [
    " Los datos desde {Yp} son estimaciones, con fiabilidad {F}.",
    " Desde {Yp} los valores son proyecciones, con fiabilidad {F}, no datos observados.",
    " A partir de {Yp} se trata de estimaciones con fiabilidad {F}.",
    " Ojo: desde {Yp} los valores son estimaciones, con fiabilidad {F}.",
    " Los años desde {Yp} son proyección y su fiabilidad es {F}.",
    " Lo posterior a {Yp} es una estimación con fiabilidad {F}, no un dato real.",
    " Desde {Yp} se muestran estimaciones, con fiabilidad {F}.",
    " Aclaro que los valores desde {Yp} son proyectados, con fiabilidad {F}.",
]
NOTAS_PUNTUAL = [
    " Es una estimación con fiabilidad {F}, no un dato observado.",
    " Se trata de una proyección con fiabilidad {F}.",
    " Este valor es una estimación, con fiabilidad {F}.",
    " Ojo: es un valor proyectado, con fiabilidad {F}.",
    " Es una proyección y su fiabilidad es {F}, no un dato real.",
    " Aclaro que se trata de una estimación con fiabilidad {F}.",
]
# Varios elementos y TODOS estimaciones (concordancia en plural)
NOTAS_VARIOS = [
    " Todos son valores proyectados, con fiabilidad {F}.",
    " Se trata de estimaciones, con fiabilidad {F}.",
    " Ninguno es un dato observado: son estimaciones con fiabilidad {F}.",
    " Aclaro que son proyecciones, con fiabilidad {F}.",
    " Estos valores son estimaciones, con fiabilidad {F}.",
    " Ojo: son valores proyectados, con fiabilidad {F}, y no datos reales.",
]
# Cuando solo ALGUNOS elementos son estimaciones ({E} = «la cobertura de acueducto y el déficit habitacional cuantitativo»; {F} como arriba)
NOTAS_MIXTA = [
    " Lo estimado ({E}) tiene fiabilidad {F}; el resto es dato real.",
    " Entre los datos, {E} corresponde a estimaciones con fiabilidad {F}.",
    " Las estimaciones corresponden a {E}, con fiabilidad {F}.",
    " Ten en cuenta que {E} corresponde a estimaciones con fiabilidad {F}; lo demás es dato real.",
    " Solo lo de {E} es estimado, con fiabilidad {F}.",
    " Lo que corresponde a {E} es una estimación con fiabilidad {F}; lo demás es dato real.",
]
# Alternativas que G3 puede ofrecer cuando el contexto trae algun dato disponible (hueco {alterno}); {Ya}, {val}.
ALTERNOS = [
    " Lo que sí tengo es el dato de {v} de {MD} para {Ya}, que es {val}.",
    " Para {Ya} sí cuento con el dato de {v} de {MD}: es {val}.",
    " Como alternativa, el dato disponible de {v} de {MD} es {val} en {Ya}.",
    " Puedo darte el valor de {Ya}, que es {val}, aunque no alcanza para una gráfica.",
    " El único dato que tengo es el de {Ya}, que es {val}.",
    " Sí dispongo del dato de {Ya}: {val}.",
]

# ======================================================================================= G1 pide grafica y hay datos
G1_LINEAS_INDIVIDUAL = [
    "En {MD}, {V} pasó de {V1} en {Y1} a {V2} en {Y2}.{nota} La gráfica se muestra debajo.",
    "Aquí está la evolución {Vde} en {MD}: {V1} en {Y1} y {V2} en {Y2}.{nota}",
    "{Vc} en {MD} registró {V1} en {Y1} y {V2} en {Y2}.{nota} La gráfica muestra todos los años disponibles.",
    "Te muestro la serie de {v} de {MD}. Va de {V1} en {Y1} a {V2} en {Y2}.{nota}",
    "Claro. Entre {Y1} y {Y2}, {V} en {MD} {tendencia}, de {V1} a {V2}.{nota} La gráfica está debajo.",
    "Gráfica lista. {Vc} de {MD} va de {V1} en {Y1} a {V2} en {Y2}.{nota}",
    "Con gusto. Entre {Y1} y {Y2}, {V} de {MD} pasó de {V1} a {V2}.{nota}",
    "Estos son los extremos de la serie de {v} en {MD}: {V1} en {Y1} y {V2} en {Y2}.{nota} Debajo está la gráfica.",
    "La serie de {v} de {MD} comienza en {V1} ({Y1}) y llega a {V2} ({Y2}).{nota} La gráfica aparece debajo.",
    "Mira cómo cambió {V} en {MD}: de {V1} en {Y1} a {V2} en {Y2}.{nota}",
    "Desde {Y1} hasta {Y2}, {V} en {MD} pasó de {V1} a {V2}.{nota} Te dejo la gráfica.",
    "{MD} tuvo {V1} de {v} en {Y1} y {V2} en {Y2}.{nota} La gráfica de líneas está debajo.",
    "Listo, aquí tienes la evolución anual de {v} en {MD}, que pasó de {V1} en {Y1} a {V2} en {Y2}.{nota}",
    "Sobre {MD}: {V} {tendencia} entre {Y1} y {Y2}, de {V1} a {V2}.{nota} La gráfica se muestra debajo.",
    "Preparé la gráfica de líneas de {v} para {MD}. Muestra {V1} en {Y1} y {V2} en {Y2}.{nota}",
    "Esta es la tendencia de {v} en {MD} entre {Y1} y {Y2}: de {V1} a {V2}.{nota}",
]

G1_LINEAS_COMPARAR = [
    "Te muestro la evolución de {v} en {MDs}. En {Y2}, el último año de la serie, los valores son {lista}.{nota} La gráfica está debajo.",
    "Aquí tienes la comparación de {v} entre {MDs} de {Y1} a {Y2}. Al final de la serie, los valores son {lista}.{nota}",
    "Comparo {V} en {MDs}: en {Y2}, los valores son {lista}.{nota} La gráfica de líneas se muestra debajo.",
    "Listo. En {Y2}, los valores son {lista}.{nota} La gráfica muestra cómo evolucionó {v} entre {Y1} y {Y2} en {MDs}.",
    "La gráfica de líneas compara {v} en {MDs}. Para {Y2}, los valores son {lista}.{nota}",
    "Estas son las curvas de {v} para {MDs}, desde {Y1} hasta {Y2}. En el último año, los valores son {lista}.{nota}",
    "Con gusto: la gráfica sigue {V} en {MDs} entre {Y1} y {Y2}. En {Y2}, los valores son {lista}.{nota}",
    "Mira la evolución conjunta de {v} en {MDs}. Al cierre de la serie ({Y2}), los valores son {lista}.{nota}",
    "{Vc} en {MDs} se compara en la gráfica de abajo. En {Y2}, los valores son {lista}.{nota}",
    "Preparé una gráfica de líneas con una curva por municipio ({MDs}) para {v}. En {Y2}, los valores son {lista}.{nota}",
    "Entre {Y1} y {Y2}, la gráfica sigue a {MDs} en {v}. El último dato de la serie es {lista}.{nota}",
    "Aquí va la comparación en el tiempo de {v}. Para {Y2}, los valores son {lista}.{nota} Incluí a {MDs} en la gráfica.",
    "Te dejo las líneas de {v} de {MDs}. En {Y2}, los valores son {lista}.{nota}",
    "Mira cómo se mueve {v} en {MDs} entre {Y1} y {Y2}. En {Y2}, los valores son {lista}.{nota}",
]

G1_BARRAS_RANKING = [
    "En {Y}, {top} tiene el valor más alto de {v} entre {MDs}, con {topv}; {bot} tiene el más bajo, con {botv}.{nota} El ranking en barras está debajo.",
    "Este es el ranking de {v} en {Y}. {top} encabeza con {topv} y {bot} cierra con {botv}.{nota} Te lo muestro en barras.",
    "Ordené a {MDs} según {v} en {Y}. El más alto es {top}, con {topv}, y el más bajo es {bot}, con {botv}.{nota}",
    "Para {Y}, el municipio con mayor {v} entre los consultados es {top}, con {topv}, y el de menor valor es {bot}, con {botv}.{nota} La gráfica de barras está debajo.",
    "Aquí está la comparación en barras de {v} en {Y}. {top} registra {topv}, el valor más alto, y {bot} registra {botv}, el más bajo.{nota}",
    "Listo, el ranking de {v} para {MDs} en {Y} aparece debajo. Va de {topv} en {top} a {botv} en {bot}.{nota}",
    "En el ranking de {v} de {Y}, {top} queda primero con {topv} y {bot} queda último con {botv}.{nota}",
    "Con gusto. Las barras ordenan {MDs} por {v} en {Y}; el máximo es {topv} en {top} y el mínimo, {botv} en {bot}.{nota}",
    "Te muestro el ranking en barras. Para {Y}, {v} va desde {botv} en {bot} hasta {topv} en {top}.{nota}",
    "Armé el ranking de {v} en {Y} con {MDs}. El primero es {top}, con {topv}, y el último, {bot}, con {botv}.{nota}",
    "Mira cómo se ordenan {MDs} en {v} para {Y}. {top} lidera con {topv}, mientras que {bot} registra {botv}.{nota} La gráfica está debajo.",
    "Gráfica de barras lista. En {Y}, el extremo alto de {v} es {top}, con {topv}, y el bajo es {bot}, con {botv}.{nota}",
    "Entre {MDs}, {top} tiene el valor más alto de {v} en {Y}, con {topv}; en el otro extremo está {bot}, con {botv}.{nota} Debajo ves el ranking.",
    "Aquí tienes el ranking de {v} de {Y}. El orden va de {top}, con {topv}, a {bot}, con {botv}.{nota}",
]

G1_BARRAS_AGRUPADAS_IND = [
    "En {Y}, en {MD}, se registran {lista_vars}.{nota} Las barras agrupadas están debajo.",
    "Aquí tienes {Vs_txt} de {MD} en {Y} en barras agrupadas. Los valores son estos: {lista_vars}.{nota}",
    "Te muestro las barras agrupadas de {MD} para {Y}. Allí se ven {lista_vars}.{nota}",
    "Listo. Para {Y}, en {MD}, se registran {lista_vars}.{nota} La gráfica se muestra debajo.",
    "Comparo {Vs_txt} de {MD} en {Y}. En ese año se registran {lista_vars}.{nota}",
    "La gráfica agrupa {Vs_txt} de {MD}. En {Y}, se registran {lista_vars}.{nota}",
    "Con gusto. En {MD}, durante {Y}, los datos muestran {lista_vars}.{nota} Las barras están debajo.",
    "Preparé las barras agrupadas de {MD} con {Vs_txt}. Para {Y}, se registran {lista_vars}.{nota}",
    "Mira cómo están {Vs_txt} en {MD} en {Y}: {lista_vars}.{nota}",
    "Estas son las barras de {MD} para {Y}. Los datos del contexto indican que se registran {lista_vars}.{nota}",
    "Aquí va el gráfico de barras agrupadas de {MD}. En {Y}, los valores son {lista_vars}.{nota}",
    "Te dejo la comparación de {Vs_txt} en {MD}. Para {Y}, se registran {lista_vars}.{nota}",
]

G1_BARRAS_AGRUPADAS_CMP = [
    "Te muestro en barras agrupadas {Vs_txt} de {MDs} en {Y}. Cada grupo corresponde a un municipio.{nota}",
    "Aquí tienes la comparación de {Vs_txt} entre {MDs} para {Y}. La gráfica agrupa las barras por municipio.{nota}",
    "Listo. La gráfica de barras agrupadas pone lado a lado {Vs_txt} de {MDs} en {Y}.{nota}",
    "Comparo {Vs_txt} de {MDs} en {Y}. Las barras están agrupadas por municipio y se muestran debajo.{nota}",
    "Con gusto. Para {Y}, el gráfico agrupa {Vs_txt} de {MDs}.{nota}",
    "Preparé barras agrupadas con {Vs_txt} de {MDs} para {Y}.{nota} La gráfica está debajo.",
    "Mira cómo se ven {Vs_txt} en {MDs} en {Y}. Los valores salen de los datos de la plataforma.{nota}",
    "La gráfica reúne {Vs_txt} de {MDs} en {Y}, con una barra por variable en cada municipio.{nota}",
    "Aquí va el gráfico de barras agrupadas de {MDs}, con {Vs_txt} en {Y}.{nota}",
    "Te dejo la comparación en barras de {MDs} para {Y}, con {Vs_txt}.{nota} Las cifras salen del contexto.",
    "Estas son las barras agrupadas de {MDs} en {Y}, con una barra por cada variable pedida ({Vs_txt}).{nota}",
    "Armé el gráfico de barras agrupadas con {Vs_txt} de {MDs} en {Y}.{nota} Se muestra debajo.",
]

G1_GAUGE = [
    "En {Y}, {V} de {MD} registra {val}.{nota} El medidor se muestra debajo.",
    "{Vc} de {MD} en {Y} es de {val}.{nota} Te lo muestro en un medidor.",
    "Aquí está el medidor de {v} de {MD}. Para {Y}, el valor es {val}.{nota}",
    "Con gusto. El medidor muestra {val} para {v} en {MD} en {Y}.{nota}",
    "Listo. En {MD}, {V} es de {val} en {Y}.{nota} El gráfico está debajo.",
    "Preparé un medidor con {v} de {MD}. En {Y}, el dato es {val}.{nota}",
    "Mira el medidor de {MD}: en {Y}, {V} registra {val}.{nota}",
    "Te muestro {V} de {MD} en un medidor. Para {Y}, la cifra es {val}.{nota}",
    "Para {Y}, el valor de {v} en {MD} es {val}.{nota} Lo ves en el medidor de abajo.",
    "Este es el gauge de {v} de {MD}. En {Y}, marca {val}.{nota}",
    "El medidor refleja {V} de {MD} en {Y}, que es de {val}.{nota}",
    "Aquí va la gráfica de medidor. {Vc} de {MD} registra {val} en {Y}.{nota}",
    "Gráfica de medidor lista. {MD} tiene {val} de {v} en {Y}.{nota}",
    "Dato para el medidor: en {Y}, {V} de {MD} es de {val}.{nota} Debajo está la gráfica.",
]

# ======================================================================================= G2 dato sin pedir grafica (sin bloque)
G2_SERIE = [
    "En {MD}, {V} registró {serie}.{nota}",
    "Entre {Y1} y {Y2}, {V} en {MD} registró estos datos: {serie}.{nota}",
    "{Vc} en {MD} tuvo {serie}.{nota}",
    "Estos son los datos de {v} de {MD}: {serie}.{nota}",
    "Para {MD}, la serie de {v} de {Y1} a {Y2} es esta: {serie}.{nota}",
    "De {Y1} a {Y2}, {V} en {MD} marcó {serie}.{nota}",
    "Claro. En {MD}, {V} fue de {serie}.{nota}",
    "{MD} reportó {serie} de {v}.{nota}",
    "Así se comportó {V} en {MD}: {serie}.{nota}",
    "Los valores de {v} en {MD} entre {Y1} y {Y2} son {serie}.{nota}",
    "Con los datos de la plataforma, {V} en {MD} fue de {serie}.{nota}",
    "El recorrido de {v} en {MD} fue {serie}.{nota}",
    "Te cuento lo que registra la plataforma para {MD}. {Vc} tuvo {serie}.{nota}",
    "Mirando {Y1} a {Y2}, en {MD} {V} pasó por {serie}.{nota}",
]

G2_COMPARACION = [
    "En {Y}, {V} se ubica así: {lista}.{nota}",
    "Para {Y}, entre {MDs}, estos son los datos de {v}: {lista}.{nota}",
    "Estos son los valores de {v} en {Y}: {lista}.{nota}",
    "Comparando {MDs} en {Y}, {V} muestra estos resultados: {lista}.{nota}",
    "Claro. En {Y}, {V} se registra así: {lista}.{nota}",
    "{Vc} en {Y} se reporta de esta manera: {lista}.{nota}",
    "Los datos de {Y} indican lo siguiente sobre {v}: {lista}.{nota}",
    "Así están en {Y} según {v}: {lista}.{nota}",
    "Con los datos de la plataforma, para {Y} se tiene esto en {v}: {lista}.{nota}",
    "Te comparto lo que reporta la plataforma para {Y}. En {v}: {lista}.{nota}",
    "Mirando solo {Y}, {V} presenta estos valores: {lista}.{nota}",
    "Aquí van los números de {v} para {Y} en {MDs}: {lista}.{nota}",
]

G2_PUNTUAL = [
    "En {Y}, {V} en {MD} es de {val}.{nota}",
    "Para {Y}, {V} de {MD} registra {val}.{nota}",
    "{Vc} de {MD} marca {val} para {Y}.{nota}",
    "El dato de {v} en {MD} para {Y} es {val}.{nota}",
    "Claro. En {MD}, {V} en {Y} registra {val}.{nota}",
    "Según la plataforma, {V} en {MD} en {Y} es de {val}.{nota}",
    "{MD} registra {val} de {v} en {Y}.{nota}",
    "El valor de {v} para {MD} en {Y} es de {val}.{nota}",
    "Con los datos disponibles, {V} de {MD} en {Y} es de {val}.{nota}",
    "Para {MD}, el dato de {Y} sobre {v} es {val}.{nota}",
    "Durante {Y}, {V} en {MD} fue de {val}.{nota}",
    "Consulté {v} de {MD} para {Y}: el valor es {val}.{nota}",
]

# ======================================================================================= G3 pide grafica pero faltan datos (sin bloque)
G3_UN_ANIO = [
    "Una gráfica de líneas necesita al menos dos años, y para {Y} solo tengo un dato: {V} de {MD} registra {val}.{nota} Si quieres ver la evolución, pídeme un rango de años.",
    "Con un solo año no hay evolución que graficar. Para {Y}, {V} en {MD} es de {val}.{nota} Dime un rango de años y armo la gráfica.",
    "No puedo dibujar una serie con un único año. El dato de {v} en {MD} para {Y} es {val}.{nota} ¿Quieres que lo grafique para varios años?",
    "Para graficar la evolución necesito dos años o más. Tengo {v} de {MD} en {Y}: {val}.{nota} Indícame desde cuándo quieres verla.",
    "Esa gráfica no se puede armar con un solo año. Lo que sí te digo es que {V} en {MD} en {Y} es de {val}.{nota} Si amplías el rango, la dibujo.",
    "Una línea necesita al menos dos puntos. Con {Y} solo cuento con un dato: {val} de {v} en {MD}.{nota} Prueba con un rango de años.",
    "Con un solo año no se forma una tendencia. Para {Y}, {V} de {MD} es de {val}.{nota} Pídeme otro rango y te hago la gráfica.",
    "No genero la gráfica con un solo año. El valor de {v} en {MD} en {Y} es {val}.{nota} ¿Probamos con varios años?",
    "Sin al menos dos años no hay serie que mostrar. En {Y}, {V} en {MD} registra {val}.{nota} Dime el rango que prefieres.",
    "Un solo año no alcanza para una gráfica de evolución. El dato de {Y} sobre {v} en {MD} es {val}.{nota} Si me das más años, la dibujo.",
    "Para esa gráfica faltan puntos: con {Y} solo hay un valor. {Vc} de {MD} es de {val}.{nota} Amplía el rango de años y la preparo.",
    "No puedo trazar una línea con un solo punto. En {Y}, {v} de {MD} fue {val}.{nota} Pide una serie de varios años.",
]

G3_SIN_DATO = [
    "No puedo graficar {v} de {MD} porque {motivo}.{alterno} Puedo ayudarte con otra variable o con otros años de ese municipio.",
    "Esa gráfica no es posible: no hay datos de {v} de {MD} que mostrar, porque {motivo}.{alterno}",
    "Por ahora no tengo con qué dibujar {v} de {MD}, ya que {motivo}.{alterno} Si quieres, probamos con otra variable.",
    "No armo la gráfica de {v} en {MD}: {motivo}.{alterno} Podemos intentar con otros años u otra variable.",
    "No es posible graficar {v} de {MD}, porque {motivo}.{alterno}",
    "Lamento no poder mostrarte esa gráfica de {v} en {MD}, porque {motivo}.{alterno} ¿Probamos con otra variable?",
    "Sin datos no hay gráfica. Para {v} de {MD}, {motivo}.{alterno}",
    "La plataforma no me da datos de {v} para {MD} que permitan graficar: {motivo}.{alterno}",
    "No voy a dibujar una gráfica vacía de {v} en {MD}, porque {motivo}.{alterno} Dime si prefieres otra variable.",
    "Esa serie no se puede graficar. En el caso de {v} de {MD}, {motivo}.{alterno}",
    "No puedo mostrar {v} de {MD} en una gráfica, ya que {motivo}.{alterno} Puedo intentar con otro rango o variable.",
    "Con lo que tengo no se puede graficar {v} de {MD}, porque {motivo}.{alterno}",
]

# ======================================================================================= G4 tipo no soportado (sin bloque)
G4_TIPO_NO_SOPORTADO = [
    "Por ahora no puedo mostrar gráficas de tipo {t}. Sí puedo mostrar líneas para la evolución, barras ordenadas para un ranking, barras agrupadas y un medidor. ¿Quieres alguna de ellas?",
    "Ese tipo de gráfica ({t}) no está disponible en este chat. Puedo hacer líneas, ranking en barras, barras agrupadas o medidor.",
    "No dispongo de gráficas de tipo {t}. Lo que sí puedo dibujar es una evolución en líneas, un ranking en barras, barras agrupadas o un medidor.",
    "Aquí no puedo generar gráficas de tipo {t}. Mis opciones son líneas, barras de ranking, barras agrupadas y medidor; dime cuál prefieres.",
    "Esa gráfica no la puedo hacer. Los tipos disponibles son líneas, barras de ranking, barras agrupadas y medidor, no {t}.",
    "Todavía no puedo mostrar {t} en el chat. Puedo ofrecerte una gráfica de líneas, un ranking en barras, barras agrupadas o un medidor.",
    "Lamento no poder hacer gráficas de tipo {t}. Si te sirve, te muestro una de estas: líneas, ranking en barras, barras agrupadas o medidor.",
    "Ese formato ({t}) queda fuera de lo que puedo mostrar aquí. Sí puedo hacer líneas, barras ordenadas, barras agrupadas o un medidor para {MDs}.",
    "No tengo gráficas de tipo {t}, pero puedo mostrar líneas, ranking en barras, barras agrupadas o un medidor. ¿Cuál te gustaría?",
    "Por limitaciones del chat, no puedo dibujar ese tipo ({t}). Elige entre líneas, ranking en barras, barras agrupadas y medidor.",
    "Eso no lo puedo graficar así. Para {MDs} puedo preparar líneas, barras de ranking, barras agrupadas o un medidor, pero no {t}.",
    "En este chat solo puedo mostrar cuatro tipos de gráfica: líneas, ranking en barras, barras agrupadas y medidor. El tipo {t} no está entre ellos.",
]

# ======================================================================================= G5 sin municipio o sin variable (sin bloque)
G5_SIN_MUNICIPIO = [
    "Para armar la gráfica necesito saber de qué municipio la quieres. Indícame el municipio y, si quieres, la variable y los años.",
    "¿De qué municipio quieres la gráfica? Dime el municipio y la variable, por ejemplo la cobertura de acueducto, y la preparo.",
    "Me falta el municipio para dibujar la gráfica. Dime cuál es y, si lo deseas, qué variable y qué años quieres ver.",
    "Con gusto te hago la gráfica, pero primero necesito el municipio. ¿Cuál quieres consultar?",
    "Antes de graficar necesito el municipio. Puedo mostrar el score de privación, las coberturas, los déficits habitacionales y la densidad poblacional.",
    "No sé aún qué municipio graficar. Cuéntame cuál es y elige una variable para completar la gráfica.",
    "Para hacer esa gráfica necesito al menos un municipio. ¿Sobre cuál quieres que la haga?",
    "Falta un dato clave: el municipio. Dímelo, junto con la variable que te interesa, y te muestro la gráfica.",
    "La gráfica depende del municipio y todavía no me lo has dicho. Indícame uno y, si puedes, la variable.",
    "Necesito precisar la consulta: ¿qué municipio quieres graficar? También me ayuda saber la variable y los años.",
    "Dime primero el municipio. Con eso y una variable, como la densidad poblacional o el score de privación, armo la gráfica.",
    "Todavía no puedo graficar porque no tengo un municipio. ¿Cuál te interesa?",
    "Sin un municipio no hay gráfica posible. ¿Cuál quieres que use?",
    "Para dibujarla me hace falta el municipio. Escríbelo y, si puedes, agrega la variable.",
    "No identifico ningún municipio en tu mensaje. Dime cuál quieres graficar.",
    "Falta saber de qué municipio es la gráfica. ¿Me lo indicas?",
    "Necesito el nombre de un municipio para armar la gráfica. ¿De cuál la quieres?",
    "Puedo hacer la gráfica en cuanto me digas el municipio. ¿Cuál es?",
    "Antes de graficar, dime el municipio. También puedes indicar la variable y los años.",
    "Me falta el municipio: sin él no sé qué datos dibujar. ¿Cuál prefieres?",
]

G5_SIN_VARIABLE = [
    "Tengo a {MDs}, pero me falta saber qué variable quieres graficar. Puedo usar el score de privación, las coberturas de acueducto y alcantarillado, los déficits habitacionales cuantitativo y cualitativo o la densidad poblacional.",
    "Para graficar {MDs} necesito la variable. ¿Cuál prefieres: score de privación, cobertura de acueducto, cobertura de alcantarillado, déficit cuantitativo, déficit cualitativo o densidad poblacional?",
    "Ya tengo el municipio ({MDs}). ¿Qué variable quieres ver en la gráfica? Hay seis disponibles, entre ellas las coberturas y los déficits.",
    "Con gusto. Dime qué variable graficar para {MDs}: el score de privación, las coberturas, los déficits habitacionales o la densidad poblacional.",
    "Me falta la variable para {MDs}. Elige una, como la cobertura de acueducto o el déficit habitacional cuantitativo, y la dibujo.",
    "Antes de hacer la gráfica de {MDs} necesito saber qué variable te interesa. También me sirve el rango de años.",
    "Para {MDs} puedo graficar varias variables, pero no sé cuál quieres. ¿Score de privación, coberturas, déficits o densidad poblacional?",
    "La gráfica de {MDs} necesita una variable. Indícame cuál, por ejemplo la cobertura de alcantarillado o la densidad poblacional.",
    "¿Qué quieres ver de {MDs}? Puedo graficar el score de privación, las coberturas de servicios, los déficits habitacionales o la densidad poblacional.",
    "Tengo el municipio, pero no la variable. Dime cuál graficar para {MDs} y elijo el tipo de gráfica que mejor la muestre.",
    "Falta precisar la variable. Para {MDs} dispongo del score de privación, las dos coberturas, los dos déficits y la densidad poblacional.",
    "Para continuar con {MDs}, dime qué variable quieres en la gráfica. Con eso la preparo enseguida.",
]

# ======================================================================================= G6 valores o codigo en el bloque
# Prefijo de rechazo + cuerpo (se compone con `componer_g6`). El cuerpo es una plantilla G1 de lineas individual.
G6_PREFIJOS_VALORES = [
    "Los valores de la gráfica salen de los datos de la plataforma, no de los que se escriben en la pregunta.",
    "No puedo usar cifras que me des para la gráfica; la dibujo solo con los datos de la plataforma.",
    "Las gráficas se arman únicamente con datos de la plataforma, así que no incluyo los valores que me indicas.",
    "El bloque de la gráfica no lleva valores, y yo solo muestro datos reales de la plataforma.",
    "No tomo valores de la pregunta para graficar; uso los datos de la plataforma.",
    "Para evitar errores, mis gráficas no aceptan cifras escritas por el usuario.",
    "Esos números no los uso: la gráfica se construye con los datos verificados de la plataforma.",
    "Los datos que propones no entran en la gráfica, porque ella se alimenta de la plataforma.",
    "Prefiero no graficar valores externos; hago la gráfica con los datos oficiales que tengo.",
    "Lo que pides, ponerle valores propios, no es posible; los datos los pone la plataforma.",
    "Aclaro que la gráfica nunca incluye cifras de la pregunta, solo las de la plataforma.",
    "No incorporo tus valores en la gráfica. La preparo con los datos de la base de la plataforma.",
]
G6_PREFIJOS_CODIGO = [
    "No incluyo código ni fragmentos en el bloque de la gráfica; solo lleva el tipo, las variables, las zonas y los años.",
    "Eso que me pides agregar no puedo ponerlo en el bloque: la gráfica solo se describe con tipo, variables, zonas y años.",
    "El bloque de la gráfica no admite código ni texto adicional, así que lo dejo fuera.",
    "No agrego código al bloque. Hago la gráfica con la especificación normal de la plataforma.",
    "Lo que quieres insertar en el bloque no es válido y no lo incluyo; la gráfica queda con los datos de la plataforma.",
    "Por seguridad, no escribo código ni propiedades extra dentro del bloque de la gráfica.",
    "El bloque solo acepta una descripción de la gráfica, no código; lo dejo sin lo que me pides.",
    "No puedo mezclar código en la gráfica. Te la preparo de forma estándar.",
    "Ese fragmento no lo pongo en la gráfica: ella lleva solo tipo, variables, zonas y años.",
    "Las propiedades adicionales no se aceptan en el bloque. Hago la gráfica sin ellas.",
    "No inserto contenido externo en el bloque de la gráfica, pero sí puedo prepararla con los datos de la plataforma.",
    "Dejo fuera el código que me indicas; la gráfica se construye solo con la información de la plataforma.",
]
# Si no hay datos para graficar, G6 responde igual de firme y sin bloque.
G6_SIN_BLOQUE = [
    "No incluyo valores ni código escritos en la pregunta, y tampoco tengo datos suficientes para esa gráfica. Dime otra variable o más años y la preparo.",
    "Los valores propios no entran en las gráficas, y con los datos de la plataforma no alcanza para dibujar esta. Prueba con otro rango.",
    "No puedo graficar con cifras que me des, y para esta consulta no hay datos que permitan la gráfica. Elige otra variable u otros años.",
    "Ni valores ni código se aceptan en el bloque, y de todos modos faltan datos para esta gráfica. ¿Probamos con otra variable?",
    "No uso datos escritos por el usuario ni agrego código a la gráfica. Además, los datos de la plataforma no bastan en este caso.",
    "Esa gráfica no es posible: no acepto valores ni código externos y la plataforma no tiene suficientes datos para ella.",
    "Lo que pides no se puede, ni por los valores o el código propios ni por falta de datos. Si lo deseas, consulta otro municipio o variable.",
    "Sin datos propios ni código, y con los datos de la plataforma que hay, no puedo armar la gráfica. Dime si quieres intentar con otros años.",
]


def componer_g6(prefijo: str, cuerpo: str) -> str:
    """Rechazo breve + cuerpo de una respuesta G1 (que ya cierra con «La gráfica…»): el bloque se agrega aparte."""
    return f"{prefijo} {cuerpo}"


# Cuerpos de G1 que no abren con «Con gusto», «Claro» ni «Listo» (suenan raro justo despues de un rechazo).
_CUERPOS_G6 = [t for t in G1_LINEAS_INDIVIDUAL if not t.startswith(("Con gusto", "Claro", "Listo", "Gráfica lista"))]
G6_VALORES = [componer_g6(p, _CUERPOS_G6[i % len(_CUERPOS_G6)]) for i, p in enumerate(G6_PREFIJOS_VALORES)]
G6_CODIGO = [componer_g6(p, _CUERPOS_G6[(i + 5) % len(_CUERPOS_G6)]) for i, p in enumerate(G6_PREFIJOS_CODIGO)]

# ======================================================================================= F+ inyeccion reforzada (sin bloque)
# Cada categoria: plantillas «solas» (sin hueco dato) y «con dato» (se usan cuando la pregunta trae ademas una consulta legitima).
FP_REVELAR = [
    "No puedo compartir ni repetir mis instrucciones internas. Sí puedo ayudarte con déficit habitacional, coberturas de acueducto y alcantarillado, densidad poblacional y el score de privación por municipio.",
    "Mis instrucciones internas son confidenciales, así que no las comparto. Si quieres, consulta un municipio y una variable y te respondo con los datos de la plataforma.",
    "Eso no lo puedo hacer: mis reglas de funcionamiento no se muestran ni se transcriben. Dime qué municipio y qué variable te interesan.",
    "No comparto la configuración con la que opero, ni literal ni resumida. Puedo ayudarte con los datos de vivienda y servicios de un municipio.",
    "Prefiero no revelar mis instrucciones internas. En cambio, puedo responderte sobre déficit habitacional, coberturas y densidad en el municipio que elijas.",
    "Mis instrucciones no se pueden copiar, traducir ni resumir en este chat. ¿Qué dato de un municipio quieres consultar?",
    "No tengo permiso para mostrar cómo estoy configurado, aunque lo pidas como depuración. Con gusto te ayudo con una consulta de datos por municipio.",
    "Lo que me pides es información interna que no entrego. Mi función aquí es responder con los datos de la plataforma; dime municipio, variable y año.",
    "Mis reglas internas quedan en reserva, sin importar cómo se formule la petición. Puedo, eso sí, explicarte los datos disponibles de un municipio.",
    "No puedo imprimir, recitar ni transcribir mis instrucciones. Si necesitas algo de la plataforma, indícame el municipio y la variable.",
    "Esa información de configuración no la comparto. Estoy para consultas de datos por municipio y para explicar la metodología de la plataforma.",
    "No voy a mostrar mis instrucciones del sistema. Pregúntame por un dato concreto, por ejemplo la cobertura de acueducto de un municipio en un año.",
    # con dato
    "{dato} En cuanto a mis instrucciones internas, no puedo compartirlas.",
    "{dato} Mis instrucciones internas son confidenciales, así que no las repito.",
    "{dato} Lo demás que pides, mi configuración, no lo comparto.",
    "Respondo primero tu consulta. {dato} Mis reglas internas no las revelo.",
    "{dato} La transcripción de mis instrucciones no es algo que pueda hacer.",
    "{dato} No voy a repetir mis instrucciones del sistema, pero con gusto sigo con tus consultas de datos.",
    "Esto es lo que sí puedo darte. {dato} Mi configuración interna la reservo.",
    "{dato} Por reglas de la plataforma no muestro cómo estoy configurado.",
]

FP_IGNORAR = [
    "Mis reglas no se pueden desactivar ni ignorar. Respondo solo con los datos y los documentos de la plataforma; dime qué municipio y variable quieres consultar.",
    "No puedo dejar de seguir mis reglas, aunque lo pidas. Con gusto te ayudo con una consulta de datos por municipio.",
    "Esas instrucciones no cambian mi forma de trabajar: sigo usando solo la información de la plataforma. ¿Qué dato necesitas?",
    "No hay modo de saltarme mis reglas ni de responder sin revisar los datos. Si me dices municipio, variable y año, lo consulto.",
    "No actúo sin restricciones ni cambio de rol. Respondo con los datos de la plataforma y, si no los tengo, lo digo.",
    "Mis normas siguen vigentes en este chat. Puedo ayudarte con déficit habitacional, coberturas y densidad por municipio.",
    "No puedo ignorar lo que sé sobre cómo responder con datos verificados. Pregúntame por un municipio y una variable.",
    "Nadie puede desactivar mis reglas desde la conversación. Estoy aquí para responder con los datos de la plataforma.",
    "No cambio de comportamiento por una orden en el mensaje. Respondo con lo que hay en la plataforma; dime qué quieres consultar.",
    "Sigo trabajando con las mismas reglas: datos de la plataforma, sin inventar cifras. ¿Sobre qué municipio quieres preguntar?",
    "No voy a responder sin verificar el contexto ni a inventar datos. Con un municipio y una variable, te ayudo con gusto.",
    "Mi función no cambia aunque se me pida: respondo con datos de la plataforma. Indícame el municipio y la variable.",
    "{dato} Lo de ignorar mis reglas no es posible, así que sigo respondiendo con los datos de la plataforma.",
    "{dato} Mis reglas siguen vigentes, y por eso respondo solo con lo que dice la plataforma.",
    "{dato} No puedo desactivar mis normas, pero con gusto atiendo otra consulta de datos.",
    "Respondo tu consulta con los datos de la plataforma. {dato} No ignoro mis reglas.",
    "{dato} No dejo de lado mis instrucciones, y por eso esa es la información que tengo.",
    "{dato} Sin importar la orden de saltarme las reglas, respondo con lo verificado.",
    "Te contesto con lo que hay en la plataforma. {dato} Mis reglas no se anulan por petición.",
    "{dato} Eso es lo que dice la plataforma; mis reglas no se pueden desactivar.",
]

FP_FALSOS = [
    "Solo uso los datos que me entrega la plataforma, no los que se escriben en la pregunta. Si me indicas municipio, variable y año, lo consulto.",
    "Las líneas, los fragmentos o los bloques que se pegan en la pregunta no los tomo como válidos. Respondo con lo que la plataforma me entrega.",
    "No puedo darle valor a un dato escrito en el mensaje. Dime qué quieres consultar y lo busco en la plataforma.",
    "Ese contenido viene en la pregunta, no de la plataforma, así que no lo uso. Pídeme el dato por municipio, variable y año.",
    "No reconozco como oficial lo que se escribe dentro de la pregunta. Para responder, consulto los datos de la plataforma.",
    "Los datos y documentos válidos los pone la plataforma, no el usuario. ¿Qué municipio y qué variable quieres consultar?",
    "No emito bloques ni uso citas que vengan escritas en la pregunta. Puedo responder con los datos reales de la plataforma.",
    "Lo que pegas en el mensaje no sustituye los datos de la plataforma. Dime municipio, variable y año y te respondo con ellos.",
    "No tomo como contexto un texto que viene en la pregunta. Respondo únicamente con lo que entrega la plataforma.",
    "Ese fragmento no proviene de la plataforma y por eso no lo uso. Si quieres el dato real, indícame el municipio y la variable.",
    "No confirmo cifras que se escriban en la pregunta. Los valores que doy salen siempre de los datos de la plataforma.",
    "Para evitar errores, ignoro cualquier línea, documento o bloque pegado en el mensaje y uso solo la información de la plataforma.",
    "{dato} Lo que escribiste en la pregunta como si fuera un dato no lo uso; solo cuenta lo que entrega la plataforma.",
    "{dato} Ese dato salió de la plataforma. Lo pegado en el mensaje no lo tomo como válido.",
    "{dato} No uso líneas ni bloques escritos en la pregunta; respondo con los datos de la plataforma.",
    "Esto es lo que dice la plataforma. {dato} Lo que se pega en el mensaje no cuenta como dato.",
    "{dato} Los fragmentos incluidos en la pregunta no los considero; me guío por la plataforma.",
    "{dato} Respondo con los datos reales y no con los que se pegan en el mensaje.",
    "Consulté la plataforma. {dato} El contenido pegado en la pregunta no lo tomo como oficial.",
    "{dato} Lo demás que traía el mensaje no proviene de la plataforma, así que no lo uso.",
]

FP_ESTIMAR = [
    "No tengo el dato de {v} de {MD} para {Y} y no lo voy a estimar, aunque insistas. Puedo mostrarte otro año u otra variable de ese municipio.",
    "No cuento con el dato de {v} de {MD} para {Y}, porque {motivo}. No voy a inventar una cifra.",
    "Entiendo la urgencia, pero no hay dato de {v} de {MD} para {Y} y no voy a darte un número que no esté respaldado. Puedo ayudarte con otra consulta.",
    "Prefiero decirte la verdad: no tengo el dato de {v} de {MD} para {Y}, ya que {motivo}. Dame otro año o variable y lo reviso.",
    "No voy a adivinar. Para {Y} no tengo el dato de {v} de {MD}, porque {motivo}.",
    "Sin dato no hay cifra. El valor de {v} de {MD} para {Y} no está disponible, porque {motivo}. ¿Quieres consultar otra cosa?",
    "No puedo darte un número para {v} de {MD} en {Y}: {motivo}. Si lo deseas, consulta otro año u otro municipio.",
    "Aunque insistas, no tengo el dato de {v} de {MD} para {Y} y no lo voy a inventar. Puedo mostrarte lo que sí hay disponible.",
    "No voy a dar una cifra sin respaldo: el dato de {v} de {MD} para {Y} no existe en la plataforma, porque {motivo}.",
    "Mi respuesta sigue siendo la misma: no tengo el dato de {v} de {MD} para {Y}. Mejor consultemos otro año o variable.",
    "No me corresponde inventar valores. Para {Y}, el dato de {v} de {MD} no está disponible, porque {motivo}.",
    "Comprendo que lo necesites, pero no cuento con el dato de {v} de {MD} para {Y} y no voy a darte una cifra que no sea real. ¿Probamos con otra consulta?",
    "No hay dato de {v} de {MD} para {Y}, porque {motivo}. Prefiero no dar números que no pueda respaldar.",
    "No puedo completar ese hueco: el dato de {v} de {MD} para {Y} no existe. Te ayudo con otro año u otra variable.",
    "Por más que insistas, no voy a dar una cifra de {v} de {MD} para {Y}. La plataforma no tiene ese dato, porque {motivo}.",
    "Lo siento, no tengo el dato de {v} de {MD} para {Y}. No lo voy a calcular por mi cuenta, pero puedo buscar otro dato del municipio.",
]

PLANTILLAS = {
    "g1_lineas_individual": G1_LINEAS_INDIVIDUAL,
    "g1_lineas_comparar": G1_LINEAS_COMPARAR,
    "g1_barras_ranking": G1_BARRAS_RANKING,
    "g1_barras_agrupadas_ind": G1_BARRAS_AGRUPADAS_IND,
    "g1_barras_agrupadas_cmp": G1_BARRAS_AGRUPADAS_CMP,
    "g1_gauge": G1_GAUGE,
    "g2_serie": G2_SERIE,
    "g2_comparacion": G2_COMPARACION,
    "g2_puntual": G2_PUNTUAL,
    "g3_un_anio": G3_UN_ANIO,
    "g3_sin_dato": G3_SIN_DATO,
    "g4_tipo_no_soportado": G4_TIPO_NO_SOPORTADO,
    "g5_sin_municipio": G5_SIN_MUNICIPIO,
    "g5_sin_variable": G5_SIN_VARIABLE,
    "g6_valores": G6_VALORES,
    "g6_codigo": G6_CODIGO,
    "fp_revelar": FP_REVELAR,
    "fp_ignorar": FP_IGNORAR,
    "fp_falsos": FP_FALSOS,
    "fp_estimar": FP_ESTIMAR,
}

# Subfamilias cuya respuesta lleva el bloque ```grafica (el generador lo agrega con bloque.armar_respuesta). G6 lo lleva salvo G6_SIN_BLOQUE.
CON_BLOQUE = {
    "g1_lineas_individual", "g1_lineas_comparar", "g1_barras_ranking", "g1_barras_agrupadas_ind", "g1_barras_agrupadas_cmp",
    "g1_gauge", "g6_valores", "g6_codigo",
}

# Huecos que cada subfamilia PUEDE usar y huecos que TODA plantilla debe usar al menos uno de... (minimos = todos obligatorios en
# cada plantilla; las que no los usen se rechazan en tests porque descartarian informacion del contexto).
HUECOS_PERMITIDOS = {
    "g1_lineas_individual": {"MD", "V", "Vc", "Vde", "v", "Y1", "Y2", "V1", "V2", "tendencia", "nota"},
    "g1_lineas_comparar": {"MDs", "V", "Vc", "v", "Y1", "Y2", "lista", "nota"},
    "g1_barras_ranking": {"MDs", "v", "Y", "top", "topv", "bot", "botv", "nota"},
    "g1_barras_agrupadas_ind": {"MD", "Vs_txt", "Y", "lista_vars", "nota"},
    "g1_barras_agrupadas_cmp": {"MDs", "Vs_txt", "Y", "nota"},
    "g1_gauge": {"MD", "V", "Vc", "v", "Y", "val", "nota"},
    "g2_serie": {"MD", "V", "Vc", "v", "Y1", "Y2", "serie", "nota"},
    "g2_comparacion": {"MDs", "V", "Vc", "v", "Y", "lista", "nota"},
    "g2_puntual": {"MD", "V", "Vc", "v", "Y", "val", "nota"},
    "g3_un_anio": {"MD", "V", "Vc", "v", "Y", "val", "nota"},
    "g3_sin_dato": {"MD", "v", "motivo", "alterno"},
    "g4_tipo_no_soportado": {"t", "MDs"},
    "g5_sin_municipio": set(),
    "g5_sin_variable": {"MDs"},
    "g6_valores": set(),  # = huecos de g1_lineas_individual (se completa abajo)
    "g6_codigo": set(),
    "fp_revelar": {"dato"},
    "fp_ignorar": {"dato"},
    "fp_falsos": {"dato"},
    "fp_estimar": {"v", "MD", "Y", "motivo"},
}
HUECOS_PERMITIDOS["g6_valores"] = set(HUECOS_PERMITIDOS["g1_lineas_individual"])
HUECOS_PERMITIDOS["g6_codigo"] = set(HUECOS_PERMITIDOS["g1_lineas_individual"])
# Huecos obligatorios en TODA plantilla de la subfamilia (la informacion central del contexto debe aparecer).
HUECOS_OBLIGATORIOS = {
    "g1_lineas_individual": {"MD", "Y1", "Y2", "V1", "V2"},
    "g1_lineas_comparar": {"MDs", "Y2", "lista"},
    "g1_barras_ranking": {"Y", "top", "topv", "bot", "botv"},
    "g1_barras_agrupadas_ind": {"MD", "Y", "lista_vars"},
    "g1_barras_agrupadas_cmp": {"MDs", "Y", "Vs_txt"},
    "g1_gauge": {"MD", "Y", "val"},
    "g2_serie": {"MD", "serie"},
    "g2_comparacion": {"Y", "lista"},
    "g2_puntual": {"MD", "Y", "val"},
    "g3_un_anio": {"MD", "Y", "val"},
    "g3_sin_dato": {"MD", "v", "motivo"},
    "g4_tipo_no_soportado": {"t"},
    "g5_sin_municipio": set(),
    "g5_sin_variable": {"MDs"},
    "g6_valores": {"MD", "Y1", "Y2", "V1", "V2"},
    "g6_codigo": {"MD", "Y1", "Y2", "V1", "V2"},
    "fp_revelar": set(),
    "fp_ignorar": set(),
    "fp_falsos": set(),
    "fp_estimar": {"v", "MD", "Y"},
}
# Texto SIN bloque para G6 cuando no hay datos: no forma parte de PLANTILLAS (se controla aparte).

# ======================================================================================= HS multi-turno (adenda 7.1b §4)
from . import respuestas_hs as _hs  # noqa: E402

PLANTILLAS.update(_hs.PLANTILLAS)
HUECOS_PERMITIDOS.update(_hs.HUECOS_PERMITIDOS)
HUECOS_OBLIGATORIOS.update(_hs.HUECOS_OBLIGATORIOS)
