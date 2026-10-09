"""A vírgula decimal não pode partir a conta ao meio.

O passo a passo do Laboratório quebra em linhas quando traz várias
atribuições: "V_i = 240, d = 15" vira duas linhas alinhadas. A vírgula era
tratada sempre como separador — mas em português ela também é o separador
DECIMAL.

Visto na tela, num print feito para o TCC:

    "V_f = 240 \\cdot 0,85 = 204"      aparecia como      V_f = 240 · 0
                                                          85 = 204

A conta saía partida no meio do número, num passo a passo que existe
justamente para o aluno acompanhar o cálculo.

Regra: vírgula seguida de dígito é decimal, sempre. Só separa a que não é
seguida de dígito.
"""

from __future__ import annotations

import pytest

from core.formatters import _preparar_formula_passo


def quebrou_em_linhas(saida: str) -> bool:
    return "aligned" in saida


# --------------------------------------------------------------------------
# vírgula decimal: a conta fica inteira
# --------------------------------------------------------------------------

DECIMAIS = [
    ("desconto percentual", r"V_f = 240 \cdot 0,85 = 204"),
    ("fator no resultado", "fator = 1 - 15/100 = 0,85"),
    ("decimal dos dois lados", r"x = 2,5 \cdot 8 = 20,0"),
    ("tres casas decimais", r"C = 0,001 \cdot 1000 = 1"),
    ("decimal sozinho", "d = 0,75"),
    ("media com decimal", "M = 24,5/3 = 8,1"),
    ("massa molar", "M = 58,5 g/mol"),
    ("velocidade decimal", "v = 12,5/2,5 = 5"),
]


@pytest.mark.parametrize("rotulo, passo", DECIMAIS, ids=[c[0] for c in DECIMAIS])
def test_virgula_decimal_nao_parte_a_conta(rotulo, passo):
    saida = _preparar_formula_passo(passo)

    assert not quebrou_em_linhas(saida), f"{rotulo}: a conta foi partida em linhas"


def test_o_numero_decimal_chega_inteiro_na_saida():
    # O sintoma exato: "0,85" virava "0" numa linha e "85" na outra.
    saida = _preparar_formula_passo(r"V_f = 240 \cdot 0,85 = 204")

    assert "0,85" in saida
    assert r"\\ 85" not in saida


# --------------------------------------------------------------------------
# vírgula separadora: continua quebrando em linhas
# --------------------------------------------------------------------------

SEPARADORES = [
    ("dois valores", "V_i = 240, d = 15"),
    ("tres valores", "a = 1, b = 2, c = 3"),
    ("com a palavra 'e'", "V_i = 240 e d = 15"),
    ("ponto e virgula", "m = 4; a = 3"),
    ("sem espaco depois da virgula", "V_i = 240,d = 15"),
]


@pytest.mark.parametrize("rotulo, passo", SEPARADORES, ids=[c[0] for c in SEPARADORES])
def test_separador_continua_quebrando(rotulo, passo):
    saida = _preparar_formula_passo(passo)

    assert quebrou_em_linhas(saida), f"{rotulo}: deixou de separar as atribuicoes"


def test_decimal_e_separador_na_mesma_linha():
    # O caso misto, que antes errava para os DOIS lados: nao quebrava na
    # virgula separadora porque parava na decimal.
    saida = _preparar_formula_passo("V_i = 2,5, d = 15")

    assert quebrou_em_linhas(saida), "nao separou as duas atribuicoes"
    assert "2,5" in saida, "partiu o numero decimal"
