"""Pruebas de la lectura de OLLAMA_NUM_THREAD en app/ollama_client.py (sin red).

Uso:
    python -m unittest app.tests_ollama_client
"""
import asyncio
import importlib
import os
import unittest
from unittest.mock import patch


def _recargar(**entorno):
    """Recarga app.ollama_client con exactamente este entorno de OLLAMA_NUM_THREAD."""
    os.environ.pop("OLLAMA_NUM_THREAD", None)
    os.environ.update(entorno)
    import app.ollama_client as cliente
    return importlib.reload(cliente)


class NumThreadDesdeEntorno(unittest.TestCase):
    def tearDown(self):
        _recargar()

    def test_sin_variable_queda_en_3(self):
        self.assertEqual(_recargar().NUM_THREAD, 3)

    def test_valor_valido(self):
        self.assertEqual(_recargar(OLLAMA_NUM_THREAD="4").NUM_THREAD, 4)
        self.assertEqual(_recargar(OLLAMA_NUM_THREAD=" 8 ").NUM_THREAD, 8)

    def test_valores_invalidos_vuelven_al_defecto_con_aviso(self):
        for malo in ("", "   ", "abc", "0", "-2", "2.5"):
            with self.subTest(valor=malo):
                with patch("logging.Logger.warning") as aviso:
                    cliente = _recargar(OLLAMA_NUM_THREAD=malo)
                self.assertEqual(cliente.NUM_THREAD, 3)
                # vacio/espacios = "no configurada": sin aviso; el resto avisa
                self.assertEqual(aviso.called, malo.strip() != "")

    def test_la_peticion_a_ollama_lleva_el_valor_configurado(self):
        for entorno, esperado in (({}, 3), ({"OLLAMA_NUM_THREAD": "5"}, 5)):
            with self.subTest(entorno=entorno):
                cliente = _recargar(**entorno)
                enviado = {}

                class _Respuesta:
                    def raise_for_status(self):
                        pass

                    def json(self):
                        return {"message": {"content": "ok"}}

                class _Cliente:
                    def __init__(self, *args, **kwargs):
                        pass

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *args):
                        return False

                    async def post(self, url, json=None):
                        enviado.update(json)
                        return _Respuesta()

                with patch.object(cliente.httpx, "AsyncClient", _Cliente):
                    self.assertEqual(asyncio.run(cliente.generar_respuesta("hola")), "ok")
                self.assertEqual(enviado["options"]["num_thread"], esperado)

if __name__ == "__main__":
    unittest.main()
