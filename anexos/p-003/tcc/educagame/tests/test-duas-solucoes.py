"""Bhaskara escreve DUAS raízes numa linha só — e isso não é um número.

Quando a validação tenta reduzir `(-5 ± 1)/2` a um único valor, ela escolhe
uma das duas raízes em silêncio e compara com a alternativa marcada. Se a
marcada for a OUTRA, uma questão certa é recusada. O próprio código já
carrega a cicatriz disso, visto em produção com Groq: "-2 e -3" acusado de
`resultado-aritmetico-invalido`.

A guarda existia, mas só reconhecia LaTeX (`\\pm`) e unicode (`±`). Em ASCII
— `+-`, `+/-`, "mais ou menos" — a expressão passava adiante.

E havia um segundo furo, pior: a lista de funções tinha `sqrt` e
`raiz quadrada`, mas não `raiz(`. Então `x = raiz(25)` era avaliado, o
normalizador apagava o "raiz" e devolvia **25 em vez de 5** — um número
errado, comparado com a resposta certa.

Ser generoso aqui é seguro: reconhecer a mais significa apenas não comparar
um trecho que talvez desse para comparar. Reconhecer a menos significa
recusar questão certa.
"""

from __future__ import annotations

import pytest

from services.ia.validacao import (
    _avaliar_expressao_numerica,
    _deve_pular_comparacao_numerica,
)

DUAS_SOLUCOES = [
    ("LaTeX \\pm com \\sqrt", r"x = \frac{-5 \pm \sqrt{25 - 24}}{2}"),
    ("LaTeX \\pm sozinho", r"x = (-5 \pm 1)/2"),
    ("LaTeX \\mp", r"x = (-5 \mp 1)/2"),
    ("unicode ± com √", "x = (-5 ± √1)/2"),
    ("unicode ± sozinho", "x = (-5 ± 1)/2"),
    ("unicode ∓", "x = (-5 ∓ 1)/2"),
    ("ASCII +-", "x = (-5 +- 1)/2"),
    ("ASCII +- com raiz()", "x = (-5 +- raiz(1))/2"),
    ("ASCII +/-", "x = (-5 +/- 1)/2"),
    ("ASCII +/- com espaco", "x = (-5 + / - 1)/2"),
    ("ASCII -+", "x = (-5 -+ 1)/2"),
    ("por extenso", "x = (-5 mais ou menos 1)/2"),
    ("por extenso, maiuscula", "x = (-5 Mais Ou Menos 1)/2"),
]


@pytest.mark.parametrize("rotulo, passo", DUAS_SOLUCOES, ids=[c[0] for c in DUAS_SOLUCOES])
def test_nao_reduz_duas_solucoes_a_um_numero(rotulo, passo):
    assert _avaliar_expressao_numerica(passo) is None, (
        f"{rotulo}: inventou um numero onde ha duas raizes"
    )


@pytest.mark.parametrize("rotulo, passo", DUAS_SOLUCOES, ids=[c[0] for c in DUAS_SOLUCOES])
def test_a_comparacao_numerica_e_pulada(rotulo, passo):
    assert _deve_pular_comparacao_numerica(passo), rotulo


# --------------------------------------------------------------------------
# raiz escrita como função, em ASCII
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "passo",
    ["x = raiz(25)", "x = raiz (25)", "d = raiz(b^2 - 4ac)", "x = sqrt(25)",
     "x = a raiz quadrada de 25"],
)
def test_raiz_como_funcao_nao_vira_numero_errado(passo):
    # "raiz(25)" valia 25 -- o normalizador apagava o nome da funcao e
    # ficava com o argumento. Numero errado e pior que numero nenhum: ele e
    # comparado com a resposta e recusa a questao.
    assert _avaliar_expressao_numerica(passo) is None, passo


# --------------------------------------------------------------------------
# a metade que importa: a conta comum continua sendo avaliada
# --------------------------------------------------------------------------


CONTAS_NORMAIS = [
    ("divisao", "240/3", 80.0),
    ("soma", "2 + 3", 5.0),
    ("desconto", "200 - 200*15/100", 170.0),
    ("media", "(6+8+10)/3", 8.0),
    ("area", "4*5", 20.0),
    ("decimal com virgula", "2,5*8", 20.0),
    ("subtracao", "15 - 5", 10.0),
    ("numero negativo", "-98", -98.0),
    ("soma com negativo", "5 + -3", 2.0),
]


@pytest.mark.parametrize(
    "rotulo, conta, esperado", CONTAS_NORMAIS, ids=[c[0] for c in CONTAS_NORMAIS]
)
def test_conta_comum_continua_sendo_avaliada(rotulo, conta, esperado):
    # Alargar a guarda nao pode desligar a checagem para todo mundo: uma
    # validacao que nunca compara nada deixa passar conta errada.
    assert _avaliar_expressao_numerica(conta) == esperado, rotulo


@pytest.mark.parametrize("conta", [c[1] for c in CONTAS_NORMAIS])
def test_conta_comum_nao_e_pulada(conta):
    assert not _deve_pular_comparacao_numerica(conta), conta


def test_menos_isolado_nao_e_confundido_com_duas_solucoes():
    # "5 + -3" tem um sinal de negativo, nao um "mais ou menos". Se fosse
    # confundido, toda soma com numero negativo deixaria de ser conferida.
    assert not _deve_pular_comparacao_numerica("5 + -3")
    assert _avaliar_expressao_numerica("5 + -3") == 2.0
