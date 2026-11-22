"""Modelos de dados (Pydantic schemas) para perfis, prompts e execuções."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContentType(str, Enum):
    DIAGNOSTICO = "diagnostico"
    PASSO_A_PASSO = "passo_a_passo"
    PERGUNTAS_ESCLARECIMENTO = "perguntas_esclarecimento"
    FLUXOGRAMA = "fluxograma"


class PromptVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"


class CustomerProfile(BaseModel):
    id: str = Field(..., description="Identificador único da persona (ex: iniciante)")
    name: str = Field(..., description="Nome descritivo da persona")
    technical_level: str = Field(..., description="Nível técnico: iniciante, intermediario, avancado")
    tone_mood: str = Field(..., description="Estado emocional da persona")
    communication_preference: str = Field(..., description="Estilo de comunicação esperado")
    context: str = Field(..., description="Cenário ou histórico de atendimento")
    guidance: str = Field(..., description="Diretrizes específicas de atendimento")
    constraints: List[str] = Field(default_factory=list, description="Lista de restrições obrigatórias")


class ExecutionRecord(BaseModel):
    id: str = Field(..., description="UUID ou ID único da execução")
    timestamp: str = Field(..., description="Timestamp ISO-8601 da execução")
    content_type: ContentType = Field(..., description="Tipo de conteúdo gerado")
    prompt_version: PromptVersion = Field(..., description="Versão de prompt utilizada")
    profile_id: str = Field(..., description="ID do perfil de cliente")
    customer_message: str = Field(..., description="Mensagem de entrada do cliente")
    output_text: str = Field(..., description="Texto gerado pelo modelo")
    cached: bool = Field(default=False, description="Indica se a resposta veio do cache")
    latency_ms: float = Field(default=0.0, description="Tempo de resposta em milissegundos")
    model_name: str = Field(default="gemini-3.5-flash", description="Modelo LLM utilizado")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")


class RubricCriterion(BaseModel):
    name: str = Field(..., description="Nome do critério oficial (Clareza, Adequação ao nível do cliente, Acionabilidade)")
    score: int = Field(..., ge=1, le=5, description="Nota de 1 a 5")
    justification: str = Field(..., description="Justificativa da nota atribuída")


class ComparisonRecord(BaseModel):
    id: str = Field(..., description="Identificador único da comparação")
    timestamp: str = Field(..., description="Timestamp ISO-8601")
    content_type: ContentType
    profile_id: str
    customer_message: str
    v1_output: str
    v2_output: str
    v1_scores: Dict[str, RubricCriterion]
    v2_scores: Dict[str, RubricCriterion]
    v1_average: float
    v2_average: float
    winner: str = Field(..., description="Versão vencedora (v1, v2 ou empate)")
    summary: str = Field(..., description="Resumo analítico comparativo")
