"""Página de visualização e filtros de logs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
import re
import json as _json
import time

import streamlit as st

from app.config import get_settings

title_left, title_right = st.columns([6, 1])
with title_left:
    st.title("Logs do sistema")
with title_right:
    if st.session_state.get("logs_auto_refresh", False):
        st.markdown(
            """
            <div style=\"display:inline-block; padding:4px 8px; background:#16a34a; color:#fff; border-radius:12px; font-weight:600; font-size:0.85rem;\">AO VIVO</div>
            """,
            unsafe_allow_html=True,
        )
settings = get_settings()
log_file = (settings.log_dir / "app.log").resolve()
log_file.parent.mkdir(parents=True, exist_ok=True)

st.caption(f"Arquivo de log: {log_file}")
colr1, colr2, colr3, colr4 = st.columns([1,1,2,2])
with colr1:
    if st.button("Recarregar logs"):
        st.rerun()
with colr2:
    tail_kb = st.number_input("Ler últimos N KB", min_value=1, max_value=10240, value=512, step=64)
with colr3:
    max_lines = st.number_input("Máx. linhas exibidas", min_value=100, max_value=20000, value=5000, step=100)
with colr4:
    auto_refresh = st.checkbox("Autoatualizar", value=st.session_state.get("logs_auto_refresh", False), help="Recarrega automaticamente aplicando os filtros atuais.")
    st.session_state["logs_auto_refresh"] = auto_refresh
    refresh_interval = st.number_input("Intervalo (s)", min_value=2, max_value=120, value=st.session_state.get("logs_refresh_interval", 5), step=1)
    st.session_state["logs_refresh_interval"] = refresh_interval

with st.expander("Configurações de log", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        log_level = st.selectbox(
            "Nível mínimo",
            ["DEBUG", "INFO", "WARNING", "ERROR", "FULL"],
            index=["DEBUG","INFO","WARNING","ERROR","FULL"].index(settings.log_level or "INFO"),
        )
    with col2:
        rotate_mb = st.number_input("Tamanho máx. (MB)", min_value=1, max_value=1024, value=int(settings.log_rotate_max_mb or 10))
    with col3:
        backups = st.number_input("Qtd. backups", min_value=1, max_value=100, value=int(settings.log_backup_count or 5))
    st.caption("Tipos habilitados controlam o filtro aplicado nos handlers")
    types = st.multiselect(
        "Tipos habilitados",
        options=["error","warning","info","debug","full"],
        default=[t.strip() for t in (settings.log_types or "error,warning,info").split(",") if t.strip()],
    )
    if st.button("Salvar configurações de log"):
        # fallback: persistir direto no .env
        try:
            from app.infrastructure.env_manager import update_env_values
            update_env_values({
                "LOG_LEVEL": log_level,
                "LOG_ROTATE_MAX_MB": str(int(rotate_mb)),
                "LOG_BACKUP_COUNT": str(int(backups)),
                "LOG_TYPES": ",".join(types) if types else "info,warning,error",
            })
            st.success("Configurações de log salvas. Reinicie a app para aplicar completamente.")
        except Exception as exc:
            st.error(f"Falha ao salvar configurações: {exc}")

st.divider()

with st.expander("Manutenção", expanded=False):
    st.caption("Limpar conteúdo do log atual e backups (opcional)")
    colm1, colm2 = st.columns([2, 2])
    with colm1:
        confirm_clear = st.checkbox("Confirmar limpeza do app.log")
    with colm2:
        remove_backups = st.checkbox("Excluir backups (app.log.*)")
    if st.button("Limpar logs"):
        if not confirm_clear:
            st.warning("Marque 'Confirmar limpeza do app.log' para prosseguir.")
        else:
            try:
                if log_file.exists():
                    log_file.write_text("", encoding="utf-8")
                removed = 0
                if remove_backups:
                    for p in log_file.parent.glob(log_file.name + ".*"):
                        try:
                            p.unlink()
                            removed += 1
                        except Exception:
                            pass
                st.success(f"Logs limpos. Backups removidos: {removed}")
            except Exception as exc:
                st.error(f"Falha ao limpar logs: {exc}")

"""
Organização: definimos primeiro utilitários, lemos a cauda do log e extraímos
as opções estruturadas de UI_EVENT para popular os filtros antes do formulário.
"""

# Leitura segura do log com limite
def read_log_lines(path: Path, max_lines: int = 5000, tail_kb: int = 512):
    if not path.exists():
        return []
    try:
        size = path.stat().st_size
        start = max(0, size - (tail_kb * 1024))
        with path.open("rb") as fb:
            fb.seek(start)
            data = fb.read()
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        return lines[-max_lines:]
    except Exception:
        return []

lines = list(read_log_lines(log_file, max_lines=int(max_lines), tail_kb=int(tail_kb)))

# Descobrir ações e páginas de UI_EVENT para filtros estruturados
ui_actions: set[str] = set()
ui_pages: set[str] = set()
for ln in lines:
    m = re.search(r"UI_EVENT\s+(\w+)", ln)
    if m:
        ui_actions.add(m.group(1))
    idx = ln.find("UI_EVENT")
    if idx != -1:
        rest = ln[idx + len("UI_EVENT"):].strip()
        parts = rest.split(None, 1)
        payload_str = parts[1] if len(parts) > 1 else ""
        jstart = payload_str.find("{")
        jend = payload_str.rfind("}")
        if jstart != -1 and jend != -1 and jend > jstart:
            js = payload_str[jstart : jend + 1]
            try:
                obj = _json.loads(js)
                page_val = obj.get("page") or obj.get("pagina") or obj.get("area")
                if page_val:
                    ui_pages.add(str(page_val))
            except Exception:
                pass

# Filtros de visualização
with st.form("log_filters"):
    colf1, colf2, colf3 = st.columns([2,2,2])
    with colf1:
        search = st.text_input("Buscar texto")
    with colf2:
        level = st.multiselect("Níveis", options=["DEBUG","INFO","WARNING","ERROR","FULL"], default=["INFO","WARNING","ERROR","FULL"])
    with colf3:
        minutes = st.number_input("Últimos N minutos", min_value=0, max_value=1440, value=0, help="0 = todos")
    run_id = st.text_input("Filtrar por run_id (opcional)", help="Ex.: web_prompt_YYYYMMDD_HHMMSS")
    colu1, colu2 = st.columns([2,2])
    with colu1:
        ui_event_actions = st.multiselect("Ações UI_EVENT", options=sorted(ui_actions))
    with colu2:
        ui_event_pages = st.multiselect("Páginas UI_EVENT", options=sorted(ui_pages))
    submitted = st.form_submit_button("Aplicar filtros")

min_timestamp = None
if minutes and minutes > 0:
    min_timestamp = datetime.now(timezone(timedelta(hours=-3))) - timedelta(minutes=int(minutes))

# Aplicar filtros
filtered: list[str] = []
for ln in lines:
    ok = True
    if level:
        ok = any((f" {lvl} ") in ln for lvl in level)
    if ok and min_timestamp:
        # espera formato padrão no início da linha: YYYY-MM-DD HH:MM:SS,mmm
        try:
            ts_str = ln.split(" - ")[0]
            ts = datetime.fromisoformat(ts_str.replace(",", "."))
            ok = ts >= min_timestamp
        except Exception:
            ok = ok
    if ok and run_id:
        ok = (run_id in ln)
    if ok and search:
        ok = (search.lower() in ln.lower())
    if ok and ui_event_actions:
        ok = any((f"UI_EVENT {act}") in ln for act in ui_event_actions)
    if ok and ui_event_pages:
        ok = any(page in ln for page in ui_event_pages)
    if ok:
        filtered.append(ln)

st.subheader("Visualização")
text = "".join(filtered) if filtered else "(sem resultados)"
st.text_area("Logs filtrados", value=text, height=420)

colb1, colb2 = st.columns(2)
with colb1:
    st.download_button("Baixar trecho filtrado", data=text.encode("utf-8"), file_name="logs_filtrados.txt")
with colb2:
    st.code(text)
    st.caption("Selecione e copie o conteúdo acima para copiar.")

# Auto-refresh controlado
if st.session_state.get("logs_auto_refresh", False):
    time.sleep(st.session_state.get("logs_refresh_interval", 5))
    st.rerun()
