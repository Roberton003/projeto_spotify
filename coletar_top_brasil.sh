#!/bin/bash
#
# Script para coletar dados dos principais gêneros musicais do Brasil.
#

set -e

# Lista de gêneros a serem coletados (baseado em pesquisa de popularidade)
# Usamos os nomes que são compatíveis com a API do Spotify.
GENEROS_BRASIL=(
    "sertanejo"
    "funk"
    "pop"
    "hip-hop"
    "pagode"
    "rock"
    "mpb"
    "gospel"
    "electronic"
    "samba"
    "forro"
)

# Garante que o ambiente virtual e as dependências estão prontos
echo "[INFO] Verificando e instalando dependências no ambiente .venv..."
./.venv/bin/python3 -m pip install --upgrade pip > /dev/null
./.venv/bin/python3 -m pip install -r requirements.txt > /dev/null

# Define a quantidade de artistas por gênero (pode ser ajustado)
QTD_ARTISTAS=25

echo "[INFO] Iniciando coleta para os TOP gêneros do Brasil. Coletando ${QTD_ARTISTAS} artistas por gênero."

# Loop para executar a coleta para cada gênero
for genero in "${GENEROS_BRASIL[@]}"; do
    echo "-----------------------------------------------------"
    echo "[INFO] Coletando para o gênero: $genero"
    echo "-----------------------------------------------------"
    
    ./.venv/bin/python3 coleta_spotify.py --genero "$genero" --qtd "$QTD_ARTISTAS" --no-interactive
    
    echo "[SUCCESS] Coleta para o gênero '$genero' concluída."
    echo ""
done

echo "-----------------------------------------------------"
echo "[FINALIZADO] Coleta de todos os gêneros brasileiros concluída com sucesso!"
echo "-----------------------------------------------------"