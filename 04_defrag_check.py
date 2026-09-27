#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASO 4 del orden de tuning: chequeo de fragmentacion del KV cache en
sesiones largas (como las de un agente que va creciendo turno a turno).

En la build probada la noche del 2026-09-26/27, --defrag-thold estaba
DEPRECADO y no hacia nada (warning en el .err al arrancar) -- este script
NO barre valores de ese flag por eso (no tiene sentido), pero SI corre una
conversacion que crece turno a turno con cache_prompt activo por defecto,
para ver si aparecen picos anomalos de prompt_ms que no sigan la tendencia
normal de crecimiento con el contexto (eso si seria sintoma de
fragmentacion real, gestionada o no por un flag).

Antes de correrlo en un build nuevo, comprueba si --defrag-thold sigue
deprecado:
    ./llama-server.exe --help | Select-String -Pattern "defrag"
Si ya NO aparece como deprecado, dimelo -- ese caso si merece un barrido de
valores de verdad, que este script no hace.

Uso:
    ./04_defrag_check.sh --exe-dir "/d/IA/llama-b11146-bin-win-vulkan-x64" \
        --model-path "models/.../archivo.gguf" --model-id ornith-1.5-35b-mtp-iq3s
"""
import argparse
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

TURN_PROMPTS = [
    "Dame un ejemplo de componente Vue 3 con Composition API que muestre un contador.",
    "Ahora anadele un boton para resetear el contador a 0.",
    "En Python con TurboGears, como defino una ruta que acepte un parametro de URL.",
    "Y si quiero que ese parametro sea opcional, como lo hago.",
    "Explica la diferencia entre ref() y reactive() en Vue 3.",
    "Dame un ejemplo corto de watch() sobre una propiedad reactive.",
    "Como valido un formulario en Vue 3 antes de enviarlo.",
    "Que hace watchEffect() de forma distinta a watch().",
    "En TurboGears, como accedo a la sesion de base de datos dentro de un controller.",
    "Como manejo una transaccion que puede fallar y necesita rollback.",
    "Dame un ejemplo de computed() que dependa de dos refs distintos.",
    "Como se testea un composable de Vue 3 con Vitest.",
    "Cual es la diferencia entre emits y props en un componente hijo.",
    "Como paso un slot con contenido dinamico a un componente hijo.",
    "En Python, como itero un diccionario y modifico sus valores a la vez sin errores.",
    "Que problema tiene modificar una lista mientras la recorro con un for.",
    "Como estructuro un store de Pinia para manejar el estado de un carrito.",
    "Anade una accion async al store anterior que llame a una API.",
    "Como manejo el estado de carga (loading) mientras se resuelve esa llamada.",
    "Resume en 3 frases todo lo que hemos hablado en esta conversacion.",
    "Dame un ejemplo de directiva personalizada v-focus en Vue 3.",
    "Como uso provide/inject para pasar datos entre componentes lejanos.",
    "Cual es el ciclo de vida de un componente Vue 3, en orden.",
    "En que hook harias una llamada a la API al montar el componente.",
    "Ultima pregunta: resume que patrones de Vue hemos cubierto en esta sesion.",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    common.add_common_server_args(ap)
    ap.add_argument("--turns", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--spike-ratio", type=float, default=1.8,
                     help="cur > avg_vecinos * ratio se marca como pico anomalo")
    args = ap.parse_args()

    base_url = "http://%s:%d/v1/chat/completions" % (
        "localhost" if args.host == "0.0.0.0" else args.host, args.port)
    health_url = "http://%s:%d/health" % (
        "localhost" if args.host == "0.0.0.0" else args.host, args.port)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    transcript_path, transcript_file = common.start_transcript(logs_dir, "defrag_check")
    print("Log de esta corrida: %s" % transcript_path)

    common.stop_llama_server()
    stamp = datetime.now().strftime("%H%M%S")
    log_path = os.path.join(logs_dir, "server_defrag_check_%s.log" % stamp)
    err_path = log_path + ".err"
    argv = common.base_argv(args)

    proc, out_f, err_f = common.start_server(args.exe_dir, argv, log_path, err_path)
    print("Arrancando server (PID %d)" % proc.pid)
    if not common.wait_server_ready(health_url, args.startup_timeout):
        print("El server no respondio a tiempo.")
        common.stop_llama_server()
        out_f.close(); err_f.close()
        sys.exit(1)

    # Aviso si el build ya NO trae --defrag-thold deprecado (para no asumir
    # ciegamente que sigue siendo un no-op).
    with open(err_path, "r", encoding="utf-8", errors="replace") as f:
        err_content = f.read()
    if "defrag-thold is deprecated" not in err_content:
        print("AVISO: no veo el warning de deprecacion de --defrag-thold en este build.")
        print("       puede que aqui SI tenga efecto -- si te interesa, habria que")
        print("       volver a montar un barrido de valores de verdad (no lo hace este script).")
        print()

    messages = []
    turns = []
    n_turns = min(args.turns, len(TURN_PROMPTS))
    for i in range(n_turns):
        messages.append({"role": "user", "content": TURN_PROMPTS[i]})
        try:
            r = common.call_model(base_url, args.api_key, args.model_id, messages,
                                   max_tokens=args.max_tokens, timeout=120)
        except Exception as e:
            print("  Turno %2d: ERROR %s" % (i + 1, e))
            continue
        t = r.get("timings", {}) or {}
        reply = r["choices"][0]["message"]["content"]
        messages.append({"role": "assistant", "content": reply})

        prompt_ms = t.get("prompt_ms", 0)
        gen_tps = t.get("predicted_per_second", 0)
        cache_n = t.get("cache_n", 0)
        turns.append({"turn": i + 1, "prompt_ms": prompt_ms, "gen_tps": gen_tps, "cache_n": cache_n})
        print("  Turno %2d: prompt_ms=%8.0f  cache_n=%6s  gen=%5.1f tok/s" % (i + 1, prompt_ms, cache_n, gen_tps))

    common.stop_llama_server()
    out_f.close(); err_f.close()

    print()
    print("Buscando picos anomalos...")
    found = False
    for i in range(1, len(turns) - 1):
        prev_ms = turns[i - 1]["prompt_ms"]
        cur_ms = turns[i]["prompt_ms"]
        next_ms = turns[i + 1]["prompt_ms"]
        avg_neighbors = (prev_ms + next_ms) / 2
        if avg_neighbors > 0 and cur_ms > avg_neighbors * args.spike_ratio:
            found = True
            print("  >> Posible pico en turno %d: prompt_ms=%.0f (vecinos ~%.0f)" % (
                turns[i]["turn"], cur_ms, avg_neighbors))
    if not found:
        print("  Ninguno por encima de %.1fx la media de sus vecinos." % args.spike_ratio)

    print()
    print("Log del server: %s" % log_path)

    transcript_file.close()


if __name__ == "__main__":
    main()
