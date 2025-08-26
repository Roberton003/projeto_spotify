import sqlite3
import pandas as pd
import plotly.express as px
import os

# --- Configurações ---
DB_PATH = os.path.join('data', 'spotify.db')
OUTPUT_HTML_PATH = 'dashboard_popularidade.html'
CHART_TITLE = 'Popularidade Média de Músicas por Gênero no Brasil'
TOP_N_TRACKS = 10 # Número de músicas no ranking por gênero

def generate_html_report(db_stats, summary_fig_html, top_tracks_df):
    """Gera o conteúdo HTML final combinando as estatísticas, o gráfico e as tabelas de ranking."""
    
    # Estilo CSS para as tabelas
    html_style = """
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f4f4f9;
            color: #333;
        }
        h1, h2, h3 {
            color: #333;
            text-align: center;
        }
        .container {
            width: 90%;
            max-width: 1200px;
            margin: auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            border-radius: 8px;
        }
        .styled-table {
            border-collapse: collapse;
            margin: 25px auto;
            font-size: 0.9em;
            width: 95%;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        }
        .styled-table thead tr {
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }
        .styled-table th,
        .styled-table td {
            padding: 12px 15px;
        }
        .styled-table tbody tr {
            border-bottom: 1px solid #dddddd;
        }
        .styled-table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
        }
        .styled-table tbody tr:last-of-type {
            border-bottom: 2px solid #009879;
        }
    </style>
    """
    
    # Tabela de Estatísticas
    stats_html = f"""
    <h2>Estatísticas Gerais do Projeto</h2>
    <table class="styled-table">
        <thead>
            <tr><th>Métrica</th><th>Valor</th></tr>
        </thead>
        <tbody>
            <tr><td>Total de Músicas no Banco de Dados</td><td>{db_stats['total_tracks']}</td></tr>
            <tr><td>Total de Artistas Únicos</td><td>{db_stats['total_artists']}</td></tr>
            <tr><td>Total de Gêneros Coletados</td><td>{db_stats['total_genres']}</td></tr>
            <tr><td>Primeira Coleta Registrada</td><td>{db_stats['first_collection']}</td></tr>
            <tr><td>Última Coleta Registrada</td><td>{db_stats['last_collection']}</td></tr>
            <tr><td>Tamanho do Banco de Dados</td><td>{db_stats['db_size_mb']} MB</td></tr>
        </tbody>
    </table>
    """

    # Início do corpo HTML
    html_body = f"""
    <html>
    <head>
        <title>Dashboard de Popularidade - Spotify</title>
        <meta charset="UTF-8">
        {html_style}
    </head>
    <body>
        <div class="container">
            <h1>Análise de Popularidade Musical - Spotify</h1>
            {stats_html}
            <hr>
            {summary_fig_html}
            <hr>
            <h2>Top {TOP_N_TRACKS} Músicas Mais Populares por Gênero</h2>
    """
    
    # Gerar uma tabela para cada gênero
    for genre in sorted(top_tracks_df['genre'].unique()):
        html_body += f"<h3>{genre.capitalize()}</h3>"
        df_genre = top_tracks_df[top_tracks_df['genre'] == genre].copy()
        
        # Formatar a data
        df_genre['collected_at'] = pd.to_datetime(df_genre['collected_at']).dt.strftime('%Y-%m-%d')
        
        # Adicionar ranking
        df_genre.insert(0, 'Rank', range(1, 1 + len(df_genre)))
        
        # Renomear colunas para apresentação
        df_genre.rename(columns={
            'track_name': 'Música',
            'artist_name': 'Artista',
            'popularity': 'Popularidade',
            'collected_at': 'Data da Coleta'
        }, inplace=True)
        
        # Remover a coluna de gênero da tabela individual
        df_genre.drop('genre', axis=1, inplace=True)
        
        html_body += df_genre.to_html(index=False, classes='styled-table', escape=False)

    # Fim do corpo HTML
    html_body += """
        </div>
    </body>
    </html>
    """
    return html_body

def criar_dashboard_avancado():
    """
    Cria um dashboard avançado com um gráfico de resumo e rankings por gênero.
    """
    if not os.path.exists(DB_PATH):
        print(f"Erro: O banco de dados '{DB_PATH}' não foi encontrado.")
        return

    print(f"Conectando ao banco de dados: {DB_PATH}")
    try:
        con = sqlite3.connect(DB_PATH)
        
        # --- Coletar Estatísticas ---
        print("Coletando estatísticas do banco de dados...")
        stats = {}
        stats['total_tracks'] = pd.read_sql_query("SELECT COUNT(*) FROM tracks", con).iloc[0,0]
        stats['total_artists'] = pd.read_sql_query("SELECT COUNT(DISTINCT artist_id) FROM tracks", con).iloc[0,0]
        stats['total_genres'] = pd.read_sql_query("SELECT COUNT(DISTINCT genre) FROM tracks", con).iloc[0,0]
        min_date_str = pd.read_sql_query("SELECT MIN(collected_at) FROM tracks", con).iloc[0,0]
        max_date_str = pd.read_sql_query("SELECT MAX(collected_at) FROM tracks", con).iloc[0,0]
        stats['first_collection'] = pd.to_datetime(min_date_str).strftime('%Y-%m-%d %H:%M')
        stats['last_collection'] = pd.to_datetime(max_date_str).strftime('%Y-%m-%d %H:%M')
        db_size_bytes = os.path.getsize(DB_PATH)
        stats['db_size_mb'] = round(db_size_bytes / (1024 * 1024), 2)

        # --- Coletar Dados para Gráficos ---
        df_summary = pd.read_sql_query("SELECT genre, popularity FROM tracks WHERE popularity IS NOT NULL", con)
        query_top_tracks = f"""
        WITH RankedTracks AS (
            SELECT
                track_name,
                artist_name,
                genre,
                popularity,
                collected_at,
                ROW_NUMBER() OVER(PARTITION BY genre ORDER BY popularity DESC, track_name) as rn
            FROM
                tracks
            WHERE popularity IS NOT NULL
        )
        SELECT
            track_name,
            artist_name,
            genre,
            popularity,
            collected_at
        FROM
            RankedTracks
        WHERE
            rn <= {TOP_N_TRACKS};
        """
        df_top_tracks = pd.read_sql_query(query_top_tracks, con)
        con.close()

    except Exception as e:
        print(f"Erro ao ler o banco de dados: {e}")
        return

    if df_summary.empty:
        print("Não foram encontrados dados para gerar o dashboard.")
        return

    # --- Gerar Gráfico de Resumo ---
    print("Gerando gráfico de popularidade média...")
    media_popularidade = df_summary.groupby('genre')['popularity'].mean().round(2).reset_index().sort_values(by='popularity', ascending=False)
    fig = px.bar(
        media_popularidade, x='genre', y='popularity', title=CHART_TITLE,
        labels={'genre': 'Gênero Musical', 'popularity': 'Popularidade Média (0-100)'},
        text='popularity', color='popularity', color_continuous_scale=px.colors.sequential.Viridis
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(yaxis=dict(range=[0, 100]))
    summary_fig_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # --- Gerar Relatório HTML Completo ---
    print("Gerando relatório HTML com rankings e estatísticas...")
    full_html = generate_html_report(stats, summary_fig_html, df_top_tracks)

    try:
        with open(OUTPUT_HTML_PATH, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"\nSucesso! Dashboard final criado em: '{os.path.abspath(OUTPUT_HTML_PATH)}'")
    except Exception as e:
        print(f"Erro ao salvar o arquivo HTML: {e}")

if __name__ == '__main__':
    criar_dashboard_avancado()
