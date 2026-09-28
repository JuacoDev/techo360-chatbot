import json
import logging
import os

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage, AbstractRobustConnection

from app.ollama_client import OllamaNoDisponibleError, generar_respuesta

logger = logging.getLogger(__name__)

# Nombre acordado con Daniel (25-sep-2026) para el pool de workers en los
# labs de la universidad -- NO cambiar sin coordinar con el otro extremo
# (quien publique en esta cola debe usar el mismo nombre exacto).
REQUEST_QUEUE = "chatbot_requests"

# Prioridad de consumer nativa de RabbitMQ (x-priority, requiere el
# feature "Consumer Priorities" del broker -- disponible por defecto en
# rabbitmq:3.13, no hay que habilitar plugin). A mayor numero, mayor
# prioridad: RabbitMQ entrega los mensajes al consumer de mayor prioridad
# que este activo, y solo cae a uno de menor prioridad si ese no esta
# conectado. Default 0 (respaldo/VPS) -- techo360-workers pone esta
# misma variable en 10 para que el pool de laboratorio tenga prioridad
# sobre el consumer del VPS sin tocar codigo, ver
# techo360-workers/README.md.
CONSUMER_PRIORITY = int(os.environ.get("CHATBOT_CONSUMER_PRIORITY", "0"))

# >>> AVISO -- por que el consumer llama a generar_respuesta() y no
# reimplementa la llamada a Ollama <<<
# Mismo patron que ya usa techo360-proyeccion (app/rabbitmq_consumer.py):
# el consumer es ahora el camino real de produccion, pero POST
# /chatbot/send (app/main.py) se mantiene para pruebas locales rapidas
# sin levantar RabbitMQ. Los dos caminos llaman a la MISMA funcion
# (app/ollama_client.generar_respuesta) para que no puedan divergir en
# modelo/system prompt/timeout -- solo cambia como se recibe la
# solicitud y como se entrega la respuesta.
#
# >>> AVISO -- este consumer YA NO llama a persistir_en_background <<<
# (cambio del 27-sep-2026, integracion real del ChatBot en
# techo360-frontend). Quien publica en esta cola ahora es
# techo360-backend/services/chatbot_rpc_client.py, que espera la
# respuesta por reply_to y persiste el intercambio el mismo
# sincronicamente (decision del 26-sep-2026 en
# techo360-backend/core/config.py: "el backend maneja TODA la
# persistencia") -- si este consumer tambien publicara el evento de
# persistencia, el intercambio quedaria duplicado en postgres-vector
# (una fila por el backend, otra por
# services/chatbot_persistencia_consumer.py). POST /chatbot/send
# (app/main.py) es distinto: no tiene un backend esperando la
# respuesta, asi que ese SI sigue llamando a persistir_en_background.


async def _procesar_mensaje(message: AbstractIncomingMessage, channel: AbstractChannel) -> None:
    async with message.process():
        try:
            payload = json.loads(message.body)
            mensaje = payload["mensaje"]
            usuario_id = payload["usuario_id"]
            consentimiento_entrenamiento = payload["consentimiento_entrenamiento"]
            respuesta_texto = await generar_respuesta(mensaje)
            respuesta = {"status": "ok", "response": respuesta_texto}
        except OllamaNoDisponibleError as error:
            # Sin este log, un timeout interno de generar_respuesta()
            # (TIMEOUT_OLLAMA_S=120s en app/ollama_client.py -- carga en
            # frio del modelo tras keep_alive de Ollama) es invisible en
            # 'docker logs': el mensaje queda ~80-180s sin ack y sin
            # rastro alguno, indistinguible de un consumer colgado
            # (confirmado real diagnosticando la integracion del ChatBot
            # en techo360-frontend, 27-sep-2026).
            logger.warning("Ollama no disponible al procesar mensaje: %s", error)
            respuesta = {"status": "error", "tipo": "ollama_no_disponible", "detail": str(error)}
        except (KeyError, json.JSONDecodeError) as error:
            respuesta = {"status": "error", "tipo": "payload_invalido", "detail": str(error)}
        except Exception as error:  # noqa: BLE001 -- limite del consumer, no debe tumbar el proceso
            logger.exception("Error inesperado generando la respuesta del chatbot")
            respuesta = {"status": "error", "tipo": "error_interno", "detail": str(error)}

        if not message.reply_to:
            logger.warning("Mensaje sin reply_to, no se puede responder: %s", message.correlation_id)
            return

        await channel.default_exchange.publish(
            Message(
                body=json.dumps(respuesta).encode(),
                content_type="application/json",
                correlation_id=message.correlation_id,
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=message.reply_to,
        )


async def iniciar_consumidor(rabbitmq_url: str) -> AbstractRobustConnection:
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()
    # prefetch_count=1, distinto del 4 de techo360-proyeccion: cada
    # mensaje aqui carga el modelo GGUF si Ollama no lo tiene ya en
    # memoria (~44s medido en T-95) y genera texto token a token -- un
    # solo worker de Ollama por instancia de chatbot, no tiene sentido
    # prefetch-ear varios mensajes que de todas formas se procesan uno
    # a la vez del lado de Ollama.
    await channel.set_qos(prefetch_count=1)

    # durable=True y con los mismos parametros que quien publique del
    # otro lado (backend o el pool de workers de los labs) -- si este
    # consumer arranca despues de que ya se publico, encuentra los
    # mensajes esperando en la cola en vez de perderlos.
    queue = await channel.declare_queue(REQUEST_QUEUE, durable=True)

    async def on_message(message: AbstractIncomingMessage) -> None:
        await _procesar_mensaje(message, channel)

    await queue.consume(on_message, arguments={"x-priority": CONSUMER_PRIORITY})
    logger.info("Consumidor de '%s' arrancado (x-priority=%d).", REQUEST_QUEUE, CONSUMER_PRIORITY)
    return connection
