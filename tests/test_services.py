from __future__ import annotations

from app.domain.entities import LLMModel, WebSource, YouTubeChannel
from app.domain.llm_service import list_llm_models, register_llm_model, delete_llm_model
from app.domain.fonte_service import (
    register_web_source,
    list_web_sources,
    register_youtube_channel,
    list_youtube_channels,
    delete_youtube_channel,
)


def test_llm_crud():
    # Create
    model = LLMModel(provedor="OpenAI", modelo="gpt-5-nano", api_key="test-key", status=True)
    register_llm_model(model)
    models = list_llm_models()
    assert any(m["modelo"] == "gpt-5-nano" for m in models)

    # Update
    mid = next(m["id"] for m in models if m["modelo"] == "gpt-5-nano")
    register_llm_model(LLMModel(provedor="OpenAI", modelo="gpt-5-nano", api_key="new-key", status=False, model_id=mid))
    models2 = list_llm_models()
    updated = next(m for m in models2 if m["id"] == mid)
    assert updated["api_key"] == "new-key"
    assert updated["status"] is False

    # Delete
    delete_llm_model(mid)
    models3 = list_llm_models()
    assert all(m["id"] != mid for m in models3)


def test_web_crud():
    # Create
    src = WebSource(tipo="site", fonte="https://exemplo.com", descricao="Teste", status=True)
    register_web_source(src)
    items = list_web_sources(active_only=False)
    assert any(i["fowe_fonte"] == "https://exemplo.com" for i in items)

    # Update
    wid = next(i["fowe_id"] for i in items if i["fowe_fonte"] == "https://exemplo.com")
    register_web_source(WebSource(tipo="blog", fonte="https://exemplo.com", descricao="Novo", status=False), entry_id=wid)
    items2 = list_web_sources(active_only=False)
    updated = next(i for i in items2 if i["fowe_id"] == wid)
    assert updated["fowe_tipo"] == "blog"
    assert updated["fowe_status"] == 0 or updated["fowe_status"] is False


def test_youtube_crud():
    # Create
    ch = YouTubeChannel(nome="Canal X", descricao="Desc", grupos=["dev"], canal_id="@canalx", status=True)
    register_youtube_channel(ch)
    chans = list_youtube_channels(active_only=False)
    assert any(c["foyt_id_canal"] == "@canalx" for c in chans)

    # Update
    cid = next(c["foyt_id"] for c in chans if c["foyt_id_canal"] == "@canalx")
    register_youtube_channel(YouTubeChannel(nome="Canal X", descricao="Nova", grupos=["dev","ai"], canal_id="@canalx", status=False, registro_id=cid))
    chans2 = list_youtube_channels(active_only=False)
    updated = next(c for c in chans2 if c["foyt_id"] == cid)
    assert "ai" in (updated.get("foyt_grupo_canal") or "")
    assert updated["foyt_status"] == 0 or updated["foyt_status"] is False

    # Delete
    delete_youtube_channel(cid)
    chans3 = list_youtube_channels(active_only=False)
    assert all(c["foyt_id"] != cid for c in chans3)
