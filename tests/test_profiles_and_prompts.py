"""Testes unitários para validação de perfis e prompts."""

import json
from pathlib import Path
import pytest
from src.models import CustomerProfile, ContentType, PromptVersion

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = PROJECT_ROOT / "profiles"
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def test_customer_profiles_validation():
    """Valida se todos os perfis JSON estão em conformidade com o schema CustomerProfile."""
    profile_files = list(PROFILES_DIR.glob("*.json"))
    assert len(profile_files) >= 3, f"Esperado ao menos 3 perfis, encontrados {len(profile_files)}"
    assert len(profile_files) <= 5, f"Esperado no máximo 5 perfis, encontrados {len(profile_files)}"

    for file_path in profile_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        profile = CustomerProfile(**data)
        assert profile.id, f"Perfil {file_path.name} sem ID"
        assert profile.name, f"Perfil {file_path.name} sem nome"
        assert profile.technical_level in ["iniciante", "intermediario", "avancado"]
        assert len(profile.constraints) > 0, f"Perfil {file_path.name} sem constraints"


def test_prompts_v1_exist_and_load():
    """Valida se todos os templates v1 existem e contêm os placeholders básicos."""
    for content_type in ContentType:
        v1_path = PROMPTS_DIR / content_type.value / "v1.txt"
        assert v1_path.exists(), f"Template v1 não encontrado para {content_type.value}"
        content = v1_path.read_text(encoding="utf-8")
        assert "{customer_message}" in content, f"Placeholder {{customer_message}} ausente em {v1_path}"
        assert "{profile_name}" in content, f"Placeholder {{profile_name}} ausente em {v1_path}"


def test_prompts_v2_exist_and_load():
    """Valida se todos os templates v2 contêm tags de engenharia de prompt avançada."""
    required_tags = [
        "{customer_message}",
        "{profile_name}",
        "{technical_level}",
        "{tone_mood}",
        "{communication_preference}",
        "{guidance}",
        "{constraints}",
    ]
    for content_type in ContentType:
        v2_path = PROMPTS_DIR / content_type.value / "v2.txt"
        assert v2_path.exists(), f"Template v2 não encontrado para {content_type.value}"
        content = v2_path.read_text(encoding="utf-8")
        for tag in required_tags:
            assert tag in content, f"Tag avançada {tag} ausente em {v2_path}"

    # Verificação específica de Mermaid no fluxograma v2
    fluxograma_v2 = (PROMPTS_DIR / ContentType.FLUXOGRAMA.value / "v2.txt").read_text(encoding="utf-8")
    assert "mermaid" in fluxograma_v2.lower()
    assert "flowchart td" in fluxograma_v2.lower()
