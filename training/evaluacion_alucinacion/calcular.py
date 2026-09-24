"""Agrega los puntajes por version y categoria. Las preguntas marcadas 'M'
(confianza media del evaluador) quedan FUERA del porcentaje principal."""
import importlib
import json
import sys

ETIQUETAS = {"C": "correcta", "I": "incorrecta", "A": "alucinacion", "N": "se_nego"}


def cargar(version):
    mod = importlib.import_module(f"puntajes_{version}")
    datos = json.load(open(f"respuestas_{version}.json", encoding="utf-8"))
    cat_por_n = {r["n"]: r["categoria"] for r in datos["resultados"]}
    return mod.PUNTAJES, cat_por_n


def resumen(version):
    puntajes, cat_por_n = cargar(version)
    punt = {n: p for n, p in puntajes.items() if p != "M"}
    aparte = [n for n, p in puntajes.items() if p == "M"]
    total = len(punt)
    conteo = {k: sum(1 for p in punt.values() if p == k) for k in ETIQUETAS}

    print(f"\n{'='*66}\nVERSION {version.upper()}  --  {total} preguntas puntuables "
          f"({len(aparte)} apartadas por confianza media)\n{'='*66}")
    for k, nombre in ETIQUETAS.items():
        print(f"  {nombre:<14}{conteo[k]:>4}   {100*conteo[k]/total:>5.1f}%")
    print(f"  {'-'*30}\n  ALUCINACION GLOBAL: {100*conteo['A']/total:.1f}%  "
          f"({conteo['A']}/{total})")

    print(f"\n  Por categoria:")
    print(f"    {'categoria':<14}{'n':>4}{'aluc':>7}{'%aluc':>8}{'corr':>7}{'incorr':>8}{'nego':>6}")
    cats = {}
    for n, p in punt.items():
        cats.setdefault(cat_por_n[n], []).append(p)
    filas = []
    for cat, ps in sorted(cats.items(), key=lambda kv: -100*sum(1 for p in kv[1] if p == "A")/len(kv[1])):
        a = sum(1 for p in ps if p == "A")
        filas.append((cat, len(ps), a, 100*a/len(ps),
                      sum(1 for p in ps if p == "C"), sum(1 for p in ps if p == "I"),
                      sum(1 for p in ps if p == "N")))
        print(f"    {cat:<14}{len(ps):>4}{a:>7}{100*a/len(ps):>7.1f}%{filas[-1][4]:>7}{filas[-1][5]:>8}{filas[-1][6]:>6}")
    return {"version": version, "total": total, "conteo": conteo,
            "pct_aluc": 100*conteo["A"]/total, "por_categoria": filas, "apartadas": aparte}


if __name__ == "__main__":
    versiones = sys.argv[1:] or ["v2"]
    resumenes = [resumen(v) for v in versiones]

    if len(resumenes) == 2:
        a, b = resumenes
        print(f"\n{'='*66}\nCOMPARACION {a['version'].upper()} vs {b['version'].upper()}\n{'='*66}")
        print(f"  Alucinacion global:  {a['version']}={a['pct_aluc']:.1f}%   "
              f"{b['version']}={b['pct_aluc']:.1f}%   "
              f"diferencia={b['pct_aluc']-a['pct_aluc']:+.1f} puntos")
        print(f"\n  Por categoria (% de alucinacion):")
        print(f"    {'categoria':<14}{a['version']:>8}{b['version']:>8}{'dif':>9}")
        da = {f[0]: f[3] for f in a["por_categoria"]}
        db = {f[0]: f[3] for f in b["por_categoria"]}
        for cat in sorted(set(da) | set(db), key=lambda c: db.get(c, 0) - da.get(c, 0)):
            print(f"    {cat:<14}{da.get(cat,0):>7.1f}%{db.get(cat,0):>7.1f}%{db.get(cat,0)-da.get(cat,0):>+8.1f}")
