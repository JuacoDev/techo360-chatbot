import logging
import os
import time

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
# Configurable con OLLAMA_NUM_THREAD (p. ej. un worker nuevo con otro numero de CPU); sin la variable
# (o con un valor invalido) queda en 3, el valor medido en produccion. Cambiarlo en la VPS se decide
# tras medirlo alli (scripts/medir-presupuesto-recursos.sh --ollama en techo360-infra), no aqui.
NUM_THREAD_POR_DEFECTO = 3


def _num_thread_desde_entorno(valor: str | None) -> int:
    """Entero positivo de OLLAMA_NUM_THREAD, o el valor por defecto si falta o es invalido."""
    if valor is None or not valor.strip():
        return NUM_THREAD_POR_DEFECTO
    try:
        hilos = int(valor)
    except ValueError:
        hilos = 0
    if hilos < 1:
        logger.warning("OLLAMA_NUM_THREAD invalido (%r): se usa %d.", valor, NUM_THREAD_POR_DEFECTO)
        return NUM_THREAD_POR_DEFECTO
    return hilos


NUM_THREAD = _num_thread_desde_entorno(os.environ.get("OLLAMA_NUM_THREAD"))


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


# ---------------------------------------------------------------------------------------------
# Camino v2 del contrato RPC (fase2-2 / fase4-especificacion-2, 4.4): los mensajes (system incluido)
# llegan ya ensamblados por el backend y se envian tal cual. generar_respuesta() de arriba (v1) NO cambia.
# Mismas opciones del runner que v1 (num_predict, num_thread; num_ctx lo fija el Modelfile: 2048): cambiarlas
# entre peticiones puede recargar el modelo.
# ---------------------------------------------------------------------------------------------
NUM_CTX = 2048
CARACTERES_POR_TOKEN = 3.0  # estimacion conservadora para español (medido 3,5-3,6)
_digest_cache: dict[str, str] = {}


def tokens_estimados(mensajes: list[dict]) -> int:
    return int(sum(len(m["content"]) for m in mensajes) / CARACTERES_POR_TOKEN) + 1


async def obtener_digest(forzar: bool = False) -> str | None:
    """Digest del modelo (de /api/tags de Ollama), cacheado en memoria por tag; None si no se puede obtener
    (el campo queda ausente en la respuesta). Se refresca con forzar=True (arranque, fallo de generacion)."""
    if not forzar and OLLAMA_MODEL in _digest_cache:
        return _digest_cache[OLLAMA_MODEL]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
        for modelo in r.json().get("models", []):
            if modelo.get("name") == OLLAMA_MODEL or modelo.get("model") == OLLAMA_MODEL:
                digest = modelo.get("digest")
                if digest:
                    _digest_cache[OLLAMA_MODEL] = digest
                    return digest
    except Exception as exc:  # noqa: BLE001 -- el digest es informativo: nunca debe impedir responder
        logger.warning("No se pudo obtener el digest del modelo: %s", exc)
    _digest_cache.pop(OLLAMA_MODEL, None)
    return None


async def generar_respuesta_v2(mensajes: list[dict]) -> dict:
    """mensajes: [{"role", "content"}, ...] tal como se envian a /api/chat. Devuelve
    {"texto", "done_reason", "prompt_eval_count", "eval_count", "duracion_ms"}."""
    inicio = time.monotonic()
    async with httpx.AsyncClient(timeout=TIMEOUT_OLLAMA_S) as client:
        try:
            respuesta = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": mensajes,
                    "stream": False,
                    "options": {"num_predict": NUM_PREDICT, "num_thread": NUM_THREAD},
                },
            )
            respuesta.raise_for_status()
        except httpx.HTTPError as exc:
            _digest_cache.pop(OLLAMA_MODEL, None)  # tras un fallo se vuelve a leer el digest
            raise OllamaNoDisponibleError(f"No se pudo contactar a Ollama: {exc}") from exc

    datos = respuesta.json()
    if datos.get("done_reason") == "length":
        logger.warning(
            "Respuesta cortada por longitud (done_reason=length, eval_count=%s, NUM_PREDICT=%d)",
            datos.get("eval_count"),
            NUM_PREDICT,
        )
    total_ns = datos.get("total_duration")
    return {
        "texto": datos["message"]["content"],
        "done_reason": datos.get("done_reason"),
        "prompt_eval_count": datos.get("prompt_eval_count"),
        "eval_count": datos.get("eval_count"),
        "duracion_ms": int(total_ns / 1e6) if isinstance(total_ns, (int, float)) else int((time.monotonic() - inicio) * 1000),
    }
