"""Puntajes 1-5 de la rubrica del holdout_v3_3 (T-124), asignados A CIEGAS por una IA (Claude) a las 280 respuestas mezcladas sin etiqueta,
con los criterios de training/rubrica_holdout_v3_3.json, antes de abrir la clave. Se unen las 9 partes en que se puntuo."""
import importlib.util, os
P = {}
for n in ("01", "02", "03", "04a", "04b", "05", "06", "07", "08", "09"):
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"puntajes_parte{n}.py")
    spec = importlib.util.spec_from_file_location("p" + n, ruta); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert not set(P) & set(m.P), "ids repetidos"
    P.update(m.P)
PUNTAJES = P
