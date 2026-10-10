import asyncio
import json
import logging
import os
import time
import uuid
from collections import OrderedDict

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

# >>> Aviso de cancelacion (opcional, mejor esfuerzo) <<<
# Cancelar un mensaje en el backend NO detenia al asistente: la generacion (~46 s de CPU) seguia
# y su resultado se descartaba con un 409 (medido el 9-oct: 3 de 10 generaciones). Ahora el
# backend, ademas de marcar el mensaje 'cancelado', publica {"mensaje_id", "intento"} en este
# exchange fanout NO durable (mismo nombre y argumentos que techo360-backend,
# services/chatbot_rpc_client.EXCHANGE_CANCELACIONES). Cada consumer se enlaza con su propia
# cola exclusiva y, si el aviso corresponde a una generacion en curso, cancela la llamada a
# Ollama (httpx cierra la conexion); si llega antes de empezar, no genera.
# COMPATIBILIDAD: todo es opcional. Sin `mensaje_id`/`intento` en el payload (backend viejo) o
# sin aviso (backend con CHATBOT_AVISAR_CANCELACION=false) el consumer se comporta como siempre;
# una imagen vieja de este servicio ignora los campos nuevos y el exchange.
EXCHANGE_CANCELACIONES = "chatbot_cancelaciones"
# Cuanto se recuerda un aviso por si llega ANTES que el mensaje (cola ocupada): tope del RPC
# del backend (200 s) mas margen.
RECUERDO_CANCELACION_S = 600
MAX_CANCELACIONES_RECORDADAS = 500


class GeneracionCancelada(Exception):
    """El usuario cancelo este intento: no hace falta (seguir) generando."""


class _Cancelaciones:
    """Avisos de cancelacion recientes y generaciones en curso, por (mensaje_id, intento)."""

    def __init__(self) -> None:
        self._recientes: OrderedDict[tuple[int, int], float] = OrderedDict()
        self.activas: dict[tuple[int, int], asyncio.Future] = {}

    @staticmethod
    def clave(datos: object) -> tuple[int, int] | None:
        """(mensaje_id, intento) si ambos son enteros; None si falta alguno (payload viejo)."""
        if not isinstance(datos, dict):
            return None
        mensaje_id, intento = datos.get("mensaje_id"), datos.get("intento")
        if isinstance(mensaje_id, int) and isinstance(intento, int) and not isinstance(mensaje_id, bool) and not isinstance(intento, bool):
            return mensaje_id, intento
        return None

    def registrar(self, clave: tuple[int, int]) -> bool:
        """Recuerda el aviso y cancela la generacion en curso de ese intento. True si la cancelo."""
        self._recientes[clave] = time.monotonic()
        while len(self._recientes) > MAX_CANCELACIONES_RECORDADAS:
            self._recientes.popitem(last=False)
        tarea = self.activas.get(clave)
        if tarea is not None and not tarea.done():
            tarea.cancel()
            return True
        return False

    def fue_cancelado(self, clave: tuple[int, int]) -> bool:
        desde = self._recientes.get(clave)
        if desde is None:
            return False
        if time.monotonic() - desde > RECUERDO_CANCELACION_S:
            del self._recientes[clave]
            return False
        return True


_cancelaciones = _Cancelaciones()


async def _generar_cancelable(mensaje: str, clave: tuple[int, int] | None) -> str:
    """generar_respuesta(), cancelable por un aviso del backend. Sin `clave` (payload viejo),
    exactamente lo de siempre."""
    if clave is None:
        return await generar_respuesta(mensaje)
    if _cancelaciones.fue_cancelado(clave):
        raise GeneracionCancelada()
    tarea = asyncio.ensure_future(generar_respuesta(mensaje))
    _cancelaciones.activas[clave] = tarea
    try:
        return await tarea
    except asyncio.CancelledError:
        if tarea.cancelled() and _cancelaciones.fue_cancelado(clave):
            raise GeneracionCancelada() from None
        tarea.cancel()  # cancelacion del propio consumer (apagado): no se deja huerfana la llamada
        raise
    finally:
        _cancelaciones.activas.pop(clave, None)


async def _on_aviso_cancelacion(message: AbstractIncomingMessage) -> None:
    try:
        clave = _Cancelaciones.clave(json.loads(message.body))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return
    if clave is not None and _cancelaciones.registrar(clave):
        logger.info("Generacion abortada por cancelacion (mensaje %s, intento %s).", *clave)

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
            respuesta_texto = await _generar_cancelable(mensaje, _Cancelaciones.clave(payload))
            respuesta = {"status": "ok", "response": respuesta_texto}
        except GeneracionCancelada:
            # El backend ya marco el mensaje 'cancelado': esta respuesta solo sirve para que su
            # RPC termine pronto (la descarta con 409) en vez de esperar al timeout.
            respuesta = {"status": "error", "tipo": "cancelado", "detail": "Mensaje cancelado; no se genero respuesta."}
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


# >>> AVISO -- causa raiz CONFIRMADA por codigo + log real (28-sep-2026) <<<
# Sintoma real observado (worker de laboratorio de un teammate,
# 27-sep-2026): el consumer arrancaba bien (x-priority=10, log de
# arranque visible), procesaba una peticion, y tras una caida de red
# real (Tailscale inestable en esa maquina, "[Errno 111] Connection
# refused" en el log) se reconectaba -- confirmado "running" en la API
# de management de RabbitMQ -- pero con consumer_count=0 permanente,
# sin ninguna excepcion ni log de error.
#
# Mecanismo exacto (aio_pika==9.4.3, aio_pika/robust_connection.py):
# RobustConnection guarda sus canales en un WeakSet
# (`self.__channels: WeakSet[...]`). Tras reconectar, `_on_connected()`
# hace `for channel in tuple(self.__channels): await channel.restore()`
# -- si nada retenia una referencia FUERTE al channel, el recolector de
# basura de Python pudo liberarlo entretanto, el WeakSet ya no lo
# contiene, y ese `for` simplemente itera sobre CERO canales: ninguna
# excepcion, ningun log, la reconexion "funciona" pero no restaura
# nada. Un primer intento de reproducirlo con un cierre limpio via API
# de management (5 ciclos, sin exito) no lo disparo -- consistente con
# que hace falta que el recolector de basura realmente ejecute sobre
# ese ciclo de referencias, no solo que la conexion se caiga.
#
# _CHANNELS_VIVOS elimina la condicion necesaria para el bug (retiene
# la referencia fuerte mientras dure el proceso, asi el WeakSet nunca
# puede perder el channel).
_CHANNELS_VIVOS: list = []

# Mismo problema, un nivel mas abajo: RobustChannel._queues es un
# defaultdict(WeakSet) (aio_pika/robust_channel.py), y _on_open() restaura
# tras reconectar SOLO las colas que siguen vivas ahi. `queue` es local de
# iniciar_consumidor(); sin otra referencia fuerte el WeakSet queda vacio, el
# canal se reabre pero no re-declara la cola ni re-registra el consumer
# (consumer_count=0, sin excepcion ni log). Reproducido en local con aio-pika
# 9.4.3: recreate de RabbitMQ (cola ausente) y docker restart (cola presente
# sin consumer). Retener la cola (con su canal arriba) lo evita (T-126).
_QUEUES_VIVAS: list = []


async def _suscribir_avisos_cancelacion(connection: AbstractRobustConnection) -> None:
    """Cola exclusiva propia enlazada al exchange de avisos, en un canal aparte (el prefetch 1
    del canal de trabajo no debe retrasar un aviso). Si algo falla, el consumer sigue como
    siempre: cancelar solo dejaria de abortar la generacion."""
    try:
        canal = await connection.channel()
        _CHANNELS_VIVOS.append(canal)
        exchange = await canal.declare_exchange(EXCHANGE_CANCELACIONES, aio_pika.ExchangeType.FANOUT, durable=False)
        # Nombre explicito (no el generado por el servidor): aio-pika puede re-declararla tal cual
        # al reconectar. Solo se conservan avisos recientes (x-message-ttl).
        cola = await canal.declare_queue(
            f"{EXCHANGE_CANCELACIONES}.{uuid.uuid4().hex}",
            exclusive=True,
            auto_delete=True,
            arguments={"x-message-ttl": RECUERDO_CANCELACION_S * 1000},
        )
        _QUEUES_VIVAS.append(cola)
        await cola.bind(exchange)
        await cola.consume(_on_aviso_cancelacion, no_ack=True)
        logger.info("Suscrito a los avisos de cancelacion ('%s').", EXCHANGE_CANCELACIONES)
    except Exception:  # noqa: BLE001 -- opcional: nunca debe impedir que el consumer arranque
        logger.warning("No se pudo suscribir a los avisos de cancelacion; cancelar no abortara la generacion.", exc_info=True)


async def iniciar_consumidor(rabbitmq_url: str) -> AbstractRobustConnection:
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()
    _CHANNELS_VIVOS.append(channel)
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
    _QUEUES_VIVAS.append(queue)

    async def on_message(message: AbstractIncomingMessage) -> None:
        await _procesar_mensaje(message, channel)

    await queue.consume(on_message, arguments={"x-priority": CONSUMER_PRIORITY})
    logger.info("Consumidor de '%s' arrancado (x-priority=%d).", REQUEST_QUEUE, CONSUMER_PRIORITY)
    await _suscribir_avisos_cancelacion(connection)
    return connection
