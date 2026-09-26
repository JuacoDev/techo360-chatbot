import asyncio
import logging
import os

import psycopg2

logger = logging.getLogger(__name__)

# En produccion (docker-compose.yml de techo360-infra) esta variable ya
# se define -- ver AVISO en migrations/0001_conversaciones_mensajes.sql
# sobre por que es la UNICA base a la que este servicio tiene
# credenciales (postgres-vector, no postgres-principal/postgres-users).
DATABASE_VECTOR_URL = os.environ.get(
    "DATABASE_VECTOR_URL", "postgresql://localhost:5432/techo360_vector"
)


def persistir_intercambio(
    usuario_id: int,
    consentimiento_entrenamiento: bool,
    mensaje_usuario: str,
    respuesta_asistente: str,
) -> None:
    """Guarda un intercambio completo (1 conversacion + 2 mensajes) en
    conversaciones/mensajes (postgres-vector).

    Cada llamada a generar_respuesta() es independiente -- sin historial
    multi-turno (ver docstring de app/ollama_client.generar_respuesta) --
    por eso cada intercambio crea su propia fila en `conversaciones` en
    vez de reutilizar una existente. Cuando el servicio implemente
    multi-turno, esta funcion debera recibir un conversacion_id opcional
    en vez de crear uno nuevo siempre.

    usuario_id y consentimiento_entrenamiento llegan ya resueltos por
    quien llama (el backend, que si tiene acceso a mapcaloruser en
    postgres-users) -- este servicio nunca consulta esa tabla
    directamente (ver AVISO en la migracion).

    Deliberadamente "best effort": un fallo al persistir NO debe tumbar
    ni invalidar la respuesta que Ollama ya genero -- perder la fila de
    historial es preferible a perder la respuesta en si. Se loguea como
    error para que quede visible en monitoreo, nunca se relanza.
    """
    try:
        # connect_timeout corto (5s) -- esto corre en un thread aparte
        # (ver app/main.py y app/rabbitmq_consumer.py), pero sin timeout
        # un postgres-vector lento/caido dejaria el thread colgado
        # indefinidamente, agotando de a poco el pool de threads de
        # asyncio.to_thread() aunque cada fallo individual sea
        # "best effort" y nunca tumbe una respuesta.
        conn = psycopg2.connect(DATABASE_VECTOR_URL, connect_timeout=5)
    except Exception:
        logger.exception("No se pudo conectar a postgres-vector para persistir la conversacion")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO conversaciones (usuario_id, consentimiento_entrenamiento) "
                    "VALUES (%s, %s) RETURNING id",
                    (usuario_id, consentimiento_entrenamiento),
                )
                conversacion_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO mensajes (conversacion_id, rol, contenido) "
                    "VALUES (%s, 'usuario', %s)",
                    (conversacion_id, mensaje_usuario),
                )
                cur.execute(
                    "INSERT INTO mensajes (conversacion_id, rol, contenido) "
                    "VALUES (%s, 'asistente', %s)",
                    (conversacion_id, respuesta_asistente),
                )
    except Exception:
        logger.exception("No se pudo persistir la conversacion/mensajes en postgres-vector")
    finally:
        conn.close()


# T-97: asyncio.create_task() NO retiene una referencia fuerte a la tarea
# -- el garbage collector puede recolectarla a mitad de ejecucion sin
# avisar (gotcha documentado de asyncio, no una hipotesis). Este set
# guarda la referencia mientras la tarea de persistencia corre, y el
# callback la quita sola al terminar (exito o error, ya logueado dentro
# de persistir_intercambio arriba). Centralizado aqui porque tanto
# app/main.py como app/rabbitmq_consumer.py necesitan exactamente el
# mismo patron -- duplicarlo en los dos lugares invitaria a que uno se
# actualice y el otro no.
_tareas_persistencia: set[asyncio.Task] = set()


def persistir_en_background(
    usuario_id: int,
    consentimiento_entrenamiento: bool,
    mensaje_usuario: str,
    respuesta_asistente: str,
) -> None:
    """Lanza persistir_intercambio() en un thread aparte (psycopg2 es
    sincrono/bloqueante) sin esperar a que termine ni poder tumbar al
    llamador -- ver docstring de persistir_intercambio."""
    tarea = asyncio.create_task(
        asyncio.to_thread(
            persistir_intercambio, usuario_id, consentimiento_entrenamiento, mensaje_usuario, respuesta_asistente
        )
    )
    _tareas_persistencia.add(tarea)
    tarea.add_done_callback(_tareas_persistencia.discard)
