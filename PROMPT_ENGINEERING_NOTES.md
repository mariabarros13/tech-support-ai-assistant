# Notas de Engenharia de Prompt (Prompt Engineering Notes)

## 1. Visão Geral e Hipóteses

O objetivo deste projeto é construir um assistente de atendimento ao cliente com IA capaz de gerar quatro tipos de conteúdo essenciais para suporte técnico:
1. **Diagnóstico do problema**
2. **Passo a passo resolutivo**
3. **Perguntas de esclarecimento**
4. **Fluxograma de atendimento**

### Hipótese Fundamental
Prompts "zero-shot" ingênuos (versão **v1 / Baseline**) geram respostas genéricas, prolixas e frequentemente desalinhadas com o perfil psicológico e o nível técnico do cliente. Ao aplicar técnicas avançadas de Engenharia de Prompt (versão **v2 / Aprimorada**)—incluindo adoção de persona especializada, injeção contextual de restrições negativas, seções estruturadas e sintaxe estrita (Mermaid)—é possível elevar substancialmente a **clareza**, a **adequação ao nível do cliente** e a **acionabilidade** das respostas, mensuradas objetivamente pela rubrica oficial.

---

## 2. Técnicas de Engenharia de Prompt Aplicadas (v1 vs v2)

| Tipo de Conteúdo | Versão v1 (Baseline) | Versão v2 (Aprimorada com Engenharia de Prompt) |
| :--- | :--- | :--- |
| **Diagnóstico** | Instrução direta em texto corrido ("analise e forneça diagnóstico"). Sem divisões. | Persona sênior de suporte; seções padronizadas (`Resumo`, `Causa Provável`, `Fatores Contribuintes`, `Gravidade/Esforço`); adequação terminológica à persona. |
| **Passo a Passo** | Lista sequencial genérica sem distinção de pré-requisitos ou checagem de sucesso. | Verbos de ação no imperativo; divisão em `Pré-requisitos`, `Plano de Ação`, `Checagem de Sucesso (Como saber se deu certo)` e `Próximo Passo se falhar`. |
| **Perguntas de Esclarecimento** | Formulação livre de perguntas sem limite ou justificativa. | Delimitação estrita (2 a 4 perguntas cirúrgicas); explicação transparente de *por que* a informação é necessária; opções de checagem adaptadas. |
| **Fluxograma** | Instrução livre ("gere um fluxograma em texto ou mermaid"). Frequentemente produz sintaxes quebradas. | Sintaxe estrita de bloco ````mermaid` com `flowchart TD`; nós com identificadores alfanuméricos e rótulos entre aspas duplas; ramos `Sim`/`Não`; resumo textual de caminho crítico. |

### Principais Técnicas Utilizadas na Versão v2
1. **Persona & Role Prompting**: Atribuição de papéis de autoridade técnica e inteligência emocional ("Especialista Sênior em Suporte", "Arquiteto de Processos").
2. **Injeção de Restrições Negativas (Negative Constraints)**: Bloqueio explícito de termos proibidos (ex.: não usar jargões obscuros com leigos; não sugerir 'reiniciar o PC' para perfis técnicos avançados).
3. **Estruturação Delimitada (Markdown Sections)**: Uso de cabeçalhos de nível 3 para forçar o LLM a preencher campos sem alucinar formatos aleatórios.
4. **Acionabilidade e Checagens de Validação**: Garantia de que cada instrução possua um critério observável de sucesso pelo usuário.

---

## 3. Rubrica Oficial de Avaliação

A comparação e benchmarking entre versões de prompts utiliza **estritamente três critérios oficiais**, avaliados em escala de 1 a 5 com justificativas textuais:

### 1. Clareza (Escala 1 a 5)
- **1 - Confuso / Amíguo**: Texto truncado, ideias desconexas ou excesso de frases prolixas sem hierarquia visual.
- **3 - Razoável**: Compreensível, mas com parágrafos densos ou terminologia pouco organizada.
- **5 - Excelente**: Estrutura modular cristalina, seções bem divididas, títulos informativos e leitura fluida.

### 2. Adequação ao Nível do Cliente (Escala 1 a 5)
- **1 - Desalinhado**: Trata um cliente leigo com comandos de terminal complexos ou trata um administrador de sistemas com orientações infantis e óbvias.
- **3 - Parcialmente Adequado**: Atende superficialmente ao pedido, mas sem calibrar o tom emocional (ex.: impaciência do apressado ou frustração do irritado).
- **5 - Perfeitamente Calibrado**: Adaptação cirúrgica de vocabulário, profundidade técnica e empatia, respeitando todas as restrições da persona em JSON.

### 3. Acionabilidade (Escala 1 a 5)
- **1 - Teórico / Inútil**: Apenas filosofa sobre o problema sem oferecer nenhum passo prático ou teste real.
- **3 - Moderado**: Lista etapas básicas, mas omite como o cliente pode verificar se o problema foi resolvido ou o que fazer caso falhe.
- **5 - Altamente Acionável**: Passos imediatos com verbos no imperativo, pontos de checagem observáveis ("Como confirmar que deu certo") e diagrama de decisão executável.

*(Observação: Validações sintáticas internas adicionais, como integridade de blocos Mermaid ou conformidade de schemas JSON, funcionam como asserções automatizadas complementares e não alteram a rubrica oficial de 3 critérios).*

### Implementação Automatizada da Rubrica
O avaliador em `src/evaluator.py` aplica a rubrica de forma **determinística e heurística**, com as mesmas regras para v1 e v2 (ele não recebe a versão do prompt):

- **Clareza**: presença de seções/títulos, itens de lista, tamanho médio das frases e extensão total.
- **Adequação ao nível do cliente**: derivada dos campos do perfil. Penaliza jargões para `iniciante`; recompensa profundidade técnica e penaliza sugestões básicas para `avancado`; para perfis com urgência, avalia brevidade e destaque da ação principal; para perfis frustrados, avalia empatia e penaliza transferência de culpa.
- **Acionabilidade**: critérios específicos por tipo de conteúdo (causa e ação no diagnóstico; passos, verificação de sucesso e contingência no passo a passo; quantidade e justificativa das perguntas; bloco Mermaid, decisões, transições e estado final no fluxograma).

As justificativas citam a evidência encontrada no texto e o resumo da comparação lista melhorias e regressões por critério. Limitação: a heurística mede forma e sinais de vocabulário, não a correção factual do conteúdo.

---

## 4. Análise dos Resultados e Comparação Prática

> **Status: resultados com o Gemini real ainda não coletados.** Os números abaixo foram obtidos em **modo Mock**, no qual as saídas são textos fixos por tipo de conteúdo e versão, independentes da mensagem do cliente e do perfil. Eles validam o pipeline (geração → avaliação → persistência) e o comportamento do avaliador, **não** a qualidade dos prompts v1/v2. A análise da hipótese da seção 1 depende de uma rodada com `GEMINI_API_KEY` válida.

Rodada Mock: os 4 casos de `samples/sample_input.json` × os 4 tipos de conteúdo (16 comparações), avaliados pelo avaliador heurístico atual:

| Critério | Média v1 | Média v2 | Delta |
| :--- | :---: | :---: | :---: |
| Clareza | 3.75 | 4.75 | +1.00 |
| Adequação ao nível do cliente | 3.31 | 3.31 | 0.00 |
| Acionabilidade | 3.25 | 5.00 | +1.75 |
| **Média geral** | **3.44** | **4.35** | **+0.91** |

- Vencedor: v2 em 15 comparações, v1 em 1 (`iniciante` / `passo_a_passo`).
- O avaliador detectou regressões reais nos textos do Mock: a v2 Mock usa termos como "tokens", "gateway", "cache" e "sessão", que reduzem a adequação para a cliente leiga; e nenhuma das versões Mock demonstra empatia com a cliente frustrada (`irritado`), o que mantém a adequação baixa nesse perfil.
- Esses achados mostram que a comparação não é favorável à v2 por construção; eles não dizem nada sobre o comportamento do Gemini com os prompts reais.

---

## 5. Conclusão e Lições Aprendidas

1. **Contexto Estruturado Supera Instruções Longas** *(hipótese de projeto)*: Separar o perfil em atributos explícitos (`technical_level`, `tone_mood`, `constraints`) e injetá-los no template tende a gerar maior aderência do que descrições longas em prosa. A confirmação depende da rodada com o modelo real.
2. **Formatação Estrita em Diagramas é Crítica** *(hipótese de projeto)*: Modelos de linguagem frequentemente quebram código Mermaid quando caracteres especiais são usados fora de aspas. A v2 restringe a sintaxe (identificadores alfanuméricos, rótulos entre aspas) para reduzir erros de parser; a taxa real de sucesso ainda precisa ser medida com o Gemini.
3. **Cache Determinístico Viabiliza Avaliação Barata e Rápida**: Com o hash SHA-256 das entradas (incluindo modelo e modo de execução), rodadas de comparação repetidas são atendidas pelo cache local, sem nova chamada de rede nem consumo de tokens.
4. **Avaliador Cego à Versão**: A primeira versão do avaliador atribuía notas com base na versão do prompt, garantindo a vitória da v2. A rubrica passou a ser aplicada apenas sobre o conteúdo, o que tornou possível identificar regressões.
