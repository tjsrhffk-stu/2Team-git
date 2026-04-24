#!/bin/bash
set -e

echo "[ValidateService] start"

sleep 5

curl -I http://127.0.0.1/ || exit 1

echo "[ValidateService] done"