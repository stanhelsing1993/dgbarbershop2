import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _carregar_secrets() -> dict:
    """Lê secrets.toml dos mesmos caminhos que o Streamlit (Cloud inclusive),
    sem inicializar o runtime do Streamlit (que quebraria o set_page_config)."""
    caminhos = (
        Path.home() / ".streamlit" / "secrets.toml",
        BASE_DIR / ".streamlit" / "secrets.toml",
    )
    for caminho in caminhos:
        if caminho.exists():
            try:
                import toml

                return toml.load(caminho)
            except Exception:
                return {}
    return {}


_SECRETS = _carregar_secrets()


def _config(nome: str, padrao: str) -> str:
    """Ordem de prioridade: variável de ambiente/.env > secrets.toml > padrão."""
    valor = os.getenv(nome)
    if valor:
        return valor
    return _SECRETS.get(nome, padrao)


DATABASE_URL = _config("DATABASE_URL", f"sqlite:///{BASE_DIR / 'barbearia.db'}")

ADMIN_USERNAME = _config("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = _config("ADMIN_PASSWORD", "admin123")

HORARIO_ABERTURA = "08:00"
HORARIO_FECHAMENTO = "19:00"
DURACAO_SLOT_MINUTOS = 30
