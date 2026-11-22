# Spec Delta

## Purpose

Permite avaliar e comparar sistematicamente os resultados gerados por diferentes versões de prompts (v1 vs v2) aplicando a rubrica oficial de atendimento ao cliente com notas e justificativas.

## ADDED Requirements

### Requirement: Avaliação por rubrica oficial de três critérios
O sistema MUST disponibilizar uma rubrica de avaliação contendo exatamente os três critérios oficiais: clareza, adequação ao nível do cliente e acionabilidade, atribuindo notas de 1 a 5 e justificativas textuais para cada critério.

#### Scenario: Avaliação de saída contra a rubrica oficial
- **WHEN** uma saída gerada for submetida ao avaliador da rubrica
- **THEN** o sistema SHALL atribuir notas de 1 a 5 para clareza, adequação ao nível do cliente e acionabilidade, acompanhadas de justificativas textuais

### Requirement: Comparação automatizada entre versões de prompt (v1 vs v2)
O sistema MUST comparar os resultados obtidos pela versão base (v1) e pela versão aprimorada (v2) sob o mesmo caso de teste e mesmo perfil de cliente, calculando o delta de desempenho entre elas.

#### Scenario: Execução de comparação entre v1 e v2
- **WHEN** o usuário solicitar a comparação de versões para um caso de teste e tipo de conteúdo
- **THEN** o sistema SHALL executar ou recuperar do cache as gerações de v1 e v2, aplicar a rubrica e destacar a versão vencedora com as diferenças observadas

### Requirement: Geração de relatório comparativo estruturado
O sistema MUST consolidar o resultado das avaliações comparativas em relatório estruturado em JSON e formato legível, expondo pontuações agregadas e análises qualitativas.

#### Scenario: Exportação do relatório de comparação
- **WHEN** a bateria de comparação entre versões for concluída
- **THEN** o sistema SHALL produzir um relatório contendo tabela de notas por critério, resumo executivo das melhorias e identificação de possíveis regressões
