#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

info() {
  printf '\n[wall-e-bot] %s\n' "$1"
}

copy_if_missing() {
  local source_file="$1"
  local target_file="$2"

  if [ -f "$target_file" ]; then
    info "Existe $target_file; no se sobrescribe."
    return
  fi

  cp "$source_file" "$target_file"
  info "Creado $target_file desde $source_file."
}

install_ollama_if_missing() {
  if command -v ollama >/dev/null 2>&1; then
    info "Ollama ya esta instalado."
    return
  fi

  info "Ollama no esta instalado; instalando con el script oficial."
  curl -fsSL https://ollama.com/install.sh | sh
}

start_ollama_if_needed() {
  if ollama list >/dev/null 2>&1; then
    info "Ollama responde correctamente."
    return
  fi

  info "Iniciando Ollama en background para descargar el modelo."
  nohup ollama serve >/tmp/wall-e-bot-ollama.log 2>&1 &
  sleep 3
}

detect_model() {
  local model
  model="$(grep -E '^OLLAMA_MODEL=' .env 2>/dev/null | tail -n 1 | cut -d '=' -f 2- || true)"

  if [ -z "$model" ]; then
    model="qwen2.5:1.5b"
  fi

  printf '%s' "$model"
}

install_python_dependencies() {
  info "Instalando dependencias Python."

  if command -v python3 >/dev/null 2>&1; then
    python3 -m pip install -r requirements.txt
    return
  fi

  if command -v python >/dev/null 2>&1; then
    python -m pip install -r requirements.txt
    return
  fi

  printf '\nERROR: No se encontro python ni python3 en PATH. Instala Python antes de continuar.\n' >&2
  exit 1
}

pull_model_if_missing() {
  local model="$1"

  if ollama list | awk 'NR > 1 {print $1}' | grep -Fx "$model" >/dev/null 2>&1; then
    info "Modelo $model ya esta instalado."
    return
  fi

  info "Descargando modelo $model."
  ollama pull "$model"
}

info "Preparando archivos locales no versionados."
copy_if_missing ".env.example" ".env"
copy_if_missing "memory/memory.example.md" "memory/memory.md"
copy_if_missing "notas/notas_e_ideas.example.md" "notas/notas_e_ideas.md"

install_python_dependencies
install_ollama_if_missing
start_ollama_if_needed
MODEL="$(detect_model)"
pull_model_if_missing "$MODEL"

info "Instalacion base terminada. Edita .env y completa TELEGRAM_TOKEN y BACKEND_SECRET_KEY antes de ejecutar python main.py."
