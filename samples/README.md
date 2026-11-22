# Exemplos (`samples/`)

> **Atenção: as saídas deste diretório são SINTÉTICAS, geradas em modo Mock (sem chamada à API do Gemini).**

| Arquivo | Conteúdo | Origem |
| :--- | :--- | :--- |
| `sample_input.json` | 4 casos de teste (um por perfil) | Escrito manualmente |
| `sample_diagnostico.txt` | Diagnóstico (v2) | Mock |
| `sample_passo_a_passo.txt` | Passo a passo (v2) | Mock |
| `sample_perguntas.txt` | Perguntas de esclarecimento (v2) | Mock |
| `sample_fluxograma.txt` | Fluxograma Mermaid (v2) | Mock |
| `sample_comparison.json` | Comparação v1 x v2 do `caso_01_iniciante` (diagnóstico) | Mock + avaliador atual |

## Limitações

- O Mock devolve **textos fixos por tipo de conteúdo e versão**, independentes do perfil e quase independentes da mensagem do cliente. Por isso o diagnóstico de exemplo fala em "falha de autenticação" para um problema de roteador: ele ilustra o **formato** esperado da v2, não uma resposta real.
- As notas em `sample_comparison.json` foram calculadas pelo avaliador heurístico atual (`src/evaluator.py`) e refletem apenas os textos do Mock. Elas não medem a qualidade dos prompts com o Gemini.

## Como gerar exemplos reais

Com `GEMINI_API_KEY` configurada no `.env`, rode os mesmos casos sem a flag `--mock`, por exemplo:

```bash
python main.py generate "Meu roteador está com uma luz vermelha piscando e a internet sumiu." --profile iniciante --type todos
python main.py compare "Meu roteador está com uma luz vermelha piscando e a internet sumiu." --profile iniciante --type diagnostico
```

Os resultados ficam em `storage/runs/` e `storage/comparisons/` (ignorados pelo Git); copie os que desejar publicar para este diretório.
