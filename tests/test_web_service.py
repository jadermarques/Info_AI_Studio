import pytest
from app.domain.fonte_service import register_web_source, list_web_sources, delete_web_source
from app.domain.entities import WebSource

@pytest.fixture(autouse=True)
def limpar_fontes():
    fontes = list_web_sources()
    for fonte in fontes:
        delete_web_source(fonte["id"])

def test_cadastrar_fonte():
    fonte = WebSource(tipo="site", fonte="https://exemplo.com", descricao="Teste")
    register_web_source(fonte)
    fontes = list_web_sources()
    assert any(f["fowe_fonte"] == "https://exemplo.com" for f in fontes)

def test_editar_fonte():
    fonte = WebSource(tipo="site", fonte="https://exemplo.com", descricao="Teste")
    register_web_source(fonte)
    fontes = list_web_sources()
    fonte_id = fontes[0]["fowe_id"]
    fonte_editada = WebSource(tipo="site", fonte="https://exemplo.com", descricao="Alterado", registro_id=fonte_id)
    register_web_source(fonte_editada, entry_id=fonte_id)
    fontes = list_web_sources()
    fonte = [f for f in fontes if f["fowe_id"] == fonte_id][0]
    assert fonte["fowe_descricao"] == "Alterado"

def test_excluir_fonte():
    fonte = WebSource(tipo="site", fonte="https://exemplo.com", descricao="Teste")
    register_web_source(fonte)
    fontes = list_web_sources()
    fonte_id = fontes[0]["fowe_id"]
    delete_web_source(fonte_id)
    fontes = list_web_sources()
    assert not any(f["fowe_id"] == fonte_id for f in fontes)
