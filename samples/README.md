# Exemplos (`samples/`)

> Saídas **reais** geradas com o modelo **`gemini-3.5-flash`** em 2026-11-22, a partir dos casos de `sample_input.json`.

| Arquivo | Conteúdo | Origem |
| :--- | :--- | :--- |
| `sample_input.json` | 4 casos de teste (um por perfil) | Escrito manualmente |
| `sample_diagnostico.txt` | Diagnóstico (v2) do `caso_01_iniciante` | Gemini real |
| `sample_passo_a_passo.txt` | Passo a passo (v2) do `caso_01_iniciante` | Gemini real |
| `sample_perguntas.txt` | Perguntas de esclarecimento (v2) do `caso_01_iniciante` | Gemini real |
| `sample_fluxograma.txt` | Fluxograma Mermaid (v2) do `caso_01_iniciante` | Gemini real |
| `sample_comparison.json` | Comparação v1 x v2 do `caso_01_iniciante` (diagnóstico) | Gemini real + avaliador atual |

## Observações

- Os textos são a saída do modelo sem edição, precedidos apenas por uma linha de origem.
- As notas em `sample_comparison.json` foram calculadas pelo avaliador heurístico de `src/evaluator.py`, que mede sinais de estrutura e vocabulário, não a correção factual. Neste caso, as versões empataram (4.67): a v2 ganhou em acionabilidade e perdeu em clareza por ultrapassar 450 palavras.
- O fluxograma não foi renderizado como parte desta rodada; a validade do diagrama Mermaid não foi verificada em um renderizador.
- As métricas da rodada completa (11 comparações) estão em `PROMPT_ENGINEERING_NOTES.md`, seção 4.

## Como regenerar

Com `GEMINI_API_KEY` e `LLM_MODEL=gemini-3.5-flash` no `.env`:

```bash
python main.py generate 'Meu roteador está com uma luz vermelha piscando e a internet sumiu. Não entendo nada de rede e tenho medo de quebrar o aparelho se apertar algo errado. Me ajudem por favor!' --profile iniciante --type todos --version v2
python main.py compare 'Meu roteador está com uma luz vermelha piscando e a internet sumiu. Não entendo nada de rede e tenho medo de quebrar o aparelho se apertar algo errado. Me ajudem por favor!' --profile iniciante --type diagnostico
```

A CLI exibe o resultado no terminal e grava o texto em `storage/runs/` e `storage/comparisons/` (ignorados pelo Git); os arquivos deste diretório foram copiados do campo `output_text` desses registros. Respostas já geradas são reaproveitadas pelo cache; use `--no-cache` para forçar novas chamadas.
