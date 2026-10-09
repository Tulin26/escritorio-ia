"""A fórmula que a IA mandou, do jeito que o aluno a viu (15/09/2026).

Numa Bhaskara da IA, no Laboratório:

  - a fórmula chegou com a barra escapada DUAS vezes e a tela mostrou
    "-bpmsqrtDelta": o MathJax lê "\\\\" como quebra de linha;
  - o "2a" do denominador virou 2 ampere, "2 a" em letra reta e separada;
  - as alternativas mostraram "x_1 = 3, x_2 = -1", com o índice cru.

As barras são montadas com chr(92), para nada no caminho mexer nelas. Cada
correção vem com o par: o que já saía certo continua saindo.
"""
from __future__ import annotations

import pytest

from core.formula_formatting import formatar_formula_principal_latex, formatar_subformulas_auxiliares_latex

B = chr(92)
SIMPLES = f"x = {B}frac{{-b {B}pm {B}sqrt{{{B}Delta}}}}{{2a}}"
DOBRADA = SIMPLES.replace(B, B * 2)


def test_a_formula_com_barra_dobrada_sai_igual_a_simples():
    assert DOBRADA.count(B) == 2 * SIMPLES.count(B)
    assert formatar_formula_principal_latex(DOBRADA) == formatar_formula_principal_latex(SIMPLES)


@pytest.mark.parametrize("comando", ["pm", "sqrt", "Delta", "cdot", "times", "approx", "pi", "theta"])
def test_nenhum_comando_conhecido_fica_com_barra_dobrada(comando):
    desenho = formatar_formula_principal_latex(f"y = 2 {B * 2}{comando} 3")

    assert f"{B * 2}{comando}" not in desenho
    assert f"{B}{comando}" in desenho


def test_a_subformula_com_barra_dobrada_tambem_sai_certa():
    assert formatar_subformulas_auxiliares_latex([f"{B * 2}Delta = b^2 - 4ac"]) == formatar_subformulas_auxiliares_latex([f"{B}Delta = b^2 - 4ac"])


def test_quebra_de_linha_seguida_de_comando_fica_com_as_tres_barras():
    """"\\\\\\Delta" é quebra de linha ("\\\\") seguida de "\\Delta": não é barra dobrada."""
    from core.utils import _desfazer_barra_dobrada

    alinhado = f"a &= 1{B * 3}Delta &= 2"

    assert _desfazer_barra_dobrada(alinhado) == alinhado
    assert _desfazer_barra_dobrada(f"a = 1 {B * 2}Delta") == f"a = 1 {B}Delta"


def test_a_quebra_de_linha_do_sistema_continua():
    """O banco escreve sistemas assim; "\\\\x" é quebra de linha, não comando."""
    sistema = f"{B}begin{{cases}}x+y=5{B * 2}x-y=1{B}end{{cases}}"

    assert f"{B * 2}x" in formatar_formula_principal_latex(sistema)


@pytest.mark.parametrize(
    "formula, nao_pode",
    [
        (SIMPLES, "mathrm{a}"),
        ("a_n = 2n - 1", "mathrm{n}"),
        ("d = 2v t", "mathrm{v}"),
        (f"{B}Delta = b^2 - 4 a c", "mathrm{a}"),
    ],
)
def test_variavel_depois_de_numero_nao_vira_unidade(formula, nao_pode):
    assert nao_pode.lower() not in formatar_formula_principal_latex(formula).lower()


@pytest.mark.parametrize(
    "formula, unidade",
    [
        ("I = 5 A", "mathrm{A}"),
        ("F = 3 N", "mathrm{N}"),
        ("U = 12 V", "mathrm{V}"),
        ("P = 60 W", "mathrm{W}"),
        ("V = 2 L", "mathrm{L}"),
        ("m = 3 kg", "mathrm{kg}"),
        ("t = 5 s", "mathrm{s}"),
        ("d = 12 m", "mathrm{m}"),
    ],
)
def test_unidade_escrita_como_unidade_continua_unidade(formula, unidade):
    assert unidade in formatar_formula_principal_latex(formula)


def test_a_alternativa_mostra_o_indice():
    from pathlib import Path

    from flask_app import app

    partial = (Path(__file__).resolve().parents[1] / "web" / "templates" / "partials" / "options_form.html").read_text(encoding="utf-8")
    assert "formula_html" in partial

    render = app.jinja_env.from_string("{{ opcao|unidades|formula_html }}")
    assert render.render(opcao="x_1 = 3, x_2 = -1") == "x<sub>1</sub> = 3, x<sub>2</sub> = -1"
    # alternativa comum continua igual
    assert render.render(opcao="R$ 108,00") == "R$ 108,00"
