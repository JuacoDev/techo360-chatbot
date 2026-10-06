"""Script de una sola corrida para verificar end-to-end, en local, que
el consumer de app/rabbitmq_consumer.py (cola 'chatbot_requests')
responde correctamente por reply_to/correlation_id -- mismo patron RPC
que services/proyeccion_rpc_client.py en techo360-backend, pero como
script standalone en vez de cliente de servicio (aqui no hay un backend
del otro lado todavia, solo se quiere probar el consumer).

Requiere, corriendo en paralelo:
  1. Un RabbitMQ accesible en RABBITMQ_URL (default: amqp://guest:guest@localhost:5672/)
  2. Ollama accesible en OLLAMA_URL con el modelo techo360-chatbot:v3.2 cargado
  3. El servicio del chatbot corriendo (python -m uvicorn app.main:app),
     que es quien arranca el consumer via el lifespan de FastAPI

Uso:
    python scripts/probar_rabbitmq_local.py "Que es el Score de Privacion?"
"""
import asyncio
import json
import os
import sys
import uuid

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractIncomingMessage

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
REQUEST_QUEUE = "chatbot_requests"
# Configurable -- el default (15s) alcanza con el modelo ya cargado en
# memoria, pero la primera peticion tras (re)iniciar Ollama incluye
# cargar el GGUF (~44s medido en T-95, ver docstring de
# app/ollama_client.py). Subir con RPC_TIMEOUT_SECONDS=90 al validar un
# worker recien arrancado (techo360-workers).
RPC_TIMEOUT_SECONDS = float(os.environ.get("RPC_TIMEOUT_SECONDS", "15.0"))


async def probar(mensaje: str) -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    correlation_id = str(uuid.uuid4())
    future: asyncio.Future[dict] = asyncio.get_running_loop().create_future()

    channel = await connection.channel()
    try:
        await channel.declare_queue(REQUEST_QUEUE, durable=True)
        reply_queue = await channel.declare_queue(exclusive=True)

        async def on_reply(message: AbstractIncomingMessage) -> None:
            async with message.process():
                if message.correlation_id == correlation_id and not future.done():
                    future.set_result(json.loads(message.body))

        consumer_tag = await reply_queue.consume(on_reply)

        print(f"Publicando en '{REQUEST_QUEUE}': {mensaje!r} (correlation_id={correlation_id})")
        await channel.default_exchange.publish(
            Message(
                # usuario_id/consentimiento_entrenamiento: contrato T-97
                # (ver docstring de app/rabbitmq_consumer.py) -- sin estos
                # dos campos el consumer responde "payload_invalido" antes
                # de siquiera llamar a Ollama. Valores fijos de prueba:
                # usuario_id=0 no corresponde a un usuario real, por eso
                # consentimiento_entrenamiento=False (no se persiste como
                # si fuera de un usuario real).
                body=json.dumps({
                    "mensaje": mensaje,
                    "usuario_id": 0,
                    "consentimiento_entrenamiento": False,
                }).encode(),
                content_type="application/json",
                correlation_id=correlation_id,
                reply_to=reply_queue.name,
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=REQUEST_QUEUE,
        )

        try:
            respuesta = await asyncio.wait_for(future, timeout=RPC_TIMEOUT_SECONDS)
            print(f"\nRespuesta recibida:\n{json.dumps(respuesta, ensure_ascii=False, indent=2)}")
        except asyncio.TimeoutError:
            print(f"\nTIMEOUT: el consumer no respondio en {RPC_TIMEOUT_SECONDS}s. "
                  f"Verifica que el servicio del chatbot este corriendo (arranca el consumer via lifespan).")
            sys.exit(1)
        finally:
            await reply_queue.cancel(consumer_tag)
            await reply_queue.delete()
    finally:
        await channel.close()
        await connection.close()


if __name__ == "__main__":
    mensaje = sys.argv[1] if len(sys.argv) > 1 else "Que es el Score de Privacion?"
    asyncio.run(probar(mensaje))
