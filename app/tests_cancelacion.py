"""Pruebas del aviso de cancelacion en app/rabbitmq_consumer.py, sin RabbitMQ ni Ollama
(generar_respuesta y el canal son dobles).

Uso:
    python -m unittest app.tests_cancelacion
"""
import asyncio
import json
import unittest
from unittest.mock import patch

from app import rabbitmq_consumer as consumer


class MensajeFalso:
    """Doble de AbstractIncomingMessage: solo lo que usa _procesar_mensaje."""

    def __init__(self, cuerpo: dict, reply_to: str | None = "cola-respuesta"):
        self.body = json.dumps(cuerpo).encode()
        self.reply_to = reply_to
        self.correlation_id = "corr-1"
        self.procesado = False

    def process(self):
        mensaje = self

        class _Ctx:
            async def __aenter__(self):
                return mensaje

            async def __aexit__(self, *args):
                mensaje.procesado = True
                return False

        return _Ctx()


class CanalFalso:
    def __init__(self):
        self.publicados = []
        canal = self

        class _Exchange:
            async def publish(self, mensaje, routing_key=None):
                canal.publicados.append(json.loads(mensaje.body))

        self.default_exchange = _Exchange()


def _payload(**extra):
    return {"mensaje": "hola", "usuario_id": 7, "consentimiento_entrenamiento": False, "conversacion_id": 1, **extra}


class Base(unittest.TestCase):
    def setUp(self):
        consumer._cancelaciones = consumer._Cancelaciones()
        self.generaciones = 0  # cuantas veces se llamo a Ollama (generar_respuesta)
        self.canal = CanalFalso()

    async def _procesar(self, payload, generar):
        async def generar_falso(mensaje):
            self.generaciones += 1
            return await generar(mensaje)

        with patch.object(consumer, "generar_respuesta", generar_falso):
            await consumer._procesar_mensaje(MensajeFalso(payload), self.canal)

    async def _aviso(self, mensaje_id, intento):
        await consumer._on_aviso_cancelacion(MensajeFalso({"mensaje_id": mensaje_id, "intento": intento}))


class TestCompatibilidad(Base):
    def test_payload_viejo_sin_ids_genera_como_siempre(self):
        async def generar(mensaje):
            return "respuesta"

        asyncio.run(self._procesar(_payload(), generar))
        self.assertEqual(self.generaciones, 1)
        self.assertEqual(self.canal.publicados, [{"status": "ok", "response": "respuesta"}])

    def test_ids_invalidos_se_tratan_como_payload_viejo(self):
        for extra in ({"mensaje_id": "5", "intento": 1}, {"mensaje_id": 5}, {"mensaje_id": True, "intento": 1}, {"intento": 2}):
            with self.subTest(extra=extra):
                self.setUp()

                async def generar(mensaje):
                    return "ok"

                asyncio.run(self._procesar(_payload(**extra), generar))
                self.assertEqual(self.generaciones, 1)

    def test_aviso_mal_formado_se_ignora(self):
        mensaje = MensajeFalso({})
        mensaje.body = b"no es json"
        asyncio.run(consumer._on_aviso_cancelacion(mensaje))
        asyncio.run(consumer._on_aviso_cancelacion(MensajeFalso({"mensaje_id": "x"})))
        self.assertFalse(consumer._cancelaciones.fue_cancelado((5, 1)))


class TestCancelarAntesDeGenerar(Base):
    def test_aviso_previo_evita_la_generacion_y_responde_cancelado(self):
        async def generar(mensaje):
            raise AssertionError("no debia llamar a Ollama")

        async def caso():
            await self._aviso(5, 1)
            await self._procesar(_payload(mensaje_id=5, intento=1), generar)

        asyncio.run(caso())
        self.assertEqual(self.generaciones, 0)
        self.assertEqual(self.canal.publicados[0]["status"], "error")
        self.assertEqual(self.canal.publicados[0]["tipo"], "cancelado")

    def test_el_mensaje_se_confirma_aunque_se_cancele(self):
        mensaje = MensajeFalso(_payload(mensaje_id=5, intento=1))

        async def caso():
            await self._aviso(5, 1)
            await consumer._procesar_mensaje(mensaje, self.canal)

        asyncio.run(caso())
        self.assertTrue(mensaje.procesado)  # salio del `async with message.process()` sin error: se hace ack

    def test_el_aviso_caduca(self):
        async def caso():
            await self._aviso(5, 1)
            with patch.object(consumer, "RECUERDO_CANCELACION_S", -1):
                self.assertFalse(consumer._cancelaciones.fue_cancelado((5, 1)))

        asyncio.run(caso())

    def test_los_avisos_recordados_tienen_tope(self):
        """Un aviso que llega antes que su mensaje se recuerda, pero la memoria esta acotada."""
        for n in range(consumer.MAX_CANCELACIONES_RECORDADAS + 100):
            consumer._cancelaciones.registrar((n, 1))
        self.assertEqual(len(consumer._cancelaciones._recientes), consumer.MAX_CANCELACIONES_RECORDADAS)
        self.assertFalse(consumer._cancelaciones.fue_cancelado((0, 1)))  # el mas viejo se descarto
        self.assertTrue(consumer._cancelaciones.fue_cancelado((consumer.MAX_CANCELACIONES_RECORDADAS + 99, 1)))


class TestCancelarDuranteLaGeneracion(Base):
    def test_el_aviso_aborta_la_llamada_a_ollama(self):
        estado = {"cancelada": False, "iniciada": asyncio.Event}

        async def generar(mensaje):
            estado["evento"].set()
            try:
                await asyncio.sleep(30)  # "generando"
            except asyncio.CancelledError:
                estado["cancelada"] = True  # httpx cerraria aqui la conexion con Ollama
                raise
            return "tarde"

        async def caso():
            estado["evento"] = asyncio.Event()
            trabajo = asyncio.ensure_future(self._procesar(_payload(mensaje_id=5, intento=1), generar))
            await estado["evento"].wait()
            await self._aviso(5, 1)
            await asyncio.wait_for(trabajo, timeout=5)

        asyncio.run(caso())
        self.assertTrue(estado["cancelada"])
        self.assertEqual(self.canal.publicados[0]["tipo"], "cancelado")
        self.assertEqual(consumer._cancelaciones.activas, {})  # no deja la generacion registrada

    def test_aviso_de_otro_mensaje_o_intento_no_toca_esta_generacion(self):
        async def generar(mensaje):
            await asyncio.sleep(0.05)
            return "ok"

        async def caso():
            trabajo = asyncio.ensure_future(self._procesar(_payload(mensaje_id=5, intento=2), generar))
            await asyncio.sleep(0.01)
            await self._aviso(5, 1)  # intento anterior
            await self._aviso(6, 2)  # otro mensaje
            await trabajo

        asyncio.run(caso())
        self.assertEqual(self.canal.publicados, [{"status": "ok", "response": "ok"}])

    def test_aviso_cuando_ya_termino_no_hace_nada(self):
        async def generar(mensaje):
            return "ok"

        async def caso():
            await self._procesar(_payload(mensaje_id=5, intento=1), generar)
            await self._aviso(5, 1)

        asyncio.run(caso())
        self.assertEqual(self.canal.publicados, [{"status": "ok", "response": "ok"}])

    def test_apagado_del_consumer_no_se_confunde_con_cancelacion(self):
        interna = {}

        async def generar(mensaje):
            interna["tarea"] = asyncio.current_task()
            await asyncio.sleep(30)

        async def caso():
            trabajo = asyncio.ensure_future(self._procesar(_payload(mensaje_id=5, intento=1), generar))
            await asyncio.sleep(0.01)
            trabajo.cancel()  # el proceso se detiene
            with self.assertRaises(asyncio.CancelledError):
                await trabajo
            await asyncio.sleep(0)
            self.assertTrue(interna["tarea"].cancelled())  # la llamada a Ollama no queda huerfana

        asyncio.run(caso())
        self.assertEqual(self.canal.publicados, [])


class TestCancelarYReintentar(Base):
    def test_una_sola_generacion_viva(self):
        """Intento 1 en curso -> cancelar (aviso 1) -> reintentar (intento 2): la del intento 1 se
        aborta y solo la del intento 2 termina con respuesta (antes: dos generaciones completas)."""
        terminadas = []

        async def generar(mensaje):
            await asyncio.sleep(0.1)
            terminadas.append(mensaje)
            return "respuesta"

        async def caso():
            primera = asyncio.ensure_future(self._procesar(_payload(mensaje_id=5, intento=1), generar))
            await asyncio.sleep(0.02)
            await self._aviso(5, 1)  # cancelar
            segunda = asyncio.ensure_future(self._procesar(_payload(mensaje_id=5, intento=2), generar))  # reintentar
            await asyncio.gather(primera, segunda)

        asyncio.run(caso())
        self.assertEqual(len(terminadas), 1)
        estados = sorted(p.get("tipo") or p["status"] for p in self.canal.publicados)
        self.assertEqual(estados, ["cancelado", "ok"])


class TestSuscripcion(unittest.TestCase):
    def test_un_fallo_al_suscribirse_no_rompe_el_consumer(self):
        class ConexionRota:
            async def channel(self):
                raise ConnectionError("sin permisos")

        with self.assertLogs(consumer.logger, level="WARNING"):
            asyncio.run(consumer._suscribir_avisos_cancelacion(ConexionRota()))  # no lanza


if __name__ == "__main__":
    unittest.main()
