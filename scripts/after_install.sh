#!/bin/bash
set -e

APP_DIR="/home/ec2-user/localeats"

echo "[AfterInstall] start"

cd "$APP_DIR"

sudo chown -R ec2-user:ec2-user "$APP_DIR"
sudo find "$APP_DIR/scripts" -type f -name "*.sh" -exec chmod +x {} \;

echo "[AfterInstall] done"