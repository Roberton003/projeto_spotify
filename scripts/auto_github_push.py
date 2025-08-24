import subprocess
import os
import argparse
import getpass
from typing import Optional
import requests
import json


def run_command(command: list[str], cwd: Optional[str] = None, input_data: Optional[str] = None):
    """Executa um comando shell e retorna sua saída."""
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            input=input_data
        )
        if process.stdout:
            print(process.stdout)
        if process.stderr:
            print(f"Erro (stderr):\n{process.stderr}")
        return process.stdout
    except subprocess.CalledProcessError as e:
        # Special handling for 'git commit' when there's nothing to commit
        stderr = e.stderr or ''
        stdout = e.stdout or ''
        if command[0] == "git" and command[1] == "commit" and "nothing to commit" in stderr:
            print("Aviso: Não há nada para comitar. Prosseguindo com o push se houver alterações remotas pendentes.")
            return stdout
        else:
            print(f"Erro ao executar comando: {' '.join(e.cmd)}")
            print(f"Stdout: {stdout}")
            print(f"Stderr: {stderr}")
            raise
    except FileNotFoundError:
        print(f"Erro: Comando '{command[0]}' não encontrado. Certifique-se de que o Git está instalado e no PATH.")
        raise


def get_github_username(github_token: str):
    """Obtém o nome de usuário do GitHub a partir do PAT."""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        response = requests.get("https://api.github.com/user", headers=headers)
        response.raise_for_status()
        return response.json()["login"]
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter nome de usuário do GitHub: {e}")
        raise


def create_github_repository(repo_name: str, github_token: str, github_username: str, is_private: bool = False):
    """Cria um novo repositório no GitHub via API."""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "private": is_private,
        "auto_init": False
    }

    print(f"Tentando criar o repositório '{repo_name}' no GitHub...")
    try:
        response = requests.post("https://api.github.com/user/repos", headers=headers, data=json.dumps(data))
        response.raise_for_status()
        repo_info = response.json()
        print(f"Repositório '{repo_name}' criado com sucesso! URL: {repo_info['html_url']}")
        return repo_info['html_url']
    except requests.exceptions.HTTPError as e:
        resp = e.response
        if resp is not None and resp.status_code == 422 and "name already exists on this account" in resp.text:
            print(f"Aviso: Repositório '{repo_name}' já existe na sua conta do GitHub. Prosseguindo...")
            return f"https://github.com/{github_username}/{repo_name}.git"
        else:
            print(f"Erro ao criar repositório no GitHub: {e}")
            if resp is not None:
                print(f"Resposta da API: {resp.text}")
            raise
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão ao tentar criar repositório no GitHub: {e}")
        raise


def automate_github_push():
    """Automatiza o processo de commit e push para o GitHub de forma interativa."""
    project_root = os.getcwd()
    project_name = os.path.basename(project_root)
    print(f"\n--- Iniciando automação Git no diretório: {project_root} ---")

    # Suporta passagem do token via ENV, argumento --token ou prompt seguro (getpass)
    parser = argparse.ArgumentParser(description="Automatiza commit e push para GitHub (interativo)")
    parser.add_argument("--token", help="Personal Access Token do GitHub. Se ausente, será lido da variável GITHUB_TOKEN ou por prompt seguro.")
    args, remaining = parser.parse_known_args()

    github_token = args.token or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        try:
            github_token = getpass.getpass(prompt="Digite seu GitHub Personal Access Token (entrada oculta): ")
        except Exception:
            github_token = None

    if not github_token:
        print("Erro: Token do GitHub não fornecido. Use --token, a variável GITHUB_TOKEN ou digite quando solicitado.")
        return

    try:
        github_username = get_github_username(github_token)
        print(f"Autenticado como usuário GitHub: {github_username}")
    except Exception as e:
        print(f"Não foi possível obter o nome de usuário do GitHub. Verifique seu PAT e conexão. Erro: {e}")
        return

    # 1. Verificar status do Git
    print("\n1. Verificando status do Git...")
    try:
        run_command(["git", "status"], cwd=project_root)
    except Exception:
        print("Parece que este não é um repositório Git ou há problemas. Deseja inicializar um novo repositório? (s/n)")
        if input().lower() == 's':
            print("Inicializando repositório Git local...")
            run_command(["git", "init"], cwd=project_root)
        else:
            print("Operação cancelada. Por favor, inicialize o repositório Git manualmente ou resolva os problemas.")
            return

    # Perguntar o nome do repositório GitHub
    repo_name = input(f"\nDigite o nome do repositório GitHub a ser criado/usado (sugestão: {project_name}): ")
    if not repo_name:
        repo_name = project_name

    # Perguntar se o repositório deve ser privado
    is_private_str = input(f"Deseja que o repositório '{repo_name}' seja privado? (s/n, padrão: n): ")
    is_private = is_private_str.lower() == 's'

    # Tentar criar o repositório no GitHub
    try:
        github_repo_url = create_github_repository(repo_name, github_token, github_username, is_private)
    except Exception as e:
        print(f"Não foi possível criar ou verificar o repositório no GitHub. Erro: {e}")
        return

    # Check for pending changes
    status_output = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True).stdout.strip()

    if status_output:
        # 2. Adicionar todos os arquivos ao stage
        print("\n2. Adicionando todos os arquivos modificados/novos ao stage...")
        run_command(["git", "add", "."], cwd=project_root)
        run_command(["git", "status"], cwd=project_root) # Mostrar o que foi adicionado

        # 3. Solicitar mensagem de commit
        commit_message = input("\n3. Digite a mensagem do commit (obrigatório): ")
        while not commit_message:
            commit_message = input("A mensagem do commit não pode ser vazia. Digite a mensagem do commit: ")

        print(f"Realizando commit com a mensagem: '{commit_message}'...")
        run_command(["git", "commit", "-m", commit_message], cwd=project_root)
    else:
        print("\nNão há alterações pendentes para comitar. Prosseguindo para o push.")

    # 4. Verificar e configurar o repositório remoto
    print("\n4. Verificando configuração do repositório remoto...")
    try:
        run_command(["git", "remote", "remove", "origin"], cwd=project_root)
        print("Remoto 'origin' existente removido para reconfiguração.")
    except Exception:
        pass

    # Adicionar o repositório remoto
    print(f"Adicionando repositório remoto: {github_repo_url}...")
    run_command(["git", "remote", "add", "origin", github_repo_url], cwd=project_root)

    # 5. Enviar (push) os arquivos para o GitHub
    default_branch = "main"
    branch_to_push = input(f"\n5. Digite o nome do branch para o push (padrão: {default_branch}): ")
    if not branch_to_push:
        branch_to_push = default_branch

    print(f"Enviando (push) para o branch '{branch_to_push}' no GitHub...")
    try:
        run_command(["git", "push", "-u", "origin", branch_to_push], cwd=project_root)
        print("\n--- Processo de push para o GitHub concluído com sucesso! ---")
        print(f"Seu projeto deve estar disponível em: {github_repo_url}")
    except Exception as e:
        stderr = getattr(e, 'stderr', '') or ''
        if "set the upstream branch" in stderr:
            print(f"Erro: O branch '{branch_to_push}' não tem um upstream configurado. Tentando configurar e fazer push novamente...")
            run_command(["git", "push", "--set-upstream", "origin", branch_to_push], cwd=project_root)
            print("\n--- Processo de push para o GitHub concluído com sucesso! ---")
            print(f"Seu projeto deve estar disponível em: {github_repo_url}")
        else:
            print("Erro durante o push. Verifique as mensagens acima para detalhes.")
            print("Certifique-se de que você tem permissão para fazer push e que o branch existe no remoto.")
            print("Você pode precisar configurar suas credenciais Git ou criar o repositório no GitHub primeiro.")


if __name__ == "__main__":
    # Mantemos sys.argv para que argparse dentro da função funcione com flags
    automate_github_push()
