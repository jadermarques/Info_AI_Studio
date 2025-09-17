"""Página para listar resultados das execuções anteriores."""

from __future__ import annotations

from datetime import datetime
import math
import mimetypes
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.config import get_settings


TEXT_EXTENSIONS = {".txt", ".json", ".md", ".html", ".log"}


def _collect_result_files(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    records: list[dict[str, Any]] = []
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        stats = entry.stat()
        size_kb = round(stats.st_size / 1024, 2)
        records.append(
            {
                "Nome do arquivo": entry.name,
                "Formato": entry.suffix.lstrip(".").upper() or "N/A",
                "Data": datetime.fromtimestamp(stats.st_mtime).date(),
                "Tamanho (KB)": size_kb,
                "Path": entry,
            }
        )
    records.sort(key=lambda item: item["Nome do arquivo"].lower())
    return records


def _filter_records(
    records: list[dict[str, Any]],
    file_type: str,
    name_query: str,
    size_range: tuple[float, float],
) -> list[dict[str, Any]]:
    size_min, size_max = float(size_range[0]), float(size_range[1])
    name_query_lower = name_query.lower().strip()
    filtered: list[dict[str, Any]] = []
    for record in records:
        if file_type != "Todos" and record["Formato"] != file_type:
            continue
        if name_query_lower and name_query_lower not in record["Nome do arquivo"].lower():
            continue
        if not (size_min <= record["Tamanho (KB)"] <= size_max):
            continue
        filtered.append(record)
    return filtered


def _render_table(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Path]]:
    mapping = {record["Nome do arquivo"]: record["Path"] for record in records}
    dataframe = pd.DataFrame(
        [
            {
                "Nome do arquivo": record["Nome do arquivo"],
                "Formato": record["Formato"],
                "Data de geração": record["Data"],
                "Tamanho (KB)": record["Tamanho (KB)"],
                "Visualizar": False,
                "Download": False,
            }
            for record in records
        ]
    )
    return dataframe, mapping


def _display_file_content(path: Path) -> None:
    st.divider()
    st.subheader(f"Visualização: {path.name}")
    if not path.exists():
        st.warning("Arquivo não encontrado. Talvez tenha sido removido ou renomeado.")
        return
    extension = path.suffix.lower()
    if extension not in TEXT_EXTENSIONS:
        st.info("Visualização disponível apenas para arquivos de texto.")
        return
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1", errors="replace")
    line_count = len(content.splitlines()) or 1
    height = min(900, max(200, line_count * 22))
    st.text_area("Conteúdo do arquivo", content, height=height, disabled=True)


st.title("Resultados das execuções")

settings = get_settings()
result_dir = settings.resultados_dir.resolve()

st.caption(f"Diretório configurado: {result_dir}")

files = _collect_result_files(result_dir)
if not files:
    st.info("Nenhum resultado encontrado no diretório configurado.")
    st.stop()

extensions = sorted({record["Formato"] for record in files if record["Formato"] != "N/A"})
max_size = max(record["Tamanho (KB)"] for record in files)

col_type, col_name, col_size = st.columns([1, 1, 1])
with col_type:
    tipo = st.selectbox("Formato do arquivo", options=["Todos", *extensions])
with col_name:
    nome = st.text_input("Nome do arquivo contém")
with col_size:
    size_step = max(1, int(math.ceil(max_size)))
    tamanho = st.slider(
        "Tamanho (KB)",
        min_value=0,
        max_value=size_step,
        value=(0, size_step),
    )

filtered_records = _filter_records(files, tipo, nome, tamanho)
if not filtered_records:
    st.info("Nenhum arquivo atende aos filtros informados.")
    st.stop()

table_df, file_map = _render_table(filtered_records)

edited_df = st.data_editor(
    table_df,
    key="resultados_editor",
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Formato": st.column_config.TextColumn("Formato", width="small"),
        "Data de geração": st.column_config.DateColumn("Data de geração", format="DD/MM/YYYY"),
        "Tamanho (KB)": st.column_config.NumberColumn("Tamanho (KB)", format="%.2f"),
        "Visualizar": st.column_config.CheckboxColumn(
            "Visualizar",
            help="Marque para exibir o conteúdo abaixo",
        ),
        "Download": st.column_config.CheckboxColumn(
            "⬇️",
            help="Marque para habilitar o download abaixo",
        ),
    },
    disabled=[
        "Nome do arquivo",
        "Formato",
        "Data de geração",
        "Tamanho (KB)",
    ],
)

selected_name = None
download_name = None
if not edited_df.empty and "Visualizar" in edited_df:
    selected_rows = [
        idx for idx, value in enumerate(edited_df["Visualizar"]) if bool(value)
    ]
    if selected_rows:
        selected_name = str(edited_df.iloc[selected_rows[-1]]["Nome do arquivo"])
    else:
        st.session_state.pop("resultados_selected", None)
if not edited_df.empty and "Download" in edited_df:
    download_rows = [
        idx for idx, value in enumerate(edited_df["Download"]) if bool(value)
    ]
    if download_rows:
        download_name = str(edited_df.iloc[download_rows[-1]]["Nome do arquivo"])
    else:
        st.session_state.pop("resultados_download", None)

if selected_name:
    st.session_state["resultados_selected"] = selected_name
if download_name:
    st.session_state["resultados_download"] = download_name

selected_session = st.session_state.get("resultados_selected")
if selected_session:
    selected_path = file_map.get(selected_session)
    if selected_path:
        _display_file_content(selected_path)

download_session = st.session_state.get("resultados_download")
if download_session:
    download_path = file_map.get(download_session)
    if download_path and download_path.exists():
        mime, _ = mimetypes.guess_type(download_path.name)
        st.download_button(
            label=f"⬇️ Baixar {download_path.name}",
            data=download_path.read_bytes(),
            file_name=download_path.name,
            mime=mime or "application/octet-stream",
            key=f"download_{download_path.name}",
        )
