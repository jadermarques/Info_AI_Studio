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

# --- Novo teste para XML do YouTubeExecutionService ---

def test_report_xml_boolean_and_params(tmp_path, monkeypatch):
    # Evita acessar config real
    from app.domain.youtube.service import YouTubeExecutionService
    svc = YouTubeExecutionService.__new__(YouTubeExecutionService)
    class C: pass
    c = C()
    c.report_format = 'xml'
    c.prefix = 'test'
    c.outdir = tmp_path
    setattr(svc, 'config', c)
    setattr(svc, 'resultados_dir', tmp_path)
    # Monta metadata mínima
    metadata = {
        'executed_at': '2025-09-21T10:00:00',
        'mode': 'simple',
        'total_channels': 1,
        'total_videos': 1,
        'params': {
            'no_llm': True,
            'ui_extras': {'a': 1, 'b': [1,2]},
            'format': 'xml',
        },
        'channels': [
            {
                'channel_id': '@test',
                'name': 'Canal Teste',
                'status': 'success',
                'videos': [
                    {
                        'id': 'vid1',
                        'url': 'u',
                        'title': 't',
                        'title_pt': 'tp',
                        'language': 'en',
                        'view_count': 10,
                        'has_transcript': False,
                        'analysis_source': 'modo_simples',
                    }
                ]
            }
        ]
    }
    xml = svc._report_xml(metadata)
    # Cabeçalho XML
    assert xml.startswith('<?xml'), 'XML deve começar com declaração XML'
    # Booleanos normalizados
    assert '<tem_transcricao>false</tem_transcricao>' in xml
    # Params dict/list em JSON como texto
    assert '<no_llm>true</no_llm>' in xml
    assert '<format>xml</format>' in xml
    # ui_extras vira JSON string
    assert '"a": 1' in xml and '"b": [1, 2]' in xml
