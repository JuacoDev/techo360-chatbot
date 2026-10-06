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

## Contrato de entrada (T-97, 26/09)

Tanto `POST /chatbot/send` como el consumer de RabbitMQ (cola
`chatbot_requests`) requieren, ademas del mensaje, `usuario_id` (int) y
`consentimiento_entrenamiento` (bool) — este servicio no tiene
credenciales para consultar `mapcaloruser` (vive en `postgres-users`,
otra base), asi que quien llame (backend / pool de workers de los labs)
debe resolver ambos valores antes de publicar. Cada intercambio exitoso
se persiste (best effort, no bloquea la respuesta) como una fila nueva
en `conversaciones` + 2 en `mensajes` (`app/persistencia.py`) — ver
`docs/politicas-uso-chatbot.md` para las reglas de uso de esos datos.

## Aplicar la migracion 0001 (conversaciones/mensajes) en el VPS

Aprobada para producción (26/09). Solo crea las 2 tablas nuevas — no
migra datos existentes, es segura de re-ejecutar (`CREATE TABLE IF NOT
EXISTS`). No correrla en paralelo con otra carga de datos en curso en
otra BD del mismo VPS (ver `techo360/CLAUDE.md`).

```bash
# Desde una maquina con acceso SSH al VPS:
scp migrations/0001_conversaciones_mensajes.sql <host>:/tmp/
ssh <host> 'docker exec -i techo360-postgres-vector psql -U "$DB_VECTOR_USER" -d "$DB_VECTOR_NAME" < /tmp/0001_conversaciones_mensajes.sql'

# Verificar:
ssh <host> 'docker exec -i techo360-postgres-vector psql -U "$DB_VECTOR_USER" -d "$DB_VECTOR_NAME" -c "\dt conversaciones; \dt mensajes;"'
```
