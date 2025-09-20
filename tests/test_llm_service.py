import pytest
from app.domain.llm_service import register_llm_model, list_llm_models, delete_llm_model
from app.domain.entities import LLMModel
from app.infrastructure.repositories import get_llm_model

@pytest.fixture(autouse=True)
def limpar_llms():
    modelos = list_llm_models()
    for modelo in modelos:
        delete_llm_model(modelo["id"])

def test_cadastrar_llm():
    modelo = LLMModel(
        provedor="OPENAI",
        modelo="gpt-5-nano",
        api_key="sk-123",
        status=True
    )
    register_llm_model(modelo)
    modelos = list_llm_models()
    assert any(m["provedor"] == "OPENAI" and m["modelo"] == "gpt-5-nano" for m in modelos)

def test_editar_llm():
    modelo = LLMModel(
        provedor="OPENAI",
        modelo="gpt-5-nano",
        api_key="sk-123",
        status=True
    )
    register_llm_model(modelo)
    modelos = list_llm_models()
    modelo_id = modelos[0]["id"]
    modelo_editado = LLMModel(
        provedor="OPENAI",
        modelo="gpt-5-nano",
        api_key="sk-456",
        status=False,
        model_id=modelo_id
    )
    register_llm_model(modelo_editado)
    modelo = get_llm_model(modelo_id)
    assert modelo["modl_api_key"] == "sk-456"
    assert modelo["modl_status"] == 0

def test_excluir_llm():
    modelo = LLMModel(
        provedor="OPENAI",
        modelo="gpt-5-nano",
        api_key="sk-123",
        status=True
    )
    register_llm_model(modelo)
    modelos = list_llm_models()
    modelo_id = modelos[0]["id"]
    delete_llm_model(modelo_id)
    modelos = list_llm_models()
    assert not any(m["id"] == modelo_id for m in modelos)
