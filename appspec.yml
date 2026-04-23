#!/bin/bash
set -e

APP_DIR="/home/ec2-user/localeats"
VENV_DIR="$APP_DIR/venv"

echo "[ApplicationStart] start"

cd "$APP_DIR"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  if [ -f "/home/ec2-user/venv/bin/activate" ]; then
    VENV_DIR="/home/ec2-user/venv"
  else
    echo "Virtualenv not found"
    exit 1
  fi
fi

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py collectstatic --noinput

sudo systemctl daemon-reload

if sudo systemctl list-unit-files | grep -q "^httpd.service"; then
  sudo systemctl restart httpd
  sudo systemctl enable httpd
else
  echo "httpd service not found"
  exit 1
fi

echo "[ApplicationStart] done"