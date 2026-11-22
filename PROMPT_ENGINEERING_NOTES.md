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

### Condições da rodada
- **Modelo**: `gemini-3.5-flash` via API do Gemini, em 2026-11-22 (`mock_mode: false` em todos os registros). O modelo padrão anterior, `gemini-2.5-flash`, retornou HTTP 404 nesta conta.
- **Casos**: os 4 casos de `samples/sample_input.json` (um por perfil), comparando v1 x v2 para cada tipo de conteúdo.
- **Cobertura**: 11 das 16 comparações planejadas. As 4 comparações de **fluxograma** e a de **perguntas de esclarecimento** do perfil `irritado` não foram concluídas: a API passou a responder HTTP 429 (`RESOURCE_EXHAUSTED`) após cerca de 27 requisições e as novas tentativas continuaram bloqueadas. O fluxograma v2 do `caso_01_iniciante` foi gerado (ver `samples/sample_fluxograma.txt`), mas não entrou em nenhuma comparação.
- **Avaliação**: avaliador heurístico de `src/evaluator.py`, com os 3 critérios oficiais, aplicado da mesma forma às duas versões. Tokens lidos do `usage_metadata`.

### Resultado por comparação

| Perfil | Conteúdo | v1 (Clareza / Adequação / Acionabilidade) | Média v1 | v2 (Clareza / Adequação / Acionabilidade) | Média v2 | Vencedor |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| iniciante | diagnóstico | 5 / 5 / 4 | 4.67 | 4 / 5 / 5 | 4.67 | empate |
| iniciante | passo a passo | 4 / 5 / 5 | 4.67 | 4 / 5 / 5 | 4.67 | empate |
| iniciante | perguntas | 4 / 5 / 3 | 4.00 | 5 / 5 / 5 | 5.00 | v2 |
| apressado | diagnóstico | 5 / 4 / 5 | 4.67 | 5 / 5 / 5 | 5.00 | v2 |
| apressado | passo a passo | 5 / 4 / 3 | 4.00 | 5 / 4 / 5 | 4.67 | v2 |
| apressado | perguntas | 4 / 4 / 4 | 4.00 | 5 / 4 / 5 | 4.67 | v2 |
| tecnico | diagnóstico | 5 / 5 / 5 | 5.00 | 4 / 5 / 5 | 4.67 | v1 |
| tecnico | passo a passo | 5 / 5 / 2 | 4.00 | 4 / 5 / 5 | 4.67 | v2 |
| tecnico | perguntas | 5 / 5 / 3 | 4.33 | 4 / 5 / 5 | 4.67 | v2 |
| irritado | diagnóstico | 5 / 4 / 5 | 4.67 | 5 / 4 / 5 | 4.67 | empate |
| irritado | passo a passo | 5 / 4 / 3 | 4.00 | 5 / 4 / 5 | 4.67 | v2 |

### Médias por critério (11 comparações)

| Critério | Média v1 | Média v2 | Delta |
| :--- | :---: | :---: | :---: |
| Clareza | 4.73 | 4.55 | -0.18 |
| Adequação ao nível do cliente | 4.55 | 4.64 | +0.09 |
| Acionabilidade | 3.82 | 5.00 | +1.18 |
| **Média geral** | **4.36** | **4.73** | **+0.37** |

Vencedor: v2 em 7 comparações, empate em 3, v1 em 1 (`tecnico` / diagnóstico).

### Análise
- **Acionabilidade é o ganho consistente da v2** (+1.18; nota 5 em todas as 11). A v1 frequentemente omite a verificação de sucesso ou o plano de contingência no passo a passo (notas 2 e 3) e produz perguntas sem justificativa nem orientação de como obter a informação (nota 3). As seções obrigatórias da v2 ("Como Confirmar que Deu Certo", "Próximo Passo se Não Funcionar", "Por que precisamos disso") eliminam essas lacunas.
- **Clareza teve regressão por extensão**: as 4 quedas de clareza da v2 (iniciante/diagnóstico e os 3 casos do técnico) têm a mesma causa: a resposta ultrapassou 450 palavras (entre 459 e 687), enquanto a v1 ficou entre 277 e 421. Estrutura e tamanho das frases foram equivalentes. É essa queda que dá a única vitória da v1.
- **Adequação ao nível do cliente praticamente não diferenciou as versões** (+0.09). Com o modelo real, a v1 já adapta bem o vocabulário: ela recebe o nome do perfil (que contém o rótulo, ex.: "Iniciante / Leiga") e o nível técnico. Nenhuma das versões usou jargão com a cliente leiga, ambas mostraram profundidade técnica ao perfil avançado e ambas validaram o sentimento da cliente frustrada. A única melhoria veio da brevidade da v2 para o cliente apressado no diagnóstico (120 palavras). Limitação: a heurística não verifica as restrições específicas do perfil (ex.: "no máximo 3 a 5 itens" para o apressado), então ganhos reais nesse ponto podem não estar refletidos na nota.

### Custo e latência (chamadas não atendidas pelo cache)

| Versão | Chamadas | Latência média | Latência máxima | Tokens de entrada | Tokens de saída | Tokens de raciocínio | Total |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| v1 | 11 | 12.6 s | 17.1 s | 137 | 524 | 1027 | 1687 |
| v2 | 12 | 14.3 s | 29.8 s | 616 | 685 | 1299 | 2600 |

A v2 consome cerca de 54% mais tokens por chamada (prompt 4,5 vezes maior e respostas mais longas) e é ~13% mais lenta em média. Os tokens de raciocínio representam a maior parcela do custo nas duas versões. A latência máxima observada (29.8 s) ficou abaixo do timeout padrão de 60 s.

---

## 5. Conclusão e Lições Aprendidas

1. **Estrutura Obrigatória Gera Acionabilidade; o Perfil Básico Já Gera Adequação**: Na rodada real, o ganho da v2 veio principalmente das seções obrigatórias (verificação de sucesso, contingência, justificativa das perguntas), com acionabilidade 5 em todas as comparações. A hipótese de que injetar mais atributos do perfil (`tone_mood`, `constraints`) melhoraria a adequação não se confirmou pela rubrica: a v1, que recebe apenas nome e nível técnico, já foi adequada ao perfil (4.55 contra 4.64). O custo da v2 é uma resposta mais longa, que reduziu a clareza em 4 de 11 casos; limitar a extensão na v2 é o próximo ajuste natural.
2. **Formatação Estrita em Diagramas é Crítica** *(hipótese de projeto, ainda não medida)*: Modelos de linguagem frequentemente quebram código Mermaid quando caracteres especiais são usados fora de aspas. A v2 restringe a sintaxe (identificadores alfanuméricos, rótulos entre aspas) para reduzir erros de parser. O único fluxograma real gerado (`samples/sample_fluxograma.txt`) segue essas regras, mas as comparações de fluxograma não foram concluídas e nenhum diagrama foi validado em um renderizador.
3. **Cache Determinístico Viabiliza Avaliação Barata e Rápida**: Com o hash SHA-256 das entradas (incluindo modelo e modo de execução), rodadas de comparação repetidas são atendidas pelo cache local, sem nova chamada de rede nem consumo de tokens.
4. **Avaliador Cego à Versão**: A primeira versão do avaliador atribuía notas com base na versão do prompt, garantindo a vitória da v2. A rubrica passou a ser aplicada apenas sobre o conteúdo, o que tornou possível identificar regressões.
