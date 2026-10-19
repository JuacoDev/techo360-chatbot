# techo360-chatbot

## Resumen

Servicio de chatbot conversacional de Techo 360.
Ejecuta un modelo local mediante Ollama.
Consume solicitudes RPC por RabbitMQ.
Persiste conversaciones y mensajes en PostgreSQL con pgvector.
Incluye RAG, evaluacion y scripts de entrenamiento fuera del contenedor.

## Uso local

```bash
pip install -r requirements.txt
CHATBOT_HABILITAR_SEND_LOCAL=0 CHATBOT_HABILITAR_DOCS=0 uvicorn app.main:app --reload
```

El consumer necesita RabbitMQ, Ollama y las bases configuradas para probar el
flujo completo. Las rutas auxiliares y la documentacion HTTP estan apagadas
por defecto.

## Variables de entorno

| Nombre | Para que sirve | Valor por defecto |
|---|---|---|
| `OLLAMA_URL` | Endpoint de Ollama | local; TODO: verificar literal |
| `OLLAMA_MODEL` | Modelo servido | `techo360-chatbot:v3.2` |
| `OLLAMA_NUM_THREAD` | Hilos de Ollama | `3` |
| `RABBITMQ_URL` | Broker RPC | TODO: verificar en compose |
| `CHATBOT_HABILITAR_SEND_LOCAL` | Habilita `/chatbot/send` local | apagado |
| `CHATBOT_HABILITAR_DOCS` | Habilita docs OpenAPI | apagado |
| `CHATBOT_CONSUMER_PRIORITY` | Prioridad del consumer | TODO: verificar |
| `RPC_TIMEOUT_SECONDS` | Tope del RPC | TODO: verificar |

No se incluyen contrasenas, tokens, claves ni valores de `.env`.

## Pruebas

Este repositorio no contiene una suite automatizada comprobada. El E2E local
disponible es:

```bash
python scripts/probar_rabbitmq_local.py
```

Tambien existe el workflow manual `test-rabbitmq-rpc.yml`. `TODO`: agregar y
ejecutar una suite automatizada reproducible para el servicio.

## Estructura

`app/` servicio; `migrations/` SQL; `dataset/` datos; `training/` scripts y
artefactos de entrenamiento; `prompts/` prompts referenciados; `scripts/`
pruebas y utilidades; `training/ollama/` Modelfiles.

## Banderas del chatbot

`CHATBOT_HABILITAR_SEND_LOCAL=0` y `CHATBOT_HABILITAR_DOCS=0` estan apagadas
por defecto. No se debe publicar `/chatbot/send` ni `/docs` en produccion.

## Versiones de modelo y system prompt

| Version | Modelo | System | Estado |
|---|---|---|---|
| `0.4.0` | `techo360-chatbot:0.4.0` | `sp-0.4.0-1` | produccion |
| `0.4.1` | `techo360-chatbot:0.4.1` | `sp-0.4.1-1` | entrenamiento |

`TODO`: verificar en los artefactos desplegados el nombre exacto de la imagen
0.4.0; el system y el estado anterior estan documentados por los commits/PRs.

## Reproducir entrenamiento

Para 0.4.0, el script es `training/entrenar_lora_v040.py` y la semilla por
defecto es `42`. Los parametros comprobables son longitud maxima `2048`,
micro-batch `1`, acumulacion `8`, `3` epocas, learning rate `2e-4`, scheduler
lineal sin warmup, `PagedAdamW8bit`, LoRA `r=16`, `alpha=32`, dropout `0.05`,
checkpoint cada `200` pasos y limite declarado de VRAM `5900 MB`. El modelo
base declarado es `meta-llama/Llama-3.2-3B-Instruct`.

```bash
python -u training/entrenar_lora_v040.py \
	--dataset <train_tokenizado.jsonl> \
	--salida training/adapters/techo360-v0.4.0
```

El script comprueba el SHA-256 esperado del dataset antes de entrenar. Las
opciones `--humo`, `--reanudar`, `--equivalencia`, `--guardar-cada`,
`--limite-vram-mb` y `--segundos-max-step` estan definidas en el script.
`TODO`: registrar la ruta concreta del dataset usado y el comando completo de
0.4.1. El directorio
`training/adapters/techo360-v0.4.0/` no esta rastreado en la base de esta rama.

## Documentacion de fases

[techo360-claude](https://github.com/JuacoDev/techo360-claude)

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

### Aviso de cancelación (opcional)
Si el payload trae `mensaje_id` e `intento` y el backend publica un aviso en el exchange fanout `chatbot_cancelaciones` (cuerpo `{"mensaje_id", "intento"}`), el consumer aborta la llamada a Ollama de ese intento (o no la inicia si el aviso llegó antes) y responde `{"status": "error", "tipo": "cancelado"}`, que el backend descarta con su 409 habitual. Sin esos campos o sin aviso, todo funciona como siempre; una imagen vieja ignora ambos. Cada consumer (VPS y workers) usa su propia cola exclusiva `chatbot_cancelaciones.<uuid>`. **No verificado:** que Ollama detenga su cálculo al cerrarse la conexión (hay que medirlo en la VPS).

### Despliegue
Un push a `development` ejecuta `deploy-service.sh chatbot` (backup, build y recreación del contenedor). Si cambia `app/`, el contenedor se recrea y `chatbot_requests` queda ~3,1 s sin consumer (medido en D10 y D11). No verificado: el reencolado de un mensaje que esté en vuelo en ese momento (en ambos despliegues no había ninguno).

### Pruebas
**No hay pruebas automatizadas** en este repo. Solo existen un E2E manual (`scripts/probar_rabbitmq_local.py`) y el workflow manual `test-rabbitmq-rpc.yml` (`workflow_dispatch`). Las comprobaciones del 5-oct (compilación con `py_compile`, la petición a Ollama con un transporte simulado y las mediciones en el VPS) se hicieron fuera del repo.

### Problemas conocidos
- **COMPROBADO:** el texto técnico de `error_detalle` (por ejemplo, `No se pudo contactar a Ollama: Server disconnected without sending a response.`) llega tal cual al usuario en el mensaje en estado `error`.
- **Reportado, no verificado por mí:** el dataset de entrenamiento define mal el score de privación y el déficit habitacional (por ejemplo, el modelo describe el score como «número de indicadores con valor negativo», pero el cálculo real es el promedio de 3 componentes normalizados), y el modelo alucina en la consulta de Pelaya. Es un tema del dataset, no del despliegue.
