"""Motor de avaliação e benchmarking comparativo baseado na rubrica oficial.

A avaliação é determinística e baseada exclusivamente no conteúdo da saída e no perfil
do cliente. O avaliador NÃO recebe a versão do prompt que gerou o texto: v1 e v2 são
pontuadas pelas mesmas regras, de modo que a comparação reflita diferenças reais de conteúdo.
"""

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional, Tuple
import uuid

from src.generator import ContentGenerator
from src.models import (
    ComparisonRecord,
    ContentType,
    CustomerProfile,
    PromptVersion,
    RubricCriterion,
)
from src.storage import StorageManager


# Termos técnicos que prejudicam a compreensão de um cliente leigo
JARGON_TERMS = [
    "dns", "dhcp", "ip", "gateway", "timeout", "token", "tokens", "api", "https", "proxy",
    "firewall", "powershell", "terminal", "traceroute", "ping", "grep", "chmod", "endpoint",
    "oauth", "log", "logs", "flush", "kernel", "driver", "sessão", "cache",
]

# Indicadores de profundidade técnica esperada por um cliente avançado
TECHNICAL_TERMS = [
    "http", "status", "log", "logs", "token", "endpoint", "dns", "tcp", "tls", "ssl", "header",
    "oauth", "api", "curl", "cache", "latência", "timeout", "flag", "porta", "payload",
    "gateway", "variável de ambiente", "causa-raiz", "stack", "trace",
]

# Sugestões básicas que um cliente avançado considera inadequadas
BASIC_SUGGESTIONS = ["reinicie o computador", "reiniciar o computador", "verifique se o cabo", "verificar se o cabo"]

EMPATHY_MARKERS = ["lamento", "entendo", "compreendo", "desculp", "sinto muito", "peço perdão", "imagino"]
BLAME_PHRASES = ["não é nossa culpa", "não é culpa nossa", "a culpa é sua", "você deveria ter", "infelizmente não podemos"]

URGENCY_SIGNALS = ["urgente", "impaciente", "telegráf", "ultra-direta", "direta", "sucint"]
FRUSTRATION_SIGNALS = ["frustrad", "irritad", "desconfiad", "de-escalonamento"]

LIST_ITEM_RE = re.compile(r"^\s*(\d+[.)]|[-*•])\s+", re.MULTILINE)
NUMBERED_ITEM_RE = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)
SECTION_RE = re.compile(r"^\s*(#{1,6}\s+\S|\*\*[^*\n]+\*\*\s*:?\s*$|[^\n]{3,60}:\s*$)", re.MULTILINE)


def _clamp(score: int) -> int:
    return max(1, min(5, score))


def _find_terms(text_lower: str, terms: List[str]) -> List[str]:
    """Retorna os termos presentes no texto, respeitando limites de palavra."""
    found = []
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text_lower):
            found.append(term)
    return found


def _contains_any(text_lower: str, fragments: List[str]) -> List[str]:
    return [f for f in fragments if f in text_lower]


def _avg_sentence_words(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?\n]+", text) if s.strip()]
    if not sentences:
        return 0.0
    return sum(len(s.split()) for s in sentences) / len(sentences)


def _extract_mermaid(text: str) -> Optional[str]:
    match = re.search(r"```mermaid\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else None


class PromptEvaluator:
    """Avaliador e comparador de prompts utilizando estritamente a rubrica oficial de 3 critérios:

    1. Clareza (1-5)
    2. Adequação ao nível do cliente (1-5)
    3. Acionabilidade (1-5)
    """

    OFFICIAL_CRITERIA = ["clareza", "adequacao_nivel_cliente", "acionabilidade"]
    CRITERIA_LABELS = {
        "clareza": "Clareza",
        "adequacao_nivel_cliente": "Adequação ao nível do cliente",
        "acionabilidade": "Acionabilidade",
    }

    def __init__(
        self,
        generator: Optional[ContentGenerator] = None,
        storage: Optional[StorageManager] = None,
    ):
        self.generator = generator or ContentGenerator()
        self.storage = storage or StorageManager()

    # ------------------------------------------------------------------ critérios

    def _score_clareza(self, content_type: ContentType, text: str) -> Tuple[int, str]:
        word_count = len(text.split())
        avg_words = _avg_sentence_words(text)
        has_sections = bool(SECTION_RE.search(text)) or (
            content_type == ContentType.FLUXOGRAMA and _extract_mermaid(text) is not None
        )
        has_list = bool(LIST_ITEM_RE.search(text))

        score = 1
        evidence = []
        if has_sections:
            score += 1
            evidence.append("possui seções/títulos")
        else:
            evidence.append("sem seções ou títulos")
        if has_list:
            score += 1
            evidence.append("usa itens de lista")
        else:
            evidence.append("sem itens de lista")
        if 0 < avg_words <= 25:
            score += 1
            evidence.append(f"frases curtas (média de {avg_words:.0f} palavras)")
        else:
            evidence.append(f"frases longas (média de {avg_words:.0f} palavras)")
        if 25 <= word_count <= 450:
            score += 1
            evidence.append(f"extensão adequada ({word_count} palavras)")
        else:
            evidence.append(f"extensão inadequada ({word_count} palavras)")

        return _clamp(score), "; ".join(evidence).capitalize() + "."

    def _score_adequacao(self, profile: CustomerProfile, text: str) -> Tuple[int, str]:
        text_lower = text.lower()
        word_count = len(text.split())
        profile_style = f"{profile.tone_mood} {profile.communication_preference}".lower()

        score = 3
        evidence = []

        if profile.technical_level == "iniciante":
            jargon = _find_terms(text_lower, JARGON_TERMS)
            if jargon:
                score -= min(len(jargon), 2)
                evidence.append(f"jargões para cliente leigo: {', '.join(jargon[:5])}")
            else:
                score += 1
                evidence.append("vocabulário sem jargões técnicos")
            if 0 < _avg_sentence_words(text) <= 20:
                score += 1
                evidence.append("frases curtas e acessíveis")
        elif profile.technical_level == "avancado":
            technical = _find_terms(text_lower, TECHNICAL_TERMS)
            if len(technical) >= 3:
                score += 2
                evidence.append(f"profundidade técnica ({', '.join(technical[:5])})")
            elif technical:
                score += 1
                evidence.append(f"alguma profundidade técnica ({', '.join(technical)})")
            else:
                score -= 1
                evidence.append("sem termos técnicos para cliente avançado")
            basic = _contains_any(text_lower, BASIC_SUGGESTIONS)
            if basic:
                score -= 1
                evidence.append("contém sugestões básicas vetadas pelo perfil")
        else:
            evidence.append(f"nível técnico '{profile.technical_level}' sem ajuste de vocabulário")

        if _contains_any(profile_style, URGENCY_SIGNALS):
            if word_count <= 150:
                score += 1
                evidence.append(f"resposta breve para cliente com pressa ({word_count} palavras)")
            elif word_count > 300:
                score -= 1
                evidence.append(f"resposta longa para cliente com pressa ({word_count} palavras)")
            if "**" in text:
                score += 1
                evidence.append("ação principal destacada em negrito")

        if _contains_any(profile_style, FRUSTRATION_SIGNALS):
            empathy = _contains_any(text_lower, EMPATHY_MARKERS)
            if empathy:
                score += 1
                evidence.append("valida o sentimento do cliente")
            else:
                score -= 1
                evidence.append("não demonstra empatia com o cliente frustrado")
            if _contains_any(text_lower, BLAME_PHRASES):
                score -= 2
                evidence.append("transfere culpa ao cliente")

        return _clamp(score), "; ".join(evidence).capitalize() + "."

    def _score_acionabilidade(self, content_type: ContentType, text: str) -> Tuple[int, str]:
        text_lower = text.lower()
        score = 1
        evidence = []

        if content_type == ContentType.FLUXOGRAMA:
            mermaid = _extract_mermaid(text)
            if mermaid is not None and re.search(r"\b(flowchart|graph)\b", mermaid, re.IGNORECASE):
                score += 1
                evidence.append("diagrama Mermaid válido")
                body = mermaid
            else:
                evidence.append("sem bloco Mermaid")
                body = text
            edges = len(re.findall(r"-->|->|-- ", body))
            if re.search(r"\{[^}]+\}", body) or re.search(r"\b(sim|não)\b", body.lower()):
                score += 1
                evidence.append("possui pontos de decisão")
            else:
                evidence.append("sem pontos de decisão")
            if edges >= 4:
                score += 1
                evidence.append(f"{edges} transições")
            else:
                evidence.append(f"apenas {edges} transições")
            if _contains_any(body.lower(), ["fim", "resolvido", "escal", "encerr"]):
                score += 1
                evidence.append("possui estado final ou escalonamento")

        elif content_type == ContentType.PERGUNTAS_ESCLARECIMENTO:
            n_questions = text.count("?")
            if 2 <= n_questions <= 6:
                score += 3
            elif n_questions > 6:
                score += 2
            elif n_questions == 1:
                score += 1
            evidence.append(f"{n_questions} perguntas")
            if _contains_any(text_lower, ["por que", "permite", "ajuda a", "como você pode verificar"]):
                score += 1
                evidence.append("explica o motivo ou como obter a informação")

        elif content_type == ContentType.PASSO_A_PASSO:
            n_steps = len(NUMBERED_ITEM_RE.findall(text))
            if n_steps >= 3:
                score += 2
            elif n_steps >= 1:
                score += 1
            evidence.append(f"{n_steps} passos numerados")
            if _contains_any(text_lower, ["confirm", "deu certo", "verifique se", "veja se", "checagem"]):
                score += 1
                evidence.append("inclui verificação de sucesso")
            else:
                evidence.append("sem verificação de sucesso")
            if _contains_any(text_lower, ["se não funcionar", "caso persista", "caso o erro", "escal", "se o problema continuar"]):
                score += 1
                evidence.append("inclui plano de contingência")
            else:
                evidence.append("sem plano de contingência")

        else:  # DIAGNOSTICO
            if _contains_any(text_lower, ["causa", "provável", "motivo", "decorre", "origem"]):
                score += 1
                evidence.append("identifica a causa provável")
            else:
                evidence.append("não identifica causa")
            if _contains_any(text_lower, ["recomenda", "verifique", "reinici", "próximo passo", "renova", "ação"]):
                score += 1
                evidence.append("indica ação recomendada")
            else:
                evidence.append("sem ação recomendada")
            if _contains_any(text_lower, ["gravidade", "impacto", "urgência", "esforço"]):
                score += 1
                evidence.append("avalia gravidade ou impacto")
            if bool(SECTION_RE.search(text)):
                score += 1
                evidence.append("organizado em seções")

        return _clamp(score), "; ".join(evidence).capitalize() + "."

    # ------------------------------------------------------------------ API pública

    def evaluate_output(
        self,
        content_type: ContentType,
        profile: CustomerProfile,
        output_text: str,
    ) -> Dict[str, RubricCriterion]:
        """Aplica a rubrica oficial de 3 critérios ao texto e retorna notas e justificativas.

        As notas dependem apenas do texto, do tipo de conteúdo e do perfil do cliente.
        """
        score_c, just_c = self._score_clareza(content_type, output_text)
        score_a, just_a = self._score_adequacao(profile, output_text)
        score_ac, just_ac = self._score_acionabilidade(content_type, output_text)

        return {
            "clareza": RubricCriterion(name="clareza", score=score_c, justification=just_c),
            "adequacao_nivel_cliente": RubricCriterion(
                name="adequacao_nivel_cliente", score=score_a, justification=just_a
            ),
            "acionabilidade": RubricCriterion(name="acionabilidade", score=score_ac, justification=just_ac),
        }

    def build_summary(
        self,
        scores_v1: Dict[str, RubricCriterion],
        scores_v2: Dict[str, RubricCriterion],
        avg_v1: float,
        avg_v2: float,
    ) -> Tuple[str, str]:
        """Define o vencedor e redige o resumo com melhorias e regressões por critério."""
        improvements, regressions = [], []
        for key in self.OFFICIAL_CRITERIA:
            delta = scores_v2[key].score - scores_v1[key].score
            label = self.CRITERIA_LABELS[key]
            if delta > 0:
                improvements.append(f"{label} (+{delta})")
            elif delta < 0:
                regressions.append(f"{label} ({delta})")

        if avg_v2 > avg_v1:
            winner = "v2"
            head = f"A versão v2 superou a v1 em {round(avg_v2 - avg_v1, 2)} ponto(s) na média da rubrica oficial."
        elif avg_v1 > avg_v2:
            winner = "v1"
            head = f"A versão v1 superou a v2 em {round(avg_v1 - avg_v2, 2)} ponto(s) na média da rubrica oficial."
        else:
            winner = "empate"
            head = "As versões empataram na média da rubrica oficial."

        parts = [head]
        parts.append(f"Melhorias da v2: {', '.join(improvements)}." if improvements else "Nenhuma melhoria da v2 por critério.")
        parts.append(f"Regressões da v2: {', '.join(regressions)}." if regressions else "Nenhuma regressão da v2 por critério.")
        return winner, " ".join(parts)

    def compare(
        self,
        content_type: ContentType,
        profile_id: str,
        customer_message: str,
        use_cache: bool = True,
    ) -> ComparisonRecord:
        """Executa v1 e v2, avalia sob a rubrica oficial de 3 critérios e persiste o relatório."""
        profile = self.generator.load_profile(profile_id)

        rec_v1 = self.generator.generate_single(
            content_type=content_type,
            profile_id=profile_id,
            customer_message=customer_message,
            prompt_version=PromptVersion.V1,
            use_cache=use_cache,
        )
        rec_v2 = self.generator.generate_single(
            content_type=content_type,
            profile_id=profile_id,
            customer_message=customer_message,
            prompt_version=PromptVersion.V2,
            use_cache=use_cache,
        )

        # Mesma rubrica para ambas as saídas: o avaliador não conhece a versão
        scores_v1 = self.evaluate_output(content_type, profile, rec_v1.output_text)
        scores_v2 = self.evaluate_output(content_type, profile, rec_v2.output_text)

        avg_v1 = round(sum(c.score for c in scores_v1.values()) / 3.0, 2)
        avg_v2 = round(sum(c.score for c in scores_v2.values()) / 3.0, 2)
        winner, summary = self.build_summary(scores_v1, scores_v2, avg_v1, avg_v2)

        comparison = ComparisonRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            content_type=content_type,
            profile_id=profile_id,
            customer_message=customer_message,
            v1_output=rec_v1.output_text,
            v2_output=rec_v2.output_text,
            v1_scores=scores_v1,
            v2_scores=scores_v2,
            v1_average=avg_v1,
            v2_average=avg_v2,
            winner=winner,
            summary=summary,
        )

        self.storage.save_comparison(comparison)
        return comparison
