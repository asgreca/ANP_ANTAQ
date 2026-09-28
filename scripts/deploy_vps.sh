#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="tcc-prod"
REMOTE_DIR="~/dlcm-normas-anp-antaq"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Sincronizando arquivos de código com o VPS ($REMOTE_HOST)..."
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR"

rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' --exclude 'data' --exclude 'logs' \
    "$LOCAL_DIR/" "$REMOTE_HOST:$REMOTE_DIR/"

echo "==> Configurando ambiente virtual Python e dependencias no VPS..."
ssh "$REMOTE_HOST" "bash -c '
    cd $REMOTE_DIR
    if [ ! -d venv ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    playwright install chromium
    chmod +x scripts/*.sh
    echo \"Ambiente configurado com sucesso no VPS!\"
'"

echo "==> Deploy concluido!"
