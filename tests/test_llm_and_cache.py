"""Testes unitários para validação do cliente LLM, cache determinístico, erros de API e tokens."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from google.genai import errors
from src.cache_manager import CacheManager
from src.llm_client import (
    AuthenticationError,
    LLMClient,
    LLMError,
    MissingAPIKeyError,
    ModelUnavailableError,
    RateLimitError,
    ServiceUnavailableError,
)


@pytest.fixture
def temp_cache():
    temp_dir = Path(tempfile.mkdtemp())
    cache = CacheManager(cache_dir=temp_dir)
    yield cache
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_cache_set_get_and_clear(temp_cache):
    """Testa armazenamento, recuperação e limpeza de cache."""
    key = temp_cache.compute_key(
        content_type="diagnostico",
        prompt_text="Prompt teste",
        profile_id="iniciante",
        customer_message="Não consigo logar",
        model_name="gemini-3.5-flash",
    )

    # Cache miss inicial
    assert temp_cache.get(key) is None

    # Gravação no cache
    temp_cache.set(key, "Diagnóstico gerado com sucesso", {"tokens": 100})

    # Cache hit
    cached_record = temp_cache.get(key)
    assert cached_record is not None
    assert cached_record["output_text"] == "Diagnóstico gerado com sucesso"
    assert cached_record["metadata"]["tokens"] == 100

    # Limpeza
    removed = temp_cache.clear()
    assert removed == 1
    assert temp_cache.get(key) is None


def test_llm_client_mock_mode_and_caching(temp_cache):
    """Testa LLMClient com mock mode, registro de tokens e verificação de cache determinístico."""
    client = LLMClient(mock_mode=True, cache_manager=temp_cache)

    content_type = "passo_a_passo"
    prompt_text = "Prompt teste v2 Especialista"
    profile_id = "apressado"
    customer_msg = "Minha tela ficou congelada na inicialização"

    # 1. Primeira chamada -> Cache Miss com tokens registrados
    out1, cached1, lat1, tokens1 = client.generate(
        content_type=content_type,
        prompt_text=prompt_text,
        profile_id=profile_id,
        customer_message=customer_msg,
        use_cache=True,
    )
    assert cached1 is False
    assert len(out1) > 20
    assert lat1 > 0
    assert "total_tokens" in tokens1
    assert tokens1["total_tokens"] > 0

    # 2. Segunda chamada idêntica -> Cache Hit
    out2, cached2, lat2, tokens2 = client.generate(
        content_type=content_type,
        prompt_text=prompt_text,
        profile_id=profile_id,
        customer_message=customer_msg,
        use_cache=True,
    )
    assert cached2 is True
    assert out2 == out1
    assert lat2 <= 1.0  # tempo instantâneo de cache
    assert tokens2 == tokens1

    # 3. Terceira chamada com bypass de cache (use_cache=False) -> Nova execução
    out3, cached3, lat3, tokens3 = client.generate(
        content_type=content_type,
        prompt_text=prompt_text,
        profile_id=profile_id,
        customer_message=customer_msg,
        use_cache=False,
    )
    assert cached3 is False
    assert len(out3) > 20


def test_llm_client_missing_api_key_raises_error(temp_cache):
    """Testa se a ausência de chave de API lança MissingAPIKeyError quando mock=False."""
    client = LLMClient(api_key="", mock_mode=False, cache_manager=temp_cache)

    with pytest.raises(MissingAPIKeyError) as exc_info:
        client.generate(
            content_type="diagnostico",
            prompt_text="Prompt teste",
            profile_id="iniciante",
            customer_message="Erro de login",
            use_cache=False,
        )

    assert "GEMINI_API_KEY" in str(exc_info.value)
    assert "--mock" in str(exc_info.value)


def test_llm_client_explicit_mock_activation(temp_cache):
    """Testa se a ativação explícita de mock_mode funciona sem necessidade de chave de API."""
    client = LLMClient(api_key="", mock_mode=True, cache_manager=temp_cache)
    out, cached, lat, tokens = client.generate(
        content_type="diagnostico",
        prompt_text="Prompt teste",
        profile_id="iniciante",
        customer_message="Erro de login",
        use_cache=False,
    )
    assert out
    assert cached is False
    assert tokens["total_tokens"] > 0


def test_mock_cache_is_not_served_to_real_mode(temp_cache, monkeypatch):
    """Garante que uma resposta gerada em modo Mock não é devolvida como cache hit a uma execução real."""
    params = dict(
        content_type="diagnostico",
        prompt_text="Prompt teste isolamento",
        profile_id="iniciante",
        customer_message="Erro de login",
        use_cache=True,
    )
    mock_client = LLMClient(api_key="", mock_mode=True, cache_manager=temp_cache)
    mock_out, _, _, _ = mock_client.generate(**params)

    # Sem chave, a execução real deve falhar mesmo com o cache Mock populado
    real_without_key = LLMClient(api_key="", mock_mode=False, cache_manager=temp_cache)
    with pytest.raises(MissingAPIKeyError):
        real_without_key.generate(**params)

    # Com chave, a execução real deve chamar a API em vez de reutilizar a saída Mock
    real_client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache)
    mock_response = MagicMock()
    mock_response.text = "Resposta real"
    mock_response.usage_metadata = None
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(real_client, "_get_gemini_client", lambda: mock_genai_client)

    out, cached, _, _ = real_client.generate(**params)
    assert cached is False
    assert out == "Resposta real" != mock_out
    mock_genai_client.models.generate_content.assert_called_once()


def test_llm_client_authentication_error(temp_cache, monkeypatch):
    """Testa tratamento de chave de API inválida (401/403)."""
    client = LLMClient(api_key="chave_invalida_teste", mock_mode=False, cache_manager=temp_cache)

    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.side_effect = errors.APIError(401, {"error": "API_KEY_INVALID"})
    monkeypatch.setattr(client, "_get_gemini_client", lambda: mock_genai_client)

    with pytest.raises(AuthenticationError) as exc_info:
        client.generate(
            content_type="diagnostico",
            prompt_text="Prompt teste",
            profile_id="iniciante",
            customer_message="Teste auth",
            use_cache=False,
        )

    assert "autenticação" in str(exc_info.value).lower()


def test_llm_client_rate_limit_error(temp_cache, monkeypatch):
    """Testa tratamento de limite de quota ou taxa excedida (HTTP 429)."""
    client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache)

    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.side_effect = errors.APIError(429, {"error": "RESOURCE_EXHAUSTED"})
    monkeypatch.setattr(client, "_get_gemini_client", lambda: mock_genai_client)

    with pytest.raises(RateLimitError) as exc_info:
        client.generate(
            content_type="diagnostico",
            prompt_text="Prompt teste",
            profile_id="iniciante",
            customer_message="Teste quota",
            use_cache=False,
        )

    assert "limite" in str(exc_info.value).lower() or "429" in str(exc_info.value)


def test_llm_client_connection_error(temp_cache, monkeypatch):
    """Testa tratamento de falhas de conexão ou timeout de rede."""
    client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache)

    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.side_effect = ConnectionError("Connection refused by remote host")
    monkeypatch.setattr(client, "_get_gemini_client", lambda: mock_genai_client)

    with pytest.raises(ServiceUnavailableError) as exc_info:
        client.generate(
            content_type="diagnostico",
            prompt_text="Prompt teste",
            profile_id="iniciante",
            customer_message="Teste rede",
            use_cache=False,
        )

    assert "conexão" in str(exc_info.value).lower() or "indisponível" in str(exc_info.value).lower()


def test_llm_client_usage_metadata_token_recording(temp_cache, monkeypatch):
    """Testa se os tokens de usage_metadata do Gemini são devidamente capturados."""
    client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache)

    mock_response = MagicMock()
    mock_response.text = "Resposta simulada da API real"
    mock_response.usage_metadata.prompt_token_count = 145
    mock_response.usage_metadata.candidates_token_count = 80
    mock_response.usage_metadata.total_token_count = 225

    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(client, "_get_gemini_client", lambda: mock_genai_client)

    out, cached, lat, tokens = client.generate(
        content_type="diagnostico",
        prompt_text="Prompt teste com contagem de tokens",
        profile_id="iniciante",
        customer_message="Teste tokens",
        use_cache=False,
    )

    assert out == "Resposta simulada da API real"
    assert tokens["prompt_tokens"] == 145
    assert tokens["completion_tokens"] == 80
    assert tokens["total_tokens"] == 225
    # Campo não informado pela API deve virar 0 (e não um objeto não serializável)
    assert tokens["thoughts_tokens"] == 0
    assert tokens["source"] == "usage_metadata"


def _client_raising(temp_cache, monkeypatch, exc):
    """Cria um LLMClient real cujo SDK lança a exceção informada."""
    client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache)
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.side_effect = exc
    monkeypatch.setattr(client, "_get_gemini_client", lambda: mock_genai_client)
    return client


def _call(client):
    return client.generate(
        content_type="diagnostico",
        prompt_text="Prompt teste",
        profile_id="iniciante",
        customer_message="Teste erro",
        use_cache=False,
    )


def test_llm_client_invalid_model_404(temp_cache, monkeypatch):
    """Modelo inexistente (HTTP 404 NOT_FOUND) deve gerar ModelUnavailableError citando o modelo."""
    exc = errors.ClientError(
        404,
        {"error": {"code": 404, "message": "models/gemini-inexistente is not found", "status": "NOT_FOUND"}},
    )
    client = _client_raising(temp_cache, monkeypatch, exc)
    client.model_name = "gemini-inexistente"

    with pytest.raises(ModelUnavailableError) as exc_info:
        _call(client)
    assert "gemini-inexistente" in str(exc_info.value)
    assert "404" in str(exc_info.value)


@pytest.mark.parametrize("code,status", [(503, "UNAVAILABLE"), (500, "INTERNAL"), (504, "DEADLINE_EXCEEDED")])
def test_llm_client_service_unavailable_5xx(temp_cache, monkeypatch, code, status):
    """Erros 5xx do servidor (ex.: 503 sobrecarga) devem gerar ServiceUnavailableError."""
    exc = errors.ServerError(code, {"error": {"code": code, "message": "The model is overloaded.", "status": status}})
    client = _client_raising(temp_cache, monkeypatch, exc)

    with pytest.raises(ServiceUnavailableError) as exc_info:
        _call(client)
    assert str(code) in str(exc_info.value)
    assert "indisponível" in str(exc_info.value).lower()


def test_llm_client_invalid_key_400_api_key_invalid(temp_cache, monkeypatch):
    """A API do Gemini responde 400 INVALID_ARGUMENT com reason API_KEY_INVALID para chave inválida."""
    exc = errors.ClientError(
        400,
        {
            "error": {
                "code": 400,
                "message": "API key not valid. Please pass a valid API key.",
                "status": "INVALID_ARGUMENT",
                "details": [{"reason": "API_KEY_INVALID"}],
            }
        },
    )
    client = _client_raising(temp_cache, monkeypatch, exc)
    with pytest.raises(AuthenticationError):
        _call(client)


def test_llm_client_other_client_error_is_generic(temp_cache, monkeypatch):
    """Outros erros 4xx (ex.: 400 sem relação com a chave) não devem ser confundidos com autenticação."""
    exc = errors.ClientError(
        400, {"error": {"code": 400, "message": "Request contains an invalid argument.", "status": "INVALID_ARGUMENT"}}
    )
    client = _client_raising(temp_cache, monkeypatch, exc)
    with pytest.raises(LLMError) as exc_info:
        _call(client)
    assert type(exc_info.value) is LLMError
    assert "400" in str(exc_info.value)


@pytest.mark.parametrize("module_name", ["httpx", "httpx2"])
def test_llm_client_transport_errors_from_sdk(temp_cache, monkeypatch, module_name):
    """Erros de rede/timeout da biblioteca HTTP do SDK (sem herdar de ConnectionError) são classificados pelo tipo."""
    http = pytest.importorskip(module_name)

    for exc, expected_kind in [
        (http.ConnectError("[Errno 11001] getaddrinfo failed"), "conexão"),
        (http.ReadTimeout("The read operation timed out"), "tempo limite"),
    ]:
        client = _client_raising(temp_cache, monkeypatch, exc)
        with pytest.raises(ServiceUnavailableError) as exc_info:
            _call(client)
        assert expected_kind in str(exc_info.value).lower()


def test_llm_client_records_thoughts_tokens(temp_cache, monkeypatch):
    """Tokens de raciocínio (thoughts_token_count) dos modelos com raciocínio devem ser registrados e persistidos no cache."""
    from google.genai import types

    client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache)
    response = MagicMock()
    response.text = "Resposta com raciocínio"
    response.usage_metadata = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=100,
        candidates_token_count=40,
        thoughts_token_count=260,
        total_token_count=400,
    )
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = response
    monkeypatch.setattr(client, "_get_gemini_client", lambda: mock_genai_client)

    params = dict(
        content_type="diagnostico",
        prompt_text="Prompt tokens",
        profile_id="iniciante",
        customer_message="Teste raciocínio",
        use_cache=True,
    )
    _, cached, _, tokens = client.generate(**params)
    assert cached is False
    assert tokens == {
        "prompt_tokens": 100,
        "completion_tokens": 40,
        "thoughts_tokens": 260,
        "total_tokens": 400,
        "source": "usage_metadata",
    }

    # O cache devolve exatamente a mesma contagem
    _, cached2, _, tokens2 = client.generate(**params)
    assert cached2 is True
    assert tokens2 == tokens


def test_llm_client_marks_estimated_tokens_without_usage_metadata(temp_cache, monkeypatch):
    """Sem usage_metadata, a contagem deve ser identificada como estimativa por palavras."""
    client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache)
    response = MagicMock()
    response.text = "um dois tres"
    response.usage_metadata = None
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = response
    monkeypatch.setattr(client, "_get_gemini_client", lambda: mock_genai_client)

    _, _, _, tokens = _call(client)
    assert tokens["source"] == "word_estimate"
    assert tokens["completion_tokens"] == 3


@pytest.mark.parametrize(
    "raw,expected",
    [(None, 60.0), ("", 60.0), ("30", 30.0), ("2.5", 2.5), ("abc", 60.0), ("0", 60.0), ("-5", 60.0)],
)
def test_parse_timeout_seconds(raw, expected):
    """LLM_TIMEOUT_SECONDS inválido, vazio ou não positivo deve cair no padrão de 60s."""
    from src.config import parse_timeout_seconds

    assert parse_timeout_seconds(raw) == expected


def test_llm_client_rejects_non_positive_timeout(temp_cache):
    with pytest.raises(ValueError):
        LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache, timeout_seconds=0)


def test_llm_client_passes_timeout_to_sdk_in_milliseconds(temp_cache, monkeypatch):
    """O cliente Gemini deve ser criado com HttpOptions.timeout em milissegundos."""
    import google.genai

    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(google.genai, "Client", FakeClient)
    client = LLMClient(api_key="chave_valida", mock_mode=False, cache_manager=temp_cache, timeout_seconds=12.5)
    client._get_gemini_client()

    assert captured["api_key"] == "chave_valida"
    assert captured["http_options"].timeout == 12500


def test_llm_client_timeout_is_enforced_against_hanging_server(temp_cache, monkeypatch):
    """Integração local: com um servidor que aceita a conexão e nunca responde, a chamada
    deve falhar por timeout (ServiceUnavailableError) em vez de travar indefinidamente."""
    import socket
    import threading
    import time as _time

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    accepted = []
    stop = threading.Event()

    def accept_and_hang():
        server.settimeout(10)
        try:
            conn, _ = server.accept()
            accepted.append(conn)
            stop.wait(10)
        except OSError:
            pass

    thread = threading.Thread(target=accept_and_hang, daemon=True)
    thread.start()
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", f"http://127.0.0.1:{port}")

    client = LLMClient(api_key="chave_teste", mock_mode=False, cache_manager=temp_cache, timeout_seconds=1)
    start = _time.perf_counter()
    try:
        with pytest.raises(ServiceUnavailableError) as exc_info:
            _call(client)
    finally:
        stop.set()
        for conn in accepted:
            conn.close()
        server.close()
    elapsed = _time.perf_counter() - start

    assert "tempo limite de 1s" in str(exc_info.value)
    assert elapsed < 8, f"A chamada levou {elapsed:.1f}s; o timeout não foi aplicado"
