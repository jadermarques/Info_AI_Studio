import pytest
from app.interfaces.web.components.ui_helpers import paginate, status_badge

# Testes para paginate

def test_paginate_lista_curta():
    items = [{"id": i} for i in range(3)]
    paginados, page, start, end = paginate(items, "test", page_size=2)
    assert paginados == [{"id": 0}, {"id": 1}]
    assert page == 0
    assert start == 0
    assert end == 2

def test_paginate_lista_vazia():
    paginados, page, start, end = paginate([], "test", page_size=2)
    assert paginados == []
    assert page == 0
    assert start == 0
    assert end == 0

def test_paginate_pagina_limite():
    items = [{"id": i} for i in range(7)]
    # Simula página fora do limite
    import streamlit as st
    st.session_state["test"] = 10
    paginados, page, start, end = paginate(items, "test", page_size=2)
    assert page == 3  # última página possível
    assert paginados == [{"id": 6}]
    assert start == 6
    assert end == 7

# Testes para status_badge

def test_status_badge_ativo():
    html = status_badge(True)
    assert "Ativo" in html
    assert "#27ae60" in html

def test_status_badge_inativo():
    html = status_badge(False)
    assert "Inativo" in html
    assert "#c0392b" in html
