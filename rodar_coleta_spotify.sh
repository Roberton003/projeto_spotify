#!/bin/bash
# Script para executar coleta e visualização de artistas do Spotify em ambiente virtual

set -e

# Ativa o ambiente virtual ou cria se não existir
echo "[INFO] Verificando ambiente virtual..."
if [ ! -d "venv" ]; then
    echo "[INFO] Criando ambiente virtual Python..."
    python3 -m venv venv
fi
source venv/bin/activate

# Instala as dependências
if [ -f requirements.txt ]; then
    echo "[INFO] Instalando dependências..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "[INFO] requirements.txt não encontrado, instalando requests e plotly..."
    pip install requests plotly
fi

# Executa o script de coleta do Spotify
echo "[INFO] Executando coleta_spotify.py..."
python3 coleta_spotify.py

# Executa o script de visualização dos artistas
echo "[INFO] Gerando visualização dos artistas..."
python3 visualizar_artistas.py

# Abre o gráfico no navegador padrão
if [ -f artistas_visual.html ]; then
    xdg-open artistas_visual.html
fi

echo "[SUCESSO] Coleta e visualização concluídas! Veja o gráfico em artistas_visual.html."
