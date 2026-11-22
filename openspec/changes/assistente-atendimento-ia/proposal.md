# Proposal

## Why

O suporte ao cliente em ambientes digitais frequentemente enfrenta inconsistências de tom, respostas genéricas que desconsideram o nível técnico do usuário e lentidão na geração de artefatos estruturados para resolução de chamados. A aplicação de Engenharia de Prompt combinada a modelos de linguagem modernos (LLMs) permite gerar respostas altamente contextualizadas, adaptadas a perfis específicos de clientes e organizadas em múltiplos formatos úteis (diagnósticos, planos passo a passo, perguntas de esclarecimento e fluxogramas operacionais).

Com a restrição de entrega em 48 horas, é essencial estabelecer uma base sólida, modular e facilmente testável que integre chamadas à API de LLM com cache determinístico para eficiência de custos/latência, persistência em JSON para rastreabilidade, uma interface CLI robusta e um framework de avaliação comparativa baseado em rubrica formal para mensurar a evolução entre versões de prompts (v1 vs v2).

## What Changes

Esta proposta introduz a arquitetura inicial e a implementação completa do assistente de atendimento inteligente:

- **Perfis de Clientes Estruturados (JSON)**: Criação de 3 a 5 personas com atributos como nível técnico, tom emocional, canal de atendimento preferido e contexto de uso (ex.: Leigo/Iniciante, Apressado/Impaciente, Técnico/Avançado, Irritado/Frustrado).
- **Geração de Conteúdos Especializados**: Suporte à geração de 4 tipos de artefatos essenciais:
  1. *Diagnóstico do problema*: identificação clara da causa provável com base no relato do cliente.
  2. *Passo a passo resolutivo*: instruções claras, ordenadas e adaptadas à familiaridade do cliente com tecnologia.
  3. *Perguntas de esclarecimento*: levantamento objetivo de informações faltantes caso o problema seja ambíguo.
  4. *Fluxograma de atendimento*: representação textual/sintática (Mermaid ou ASCII) da árvore de decisão/resolução.
- **Engenharia e Versionamento de Prompts**: Organização desacoplada de prompts em arquivos dedicados por tipo de conteúdo e versão (`prompts/<conteudo>/v1.txt` e `v2.txt`), aplicando técnicas avançadas (persona adoption, few-shot, restrições explícitas de formato e raciocínio estruturado).
- **Integração com API de LLM**: Camada de serviço desacoplada para conexão com provedores de LLM (Google Gemini / OpenAI / LiteLLM) via chave de API gerenciada por variáveis de ambiente (`.env`).
- **Sistema de Cache Determinístico**: Camada de cache baseada em hash SHA-256 (payload de entrada + perfil + versão do prompt + modelo) para evitar chamadas redundantes à API, economizando custos e tempo.
- **Persistência de Execuções e Histórico em JSON**: Armazenamento estruturado de cada geração com metadados (timestamp, tokens, latência, versão de prompt, perfil e saída).
- **Mecanismo de Avaliação e Comparação de Prompts (Rubrica Oficial)**: Módulo de benchmarking que executa e contrasta saídas da versão `v1` vs `v2` sob os mesmos perfis, gerando relatórios de avaliação com notas de 1 a 5 e justificativas nos três critérios oficiais: clareza, adequação ao nível do cliente e acionabilidade (permitindo verificações internas de sintaxe/formatação como checagens complementares sem alterar a rubrica oficial).
- **CLI Obrigatória**: Interface de linha de comando completa para interagir com o assistente, alternar perfis, selecionar versões de prompt, disparar execuções em lote e rodar o pipeline de comparação.
- **Interface Web Demonstrável (Diferencial)**: Interface interativa leve (Streamlit/FastAPI) para testes rápidos e demonstração visual dos fluxogramas e comparações.
- **Documentação e Entregáveis**: `README.md`, `requirements.txt`, `.env.example`, diretório de exemplos `samples/` e o documento analítico `PROMPT_ENGINEERING_NOTES.md`.

## Capabilities

### New Capabilities
- `content-generation`: Geração dos 4 tipos de conteúdo de atendimento (diagnóstico, passo a passo, perguntas de esclarecimento, fluxograma) condicionados a perfis de clientes em JSON e templates de prompts versionados.
- `prompt-evaluation`: Mecanismo de comparação entre versões de prompts (v1 vs v2) aplicando a rubrica oficial de qualidade e conformidade com perfis.
- `execution-management`: Camada de persistência em JSON de execuções e histórico, acompanhada de cache determinístico baseado em hash para chamadas de LLM.
- `user-interface`: Interface de linha de comando (CLI) obrigatória para operação e automação do sistema, acrescida de interface web leve demonstrável.

### Modified Capabilities
Nenhuma. Trata-se da fundação inicial do sistema.

## Impact

- **Código e Arquitetura**: Novo repositório modular em Python (3.11+), com separação clara entre domínio (modelos/perfis), serviços (LLM, cache, persistência, avaliador), prompts (arquivos de texto versionados) e interfaces (CLI e Web).
- **Dependências**: Adição de dependências essenciais e leves (`google-genai` ou `openai`, `pydantic`, `python-dotenv`, `typer` ou `click`, `rich`, e opcionalmente `streamlit`).
- **Configuração e Ambiente**: Criação de `.env.example` exigindo chave de API de LLM e parâmetros de configuração (diretório de cache, diretório de persistência).
- **Sistemas Externos**: Chamadas de rede para a API de LLM configurada, mitigadas localmente pelo cache determinístico.
