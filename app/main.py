import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.ollama_client import OllamaNoDisponibleError, generar_respuesta
from app.rabbitmq_consumer import iniciar_consumidor

# En produccion (docker-compose.yml de techo360-infra) esta variable ya
# se define -- el default de aqui es solo para correr localmente sin
# RabbitMQ (ver README de techo360-proyeccion, mismo patron).
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # T-96: el consumer de RabbitMQ es ahora el camino real de
    # produccion (pool de workers en los labs de la universidad); POST
    # /chatbot/send se mantiene abajo para pruebas locales rapidas sin
    # RabbitMQ, pero ya no es el camino principal.
    connection = await iniciar_consumidor(RABBITMQ_URL)
    yield
    await connection.close()


app = FastAPI(title="Techo 360 - Servicio IA Chatbot", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chatbot/send", response_model=ChatResponse)
async def chatbot_send(payload: ChatRequest):
    """Recibe un mensaje del usuario, lo envia a Ollama (API HTTP local)
    con el system prompt sincronizado, y devuelve la respuesta generada.

    T-96: se mantiene solo para pruebas locales rapidas sin levantar
    RabbitMQ -- el camino real de produccion es ahora el consumer de
    app/rabbitmq_consumer.py (cola 'chatbot_requests'), que llama a la
    misma logica compartida (app/ollama_client.generar_respuesta).
    """
    try:
        respuesta_texto = await generar_respuesta(payload.message)
    except OllamaNoDisponibleError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(response=respuesta_texto)


@app.get("/health")
def health():
    """Prueba de humo: confirma que el contenedor levanto correctamente."""
    return {"status": "ok", "service": "chatbot", "version": "ci-cd-test-1"}


# prueba CI/CD


# TODO: sigue pendiente:
#   RAG contra pgvector antes de llamar a Ollama (ver docstring de
#   app/ollama_client.generar_respuesta -- deliberadamente fuera del
#   alcance de T-95/T-96)
