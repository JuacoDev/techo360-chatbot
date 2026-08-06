# techo360-chatbot

Servicio IA - Chatbot conversacional (LLM propio via Ollama + RAG sobre pgvector).

Parte de la arquitectura multi-repo de Techo 360. Se despliega desde
`techo360-infra` — ver ese repo para el `docker-compose.yml` completo.

## Desarrollo local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
