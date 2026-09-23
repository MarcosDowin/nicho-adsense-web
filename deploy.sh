#!/usr/bin/env bash
# Compila el sitio y sube los cambios a GitHub; Cloudflare Pages (conectado al
# repo) despliega automaticamente al detectar el push.
#
# Es un envoltorio fino sobre scripts/deploy.py: reusa esa logica (ya probada)
# en vez de duplicarla, pero te da el punto de entrada `deploy.sh` como pediste.
#
# Uso:
#   ./deploy.sh                    build + commit + push a la rama actual
#   ./deploy.sh --branch gh-pages  publica solo dist/ en una rama dedicada
#   ./deploy.sh --dry-run          muestra que cambios subiria, sin tocarlos
#   ./deploy.sh --no-build         sube el dist/ actual sin recompilar

set -euo pipefail
cd "$(dirname "$0")"

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  echo "[ERROR] No se encuentra el entorno virtual .venv. Ejecuta primero:"
  echo "        python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt"
  exit 1
fi

"$PYTHON" scripts/deploy.py "$@"
