# Tuning de llama-server (Ornith / cualquier modelo futuro)

Kit para repetir el proceso de ajuste cada vez que cambies de modelo, versión
o cuantización, sin tener que reinventarlo. Todo en bash + Python (nada de
PowerShell) — cada `.sh` es un lanzador de tres líneas que llama a un `.py`
con la lógica real.

## Arranque rápido (uso diario)

Dos comandos, cada uno en **su propia terminal** (Git Bash). Las dos ventanas
tienen que quedarse abiertas mientras uses el chat.

```bash
# 1) La IA local (llama-server, puerto 10001, con --api-key)
./ornith-1.5-35b.sh

# 2) Open WebUI con búsqueda web -> abre http://localhost:3000
./llm-search/start-open-webui.sh
```

- Arranca siempre primero el 1 y espera a que termine de cargar el modelo.
- Si tienes las capacidades por defecto configuradas (ver más abajo), no
  hace falta tocar nada más en cada chat nuevo; si no, activa **Web Search**
  a mano con el icono `+` junto al cuadro de texto.
- Primera vez, o si algo falla: ver la sección
  [Conectar la IA a internet](#conectar-la-ia-a-internet-open-webui--búsqueda-web)
  al final de este README.

### Alternativa: un solo doble-clic (`Ornith-Launcher.exe`)

`llm-search/Ornith-Launcher.ps1` hace los dos pasos de arriba automáticamente:

1. Arranca `ornith-1.5-35b.sh` con la ventana **oculta desde el principio**
   (no se llega a mostrar ninguna ventana de consola) y va mostrando el
   progreso de carga del modelo tal cual sale en su log, dentro de la propia
   ventana del launcher.
2. En cuanto el puerto de llama-server responde, hace lo mismo con
   `start-open-webui.sh`.
3. Abre Open WebUI en una **ventana de navegador dedicada** (sin barra de
   direcciones ni pestañas, con un perfil aislado en
   `%TEMP%\ornith-webui-profile`), usando tu navegador predeterminado si es
   Chrome/Edge/Brave, o Edge si no lo es.
4. Oculta también su propia ventana y se queda vigilando en segundo plano
   (no se cierra del todo, porque si se cerrara no podría enterarse de
   cuándo cierras el navegador).
5. **En cuanto cierras esa ventana del navegador**, apaga llama-server y
   Open WebUI solo — no hace falta cerrar nada a mano.

Los tres procesos (llama-server, Open WebUI y el propio launcher) acaban
invisibles: no aparecen ventanas ni en la barra de tareas. Si necesitas ver
qué está pasando en algún momento, están los logs (ver más abajo), no una
ventana que reabrir.

**Configúralo una vez** — abre `Ornith-Launcher.ps1` con un editor de texto y
ajusta el bloque `CONFIGURA ESTO` al principio: la carpeta del proyecto
(`$ProjectDir` — la carpeta donde está `ornith-1.5-35b.sh`, no la del build
de llama.cpp), los puertos si los cambiaste, y la ruta a `bash.exe` si Git no
está en `C:\Program Files\Git`.

**Compilar el .exe** (una sola vez, en tu PC, con PowerShell):

```powershell
Install-Module ps2exe -Scope CurrentUser -Force
Import-Module ps2exe
Invoke-ps2exe .\llm-search\Ornith-Launcher.ps1 .\Ornith-Launcher.exe -title "Ornith Launcher"
```

Esto genera `Ornith-Launcher.exe`. Da igual en qué carpeta lo dejes o desde
dónde lo ejecutes (escritorio, accesos directos, etc.): el script siempre
trabaja sobre la carpeta fija de `$ProjectDir`, no sobre la carpeta del
propio `.exe`. Si vuelves a tocar el `.ps1` (cambias un puerto, una ruta),
repite el comando `Invoke-ps2exe` para regenerar el `.exe`.

**Logs de cada arranque**, por si algo no responde a tiempo (se sobrescriben
en cada ejecución):

```
llm-search/logs/launcher-llama.log    salida completa de ornith-1.5-35b.sh
llm-search/logs/launcher-webui.log    salida completa de start-open-webui.sh
llm-search/logs/run-llama.sh          script temporal que lanza llama-server
llm-search/logs/run-webui.sh          script temporal que lanza Open WebUI
```

Detalles a tener en cuenta:

- Si `Import-Module ps2exe` falla con "el módulo no pudo cargarse", suele ser
  la política de ejecución de scripts de Windows. Arréglalo con
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` (solo
  tu usuario, sin necesitar administrador) y repite.
- Si `PS2EXE` da error de permisos al instalar el módulo, ejecuta PowerShell
  como administrador solo para ese paso, o usa `-Scope CurrentUser` (ya
  incluido arriba).
- Windows SmartScreen puede avisar la primera vez que ejecutes un `.exe` sin
  firmar — es tuyo, así que "Más información -> Ejecutar de todas formas".
- Los tiempos de espera (`$LlamaTimeout`, `$WebUITimeout` en el `.ps1`) están
  puestos con margen, pero si tu modelo tarda mucho en cargar desde disco,
  súbelos y recompila.
- Si algo se queda colgado y no hay ventana que cerrar, mata los procesos
  desde el Administrador de tareas (busca `bash.exe`, `llama-server.exe` o
  `Ornith-Launcher.exe`) — eso apaga todo igual, aunque no hayas cerrado el
  navegador.

## Requisitos

- Git Bash (o cualquier bash en Windows).
- Python en el PATH. En Windows, `py` (el launcher oficial) es más fiable
  que `python`/`python3`, que a veces resuelven al alias de la Microsoft
  Store aunque tengas Python instalado — los `.sh` de aquí ya prueban `py`
  primero por eso.
- El server se controla con `taskkill` (Windows), así que esto está pensado
  para correr en Windows/Git Bash, no en WSL/Linux puro.

## Cómo apuntar esto a un modelo/build nuevo

Los scripts que relanzan el server (`02`, `04`, `05`) y los que no (`01`,
`03`, `benchmark_quick`) necesitan estos datos — son los únicos que hay que
cambiar al pasar de un modelo a otro:

| Flag | Qué es | Ejemplo |
|---|---|---|
| `--exe-dir` | Carpeta del build, donde vive `llama-server.exe` | `/d/IA/llama-b11146-bin-win-vulkan-x64` |
| `--model-path` | Ruta al `.gguf`, relativa a `--exe-dir` | `models/Ornith-.../archivo.gguf` |
| `--model-id` | Valor que mandas en `"model"` en cada request | `ornith-1.5-35b-mtp-iq3s` |
| `--base-url` (scripts sin relanzar server) | Endpoint del chat | `http://localhost:10001/v1/chat/completions` |

El resto de flags (`--cache-type-k/v`, `--temp`, `--batch-size`, etc.) tienen
como default lo último que dejamos validado para Ornith — cámbialos solo si
el modelo nuevo lo pide (p.ej. otra cuantización de KV cache).

## Orden de tuning: de más a menos impacto

La idea es ir fijando cada parámetro sobre los que ya has dejado atinados en
el paso anterior, no todos a la vez. Corre `benchmark_quick.sh` ANTES de
empezar (baseline de referencia) y otra vez después de cada paso, para
detectar si algo se rompió o degradó sin querer.

```bash
./benchmark_quick.sh --model-id ornith-1.5-35b-mtp-iq3s --label baseline
```

### Paso 1 — Contexto máximo real (`01_context_sweep`)

**Por qué primero**: es la restricción más dura — si el contexto que
necesitas para tu uso real (agente, Copilot con prompts largos) cae después
de un muro de rendimiento, todo lo demás se ajusta sabiendo ese límite, no
al revés. Necesitas el server YA arrancado con un `--ctx-size` al menos tan
grande como el `--max` que le pidas.

```bash
# arranca el server a mano con un --ctx-size generoso, luego:
./01_context_sweep.sh --model-id ornith-1.5-35b-mtp-iq3s --max 65536 --step 4096
```

Mira dónde aparece el primer `<-- CAE` (caída >=15% respecto al baseline de
gen tok/s). Ese es tu techo práctico — no el contexto nativo del modelo.
Anota ese valor: es el `--ctx-size` que usarás en TODOS los pasos siguientes.

### Paso 2 — Parámetros del MTP: `spec-draft-n-max` / `spec-draft-p-min` (`02_mtp_draft_params`)

**Por qué segundo**: es lo que más impacto tiene en velocidad de generación
de los que quedan por decidir (confirmado el 2026-09-26/27: subir n-max de 2
a 4 tiró la velocidad un 16% con la cabeza de este modelo). Solo aplica si
el modelo trae cabeza de draft especulativo (MTP/EAGLE/etc.) — si no, salta
este paso.

```bash
./02_mtp_draft_params.sh \
    --exe-dir "/d/IA/llama-b11146-bin-win-vulkan-x64" \
    --model-path "models/Ornith-1.5-35B-A3B-MTP-IQ3_S/Ornith-1.5-35B-A3B-MTP.i1-IQ3_S.gguf" \
    --model-id ornith-1.5-35b-mtp-iq3s \
    --ctx-size 40960
```

Lee la tabla final: `gen avg tok/s` manda, pero mira también `aceptacion avg`
y `mean len` — si al subir `n-max` la aceptación se desploma y el `mean len`
no sube en proporción, es la cabeza saturándose, no una mejora real (así fue
con Ornith). Quédate con el combo de mayor `gen avg tok/s` que además tenga
sentido en aceptación/mean-len, no el primero que parezca ganar por ruido.

### Paso 3 — Sampling: `temp` / `top-p` / `top-k` (`03_sampling_quality`)

**Por qué tercero**: no afecta a velocidad, afecta a que el código generado
sea correcto — se mide con casos de prueba automáticos (funciones Python con
tests), no a ojo. No relanza el server: `temperature`/`top_p`/`top_k` se
mandan por request, así que puedes iterar rápido sin reiniciar nada.

```bash
./03_sampling_quality.sh --model ornith-1.5-35b-mtp-iq3s --repeats 8
```

Si tu cliente (VS Code Copilot u otro) ya manda su propio `temperature` por
request, cambiar el default del server no hace nada — comprueba tu config
del cliente antes de gastar tiempo aquí.

Añade tus propios prompts a la lista `PROMPTS` en `03_sampling_quality.py`
si los 4 que hay no representan bien lo que sueles pedirle al modelo — el
harness solo sirve si los casos de prueba son representativos.

### Paso 4 — Fragmentación del KV cache en sesiones largas (`04_defrag_check`)

**Por qué cuarto**: solo importa si usas sesiones de agente largas (muchos
turnos, contexto creciendo). Es más un diagnóstico que un parámetro a
ajustar — si `--defrag-thold` sigue deprecado en tu build (el script te
avisa si ya no lo está), no hay nada que tocar, solo confirmar que no
aparecen picos anómalos de `prompt_ms` a medida que crece la conversación.

```bash
./04_defrag_check.sh \
    --exe-dir "/d/IA/llama-b11146-bin-win-vulkan-x64" \
    --model-path "models/Ornith-1.5-35B-A3B-MTP-IQ3_S/Ornith-1.5-35B-A3B-MTP.i1-IQ3_S.gguf" \
    --model-id ornith-1.5-35b-mtp-iq3s --ctx-size 40960 --turns 25
```

Si aparecen picos y el flag SÍ tiene efecto en tu build nuevo, este script
no basta — habría que montar un barrido de valores de verdad (pídemelo
cuando llegue el caso, no es difícil añadirlo sobre esta misma base).

### Paso 5 — Hilos de CPU y `--load-mode` (`05_threads_loadmode`) — menor prioridad

**Por qué último**: con todo el modelo en VRAM (`--n-gpu-layers 99`), la CPU
casi no pinta nada — confirmado que ni `-t`/`--threads-batch` ni
`--load-mode mlock` cambian nada medible. Solo merece la pena repetir esto
si cambias de hardware, o si algún día dejas capas en CPU
(`--n-gpu-layers` más bajo o `--n-cpu-moe`), que es cuando esto empezaría a
importar de verdad.

```bash
./05_threads_loadmode.sh \
    --exe-dir "/d/IA/llama-b11146-bin-win-vulkan-x64" \
    --model-path "models/Ornith-1.5-35B-A3B-MTP-IQ3_S/Ornith-1.5-35B-A3B-MTP.i1-IQ3_S.gguf" \
    --model-id ornith-1.5-35b-mtp-iq3s --ctx-size 40960
```

`--load-mode mlock` puede bajar el `WorkingSet` del proceso sin coste de
velocidad (lo vimos con Ornith) — vale la pena dejarlo puesto igualmente
aunque no gane benchmarks, es higiene gratis.

### Al terminar

Corre `benchmark_quick.sh` una última vez con la config final y compara
contra el baseline del principio. Si todo cuadra, traslada los valores
ganadores de cada paso a tu `.sh` de arranque definitivo (el que lanza
`llama-server.exe` de verdad) — este kit no lo toca ni lo genera, solo te da
los números para decidir qué escribir ahí.

## Ya resuelto, no hace falta repetir (salvo que cambie el hardware)

- `--cache-type-k/v q8_0`: confirmado con `llama-bench`, q4 no da más
  velocidad, solo ahorra VRAM que no hace falta.
- `--flash-attn on`: sin discusión en GPU moderna.
- `--batch-size 2048 --ubatch-size 512`: +75% en `pp2048` sin coste en
  generación.
- `--n-gpu-layers 99`: el warning de `common_fit_params` es inofensivo.

## No merece la pena probar (para este hardware/uso)

- `--parallel` > 1: solo aporta si sirves varias peticiones a la vez.
- `--numa`: para servidores multi-socket.
- `--rope-scaling` / `--grp-attn-*`: para extender contexto MÁS ALLÁ del
  nativo (YaRN, self-extend) — si el modelo ya es nativo a 128k/256k, no
  hace falta.
- Repartir capas a una iGPU con `--split-mode`/`--tensor-split`: la iGPU
  comparte el ancho de banda de RAM con la CPU, beneficio marginal.

## Archivos

```
common.py                  utilidades compartidas (arrancar/parar server, HTTP, parseo de logs)
01_context_sweep.{py,sh}   paso 1: techo de contexto
02_mtp_draft_params.{py,sh} paso 2: spec-draft-n-max / spec-draft-p-min
03_sampling_quality.{py,sh} paso 3: temp / top-p / top-k (calidad de codigo)
04_defrag_check.{py,sh}    paso 4: fragmentacion KV cache en sesiones largas
05_threads_loadmode.{py,sh} paso 5: hilos de CPU / --load-mode
benchmark_quick.{py,sh}    chequeo rapido de velocidad + aciertos (antes/despues de cada paso)
logs/                      logs de cada corrida (se crea solo)
```

Y, en la carpeta hermana `llm-search/` (ver la última sección):

```
llm-search/start-open-webui.sh       lanza Open WebUI sin Docker (la vía que usamos)
llm-search/Ornith-Launcher.ps1       fuente del .exe: arranca todo, oculta ventanas, apaga al cerrar el navegador
llm-search/Ornith-Launcher.exe       compilado a partir del .ps1 (no se versiona; genéralo tú con ps2exe)
llm-search/logs/                     logs de cada arranque del launcher (se crea solo)
llm-search/docker-compose.yml        alternativa: Open WebUI + SearXNG en Docker (opcional)
llm-search/searxng/settings.yml      config de SearXNG para el compose (habilita JSON)
```

## Conectar la IA a internet (Open WebUI + búsqueda web)

Ni llama.cpp ni el modelo navegan por sí solos: la búsqueda es una herramienta
que añade la aplicación cliente. Aquí usamos **Open WebUI** como cliente: él
genera la consulta, busca (DuckDuckGo), descarga las páginas y le pasa los
fragmentos relevantes al modelo. El modelo no tiene que decidir qué herramienta
llamar, que es lo que falla con una cuantización tan baja (IQ3_S).

### Piezas

| Pieza | Qué hace | Dónde |
|---|---|---|
| llama-server | Sirve el modelo (API compatible con OpenAI) | `http://localhost:10001/v1`, con `--api-key` |
| Open WebUI | Interfaz de chat + búsqueda web | `http://localhost:3000` |
| DuckDuckGo (`DDGS`) | Motor de búsqueda, sin clave ni servidor | integrado en Open WebUI |

### Instalación (una sola vez)

1. Instala `uv`: `winget install -e --id astral-sh.uv`.
2. **Cierra y abre la terminal.** El instalador modifica el PATH y la ventana
   actual no lo ve (síntoma: `uvx : no se reconoce como nombre de un cmdlet`).
3. Edita `llm-search/start-open-webui.sh` y pon tu clave en `LLAMA_API_KEY`
   (la misma que `--api-key` en `ornith-1.5-35b.sh`).
4. Lánzalo: `./llm-search/start-open-webui.sh`. La primera vez descarga
   Python 3.11 y muchas dependencias: tarda varios minutos, no lo cortes.
   Los avisos `UNEXPECTED ... embeddings.position_ids` son inofensivos.
5. Abre `http://localhost:3000` y crea el usuario admin (es local).

### Configuración en Open WebUI (una sola vez)

Las variables de entorno del script solo se leen la primera vez; después manda
lo guardado en la base de datos (`DATA_DIR`). Si algo no cuadra, se corrige aquí:

1. **Conexión al modelo** (*Ajustes → Conexiones*): URL
   `http://localhost:10001/v1`, autorización Bearer con tu `--api-key`. Verifica
   con el icono de las dos flechas, guarda y recarga (F5). Apaga la conexión de
   Ollama (`localhost:11434`): no la usamos y solo estorba.
2. **Modo de llamada a funciones** (*Panel de administración → Ajustes →
   Modelos → tu modelo → Parámetros avanzados → Modo de Llamada a Funciones*):
   ponlo en **Heredado**. Con Nativo/Predeterminado el modelo usó
   herramientas equivocadas (`search_knowledge_files`, `search_memories`) y
   nunca buscó en la web; con Heredado es Open WebUI quien busca.
3. **Búsqueda web** (*Panel de administración → Ajustes → Búsqueda Web*):
   activada, motor **DDGS**, y **6-8 resultados** (con 3 un solo resultado
   malo pesa demasiado).
4. **Prompt de sistema** del modelo (recomendado):
   > Cuando uses resultados de búsqueda web, prioriza fuentes oficiales. Si las
   > fuentes se refieren a cosas distintas o se contradicen, dilo
   > explícitamente en vez de mezclarlas en una sola respuesta.
5. En cada **chat nuevo**, activa *Web Search* con el `+` junto al cuadro de texto
   — o configura el punto siguiente para que venga activado por defecto.

### Capacidades extra del modelo (opcional)

En *Panel de administración → Ajustes → Modelos → tu modelo → Capacidades*
puedes marcar de forma permanente qué herramientas lleva activadas cada chat
nuevo con Ornith, sin tener que tocar el `+` cada vez.

**Búsqueda web activada por defecto**: marca la capacidad **Web Search** ahí.
A partir de ese momento, cualquier chat nuevo con Ornith sale ya con la
búsqueda encendida. Si no ves esa opción en Capacidades del modelo, mira
también en *Panel de administración → Ajustes → Interfaz*, donde algunas
versiones tienen un ajuste global de "herramientas activadas por defecto" en
vez de por modelo.

**Generación de imágenes — no la actives sin más**: el checkbox de
**Image Generation** por sí solo no hace nada útil. Necesita un motor de
imágenes de verdad configurado en *Panel de administración → Ajustes →
Imágenes* (Automatic1111, ComfyUI, Gemini o DALL·E). Sin eso, cuando le pidas
una imagen el modelo puede "alucinar" que tiene un intérprete de código
disponible e intentar dibujarla a mano con Python (PIL), fallando encima el
formato de etiquetas que ese intérprete exige — el resultado es código suelto
en el chat, sin ejecutar. Comprobado en septiembre de 2026: no existe ninguna
API de imágenes gratuita compatible con los motores que soporta Open WebUI —
Gemini y DALL·E exigen facturación/pago desde la primera imagen. La única vía
sin coste por imagen es local: instalar Stable Diffusion (Automatic1111 o
ComfyUI) en tu propia máquina, aunque compite por la misma VRAM que ya usa
Ornith. Si no vas a montar eso, deja **Image Generation** desactivada.

### Comprobar que funciona

Pregunta algo que el modelo no pueda saber de memoria (una versión reciente de
una librería, una noticia de esta semana). Debe aparecer un paso de "Buscando en
la web" y una respuesta con fuentes enlazadas. Si en vez de eso habla de
"bases de conocimiento", el interruptor de Web Search del chat está apagado o
el modo de llamada a funciones sigue en Nativo.

### Problemas que nos encontramos

| Síntoma | Causa | Solución |
|---|---|---|
| `docker` no existe en bash ni en PowerShell | Docker no viene instalado en Windows (necesita Docker Desktop + WSL2) | Usar la vía sin Docker (`start-open-webui.sh`) |
| `uvx` no se reconoce justo después de instalar `uv` | La terminal abierta tiene el PATH antiguo | Cerrar y abrir la terminal |
| El modelo no aparece en el selector | Open WebUI apuntaba a `:8080` y llama-server está en `:10001` | Cambiar la URL de la conexión |
| `/v1/models` da `401 Invalid API Key` en el navegador | Es normal: el navegador no manda la clave. Confirma que el servidor está vivo | Poner la `--api-key` en la conexión (Bearer) |
| `/v1/models` rechaza la conexión | llama-server no está arrancado en ese puerto | Arrancar `ornith-1.5-35b.sh` y revisar `--port` |
| El modelo recorre "bases de conocimiento" y nunca busca | Modo de llamada a funciones Nativo/Predeterminado | Poner **Heredado** |
| Respuesta que mezcla cosas distintas | Nombre ambiguo + pocos resultados + síntesis débil del modelo | Preguntar con contexto, subir a 6-8 resultados, usar el prompt de sistema |

### Límites a tener en cuenta

- Con el `--reasoning off` del servidor el modelo no "piensa de más": los
  fallos de síntesis vienen de qué fuentes se recuperan, no del razonamiento.
- Con nombres ambiguos ("World of Warcraft Forever" es a la vez un servidor
  privado 3.3.5a y el juego oficial de Blizzard) el modelo puede fundir fuentes
  distintas. Añade contexto a la pregunta y abre las fuentes enlazadas cuando
  te juegues algo.
- DuckDuckGo puede limitar el ritmo si haces muchas búsquedas seguidas.
- La búsqueda añade latencia: generar consulta, buscar, descargar y leer.

### Opcional: Docker + SearXNG

Solo si DuckDuckGo se te queda corto (límites de ritmo). SearXNG es local, sin
clave ni límites. Requiere Docker Desktop funcionando (`docker --version` y
`wsl --status` deben responder).

1. Cambia `SEARXNG_SECRET` en `llm-search/docker-compose.yml` por una cadena
   larga aleatoria y pon tu clave en `OPENAI_API_KEY`.
2. Arranca llama-server con `--host 0.0.0.0` (para que el contenedor lo
   alcance vía `host.docker.internal`) y permítelo en el firewall de Windows.
3. Para el Open WebUI de `start-open-webui.sh` antes de seguir: el compose
   también usa el puerto 3000.
4. `cd llm-search && docker compose up -d`.
5. Comprueba SearXNG en `http://localhost:8081` y el JSON en
   `http://localhost:8081/search?q=test&format=json` (un 403 indica que
   `searxng/settings.yml` no se montó bien).
6. En Open WebUI, *Búsqueda Web*: motor **searxng** y URL de consulta
   `http://searxng:8080/search?q=<query>`.

El compose y el modo *Heredado* del punto anterior siguen siendo necesarios en
esta variante.
