"""Entorno de la Fase B de 7.3: rutas, importacion del backend y del nucleo de proyeccion, y trazabilidad de commits.

El generador NO lee la base de datos: usa el snapshot CSV de training/datos/ y funciones REALES de:
  * techo360-backend (services/orquestador: resolutor, herencia, contexto, ensamblador, rag, grafica_*; services.proyeccion_service
    para el Score), en un worktree de origin/testing;
  * techo360-proyeccion (app/services/puntos.py y app/origen.py: huecos y proyecciones), en un worktree de origin/Testing.
`TECHO_BACKEND_DIR` y `TECHO_PROYECCION_DIR` cambian los directorios. `BREVO_API_KEY` y `JWT_SECRET_KEY` se definen con valores
inertes solo para que `core.config.Settings()` importe: ningun servicio externo se usa.
"""
import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ_CHATBOT = Path(__file__).resolve().parents[2]
RAIZ_MONOREPO = RAIZ_CHATBOT.parent
BACKEND_DIR = Path(os.environ.get("TECHO_BACKEND_DIR", RAIZ_MONOREPO / "techo360-backend-wt-ds73"))
PROYECCION_DIR = Path(os.environ.get("TECHO_PROYECCION_DIR", RAIZ_MONOREPO / "techo360-proyeccion-wt-ds73"))
SNAPSHOT_DIR = Path(os.environ.get("TECHO_SNAPSHOT_DIR", RAIZ_CHATBOT / "training" / "datos" / "snapshot_mapcalordb_20261019"))
LOCK_PROYECCION = Path(__file__).with_name("nucleo_proyeccion.lock.json")
ARCHIVOS_NUCLEO = ("app/services/puntos.py", "app/origen.py")
SEMILLA = 20261019

os.environ.setdefault("BREVO_API_KEY", "inerte-solo-para-importar")
os.environ.setdefault("JWT_SECRET_KEY", "inerte-solo-para-importar")


def preparar_rutas() -> None:
    """Pone el backend y la proyeccion en sys.path (idempotente)."""
    for d in (BACKEND_DIR, PROYECCION_DIR):
        if not d.exists():
            raise FileNotFoundError(f"No existe {d}: crea el worktree o define TECHO_BACKEND_DIR / TECHO_PROYECCION_DIR")
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} fallo: {r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout.decode("utf-8").strip()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def commit_de(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


def huella_nucleo_proyeccion() -> dict:
    """{commit, archivos: {ruta: sha256}} del worktree de proyeccion en uso (bytes del disco)."""
    return {
        "repo": "techo360-proyeccion", "commit": commit_de(PROYECCION_DIR),
        "archivos": {a: sha256_bytes((PROYECCION_DIR / a).read_bytes()) for a in ARCHIVOS_NUCLEO},
    }


def verificar_nucleo_proyeccion() -> dict:
    """Comprueba que el nucleo en uso es el registrado en el lock Y coincide con `git show <commit>:<ruta>` del repo. Falla si no."""
    lock = json.loads(LOCK_PROYECCION.read_text(encoding="utf-8"))
    actual = huella_nucleo_proyeccion()
    if actual != {k: lock[k] for k in actual}:
        raise RuntimeError(f"El nucleo de proyeccion en uso difiere del lock: {actual} != {lock}")
    for ruta, sha in lock["archivos"].items():
        origen = subprocess.run(["git", "-C", str(PROYECCION_DIR), "show", f"{lock['commit']}:{ruta}"], capture_output=True).stdout
        if sha256_bytes(origen) != sha:
            # Windows: el worktree puede tener CRLF; se compara tambien normalizando saltos de linea
            if sha256_bytes(origen.replace(b"\r\n", b"\n")) != sha256_bytes((PROYECCION_DIR / ruta).read_bytes().replace(b"\r\n", b"\n")):
                raise RuntimeError(f"{ruta} no coincide con git show {lock['commit']}")
    return actual


def huella_backend() -> dict:
    return {"repo": "techo360-backend", "commit": commit_de(BACKEND_DIR)}


def importar(nombre: str):
    preparar_rutas()
    return importlib.import_module(nombre)
