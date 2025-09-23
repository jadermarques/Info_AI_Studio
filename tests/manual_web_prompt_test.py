from datetime import date
from pathlib import Path

from app.domain.web_prompt_execution import _build_prompt_text, WebPromptParams


def make_params(prompt_base: str, instrucoes: str = "Instrucoes padrao.", formato: str = ".md") -> WebPromptParams:
    return WebPromptParams(
        data_inicio=date(2025, 9, 22),
        data_fim=date(2025, 9, 23),
        persona="Analista X",
        publico_alvo="Lideranças",
        segmentos="Saúde; Varejo",
        instrucoes=instrucoes,
        prompt_base=prompt_base,
        formato_saida=formato,
        llm_provedor="OPENAI",
        llm_modelo="gpt-4o-mini",
        api_key="dummy",
        outdir=Path("resultados_extracao/teste")
    )


def test_substituicoes_tokens():
    tpl = (
        "A {PERSONA} {DATA_INICIAL} {DATA_FINAL} {PUBLICO_ALVO} {SEGMENTOS} {FORMATO_SAIDA} "
        "[PERSONA] [PUBLICO ALVO] [DATA DE INICIO] [DATA DE FIM] [SEGMENTOS] [FORMATO SAIDA]"
    )
    res = _build_prompt_text(make_params(tpl))
    assert "{" not in res and "[" not in res, f"Tokens não substituídos: {res}"
    assert "Analista X" in res
    assert "22/09/2025" in res and "23/09/2025" in res
    assert "Lideranças" in res and "Saúde" in res
    assert ".md" in res


def test_dedupe_instrucoes_identicas():
    instr = "Bloco de instrucoes."
    tpl = (
        "<INSTRUCOES_GERAIS>\n" + instr + "\n</INSTRUCOES_GERAIS>\n\n"
        "Corpo do prompt.\n"
        "<INSTRUCOES_GERAIS>\n" + instr + "\n</INSTRUCOES_GERAIS>\n"
    )
    res = _build_prompt_text(make_params(tpl, instrucoes=instr))
    count = res.lower().count("<instrucoes_gerais>")
    assert count == 1, f"Esperava 1 bloco de instruções, obtive {count}:\n{res}"


def test_conflito_instrucoes_diferentes():
    tpl = (
        "<INSTRUCOES_GERAIS>\nA\n</INSTRUCOES_GERAIS>\nCorpo\n"
        "<INSTRUCOES_GERAIS>\nA\n</INSTRUCOES_GERAIS>\n"
    )
    try:
        _build_prompt_text(make_params(tpl, instrucoes="B"))
    except ValueError as e:
        assert "Inconsistência no prompt" in str(e)
    else:
        raise AssertionError("Esperava ValueError em conflito de instruções.")


if __name__ == "__main__":
    test_substituicoes_tokens()
    print("OK: substituições de tokens")
    test_dedupe_instrucoes_identicas()
    print("OK: deduplicação de instruções idênticas")
    test_conflito_instrucoes_diferentes()
    print("OK: conflito de instruções detectado")
    print("Todos os testes manuais passaram.")
