"""Ponto de entrada principal para a CLI do Assistente de Atendimento ao Cliente."""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.cli import run

if __name__ == "__main__":
    run()
