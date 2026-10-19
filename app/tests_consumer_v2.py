"""Pruebas del consumer que acepta v1 y v2 (fase4-especificacion-2, 4.4), sin RabbitMQ ni Ollama (dobles).

* Regresion v1: los payloads actuales dan exactamente las mismas respuestas que antes.
* v2: valida con el esquema, envia `mensajes` tal cual (el system viene en la peticion), mismas opciones del
  runner, y responde con metadatos validos contra RespuestaV2.
* Errores v2: contrato_no_soportado, payload_invalido, contexto_excedido, cancelado, ollama_no_disponible.

Uso:
    python -m unittest app.tests_consumer_v2
"""
import asyncio
import copy
import json
import unittest
from unittest.mock import AsyncMock, patch

from app import ollama_client as cliente
from app import rabbitmq_consumer as consumer
from app.contrato_v2 import RespuestaErrorV2, RespuestaOkV2, validar_respuesta
from app.tests_cancelacion import Base, CanalFalso, MensajeFalso, _payload

EJEMPLOS = json.load(open(__import__("os").path.join(__import__("os").path.dirname(__file__), "contrato_v2_ejemplos.json"), encoding="utf-8"))
V2 = next(c["payload"] for c in EJEMPLOS["peticiones_v2_validas"] if c["nombre"] == "v2_ejemplo_spec")


def v2(**cambios):
    p = copy.deepcopy(V2)
    p.update(cambios)
    return p


GENERADA = {"texto": "La cobertura es 94,2 %.", "done_reason": "stop", "prompt_eval_count": 612, "eval_count": 187, "duracion_ms": 31200}


class V1SinCambios(Base):
    def test_v1_minimo_responde_como_siempre(self):
        async def generar(mensaje):
            return "hola"

        asyncio.run(self._procesar(_payload(), generar))
        self.assertEqual(self.canal.publicados, [{"status": "ok", "response": "hola"}])

    def test_v1_con_version_contrato_1_es_v1(self):
        async def generar(mensaje):
            return "hola"

        asyncio.run(self._procesar(_payload(version_contrato=1), generar))
        self.assertEqual(self.canal.publicados, [{"status": "ok", "response": "hola"}])

    def test_v1_sin_campos_obligatorios_es_payload_invalido(self):
        async def generar(mensaje):
            return "x"

        asyncio.run(self._procesar({"mensaje": "hola"}, generar))
        self.assertEqual(self.canal.publicados[0]["status"], "error")
        self.assertEqual(self.canal.publicados[0]["tipo"], "payload_invalido")
        self.assertNotIn("version_contrato", self.canal.publicados[0])

    def test_v1_ollama_caido_y_cancelacion_siguen_igual(self):
        async def caido(mensaje):
            raise consumer.OllamaNoDisponibleError("sin ollama")

        asyncio.run(self._procesar(_payload(), caido))
        self.assertEqual(self.canal.publicados, [{"status": "error", "tipo": "ollama_no_disponible", "detail": "sin ollama"}])

    def test_v1_no_usa_el_camino_v2(self):
        with patch.object(consumer, "generar_respuesta_v2", AsyncMock()) as v2fn, patch.object(consumer, "generar_respuesta", AsyncMock(return_value="r")):
            asyncio.run(consumer._procesar_mensaje(MensajeFalso(_payload()), self.canal))
        v2fn.assert_not_awaited()


class ConsumerV2(Base):
    def _v2(self, payload, generada=GENERADA, digest="sha256:abc", generador=None):
        async def hacer():
            fake = generador or AsyncMock(return_value=generada)
            with patch.object(consumer, "generar_respuesta_v2", fake), patch.object(consumer, "obtener_digest", AsyncMock(return_value=digest)):
                await consumer._procesar_mensaje(MensajeFalso(payload), self.canal)
            return fake

        return asyncio.run(hacer())

    def test_valido_responde_con_metadatos_y_cumple_el_esquema(self):
        fake = self._v2(v2())
        respuesta = self.canal.publicados[0]
        validado = validar_respuesta(respuesta)
        self.assertIsInstance(validado, RespuestaOkV2)
        self.assertEqual(respuesta["response"], "La cobertura es 94,2 %.")
        m = respuesta["metadatos"]
        self.assertEqual((m["done_reason"], m["prompt_eval_count"], m["eval_count"], m["duracion_ms"]), ("stop", 612, 187, 31200))
        self.assertEqual((m["contexto_ids"], m["digest"]), (["c1"], "sha256:abc"))
        self.assertEqual(m["modelo"], cliente.OLLAMA_MODEL)

    def test_los_mensajes_se_envian_tal_cual_con_el_system_de_la_peticion(self):
        fake = self._v2(v2())
        enviados = fake.await_args.args[0]
        self.assertEqual([m["role"] for m in enviados], ["system", "user"])
        self.assertEqual(enviados[0]["content"], V2["mensajes"][0]["contenido"])
        self.assertNotEqual(enviados[0]["content"], cliente.SYSTEM_PROMPT)
        self.assertEqual(enviados[1]["content"], V2["mensajes"][1]["contenido"])

    def test_sin_digest_el_campo_queda_ausente(self):
        self._v2(v2(), digest=None)
        self.assertNotIn("digest", self.canal.publicados[0]["metadatos"])
        self.assertIsInstance(validar_respuesta(self.canal.publicados[0]), RespuestaOkV2)

    def test_contrato_no_soportado(self):
        fake = self._v2(v2(version_contrato=3))
        r = self.canal.publicados[0]
        self.assertEqual((r["status"], r["tipo"], r["version_contrato"]), ("error", "contrato_no_soportado", 2))
        self.assertIsInstance(validar_respuesta(r), RespuestaErrorV2)
        fake.assert_not_awaited()

    def test_payload_invalido_en_v2(self):
        malos = [v2(mensajes=[V2["mensajes"][1]]), {k: v for k, v in V2.items() if k != "metadatos"}, v2(version_contrato="2")]
        for malo in malos:
            with self.subTest(list(malo)[:2]):
                self.canal.publicados.clear()
                fake = self._v2(malo)
                self.assertEqual(self.canal.publicados[0]["tipo"], "payload_invalido")
                fake.assert_not_awaited()

    def test_v2_con_campo_mensaje_es_payload_invalido(self):
        self._v2(v2(mensaje="hola"))
        self.assertEqual(self.canal.publicados[0]["tipo"], "payload_invalido")

    def _con_caracteres_totales(self, total):
        """V2 con exactamente `total` caracteres entre todos los mensajes (el system del ejemplo se deja igual)."""
        p = copy.deepcopy(V2)
        resto = total - sum(len(m["contenido"]) for m in p["mensajes"][:-1])
        p["mensajes"][-1]["contenido"] = "x" * resto
        return p

    def test_presupuesto_por_defecto_es_2608(self):
        self.assertEqual((consumer.NUM_CTX, cliente.NUM_PREDICT, consumer.PRESUPUESTO_PROMPT), (3072, 400, 2608))

    def test_limite_justo_pasa(self):
        # 5.998 caracteres / 2,3 -> 2.607 + 1 = 2.608 tokens estimados = el presupuesto exacto
        p = self._con_caracteres_totales(5998)
        self.assertEqual(consumer.tokens_estimados([{"content": m["contenido"]} for m in p["mensajes"]]), 2608)
        self._v2(p)
        self.assertEqual(self.canal.publicados[0]["status"], "ok")

    def test_un_token_mas_se_rechaza(self):
        p = self._con_caracteres_totales(5999)  # 2.609 tokens estimados
        self.assertEqual(consumer.tokens_estimados([{"content": m["contenido"]} for m in p["mensajes"]]), 2609)
        fake = self._v2(p)
        self.assertEqual(self.canal.publicados[0]["tipo"], "contexto_excedido")
        fake.assert_not_awaited()

    def test_prompt_que_antes_se_rechazaba_ahora_pasa(self):
        # ~1.800 tokens estimados con 3,0 car/token (5.400 car.) superaban el viejo limite de 1.648 y se rechazaban; con 3072 caben
        self._v2(self._con_caracteres_totales(5400))
        self.assertEqual(self.canal.publicados[0]["status"], "ok")

    def test_prompt_normal_pasa(self):
        self._v2(v2())
        self.assertEqual(self.canal.publicados[0]["status"], "ok")

    def test_ollama_no_disponible_en_v2(self):
        fake = AsyncMock(side_effect=consumer.OllamaNoDisponibleError("sin ollama"))
        self._v2(v2(), generador=fake)
        r = self.canal.publicados[0]
        self.assertEqual((r["version_contrato"], r["tipo"]), (2, "ollama_no_disponible"))

    def test_cancelacion_del_intento_en_v2(self):
        async def hacer():
            async def lenta(mensajes):
                await asyncio.sleep(5)

            with patch.object(consumer, "generar_respuesta_v2", lenta), patch.object(consumer, "obtener_digest", AsyncMock(return_value=None)):
                tarea = asyncio.ensure_future(consumer._procesar_mensaje(MensajeFalso(v2()), self.canal))
                await asyncio.sleep(0.05)
                await self._aviso(345, 1)  # metadatos de V2: mensaje_id 345, intento 1
                await asyncio.wait_for(tarea, 2)

        asyncio.run(hacer())
        self.assertEqual(self.canal.publicados[0]["tipo"], "cancelado")
        self.assertEqual(self.canal.publicados[0]["version_contrato"], 2)

    def test_error_inesperado_no_tumba_el_consumer(self):
        fake = AsyncMock(side_effect=RuntimeError("boom"))
        self._v2(v2(), generador=fake)
        self.assertEqual(self.canal.publicados[0]["tipo"], "error_interno")


class ClienteOllamaV2(unittest.TestCase):
    def _cliente(self, respuesta_json, enviado, falla=False):
        class _Resp:
            def raise_for_status(self_):
                if falla:
                    import httpx
                    raise httpx.ConnectError("sin red")

            def json(self_):
                return respuesta_json

        class _Cliente:
            def __init__(self_, *a, **k):
                pass

            async def __aenter__(self_):
                return self_

            async def __aexit__(self_, *a):
                return False

            async def post(self_, url, json=None):
                enviado.update(url=url, json=json)
                return _Resp()

            async def get(self_, url):
                enviado.update(url=url)
                return _Resp()

        return _Cliente

    def test_envia_los_mensajes_con_las_opciones_de_v1(self):
        enviado = {}
        mensajes = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
        resp = {"message": {"content": "r"}, "done_reason": "stop", "prompt_eval_count": 10, "eval_count": 2, "total_duration": 1_500_000_000}
        with patch.object(cliente.httpx, "AsyncClient", self._cliente(resp, enviado)):
            r = asyncio.run(cliente.generar_respuesta_v2(mensajes))
        self.assertEqual(enviado["json"]["messages"], mensajes)
        self.assertEqual(enviado["json"]["options"], {"num_predict": cliente.NUM_PREDICT, "num_thread": cliente.NUM_THREAD})
        self.assertIs(enviado["json"]["stream"], False)
        self.assertEqual(r, {"texto": "r", "done_reason": "stop", "prompt_eval_count": 10, "eval_count": 2, "duracion_ms": 1500})

    def test_error_http_es_ollama_no_disponible(self):
        with patch.object(cliente.httpx, "AsyncClient", self._cliente({}, {}, falla=True)):
            with self.assertRaises(cliente.OllamaNoDisponibleError):
                asyncio.run(cliente.generar_respuesta_v2([{"role": "user", "content": "U"}]))

    def test_digest_se_cachea_y_se_refresca_si_se_pide(self):
        cliente._digest_cache.clear()
        enviado = {}
        tags = {"models": [{"name": cliente.OLLAMA_MODEL, "digest": "d1"}]}
        with patch.object(cliente.httpx, "AsyncClient", self._cliente(tags, enviado)):
            self.assertEqual(asyncio.run(cliente.obtener_digest()), "d1")
            tags["models"][0]["digest"] = "d2"
            self.assertEqual(asyncio.run(cliente.obtener_digest()), "d1")  # cacheado
            self.assertEqual(asyncio.run(cliente.obtener_digest(forzar=True)), "d2")
        self.assertTrue(enviado["url"].endswith("/api/tags"))

    def test_digest_ausente_si_falla(self):
        cliente._digest_cache.clear()
        with patch.object(cliente.httpx, "AsyncClient", self._cliente({}, {}, falla=True)):
            self.assertIsNone(asyncio.run(cliente.obtener_digest()))

    def test_tokens_estimados(self):
        self.assertEqual(cliente.tokens_estimados([{"role": "u", "content": "x" * 300}]), 131)


if __name__ == "__main__":
    unittest.main()
