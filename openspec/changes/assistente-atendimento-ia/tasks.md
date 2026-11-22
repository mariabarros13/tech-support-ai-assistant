# Tasks

## 1. Configuração do Ambiente e Estrutura Inicial

- [x] 1.1 Criar a árvore de diretórios do projeto (`src/`, `profiles/`, `prompts/`, `storage/`, `samples/`, `web/`) e verificar a existência das pastas com comando de listagem
- [x] 1.2 Definir `requirements.txt` com dependências essenciais (`pydantic`, `python-dotenv`, `typer`, `rich`, `google-genai`, `streamlit`) e verificar instalação em ambiente virtual Python
- [x] 1.3 Criar o arquivo `.env.example` com chaves de configuração (`GEMINI_API_KEY`, `LLM_MODEL`, `CACHE_DIR`, `STORAGE_DIR`) e verificar que nenhuma credencial real está exposta

## 2. Perfis de Clientes e Versionamento de Prompts

- [x] 2.1 Criar de 3 a 5 arquivos JSON em `profiles/` modelando personas com níveis técnicos, tons emocionais e preferências de comunicação distintas (ex.: `iniciante.json`, `apressado.json`, `tecnico.json`, `irritado.json`), verificando conformidade do schema com testes unitários
- [x] 2.2 Implementar templates baseline (v1) para os 4 tipos de conteúdo em `prompts/` (`diagnostico/v1.txt`, `passo_a_passo/v1.txt`, `perguntas_esclarecimento/v1.txt`, `fluxograma/v1.txt`) e verificar carregamento correto dos arquivos
- [x] 2.3 Implementar templates aprimorados (v2) com engenharia de prompt avançada (persona, restrições explícitas, formatação estrita e sintaxe Mermaid) em `prompts/` e verificar que todas as tags de substituição estão presentes

## 3. Integração com LLM e Cache Determinístico

- [x] 3.1 Implementar `src/llm_client.py` com suporte ao provedor de LLM e modo mock offline com respostas sintéticas para testes, verificando chamada com e sem flag de mock
- [x] 3.2 Implementar `src/cache_manager.py` com cálculo de hash SHA-256 sobre entradas de requisição e persistência em `storage/cache/`, verificando com teste de cache hit e cache miss
- [x] 3.3 Integrar cliente de LLM e gerenciador de cache com suporte a bypass (`--no-cache`), verificando que chamadas idênticas subsequentes não disparam novas requisições de rede

## 4. Persistência de Execuções e Orquestrador de Conteúdos

- [x] 4.1 Implementar `src/storage.py` para salvar e consultar execuções individuais e históricas em JSON com metadados completos (timestamp, perfil, versão, latência e conteúdo), verificando gravação em `storage/runs/`
- [x] 4.2 Implementar `src/generator.py` orquestrando a injeção de perfis, formatação de prompts, consulta ao cache e persistência para os 4 tipos de conteúdo, verificando geração individual e em lote

## 5. Motor de Avaliação e Comparação de Prompts

- [x] 5.1 Implementar a rubrica oficial de atendimento em `src/evaluator.py` contendo exatamente os três critérios oficiais (Clareza, Adequação ao nível do cliente e Acionabilidade), com notas de 1 a 5 e justificativas, verificando a atribuição e cálculo das notas
- [x] 5.2 Implementar rotina de comparação comparando execuções de v1 vs v2 para um mesmo caso e perfil, salvando os resultados em `storage/comparisons/` e verificando o cálculo do delta de melhoria

## 6. Interface de Linha de Comando (CLI) Obrigatória

- [x] 6.1 Implementar comandos da CLI (`generate`, `compare`, `profiles`, `history`) em `src/cli.py` utilizando `typer` e tabelas informativas com `rich`, verificando execução de cada subcomando com `--help`
- [x] 6.2 Implementar flags na CLI para alternar perfis, selecionar versões de prompt (v1/v2), desativar cache e habilitar modo mock, verificando tratamento gracioso de erros de chave ou arquivos ausentes

## 7. Interface Web Demonstrativa e Documentação

- [x] 7.1 Implementar aplicação Streamlit em `web/app.py` com abas para os quatro conteúdos, seleção de perfil, renderização de fluxograma Mermaid e visualização de comparações v1 vs v2, verificando inicialização local do servidor
- [x] 7.2 Elaborar `PROMPT_ENGINEERING_NOTES.md` detalhando as hipóteses, técnicas aplicadas (v1 vs v2), critérios da rubrica oficial e análise crítica dos resultados comparativos
- [x] 7.3 Elaborar `README.md` completo com visão geral da arquitetura, guia de instalação passo a passo, exemplos de comandos CLI, instruções da interface web e estrutura de diretórios
- [x] 7.4 Criar diretório `samples/` com exemplos demonstrativos de entradas, saídas dos 4 conteúdos e relatório comparativo gerado

## Workflow follow-up

- Validar todo o fluxo automatizado com script de verificação de ponta a ponta.
- Apresentar os artefatos gerados para revisão do usuário antes de iniciar a implementação.
