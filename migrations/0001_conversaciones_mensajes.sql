-- ============================================================
-- NO EJECUTAR TODAVIA CONTRA PRODUCCION
-- ============================================================
-- Migracion versionada, disenada 25-sep-2026 -- cambio de esquema
-- pendiente de confirmacion explicita del usuario, por separado, y
-- NUNCA en paralelo con una carga de datos en curso en otra BD del
-- mismo VPS (ver techo360/CLAUDE.md, restricciones de infraestructura).
--
-- Destino: postgres-vector (DATABASE_VECTOR_URL) -- es la UNICA base a
-- la que techo360-chatbot ya tiene credenciales inyectadas por
-- docker-compose.yml (ver techo360-infra/docker-compose.yml, servicio
-- "chatbot": solo DATABASE_VECTOR_URL, RABBITMQ_URL, OLLAMA_URL -- no
-- DATABASE_URL de postgres-principal). No se crea una BD nueva para
-- esto ni se le pide a techo360-chatbot una credencial que hoy no
-- tiene.
--
-- >>> AVISO -- usuario_id NO tiene FK real <<<
-- Las cuentas (mapcaloruser) viven en postgres-users, una base DISTINTA
-- (Postgres no soporta FOREIGN KEY entre bases de datos separadas,
-- incluso en el mismo servidor). usuario_id se guarda como INTEGER
-- suelto, logicamente equivalente a mapcaloruser.id, pero sin
-- integridad referencial forzada por la BD -- cualquier validacion de
-- que el usuario_id exista debe hacerse en capa de aplicacion (backend),
-- no aqui.
--
-- >>> AVISO -- consentimiento_entrenamiento es un SNAPSHOT, no un JOIN <<<
-- "Heredado de cuenta" significa: se copia el valor de consentimiento
-- de la cuenta AL MOMENTO de crear la fila, no se recalcula despues.
-- Si el usuario cambia su consentimiento mas tarde, las conversaciones
-- ya existentes conservan el consentimiento que tenian cuando ocurrieron
-- -- necesario para poder auditar honestamente que datasets de
-- reentrenamiento pasados si tenian consentimiento real en su momento,
-- sin que un cambio posterior reescriba la historia.
--
-- NOTA: mapcaloruser (techo360-backend/models/mapcalor_user.py) HOY NO
-- tiene ninguna columna de consentimiento -- agregarla es un cambio
-- aparte en postgres-users/techo360-backend, fuera del alcance de esta
-- migracion (que es solo de techo360-chatbot/postgres-vector). Sin esa
-- columna en origen, la aplicacion no tiene de donde leer el valor a
-- copiar aqui todavia.
--
-- Ver tambien docs/politicas-uso-chatbot.md (mismo repo) para las
-- reglas de que datos entran al dataset de reentrenamiento.

CREATE TABLE IF NOT EXISTS conversaciones (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    consentimiento_entrenamiento BOOLEAN NOT NULL,
    fecha TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversaciones_usuario_id ON conversaciones (usuario_id);
CREATE INDEX IF NOT EXISTS idx_conversaciones_fecha ON conversaciones (fecha);

CREATE TABLE IF NOT EXISTS mensajes (
    id BIGSERIAL PRIMARY KEY,
    conversacion_id BIGINT NOT NULL REFERENCES conversaciones (id) ON DELETE CASCADE,
    rol TEXT NOT NULL CHECK (rol IN ('usuario', 'asistente')),
    contenido TEXT NOT NULL,
    -- NULL = sin feedback dado todavia; TRUE/FALSE = util/no util.
    -- Deliberadamente NO NOT NULL: la ausencia de feedback es un estado
    -- real y distinto de "no fue util", no un valor por defecto a
    -- inventar (mismo criterio de "sin_dato" ya usado en el resto del
    -- proyecto -- ver PanelIndicadores.jsx en techo360-frontend).
    feedback_util BOOLEAN,
    fecha TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion_id ON mensajes (conversacion_id);
