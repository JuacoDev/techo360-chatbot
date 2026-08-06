from fastapi import FastAPI

app = FastAPI(title="Techo 360 - Servicio IA Chatbot")


@app.get("/health")
def health():
    """Prueba de humo: confirma que el contenedor levanto correctamente."""
    return {"status": "ok", "service": "chatbot"}


# prueba CI/CD


# TODO: aqui van los endpoints reales:
#   POST /chatbot/send  (recibe pregunta, hace RAG contra pgvector,
#                         llama a Ollama, devuelve respuesta)
#   consumidor de RabbitMQ para tareas largas (proyecciones, PDFs)
