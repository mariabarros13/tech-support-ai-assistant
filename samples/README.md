# Exemplos (`samples/`)

> Saídas **reais** geradas com o modelo **`gemini-3.5-flash`** em 2026-11-22, a partir dos casos de `sample_input.json`.

| Arquivo | Conteúdo | Origem |
| :--- | :--- | :--- |
| `sample_input.json` | 4 casos de teste (um por perfil) | Escrito manualmente |
| `sample_diagnostico.txt` | Diagnóstico (v2) do `caso_01_iniciante` | Gemini real |
| `sample_passo_a_passo.txt` | Passo a passo (v2) do `caso_01_iniciante` | Gemini real |
| `sample_perguntas.txt` | Perguntas de esclarecimento (v2) do `caso_01_iniciante` | Gemini real |
| `sample_fluxograma.txt` | Fluxograma Mermaid (v2) do `caso_01_iniciante` | Gemini real |
| `sample_comparison.json` | Comparação v1 x v2 do `caso_01_iniciante` (diagnóstico) | Gemini real + avaliação heurística (`v1_scores`, `v2_scores`) + avaliação manual (`evaluation`) |

## Observações

- Os textos são a saída do modelo sem edição, precedidos apenas por uma linha de origem.
- `sample_comparison.json` reúne duas avaliações do mesmo caso, com a mesma rubrica de 3 critérios (1 a 5):
  - **Heurística automática** (`v1_scores`, `v2_scores`): calculada por `src/evaluator.py`, que mede sinais de estrutura e vocabulário, não a correção factual. Aqui as versões empataram (4.67): a v2 ganhou em acionabilidade e perdeu em clareza por ultrapassar 450 palavras.
  - **Avaliação manual do candidato** (`evaluation`, com `v1`, `v2` e `conclusao`): notas e justificativas escritas após ler as duas saídas, nas chaves `clarity`, `customer_fit` e `actionability`. Aqui a v2 vence por 14 a 11. A comparação está em `PROMPT_ENGINEERING_NOTES.md`, seção 4.
- O fluxograma não foi renderizado como parte desta rodada; a validade do diagrama Mermaid não foi verificada em um renderizador.
- As métricas da rodada completa (11 comparações) estão em `PROMPT_ENGINEERING_NOTES.md`, seção 4.

## Como regenerar

Com `GEMINI_API_KEY` e `LLM_MODEL=gemini-3.5-flash` no `.env`:

```bash
python main.py generate 'Meu roteador está com uma luz vermelha piscando e a internet sumiu. Não entendo nada de rede e tenho medo de quebrar o aparelho se apertar algo errado. Me ajudem por favor!' --profile iniciante --type todos --version v2
python main.py compare 'Meu roteador está com uma luz vermelha piscando e a internet sumiu. Não entendo nada de rede e tenho medo de quebrar o aparelho se apertar algo errado. Me ajudem por favor!' --profile iniciante --type diagnostico
```

A CLI exibe o resultado no terminal e grava o texto em `storage/runs/` e `storage/comparisons/` (ignorados pelo Git); os arquivos deste diretório foram copiados do campo `output_text` desses registros. Respostas já geradas são reaproveitadas pelo cache; use `--no-cache` para forçar novas chamadas.
