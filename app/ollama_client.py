import logging
import os

import httpx

logger = logging.getLogger(__name__)

# T-94: sincronizado caracter por caracter con SYSTEM_PROMPT de
# training/convertir_dataset.py (T-70), el mismo con el que se genero
# dataset/entrenamiento_formateado/train.jsonl y se entreno el adaptador
# LoRA de T-92, y con la directiva SYSTEM del Modelfile de Ollama
# (training/ollama/Modelfile.v3.2). Debe mantenerse identico en los tres
# lugares -- un system prompt distinto en inferencia invalidaria parte
# de lo aprendido en el fine-tuning.
#
# Se pasa explicitamente en cada llamada a Ollama (abajo) en vez de
# confiar unicamente en el SYSTEM ya horneado en el Modelfile -- Ollama
# permite que el campo "system" de la solicitud sobreescriba el del
# Modelfile, asi que pasarlo aqui tambien evita que un futuro cambio de
# modelo/tag en Ollama sin el Modelfile correcto sirva silenciosamente
# con un system prompt distinto al que se entreno.
SYSTEM_PROMPT = (
    "Eres el asistente virtual de Techo 360, una plataforma que analiza la "
    "pobreza y el deficit de vivienda en los municipios de Colombia. "
    "Respondes en espanol de forma clara y precisa sobre el Score de "
    "Privacion y los indicadores de Techo 360, y sobre la politica publica "
    "colombiana de vivienda y pobreza (IPM, deficit habitacional, cobertura "
    "de acueducto y alcantarillado) en la que se basa el sistema."
)

# En produccion (docker-compose.yml de techo360-infra) esta variable ya
# se define como OLLAMA_URL=http://ollama:11434 -- el default de aqui
# (localhost) es solo para correr y probar el servicio fuera de Docker.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
# Tag explicito -- "techo360-chatbot" sin tag resuelve a ":latest", que
# quedo apuntando a v1 desde su primer push y nunca se re-etiqueto (ver
# training/ollama/Modelfile.v3.2: "NO se toca el tag `latest`"). v3.2 es
# el modelo de referencia vigente (25-sep-2026).
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "techo360-chatbot:v3.2")

# Timeout generoso: la primera solicitud tras (re)iniciar el contenedor
# de Ollama incluye cargar el modelo GGUF a memoria (~1.9 GB, medido en
# T-95 en ~44s en la maquina de desarrollo via CPU; puede variar en el
# VPS de produccion), no solo generar la respuesta. Solicitudes
# posteriores con el modelo ya cargado son mucho mas rapidas (~5s en la
# prueba local de T-95).
TIMEOUT_OLLAMA_S = 120.0

# Tope de tokens generados por respuesta (options.num_predict de Ollama). Medido en el VPS con
# 3 CPU y NUM_THREAD = 3 (05-oct-2026): ~7,5 tokens/s, asi que 400 tokens ~ 54 s (~66 s con la carga
# en frio del modelo, ~12 s); en el peor caso medido, ~4,6 tokens/s, ~87 s (~99 s con la carga) --
# por debajo de TIMEOUT_OLLAMA_S (120 s) y del RPC del backend (200 s). Las respuestas reales hasta
# hoy llegan a ~250 tokens (1010 caracteres).
# Si se corta por longitud, Ollama devuelve done_reason="length" y el texto puede quedar a medias
# (ver el warning en generar_respuesta()).
NUM_PREDICT = 400

# Hilos de CPU de llama.cpp (options.num_thread). Medido en el VPS el 05-oct-2026 con cpus=3 en el
# contenedor de Ollama: 4,91 tokens/s con el valor por defecto frente a 7,46 con 3 hilos. Debe igualar
# la cuota de CPU del contenedor de Ollama (cpus en techo360-infra). Todas las peticiones deben usar
# el mismo valor: cambiar las opciones del runner entre peticiones puede recargar el modelo.
NUM_THREAD = 3


class OllamaNoDisponibleError(RuntimeError):
    """No se pudo contactar a Ollama o respondio con error HTTP. Cada
    consumidor (endpoint HTTP, consumer de RabbitMQ) decide como
    traducir esto a su propio protocolo -- 502 en el caso HTTP, un
    campo "status": "error" en el caso RPC."""


async def generar_respuesta(mensaje: str) -> str:
    """Logica compartida entre POST /chatbot/send (app/main.py) y el
    consumer de RabbitMQ (app/rabbitmq_consumer.py) -- ver AVISO en
    rabbitmq_consumer.py sobre por que ambos caminos deben llamar
    exactamente la misma funcion en vez de duplicar la llamada a
    Ollama: evita que los dos caminos de entrada al chatbot diverjan
    (system prompt, modelo, timeout) con el tiempo.

    Fuera de alcance en esta version, deliberadamente omitido (T-95,
    segundo frente, y sin cambios en T-96/consumer):
    - RAG contra pgvector: el mensaje del usuario se envia tal cual a
      Ollama, sin recuperar contexto adicional de la base de datos
      vectorial.
    - Historial de conversacion multi-turno: cada llamada es
      independiente -- no se mantiene ni se envia el historial de
      mensajes previos del usuario.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_OLLAMA_S) as client:
        try:
            respuesta = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": mensaje},
                    ],
                    "stream": False,
                    "options": {"num_predict": NUM_PREDICT, "num_thread": NUM_THREAD},
                },
            )
            respuesta.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaNoDisponibleError(f"No se pudo contactar a Ollama: {exc}") from exc

    datos = respuesta.json()
    if datos.get("done_reason") == "length":
        logger.warning(
            "Respuesta cortada por longitud (done_reason=length, eval_count=%s, NUM_PREDICT=%d)",
            datos.get("eval_count"),
            NUM_PREDICT,
        )
    return datos["message"]["content"]
