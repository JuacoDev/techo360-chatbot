"""Pruebas de la Fase B (sin red ni base de datos):  python -m unittest training.dataset_0_4_1.tests_fase_b -v

Requieren los worktrees del backend y de proyeccion (ver `entorno.py`) y el snapshot; la comparacion con 0.4.0 y la del dataset generado se
omiten si `trabajo-dataset-0.4.0-r2` / `trabajo-dataset-0.4.1` no estan.
"""
import hashlib
import json
import random
import unittest
from pathlib import Path

from . import entorno

DIR_040 = entorno.RAIZ_MONOREPO / "trabajo-dataset-0.4.0-r2"
DIR_041 = entorno.RAIZ_MONOREPO / "trabajo-dataset-0.4.1"


def _jsonl(ruta: Path) -> list[dict]:
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


class NucleoProyeccion(unittest.TestCase):
    def test_sha256_contra_el_repo_y_el_lock(self):
        huella = entorno.verificar_nucleo_proyeccion()  # falla si difiere del lock o de `git show <commit>:<ruta>`
        lock = json.loads(entorno.LOCK_PROYECCION.read_text(encoding="utf-8"))
        self.assertEqual(huella["commit"], lock["commit"])
        self.assertEqual(len(lock["archivos"]), 2)
        # el commit registrado es el de origin/Testing de techo360-proyeccion con el que se generó el dataset
        self.assertRegex(lock["commit"], r"^[0-9a-f]{40}$")


class Score(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from .motor import Entorno
        cls.E = Entorno()

    def test_limites_2024_son_los_de_la_base(self):
        """Los limites fijos de 2024 salen de calcular_limites_desde_filas (la funcion del backend) sobre el snapshot."""
        lim = self.E.d.limites
        self.assertEqual(set(lim), {"cobertura_acueducto", "cobertura_alcantarillado", "deficit_habitacional_cuantitativo"})
        self.assertTrue(all(a is not None and b is not None and a < b for a, b in lim.values()))

    def test_score_igual_a_la_formula_del_backend_en_una_muestra(self):
        """Score 2018 (componentes reales) calculado AQUI con normalizar_minmax + calcular_score_privacion del backend sobre las filas
        crudas del snapshot == el valor que escribe el contexto (via el pipeline real) para una muestra de 40 municipios."""
        from services.orquestador import contexto as cx
        from services.score_privacion import calcular_score_privacion, normalizar_minmax
        d = self.E.d
        rng = random.Random(7)
        muestra = rng.sample(sorted(d.universo), 40)
        comparados = 0
        for cod in muestra:
            comp = {}
            for v in ("cobertura_acueducto", "cobertura_alcantarillado", "deficit_habitacional_cuantitativo"):
                fila = next((f for f in d.serie(cod, v) if f["anio"] == 2018 and f["valor"] is not None), None)
                comp[v] = None if fila is None else {"score_normalizado": normalizar_minmax(fila["valor"], *d.limites[v])}
            if any(x is None for x in comp.values()):
                continue
            esperado = calcular_score_privacion(comp)
            m = d.municipio(cod)
            r = self.E.preparar(f"Score de privación de {m['nombre']} ({m['departamento']}) en 2018", usar_rag=False)
            if r["accion"] != "consultar":
                continue
            items = [i for i in r["peticion"]["contexto"] if i["variable"] == "score_privacion" and i["codigodivipola"] == cod and i["anio"] == 2018]
            if not items:
                continue
            self.assertAlmostEqual(items[0]["valor"], esperado, places=3, msg=cod)
            self.assertIn(cx.formato_valor("score_privacion", items[0]["valor"]), r["peticion"]["mensajes"][-1]["contenido"])
            comparados += 1
        self.assertGreaterEqual(comparados, 20)


@unittest.skipUnless(DIR_040.exists(), "falta trabajo-dataset-0.4.0-r2")
class Contra040(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from .motor import Entorno
        cls.E = Entorno()
        cls.filas = _jsonl(DIR_040 / "train_nuevos.jsonl")

    def test_el_snapshot_reproduce_el_contexto_generado_con_la_base_en_0_4_0(self):
        """150 pares de 0.4.0 (todas las subfamilias, incluidos los de Score y proyeccion): el user re-armado con snapshot + pipeline real
        es IDENTICO byte a byte al que se generó leyendo la base de datos."""
        rng = random.Random(11)
        muestra = rng.sample(self.filas, 150) + [f for f in self.filas if "Score de privación" in f["instruction"]][:60]
        for f in muestra:
            e = f["entrada"]
            r = self.E.preparar(e["pregunta"], huecos=e.get("huecos"), usar_rag=False)
            self.assertEqual(r["accion"], "consultar", f["id"])
            self.assertEqual(r["peticion"]["mensajes"][-1]["contenido"], f["instruction"], f["id"])


@unittest.skipUnless((DIR_041 / "dataset_0_4_1.jsonl").exists(), "falta el dataset generado")
class DatasetGenerado(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from .motor import Entorno
        cls.E = Entorno()
        cls.filas = _jsonl(DIR_041 / "dataset_0_4_1.jsonl")

    def test_sha256sums(self):
        sums = dict(l.split("  ", 1)[::-1] for l in (DIR_041 / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if l.strip())
        for nombre, sha in sums.items():
            self.assertEqual(hashlib.sha256((DIR_041 / nombre).read_bytes()).hexdigest(), sha, nombre)

    def test_estructura(self):
        from .motor import SYSTEM_SHA256
        ids = [f["id"] for f in self.filas]
        self.assertEqual(len(ids), len(set(ids)), "ids repetidos")
        for f in self.filas:
            self.assertEqual(f["mensajes"][0]["rol"], "system")
            self.assertEqual(hashlib.sha256(f["mensajes"][0]["contenido"].encode("utf-8")).hexdigest(), SYSTEM_SHA256)
            self.assertEqual(f["mensajes"][-1]["rol"], "user")
            self.assertEqual(f["perdida"], "ultimo_assistant")
            roles = [m["rol"] for m in f["mensajes"]]
            self.assertEqual(roles[1:-1], ["user", "assistant"] * ((len(roles) - 2) // 2))
            self.assertLessEqual(len(roles), 6)  # system + 2 intercambios + user

    def test_dorada_en_una_muestra(self):
        """Re-armar con el pipeline real da los mismos mensajes (historial, RAG y bloque de opciones incluidos)."""
        rng = random.Random(3)
        nuevos = [f for f in self.filas if f["source"].startswith("techo360-generador-0.4.1")]
        for f in rng.sample(nuevos, min(250, len(nuevos))):
            self.assertEqual(self.E.rearmar(f), f["mensajes"], f["id"])

    def test_los_holdouts_no_comparten_preguntas_con_el_train(self):
        train_q = {f["entrada"]["pregunta"] for f in self.filas}
        for nombre in ("holdout_graf.jsonl", "holdout_rag.jsonl", "holdout_hist.jsonl"):
            for h in _jsonl(DIR_041 / nombre):
                self.assertNotIn(h["entrada"]["pregunta"], train_q, nombre)


if __name__ == "__main__":
    unittest.main()
