# Design

## Context

O projeto consiste no desenvolvimento em 48 horas de um assistente inteligente de atendimento ao cliente com engenharia de prompt avançada, executado sobre um repositório Python novo. O sistema precisa gerar quatro tipos de conteúdo de suporte, aplicar perfis de clientes estruturados, versionar prompts, gerenciar chamadas a LLMs com cache determinístico, registrar execuções em JSON, comparar versões de prompts com a rubrica oficial e expor a funcionalidade através de CLI obrigatória e interface web demonstrativa.

Para maiores detalhes de motivação, consulte [proposal.md](proposal.md). Para os requisitos contratuais, consulte as especificações em `specs/`.

## Goals / Non-Goals

**Goals:**
- Implementar uma arquitetura modular, limpa e testável em Python (3.11+).
- Modelar 4 perfis de clientes realistas em arquivos JSON (`profiles/`).
- Desacoplar prompts em arquivos versionados (`prompts/<tipo>/v1.txt` e `v2.txt`), documentando as melhorias no `PROMPT_ENGINEERING_NOTES.md`.
- Construir um adaptador de LLM flexível com suporte a provedor real (ex.: Gemini / OpenAI) e modo simulado (mock) para testes sem consumo de cota.
- Implementar cache determinístico baseado em hash SHA-256 e persistência estruturada em arquivos JSON para execuções e comparações.
- Desenvolver um motor de avaliação comparativa (v1 vs v2) baseado exatamente nos três critérios da rubrica oficial (clareza, adequação ao nível do cliente e acionabilidade), com notas de 1 a 5 e justificativas textuais.
- Criar uma interface CLI ergonômica e informativa via terminal (`rich` / `typer`).
- Desenvolver uma interface web demonstrativa leve com Streamlit para inspeção visual e testes rápidos.

**Non-Goals:**
- Não implementar banco de dados relacional pesado ou infraestrutura de nuvem (arquivos JSON locais atendem plenamente à rastreabilidade exigida no prazo de 48h).
- Não criar sistemas complexos de autenticação, mensageria assíncrona (RabbitMQ/Celery) ou multi-tenancy.
- Não utilizar frameworks de orquestração de agentes complexos (como AutoGen ou CrewAI) para evitar latência excessiva e comportamento não determinístico.
- Não introduzir funcionalidades adicionais fora das especificações do desafio.

## Decisions

### 1. Estrutura de Diretórios e Modularização em Python
- **Decisão**: Organizar o projeto em pacotes com responsabilidades estritamente separadas:
  ```text
  ├── profiles/                  # Perfis de clientes em JSON
  │   ├── iniciante.json
  │   ├── apressado.json
  │   ├── tecnico.json
  │   └── irritado.json
  ├── prompts/                   # Templates versionados de prompt
  │   ├── diagnostico/
  │   │   ├── v1.txt
  │   │   └── v2.txt
  │   ├── passo_a_passo/
  │   │   ├── v1.txt
  │   │   └── v2.txt
  │   ├── perguntas_esclarecimento/
  │   │   ├── v1.txt
  │   │   └── v2.txt
  │   └── fluxograma/
  │       ├── v1.txt
  │       └── v2.txt
  ├── src/                       # Código-fonte da aplicação
  │   ├── config.py              # Carregamento de variáveis de ambiente (.env)
  │   ├── models.py              # Schemas de dados (Pydantic)
  │   ├── llm_client.py          # Cliente de integração com LLM e fallback
  │   ├── cache_manager.py       # Gerenciador de cache determinístico (SHA-256)
  │   ├── storage.py             # Persistência de execuções e comparações em JSON
  │   ├── generator.py           # Orquestrador da geração dos 4 conteúdos
  │   ├── evaluator.py           # Motor de avaliação e comparação por rubrica
  │   └── cli.py                 # Ponto de entrada da CLI
  ├── web/                       # Interface web demonstrativa
  │   └── app.py                 # Aplicação Streamlit interativa
  ├── samples/                   # Exemplos de entrada e saídas de demonstração
  ├── storage/                   # Diretório de persistência de execuções e cache
  │   ├── cache/
  │   ├── runs/
  │   └── comparisons/
  ├── .env.example
  ├── requirements.txt
  ├── PROMPT_ENGINEERING_NOTES.md
  └── README.md
  ```
- **Alternativas consideradas**: Monolito de arquivo único (prejudicaria legibilidade e testes) ou separação em múltiplos microsserviços (inviável e desnecessário para o escopo e prazo de 48 horas).

### 2. Provedor de LLM com Camada de Abstração e Mock Offline
- **Decisão**: Utilizar um cliente abstrato `LLMClient` que consome primariamente a API oficial do Google Gemini (ou OpenAI compatível), implementando uma camada de Mock/Fallback offline. Caso a chave de API não esteja configurada ou o usuário utilize a flag `--mock`, o sistema opera normalmente com respostas sintéticas de demonstração, viabilizando execução de testes unitários contínuos sem custo e sem rede.
- **Alternativas consideradas**: Chamar a biblioteca do LLM diretamente dentro das funções de negócio (acoplamento indesejado) ou depender exclusivamente de APIs pagas sem opção offline.

### 3. Cache Determinístico com Hashing SHA-256
- **Decisão**: O cache armazena as respostas em arquivos JSON dentro de `storage/cache/` identificados por:
  `cache_key = sha256(f"{content_type}:{prompt_template}:{profile_json}:{user_input}:{model_name}")`.
  Se a chave existir e o bypass não for solicitado (`--no-cache`), o resultado é retornado instantaneamente com a flag `cached: true`.
- **Alternativas consideradas**: Armazenamento em memória volátil (perde o cache entre execuções de CLI) ou Redis (exigiria servidor externo rodando).

### 4. Engenharia de Prompts (v1 vs v2) e Rubrica Oficial
- **Decisão**:
  - **Versão v1 (Baseline)**: Prompt direto, com instruções sucintas em linguagem natural e poucas restrições de formatação ou persona.
  - **Versão v2 (Aprimorada)**: Prompt estruturado com adoção clara de persona de atendimento empático e técnico, injeção precisa das variáveis do perfil do cliente, restrições negativas explícitas (ex.: não usar jargões com perfil leigo), delimitação de seções de saída e sintaxe estrita (Mermaid no fluxograma).
  - **Rubrica Oficial**: Implementada em `evaluator.py`, avaliando exatamente os três critérios oficiais em escala de 1 a 5 com justificativas textuais:
    1. *Clareza* (linguagem clara, direta, bem explicada e de fácil compreensão)
    2. *Adequação ao nível do cliente* (adaptação vocabular, técnica e de profundidade à persona/perfil em JSON)
    3. *Acionabilidade* (orientações práticas, passo a passo exequível e direcionamento resolutivo)
    *Nota de arquitetura*: Validações técnicas internas adicionais (como checagem de sintaxe Mermaid ou integridade estrutural de JSON) operam como asserções automatizadas complementares e não alteram a rubrica oficial de 3 critérios.
- **Alternativas consideradas**: Comparação puramente visual/manual (não automatizável) ou avaliação apenas por similaridade de embeddings (não captura adequadamente nuances de tom e acionabilidade).

### 5. CLI com Typer/Rich e Interface Web com Streamlit
- **Decisão**:
  - CLI construída com `typer` e `rich`, oferecendo comandos declarativos (`generate`, `compare`, `profiles`, `history`), ajuda contextual clara e tabelas visualmente atraentes no terminal.
  - Interface Web construída com `streamlit`, que oferece componentes nativos em Python puro para renderizar Markdown, tabelas e diagramas Mermaid sem necessidade de setup de frontend complexo (React/Node).
- **Alternativas consideradas**: CLI básica com `sys.argv` (difícil manutenção de flags) ou frontend em React/TypeScript (alto custo de setup para o prazo de 48 horas).

## Risks / Trade-offs

- **[Risco: Esgotamento de cota ou latência na API de LLM]**
  → *Mitigação*: Implementação de cache determinístico vigoroso e modo mock automático para desenvolvimento e testes unitários.
- **[Risco: Não determinismo no output de fluxogramas afetando renderização]**
  → *Mitigação*: Na versão v2 de prompts, inclusão de restrições rígidas de sintaxe Mermaid (usando bloco ````mermaid e grafos direcionados `flowchart TD`) com fallback em texto estruturado caso a sintaxe quebre.
- **[Risco: Complexidade temporal com prazo de 48 horas]**
  → *Mitigação*: Utilização de dependências maduras em Python (`pydantic`, `typer`, `rich`, `streamlit`), sem reinventar componentes de serialização, validação ou UI.
- **[Risco: Variação nas notas atribuídas pela rubrica]**
  → *Mitigação*: Uso de critérios pontuados objetivos e temperatura baixa (0.1 ou 0.2) na chamada do avaliador para maximizar consistência.

## Open Questions

Nenhuma no momento. O escopo e os requisitos estão completamente delimitados para execução em 48 horas.
