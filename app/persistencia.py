import asyncio
import json
import logging
import os

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractRobustConnection

logger = logging.getLogger(__name__)

# En produccion (docker-compose.yml de techo360-infra) esta variable ya
# se define -- el default de aqui es solo para correr localmente sin
# RabbitMQ (mismo patron que RABBITMQ_URL en app/main.py).
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

# Contrato interno con techo360-backend (services/chatbot_persistencia_consumer.py
# lo consume). T-97 (rediseño): este servicio dejo de tener credenciales
# a postgres-vector -- el pool de workers de laboratorio que se
# despliega en maquinas con acceso fisico de estudiantes debe quedar
# limitado a hablar con RabbitMQ, nunca tener una credencial de base de
# datos. Publicar aqui reemplaza el psycopg2.connect() directo que
# tenia esta funcion antes.
EVENTOS_QUEUE = "chatbot_eventos_persistencia"

_connection: AbstractRobustConnection | None = None
_connection_lock = asyncio.Lock()


async def _obtener_channel():
    global _connection
    async with _connection_lock:
        if _connection is None or _connection.is_closed:
            _connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await _connection.channel()
    await channel.declare_queue(EVENTOS_QUEUE, durable=True)
    return channel


async def persistir_intercambio(
    usuario_id: int,
    consentimiento_entrenamiento: bool,
    mensaje_usuario: str,
    respuesta_asistente: str,
    conversacion_id: int | None = None,
) -> None:
    """Publica un evento "intercambio_completo" para que el backend
    (unico servicio con credenciales a postgres-vector) inserte los 2
    mensajes.

    conversacion_id es opcional: si el llamador ya tiene una
    conversacion existente (creada via POST /chatbot/conversaciones en
    techo360-backend), pasarla aqui evita que
    chatbot_persistencia_consumer.py cree una conversacion nueva en
    cada intercambio. Si no se pasa (o es None), el backend sigue
    creando una nueva -- comportamiento historico, usado solo por
    llamadores sin ese contexto (pruebas locales via POST /chatbot/send).

    usuario_id y consentimiento_entrenamiento llegan ya resueltos por
    quien llama (el backend, que si tiene acceso a mapcaloruser en
    postgres-users) -- este servicio nunca consulta esa tabla
    directamente.

    Deliberadamente "best effort": un fallo al publicar NO debe tumbar
    ni invalidar la respuesta que Ollama ya genero -- perder la fila de
    historial es preferible a perder la respuesta en si. Se loguea como
    error para que quede visible en monitoreo, nunca se relanza.
    """
    try:
        channel = await _obtener_channel()
        payload = {
            "tipo": "intercambio_completo",
            "usuario_id": usuario_id,
            "consentimiento_entrenamiento": consentimiento_entrenamiento,
            "mensaje_usuario": mensaje_usuario,
            "respuesta_asistente": respuesta_asistente,
            "conversacion_id": conversacion_id,
        }
        await channel.default_exchange.publish(
            Message(
                body=json.dumps(payload).encode(),
                content_type="application/json",
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=EVENTOS_QUEUE,
        )
        await channel.close()
    except Exception:
        logger.exception("No se pudo publicar el evento de persistencia en RabbitMQ")


# T-97: asyncio.create_task() NO retiene una referencia fuerte a la tarea
# -- el garbage collector puede recolectarla a mitad de ejecucion sin
# avisar (gotcha documentado de asyncio, no una hipotesis). Este set
# guarda la referencia mientras la tarea de persistencia corre, y el
# callback la quita sola al terminar (exito o error, ya logueado dentro
# de persistir_intercambio arriba). Centralizado aqui porque tanto
# app/main.py como app/rabbitmq_consumer.py necesitan exactamente el
# mismo patron -- duplicarlo en los dos lugares invitaria a que uno se
# actualice y el otro no.
_tareas_persistencia: set[asyncio.Task] = set()


def persistir_en_background(
    usuario_id: int,
    consentimiento_entrenamiento: bool,
    mensaje_usuario: str,
    respuesta_asistente: str,
    conversacion_id: int | None = None,
) -> None:
    """Lanza persistir_intercambio() sin esperar a que termine ni poder
    tumbar al llamador -- ver docstring de persistir_intercambio.

    T-97 (rediseño): ya no necesita asyncio.to_thread() -- publicar en
    RabbitMQ via aio_pika es I/O async nativo, no bloqueante como lo
    era psycopg2.
    """
    tarea = asyncio.create_task(
        persistir_intercambio(
            usuario_id, consentimiento_entrenamiento, mensaje_usuario, respuesta_asistente, conversacion_id
        )
    )
    _tareas_persistencia.add(tarea)
    tarea.add_done_callback(_tareas_persistencia.discard)
