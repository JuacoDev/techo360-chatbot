"""5.9b: pico de memoria de Ollama en un contenedor con los limites del VPS (3 GiB, 3 CPU), con el prompt real mas largo y uno cercano al maximo teorico.

    python training/evaluacion/memoria_contenedor_5_9b.py --etiqueta ctx3072 --num-ctx 3072 [--kv q8_0 --flash] [--num-predict 400]

Un contenedor nuevo por combinacion (el pico incluye la carga). Solo lectura de datasets; el GGUF se monta de solo lectura. Salida: <DIR_SALIDA>/memoria_<etiqueta>.json
"""
import argparse
import json
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import evaluar_v040 as ev  # noqa: E402

GGUF = Path.home() / "modelos" / "techo360-v0.4.0" / "techo360-v0.4.0-Q4_K_M.gguf"
PUERTO = 11439
GIB = 1024 ** 3


def sh(*a, entrada=None) -> str:
    r = subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8", input=entrada)
    return r.stdout + r.stderr


def post(ruta, cuerpo, timeout=900):
    req = urllib.request.Request(f"http://127.0.0.1:{PUERTO}{ruta}", data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def leer_cgroup(nombre) -> dict:
    s = sh("docker", "exec", nombre, "sh", "-c", "grep -E '^(anon|file) ' /sys/fs/cgroup/memory.stat; cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak 2>/dev/null; "
          "for p in /proc/[0-9]*; do n=$(cat $p/comm 2>/dev/null); case $n in ollama*|llama*) echo \"P $n $(grep VmHWM $p/status)\";; esac; done").splitlines()
    d = {"anon": 0, "file": 0, "actual": 0, "pico_cgroup": 0, "runner_hwm_kb": 0}
    nums = []
    for linea in s:
        p = linea.split()
        if not p:
            continue
        if p[0] in ("anon", "file"):
            d[p[0]] = int(p[1])
        elif p[0] == "P" and len(p) >= 4 and p[2] == "VmHWM:":
            d["runner_hwm_kb"] = max(d["runner_hwm_kb"], int(p[3]))
        elif p[0].isdigit():
            nums.append(int(p[0]))
    if len(nums) >= 2:
        d["actual"], d["pico_cgroup"] = nums[0], nums[1]
    return d


def ntok(tok, sp, user) -> int:
    texto = tok.apply_chat_template([{"role": "system", "content": sp}, {"role": "user", "content": user}], tokenize=False, add_generation_prompt=True, date_string=ev.FECHA)
    return len(tok(texto, add_special_tokens=False)["input_ids"])


def prompt_largo_real(tok, sp):
    mejor = (0, None, None)
    for f in ("train_nuevos.jsonl", "holdout_ctx_v0_4.jsonl"):
        for p in ev.leer_jsonl(ev.DIR_R2 / f):
            n = ntok(tok, sp, p["instruction"])
            if n > mejor[0]:
                mejor = (n, p["id"], p["instruction"])
    return mejor[2], mejor[1], mejor[0]


def prompt_cercano_maximo(tok, sp, objetivo):
    """Lineas de contexto reales de train/holdout (cifras y municipios variados) hasta `objetivo` tokens totales; pregunta de 1.500 caracteres al final."""
    lineas, vistos = [], set()
    for f in ("train_nuevos.jsonl", "holdout_ctx_v0_4.jsonl"):
        for p in ev.leer_jsonl(ev.DIR_R2 / f):
            ls, _ = ev.partir_instruccion(p["instruction"])
            for linea in ls:
                if linea not in vistos and linea.startswith("["):
                    vistos.add(linea)
                    lineas.append(linea)
    pregunta = ("Con los datos anteriores, compara el deficit habitacional cuantitativo y cualitativo de los municipios listados, explica que significa la fiabilidad de cada cifra y "
                "dime si alguno esta marcado como proyeccion, citando municipio, departamento y año de cada dato. ") * 5
    pregunta = pregunta[:1500]

    def armar(k):
        u = "CONTEXTO\n" + "\n".join(lineas[:k]) + "\n\nPREGUNTA DEL USUARIO\n" + pregunta
        return u, ntok(tok, sp, u)

    lo, hi = 1, len(lineas)
    while lo < hi:
        m = (lo + hi + 1) // 2
        if armar(m)[1] <= objetivo:
            lo = m
        else:
            hi = m - 1
    return armar(lo)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--num-ctx", type=int, default=2048)
    ap.add_argument("--num-predict", type=int, default=400)
    ap.add_argument("--kv", default="")
    ap.add_argument("--flash", action="store_true")
    ap.add_argument("--objetivo", type=int, default=0, help="tokens del prompt cercano al maximo (por defecto num_ctx - num_predict - 20)")
    ap.add_argument("--imagen", default="ollama/ollama:latest")
    a = ap.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(ev.ADAPTADORES["0.4.0"]))
    sp = ev.cargar_system_sp()
    largo, id_largo, n_largo = prompt_largo_real(tok, sp)
    objetivo = a.objetivo or (a.num_ctx - a.num_predict - 20)
    cercano, n_cercano = prompt_cercano_maximo(tok, sp, objetivo)
    print(f"prompt real mas largo {id_largo}: {n_largo} tokens; prompt cercano al maximo: {n_cercano} tokens", flush=True)
    nombre = f"t360-mem-{a.etiqueta}"
    sh("docker", "rm", "-f", nombre)
    env = []
    if a.flash:
        env += ["-e", "OLLAMA_FLASH_ATTENTION=1"]
    if a.kv:
        env += ["-e", f"OLLAMA_KV_CACHE_TYPE={a.kv}"]
    sh("docker", "run", "-d", "--name", nombre, "--memory", "3g", "--memory-swap", "3g", "--cpus", "3", "-p", f"127.0.0.1:{PUERTO}:11434",
       "-v", f"{GGUF}:/g/m.gguf:ro", *env, a.imagen)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/api/version", timeout=2).read()
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        version = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/api/version").read())["version"]
        modelfile = f"FROM /g/m.gguf\nPARAMETER temperature 0.3\nPARAMETER top_p 0.9\nPARAMETER repeat_penalty 1.15\nPARAMETER num_ctx {a.num_ctx}\n"
        sh("docker", "exec", "-i", nombre, "sh", "-c", "cat > /tmp/Modelfile", entrada=modelfile)
        print(sh("docker", "exec", nombre, "ollama", "create", "m", "-f", "/tmp/Modelfile")[-60:].strip(), flush=True)
        filas = []
        for etiqueta, user in (("real_mas_largo", largo), ("cercano_al_maximo", cercano)):
            maximo = {"anon": 0, "runner_hwm_kb": 0, "pico_cgroup": 0}
            parar = threading.Event()

            def muestrear():
                while not parar.is_set():
                    d = leer_cgroup(nombre)
                    for k in maximo:
                        maximo[k] = max(maximo[k], d[k])
                    time.sleep(1.0)

            hilo = threading.Thread(target=muestrear, daemon=True)
            hilo.start()
            t0 = time.time()
            r = post("/api/chat", {"model": "m", "stream": False, "keep_alive": "30m", "messages": [{"role": "system", "content": sp}, {"role": "user", "content": user}],
                                   "options": {"num_predict": a.num_predict, "num_thread": 3, "seed": 1}})
            parar.set()
            hilo.join()
            fin = leer_cgroup(nombre)
            for k in maximo:
                maximo[k] = max(maximo[k], fin[k])
            ev_cg = sh("docker", "exec", nombre, "cat", "/sys/fs/cgroup/memory.events")
            fila = {"prompt": etiqueta, "tokens_prompt_hf": n_largo if etiqueta == "real_mas_largo" else n_cercano, "id": id_largo if etiqueta == "real_mas_largo" else None,
                    "tokens_prompt_ollama": r.get("prompt_eval_count"), "tokens_generados": r.get("eval_count"), "done_reason": r.get("done_reason"),
                    "seg": round(time.time() - t0, 1), "tok_s": round(r["eval_count"] / (r["eval_duration"] / 1e9), 2) if r.get("eval_duration") else None,
                    "anon_max_GiB": round(maximo["anon"] / GIB, 3), "runner_VmHWM_GiB": round(maximo["runner_hwm_kb"] * 1024 / GIB, 3), "pico_cgroup_GiB": round(maximo["pico_cgroup"] / GIB, 3),
                    "eventos_cgroup": " ".join(ev_cg.split())}
            filas.append(fila)
            print(json.dumps(fila, ensure_ascii=False), flush=True)
        reinicios = sh("docker", "inspect", "-f", "{{.RestartCount}} {{.State.OOMKilled}}", nombre).strip()
        out = {"etiqueta": a.etiqueta, "ollama": version, "imagen": a.imagen, "num_ctx": a.num_ctx, "num_predict": a.num_predict, "kv": a.kv or "f16", "flash": a.flash,
               "limites": "3g/3cpu", "restart_oomkilled": reinicios, "filas": filas}
        (ev.DIR_SALIDA / f"memoria_{a.etiqueta}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        sh("docker", "rm", "-f", nombre)
    return 0


if __name__ == "__main__":
    sys.exit(main())
