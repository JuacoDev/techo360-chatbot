"""Arranca el servicio REAL del chatbot (app/main.py) sin RabbitMQ, solo para evaluar (T-124).

El lifespan de app/main.py conecta un consumer a RabbitMQ y POST /chatbot/send publica un evento de persistencia (best effort). Para medir el modelo
no hace falta ninguno de los dos, asi que se reemplazan por no-op; el endpoint /chatbot/send, el system prompt y las opciones de
app/ollama_client.py son EXACTAMENTE los de produccion.

Uso: OLLAMA_MODEL=techo360-chatbot:v3.2 python training/servicio_eval_sin_rabbitmq.py <puerto>
"""
import contextlib
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import uvicorn  # noqa: E402

# POST /chatbot/send ya no se registra salvo con esta variable (SEGURIDAD, ver app/main.py).
os.environ.setdefault("CHATBOT_HABILITAR_SEND_LOCAL", "1")

import app.main as principal  # noqa: E402


@contextlib.asynccontextmanager
async def _sin_rabbitmq(_app):
    yield


principal.app.router.lifespan_context = _sin_rabbitmq

if __name__ == "__main__":
    uvicorn.run(principal.app, host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")
