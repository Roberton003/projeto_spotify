import os
from coleta_spotify import autenticar_spotify, get_available_genres

print("--- Buscando gêneros disponíveis na API do Spotify ---")

try:
    # As funções importadas já lidam com as variáveis de ambiente.
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

    token = autenticar_spotify(CLIENT_ID, CLIENT_SECRET)
    lista_de_generos = get_available_genres(token)

    if lista_de_generos:
        print("\n[SUCESSO] A API retornou a seguinte lista de gêneros:")
        # Imprimir em ordem alfabética para facilitar a leitura
        for genero in sorted(lista_de_generos):
            print(f"- {genero}")
        print(f"\nTotal: {len(lista_de_generos)} gêneros.")
    else:
        print("\n[AVISO] A API não retornou nenhuma lista de gêneros disponíveis.")

except Exception as e:
    print(f"\nOcorreu um erro durante a execução: {e}")

print("\n--- Fim da listagem ---")
