#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 5 (menor prioridad) del orden de tuning: -t/--threads-batch y
--load-mode (mlock incluido -- OJO: "mlock" es un VALOR de --load-mode,
no un flag independiente; confirmado con --help el 2026-09-27).

Confirmado esa noche con --n-gpu-layers 99 (todo el modelo en VRAM): NI
los hilos de batch NI el load-mode cambian gen tok/s ni pp tok/s de forma
medible. Este script queda para volver a comprobarlo rapido si cambias de
build, de hardware, o si algun dia dejas capas en CPU (--n-gpu-layers <99
o --n-cpu-moe), que es cuando esto SI podria importar.

Cada combo cambia UNA sola cosa respecto al baseline (no factorial). Usa
un prompt grande fijo con cache_prompt:false para forzar reprocesar el
prompt entero en cada peticion (si no, la cache lo enmascara a partir de
la 2a llamada).

Uso:
    ./05_threads_loadmode.sh --exe-dir "/d/IA/llama-b11146-bin-win-vulkan-x64" \
        --model-path "models/.../archivo.gguf" --model-id ornith-1.5-35b-mtp-iq3s
"""
import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

FILLER_PARAGRAPH = (
    "En TurboGears, un controller tipico expone metodos via @expose, y cada uno "
    "puede aceptar parametros de la URL o del query string. Es habitual separar "
    "la logica de negocio en un modulo de servicios, para que el controller "
    "quede fino y solo orqueste llamadas, validacion basica de entrada y la "
    "serializacion de la respuesta. En Vue 3 con Composition API, el equivalente "
    "conceptual es un composable: una funcion que encapsula estado reactivo "
    "(ref/reactive) y la logica que lo modifica, para que el componente que lo "
    "consume solo se preocupe de la plantilla y de enlazar eventos.\n"
)


def build_big_prompt(n_repeats=40):
    parts = ["Resume brevemente, sin repetir literalmente, la idea central de este "
             "texto (esta repetido varias veces a proposito para alargarlo):\n\n"]
    for r in range(n_repeats):
        parts.append("[%d] %s" % (r, FILLER_PARAGRAPH))
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    common.add_common_server_args(ap)
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()

    base_url = "http://%s:%d/v1/chat/completions" % (
        "localhost" if args.host == "0.0.0.0" else args.host, args.port)
    health_url = "http://%s:%d/health" % (
        "localhost" if args.host == "0.0.0.0" else args.host, args.port)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    transcript_path, transcript_file = common.start_transcript(logs_dir, "threads_loadmode")
    print("Log de esta corrida: %s" % transcript_path)

    big_prompt = build_big_prompt()

    combos = [
        {"name": "baseline", "extra_threads": None, "load_mode": args.load_mode},
        {"name": "threads16", "extra_threads": ["-t", "16", "--threads-batch", "16"], "load_mode": args.load_mode},
        {"name": "mlock", "extra_threads": None, "load_mode": "mlock"},
    ]

    results = []
    for combo in combos:
        print()
        print("=== %s (load-mode=%s extra=%s) ===" % (combo["name"], combo["load_mode"], combo["extra_threads"] or ""))
        common.stop_llama_server()

        stamp = datetime.now().strftime("%H%M%S")
        log_path = os.path.join(logs_dir, "server_%s_%s.log" % (combo["name"], stamp))
        err_path = log_path + ".err"
        argv = common.base_argv(args, extra_threads=combo["extra_threads"], load_mode_override=combo["load_mode"])

        proc, out_f, err_f = common.start_server(args.exe_dir, argv, log_path, err_path)
        print("  Arrancando server (PID %d)" % proc.pid)
        if not common.wait_server_ready(health_url, args.startup_timeout):
            print("  El server no respondio a tiempo, salto este combo.")
            common.stop_llama_server()
            out_f.close(); err_f.close()
            continue

        try:
            common.call_model(base_url, args.api_key, args.model_id,
                               [{"role": "user", "content": "Hola"}],
                               max_tokens=10, timeout=60, extra={"cache_prompt": False})
        except Exception:
            pass

        pp_vals, gen_vals = [], []
        for i in range(args.repeats):
            try:
                r = common.call_model(base_url, args.api_key, args.model_id,
                                       [{"role": "user", "content": big_prompt}],
                                       max_tokens=200, timeout=180, extra={"cache_prompt": False})
            except Exception as e:
                print("  Rep %2d: ERROR %s" % (i + 1, e))
                continue
            t = r.get("timings", {}) or {}
            prompt_ms = t.get("prompt_ms", 0)
            prompt_n = t.get("prompt_n", 0)
            pp_tps = (prompt_n / (prompt_ms / 1000.0)) if prompt_ms else 0
            gen_tps = t.get("predicted_per_second", 0)
            pp_vals.append(pp_tps)
            gen_vals.append(gen_tps)
            print("  Rep %2d: prompt_ms=%7.0f  prompt_n=%s  pp=%6.0f tok/s  gen=%5.1f tok/s" % (
                i + 1, prompt_ms, prompt_n, pp_tps, gen_tps))

        common.stop_llama_server()
        out_f.close(); err_f.close()

        results.append({"name": combo["name"], "pp_avg": common.avg(pp_vals), "gen_avg": common.avg(gen_vals)})

    print()
    print("=" * 60)
    print("  RESUMEN: -t/--threads-batch y --load-mode (%d repeticiones/combo)" % args.repeats)
    print("=" * 60)
    print("%-12s%-16s%-16s" % ("combo", "pp avg tok/s", "gen avg tok/s"))
    for r in results:
        print("%-12s%-16.0f%-16.1f" % (r["name"], r["pp_avg"], r["gen_avg"]))

    transcript_file.close()


if __name__ == "__main__":
    main()
