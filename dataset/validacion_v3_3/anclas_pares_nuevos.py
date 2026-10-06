"""Especificacion de los anclajes de los pares NUEVOS de v3.3 (T-122). La lee generar_manifiesto.py.

Cada entrada:
  pregunta   inicio exacto del campo instruction del par (basta para identificarlo)
  cat        categoria segun dataset/README.md: (a) general con fuente externa, (b) propio de Techo 360, sin fuente externa,
             (c) hibrida: conecta un dato de Techo 360 con una fuente oficial
  codigo     lista de (repo, ruta, texto) -- el texto debe aparecer en esa ruta; el generador busca su linea en origin/development de cada repo
  externa    lista de (descripcion, url, como se verifico)
Convencion de v3.2 que se mantiene: `source` solo en (a) y (c); los (b) se anclan a codigo o README propios y no llevan `source`.
"""

DNP = ("DNP - TerriData, Sistema de Estadísticas Territoriales", "https://dnp.gov.co/LaEntidad_/subdireccion-general-descentralizacion-desarrollo-territorial/direccion-ordenamiento-desarrollo-territorial/Paginas/sistema-de-estadisticas-territoriales-terridata.aspx", "pagina oficial leida (WebFetch)")
SSPD = ("SSPD - Funciones y SUI (Ley 142 de 1994, art. 53)", "https://www.superservicios.gov.co/Nuestra-entidad/Quienes-somos/funciones", "resultado de busqueda dirigida a dominios oficiales (superservicios.gov.co, funcionpublica.gov.co)")
DANE = ("DANE - Boletín Técnico Déficit Habitacional 2018 (metodología 2020)", "https://www.dane.gov.co/files/investigaciones/deficit-habitacional/deficit-hab-2020-boletin.pdf", "PDF oficial descargado y leido (texto completo, secciones 2 y 3)")
MP = lambda tema, url: ("MedlinePlus (NIH/NLM) - " + tema, url, "resultado de busqueda dirigida a medlineplus.gov (resumen de la pagina)")  # noqa: E731
OMS = lambda tema, url: ("OMS - " + tema, url, "resultado de busqueda dirigida a who.int (nota descriptiva)")  # noqa: E731
LEY100 = ("Ley 100 de 1993 (SGSSS)", "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5248", "resultado de busqueda dirigida a minsalud.gov.co y funcionpublica.gov.co")

ANCLAS = [
    # ---------------- Score ----------------
    {"pregunta": "¿Cómo se calcula el Score de Privación de un año futuro", "cat": "b",
     "codigo": [("backend", "services/proyeccion_service.py", "ANIO_BASE_SCORE = 2024"), ("backend", "services/proyeccion_service.py", "obtener_deficit_base"),
                ("proyeccion", "app/services/proyeccion.py", "INDICADORES_SOPORTADOS = frozenset")]},
    {"pregunta": "¿Por qué el déficit habitacional no se proyecta con regresión lineal", "cat": "b",
     "codigo": [("proyeccion", "app/services/proyeccion.py", "deficit_habitacional_cuantitativo NO entra aqui a proposito")]},
    {"pregunta": "¿Qué variables del panel de Techo 360 no forman parte del Score", "cat": "b",
     "codigo": [("backend", "routers/zonas.py", "densidad_poblacional queda fuera a proposito"), ("backend", "services/score_privacion.py", "VARIABLES_SCORE = ")]},
    {"pregunta": "¿Qué componentes forman el déficit habitacional cuantitativo del DANE?", "cat": "c", "externa": [DANE],
     "codigo": [("backend", "routers/zonas.py", "Deficit CUANTITATIVO (cols 11-14)")]},
    {"pregunta": "¿Qué componentes forman el déficit habitacional cualitativo del DANE", "cat": "c", "externa": [DANE],
     "codigo": [("backend", "routers/zonas.py", "Deficit CUALITATIVO (cols 15-28)")]},
    {"pregunta": "¿Cambió alguna vez la fórmula del Score de Privación", "cat": "c", "externa": [DANE],
     "codigo": [("backend", "routers/zonas.py", "Hasta este cambio, el tercer componente era deficit_habitacional_total")]},
    {"pregunta": "¿Por qué las zonas del mapa no incluyen el registro nacional agregado", "cat": "b",
     "codigo": [("backend", "routers/zonas.py", 'CODIGO_AGREGADO_NACIONAL_TERRIDATA = "01001"'), ("backend", "ingestion/terridata_adapter.py", "def _es_agregado_nacional")]},
    {"pregunta": "¿El déficit habitacional que entra al Score de Privación de 2024", "cat": "b",
     "codigo": [("backend", "ingestion/proyeccion_2024.py", "valor_2024_proyectado = valor_2018_real")]},
    {"pregunta": "¿Cómo se rellenan las coberturas de acueducto y alcantarillado para 2025", "cat": "b",
     "codigo": [("backend", "ingestion/db.py", "fiabilidad = max(30, 60 - 10*(antiguedad-1))")]},
    {"pregunta": "¿Por qué el déficit cuantitativo resulta adecuado como componente", "cat": "c", "externa": [DANE],
     "codigo": [("backend", "routers/zonas.py", "corr(deficit_CUANTITATIVO, cobertura_alcantarillado)")]},
    {"pregunta": "¿Qué significa que un municipio tenga un Score de Privación de 0,5?", "cat": "b",
     "codigo": [("backend", "services/score_privacion.py", "def normalizar_minmax")]},
    {"pregunta": "¿Por qué el score de un municipio puede variar de un año a otro", "cat": "b",
     "codigo": [("backend", "routers/zonas.py", "Min-max por variable, calculado sobre TODAS las filas")]},
    {"pregunta": "¿Por qué Techo 360 normaliza las variables antes de promediarlas", "cat": "b",
     "codigo": [("backend", "services/score_privacion.py", "def calcular_score_privacion")]},
    # ---------------- TerriData y SSPD ----------------
    {"pregunta": "¿Qué es TerriData y qué entidad la administra?", "cat": "a", "externa": [DNP]},
    {"pregunta": "¿En qué se diferencian TerriData y la Superintendencia", "cat": "c", "externa": [DNP, SSPD]},
    {"pregunta": "¿De dónde toma Techo 360 las coberturas de acueducto y alcantarillado", "cat": "b",
     "codigo": [("backend", "ingestion/terridata_adapter.py", '"cobertura_acueducto": {"dimension": "3"')]},
    {"pregunta": "¿Qué trae TerriData de cada dato, además de su valor?", "cat": "c", "externa": [DNP],
     "codigo": [("backend", "ingestion/terridata_adapter.py", "Código Departamento | Departamento | Código Entidad")]},
    {"pregunta": "¿Qué significa que el origen de una densidad poblacional futura", "cat": "c", "externa": [DNP],
     "codigo": [("backend", "ingestion/actualizar_densidad_dane.py", "TerriData-proyeccion")]},
    {"pregunta": "¿Por qué Techo 360 descarta de TerriData las filas cuyo código termina en 000?", "cat": "c", "externa": [DNP],
     "codigo": [("backend", "ingestion/terridata_adapter.py", 'codigo.endswith("000")')]},
    {"pregunta": "¿Por qué fue necesario un tratamiento especial para los números que entrega TerriData?", "cat": "c", "externa": [DNP],
     "codigo": [("backend", "ingestion/terridata_adapter.py", "def _parsear_numero_terridata")]},
    {"pregunta": "¿Por qué Techo 360 usa de TerriData la variante de cobertura", "cat": "c", "externa": [DNP],
     "codigo": [("backend", "ingestion/terridata_adapter.py", 'Se eligio la variante "(REC)"')]},
    {"pregunta": "¿Qué pasa si TerriData cambia el formato de sus archivos?", "cat": "b",
     "codigo": [("backend", "ingestion/validacion_esquema.py", "class EsquemaCambiadoError")]},
    {"pregunta": "¿TerriData es una plataforma de la Superintendencia", "cat": "c", "externa": [DNP, SSPD]},
    {"pregunta": "¿Techo 360 consulta TerriData cada vez que alguien abre el mapa?", "cat": "b",
     "codigo": [("backend", "ingestion/scheduler.py", "CRON_SEMANAL")]},
    # ---------------- Ollama y repositorios ----------------
    {"pregunta": "¿Qué tecnología usa cada uno de los cinco repositorios", "cat": "b",
     "codigo": [("backend", "requirements.txt", "fastapi"), ("frontend", "package.json", "react-leaflet"), ("chatbot", "requirements.txt", "aio-pika"),
                ("proyeccion", "requirements.txt", "pandas"), ("infra", "docker-compose.yml", "image: ollama/ollama:latest")]},
    {"pregunta": "¿El chatbot de Techo 360 usa Dialogflow", "cat": "b",
     "codigo": [("chatbot", "app/ollama_client.py", "OLLAMA_URL = os.environ.get")]},
    {"pregunta": "¿Qué piezas componen el servicio de techo360-chatbot", "cat": "b",
     "codigo": [("chatbot", "app/main.py", "iniciar_consumidor(RABBITMQ_URL)"), ("chatbot", "app/ollama_client.py", "/api/chat")]},
    {"pregunta": "¿Cómo se entrenó el modelo del chatbot", "cat": "b",
     "codigo": [("chatbot", "README.md", "## Fine-tuning (Llama 3.2 LoRA/QLoRA)")]},
    {"pregunta": "¿Quién responde la pregunta de un usuario cuando hay un worker", "cat": "b",
     "codigo": [("workers", "README.md", "usa prioridad **10**"), ("chatbot", "app/rabbitmq_consumer.py", "CHATBOT_CONSUMER_PRIORITY"),
                ("backend", "routers/chatbot.py", "Ningun worker respondio a tiempo")]},
    {"pregunta": "¿Qué datos debe traer cada petición al chatbot", "cat": "b",
     "codigo": [("chatbot", "README.md", "## Contrato de entrada (T-97, 26/09)"), ("chatbot", "README.md", "credenciales para consultar `mapcaloruser`")]},
    {"pregunta": "¿Qué servicio guarda el historial de conversaciones del chatbot?", "cat": "b",
     "codigo": [("backend", "routers/chatbot.py", "El backend persiste sincronicamente aqui")]},
    {"pregunta": "¿Qué le responde el backend al usuario si el chatbot no está disponible?", "cat": "b",
     "codigo": [("backend", "routers/chatbot.py", "El asistente no esta disponible")]},
    {"pregunta": "¿Qué pasa con los consumidores de RabbitMQ cuando el broker se reinicia?", "cat": "b",
     "codigo": [("chatbot", "app/rabbitmq_consumer.py", "_QUEUES_VIVAS: list"), ("proyeccion", "app/rabbitmq_consumer.py", "_QUEUES_VIVAS: list"),
                ("backend", "services/chatbot_persistencia_consumer.py", "_QUEUES_VIVAS: list")]},
    {"pregunta": "¿Cómo evita techo360-infra que dos despliegues se pisen", "cat": "b",
     "codigo": [("infra", "scripts/deploy-service.sh", "flock -w 1800 9"), ("infra", "scripts/deploy-infra.sh", "flock -w 1800 9")]},
    {"pregunta": "¿Qué servicios levanta techo360-infra además de los cuatro", "cat": "b",
     "codigo": [("infra", "docker-compose.yml", "image: pgvector/pgvector:pg16"), ("infra", "docker-compose.yml", "image: postgis/postgis:16-3.4")]},
    {"pregunta": "¿Qué partes de Techo 360 se comunican por HTTP y cuáles por RabbitMQ?", "cat": "b",
     "codigo": [("frontend", "nginx.conf", "location /api/"), ("backend", "services/proyeccion_rpc_client.py", 'REQUEST_QUEUE = "proyeccion_requests"'),
                ("chatbot", "app/ollama_client.py", "/api/chat")]},
    {"pregunta": "¿En qué base de datos se guardan los usuarios y en cuál las conversaciones", "cat": "b",
     "codigo": [("infra", "docker-compose.yml", "container_name: techo360-postgres-users"), ("chatbot", "README.md", "credenciales para consultar `mapcaloruser`")]},
    {"pregunta": "¿Qué librería usa el frontend de Techo 360 para dibujar el mapa?", "cat": "b",
     "codigo": [("frontend", "package.json", "react-leaflet")]},
    {"pregunta": "¿Por qué el navegador no se queda con una versión vieja", "cat": "b",
     "codigo": [("frontend", "nginx.conf", 'add_header Cache-Control "no-cache" always;')]},
    # ---------------- Salud ----------------
    {"pregunta": "¿Qué función cumplen las plaquetas?", "cat": "a", "externa": [MP("Conteo de plaquetas", "https://medlineplus.gov/spanish/ency/article/003647.htm")]},
    {"pregunta": "¿Para qué sirven los leucocitos?", "cat": "a", "externa": [MP("Conteo de glóbulos blancos", "https://medlineplus.gov/spanish/ency/article/003643.htm")]},
    {"pregunta": "¿Qué mide un hematocrito?", "cat": "a", "externa": [MP("Hematocrito", "https://medlineplus.gov/spanish/ency/article/003646.htm")]},
    {"pregunta": "¿Qué es la anemia?", "cat": "a", "externa": [MP("Anemia", "https://medlineplus.gov/spanish/ency/article/000560.htm")]},
    {"pregunta": "¿Qué significan los dos números de la presión arterial?", "cat": "a", "externa": [MP("Medición de la presión arterial", "https://medlineplus.gov/lab-tests/measuring-blood-pressure/")]},
    {"pregunta": "¿Cuál es la diferencia entre una arteria y una vena?", "cat": "a", "externa": [MP("Sistema circulatorio", "https://medlineplus.gov/spanish/ency/esp_imagepages/8747.htm")]},
    {"pregunta": "¿Sirven los antibióticos para curar un resfriado?", "cat": "a", "externa": [MP("Resfriados y gripe - antibióticos", "https://medlineplus.gov/spanish/ency/article/002070.htm")]},
    {"pregunta": "¿En qué se diferencian un virus y una bacteria?", "cat": "a", "externa": [MP("Enfermedades infecciosas", "https://medlineplus.gov/infectiousdiseases.html")]},
    {"pregunta": "¿Cómo protege una vacuna?", "cat": "a", "externa": [MP("Vacunas", "https://medlineplus.gov/spanish/ency/article/002024.htm")]},
    {"pregunta": "¿Cómo se calcula el índice de masa corporal?", "cat": "a", "externa": [OMS("Obesidad y sobrepeso (nota descriptiva)", "https://www.who.int/es/news-room/fact-sheets/detail/obesity-and-overweight")]},
    {"pregunta": "¿Qué formas de desnutrición distingue la OMS?", "cat": "a", "externa": [OMS("Malnutrición (nota descriptiva)", "https://www.who.int/es/news-room/fact-sheets/detail/malnutrition")]},
    {"pregunta": "¿En qué se diferencian el régimen contributivo y el subsidiado", "cat": "a", "externa": [LEY100]},
    {"pregunta": "¿Qué es el sistema inmunitario?", "cat": "a", "externa": [MP("Sistema inmunitario y sus enfermedades", "https://medlineplus.gov/immunesystemanddisorders.html")]},
    {"pregunta": "¿Qué es el colesterol?", "cat": "a", "externa": [MP("Colesterol total", "https://medlineplus.gov/spanish/ency/article/007813.htm")]},
    {"pregunta": "¿Es obligatoria la afiliación al sistema de salud en Colombia?", "cat": "a", "externa": [LEY100]},
]
