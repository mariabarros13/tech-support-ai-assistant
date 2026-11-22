"""Interface de Linha de Comando (CLI) para o Assistente de Atendimento ao Cliente com IA."""

import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import CACHE_DIR, GEMINI_API_KEY
from src.evaluator import PromptEvaluator
from src.generator import ContentGenerator
from src.llm_client import (
    LLMClient,
    LLMError,
    MissingAPIKeyError,
    AuthenticationError,
    RateLimitError,
    ModelUnavailableError,
    ServiceUnavailableError,
)
from src.models import ContentType, PromptVersion
from src.storage import StorageManager

app = typer.Typer(
    name="assistente-ia",
    help="Assistente de Atendimento ao Cliente com IA e Engenharia de Prompt",
    add_completion=False,
)
console = Console()


def ensure_utf8_output() -> None:
    """Garante saída em UTF-8 no terminal.

    No Windows, quando a saída é redirecionada ou passa por pipe (Git Bash, CI, `> arquivo`),
    o Python usa a codificação local (ex.: cp1252), que não representa emojis nem todos os
    caracteres das caixas do rich, o que causava UnicodeEncodeError no meio das mensagens.
    """
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        reconfigure = getattr(stream, "reconfigure", None)
        if encoding != "utf8" and callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def run() -> None:
    """Ponto de entrada da CLI."""
    ensure_utf8_output()
    app()


def get_generator(mock: bool = False) -> ContentGenerator:
    llm = LLMClient(mock_mode=mock)
    storage = StorageManager()
    return ContentGenerator(llm_client=llm, storage_manager=storage)


@app.command("profiles")
def list_profiles():
    """Lista todos os perfis de clientes disponíveis."""
    generator = get_generator()
    profiles = generator.get_available_profiles()

    table = Table(title="Perfis de Clientes Disponíveis", header_style="bold cyan")
    table.add_column("ID", style="bold green", width=12)
    table.add_column("Nome", style="bold white", width=32)
    table.add_column("Nível Técnico", style="yellow", width=14)
    table.add_column("Estado Emocional", style="magenta", width=20)
    table.add_column("Preferência de Comunicação", style="white")

    for p in profiles:
        table.add_row(p.id, p.name, p.technical_level, p.tone_mood, p.communication_preference)

    console.print(table)


@app.command("generate")
def generate_content(
    message: str = typer.Argument(..., help="Mensagem / relato de problema do cliente"),
    profile: str = typer.Option("iniciante", "--profile", "-p", help="ID do perfil (iniciante, apressado, tecnico, irritado)"),
    content_type: str = typer.Option("todos", "--type", "-t", help="Tipo de conteúdo (diagnostico, passo_a_passo, perguntas_esclarecimento, fluxograma, todos)"),
    version: str = typer.Option("v2", "--version", "-v", help="Versão do prompt (v1 ou v2)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Ignora o cache determinístico"),
    mock: bool = typer.Option(False, "--mock", help="Força a execução em modo Mock offline"),
):
    """Gera conteúdos estruturados de atendimento ao cliente."""
    try:
        generator = get_generator(mock=mock)
        p_version = PromptVersion(version.lower())
        use_cache = not no_cache

        console.print(f"[bold blue]Processando solicitação com perfil '[green]{profile}[/green]' e versão '[yellow]{version}[/yellow]'...[/bold blue]\n")

        if content_type.lower() == "todos":
            results = generator.generate_all(
                profile_id=profile,
                customer_message=message,
                prompt_version=p_version,
                use_cache=use_cache,
            )
            for c_type, record in results.items():
                cache_status = "[green]CACHE HIT[/green]" if record.cached else "[yellow]NOVA CHAMADA[/yellow]"
                panel_title = f"{c_type.value.upper()} | {cache_status} | Latência: {record.latency_ms}ms"
                console.print(Panel(record.output_text, title=panel_title, border_style="cyan"))
        else:
            c_type = ContentType(content_type.lower())
            record = generator.generate_single(
                content_type=c_type,
                profile_id=profile,
                customer_message=message,
                prompt_version=p_version,
                use_cache=use_cache,
            )
            cache_status = "[green]CACHE HIT[/green]" if record.cached else "[yellow]NOVA CHAMADA[/yellow]"
            panel_title = f"{c_type.value.upper()} | {cache_status} | Latência: {record.latency_ms}ms"
            console.print(Panel(record.output_text, title=panel_title, border_style="cyan"))

    except MissingAPIKeyError as e:
        console.print(Panel(str(e), title="[bold yellow]Configuração de API Necessária[/bold yellow]", border_style="yellow"))
        raise typer.Exit(code=1)
    except AuthenticationError as e:
        console.print(Panel(str(e), title="[bold red]Erro de Autenticação[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except RateLimitError as e:
        console.print(Panel(str(e), title="[bold yellow]Limite Excedido (Rate Limit)[/bold yellow]", border_style="yellow"))
        raise typer.Exit(code=1)
    except ModelUnavailableError as e:
        console.print(Panel(str(e), title="[bold red]Modelo Não Disponível[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except ServiceUnavailableError as e:
        console.print(Panel(str(e), title="[bold red]Serviço Indisponível / Conexão[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except LLMError as e:
        console.print(Panel(str(e), title="[bold red]Erro na Integração LLM[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        console.print(f"[bold red]Erro de arquivo ou perfil:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Erro durante a geração:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("compare")
def compare_prompts(
    message: str = typer.Argument(..., help="Mensagem do cliente para caso de teste"),
    profile: str = typer.Option("iniciante", "--profile", "-p", help="ID do perfil de cliente"),
    content_type: str = typer.Option("diagnostico", "--type", "-t", help="Tipo de conteúdo a ser comparado"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Ignora o cache nas execuções"),
    mock: bool = typer.Option(False, "--mock", help="Executa em modo Mock offline"),
):
    """Compara as versões v1 e v2 do prompt utilizando rigorosamente os 3 critérios da rubrica oficial."""
    try:
        generator = get_generator(mock=mock)
        storage = StorageManager()
        evaluator = PromptEvaluator(generator=generator, storage=storage)
        c_type = ContentType(content_type.lower())
        use_cache = not no_cache

        console.print(f"[bold cyan]Executando comparação v1 vs v2 para '{c_type.value}' com perfil '{profile}'...[/bold cyan]\n")
        comparison = evaluator.compare(
            content_type=c_type,
            profile_id=profile,
            customer_message=message,
            use_cache=use_cache,
        )

        # Tabela Comparativa de Notas
        table = Table(title="Resultado da Avaliação pela Rubrica Oficial (1 a 5)", header_style="bold magenta")
        table.add_column("Critério Oficial", style="bold white", width=36)
        table.add_column("Nota v1 (Baseline)", justify="center", style="yellow", width=18)
        table.add_column("Nota v2 (Aprimorado)", justify="center", style="green", width=18)
        table.add_column("Diferença (Delta)", justify="center", style="cyan", width=16)

        criteria_labels = {
            "clareza": "1. Clareza",
            "adequacao_nivel_cliente": "2. Adequação ao nível do cliente",
            "acionabilidade": "3. Acionabilidade",
        }

        for key, label in criteria_labels.items():
            s1 = comparison.v1_scores[key].score
            s2 = comparison.v2_scores[key].score
            delta = f"+{s2 - s1}" if s2 >= s1 else f"{s2 - s1}"
            table.add_row(label, f"{s1}/5", f"{s2}/5", delta)

        table.add_section()
        delta_total = round(comparison.v2_average - comparison.v1_average, 2)
        delta_str = f"+{delta_total}" if delta_total >= 0 else f"{delta_total}"
        table.add_row(
            "[bold]MÉDIA GERAL[/bold]",
            f"[bold]{comparison.v1_average}/5.0[/bold]",
            f"[bold]{comparison.v2_average}/5.0[/bold]",
            f"[bold green]{delta_str}[/bold green]",
        )
        console.print(table)

        # Painel com Vencedor e Justificativas
        winner_color = "green" if comparison.winner == "v2" else "yellow"
        console.print(Panel(
            f"[bold {winner_color}]Vencedor: {comparison.winner.upper()}[/bold {winner_color}]\n\n"
            f"[bold]Resumo:[/bold] {comparison.summary}\n\n"
            f"[bold]Justificativa v2 (Adequação):[/bold] {comparison.v2_scores['adequacao_nivel_cliente'].justification}\n"
            f"[bold]Justificativa v2 (Acionabilidade):[/bold] {comparison.v2_scores['acionabilidade'].justification}",
            title="Veredito da Rubrica Oficial",
            border_style=winner_color,
        ))

    except MissingAPIKeyError as e:
        console.print(Panel(str(e), title="[bold yellow]Configuração de API Necessária[/bold yellow]", border_style="yellow"))
        raise typer.Exit(code=1)
    except AuthenticationError as e:
        console.print(Panel(str(e), title="[bold red]Erro de Autenticação[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except RateLimitError as e:
        console.print(Panel(str(e), title="[bold yellow]Limite Excedido (Rate Limit)[/bold yellow]", border_style="yellow"))
        raise typer.Exit(code=1)
    except ModelUnavailableError as e:
        console.print(Panel(str(e), title="[bold red]Modelo Não Disponível[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except ServiceUnavailableError as e:
        console.print(Panel(str(e), title="[bold red]Serviço Indisponível / Conexão[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except LLMError as e:
        console.print(Panel(str(e), title="[bold red]Erro na Integração LLM[/bold red]", border_style="red"))
        raise typer.Exit(code=1)
    except FileNotFoundError as e:
        console.print(f"[bold red]Erro de arquivo ou perfil:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Erro na comparação:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("history")
def show_history(
    type_: str = typer.Option("runs", "--type", "-t", help="Tipo de histórico: 'runs' ou 'comparisons'"),
    limit: int = typer.Option(10, "--limit", "-l", help="Quantidade máxima de registros exibidos"),
):
    """Exibe o histórico de execuções ou comparações persistidas."""
    storage = StorageManager()

    if type_.lower() == "comparisons":
        items = storage.list_comparisons(limit=limit)
        table = Table(title=f"Histórico de Comparações (Últimas {len(items)})", header_style="bold blue")
        table.add_column("ID", width=10)
        table.add_column("Timestamp", width=22)
        table.add_column("Conteúdo", width=20)
        table.add_column("Perfil", width=12)
        table.add_column("Média v1", justify="center")
        table.add_column("Média v2", justify="center")
        table.add_column("Vencedor", justify="center", style="bold green")

        for c in items:
            table.add_row(c.id[:8], c.timestamp[:19], c.content_type.value, c.profile_id, str(c.v1_average), str(c.v2_average), c.winner)
        console.print(table)
    else:
        items = storage.list_runs(limit=limit)
        table = Table(title=f"Histórico de Execuções (Últimas {len(items)})", header_style="bold blue")
        table.add_column("ID", width=10)
        table.add_column("Timestamp", width=22)
        table.add_column("Conteúdo", width=22)
        table.add_column("Perfil", width=12)
        table.add_column("Versão", justify="center")
        table.add_column("Cache?", justify="center")
        table.add_column("Latência", justify="right")

        for r in items:
            table.add_row(
                r.id[:8],
                r.timestamp[:19],
                r.content_type.value,
                r.profile_id,
                r.prompt_version.value,
                "SIM" if r.cached else "NÃO",
                f"{r.latency_ms}ms",
            )
        console.print(table)


if __name__ == "__main__":
    run()
