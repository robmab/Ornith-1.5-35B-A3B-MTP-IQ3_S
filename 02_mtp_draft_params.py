#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 2 del orden de tuning: --spec-draft-n-max / --spec-draft-p-min de la
cabeza MTP. Es el que mas impacto tiene en gen tok/s de los que quedan por
tocar tras fijar el contexto (paso 1) -- lo confirmamos la noche del
2026-09-26/27: subir n-max de 2 a 4 puede tirar la velocidad un 16% si la
cabeza no acepta drafts largos.

Relanza el server por combo (son flags de arranque). Un combo por variable
respecto al baseline que le pases (no hace factorial completo, para no
multiplicar relanzamientos).

Uso:
    ./02_mtp_draft_params.sh --exe-dir "/d/IA/llama-b11146-bin-win-vulkan-x64" \
        --model-path "models/Ornith-1.5-35B-A3B-MTP-IQ3_S/Ornith-1.5-35B-A3B-MTP.i1-IQ3_S.gguf" \
        --model-id ornith-1.5-35b-mtp-iq3s --ctx-size 40960
"""
import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

PROMPT = ("Escribe en Python una clase LRUCache sin usar libreria externa (nada de "
          "functools.lru_cache ni collections.OrderedDict), con metodos get(key) y "
          "put(key, value), capacidad fija, y O(1) por operacion. Incluye una breve "
          "explicacion de por que es O(1).")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    common.add_common_server_args(ap)
    ap.add_argument("--repeats", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--n-max-values", default="2,3,4",
                     help="Valores de n-max a probar (coma-separados); el primero es el baseline")
    ap.add_argument("--p-min-values", default="0.05,0.1,0.2",
                     help="Valores de p-min a probar (coma-separados); el del medio es el baseline")
    args = ap.parse_args()

    n_max_values = [v.strip() for v in args.n_max_values.split(",")]
    p_min_values = [v.strip() for v in args.p_min_values.split(",")]
    baseline_n_max = n_max_values[0]
    baseline_p_min = p_min_values[len(p_min_values) // 2]

    combos = [("baseline", baseline_n_max, baseline_p_min)]
    for n in n_max_values:
        if n != baseline_n_max:
            combos.append(("nmax" + n, n, baseline_p_min))
    for p in p_min_values:
        if p != baseline_p_min:
            combos.append(("pmin" + p, baseline_n_max, p))

    base_url = "http://%s:%d/v1/chat/completions" % (
        "localhost" if args.host == "0.0.0.0" else args.host, args.port)
    health_url = "http://%s:%d/health" % (
        "localhost" if args.host == "0.0.0.0" else args.host, args.port)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path, log_file = common.start_transcript(logs_dir, "mtp_draft_params")
    print("Log de esta corrida: %s" % log_path)

    results = []
    for name, n_max, p_min in combos:
        print()
        print("=== %s (n-max=%s p-min=%s) ===" % (name, n_max, p_min))
        common.stop_llama_server()

        stamp = datetime.now().strftime("%H%M%S")
        log_path = os.path.join(logs_dir, "server_mtp_%s_%s.log" % (name, stamp))
        err_path = log_path + ".err"
        argv = common.base_argv(args, n_max_override=n_max, p_min_override=p_min)

        proc, out_f, err_f = common.start_server(args.exe_dir, argv, log_path, err_path)
        print("  Arrancando server (PID %d)" % proc.pid)
        if not common.wait_server_ready(health_url, args.startup_timeout):
            print("  El server no respondio a tiempo, salto este combo.")
            common.stop_llama_server()
            out_f.close(); err_f.close()
            continue

        # Warm-up descartado
        try:
            common.call_model(base_url, args.api_key, args.model_id,
                               [{"role": "user", "content": "Hola, dime un dato curioso"}],
                               max_tokens=30, timeout=60)
        except Exception:
            pass

        gen_vals = []
        for i in range(args.repeats):
            try:
                r = common.call_model(base_url, args.api_key, args.model_id,
                                       [{"role": "user", "content": PROMPT}],
                                       max_tokens=args.max_tokens, timeout=180)
            except Exception as e:
                print("  Rep %2d: ERROR %s" % (i + 1, e))
                continue
            t = r.get("timings", {}) or {}
            gen_tps = t.get("predicted_per_second", 0)
            gen_vals.append(gen_tps)
            print("  Rep %2d: gen=%5.1f tok/s  tokens=%s" % (i + 1, gen_tps, t.get("predicted_n", "?")))

        common.stop_llama_server()
        out_f.close(); err_f.close()
        time.sleep(0.5)

        draft_stats = common.parse_draft_acceptance(err_path, take_last_n=args.repeats)
        results.append({
            "name": name, "n_max": n_max, "p_min": p_min,
            "gen_avg": common.avg(gen_vals),
            "acc_avg": common.avg([d["acceptance"] for d in draft_stats]) * 100,
            "mean_len_avg": common.avg([d["mean_len"] for d in draft_stats]),
        })

    print()
    print("=" * 70)
    print("  RESUMEN: spec-draft-n-max / spec-draft-p-min (%d repeticiones/combo)" % args.repeats)
    print("=" * 70)
    print("%-12s%-8s%-8s%-16s%-16s%-10s" % ("combo", "n-max", "p-min", "gen avg tok/s", "aceptacion avg", "mean len"))
    for r in results:
        print("%-12s%-8s%-8s%-16.1f%-16s%-10.2f" % (
            r["name"], r["n_max"], r["p_min"], r["gen_avg"], "%.1f%%" % r["acc_avg"], r["mean_len_avg"]))

    log_file.close()


if __name__ == "__main__":
    main()
