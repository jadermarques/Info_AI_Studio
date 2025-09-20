import pytest
from app.domain.fonte_service import register_youtube_channel, list_youtube_channels, delete_youtube_channel
from app.domain.entities import YouTubeChannel
from app.infrastructure.repositories import get_youtube_channel_by_id

@pytest.fixture(autouse=True)
def limpar_canais():
    # Remove todos os canais antes de cada teste
    canais = list_youtube_channels()
    for canal in canais:
        delete_youtube_channel(canal["id"])


def test_cadastrar_canal():
    canal = YouTubeChannel(
        nome="Canal Teste",
        canal_id="UC1234567890",
        grupos=[],
        descricao="",
        status=True,
        registro_id=None
    )
    register_youtube_channel(canal)
    canais = list_youtube_channels()
    assert any(c["foyt_nome_canal"] == "Canal Teste" and c["foyt_id_canal"] == "UC1234567890" for c in canais)


def test_alterar_canal():
    canal = YouTubeChannel(
        nome="Canal Teste",
        canal_id="UC1234567890",
        grupos=[],
        descricao="",
        status=True,
        registro_id=None
    )
    register_youtube_channel(canal)
    canais = list_youtube_channels(active_only=False)
    canal_id = canais[0]["foyt_id"]
    canal_editado = YouTubeChannel(
        nome="Canal Alterado",
        canal_id="UC1234567890",
        grupos=[],
        descricao="Alterado",
        status=False,
        registro_id=canal_id
    )
    register_youtube_channel(canal_editado)
    canais = list_youtube_channels(active_only=False)
    canal = [c for c in canais if c["foyt_id"] == canal_id][0]
    assert canal["foyt_nome_canal"] == "Canal Alterado"
    assert canal["foyt_status"] == 0


def test_excluir_canal():
    canal = YouTubeChannel(
        nome="Canal Teste",
        canal_id="UC1234567890",
        grupos=[],
        descricao="",
        status=True,
        registro_id=None
    )
    register_youtube_channel(canal)
    canais = list_youtube_channels(active_only=False)
    canal_id = canais[0]["foyt_id"]
    delete_youtube_channel(canal_id)
    canais = list_youtube_channels(active_only=False)
    assert not any(c["foyt_id"] == canal_id for c in canais)
