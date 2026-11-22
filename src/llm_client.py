"""Cliente de integração com API de LLM com suporte a Mock offline, tratamento de erros e Cache."""

import time
from typing import Any, Dict, Optional, Tuple
from src.cache_manager import CacheManager
from src.config import GEMINI_API_KEY, LLM_MODEL, MOCK_MODE, CACHE_DIR


def _transport_error_types() -> Tuple[type, ...]:
    """Coleta as classes de erro de rede/timeout das bibliotecas HTTP que o SDK pode usar.

    O google-genai usa httpx ou httpx2 (e requests em alguns caminhos). As exceções dessas
    bibliotecas não herdam de ConnectionError/TimeoutError nativos, então são listadas aqui
    explicitamente para que a classificação não dependa do texto da mensagem.
    """
    types_found = [ConnectionError, TimeoutError]
    for module_name in ("httpx", "httpx2"):
        try:
            module = __import__(module_name)
            types_found.append(module.TransportError)
        except (ImportError, AttributeError):
            pass
    try:
        import requests

        types_found.extend([requests.exceptions.ConnectionError, requests.exceptions.Timeout])
    except ImportError:
        pass
    try:
        import aiohttp

        types_found.extend([aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError])
    except ImportError:
        pass
    return tuple(types_found)


TRANSPORT_ERRORS = _transport_error_types()

# Códigos HTTP tratados como indisponibilidade temporária do serviço
SERVICE_UNAVAILABLE_CODES = {500, 502, 503, 504}


def _as_int(value: Any) -> int:
    """Converte contagens de tokens do SDK em int, tratando None e valores não numéricos como 0."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def extract_token_usage(usage_metadata: Any) -> Dict[str, Any]:
    """Extrai a contagem de tokens do usage_metadata do Gemini.

    - prompt_tokens: tokens de entrada (prompt_token_count)
    - completion_tokens: tokens da resposta visível (candidates_token_count)
    - thoughts_tokens: tokens de raciocínio interno (thoughts_token_count), cobrados como saída
      nos modelos 2.5 e não incluídos em candidates_token_count
    - total_tokens: total informado pela API (ou a soma, se ausente)
    """
    prompt_tokens = _as_int(getattr(usage_metadata, "prompt_token_count", None))
    completion_tokens = _as_int(getattr(usage_metadata, "candidates_token_count", None))
    thoughts_tokens = _as_int(getattr(usage_metadata, "thoughts_token_count", None))
    total_tokens = _as_int(getattr(usage_metadata, "total_token_count", None))
    if total_tokens == 0:
        total_tokens = prompt_tokens + completion_tokens + thoughts_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "thoughts_tokens": thoughts_tokens,
        "total_tokens": total_tokens,
        "source": "usage_metadata",
    }


def estimate_token_usage(prompt_text: str, output_text: str, source: str) -> Dict[str, Any]:
    """Estimativa aproximada por contagem de palavras (não são tokens reais)."""
    p_tokens = len(prompt_text.split())
    c_tokens = len(output_text.split())
    return {
        "prompt_tokens": p_tokens,
        "completion_tokens": c_tokens,
        "thoughts_tokens": 0,
        "total_tokens": p_tokens + c_tokens,
        "source": source,
    }


class LLMError(Exception):
    """Exceção base para erros de integração com LLM."""
    pass


class MissingAPIKeyError(LLMError):
    """Lançada quando a chave de API não foi fornecida e o modo Mock não foi solicitado."""
    pass


class AuthenticationError(LLMError):
    """Lançada quando a chave de API é inválida ou expirou (HTTP 401/403)."""
    pass


class RateLimitError(LLMError):
    """Lançada quando a quota ou o limite de requisições foi excedido (HTTP 429)."""
    pass


class ModelUnavailableError(LLMError):
    """Lançada quando o modelo solicitado não existe ou não está acessível (HTTP 404)."""
    pass


class ServiceUnavailableError(LLMError):
    """Lançada quando a API do Gemini está indisponível ou há falha de conexão/timeout."""
    pass


class LLMClient:
    """Cliente para execução de inferências com LLM (Google Gemini) e modo Mock."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        mock_mode: Optional[bool] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        self.api_key = api_key if api_key is not None else GEMINI_API_KEY
        self.model_name = model_name or LLM_MODEL
        self.mock_mode = mock_mode if mock_mode is not None else MOCK_MODE
        self.cache = cache_manager or CacheManager(CACHE_DIR)
        self._gemini_client = None
        self.last_token_usage: Dict[str, int] = {}

    def _get_gemini_client(self):
        if self._gemini_client is None:
            from google import genai
            self._gemini_client = genai.Client(api_key=self.api_key)
        return self._gemini_client

    def _classify_error(self, e: Exception) -> LLMError:
        """Converte exceções do SDK/transporte em erros de domínio, pelo tipo e código HTTP."""
        from google.genai import errors as genai_errors

        if isinstance(e, genai_errors.APIError):
            code = e.code if isinstance(e.code, int) else None
            status = str(e.status or "").upper()
            details = str(e.details or "")
            label = f"HTTP {code} {status}".strip() if code else (status or "erro desconhecido")

            # A API do Gemini responde 400 INVALID_ARGUMENT com reason API_KEY_INVALID para chave inválida
            if (
                code in (401, 403)
                or status in ("UNAUTHENTICATED", "PERMISSION_DENIED")
                or "API_KEY_INVALID" in details
            ):
                return AuthenticationError(
                    f"Falha de autenticação com a API do Gemini ({label}): chave inválida ou sem permissão. "
                    "Verifique sua GEMINI_API_KEY no arquivo .env."
                )
            if code == 429 or status == "RESOURCE_EXHAUSTED":
                return RateLimitError(
                    f"Limite de requisições ou quota da API do Gemini excedido ({label}). "
                    "Aguarde alguns instantes ou execute com a flag --mock."
                )
            if code == 404 or status == "NOT_FOUND":
                return ModelUnavailableError(
                    f"O modelo '{self.model_name}' não foi encontrado ou não está disponível para esta conta ({label}). "
                    "Verifique a variável LLM_MODEL no arquivo .env."
                )
            if code in SERVICE_UNAVAILABLE_CODES or isinstance(e, genai_errors.ServerError):
                return ServiceUnavailableError(
                    f"A API do Gemini está temporariamente indisponível ({label}). "
                    "Tente novamente em alguns instantes ou utilize a flag --mock."
                )
            return LLMError(f"A API do Gemini rejeitou a requisição ({label}): {e.message or details}")

        if isinstance(e, TRANSPORT_ERRORS):
            kind = "tempo limite excedido" if "timeout" in type(e).__name__.lower() else "falha de conexão"
            return ServiceUnavailableError(
                f"Não foi possível comunicar com a API do Gemini ({kind}: {type(e).__name__}). "
                "Verifique sua conexão com a internet ou utilize a flag --mock."
            )

        return LLMError(f"Erro na comunicação com a API do Gemini: {type(e).__name__} - {e}")

    def _generate_mock_response(
        self, content_type: str, profile_id: str, customer_message: str, prompt_text: str
    ) -> str:
        """Gera respostas sintéticas estruturadas e plausíveis para testes offline."""
        time.sleep(0.05)  # simula breve latência de rede
        is_v2 = "v2" in prompt_text.lower() or "especialista" in prompt_text.lower()

        if content_type == "diagnostico":
            if is_v2:
                return (
                    "### 1. Resumo do Problema\n"
                    f"Falha de autenticação e comunicação decorrente de instabilidade no serviço relatado em: '{customer_message[:60]}...'.\n\n"
                    "### 2. Causa Provável (Diagnóstico Técnico)\n"
                    "Inconsistência nos tokens de sessão locais ou timeout na resolução de nomes do gateway de autenticação.\n\n"
                    "### 3. Fatores Contribuintes e Sintomas Associados\n"
                    "Cache de credenciais corrompido no cliente ou intermitência na conexão HTTPS com a API central.\n\n"
                    "### 4. Gravidade e Nível de Esforço Estimado\n"
                    "Gravidade: Média. Resolução estimada em menos de 10 minutos com renovação de sessão."
                )
            return (
                f"Diagnóstico básico para {profile_id}: O problema relatado ('{customer_message}') decorre "
                "de uma falha temporária de conexão ou credenciais inválidas. Recomenda-se reiniciar a sessão."
            )

        elif content_type == "passo_a_passo":
            if is_v2:
                return (
                    "### Pré-requisitos / Atenção Inicial\n"
                    "- Certifique-se de salvar qualquer trabalho pendente antes de prosseguir.\n"
                    "- Tenha em mãos seu usuário e senha de acesso.\n\n"
                    "### Plano de Ação Passo a Passo\n"
                    "1. **Encerre a sessão ativa**: Clique no seu perfil no canto superior e selecione 'Sair da conta'.\n"
                    "2. **Limpe os dados temporários**: Acesse as configurações de privacidade do aplicativo e limpe o cache.\n"
                    "3. **Reinicie a conexão**: Desconecte e reconecte sua rede ou aguarde 15 segundos.\n"
                    "4. **Faça um novo login**: Insira novamente suas credenciais e confirme o acesso.\n\n"
                    "### Como Confirmar que Deu Certo (Checagem de Sucesso)\n"
                    "O painel principal deve carregar sem mensagens de erro e com o indicador de status verde ('Conectado').\n\n"
                    "### Próximo Passo se Não Funcionar\n"
                    "Caso o erro persista, reporte o código de erro exibido na tela para nossa equipe de atendimento avançado."
                )
            return (
                "Passo a passo:\n"
                "1. Saia da sua conta.\n"
                "2. Limpe os dados do aplicativo.\n"
                "3. Conecte-se novamente e veja se o erro sumiu."
            )

        elif content_type == "perguntas_esclarecimento":
            if is_v2:
                return (
                    "### Perguntas Prioritárias de Esclarecimento\n"
                    "1. **Qual é o código exato ou mensagem de erro exibida na tela?**\n"
                    "   - *Por que precisamos disso*: Permite identificar o módulo exato que falhou sem suposições.\n"
                    "   - *Como você pode verificar*: Observe a caixa de alerta que surge ao tentar a ação.\n\n"
                    "2. **O problema acontece em outros dispositivos ou apenas neste?**\n"
                    "   - *Por que precisamos disso*: Ajuda a diferenciar uma falha da sua conta de uma instabilidade local do aparelho.\n"
                    "   - *Como você pode verificar*: Tente acessar o mesmo recurso pelo navegador do celular."
                )
            return (
                "Perguntas de esclarecimento:\n"
                "1. Qual é a mensagem de erro que aparece?\n"
                "2. Desde quando o problema começou?\n"
                "3. Você já tentou reiniciar o dispositivo?"
            )

        elif content_type == "fluxograma":
            if is_v2:
                return (
                    "### Diagrama de Fluxo de Atendimento\n"
                    "```mermaid\n"
                    "flowchart TD\n"
                    "    A[\"Início: Relato de Erro\"] --> B{\"Erro persiste após reload?\"}\n"
                    "    B -- Sim --> C[\"Ação: Limpeza de Cache de Sessão\"]\n"
                    "    B -- Não --> D([\"Problema Resolvido\"])\n"
                    "    C --> E{\"Conseguiu autenticar?\"}\n"
                    "    E -- Sim --> D\n"
                    "    E -- Não --> F[\"Escalar para Suporte Nível 2\"]\n"
                    "```\n\n"
                    "### Caminho Crítico e Tomada de Decisão\n"
                    "- **Ramo Principal**: O usuário recarrega ou limpa a sessão e normaliza o serviço.\n"
                    "- **Ramo Alternativo**: Falha contínua após limpeza de cache aciona o escalonamento para Nível 2.\n"
                    "- **Ponto de Escalonamento**: Nó F caso a autenticação continue bloqueada."
                )
            return (
                "Fluxograma:\n"
                "[Início] -> [Checar conexão] -> [Reiniciar] -> [Fim]"
            )

        return f"Resposta genérica para {content_type} ({profile_id}): {customer_message}"

    def generate(
        self,
        content_type: str,
        prompt_text: str,
        profile_id: str,
        customer_message: str,
        use_cache: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, bool, float, Dict[str, Any]]:
        """Gera o conteúdo utilizando cache determinístico, registro de tokens e medição de latência.

        Retorna:
            Tuple[output_text, is_cached, latency_ms, token_usage]
        """
        # 1. Verificação explícita de credencial se não for mock (antes do cache,
        #    para que a ausência de chave nunca seja mascarada por um cache hit)
        if not self.mock_mode:
            if not self.api_key or self.api_key.strip() in ("", "sua_chave_aqui"):
                raise MissingAPIKeyError(
                    "A variável GEMINI_API_KEY não está configurada no seu arquivo .env.\n"
                    "- Para utilizar a API real do Gemini, adicione sua chave ao arquivo .env:\n"
                    "   GEMINI_API_KEY=sua_chave_aqui\n"
                    "- Para executar offline sem consumir cota ou sem chave, utilize a flag --mock."
                )

        cache_key = self.cache.compute_key(
            content_type=content_type,
            prompt_text=prompt_text,
            profile_id=profile_id,
            customer_message=customer_message,
            model_name=self.model_name,
            mock_mode=self.mock_mode,
        )

        # 2. Consulta ao cache se habilitado (ignora entradas de outro modo de execução)
        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                cached_meta = cached_data.get("metadata", {})
                if bool(cached_meta.get("mock_mode", False)) == self.mock_mode:
                    token_usage = cached_meta.get("token_usage", {
                        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
                    })
                    self.last_token_usage = token_usage
                    return cached_data["output_text"], True, 0.5, token_usage

        start_time = time.perf_counter()

        if self.mock_mode:
            output_text = self._generate_mock_response(
                content_type=content_type,
                profile_id=profile_id,
                customer_message=customer_message,
                prompt_text=prompt_text,
            )
            # Metadados sintéticos de tokens proporcionais ao texto
            token_usage = estimate_token_usage(prompt_text, output_text, source="mock_estimate")
        else:
            try:
                client = self._get_gemini_client()
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_text,
                )
            except Exception as e:
                raise self._classify_error(e) from None

            output_text = response.text or ""

            # Registro de tokens via usage_metadata oficial do SDK
            usage_metadata = getattr(response, "usage_metadata", None)
            if usage_metadata:
                token_usage = extract_token_usage(usage_metadata)
            else:
                token_usage = estimate_token_usage(prompt_text, output_text, source="word_estimate")

        latency_ms = (time.perf_counter() - start_time) * 1000
        self.last_token_usage = token_usage

        # 3. Gravação no cache incluindo metadados de tokens
        meta = {
            "model_name": self.model_name,
            "latency_ms": latency_ms,
            "mock_mode": self.mock_mode,
            "token_usage": token_usage,
            **(extra_metadata or {}),
        }
        self.cache.set(cache_key, output_text, metadata=meta)

        return output_text, False, latency_ms, token_usage
