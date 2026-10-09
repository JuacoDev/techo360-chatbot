"""Pruebas de SEGURIDAD de app/main.py sin RabbitMQ ni Ollama (TestClient sin
`with`, asi no corre el lifespan que conecta el consumer).

Uso:
    python -m unittest app.tests_main
"""
import importlib
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def _cargar(**entorno):
    """Recarga app.main con estas variables (y sin las demas de este modulo)."""
    for var in ("CHATBOT_HABILITAR_SEND_LOCAL", "CHATBOT_HABILITAR_DOCS"):
        os.environ.pop(var, None)
    os.environ.update(entorno)
    import app.main as principal
    return importlib.reload(principal)


def _rutas(app):
    return {getattr(r, "path", None) for r in app.routes}


class RutasDelServicio(unittest.TestCase):
    def tearDown(self):
        _cargar()

    def test_produccion_sin_send_ni_docs(self):
        principal = _cargar()
        cliente = TestClient(principal.app)
        self.assertNotIn("/chatbot/send", _rutas(principal.app))
        for ruta in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual(cliente.get(ruta).status_code, 404, ruta)
        self.assertEqual(cliente.post("/chatbot/send", json={"message": "hola", "usuario_id": 1}).status_code, 404)
        self.assertEqual(cliente.get("/health").status_code, 200)

    def test_docs_solo_con_variable(self):
        principal = _cargar(CHATBOT_HABILITAR_DOCS="1")
        self.assertEqual(TestClient(principal.app).get("/openapi.json").status_code, 200)

    def test_send_local_no_persiste_ni_usa_ids_del_cuerpo(self):
        principal = _cargar(CHATBOT_HABILITAR_SEND_LOCAL="1")
        self.assertIn("/chatbot/send", _rutas(principal.app))
        self.assertFalse(hasattr(principal, "persistir_en_background"), "main ya no importa la persistencia")
        with patch.object(principal, "generar_respuesta", AsyncMock(return_value="respuesta")), \
             patch("app.persistencia.persistir_en_background") as persistir:
            r = TestClient(principal.app).post(
                "/chatbot/send",
                json={"message": "hola", "usuario_id": 7, "conversacion_id": 1, "consentimiento_entrenamiento": True},
            )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"response": "respuesta"})
        persistir.assert_not_called()

    def test_valor_distinto_de_1_no_habilita(self):
        principal = _cargar(CHATBOT_HABILITAR_SEND_LOCAL="true", CHATBOT_HABILITAR_DOCS="si")
        self.assertNotIn("/chatbot/send", _rutas(principal.app))
        self.assertEqual(TestClient(principal.app).get("/docs").status_code, 404)


if __name__ == "__main__":
    unittest.main()
