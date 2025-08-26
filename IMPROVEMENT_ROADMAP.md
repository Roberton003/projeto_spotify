# Roadmap de Melhorias e Escalabilidade

## 1. Introdução

Este documento descreve os próximos passos sugeridos para evoluir o projeto de coleta de dados do Spotify, transformando-o de um pipeline robusto em um sistema de dados de produção de larga escala. As sugestões baseiam-se na excelente fundação já existente e visam prepará-lo para maiores volumes de dados, maior automação e melhor performance analítica.

## 2. Itens do Roadmap

### 2.1. Orquestração de Workflow Profissional

- **O quê:** Substituir a orquestração baseada em `cron` e shell scripts por uma ferramenta dedicada como **Apache Airflow**, **Prefect** ou **Dagster**.
- **Por quê:** Obter uma interface gráfica para monitoramento, gerenciamento centralizado de logs, definição explícita de dependências entre tarefas, retries automáticos em nível de tarefa e melhor escalabilidade do agendamento.
- **Como:**
    1.  Definir o pipeline como um DAG (Grafo Acíclico Dirigido).
    2.  Transformar os scripts atuais (`coleta_spotify.py`, `visualizar_artistas.py`) em tarefas ou operadores dentro do DAG.
    3.  A lógica de rotação de gêneros (`run_batch_genres`) pode ser implementada como um padrão de "dynamic tasks" no orquestrador.

### 2.2. Escalabilidade do Armazenamento de Dados

- **O quê:** Migrar o banco de dados analítico de SQLite para um sistema de banco de dados ou Data Warehouse mais robusto.
- **Por quê:** O SQLite não suporta acesso concorrente de forma eficiente e possui limitações de performance para grandes volumes de dados. Um sistema de produção requer uma solução mais poderosa.
- **Como:**
    1.  **Opção A (Banco de Dados Relacional):** Substituir o `sqlite3` por **PostgreSQL** ou **MySQL**. Isso exigiria apenas a alteração do driver no `db_client.py` (usando `psycopg2` ou similar).
    2.  **Opção B (Cloud Data Warehouse):** Para análises em larga escala, carregar os dados diretamente em **Google BigQuery**, **Snowflake** ou **Amazon Redshift**. Isso envolveria a adaptação do `db_client.py` para usar as bibliotecas cliente dessas plataformas.

### 2.3. Otimização do Formato de Arquivo para Análise

- **O quê:** Salvar os dados da camada processada (`processed`) em **Apache Parquet** em vez de JSON.
- **Por quê:** Parquet é um formato colunar otimizado para queries analíticas. Ele oferece compressão muito superior (reduzindo custos de armazenamento) e uma performance de leitura ordens de magnitude mais rápida para ferramentas como Pandas, Spark, BigQuery, etc.
- **Como:**
    1.  No final da função `processar_e_salvar`, após normalizar os dados, utilizar a biblioteca `pandas` (já uma dependência) ou `pyarrow` (também já presente).
    2.  Criar um DataFrame com os dados processados.
    3.  Em vez de `json.dump`, usar `dataframe.to_parquet(out_path, index=False)`. O caminho de saída (`out_path`) teria a extensão `.parquet`.

### 2.4. Escalabilidade do Processamento (Paralelismo)

- **O quê:** Processar múltiplos artistas ou gêneros em paralelo.
- **Por quê:** Reduzir drasticamente o tempo total de execução do pipeline à medida que o volume de dados a ser coletado aumenta.
- **Como:**
    1.  **Opção A (Serverless):** Usar **AWS Lambda** ou **Google Cloud Functions**. Uma função "orquestradora" obteria a lista de artistas/gêneros e invocaria uma outra função (a de coleta) para cada item da lista, executando-as em paralelo.
    2.  **Opção B (Frameworks de Cluster):** Para volumes massivos, usar **Apache Spark** ou **Dask**. O framework leria a lista de artistas e distribuiria a tarefa de coleta e processamento por múltiplos nós de um cluster.

## 3. Conclusão

A implementação destes itens do roadmap transformará o projeto em uma plataforma de dados completa, capaz de suportar análises complexas em grande escala e operar de forma autônoma e resiliente em um ambiente de produção.
