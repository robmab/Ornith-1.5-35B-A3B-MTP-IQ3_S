#!/bin/bash

# Ornith-1.5-35B-A3B-MTP IQ3_S (mradermacher, 15.6GB) — la cabeza MTP de
# fabrica venia SIN ENTRENAR (std=0.0200 en todos los tensores, puro init,
# confirmado en huggingface.co/ornith-ai/Ornith-1.5-35B-A3B/discussions/10).
# Este archivo lleva la cabeza MTP re-entrenada por shisa-ai (destilacion KL),
# aceptacion de draft ~69% en codigo segun su benchmark, frente al ~10-28%
# que dabamos con la cabeza rota. Cabe en 16GB igual que la IQ3_XXS anterior.

CTX_SIZE="${1:-262144}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$EXE_DIR"

./llama-server.exe -m models/Ornith-1.5-35B-A3B-MTP-IQ3_S/Ornith-1.5-35B-A3B-MTP.i1-IQ3_S.gguf \
    --host 0.0.0.0 \
    --port 10001 \
    --api-key apikey \
    --device Vulkan0 \
    --n-gpu-layers 99 \
    --load-mode mlock \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --flash-attn on \
    --ctx-size "$CTX_SIZE" \
    --parallel 1 \
    --jinja \
    --reasoning off \
    --no-reasoning-preserve \
    --spec-type draft-mtp \
    --spec-draft-n-max 2 \
    --spec-draft-p-min 0.05 \
    --temp 0.3 \
    --top-p 0.95 \
    --top-k 20 \
    --min-p 0 \
    --repeat-penalty 1.0 \
    --batch-size 2048 \
    --ubatch-size 512 \
    --mmproj models/Ornith-1.5-35B-A3B-MTP-IQ3_S/Ornith-1.5-35B-A3B-MTP.mmproj-f16.gguf


#   VISION (no descargada a propósito, dejar comentado)
#   --mmproj models/Ornith-1.5-35B-A3B-IQ3_XXS/mmproj-Ornith-1.5-35B-A3B-f16.gguf \

#   PARA DESACTIVAR EL MODO THINKING (respuestas más rápidas, menos razonamiento):
#   --reasoning off \

#   SI ARRANCA SIN CABER, offload mínimo (no debería hacer falta, ya lo
#   confirmamos con el archivo de AtomicChat del mismo tamaño):
#   --n-cpu-moe 2 \

#   SI EL LOG DE ARRANQUE NO MUESTRA "creating MTP draft context" (es decir,
#   si este archivo de Bartowski tampoco trae el MTP pese a lo que dice su
#   ficha), quitar estas 3 líneas y volver al comportamiento sin MTP:
#   --spec-type draft-mtp \
#   --spec-draft-n-max 2 \
#   --spec-draft-p-min 0.1 \

#   POR QUÉ ESTA CONFIG (llama-bench + context-sweep.ps1 v2, 26/09):
#   - cache-type-k/v en q8_0: cuantizar a q4_0 NO da mas tg128 (dentro del
#     margen de error en todos los depths probados), solo ahorra VRAM. Sin
#     necesidad real de esa VRAM, no compensa perder calidad de KV a cambio
#     de nada.
#   - batch-size 2048 + ubatch-size 512: en pp2048 pasa de ~950 a ~1660 tok/s
#     en d0 (y se mantiene la ventaja en todo el rango de depth). No toca la
#     generacion (tg128 igual que con ubatch 128), pero Copilot manda prompts
#     largos de golpe y ahi es donde se nota.
#   - ctx-size 40960: el context-sweep.ps1 v2 con prompt real (no relleno)
#     encontro un MURO real entre 40960 y 45056 tokens de contexto usado:
#     de 54 tok/s cae a 40 (-25%) y sigue empeorando hasta -41% a 53248.
#     NO es VRAM (la memoria compartida crece suave, sin salto ahi) - es
#     coste de computo de las capas de atencion completa + la cabeza
#     MTP rota (ver arriba) degradandose aun mas con contexto largo. El
#     llama-bench SIN mtp solo caia un 9% hasta d65536, o sea que parte del
#     muro puede ser la cabeza MTP sin entrenar, no el modelo en si. Con la
#     cabeza de shisa-ai (este archivo), pendiente repetir el sweep fino
#     entre 40960-53248 para ver si el muro se suaviza o se mantiene igual.
#   - maxInputTokens/maxOutputTokens en VS Code Copilot deben sumar <= 40960
#     mientras no se confirme que el muro se movio con la cabeza nueva.

#   VERSIONES ANTERIORES, por si hace falta comparar:
#   - Bartowski IQ3_XXS (14.28GB), con la cabeza MTP de fabrica SIN entrenar
#     (std=0.0200, puro init) — queda en models/Ornith-1.5-35B-A3B-IQ3_XXS/
#   - AtomicChat AD-IQ3_S-IQ3_XXS, sin MTP en absoluto — queda en
#     models/Ornith-1.5-35B-A3B-AD-IQ3_S-IQ3_XXS/
