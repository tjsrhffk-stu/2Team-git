#!/bin/bash
set -e

APP_DIR="/home/ec2-user/localeats"

echo "[BeforeInstall] start"

sudo mkdir -p "$APP_DIR"
sudo mkdir -p /var/log/gunicorn

sudo chown -R ec2-user:ec2-user "$APP_DIR"
sudo chown -R ec2-user:ec2-user /var/log/gunicorn

echo "[BeforeInstall] done"