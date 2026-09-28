#!/usr/bin/env bash
set -euo pipefail

# Diretorio base da aplicacao no VPS
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Ativar ambiente virtual
source "$PROJECT_DIR/venv/bin/activate"

# Garantir diretorio de logs
mkdir -p "$PROJECT_DIR/logs"
LOG_FILE="$PROJECT_DIR/logs/dou_cron.log"

DATA_EXECUCAO=$(date +"%d-%m-%Y")
HORA_INICIO=$(date +"%Y-%m-%d %H:%M:%S")

echo "==========================================================" >> "$LOG_FILE"
echo "[$HORA_INICIO] Iniciando monitoramento diario DOU: $DATA_EXECUCAO" >> "$LOG_FILE"
echo "==========================================================" >> "$LOG_FILE"

# Executar pipeline unificado para a data de hoje
python3 main.py --data "$DATA_EXECUCAO" >> "$LOG_FILE" 2>&1 || {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] [ERRO] Falha na execucao do pipeline" >> "$LOG_FILE"
    exit 1
}

HORA_FIM=$(date +"%Y-%m-%d %H:%M:%S")
echo "[$HORA_FIM] Coleta concluida com sucesso." >> "$LOG_FILE"
