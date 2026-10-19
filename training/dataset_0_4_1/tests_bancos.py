"""Pruebas de la Fase A de 7.3 (sin BD ni red):  python -m unittest training.dataset_0_4_1.tests_bancos -v"""
import importlib.util
import sys
import unittest
from pathlib import Path

from . import bloque as bl
from . import catalogo as cat
from . import controles as ct
from . import preguntas as pq
from . import respuestas as rp

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO_BACKEND = [
    RAIZ.parent / "techo360-backend-wt-w1" / "services" / "reportes_graficas_catalogo.py",
    RAIZ.parent / "techo360-backend" / "services" / "reportes_graficas_catalogo.py",
]

CONTEXTO = (
    "CONTEXTO\n[c1] Cobertura de acueducto, Bucaramanga (Santander), 2019: 90,1 %. Fuente: DNP - TerriData. Dato real.\n"
    "[c2] Cobertura de acueducto, Bucaramanga (Santander), 2024: 94,2 %. Fuente: DNP - TerriData. Dato real.\n"
    "Gráfica disponible. Tipos: lineas, barras_ranking, barras_agrupadas, gauge. Variables: score_privacion, cobertura_acueducto, "
    "cobertura_alcantarillado, deficit_habitacional_cuantitativo, deficit_habitacional_cualitativo, densidad_poblacional. "
    "Zonas: 68001 = Bucaramanga (Santander); 05001 = Medellín (Antioquia).\n\nPREGUNTA DEL USUARIO\nGrafícame la evolución de la cobertura de acueducto en Bucaramanga."
)
BLOQUE_OK = '```grafica\n{"v":1,"tipo":"lineas","modo":"individual","variables":["cobertura_acueducto"],"zonas":["68001"],"anios":[2019,2024]}\n```'


class Bancos(unittest.TestCase):
    def test_preguntas(self):
        for sub, problemas in ct.controlar_preguntas().items():
            self.assertEqual(problemas, [], sub)

    def test_respuestas(self):
        for sub, problemas in ct.controlar_respuestas().items():
            self.assertEqual(problemas, [], sub)

    def test_notas_y_g6(self):
        self.assertEqual(ct.controlar_notas(), [])

    def test_cuotas(self):
        self.assertEqual(ct.controlar_cuotas(), [])

    def test_diversidad(self):
        self.assertEqual(ct.controlar_diversidad(), [])

    def test_dedup_contra_evaluacion(self):
        conjuntos, _ = ct.cargar_conjuntos_evaluacion(RAIZ, RAIZ.parent)
        problemas, _ = ct.controlar_dedup(conjuntos)
        self.assertEqual(problemas, [])

    def test_minimos(self):
        for sub, banco in pq.BANCOS.items():
            self.assertGreaterEqual(len(banco), cat.MINIMO_PREGUNTAS, sub)

    def test_detector_copiado_distingue_g1_de_g2(self):
        self.assertTrue(ct.pide_grafica("Grafícame la evolución de la cobertura de acueducto en Cali"))
        self.assertTrue(ct.pide_grafica("Muéstrame el medidor del score"))
        self.assertFalse(ct.pide_grafica("¿Cómo evolucionó la cobertura de acueducto en Cali entre 2019 y 2024?"))
        self.assertTrue(ct.es_evolucion("Grafícame la cobertura de acueducto en Cali"))
        self.assertFalse(ct.es_evolucion("Hazme un ranking en barras de la cobertura de acueducto"))


class BloqueTest(unittest.TestCase):
    def test_armar_bloque_exacto(self):
        self.assertEqual(
            bl.armar_bloque("lineas", "individual", ["cobertura_acueducto"], ["68001"], [2019, 2024]), BLOQUE_OK)

    def test_armar_rechaza_combinaciones_invalidas(self):
        casos = [
            ("lineas", "individual", ["cobertura_acueducto"], ["68001"], [2019]),  # un solo año
            ("lineas", "individual", ["cobertura_acueducto", "cobertura_alcantarillado"], ["68001"], [2019, 2020]),
            ("lineas", "comparar", ["cobertura_acueducto"], ["68001"], [2019, 2020]),  # comparar con 1 zona
            ("barras_ranking", "individual", ["cobertura_acueducto"], ["68001"], [2024]),
            ("barras_ranking", "comparar", ["cobertura_acueducto"], ["68001", "05001"], [2023, 2024]),
            ("barras_agrupadas", "individual", ["cobertura_acueducto", "densidad_poblacional"], ["68001"], [2024]),
            ("barras_agrupadas", "individual", ["cobertura_acueducto"], ["68001"], [2024]),
            ("gauge", "individual", ["densidad_poblacional"], ["68001"], [2024]),
            ("radar", "individual", ["cobertura_acueducto"], ["68001"], [2024]),
            ("lineas", "individual", ["cobertura_acueducto"], ["68001"], [2024, 2019]),  # desordenado
            ("lineas", "individual", ["cobertura_acueducto"], ["68001"], [2010, 2024]),  # fuera de rango
            ("lineas", "individual", ["cobertura_acueducto"], ["Bucaramanga"], [2019, 2024]),  # nombre en vez de código
        ]
        for caso in casos:
            with self.assertRaises(ValueError, msg=str(caso)):
                bl.armar_bloque(*caso)

    def test_combinaciones_validas(self):
        validos = [
            ("lineas", "comparar", ["deficit_habitacional_cuantitativo"], ["68001", "05001"], [2018, 2019, 2020]),
            ("barras_ranking", "comparar", ["score_privacion"], ["68001", "05001", "11001"], [2024]),
            ("barras_agrupadas", "individual", ["cobertura_acueducto", "deficit_habitacional_cualitativo"], ["68001"], [2024]),
            ("barras_agrupadas", "comparar", ["cobertura_acueducto", "cobertura_alcantarillado"], ["68001", "05001"], [2024]),
            ("gauge", "individual", ["score_privacion"], ["68001"], [2024]),
        ]
        for caso in validos:
            self.assertTrue(bl.armar_bloque(*caso).startswith("```grafica\n"))

    def test_validar_respuesta_g_acepta_y_rechaza(self):
        texto = "En Bucaramanga (Santander), la cobertura de acueducto pasó de 90,1 % en 2019 a 94,2 % en 2024. La gráfica se muestra debajo."
        ok = bl.armar_respuesta(texto, BLOQUE_OK)
        self.assertEqual(bl.validar_respuesta_g(ok, CONTEXTO, debe_tener_bloque=True), [])
        # con valores de datos
        malo = ok.replace('"anios":[2019,2024]', '"anios":[2019,2024],"datos":[90.1,94.2]')
        self.assertTrue(bl.validar_respuesta_g(malo, CONTEXTO, debe_tener_bloque=True))
        # código de zona inventado
        self.assertTrue(bl.validar_respuesta_g(ok.replace("68001", "68002"), CONTEXTO, debe_tener_bloque=True))
        # sin línea en blanco
        self.assertTrue(bl.validar_respuesta_g(ok.replace("\n\n```", "\n```"), CONTEXTO, debe_tener_bloque=True))
        # dos bloques
        self.assertTrue(bl.validar_respuesta_g(ok + "\n\n" + BLOQUE_OK, CONTEXTO, debe_tener_bloque=True))
        # bloque donde no corresponde (G2-G5)
        self.assertTrue(bl.validar_respuesta_g(ok, CONTEXTO, debe_tener_bloque=False))
        self.assertEqual(bl.validar_respuesta_g("Solo texto.", CONTEXTO, debe_tener_bloque=False), [])
        # contexto sin línea de opciones
        self.assertTrue(bl.validar_respuesta_g(ok, CONTEXTO.split("Gráfica disponible.")[0], debe_tener_bloque=True))

    def test_opciones_del_contexto(self):
        op = bl.opciones_del_contexto(CONTEXTO)
        self.assertEqual(op["zonas"], {"68001", "05001"})
        self.assertEqual(op["tipos"], list(cat.TIPOS_MODELO))
        self.assertEqual(tuple(op["variables"]), cat.VARIABLES)

    def test_paridad_backend(self):
        """Si el catálogo real del backend está disponible, `tipos_validos` coincide con `validar_combinacion` en una malla."""
        ruta = next((r for r in CATALOGO_BACKEND if r.exists()), None)
        if ruta is None:
            self.skipTest("catálogo del backend no disponible")
        spec = importlib.util.spec_from_file_location("catalogo_backend", ruta)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        variables = [[v] for v in cat.VARIABLES] + [
            ["cobertura_acueducto", "cobertura_alcantarillado"], ["cobertura_acueducto", "deficit_habitacional_cuantitativo", "deficit_habitacional_cualitativo"],
            ["cobertura_acueducto", "densidad_poblacional"], ["score_privacion", "cobertura_acueducto"],
        ]
        for tipo in cat.TIPOS_MODELO:
            for modo in ("individual", "comparar"):
                for vs in variables:
                    for n_zonas in (1, 2, 5):
                        for n_anios in (1, 2, 6):
                            propio = cat.tipos_validos(tipo, modo, vs, n_zonas, n_anios) is None
                            # La combinación del catálogo no mira años; los años los acota el modelo (tabla 7.1 §3).
                            real = mod.validar_combinacion(tipo, modo, vs, n_zonas) is None
                            if propio:
                                self.assertTrue(real, (tipo, modo, vs, n_zonas, n_anios))


if __name__ == "__main__":
    unittest.main()
