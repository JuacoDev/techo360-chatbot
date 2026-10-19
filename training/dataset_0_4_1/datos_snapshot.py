"""Datos de mapcalordb desde el SNAPSHOT local (sin base de datos) + funciones reales del orquestador del backend.

`DatosSnapshot` hereda de `scripts.dataset_0_4.datos.Datos` (5.2) y sustituye solo la lectura: catalogo, series y limites del Score
salen de los CSV del snapshot; huecos y proyecciones, del nucleo de techo360-proyeccion (con sha256 verificado); el Score, de
`services.proyeccion_service` y `services.score_privacion` del backend (limites fijos del anio base 2024). El contexto y el
mensaje los arman `construir_contexto` y `ensamblar` del backend, con intencion de grafica, RAG e historial.
"""
import asyncio
import csv
from pathlib import Path

from . import entorno

entorno.preparar_rutas()

from scripts.dataset_0_4.datos import HOY, META, VARIABLES_BD, Datos, _cargar_proyeccion  # noqa: E402
from services import proyeccion_service as pservicio  # noqa: E402
from services.orquestador import alias as al  # noqa: E402
from services.orquestador import contexto as cx  # noqa: E402
from services.orquestador import ensamblador as ens  # noqa: E402
from services.orquestador.grafica_intencion import SIN_INTENCION  # noqa: E402
from services.orquestador.resolutor import CODIGOS_FUERA_DEL_UNIVERSO, Catalogo, Municipio  # noqa: E402
from services.score_privacion import VARIABLES_SCORE, calcular_limites_desde_filas  # noqa: E402

CODIGO_NACIONAL = "01001"


class DatosSnapshot(Datos):
    def __init__(self, directorio: Path = entorno.SNAPSHOT_DIR):
        entorno.verificar_nucleo_proyeccion()
        self.puntos = _cargar_proyeccion(entorno.PROYECCION_DIR)
        self.db = None
        self.solo_lectura = "snapshot"
        filas = list(csv.DictReader((directorio / "zonas_municipio.csv").open(encoding="utf-8", newline="")))
        self.catalogo = Catalogo([
            Municipio(f["codigo_municipio"], f["municipio"], f["codigo_departamento"], f["departamento"] or "")
            for f in filas if f["codigo_municipio"] not in CODIGOS_FUERA_DEL_UNIVERSO
        ])
        self.series: dict[tuple[str, str], list[dict]] = {}
        base = []
        for f in csv.DictReader((directorio / "mapcalordb.csv").open(encoding="utf-8", newline="")):
            if f["namevar"] not in VARIABLES_BD:
                continue
            valor = None if f["valuevar"] == "" else float(f["valuevar"])
            self.series.setdefault((f["codigodivipola"], f["namevar"]), []).append({
                "anio": int(f["yearm"]), "valor": valor, "origen": f["originvar"],
                "intervalo": None if f["intervaloconfianza"] == "" else float(f["intervaloconfianza"]),
            })
            if int(f["yearm"]) == pservicio.ANIO_BASE_SCORE and f["namevar"] in VARIABLES_SCORE and f["codigodivipola"] != CODIGO_NACIONAL:
                base.append({"codigodivipola": f["codigodivipola"], "namevar": f["namevar"], "valuevar": valor})
        for lista in self.series.values():
            lista.sort(key=lambda x: x["anio"])
        self.universo = set(self.catalogo.por_codigo)
        self.limites = calcular_limites_desde_filas(base, self.universo)

        async def _limites(_db):
            return self.limites

        pservicio._obtener_limites_base_cacheados = _limites

    # ------------------------------------------------------------------ contexto y mensaje reales
    def contexto(self, entrada: dict, intencion=SIN_INTENCION, fragmentos: list[dict] | None = None) -> cx.ContextoConstruido:
        huecos = {(h["variable"], h["divipola"], int(h["anio"])): h.get("motivo") for h in entrada.get("huecos", [])}
        leer, completar, score_fn = self._fabrica(huecos)
        ctx = asyncio.run(cx.construir_contexto(
            self.resolucion(entrada), self.db, hoy_anio=HOY.year, leer_serie_fn=leer, completar=completar, score_fn=score_fn,
            intencion_grafica=intencion,
        ))
        if fragmentos:
            ctx.fragmentos_rag = list(fragmentos)
        return ctx

    def renderizar(self, entrada: dict, system: str | None = None, historial: list[dict] | None = None, intencion=SIN_INTENCION,
                   fragmentos: list[dict] | None = None) -> dict:
        """-> {"mensajes": [...], "user": ultimo mensaje, "items", "lineas", "notas", "contexto_texto"}. Usa `ensamblar` del backend."""
        contexto = self.contexto(entrada, intencion, fragmentos)
        paquete = ens.ensamblar(entrada["pregunta"], contexto, dict(META), system, historial)
        mensajes = paquete["peticion"]["mensajes"]
        user = mensajes[-1]["contenido"]
        bloque = user.split("\n\nPREGUNTA DEL USUARIO\n")[0]
        return {
            "mensajes": mensajes, "user": user, "items": paquete["peticion"]["contexto"], "lineas": bloque.split("\n")[1:],
            "contexto_texto": bloque, "notas": paquete["notas"],
        }
