# Spec Delta

## Purpose

Gerencia o ciclo de vida das execuções do assistente, garantindo cache determinístico baseado em hash para chamadas de LLM e persistência completa em JSON para rastreabilidade e histórico.

## ADDED Requirements

### Requirement: Cache determinístico de chamadas à API
O sistema MUST interceptar solicitações de inferência e consultar um repositório de cache local indexado por hash SHA-256 gerado a partir do template do prompt, perfil do cliente, mensagem de entrada e parâmetros do modelo.

#### Scenario: Recuperação de resposta em cache
- **WHEN** for solicitada uma geração cujos parâmetros e entradas sejam idênticos a uma execução prévia já armazenada em cache
- **THEN** o sistema SHALL retornar o resultado do cache imediatamente sem realizar nova chamada de rede à API de LLM

#### Scenario: Ausência de cache (cache miss)
- **WHEN** os parâmetros de entrada não corresponderem a nenhuma chave existente no cache
- **THEN** o sistema SHALL efetuar a chamada à API de LLM e gravar a nova resposta associada à chave hash calculada

### Requirement: Persistência de execuções em JSON
O sistema MUST registrar em arquivos JSON todas as execuções realizadas, armazenando entradas, saídas e metadados contextuais como timestamp UTC, tempo de resposta, perfil selecionado e versão do prompt.

#### Scenario: Gravação de registro de execução
- **WHEN** uma geração de conteúdo for finalizada com sucesso
- **THEN** o sistema SHALL persistir um registro em formato JSON no diretório de execuções com identificador único

### Requirement: Persistência de resultados de comparação
O sistema MUST salvar os resultados das rodadas de avaliação e comparação de prompts em arquivos JSON dedicados, assegurando reprodutibilidade das análises.

#### Scenario: Salvamento de benchmark comparativo
- **WHEN** uma rotina de comparação entre versões v1 e v2 for concluída
- **THEN** o sistema SHALL armazenar o resultado consolidado e os escores da rubrica em arquivo JSON com metadados da execução

### Requirement: Invalidação e limpeza de cache sob demanda
O sistema MUST prover mecanismo explícito para forçar a atualização de chamadas (bypass do cache) ou limpar o histórico de cache acumulado.

#### Scenario: Execução com flag de bypass de cache
- **WHEN** o usuário acionar uma execução com instrução explícita para ignorar o cache
- **THEN** o sistema SHALL realizar nova chamada direta à API de LLM e atualizar a entrada correspondente no cache
