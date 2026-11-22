# Spec Delta

## Purpose

Define a geração estruturada dos quatro conteúdos de atendimento ao cliente (diagnóstico, passo a passo, perguntas de esclarecimento e fluxograma), orientada por perfis de clientes em JSON e templates de prompts versionados.

## ADDED Requirements

### Requirement: Suporte aos quatro conteúdos de atendimento
O sistema MUST ser capaz de gerar quatro tipos distintos de artefatos de atendimento ao cliente: diagnóstico da situação, passo a passo resolutivo, perguntas de esclarecimento e fluxograma do fluxo de atendimento.

#### Scenario: Geração dos quatro conteúdos para uma solicitação
- **WHEN** o usuário solicitar a geração completa de suporte para uma mensagem de cliente
- **THEN** o sistema SHALL gerar e retornar os quatro conteúdos estruturados de forma independente e coerente com a solicitação

### Requirement: Carregamento e validação de perfis de clientes
O sistema MUST carregar e validar perfis de clientes a partir de arquivos JSON, contemplando de 3 a 5 personas com atributos de perfil como nível de familiaridade técnica, estado emocional/tom e restrições de comunicação.

#### Scenario: Carregamento de perfil válido
- **WHEN** um identificador de perfil existente em JSON for fornecido na requisição
- **THEN** o sistema SHALL carregar os atributos da persona e injetá-los no contexto de geração do prompt

#### Scenario: Perfil inválido ou inexistente
- **WHEN** for requisitado um perfil inexistente ou com JSON malformado
- **THEN** o sistema SHALL rejeitar a execução com uma mensagem de erro descritiva sem interromper o serviço

### Requirement: Prompts desacoplados e versionados
O sistema MUST manter templates de prompts isolados e organizados por tipo de conteúdo e versão (mínimo v1 e v2), permitindo sua substituição ou evolução sem alteração no código-fonte da aplicação.

#### Scenario: Seleção explícita de versão do prompt
- **WHEN** uma versão específica de prompt for informada (ex.: v1 ou v2) para determinado tipo de conteúdo
- **THEN** o sistema SHALL carregar o respectivo arquivo de template e aplicá-lo na geração

### Requirement: Formatação de fluxograma em padrão estruturado
O conteúdo de fluxograma MUST ser emitido em formato sintático estruturado (como Mermaid ou diagrama textual ordenado), garantindo legibilidade tanto em texto puro quanto em renderizadores visuais.

#### Scenario: Geração de fluxograma com passos e decisões
- **WHEN** o tipo de conteúdo fluxograma for gerado
- **THEN** a saída gerada SHALL conter nós de início, etapas de ação, pontos de decisão condicional e estado final em sintaxe estruturada

### Requirement: Comunicação com a API de LLM
O sistema MUST enviar as instruções parametrizadas para a API de LLM configurada via variáveis de ambiente, tratando limites de taxa, erros de conexão e respostas incompletas.

#### Scenario: Chamada bem-sucedida à API de LLM
- **WHEN** o payload com prompt preenchido for despachado para a API de LLM
- **THEN** o sistema SHALL receber a resposta textual, calcular metadados de execução (tempo e tokens se disponíveis) e retorná-la ao chamador
