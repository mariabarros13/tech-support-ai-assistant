"""Gerenciador de cache determinístico baseado em hash SHA-256."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional


class CacheManager:
    """Gerencia leitura e escrita de respostas de LLM em arquivos JSON indexados por hash SHA-256."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_key(
        content_type: str,
        prompt_text: str,
        profile_id: str,
        customer_message: str,
        model_name: str = "gemini-3.5-flash",
        mock_mode: bool = False,
    ) -> str:
        """Gera um hash SHA-256 determinístico para a combinação exata de entradas.

        O modo de execução (mock ou real) faz parte da chave, para que respostas
        sintéticas nunca sejam servidas a uma execução real e vice-versa.
        """
        raw_payload = (
            f"type:{content_type.strip()}|"
            f"prompt:{prompt_text.strip()}|"
            f"profile:{profile_id.strip()}|"
            f"msg:{customer_message.strip()}|"
            f"model:{model_name.strip()}|"
            f"mode:{'mock' if mock_mode else 'real'}"
        )
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Recupera registro do cache se existir."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def set(self, cache_key: str, output_text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Grava registro no cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        data = {
            "cache_key": cache_key,
            "output_text": output_text,
            "metadata": metadata or {},
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def clear(self) -> int:
        """Limpa todos os arquivos do diretório de cache e retorna o total removido."""
        count = 0
        for item in self.cache_dir.glob("*.json"):
            try:
                item.unlink()
                count += 1
            except Exception:
                pass
        return count
