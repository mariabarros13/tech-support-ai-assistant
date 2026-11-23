# Assistente de Atendimento ao Cliente com IA e Engenharia de Prompt

Assistente inteligente de atendimento ao cliente desenvolvido em Python, focado em Engenharia de Prompt avançada, suporte a perfis de clientes estruturados em JSON, cache determinístico, persistência de execuções e avaliação comparativa de prompts baseada em rubrica oficial.

> 🚀 **Demonstração online:** [https://tech-support-ai-assistant.streamlit.app/](https://tech-support-ai-assistant.streamlit.app/)

---

## 🎯 Funcionalidades Principais

- **Quatro Conteúdos de Atendimento**:
  1. *Diagnóstico do Problema*: identificação de causas, sintomas e esforço estimado.
  2. *Passo a Passo Resolutivo*: instruções imperativas com critérios de validação de sucesso.
  3. *Perguntas de Esclarecimento*: levantamento objetivo e justificado de informações faltantes.
  4. *Fluxograma de Atendimento*: árvore de decisão com ramificações Sim/Não gerada em sintaxe estrita Mermaid.
- **Perfis de Clientes em JSON (`profiles/`)**:
  - `iniciante.json` (Maria Silva): didática, acolhedora, sem jargões técnicos.
  - `apressado.json` (Carlos Mendes): telegráfica, direta ao ponto, foco na ação imediata.
  - `tecnico.json` (Roberto Albuquerque): analítica, profunda, com logs, portas e causas-raiz.
  - `irritado.json` (Fernanda Rocha): de-escalonamento emocional, empatia e compromisso de solução.
- **Versionamento de Prompts (`prompts/`)**:
  - `v1` (Baseline): instruções zero-shot simples.
  - `v2` (Aprimorada): persona adoption, restrições negativas, formatação estrita e sintaxe Mermaid.
- **Cache Determinístico (SHA-256)**:
  - Cache local em `storage/cache/` para evitar chamadas redundantes de rede, poupar cota e reduzir latência.
- **Persistência Estruturada em JSON (`storage/`)**:
  - `storage/runs/`: registros de todas as execuções com timestamps, latência e metadados.
  - `storage/comparisons/`: relatórios de benchmarking comparativo com notas da rubrica.
- **Rubrica Oficial de Avaliação (1 a 5 com Justificativas)**:
  - **1. Clareza**: linguagem direta, sem ambiguidades e com hierarquia visual.
  - **2. Adequação ao nível do cliente**: calibração precisa para a persona em JSON.
  - **3. Acionabilidade**: passos imediatos, práticos e com checagem de sucesso.
  - O avaliador (`src/evaluator.py`) é **determinístico e heurístico**: pontua v1 e v2 com as mesmas regras, sem saber qual versão gerou o texto, a partir de sinais objetivos (seções, listas, tamanho das frases, jargões, termos técnicos, empatia, passos numerados, verificação de sucesso, contingência, estrutura Mermaid). As justificativas citam a evidência encontrada e o resumo aponta melhorias e regressões por critério. Por ser heurístico, não avalia a correção factual da resposta.
- **Interfaces**:
  - **CLI Completa** com `typer` e `rich` para execução e automação no terminal.
  - **Interface Web Demonstrativa** interativa com `streamlit`.

---

## 📁 Estrutura do Projeto

```text
├── profiles/                  # Perfis de clientes em JSON
│   ├── iniciante.json
│   ├── apressado.json
│   ├── tecnico.json
│   └── irritado.json
├── prompts/                   # Templates versionados de prompts
│   ├── diagnostico/           # v1.txt e v2.txt
│   ├── passo_a_passo/         # v1.txt e v2.txt
│   ├── perguntas_esclarecimento/ # v1.txt e v2.txt
│   └── fluxograma/            # v1.txt e v2.txt
├── src/                       # Código-fonte da aplicação
│   ├── config.py              # Variáveis de ambiente e caminhos
│   ├── models.py              # Schemas de dados com Pydantic
│   ├── cache_manager.py       # Cache determinístico SHA-256
│   ├── llm_client.py          # Cliente Gemini com modo Mock offline
│   ├── storage.py             # Persistência de runs e comparações em JSON
│   ├── generator.py           # Orquestrador de geração dos 4 conteúdos
│   ├── evaluator.py           # Motor de avaliação pela rubrica oficial
│   └── cli.py                 # Interface de linha de comando (CLI)
├── web/                       # Interface Web Demonstrativa
│   └── app.py                 # Aplicação interativa em Streamlit
├── samples/                   # Casos de teste e saídas de exemplo (saídas reais do Gemini)
│   ├── README.md              # Origem e limitações dos exemplos
│   ├── sample_input.json
│   ├── sample_diagnostico.txt
│   ├── sample_passo_a_passo.txt
│   ├── sample_perguntas.txt
│   ├── sample_fluxograma.txt
│   └── sample_comparison.json
├── storage/                   # Diretório de armazenamento local
│   ├── cache/
│   ├── runs/
│   └── comparisons/
├── tests/                     # Suíte de testes automatizados com pytest
│   ├── test_profiles_and_prompts.py
│   ├── test_llm_and_cache.py
│   ├── test_storage_and_generator.py
│   ├── test_evaluator.py
│   ├── test_security_and_gitignore.py
│   └── test_cli.py
├── main.py                    # Ponto de entrada da CLI
├── requirements.txt           # Dependências do projeto
├── .env.example               # Modelo de variáveis de ambiente
├── PROMPT_ENGINEERING_NOTES.md# Análise de engenharia de prompt e rubrica
└── README.md                  # Documentação completa
```

---

## 🚀 Instalação e Configuração

### 1. Clonar e Acessar o Diretório
```bash
cd vlab-desafio-IA
```

### 2. Configurar o Ambiente Virtual Python (Recomendado)
```bash
python -m venv .venv
# No Windows:
.venv\Scripts\activate
# No Linux/Mac:
source .venv/bin/activate
```

### 3. Instalar Dependências
```bash
python -m pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
copy .env.example .env
```
Edite o arquivo `.env` para inserir sua chave da API Google Gemini (`GEMINI_API_KEY`).

### 5. Modo Real x Modo Mock
- **Modo real (padrão)**: exige `GEMINI_API_KEY` válida. Se a chave estiver ausente (ou com o placeholder `sua_chave_aqui`), a CLI **interrompe a execução** com código de saída `1` e uma mensagem orientando a configurar o `.env` ou usar `--mock`. Não há ativação automática do Mock.
- **Modo Mock (opt-in)**: ativado explicitamente com a flag `--mock` na CLI, com `MOCK_MODE=true` no `.env` ou com a caixa "Modo Mock" na interface web (que vem **marcada por padrão** na web). O Mock devolve **textos fixos e sintéticos** por tipo de conteúdo e versão, sem chamar a API: serve para testar o fluxo offline, não para avaliar a qualidade dos prompts.
- **Isolamento do cache**: o modo de execução faz parte da chave do cache, portanto respostas Mock nunca são servidas a execuções reais (e vice-versa). Cada registro em `storage/runs/` informa `metadata.mock_mode`.
- **Erros da API tratados**: autenticação (401/403 ou 400 `API_KEY_INVALID`), limite de requisições/quota (429), modelo inexistente ou indisponível (404), indisponibilidade do serviço (500/502/503/504) e falhas de conexão ou timeout da biblioteca HTTP do SDK geram mensagens específicas (com o código HTTP) e código de saída `1`. A classificação usa o tipo da exceção e o código HTTP, não o texto da mensagem.
- **Timeout**: cada chamada ao Gemini espera no máximo `LLM_TIMEOUT_SECONDS` segundos (padrão `60`; valores vazios, inválidos ou não positivos usam o padrão). Sem essa configuração, o SDK não impõe limite e uma chamada poderia ficar travada indefinidamente. Ao estourar o limite, a CLI informa o tempo configurado e sai com código `1`.
- **Registro de tokens**: em chamadas reais, `metadata.token_usage` traz `prompt_tokens`, `completion_tokens`, `thoughts_tokens` (raciocínio interno dos modelos com raciocínio, como 2.5 e 3.5, cobrado como saída) e `total_tokens`, lidos do `usage_metadata` do Gemini. O campo `source` indica a origem: `usage_metadata` (valor real), `word_estimate` (API não informou; estimativa por palavras) ou `mock_estimate` (modo Mock).

---

## 💻 Uso da Linha de Comando (CLI)

### 1. Listar Perfis Disponíveis
```bash
python main.py profiles
```

### 2. Gerar Conteúdo de Atendimento
Gerar os 4 conteúdos para o perfil leigo/iniciante usando a API real do Gemini (requer `GEMINI_API_KEY`):
```bash
python main.py generate "Meu roteador está com luz vermelha piscando" --profile iniciante --type todos
```

Os exemplos a seguir usam `--mock` para rodar offline, sem chave e sem consumir cota (saídas sintéticas).

Mesmo comando em modo Mock:
```bash
python main.py generate "Meu roteador está com luz vermelha piscando" --profile iniciante --type todos --mock
```

Gerar apenas o passo a passo com versão v2 e perfil apressado:
```bash
python main.py generate "Painel travou em reunião de diretoria" --profile apressado --type passo_a_passo --mock
```

Ignorar o cache e forçar nova inferência:
```bash
python main.py generate "Erro 504 no endpoint" --profile tecnico --type diagnostico --no-cache --mock
```

### 3. Comparar Versões de Prompts (Rubrica Oficial de 3 Critérios)
```bash
python main.py compare "Meu aplicativo fechou sozinho e perdi os dados" --profile irritado --type passo_a_passo --mock
```

### 4. Consultar Histórico Persistido
Visualizar últimas execuções:
```bash
python main.py history --type runs --limit 10
```

Visualizar últimas comparações de prompts:
```bash
python main.py history --type comparisons --limit 10
```

---

## 🌐 Interface Web Demonstrativa (Streamlit)

🔗 **Aplicação publicada (Streamlit Community Cloud):** [https://tech-support-ai-assistant.streamlit.app/](https://tech-support-ai-assistant.streamlit.app/)

Para abrir a interface web visual:
```bash
streamlit run web/app.py
```
No Windows, se o comando `streamlit` não for reconhecido (pasta de scripts do Python fora do `PATH`), use:
```bash
python -m streamlit run web/app.py
```
A interface será aberta em `http://localhost:8501`. A caixa **Modo Mock** vem marcada por padrão; desmarque-a para usar o Gemini real (requer `GEMINI_API_KEY`). A interface oferece:
- Seleção visual de personas e inspeção de restrições.
- Abas com os 4 conteúdos formatados e **renderização gráfica de diagramas Mermaid**.
- Painel de comparação lado a lado de v1 vs v2 com pontuações da rubrica oficial e veredito analítico.
- Tabelas de auditoria de execuções persistidas e cache.

### Nota de acesso para a banca avaliadora

- **API real x Modo Mock**: a barra lateral permite alternar entre a API real (`gemini-3.5-flash`) e o **Modo Mock**. Se a cota gratuita diária de requisições da API estiver esgotada no momento do teste, **recomenda-se o Modo Mock**: ele responde offline com textos sintéticos e permite percorrer todo o fluxo da interface (a qualidade dos prompts deve ser avaliada pelos exemplos reais em `samples/`).
- **Armazenamento efêmero**: na nuvem, o diretório `storage/` (execuções, comparações e cache) é temporário e dura apenas enquanto a sessão do container estiver ativa. Reinicializações da aplicação apagam esse histórico.

---

## 🧪 Testes Automatizados

Para executar toda a suíte de testes unitários e de integração:
```bash
python -m pytest tests/ -v
```
A suíte cobre validação de perfis e templates, cache determinístico (incluindo isolamento entre Mock e modo real), tratamento de erros da API Gemini, registro de tokens via `usage_metadata`, persistência, rubrica oficial, regras do `.gitignore` e interface CLI. Todos os testes rodam offline: a API do Gemini é simulada e os testes da CLI usam diretórios temporários, sem gravar em `storage/`.

## ⚠️ Limitações Conhecidas

- A rodada real documentada em `PROMPT_ENGINEERING_NOTES.md` cobre 11 das 16 comparações planejadas: as 4 de fluxograma e a de perguntas de esclarecimento do perfil `irritado` foram interrompidas por limite de cota da API (HTTP 429).
- O avaliador é heurístico (ver seção da rubrica); ele não substitui revisão humana nem um avaliador baseado em LLM.
