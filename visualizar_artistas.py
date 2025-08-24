import os
import json
import plotly.express as px

# Pasta onde estão os arquivos de artistas
DATA_DIR = 'data'

# Lista para armazenar nomes dos artistas
nomes = []

# Percorre todos os arquivos JSON na pasta data
def coletar_nomes_artistas():
    for arquivo in os.listdir(DATA_DIR):
        if arquivo.endswith('.json'):
            caminho = os.path.join(DATA_DIR, arquivo)
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                # Tenta extrair o nome do artista
                nome = dados.get('name')
                if nome:
                    nomes.append(nome)

coletar_nomes_artistas()

if not nomes:
    print('Nenhum artista encontrado na pasta data/.')
else:
    # Conta a frequência de cada artista
    from collections import Counter
    contagem = Counter(nomes)
    artistas = list(contagem.keys())
    frequencias = list(contagem.values())

    # Gera gráfico de barras
    fig = px.bar(x=artistas, y=frequencias, labels={'x': 'Artista', 'y': 'Frequência'},
                 title='Frequência de Artistas Coletados')
    fig.update_layout(xaxis_tickangle=-45)
    fig.write_html('artistas_visual.html')
    print('Gráfico gerado em artistas_visual.html')
