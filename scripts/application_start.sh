#!/bin/bash
set -Eeuo pipefail

APP_DIR="/home/ec2-user/localeats"
VENV_DIR="$APP_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"

echo "[ApplicationStart] start"

cd "$APP_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Virtualenv python not found: $PYTHON_BIN"
  exit 1
fi

"$PYTHON_BIN" --version
"$PYTHON_BIN" -m pip --version

"$PYTHON_BIN" manage.py migrate --noinput
"$PYTHON_BIN" manage.py collectstatic --noinput

systemctl restart httpd
systemctl enable httpd

echo "[ApplicationStart] done"