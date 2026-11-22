"""Testes de segurança e verificação de regras do .gitignore."""

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True)


@pytest.fixture
def git_repo():
    """Exige git disponível e o projeto dentro de um repositório; caso contrário, pula o teste."""
    if shutil.which("git") is None:
        pytest.skip("git não está disponível")
    if _git("rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        pytest.skip("projeto não está em um repositório git")


def test_gitignore_exists_and_protects_secrets():
    """Valida se o arquivo .gitignore existe e protege adequadamente arquivos sensíveis."""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    assert gitignore_path.exists(), "Arquivo .gitignore não encontrado na raiz do projeto"

    content = gitignore_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    # Verificação de arquivos e pastas sensíveis
    assert ".env" in lines, ".env deve estar explicitamente bloqueado no .gitignore"
    assert "!.env.example" in lines, ".env.example deve ser preservado pelo .gitignore"
    assert lines.index("!.env.example") > lines.index(".env.*"), "!.env.example deve vir depois de .env.*"
    assert ".streamlit/secrets.toml" in lines, "Segredos do Streamlit devem estar ignorados"
    assert any("__pycache__" in line for line in lines), "__pycache__/ deve estar ignorado"
    assert any(".pytest_cache" in line for line in lines), ".pytest_cache/ deve estar ignorado"
    assert any("storage/cache" in line for line in lines), "storage/cache/ deve estar ignorado"


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.local",
        ".env.production",
        ".streamlit/secrets.toml",
        "storage/cache/abc.json",
        "storage/runs/abc.json",
        "storage/comparisons/abc.json",
        "src/__pycache__/x.pyc",
        ".vscode/settings.json",
        "app.log",
    ],
)
def test_sensitive_and_generated_paths_are_ignored(git_repo, path):
    """Confere com o próprio git que credenciais e dados gerados são ignorados."""
    result = _git("check-ignore", "-q", "--no-index", path)
    assert result.returncode == 0, f"{path} deveria ser ignorado pelo .gitignore"


@pytest.mark.parametrize(
    "path",
    [".env.example", "samples/sample_comparison.json", "src/llm_client.py", "profiles/iniciante.json", "README.md"],
)
def test_deliverables_are_not_ignored(git_repo, path):
    """Arquivos de entrega não podem ser ignorados por engano."""
    result = _git("check-ignore", "-q", "--no-index", path)
    assert result.returncode == 1, f"{path} não deveria ser ignorado pelo .gitignore"


def test_env_example_has_only_placeholders():
    """Confirma que .env.example contém apenas o placeholder, sem chave real."""
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "GEMINI_API_KEY=sua_chave_aqui" in env_example
    assert "AIza" not in env_example  # prefixo padrão de chaves Google reais


def test_no_env_file_is_tracked(git_repo):
    """Um .env local (necessário para usar a API real) pode existir, mas nunca pode ser rastreado pelo git."""
    tracked = _git("ls-files", "--", ".env", ".env.*", "*/.env").stdout.split()
    assert [p for p in tracked if p != ".env.example"] == [], f"Arquivos .env rastreados: {tracked}"
