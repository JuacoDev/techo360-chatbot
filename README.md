# techo360-chatbot

Servicio IA - Chatbot conversacional (LLM propio via Ollama + RAG sobre pgvector).

Parte de la arquitectura multi-repo de Techo 360. Se despliega desde
`techo360-infra` — ver ese repo para el `docker-compose.yml` completo.

## Desarrollo local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Fine-tuning (Llama 3.2 LoRA/QLoRA)

Proceso y estado documentados en [`training/`](training/); dataset de
entrenamiento en [`dataset/`](dataset/). El entrenamiento corre localmente
(no en este servicio ni en el VPS).
