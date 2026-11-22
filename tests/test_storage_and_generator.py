"""Testes unitários para persistência e orquestração de geração."""

import shutil
import tempfile
from pathlib import Path
import pytest

from src.cache_manager import CacheManager
from src.generator import ContentGenerator
from src.llm_client import LLMClient
from src.models import ContentType, PromptVersion
from src.storage import StorageManager


@pytest.fixture
def temp_environment():
    temp_dir = Path(tempfile.mkdtemp())
    cache_dir = temp_dir / "cache"
    storage_dir = temp_dir / "storage"

    cache = CacheManager(cache_dir=cache_dir)
    storage = StorageManager(base_storage_dir=storage_dir)
    llm = LLMClient(mock_mode=True, cache_manager=cache)
    generator = ContentGenerator(llm_client=llm, storage_manager=storage)

    yield {
        "temp_dir": temp_dir,
        "cache": cache,
        "storage": storage,
        "generator": generator,
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_generator_single_content(temp_environment):
    """Testa geração de um único conteúdo com persistência e cache."""
    generator = temp_environment["generator"]
    storage = temp_environment["storage"]

    record = generator.generate_single(
        content_type=ContentType.DIAGNOSTICO,
        profile_id="iniciante",
        customer_message="Meu aplicativo não abre após atualizar o celular",
        prompt_version=PromptVersion.V2,
        use_cache=True,
    )

    assert record.id
    assert record.content_type == ContentType.DIAGNOSTICO
    assert record.profile_id == "iniciante"
    assert "Resumo do Problema" in record.output_text

    # Verifica se foi persistido em disco
    saved_run = storage.get_run(record.id)
    assert saved_run is not None
    assert saved_run.id == record.id
    assert saved_run.output_text == record.output_text


def test_generator_all_contents(temp_environment):
    """Testa geração em lote de todos os 4 conteúdos para o chamado."""
    generator = temp_environment["generator"]
    storage = temp_environment["storage"]

    results = generator.generate_all(
        profile_id="tecnico",
        customer_message="O serviço retorna HTTP 504 Gateway Timeout esporadicamente",
        prompt_version=PromptVersion.V2,
        use_cache=True,
    )

    assert len(results) == 4
    for content_type in ContentType:
        assert content_type in results
        rec = results[content_type]
        assert rec.profile_id == "tecnico"
        assert rec.output_text
        # Verifica persistência
        assert storage.get_run(rec.id) is not None

    # Verifica list_runs
    all_runs = storage.list_runs()
    assert len(all_runs) >= 4
