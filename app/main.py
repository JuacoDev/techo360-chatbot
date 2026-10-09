import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.ollama_client import OllamaNoDisponibleError, generar_respuesta
from app.rabbitmq_consumer import iniciar_consumidor

# Sin esto, logger.info() de app/rabbitmq_consumer.py y app/persistencia.py
# nunca aparecia en 'docker logs' (el logging estandar de Python no tiene
# handler configurado por defecto; Uvicorn configura SUS propios loggers,
# no el root) -- confirmado real al validar el primer worker de
# techo360-workers (27-sep-2026): la conexion/consumo si funcionaba, pero
# no habia forma de verlo en el log para confirmarlo sin mirar RabbitMQ
# directamente.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

# En produccion (docker-compose.yml de techo360-infra) esta variable ya
# se define -- el default de aqui es solo para correr localmente sin
# RabbitMQ (ver README de techo360-proyeccion, mismo patron).
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

# SEGURIDAD: POST /chatbot/send NO se registra en produccion. Estaba publicado por
# nginx sin sesion ni limite y confiaba en usuario_id/conversacion_id del cuerpo
# (inyectaba mensajes en conversaciones ajenas via el evento de persistencia y
# cargaba Ollama). El camino real es el consumer de RabbitMQ (backend -> RPC).
# Solo existe si CHATBOT_HABILITAR_SEND_LOCAL=1, para la evaluacion local
# (training/servicio_eval_sin_rabbitmq.py, en 127.0.0.1), y aun asi NO persiste
# nada: ya no recibe ni usa usuario_id ni conversacion_id.
HABILITAR_SEND_LOCAL = os.environ.get("CHATBOT_HABILITAR_SEND_LOCAL") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # T-96: el consumer de RabbitMQ es ahora el camino real de
    # produccion (pool de workers en los labs de la universidad); POST
    # /chatbot/send se mantiene abajo para pruebas locales rapidas sin
    # RabbitMQ, pero ya no es el camino principal.
    connection = await iniciar_consumidor(RABBITMQ_URL)
    yield
    await connection.close()


# SEGURIDAD: sin /docs, /redoc ni /openapi.json salvo CHATBOT_HABILITAR_DOCS=1 (desarrollo).
_DOCS = os.environ.get("CHATBOT_HABILITAR_DOCS") == "1"
app = FastAPI(
    title="Techo 360 - Servicio IA Chatbot",
    lifespan=lifespan,
    docs_url="/docs" if _DOCS else None,
    redoc_url="/redoc" if _DOCS else None,
    openapi_url="/openapi.json" if _DOCS else None,
)


class ChatRequest(BaseModel):
    # Solo el texto. Los campos viejos (usuario_id, consentimiento_entrenamiento,
    # conversacion_id) se ignoran si llegan: este endpoint ya no persiste.
    message: str


class ChatResponse(BaseModel):
    response: str


async def chatbot_send(payload: ChatRequest):
    """Solo evaluacion local (CHATBOT_HABILITAR_SEND_LOCAL=1): envia el mensaje a
    Ollama con el system prompt y las opciones de produccion y devuelve la
    respuesta. No persiste nada (SEGURIDAD, ver HABILITAR_SEND_LOCAL arriba)."""
    try:
        respuesta_texto = await generar_respuesta(payload.message)
    except OllamaNoDisponibleError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatResponse(response=respuesta_texto)


if HABILITAR_SEND_LOCAL:
    app.add_api_route("/chatbot/send", chatbot_send, methods=["POST"], response_model=ChatResponse)


@app.get("/health")
def health():
    """Prueba de humo: confirma que el contenedor levanto correctamente."""
    return {"status": "ok", "service": "chatbot", "version": "ci-cd-test-1"}


# prueba CI/CD


# TODO: sigue pendiente:
#   RAG contra pgvector antes de llamar a Ollama (ver docstring de
#   app/ollama_client.generar_respuesta -- deliberadamente fuera del
#   alcance de T-95/T-96)
