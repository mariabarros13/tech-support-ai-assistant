"""Gerenciamento de configurações e variáveis de ambiente."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega arquivo .env se presente
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Provedor e Chaves
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# Diretórios
CACHE_DIR = BASE_DIR / os.getenv("CACHE_DIR", "storage/cache")
STORAGE_DIR = BASE_DIR / os.getenv("STORAGE_DIR", "storage")
PROFILES_DIR = BASE_DIR / os.getenv("PROFILES_DIR", "profiles")
PROMPTS_DIR = BASE_DIR / os.getenv("PROMPTS_DIR", "prompts")

# Flags
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() in ("true", "1", "yes")
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")

# Garantir existência de diretórios básicos
CACHE_DIR.mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "runs").mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "comparisons").mkdir(parents=True, exist_ok=True)
