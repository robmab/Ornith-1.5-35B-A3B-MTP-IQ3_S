#!/usr/bin/env bash
# Lanza Open WebUI (sin Docker) apuntando a tu llama-server local.
# Requisitos: uv instalado (winget install astral-sh.uv) y llama-server en marcha.
# Abre despues http://localhost:3000

# --- Ajusta estos dos valores ---
LLAMA_PORT=10001
LLAMA_API_KEY="pon-aqui-tu-api-key"   # la misma que --api-key en ornith-1.5-35b.sh

# Los datos (usuarios, chats, ajustes) viven aqui; no lo cambies o "pierdes" la config.
export DATA_DIR="C:/open-webui/data"

# Conexion al modelo. Solo se leen la PRIMERA vez: despues manda lo guardado
# en Admin Panel > Ajustes > Conexiones.
export ENABLE_OLLAMA_API="false"
export OPENAI_API_BASE_URL="http://localhost:${LLAMA_PORT}/v1"
export OPENAI_API_KEY="${LLAMA_API_KEY}"

# Busqueda web con DuckDuckGo (tampoco pasa nada si ya esta guardado en la UI).
export ENABLE_WEB_SEARCH="true"
export WEB_SEARCH_ENGINE="duckduckgo"

# Puerto 3000 (el 8080 es el default de Open WebUI, pero puede chocar con otros servicios).
exec uvx --python 3.11 open-webui@latest serve --port 3000
