import sqlite3
import os

DB_PATH = os.path.join('data', 'spotify.db')

print("--- Verificando Gêneros no Banco de Dados ---")

if not os.path.exists(DB_PATH):
    print(f"Erro: Banco de dados '{DB_PATH}' não encontrado.")
    exit()

try:
    con = sqlite3.connect(DB_PATH)
    cursor = con.cursor()
    cursor.execute("SELECT DISTINCT genre FROM tracks")
    genres_in_db = [row[0] for row in cursor.fetchall()]
    con.close()
except Exception as e:
    print(f"Ocorreu um erro ao ler o banco de dados: {e}")
    exit()

if not genres_in_db:
    print("Nenhum gênero encontrado no banco de dados.")
else:
    print("\nGêneros encontrados no banco de dados:")
    for genre in sorted(genres_in_db):
        print(f"- {genre}")

# Lista original de gêneros que tentamos coletar
target_genres = {
    "sertanejo", "funk", "pop", "hip-hop", "pagode", "rock",
    "mpb", "gospel", "electronic", "samba", "forro"
}

found_genres = set(genres_in_db)
missing_genres = target_genres - found_genres

if missing_genres:
    print("\nGêneros que não retornaram dados da API e estão ausentes no DB:")
    for genre in sorted(list(missing_genres)):
        print(f"- {genre}")
else:
    print("\nTodos os gêneros alvo foram encontrados no banco de dados.")

print("--- Fim da Verificação ---")
