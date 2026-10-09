"""`\\dfrac` chega inteiro na tela.

Visto em produção em 11/09/2026, no Laboratório de Física: a fórmula veio da
IA como `W = F \\cdot d, \\; P = \\dfrac{W}{t}` -- LaTeX válido -- e a tela
mostrou `P = \\d` em vermelho seguido da fração.

O estrago era nosso. `_normalizar_frac` conserta o `frac{` escrito sem barra
olhando só se o caractere ANTES é uma barra. Em `\\dfrac` o que vem antes de
`frac` é a letra `d`, e a regra enfiava outra barra no meio: `\\d\\frac`.

Medido antes de consertar: nenhuma das 50.900 questões do banco próprio usa
`\\dfrac`; das 13 questões reais da IA registradas no dia, 1 usou -- e quebrou.
"""

from __future__ import annotations

import pytest

from core.utils import _normalizar_frac, preparar_formula_latex


@pytest.mark.parametrize(
    "formula",
    [r"P = \dfrac{W}{t}", r"x = \tfrac{a}{b}", r"y = \cfrac{1}{1 + x}"],
    ids=["dfrac", "tfrac", "cfrac"],
)
def test_as_variantes_do_frac_chegam_inteiras(formula):
    assert _normalizar_frac(formula) == formula


def test_o_caso_de_producao_ate_a_tela():
    """O caminho inteiro que a rota usa, e não só a função do meio."""
    saida = preparar_formula_latex(r"W = F \cdot d, \; P = \dfrac{W}{t}")

    assert r"\d\frac" not in saida, saida
    assert r"\dfrac{W}{t}" in saida, saida


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        (r"frac{1}{2}", r"\frac{1}{2}"),
        (r"x = 3frac{1}{2}", r"x = 3\frac{1}{2}"),
        (r"ffrac{1}{2}", r"\frac{1}{2}"),
    ],
    ids=["solto", "depois-de-numero", "f-dobrado"],
)
def test_o_frac_sem_barra_continua_consertado(bruto, esperado):
    """O que a regra existe para consertar não pode deixar de ser consertado."""
    assert _normalizar_frac(bruto) == esperado


def test_frac_colado_em_letra_comum_continua_virando_fracao():
    """Por que a trava é só para \\dfrac, \\tfrac e \\cfrac, e não para
    "qualquer letra antes": `xfrac{1}{2}` hoje desenha x vezes a fração."""
    assert _normalizar_frac(r"xfrac{1}{2}") == r"x\frac{1}{2}"
