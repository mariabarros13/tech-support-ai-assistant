"""Testes unitários para a rubrica oficial de 3 critérios e comparação de prompts."""

import inspect
import shutil
import tempfile
from pathlib import Path
import pytest

from src.cache_manager import CacheManager
from src.evaluator import PromptEvaluator
from src.generator import ContentGenerator
from src.llm_client import LLMClient
from src.models import ContentType
from src.storage import StorageManager


STRUCTURED_STEPS = (
    "### Plano de Ação\n"
    "1. Desligue o roteador da tomada.\n"
    "2. Aguarde 30 segundos.\n"
    "3. Ligue o roteador novamente.\n"
    "4. Espere as luzes ficarem verdes.\n\n"
    "### Como Confirmar que Deu Certo\n"
    "Abra um site qualquer. Se ele carregar, a internet voltou.\n\n"
    "### Se Não Funcionar\n"
    "Se não funcionar, entre em contato com o suporte e informe a cor da luz."
)

VAGUE_TEXT = "Pode ser algum problema na sua conexão, é difícil dizer, tente ver depois."


@pytest.fixture
def temp_evaluator():
    temp_dir = Path(tempfile.mkdtemp())
    cache = CacheManager(cache_dir=temp_dir / "cache")
    storage = StorageManager(base_storage_dir=temp_dir / "storage")
    llm = LLMClient(mock_mode=True, cache_manager=cache)
    generator = ContentGenerator(llm_client=llm, storage_manager=storage)
    evaluator = PromptEvaluator(generator=generator, storage=storage)

    yield {
        "evaluator": evaluator,
        "storage": storage,
        "generator": generator,
        "temp_dir": temp_dir,
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_rubric_has_exact_three_official_criteria(temp_evaluator):
    """Verifica se a rubrica oficial contém exatamente os três critérios exigidos."""
    evaluator = temp_evaluator["evaluator"]
    generator = temp_evaluator["generator"]

    profile = generator.load_profile("iniciante")
    scores = evaluator.evaluate_output(
        content_type=ContentType.DIAGNOSTICO,
        profile=profile,
        output_text="Exemplo de saída de teste com texto explicativo",
    )

    expected_keys = {"clareza", "adequacao_nivel_cliente", "acionabilidade"}
    assert set(scores.keys()) == expected_keys, f"Esperado exatamente {expected_keys}, obtido {set(scores.keys())}"

    for crit_key, criterion in scores.items():
        assert 1 <= criterion.score <= 5, f"Nota fora do intervalo 1-5 em {crit_key}: {criterion.score}"
        assert len(criterion.justification) > 10, f"Justificativa insuficiente em {crit_key}"


def test_evaluator_is_blind_to_prompt_version(temp_evaluator):
    """O avaliador não pode receber a versão do prompt: notas dependem só do conteúdo."""
    evaluator = temp_evaluator["evaluator"]
    params = inspect.signature(evaluator.evaluate_output).parameters
    assert "is_v2" not in params
    assert set(params) == {"content_type", "profile", "output_text"}

    profile = temp_evaluator["generator"].load_profile("apressado")
    first = evaluator.evaluate_output(ContentType.PASSO_A_PASSO, profile, STRUCTURED_STEPS)
    second = evaluator.evaluate_output(ContentType.PASSO_A_PASSO, profile, STRUCTURED_STEPS)
    assert first == second


def test_rubric_discriminates_by_content(temp_evaluator):
    """Um passo a passo estruturado e verificável deve superar um texto vago em clareza e acionabilidade.

    A adequação ao nível é um critério independente: ambos os textos são livres de jargão,
    então ela não precisa diferir.
    """
    evaluator = temp_evaluator["evaluator"]
    profile = temp_evaluator["generator"].load_profile("iniciante")

    good = evaluator.evaluate_output(ContentType.PASSO_A_PASSO, profile, STRUCTURED_STEPS)
    bad = evaluator.evaluate_output(ContentType.PASSO_A_PASSO, profile, VAGUE_TEXT)

    for key in ("clareza", "acionabilidade"):
        assert good[key].score > bad[key].score, f"{key}: {good[key].score} <= {bad[key].score}"
    assert good["acionabilidade"].score == 5
    assert bad["acionabilidade"].score <= 2


def test_jargon_penalized_for_beginner_but_not_for_advanced(temp_evaluator):
    """Jargão técnico reduz a adequação para iniciante e aumenta para cliente avançado."""
    evaluator = temp_evaluator["evaluator"]
    generator = temp_evaluator["generator"]
    technical_text = (
        "### Causa\nO token OAuth expira antes do refresh; o endpoint retorna HTTP 401 e o log mostra timeout no gateway."
    )

    beginner = evaluator.evaluate_output(ContentType.DIAGNOSTICO, generator.load_profile("iniciante"), technical_text)
    advanced = evaluator.evaluate_output(ContentType.DIAGNOSTICO, generator.load_profile("tecnico"), technical_text)

    assert beginner["adequacao_nivel_cliente"].score < advanced["adequacao_nivel_cliente"].score
    assert "jargões" in beginner["adequacao_nivel_cliente"].justification.lower()


def test_empathy_and_blame_affect_frustrated_profile(temp_evaluator):
    """Para cliente frustrado, empatia eleva e transferência de culpa reduz a adequação."""
    evaluator = temp_evaluator["evaluator"]
    profile = temp_evaluator["generator"].load_profile("irritado")

    empathetic = evaluator.evaluate_output(
        ContentType.DIAGNOSTICO, profile, "Entendo sua frustração e lamento o transtorno. Vamos resolver agora."
    )
    blaming = evaluator.evaluate_output(
        ContentType.DIAGNOSTICO, profile, "Infelizmente não é nossa culpa. Você deveria ter reiniciado antes."
    )
    assert empathetic["adequacao_nivel_cliente"].score > blaming["adequacao_nivel_cliente"].score


def test_summary_reports_regressions(temp_evaluator):
    """O resumo deve apontar regressões quando a v2 piora em algum critério, inclusive declarando v1 vencedora."""
    evaluator = temp_evaluator["evaluator"]
    profile = temp_evaluator["generator"].load_profile("iniciante")

    scores_good = evaluator.evaluate_output(ContentType.PASSO_A_PASSO, profile, STRUCTURED_STEPS)
    scores_bad = evaluator.evaluate_output(ContentType.PASSO_A_PASSO, profile, VAGUE_TEXT)
    avg_good = sum(c.score for c in scores_good.values()) / 3
    avg_bad = sum(c.score for c in scores_bad.values()) / 3

    winner, summary = evaluator.build_summary(scores_good, scores_bad, avg_good, avg_bad)
    assert winner == "v1"
    assert "Regressões da v2" in summary
    assert "Nenhuma regressão" not in summary


def test_comparison_v1_vs_v2_and_persistence(temp_evaluator):
    """Testa benchmarking comparativo entre versões e persistência do relatório."""
    evaluator = temp_evaluator["evaluator"]
    storage = temp_evaluator["storage"]

    comp = evaluator.compare(
        content_type=ContentType.PASSO_A_PASSO,
        profile_id="apressado",
        customer_message="O sistema travou no meio do checkout e não sei se cobrou",
        use_cache=True,
    )

    assert comp.id
    assert len(comp.v1_scores) == 3
    assert len(comp.v2_scores) == 3
    assert 1.0 <= comp.v1_average <= 5.0
    assert 1.0 <= comp.v2_average <= 5.0

    # O vencedor deve ser consistente com as médias calculadas
    if comp.v2_average > comp.v1_average:
        assert comp.winner == "v2"
    elif comp.v1_average > comp.v2_average:
        assert comp.winner == "v1"
    else:
        assert comp.winner == "empate"

    # Verifica persistência da comparação em storage/comparisons/
    saved_comp = storage.get_comparison(comp.id)
    assert saved_comp is not None
    assert saved_comp.id == comp.id
    assert saved_comp.winner == comp.winner
    assert saved_comp.summary == comp.summary
    assert len(saved_comp.v1_scores) == 3
    assert len(saved_comp.v2_scores) == 3
