from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import json
import os
import re

from app.config import get_settings

try:  # optional at runtime
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

# Reutiliza tabela de preços conhecida (se disponível)
try:
    from app.domain.llm_client import _MODEL_PRICES as MODEL_PRICES  # type: ignore
except Exception:  # pragma: no cover
    MODEL_PRICES = {}


@dataclass(slots=True)
class WebPromptParams:
    data_inicio: date
    data_fim: date
    persona: str
    publico_alvo: str
    segmentos: str
    instrucoes: str
    prompt_base: str
    formato_saida: str  # .txt | .md | .pdf | .json | .xml
    llm_provedor: str
    llm_modelo: str
    api_key: str
    outdir: Path


@dataclass(slots=True)
class WebPromptResult:
    started_at: datetime
    ended_at: datetime
    elapsed_seconds: float
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    cost_estimated: float
    prompt_executed: str
    result_text: str
    report_path: Optional[str]
    log_path: Optional[str]


def _format_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = MODEL_PRICES.get(model.lower()) if hasattr(model, "lower") else None
    if not prices:
        return 0.0
    cost = (prompt_tokens / 1000.0) * float(prices.get("input", 0.0))
    cost += (completion_tokens / 1000.0) * float(prices.get("output", 0.0))
    return round(cost, 4)


def _build_prompt_text(params: WebPromptParams) -> str:
    inicio = _format_br(params.data_inicio)
    fim = _format_br(params.data_fim)
    mapping = {
        "{persona}": params.persona.strip(),
        "{publico_alvo}": params.publico_alvo.strip(),
        "{segmentos}": params.segmentos.strip(),
        "{data_inicio}": inicio,
        "{data_fim}": fim,
        "{formato_saida}": params.formato_saida,
    "{FORMATO_SAIDA}": params.formato_saida,
    # tokens com underscore e caixa alta (variação solicitada)
    "{PERSONA}": params.persona.strip(),
    "{PUBLICO_ALVO}": params.publico_alvo.strip(),
    "{SEGMENTOS}": params.segmentos.strip(),
    "{DATA_INICIAL}": inicio,
    "{DATA_FINAL}": fim,
        # suportar forma textual do exemplo
        "{valor do campo persona}": params.persona.strip(),
        "{valor do campo publico-alvo}": params.publico_alvo.strip(),
        "{valor do campo segmentos}": params.segmentos.strip(),
        "{valor do campo data de inicio}": inicio,
        "{valor do campo data de termino}": fim,
        "{valor do campo formato saida}": params.formato_saida,
    # placeholders com colchetes do arquivo de prompt
    "[PERSONA]": params.persona.strip(),
    "[PUBLICO ALVO]": params.publico_alvo.strip(),
    "[SEGMENTOS]": params.segmentos.strip(),
    "[DATA DE INÍCIO]": inicio,
    "[DATA DE INICIO]": inicio,
    "[DATA DE FIM]": fim,
    "[FORMATO SAIDA]": params.formato_saida,
    }

    def _apply_mapping(text: str) -> str:
        out = text
        for token, value in mapping.items():
            out = out.replace(token, value)
        return out

    # Helpers para tratar <INSTRUCOES_GERAIS>
    tag_re = re.compile(r"<\s*instrucoes_gerais\s*>(.*?)<\s*/\s*instrucoes_gerais\s*>", re.IGNORECASE | re.DOTALL)

    def _normalize(s: str) -> str:
        # Normaliza espaços e quebras de linha para comparar conteúdo
        return " ".join((s or "").strip().split())

    def _dedupe_instr(text: str) -> str:
        # Remove ocorrências duplicadas idênticas, mantendo a primeira
        matches = list(tag_re.finditer(text))
        if len(matches) <= 1:
            return text
        contents = [m.group(1) for m in matches]
        norm = [_normalize(c) for c in contents]
        # Se houver mais de um conteúdo distinto, sinaliza inconsistência
        if len(set(norm)) > 1:
            raise ValueError(
                "Inconsistência no prompt: múltiplas tags <INSTRUCOES_GERAIS> com conteúdos diferentes. "
                "Edite o template ou o campo de instruções para manter apenas uma versão."
            )
        # Todos idênticos: manter apenas a primeira ocorrência
        first_span = matches[0].span()
        first_block = text[first_span[0]:first_span[1]]
        # Remove todas e reinjeta a primeira no início do texto
        text_without = tag_re.sub("", text)
        # Evita duplicar nova linha em excesso
        if not text_without.lstrip().startswith("<"):
            sep = "\n\n"
        else:
            sep = "\n"
        return first_block + sep + text_without.strip()

    if params.prompt_base and params.prompt_base.strip():
        base = _apply_mapping(params.prompt_base)
        # Verifica ocorrências no template
        blocks = [m.group(1) for m in tag_re.finditer(base)]
        instr_form = params.instrucoes.strip()
        if blocks:
            # Dedup dentro do template
            base = _dedupe_instr(base)
            # Comparar conteúdo do template com o do formulário (se preenchido)
            if instr_form:
                # Reextrai o bloco único após dedupe
                m = tag_re.search(base)
                tpl_content = m.group(1) if m else ""
                if _normalize(tpl_content) != _normalize(instr_form):
                    raise ValueError(
                        "Inconsistência no prompt: o conteúdo de <INSTRUCOES_GERAIS> no template difere do digitado "
                        "em 'Instruções gerais do prompt'. Ajuste para manter apenas um conteúdo."
                    )
            # Já existe a tag no template (após dedupe) e é consistente: não adicionar cabeçalho extra
            return base
        else:
            # Não existe a tag no template: adiciona cabeçalho com instruções (se houver)
            head = f"<INSTRUCOES_GERAIS>\n{instr_form}\n</INSTRUCOES_GERAIS>\n\n" if instr_form else ""
            return head + base

    # fallback para template padrão interno
    default_template = (
        """
<INSTRUCOES_GERAIS>
{instrucoes}
</INSTRUCOES_GERAIS>

<PROMPT>
Atue como {persona}.
Seu objetivo é compilar um briefing semanal conciso, abrangente e estratégico para a semana de {data_inicio} a {data_fim}.
O público-alvo é {publico_alvo}.
O formato final deve ser em {formato_saida}.
A saída deve conforme a estrutura abaixo:
- Para cada item, forneça um resumo curto (1-2 frases) e, sempre que possível, o link para a fonte original.
- Priorize fontes de alta credibilidade (ex: The Verge, TechCrunch, blogs oficiais das empresas, artigos de pesquisa, relatórios de consultorias).

# Briefing Semanal de IA e IA Generativa

**Período:** {data_inicio} a {data_fim}

## 1. Resumo Executivo
* **Destaque 1:** [Resumo do fato mais importante da semana] [Link]
* **Destaque 2:** [Resumo do segundo fato mais importante] [Link]
* **Destaque 3:** [Resumo do terceiro fato mais importante] [Link]
* **Destaque 4:** [Resumo do quarto fato mais importante] [Link]
* **Destaque 5:** [Resumo do quinto fato mais importante] [Link]

## 2. Notícias e Anúncios de Destaque
* **Big Techs:** 
* [Nome da Empresa]: [Resumo da notícia] - [Link]

* **Startups e Investimentos:** 
* [Nome da Startup]: [Resumo da notícia sobre investimento ou aquisição] - [Link]

* **Regulamentação e Ética:** 
* [Tópico ou Região]: [Resumo da notícia] - [Link]

## 3. Inovações em Modelos 
* **Novos Lançamentos:** 
* [Nome do Modelo] por [Empresa/Organização]: [Descrição das capacidades] - [Link]
* **Atualizações Relevantes:** 
* [Nome do Modelo Existente]: [Descrição da atualização] - [Link]
* **Destaques Open Source:** 
* [Nome do Modelo Open Source]: [Descrição e motivo do destaque] - [Link]

## 4. Novas Ferramentas e Aplicações 
* **Para Desenvolvedores:** 
* [Nome da Ferramenta/Biblioteca]: [Descrição da sua função] - [Link]
* **Para Usuários Finais:** 
* [Nome do Aplicativo]: [Descrição da sua função] - [Link]
* **Caso de Uso de Impacto:** 
* [Empresa/Setor]: [Descrição de como a IA foi aplicada e o resultado] - [Link]

## 5. Análises de Mercado e Insights Estratégicos 
* **Insights de Consultorias:** 
* [Nome da Consultoria (ex: Gartner)]:[Principal insight do relatório/artigo] - [Link]
* **Tendência Emergente:** 
* [Nome da Tendência]: [Breve explicação sobre o que é e por que é importante] - [Link]
* **Análise de Influenciador:** 
* [Nome do Influenciador]: [Resumo da sua análise ou opinião] - [Link para post/vídeo]

# Análise IA por Segmento

Faça a análise, conforme estrutura abaixo, para cada um dos segmentos em {segmentos}.
## Segmento {{segmento}}

### 1. Análises de Mercado e Insights Estratégicos 
* **Insights de Consultorias:** 
* [Nome da Consultoria (ex: Gartner)]:[Principal insight do relatório/artigo] - [Link]
* **Tendência Emergente:** 
* [Nome da Tendência]: [Breve explicação sobre o que é e por que é importante] - [Link]
* **Análise de Influenciador:** 
* [Nome do Influenciador]: [Resumo da sua análise ou opinião] - [Link para post/vídeo]

### 2. Inovação em Ferramentas de IA Generativa (Grandes Empresas)
* **Cases de inovação com implantação de IA Generativa:** 
* [Nome da Empresa ]:[Breve descrição do processo de implantação da IA Generatica na empresa, benefícios/resultados] - [Link]
* **Notícias sobre automatização de tarefas/rotinas:** 
* [Nome da Empresa]: [Breve descrição do processo/tarefa/rotina automatizada] - [Link]

### 3. Inovação em Ferramentas de IA Generativa (Pequenas e Médias Empresas)
* **Cases de inovação com implantação de IA Generativa:** 
* [Nome da Empresa ]:[Breve descrição do processo de implantação da IA Generatica na empresa, benefícios/resultados] - [Link]
* **Notícias sobre automatização de tarefas/rotinas:** 
* [Nome da Empresa]: [Breve descrição do processo/tarefa/rotina automatizada] - [Link]

</PROMPT>
"""
    )
    return _apply_mapping(default_template.format(instrucoes=params.instrucoes.strip()))


def _ensure_outdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_outputs(prefix: str, outdir: Path, formato: str, prompt_text: str, result_text: str, meta: dict) -> tuple[Optional[str], Optional[str]]:
    """Salva relatório no formato indicado e um arquivo de log básico."""
    _ensure_outdir(outdir)
    report_path: Optional[str] = None
    log_path = str(outdir / f"{prefix}.log")
    # Log
    try:
        with open(log_path, "w", encoding="utf-8") as logf:
            logf.write(json.dumps(meta, ensure_ascii=False, indent=2))
            logf.write("\n\n=== PROMPT EXECUTADO ===\n")
            logf.write(prompt_text)
            logf.write("\n\n=== RESULTADO ===\n")
            logf.write(result_text)
    except Exception:
        log_path = None

    ext = formato.lower()
    if ext == ".txt" or ext == "txt":
        report_path = str(outdir / f"{prefix}.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result_text)
    elif ext == ".md" or ext == "md":
        report_path = str(outdir / f"{prefix}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result_text)
    elif ext == ".json" or ext == "json":
        report_path = str(outdir / f"{prefix}.json")
        payload = {"prompt": prompt_text, "resultado": result_text, "meta": meta}
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    elif ext == ".xml" or ext == "xml":
        import xml.etree.ElementTree as ET
        from xml.dom import minidom
        root = ET.Element("consulta_web")
        params_el = ET.SubElement(root, "parametros")
        for k, v in {
            "data_inicio": meta.get("data_inicio"),
            "data_fim": meta.get("data_fim"),
            "persona": meta.get("persona"),
            "publico_alvo": meta.get("publico_alvo"),
            "segmentos": meta.get("segmentos"),
            "formato": meta.get("formato"),
            "modelo": meta.get("modelo"),
        }.items():
            el = ET.SubElement(params_el, k)
            el.text = str(v) if v is not None else ""
        prompt_el = ET.SubElement(root, "prompt")
        prompt_el.text = prompt_text
        result_el = ET.SubElement(root, "resultado")
        result_el.text = result_text
        xml_bytes = ET.tostring(root, encoding="utf-8")
        pretty = minidom.parseString(xml_bytes).toprettyxml(indent="  ")
        report_path = str(outdir / f"{prefix}.xml")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(pretty)
    elif ext == ".pdf" or ext == "pdf":
        try:
            from fpdf import FPDF  # type: ignore
        except Exception as exc:
            raise RuntimeError("Para gerar PDF, instale a biblioteca 'fpdf2'.") from exc
        report_path = str(outdir / f"{prefix}.pdf")
        import textwrap
        pdf = FPDF()
        pdf.set_left_margin(12)
        pdf.set_right_margin(12)
        pdf.add_page()
        pdf.set_auto_page_break(True, margin=15)
        # Tentar carregar fonte Unicode (DejaVuSans.ttf) se disponível
        using_unicode_font = False
        try:
            base_dir = Path(__file__).resolve()
            candidates = [
                base_dir.parent.parent / "assets" / "DejaVuSans.ttf",        # src/app/assets
                base_dir.parent.parent.parent / "assets" / "DejaVuSans.ttf", # projeto_root/assets
            ]
            for cand in candidates:
                if cand.exists():
                    pdf.add_font("DejaVu", "", str(cand), uni=True)
                    pdf.set_font("DejaVu", size=11)
                    using_unicode_font = True
                    break
        except Exception:
            using_unicode_font = False
        if not using_unicode_font:
            # Fallback para fonte padrão (sem suporte completo a Unicode)
            pdf.set_font("Arial", size=11)

        def _insert_soft_breaks(s: str, max_run: int = 80) -> str:
            """Insere espaços em sequências muito longas sem espaços para permitir quebra.
            Útil para URLs ou palavras contínuas.
            """
            out_parts: list[str] = []
            token = []
            run = 0
            for ch in s:
                if ch.isspace():
                    if token:
                        out_parts.append("".join(token))
                        token = []
                        run = 0
                    out_parts.append(ch)
                else:
                    token.append(ch)
                    run += 1
                    if run >= max_run:
                        out_parts.append("".join(token))
                        out_parts.append(" ")  # espaço vira ponto de quebra
                        token = []
                        run = 0
            if token:
                out_parts.append("".join(token))
            return "".join(out_parts)

        def _md_to_readable(text: str) -> str:
            lines_out: list[str] = []
            for raw in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
                line = raw.expandtabs(4)
                # Títulos markdown (#, ##, ### ...)
                if re.match(r"^\s*#{1,6}\s+", line):
                    title = re.sub(r"^\s*#{1,6}\s+", "", line).strip()
                    if title:
                        lines_out.append("")  # espaço antes
                        lines_out.append(title.upper())
                        lines_out.append("")  # espaço depois
                    continue
                # Bullets (*, -)
                line = re.sub(r"^\s*[\*-]\s+", "• ", line)
                # Remover marcações de ênfase simples (** **, __ __, ` `)
                line = line.replace("**", "").replace("__", "").replace("`", "")
                lines_out.append(line)
            return "\n".join(lines_out)

        def _write_text_safe(text: str) -> None:
            text = _md_to_readable(text)
            max_w = pdf.w - pdf.l_margin - pdf.r_margin

            def _encode_if_needed(s: str) -> str:
                if using_unicode_font:
                    return s
                try:
                    s.encode("latin-1")
                    return s
                except Exception:
                    return s.encode("latin-1", "replace").decode("latin-1")

            def _write_line_char_wrapped(line: str, line_h: float) -> None:
                # Insere soft breaks e aplica encode conforme a fonte
                txt = _insert_soft_breaks(line, max_run=60)
                txt = _encode_if_needed(txt)
                curr = ""
                for ch in txt:
                    try:
                        ch_w = pdf.get_string_width(ch)
                    except Exception:
                        ch = "?"
                        ch_w = pdf.get_string_width(ch)
                    curr_w = pdf.get_string_width(curr)
                    if curr_w + ch_w <= max_w:
                        curr += ch
                        continue
                    # Se nenhum caractere cabe em linha vazia, reduzir fonte temporariamente
                    if curr == "":
                        # reduzir e tentar novamente
                        original_size = pdf.font_size_pt
                        new_size = max(7, int(original_size) - 2)
                        try:
                            if using_unicode_font:
                                pdf.set_font("DejaVu", size=new_size)
                            else:
                                pdf.set_font("Arial", size=new_size)
                            # Recalcula larguras com nova fonte
                            ch_w = pdf.get_string_width(ch)
                            if ch_w > max_w:
                                ch = "?"
                            # ainda que grande, escrevemos sozinho
                            pdf.multi_cell(max_w, line_h - 1, txt=ch)
                        finally:
                            # restaurar fonte original
                            if using_unicode_font:
                                pdf.set_font("DejaVu", size=original_size)
                            else:
                                pdf.set_font("Arial", size=original_size)
                        continue
                    # quebra linha antes de adicionar ch
                    pdf.multi_cell(max_w, line_h, txt=curr)
                    curr = ch
                if curr:
                    pdf.multi_cell(max_w, line_h, txt=curr)

            try:
                # primeira tentativa com fonte atual e altura 6
                for line in text.splitlines() or [text]:
                    _write_line_char_wrapped(line, line_h=6)
            except Exception:
                # Fallback 1: reduzir fonte
                try:
                    if using_unicode_font:
                        pdf.set_font("DejaVu", size=9)
                    else:
                        pdf.set_font("Arial", size=9)
                    for line in text.splitlines() or [text]:
                        _write_line_char_wrapped(line, line_h=5)
                except Exception:
                    # Fallback 2: reduzir mais e quebrar agressivamente
                    if using_unicode_font:
                        pdf.set_font("DejaVu", size=8)
                    else:
                        pdf.set_font("Arial", size=8)
                    for para in text.splitlines() or [text]:
                        wrapped = textwrap.wrap(_encode_if_needed(para), width=80, break_long_words=True, break_on_hyphens=True)
                        for sub in wrapped:
                            pdf.multi_cell(max_w, 4, txt=sub)

        _write_text_safe(result_text)
        pdf.output(report_path)
    else:
        # por padrão, salva como .txt
        report_path = str(outdir / f"{prefix}.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result_text)
    return report_path, log_path


def execute_web_prompt(params: WebPromptParams) -> WebPromptResult:
    if OpenAI is None:
        raise RuntimeError("Biblioteca OpenAI não instalada no ambiente.")

    started = datetime.now()
    fmt = params.formato_saida if params.formato_saida.startswith(".") else "." + params.formato_saida
    final_prompt = _build_prompt_text(params)

    base_url: Optional[str] = None
    prov = params.llm_provedor.strip().upper()
    if prov == "PERPLEXITY":
        base_url = "https://api.perplexity.ai"
    # OPENAI e outros compatíveis usam base padrão
    client = OpenAI(api_key=params.api_key, base_url=base_url) if base_url else OpenAI(api_key=params.api_key)

    # Chamada ao modelo
    response = client.chat.completions.create(
        model=params.llm_modelo,
        messages=[
            {"role": "system", "content": "Você é um analista competente. Responda em Português (Brasil) quando possível."},
            {"role": "user", "content": final_prompt},
        ],
    )
    # Extrai texto e usage
    content = ""
    if hasattr(response, "choices") and response.choices:
        first = response.choices[0]
        message = getattr(first, "message", None)
        if message is not None:
            content = getattr(message, "content", "") or ""
        if not content:
            content = getattr(first, "text", "") or ""
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or (usage.get("prompt_tokens") if isinstance(usage, dict) else 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or (usage.get("completion_tokens") if isinstance(usage, dict) else 0) or 0)
    cost = _estimate_cost(params.llm_modelo, prompt_tokens, completion_tokens)

    settings = get_settings()
    prefix = f"web_prompt_{started.strftime('%Y%m%d_%H%M%S')}"
    meta = {
        "data_inicio": _format_br(params.data_inicio),
        "data_fim": _format_br(params.data_fim),
        "persona": params.persona,
        "publico_alvo": params.publico_alvo,
        "segmentos": params.segmentos,
        "formato": fmt,
        "modelo": params.llm_modelo,
        "provedor": params.llm_provedor,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "custo_estimado": cost,
        "started_at": started.isoformat(timespec="seconds"),
    }
    report_path, log_path = _save_outputs(prefix, params.outdir, fmt, final_prompt, content, meta)

    ended = datetime.now()
    return WebPromptResult(
        started_at=started,
        ended_at=ended,
        elapsed_seconds=(ended - started).total_seconds(),
        model_used=params.llm_modelo,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_estimated=cost,
        prompt_executed=final_prompt,
        result_text=content,
        report_path=report_path,
        log_path=log_path,
    )
