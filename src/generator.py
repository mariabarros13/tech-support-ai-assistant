"""Orquestrador de geração de conteúdos de atendimento ao cliente."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from src.config import PROFILES_DIR, PROMPTS_DIR
from src.llm_client import LLMClient
from src.models import ContentType, CustomerProfile, ExecutionRecord, PromptVersion
from src.storage import StorageManager


class ContentGenerator:
    """Carrega perfis e prompts, orquestra chamadas LLM com cache e persiste execuções."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        storage_manager: Optional[StorageManager] = None,
        profiles_dir: Optional[Path] = None,
        prompts_dir: Optional[Path] = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self.storage = storage_manager or StorageManager()
        self.profiles_dir = Path(profiles_dir) if profiles_dir else PROFILES_DIR
        self.prompts_dir = Path(prompts_dir) if prompts_dir else PROMPTS_DIR

    def get_available_profiles(self) -> List[CustomerProfile]:
        """Retorna todos os perfis disponíveis no diretório de perfis."""
        profiles = []
        for file_path in self.profiles_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                profiles.append(CustomerProfile(**data))
            except Exception:
                continue
        return profiles

    def load_profile(self, profile_id: str) -> CustomerProfile:
        """Carrega um perfil específico pelo seu identificador."""
        file_path = self.profiles_dir / f"{profile_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Perfil de cliente '{profile_id}' não encontrado em {self.profiles_dir}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CustomerProfile(**data)

    def load_prompt_template(self, content_type: ContentType, version: PromptVersion) -> str:
        """Lê o arquivo de template de prompt."""
        file_path = self.prompts_dir / content_type.value / f"{version.value}.txt"
        if not file_path.exists():
            raise FileNotFoundError(f"Template de prompt não encontrado: {file_path}")
        return file_path.read_text(encoding="utf-8")

    def build_prompt(
        self,
        template: str,
        profile: CustomerProfile,
        customer_message: str,
    ) -> str:
        """Preenche o template de prompt com dados do perfil e a mensagem do cliente."""
        constraints_formatted = "\n".join(f"- {c}" for c in profile.constraints)
        return (
            template.replace("{customer_message}", customer_message)
            .replace("{profile_name}", profile.name)
            .replace("{technical_level}", profile.technical_level)
            .replace("{tone_mood}", profile.tone_mood)
            .replace("{communication_preference}", profile.communication_preference)
            .replace("{guidance}", profile.guidance)
            .replace("{constraints}", constraints_formatted)
        )

    def generate_single(
        self,
        content_type: ContentType,
        profile_id: str,
        customer_message: str,
        prompt_version: PromptVersion = PromptVersion.V2,
        use_cache: bool = True,
    ) -> ExecutionRecord:
        """Gera um único tipo de conteúdo, consulta/grava cache e salva a execução."""
        profile = self.load_profile(profile_id)
        template = self.load_prompt_template(content_type, prompt_version)
        prompt_text = self.build_prompt(template, profile, customer_message)

        output_text, cached, latency_ms, token_usage = self.llm_client.generate(
            content_type=content_type.value,
            prompt_text=prompt_text,
            profile_id=profile_id,
            customer_message=customer_message,
            use_cache=use_cache,
            extra_metadata={"version": prompt_version.value},
        )

        record = ExecutionRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            content_type=content_type,
            prompt_version=prompt_version,
            profile_id=profile.id,
            customer_message=customer_message,
            output_text=output_text,
            cached=cached,
            latency_ms=round(latency_ms, 2),
            model_name=self.llm_client.model_name,
            metadata={
                "profile_name": profile.name,
                "technical_level": profile.technical_level,
                "token_usage": token_usage,
                "mock_mode": self.llm_client.mock_mode,
            },
        )

        self.storage.save_run(record)
        return record

    def generate_all(
        self,
        profile_id: str,
        customer_message: str,
        prompt_version: PromptVersion = PromptVersion.V2,
        use_cache: bool = True,
    ) -> Dict[ContentType, ExecutionRecord]:
        """Gera em lote os 4 tipos de conteúdo para o mesmo chamado e perfil."""
        results = {}
        for content_type in ContentType:
            results[content_type] = self.generate_single(
                content_type=content_type,
                profile_id=profile_id,
                customer_message=customer_message,
                prompt_version=prompt_version,
                use_cache=use_cache,
            )
        return results
