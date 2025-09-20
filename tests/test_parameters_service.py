from app.domain.parameters_service import update_parameters
from app.config import get_settings
import os

def test_get_settings():
    settings = get_settings()
    # Verifica se é um objeto Settings
    assert hasattr(settings, "db_path")

def test_update_parameters(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("")  # garante que o arquivo existe
    monkeypatch.setenv("ENV_PATH", str(env_path))
    update_parameters({"OPENAI_API_KEY": "sk-xyz"})
    with open(env_path) as f:
        content = f.read()
    assert "OPENAI_API_KEY=sk-xyz" in content
