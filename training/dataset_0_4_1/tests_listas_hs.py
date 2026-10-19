"""Pruebas de listas (adenda 7.1b §2) y familias HS (§4):  python -m unittest training.dataset_0_4_1.tests_listas_hs -v"""
import sys
import unittest
from pathlib import Path

from . import catalogo as cat
from . import controles as ct
from . import listas as ls

RAIZ = Path(__file__).resolve().parents[2]
BACKEND_W1 = RAIZ.parent / "techo360-backend-wt-w1"

LISTA_OK = (
    "Esta es la serie de cobertura de acueducto en Bucaramanga (Santander), año por año:\n"
    "- 2019: 90,1 % (dato real)\n- 2020: 91,5 % (dato real)\n- 2025: 95,0 % (estimación con fiabilidad de 30 %)\n\n"
    "Los elementos marcados como estimación son proyecciones, no datos observados."
)


class ListasHS(unittest.TestCase):
    def test_listas_y_turno_previo(self):
        self.assertEqual(ct.controlar_listas(), [])
        self.assertEqual(ct.controlar_turno_previo(), [])

    def test_validar_formato(self):
        self.assertEqual(ls.validar_formato(LISTA_OK), [])
        self.assertEqual(ls.validar_formato("En 2024, la cobertura fue de 94,2 %."), [])
        malos = {
            "encabezado": "## Serie\n- a: 1\n- b: 2\n- c: 3",
            "tabla": "| año | valor |\n|---|---|",
            "negrita": "La cobertura fue **94,2 %**.",
            "menos de 3": "Estos son los datos:\n- 2019: 90,1 % (dato real)\n- 2020: 91,5 % (dato real)",
            "marcador": "Estos son los datos:\n* 2019: 90,1 %\n* 2020: 91,5 %\n* 2021: 92,0 %",
            "numerada": "Estos son los datos:\n1. 2019: 90,1 %\n2. 2020: 91,5 %\n3. 2021: 92,0 %",
            "sin intro": "- 2019: 90,1 % (dato real)\n- 2020: 91,5 % (dato real)\n- 2021: 92,0 % (dato real)",
            "no contigua": "Estos son los datos:\n- 2019: 90,1 %\ntexto suelto\n- 2020: 91,5 %\n- 2021: 92,0 %",
        }
        for nombre, texto in malos.items():
            self.assertTrue(ls.validar_formato(texto), nombre)

    def test_armar_lista_exige_tres(self):
        with self.assertRaises(ValueError):
            ls.armar_lista("Datos:", ["- 2019: 1 %", "- 2020: 2 %"])
        with self.assertRaises(ValueError):
            ls.armar_lista("Datos", ["- a: 1", "- b: 2", "- c: 3"])

    def test_cuotas_hs(self):
        self.assertEqual(cat.CUOTAS_FAMILIA["HS"], 220)
        self.assertEqual(sum(v for k, v in cat.CUOTAS.items() if cat.familia(k) == "HS"), 220)
        self.assertEqual(cat.familia("hs4_real"), "HS")

    def test_validador_y_sanitizador_no_tocan_guiones(self):
        """Adenda §2: el validador 4.5 y el sanitizador 4.7 del backend dejan intacta la lista."""
        if not (BACKEND_W1 / "services" / "orquestador" / "sanitizador.py").exists():
            self.skipTest("backend no disponible")
        sys.path.insert(0, str(BACKEND_W1))
        try:
            from services.orquestador.sanitizador import sanitizar_texto
            from services.orquestador.validador_cifras import validar_cifras
        except Exception as e:  # dependencias del backend ausentes
            self.skipTest(f"no se pudo importar el backend: {e}")
        finally:
            sys.path.remove(str(BACKEND_W1))
        self.assertEqual(sanitizar_texto(LISTA_OK), LISTA_OK)
        lineas = [
            "[c1] Cobertura de acueducto, Bucaramanga (Santander), 2019: 90,1 %. Fuente: DNP - TerriData. Dato real.",
            "[c2] Cobertura de acueducto, Bucaramanga (Santander), 2020: 91,5 %. Fuente: DNP - TerriData. Dato real.",
            "[c3] Cobertura de acueducto, Bucaramanga (Santander), 2025: 95,0 %. Fuente: Proyección Techo 360. Proyección, fiabilidad 30 %.",
        ]
        self.assertEqual(validar_cifras(LISTA_OK, lineas)["no_validadas"], [])


if __name__ == "__main__":
    unittest.main()
