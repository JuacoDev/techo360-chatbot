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

> **Actualizacion (SEGURIDAD, 09/10/2026):** `POST /chatbot/send` ya no existe en produccion (nginx no lo publica y el servicio solo lo registra con `CHATBOT_HABILITAR_SEND_LOCAL=1`, para la evaluacion local de `training/`). Cuando esta habilitado solo recibe `message` y **no persiste nada**. `/docs`, `/redoc` y `/openapi.json` solo existen con `CHATBOT_HABILITAR_DOCS=1`. Lo que sigue describe el contrato historico.

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

## Estado en producción (`development`, 5-oct-2026)

Estado de `development` (lo que corre en producción) hasta el SHA `e681b88`. La rama `Testing` está 14 commits por detrás de `development` (no incluye la migración 0002 ni D10 ni D11), por eso este README documenta `development`. Cada cambio se desplegó por separado y se revierte con `git revert -m 1 <SHA del merge>` y un nuevo deploy (push a `development`).

| Paso | PR | SHA del merge | SHA anterior | Qué cambia |
|---|---|---|---|---|
| Migración 0002 | #1 | `13c6bd1` | `c4cfc90` | Versiona la migración de estados de mensaje (solo archivos en `migrations/`). |
| D10 | #2 | `7cb4b28` | `13c6bd1` | `NUM_PREDICT = 400` y aviso cuando Ollama corta por longitud. |
| D11 | #3 | `e681b88` | `7cb4b28` | `NUM_THREAD = 3` en las opciones de Ollama. |

### Migración 0002 (`migrations/`)
- `0002_mensajes_estado.sql`: añade a `mensajes` las columnas `estado`, `error_detalle`, `actualizado_en` e `intentos`, tres restricciones y dos índices (uno único parcial: un mensaje de usuario sin resolver por conversación). Es **idempotente** (`IF NOT EXISTS`, restricciones protegidas por nombre), usa `lock_timeout` de 3 s y el backfill de los 6 mensajes antiguos sin respuesta solo ocurre la primera vez.
- `0002_mensajes_estado_down.sql` (reversa) y `verificar_0002_antes.sql` / `verificar_0002_despues.sql` (solo `SELECT`).
- Se aplicó **a mano** en el VPS el 5-oct, con respaldo previo y `psql -v ON_ERROR_STOP=1` (sin `-1`: el archivo trae su `BEGIN`/`COMMIT`). Fusionar el PR #1 **no ejecuta migraciones**: solo versiona los archivos, y como el `Dockerfile` copia únicamente `app/`, el contenedor no se recreó.
- Validada contra un PostgreSQL 16.4 desechable (41 comprobaciones). Reversa de la base: `0002_mensajes_estado_down.sql`, pero antes hay que apagar el interruptor del backend o revertir backend y frontend (el backend nuevo lee esas columnas).

### Ollama: opciones de la petición (`app/ollama_client.py`)
- `TIMEOUT_OLLAMA_S = 120.0` (constante): tiempo máximo que espera el chatbot a Ollama. El backend espera hasta 200 s por el RPC.
- `NUM_PREDICT = 400`: tope de tokens por respuesta (`options.num_predict`). Si Ollama corta por longitud (`done_reason = "length"`), el chatbot registra un `warning` con `eval_count` y el texto puede quedar a medias. Las respuestas reales hasta el 5-oct llegaron como máximo a ~250 tokens (1010 caracteres), así que el tope no se alcanzó.
- `NUM_THREAD` (`options.num_thread`) se lee de la variable de entorno `OLLAMA_NUM_THREAD` (entero ≥ 1; sin ella o con un valor inválido, 3 —el valor medido en producción—, con un `warning` si es inválido). En la VPS **no se ha cambiado**: subirlo (la medición local sugiere 4) se decide tras medirlo allí. Valor actual 3: debe igualar la cuota de CPU del contenedor de Ollama (`cpus: 3.0` en `techo360-infra`) y todas las peticiones deben usar el mismo valor (cambiar las opciones del runner puede recargar el modelo). Medición directa a Ollama con un prompt corto: 5,32 → 7,18 tokens/s. **No verificado** el efecto con respuestas reales por la app.
- El consumer de RabbitMQ usa `prefetch 1`: **atiende los mensajes en serie** (~46 s por mensaje antes de D11). Con 4 envíos simultáneos la última respuesta tardó 183,8 s (antes de D11), a ~16 s del tope de 200 s del backend; el quinto no se probó.
- Los workers de laboratorio reutilizan esta imagen; el tope y los hilos solo les aplican cuando reconstruyen desde el repo actualizado (no verificado qué hacen).

### Despliegue
Un push a `development` ejecuta `deploy-service.sh chatbot` (backup, build y recreación del contenedor). Si cambia `app/`, el contenedor se recrea y `chatbot_requests` queda ~3,1 s sin consumer (medido en D10 y D11). No verificado: el reencolado de un mensaje que esté en vuelo en ese momento (en ambos despliegues no había ninguno).

### Pruebas
**No hay pruebas automatizadas** en este repo. Solo existen un E2E manual (`scripts/probar_rabbitmq_local.py`) y el workflow manual `test-rabbitmq-rpc.yml` (`workflow_dispatch`). Las comprobaciones del 5-oct (compilación con `py_compile`, la petición a Ollama con un transporte simulado y las mediciones en el VPS) se hicieron fuera del repo.

### Problemas conocidos
- **COMPROBADO:** el texto técnico de `error_detalle` (por ejemplo, `No se pudo contactar a Ollama: Server disconnected without sending a response.`) llega tal cual al usuario en el mensaje en estado `error`.
- **Reportado, no verificado por mí:** el dataset de entrenamiento define mal el score de privación y el déficit habitacional (por ejemplo, el modelo describe el score como «número de indicadores con valor negativo», pero el cálculo real es el promedio de 3 componentes normalizados), y el modelo alucina en la consulta de Pelaya. Es un tema del dataset, no del despliegue.
