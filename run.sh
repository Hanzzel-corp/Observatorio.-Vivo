#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# P2 #27: Solo crear venv si no existe
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  # Marcar que se acaba de crear (necesita pip install)
  touch ".venv/just_created"
fi

source .venv/bin/activate

# P2 #27: Solo correr pip install si .venv se acaba de crear o requirements.txt cambió
RUN_PIP=false
if [ -f ".venv/just_created" ]; then
  RUN_PIP=true
  rm ".venv/just_created"
elif [ ! -f ".venv/requirements.md5" ]; then
  RUN_PIP=true
else
  # Verificar si requirements.txt cambió comparando md5
  CURRENT_MD5=$(md5sum requirements.txt 2>/dev/null | cut -d' ' -f1)
  STORED_MD5=$(cat .venv/requirements.md5 2>/dev/null)
  if [ "$CURRENT_MD5" != "$STORED_MD5" ]; then
    RUN_PIP=true
  fi
fi

if [ "$RUN_PIP" = true ]; then
  echo "📦 Instalando dependencias..."
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  # Guardar hash actual
  md5sum requirements.txt > .venv/requirements.md5
  echo "✅ Dependencias actualizadas"
else
  echo "📦 Dependencias sin cambios (saltando pip install)"
fi

echo ""
echo "Observatorio Vivo v6 iniciado en:"
echo "  http://127.0.0.1:8765"
echo ""
uvicorn app:app --reload --host 127.0.0.1 --port 8765
