# Documento de Orientação do Projeto (Análise GEMINI)

## 1. Visão Geral

Este documento formaliza os princípios arquitetônicos e as boas práticas que norteiam o projeto de coleta de dados do Spotify. Ele serve como um guia para garantir que o desenvolvimento futuro mantenha a alta qualidade, robustez e manutenibilidade já estabelecidas.

A análise deste projeto revelou uma base sólida e profissional, aplicando conceitos de engenharia de dados que são essenciais para pipelines confiáveis e escaláveis.

## 2. Princípios Fundamentais da Arquitetura

Qualquer alteração ou nova funcionalidade deve aderir aos seguintes princípios:

### 2.1. Resiliência e Idempotência
O pipeline é projetado para ser tolerante a falhas e seguro para ser re-executado.
- **Checkpoints:** O sistema de checkpoints por gênero é um pilar central. Ele deve ser mantido e expandido para novas entidades, garantindo que o trabalho não seja refeito desnecessariamente.
- **Retries e Backoff:** A comunicação com APIs externas deve, obrigatoriamente, implementar uma estratégia de retry com backoff exponencial para lidar com instabilidades temporárias e `rate limiting`.

### 2.2. Qualidade e Contrato de Dados
A integridade dos dados é uma prioridade.
- **Validação de Schema:** Nenhum dado deve ser gravado na camada processada (`processed`) sem antes passar por uma validação de schema. O `schema/` deve ser tratado como a "fonte da verdade" para a estrutura dos dados.
- **Imutabilidade da Camada Raw:** Os dados na camada `raw` são imutáveis. Eles representam a resposta original da API e não devem ser alterados. Qualquer transformação ocorre no passo seguinte, gerando novos artefatos na camada `processed`.

### 2.3. Arquitetura em Camadas (Layered Architecture)
A separação de responsabilidades entre as camadas de dados deve ser mantida.
- **`data/raw` (Bronze):** Armazena os dados brutos, exatamente como foram recebidos da fonte.
- **`data/processed` (Silver):** Armazena os dados após limpeza, normalização e validação. Esta é a camada que deve ser consumida por aplicações analíticas.

### 2.4. Observabilidade e Monitoramento
O pipeline deve ser transparente sobre sua execução.
- **Métricas:** A coleta de métricas de execução (ex: número de registros processados, chamadas de API, tempo de execução) é essencial. A integração existente com arquivos JSON e Prometheus é um padrão a ser seguido.
- **Logging Estruturado:** O log em formato estruturado (JSON) deve ser mantido para facilitar a análise e a busca em sistemas de gerenciamento de logs.

### 2.5. Modularidade e Abstração
O código deve ser organizado, desacoplado e testável.
- **Abstração de Componentes:** A separação da lógica de banco de dados (`db_client.py`) é um exemplo a ser seguido. Componentes externos (APIs, bancos de dados, sistemas de arquivos) devem ser acessados através de módulos de abstração.
- **Testabilidade:** Todo novo código de lógica de negócios deve ser acompanhado de testes unitários e de integração correspondentes na pasta `tests/`.

### 2.6. Segurança e Configuração
A gestão de configurações e segredos deve ser feita de forma segura.
- **Variáveis de Ambiente:** Credenciais, chaves de API e outras configurações sensíveis devem ser gerenciadas exclusivamente por meio de variáveis de ambiente, nunca hardcoded no código ou versionadas em arquivos `.env`.

## 3. Conclusão

Este projeto serve como um excelente exemplo de um pipeline de dados bem construído. Ao aderir a estes princípios, garantimos que o projeto continuará a ser robusto, escalável e fácil de manter à medida que evolui.
