#!/bin/bash

# Script para executar o probe diretamente, sem Docker

echo "===== Iniciando Uptime Probe (modo local) ====="

# Verificar se Python e pip estão instalados
if ! command -v python3 &> /dev/null; then
    echo "Python3 não encontrado. Por favor, instale o Python3."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "pip3 não encontrado. Por favor, instale o pip3."
    exit 1
fi

# Verificar se ping está instalado
if ! command -v ping &> /dev/null; then
    echo "ping não encontrado. Por favor, instale o pacote iputils-ping."
    exit 1
fi

# Instalar dependências
echo "Instalando dependências Python..."
pip3 install -r requirements.txt

# Criar diretório de logs
mkdir -p logs

# Obter configurações
read -p "Digite a API key do probe: " API_KEY
read -p "Digite a URL do servidor (padrão: http://localhost:5001): " SERVER_URL
SERVER_URL=${SERVER_URL:-http://localhost:5001}
read -p "Digite o intervalo de atualização de jobs em segundos (padrão: 60): " FETCH_INTERVAL
FETCH_INTERVAL=${FETCH_INTERVAL:-60}
read -p "Digite o intervalo de heartbeat em segundos (padrão: 20): " HEARTBEAT_INTERVAL
HEARTBEAT_INTERVAL=${HEARTBEAT_INTERVAL:-20}

# Exportar variáveis de ambiente
export API_KEY="$API_KEY"
export SERVER_URL="$SERVER_URL"
export FETCH_INTERVAL="$FETCH_INTERVAL"
export HEARTBEAT_INTERVAL="$HEARTBEAT_INTERVAL"

# Executar o probe
echo "Iniciando o probe..."
python3 -u probe.py
