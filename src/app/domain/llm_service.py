"""Domain services related to LLM models."""

from __future__ import annotations

from typing import Any

from app.domain.entities import LLMModel
from app.infrastructure import repositories


def register_llm_model(model: LLMModel) -> None:
    """Persist a new LLM model or update an existing one."""

    repositories.save_llm_model(
        provedor=model.provedor,
        modelo=model.modelo,
        api_key=model.api_key,
        status=1 if model.status else 0,
    )


def list_llm_models() -> list[dict[str, Any]]:
    """Return stored LLM models."""

    return repositories.list_llm_models()