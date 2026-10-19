"""Motor de la Fase B: arma peticiones con el pipeline REAL del backend (`preparar_consulta`) sobre el snapshot.

`Entorno.preparar(...)` llama a `services.orquestador.orquestador.preparar_consulta`, es decir: resolutor, herencia, intencion de
grafica, serie completa, enrutador conceptual + RAG (recuperador real sobre un Postgres local), ensamblador con historial y
presupuesto de tokens. Lo unico sustituido es la FUENTE de los datos (snapshot en vez de base) y el system (sp-0.4.1-1 en vez
del que carga el backend, que sigue en sp-0.4.0-1 hasta el despliegue). Cada par guarda lo necesario para re-armarse byte a byte
(prueba dorada) sin red ni base de datos.
"""
import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import entorno

entorno.preparar_rutas()

from core.config import settings  # noqa: E402
from services.orquestador import ensamblador as ens  # noqa: E402
from services.orquestador.herencia import resolver_cadena  # noqa: E402
from services.orquestador.orquestador import preparar_consulta  # noqa: E402
from services.orquestador.resolutor import resolver  # noqa: E402

from .datos_snapshot import HOY, META, DatosSnapshot  # noqa: E402

RUTA_SYSTEM = entorno.RAIZ_CHATBOT / "prompts" / "sp-0.4.1-1.txt"
VERSION_PROMPT = "sp-0.4.1-1"
SYSTEM_SHA256 = "7e58d55bc020caa4f4fec204c72382cf905535954d64ea9db3d50d1da70ab921"
MAX_TOKENS_PAR = 1720  # maximo de 0.4.0 (prompt + respuesta), fase7-1 seccion 7


def cargar_system() -> str:
    crudo = RUTA_SYSTEM.read_bytes()
    if hashlib.sha256(crudo).hexdigest() != SYSTEM_SHA256:
        raise RuntimeError("prompts/sp-0.4.1-1.txt no coincide con su sha256 registrado")
    return crudo.decode("utf-8")


@dataclass
class Par:
    """Un par de entrenamiento: mensajes de entrada (system, historial, ultimo user), respuesta objetivo y trazabilidad."""
    id: str
    familia: str
    subfamilia: str
    mensajes: list[dict]
    respuesta: str
    entrada: dict
    plantilla_p: str = ""
    plantilla_r: str = ""
    meta: dict = field(default_factory=dict)

    def a_dict(self, semilla: int) -> dict:
        return {
            "id": self.id, "familia": self.familia, "subfamilia": self.subfamilia,
            "instruction": self.mensajes[-1]["contenido"], "response": self.respuesta,
            "mensajes": self.mensajes, "perdida": "ultimo_assistant",
            "source": f"techo360-generador-0.4.1/{self.subfamilia}", "version_prompt": VERSION_PROMPT,
            "system_sha256": SYSTEM_SHA256, "semilla": semilla, "entrada": self.entrada,
            "plantilla_pregunta": self.plantilla_p, "plantilla_respuesta": self.plantilla_r, **self.meta,
        }


class Entorno:
    """Datos del snapshot + pipeline real. Una instancia por proceso."""

    def __init__(self, rag=None):
        self.d = DatosSnapshot()
        self.system = cargar_system()
        ens.cargar_system = lambda *a, **k: self.system  # el backend carga sp-0.4.0-1; el entrenamiento usa sp-0.4.1-1
        settings.chatbot_rag_activo = True
        self.rag = rag
        self.hoy = HOY
        self.catalogo = self.d.catalogo

    # ------------------------------------------------------------------ pipeline real
    def previa_de(self, preguntas: list[str]):
        """Resolucion efectiva del turno anterior (como `pipeline.responder`)."""
        return resolver_cadena(preguntas, self.catalogo, self.hoy) if preguntas else None

    def preparar(self, pregunta: str, *, huecos: list[dict] | None = None, historial: list[dict] | None = None,
                 previas: list[str] | None = None, rag_resultados: list[dict] | None = None, usar_rag: bool = True) -> dict:
        """-> el dict de `preparar_consulta` ({"accion": "consultar"|"aclarar", "peticion", "notas", "resolucion", ...})
        mas `rag_resultados` (lo que devolvio el recuperador, para re-armar sin base)."""
        hc = {(h["variable"], h["divipola"], int(h["anio"])): h.get("motivo") for h in (huecos or [])}
        leer, completar, score_fn = self.d._fabrica(hc)
        usados: dict = {}

        def rag_fn(p):
            if rag_resultados is not None:
                usados["r"] = rag_resultados
            elif usar_rag and self.rag is not None:
                usados["r"] = self.rag.buscar(p)
            else:
                usados["r"] = []
            return usados["r"]

        previa = self.previa_de(previas or [])
        r = asyncio.run(preparar_consulta(
            pregunta, None, dict(META), hoy=self.hoy, catalogo=self.catalogo, rag_fn=rag_fn,
            historial=historial, previa=previa, leer_serie_fn=leer, completar=completar, score_fn=score_fn,
        ))
        r["rag_resultados"] = usados.get("r")
        return r

    def resolucion_de(self, pregunta: str):
        return resolver(pregunta, self.catalogo, self.hoy)

    # ------------------------------------------------------------------ re-armado (prueba dorada)
    def rearmar(self, par: dict) -> list[dict] | None:
        """Re-arma los mensajes de entrada de un par guardado, sin red ni base. None si el pipeline no consulta."""
        e = par["entrada"]
        r = self.preparar(
            e["pregunta"], huecos=e.get("huecos"), historial=e.get("historial"), previas=e.get("previas"),
            rag_resultados=e.get("rag_resultados"), usar_rag=bool(e.get("rag_resultados")),
        )
        return r["peticion"]["mensajes"] if r["accion"] == "consultar" else None

    # ------------------------------------------------------------------ pruebas de grafica (validador real del backend)
    def validar_grafica(self, texto: str, huecos: list[dict] | None = None) -> dict | None:
        """`procesar_grafica` del backend sobre el texto de una respuesta -> resultado (valida, motivo, payload) o None sin bloque."""
        from services.orquestador.grafica_bloque import procesar_grafica
        hc = {(h["variable"], h["divipola"], int(h["anio"])): h.get("motivo") for h in (huecos or [])}
        leer, completar, score_fn = self.d._fabrica(hc)

        async def universo(variables, a0, a1):  # estadisticos ficticios: aqui solo se valida la ESPECIFICACION y que haya datos
            return {v: {"media": 0.0, "min": 0.0, "q1": 0.0, "mediana": 0.0, "q3": 0.0, "max": 0.0, "n": 1} for v in variables}

        async def score_filas(m, a):
            from services.orquestador.contexto import score_con_filas_base
            return await score_con_filas_base(m, a, None, leer)

        _, grafica = asyncio.run(procesar_grafica(
            texto, set(self.catalogo.por_codigo), leer_serie_fn=leer, completar=completar, score_fn=score_fn,
            municipios=self.catalogo.por_codigo, score_con_filas=score_filas, universo_fn=universo,
        ))
        return grafica


# ---------------------------------------------------------------------- tokens (plantilla de chat de Llama 3.2, multi-turno)
def prompt_multiturno(mensajes: list[dict], fecha: str = "18 Sep 2026") -> str:
    """Los mensajes de entrada tal como los renderiza el chat template, hasta la cabecera del asistente."""
    partes = ["<|begin_of_text|>"]
    for i, m in enumerate(mensajes):
        contenido = m["contenido"]
        if m["rol"] == "system":
            contenido = f"Cutting Knowledge Date: December 2023\nToday Date: {fecha}\n\n{contenido}"
        partes.append(f"<|start_header_id|>{m['rol']}<|end_header_id|>\n\n{contenido}<|eot_id|>")
    partes.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    return "".join(partes)


def sha256_texto(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def escribir_jsonl(ruta: Path, filas: list[dict]) -> str:
    """JSONL con \\n, UTF-8 sin BOM, claves en el orden dado. Devuelve el sha256 del archivo."""
    datos = "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas).encode("utf-8")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return hashlib.sha256(datos).hexdigest()
