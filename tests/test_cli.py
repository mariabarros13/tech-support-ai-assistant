"""Testes para a interface de linha de comando (CLI)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner
from src.cli import app

runner = CliRunner()
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Redireciona cache e persistência para um diretório temporário e remove a chave de API.

    Evita que os testes gravem em storage/ do projeto e que o resultado dependa
    de cache acumulado ou de uma GEMINI_API_KEY presente no ambiente.
    """
    monkeypatch.setattr("src.llm_client.CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr("src.storage.STORAGE_DIR", tmp_path / "storage")
    monkeypatch.setattr("src.llm_client.GEMINI_API_KEY", "")


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Assistente de Atendimento ao Cliente" in result.stdout
    assert "profiles" in result.stdout
    assert "generate" in result.stdout
    assert "compare" in result.stdout
    assert "history" in result.stdout


def test_cli_profiles():
    result = runner.invoke(app, ["profiles"])
    assert result.exit_code == 0
    assert "iniciante" in result.stdout
    assert "apressado" in result.stdout
    assert "tecnico" in result.stdout
    assert "irritado" in result.stdout


def test_cli_generate_mock():
    result = runner.invoke(
        app,
        ["generate", "Minha tela ficou azul", "--profile", "iniciante", "--type", "diagnostico", "--mock"],
    )
    assert result.exit_code == 0
    assert "DIAGNOSTICO" in result.stdout
    assert "Resumo do Problema" in result.stdout


def test_cli_compare_mock():
    result = runner.invoke(
        app,
        ["compare", "Meu aplicativo fechou sozinho", "--profile", "apressado", "--type", "passo_a_passo", "--mock"],
    )
    assert result.exit_code == 0
    assert "1. Clareza" in result.stdout
    assert "Adequação" in result.stdout
    assert "3. Acionabilidade" in result.stdout
    assert "Vencedor" in result.stdout


def test_cli_history():
    result = runner.invoke(app, ["history", "--limit", "5"])
    assert result.exit_code == 0
    assert "Histórico" in result.stdout


def test_cli_missing_api_key_warning():
    """Valida se a CLI alerta o usuário e sugere .env ou --mock quando a chave está ausente."""
    result = runner.invoke(
        app,
        ["generate", "Minha tela ficou azul", "--profile", "iniciante", "--type", "diagnostico"],
    )
    assert result.exit_code == 1
    assert "GEMINI_API_KEY" in result.stdout
    assert "--mock" in result.stdout


def _run_main_with_legacy_encoding(tmp_path, *args):
    """Executa main.py em subprocesso com a saída forçada para cp1252 (como num pipe no Windows)."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8",)}
    env.update(
        PYTHONIOENCODING="cp1252",
        PYTHONDONTWRITEBYTECODE="1",
        GEMINI_API_KEY="",
        MOCK_MODE="false",
        STORAGE_DIR=str(tmp_path / "storage"),
        CACHE_DIR=str(tmp_path / "storage" / "cache"),
    )
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        timeout=120,
    )


def test_cli_output_with_emoji_on_legacy_encoding(tmp_path):
    """Mensagens com emoji não podem derrubar a CLI quando o terminal usa codificação não UTF-8."""
    result = _run_main_with_legacy_encoding(
        tmp_path, "generate", "Minha tela travou 😡", "--profile", "iniciante", "--type", "diagnostico", "--mock"
    )
    stdout = result.stdout.decode("utf-8")
    stderr = result.stderr.decode("utf-8", errors="replace")
    assert result.returncode == 0, stderr
    assert "Traceback" not in stdout + stderr
    assert "😡" in stdout
    assert "Resumo do Problema" in stdout


def test_cli_missing_key_message_on_legacy_encoding(tmp_path):
    """O aviso de chave ausente deve ser exibido por completo, sem traceback, em terminais não UTF-8."""
    result = _run_main_with_legacy_encoding(tmp_path, "generate", "Erro", "--profile", "iniciante", "--type", "diagnostico")
    stdout = result.stdout.decode("utf-8")
    assert result.returncode == 1
    assert "Traceback" not in stdout + result.stderr.decode("utf-8", errors="replace")
    assert "GEMINI_API_KEY" in stdout
    assert "--mock" in stdout

