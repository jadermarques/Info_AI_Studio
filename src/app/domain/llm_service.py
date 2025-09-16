"""Domain services related to LLM models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.entities import LLMModel
from app.infrastructure import env_manager, repositories

try:  # pragma: no cover - optional dependency at runtime
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]


@dataclass(slots=True)
class LLMConnectionResult:
    """Resultado de validação de credenciais do modelo LLM."""

    sucesso: bool
    mensagem: str
    variavel_ambiente: str


class LLMConnectionError(RuntimeError):
    """Erro ao validar conexão com LLM."""

    def __init__(self, message: str, env_var: str) -> None:
        super().__init__(message)
        self.message = message
        self.env_var = env_var


def _normalizar_provedor(provedor: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", provedor.strip().upper()).strip("_")


def compute_api_key_env_name(provedor: str) -> str:
    """Retorna o nome padrão da variável de API para o provedor informado."""

    normalizado = _normalizar_provedor(provedor)
    return f"{normalizado or 'LLM'}_API_KEY"


def register_llm_model(model: LLMModel) -> None:
    """Persist a new LLM model or update an existing one."""

    provedor_normalizado = _normalizar_provedor(model.provedor)
    if model.model_id is not None:
        repositories.update_llm_model(
            model_id=model.model_id,
            provedor=provedor_normalizado,
            modelo=model.modelo,
            api_key=model.api_key,
            status=1 if model.status else 0,
        )
    else:
        repositories.save_llm_model(
            provedor=provedor_normalizado,
            modelo=model.modelo,
            api_key=model.api_key,
            status=1 if model.status else 0,
        )

    env_var = compute_api_key_env_name(provedor_normalizado)
    env_manager.update_env_values(
        {
            "LLM_PROVIDER": provedor_normalizado,
            "LLM_MODEL": model.modelo,
            "LLM_API_KEY": model.api_key,
            env_var: model.api_key,
        }
    )


def list_llm_models() -> list[dict[str, Any]]:
    """Return stored LLM models using normalized field names."""

    registros = repositories.list_llm_models()
    resultado: list[dict[str, Any]] = []
    for row in registros:
        resultado.append(
            {
                "id": row["modl_id"],
                "provedor": row["modl_provedor"],
                "modelo": row["modl_modelo_llm"],
                "api_key": row["modl_api_key"],
                "status": bool(row["modl_status"]),
                "created_at": row["modl_created_at"],
                "env_var": compute_api_key_env_name(row["modl_provedor"]),
            }
        )
    return resultado


def get_llm_model(model_id: int) -> LLMModel | None:
    """Fetch an LLM model and adapt it to the domain entity."""

    dados = repositories.get_llm_model(model_id)
    if not dados:
        return None
    return LLMModel(
        provedor=dados["modl_provedor"],
        modelo=dados["modl_modelo_llm"],
        api_key=dados["modl_api_key"],
        status=bool(dados["modl_status"]),
        model_id=dados["modl_id"],
    )


def delete_llm_model(model_id: int) -> None:
    """Remove o modelo informado."""

    repositories.delete_llm_model(model_id)


def _traduzir_erro(mensagem: str) -> str:
    """Mapeia mensagens de erro comuns para Português."""

    texto = mensagem.strip()
    if not texto:
        return "Erro desconhecido ao validar o modelo."
    texto_lower = texto.lower()
    if "api key" in texto_lower and ("invalid" in texto_lower or "incorrect" in texto_lower):
        return "Chave de API inválida ou não autorizada."
    if "not found" in texto_lower or "does not exist" in texto_lower:
        return "Modelo informado não existe ou não está disponível."
    if "rate limit" in texto_lower:
        return "Limite de requisições atingido para o provedor."
    if "timeout" in texto_lower or "connection" in texto_lower:
        return "Não foi possível conectar ao provedor. Verifique sua rede."
    return texto


def test_llm_connection(model: LLMModel) -> LLMConnectionResult:
    """Verifica se as credenciais informadas permitem acessar o provedor."""

    provedor_normalizado = _normalizar_provedor(model.provedor)
    env_var = compute_api_key_env_name(provedor_normalizado)
    if not provedor_normalizado:
        raise LLMConnectionError("Informe o provedor do modelo.", env_var)
    if not model.api_key.strip():
        raise LLMConnectionError("Informe a chave de API para testar a conexão.", env_var)
    if provedor_normalizado == "OPENAI":
        if OpenAI is None:
            raise LLMConnectionError(
                "Biblioteca OpenAI não instalada no ambiente.", env_var
            )
        try:
            cliente = OpenAI(api_key=model.api_key)
            cliente.models.retrieve(model.modelo)
            return LLMConnectionResult(
                sucesso=True,
                mensagem=(
                    f"Conexão com {provedor_normalizado} bem-sucedida."
                    f" Variável {env_var} válida."
                ),
                variavel_ambiente=env_var,
            )
        except Exception as exc:  # pragma: no cover - depende da API externa
            mensagem = _traduzir_erro(str(exc))
            raise LLMConnectionError(mensagem, env_var) from exc
    raise LLMConnectionError(
        f"Provedor {provedor_normalizado} ainda não suportado para validação.", env_var
    )
