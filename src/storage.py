"""Camada de persistência em arquivos JSON para execuções e comparações."""

import json
from pathlib import Path
from typing import List, Optional
from src.config import STORAGE_DIR
from src.models import ExecutionRecord, ComparisonRecord


class StorageManager:
    """Gerencia a persistência de execuções e comparações em arquivos JSON."""

    def __init__(self, base_storage_dir: Optional[Path] = None):
        self.base_dir = Path(base_storage_dir) if base_storage_dir else STORAGE_DIR
        self.runs_dir = self.base_dir / "runs"
        self.comparisons_dir = self.base_dir / "comparisons"

        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.comparisons_dir.mkdir(parents=True, exist_ok=True)

    def save_run(self, record: ExecutionRecord) -> Path:
        """Salva um registro de execução em arquivo JSON."""
        file_path = self.runs_dir / f"{record.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)
        return file_path

    def get_run(self, run_id: str) -> Optional[ExecutionRecord]:
        """Recupera uma execução por ID."""
        file_path = self.runs_dir / f"{run_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ExecutionRecord(**data)

    def list_runs(self, limit: int = 50) -> List[ExecutionRecord]:
        """Lista as execuções ordenadas cronologicamente da mais recente para a mais antiga."""
        records = []
        for file_path in self.runs_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records.append(ExecutionRecord(**data))
            except Exception:
                continue
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def save_comparison(self, record: ComparisonRecord) -> Path:
        """Salva um relatório de comparação em arquivo JSON."""
        file_path = self.comparisons_dir / f"{record.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(), f, ensure_ascii=False, indent=2)
        return file_path

    def get_comparison(self, comp_id: str) -> Optional[ComparisonRecord]:
        """Recupera uma comparação por ID."""
        file_path = self.comparisons_dir / f"{comp_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ComparisonRecord(**data)

    def list_comparisons(self, limit: int = 50) -> List[ComparisonRecord]:
        """Lista as comparações ordenadas cronologicamente."""
        records = []
        for file_path in self.comparisons_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records.append(ComparisonRecord(**data))
            except Exception:
                continue
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]
