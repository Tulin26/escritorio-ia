"""Conta sem "=" é fórmula, e `sqrt(144)` precisa cobrir o 144.

O que estava errado
-------------------
Um passo do Laboratório apareceu na tela como texto cru:

    (-8 ± sqrt(144)) / (2*(-2))

com `sqrt` e `*` literais, em vez de √ e ·. São dois defeitos empilhados.

**1. `parece_formula_laboratorio` exigia um `=`.** Sem ele o passo inteiro
descia para prosa. Mas `(-8 ± 12)/(-4)` é passo legítimo -- mostrar a
substituição *antes* de resolver é exatamente o que o prompt pede.

A função tinha quatro portas, e a história delas (`tests/test_passo_com_prosa.py`)
é a de um mesmo defeito que voltou **duas vezes**, porque a guarda de prosa foi
entrando uma porta por vez. Por isso a quinta porta não pergunta *"tem prosa
demais?"* -- ausência de prosa não é presença de fórmula. Ela pergunta *"isto é
só notação?"*: evidência positiva.

Medido antes de ligar: **5.784 passos distintos** dos bancos offline,
**0** regressões (nenhuma fórmula deixou de ser fórmula) e 101 passos que
passaram a ser tratados como matemática -- frações (`10/13`, `2/5`) e valores
com unidade (`2,18 g/L`), que renderizam melhor como LaTeX do que como texto.

**2. `sqrt(144)` virava `\\sqrt(144)`** -- radical sobre o vazio, com "(144)"
ao lado. A conversão para `\\sqrt{...}` existia só em `formatar_latex()`, que é
do Streamlit; o caminho do Flask nunca teve. Das cinco grafias que a IA usa, só
uma chegava certa.
"""

from __future__ import annotations

import pytest

from core.formula_formatting import (
    parece_formula_laboratorio,
    separar_texto_formula_passo,
)
from core.utils import preparar_formula_latex

# ====================== A QUINTA PORTA ======================

CONTAS_SEM_IGUAL = [
    "(-8 ± sqrt(144)) / (2*(-2))",   # o passo da tela
    "(-8 ± 12)/(-4)",
    "(7 + 5)/4",
    "12 · 0,577",
    "2 + 3",
    "10/13",
    "(-7)^2 - 4 · 2 · 3",
]


@pytest.mark.parametrize("conta", CONTAS_SEM_IGUAL)
def test_conta_sem_igual_e_formula(conta):
    assert parece_formula_laboratorio(conta), conta


@pytest.mark.parametrize("conta", CONTAS_SEM_IGUAL)
def test_conta_sem_igual_sai_inteira_como_formula(conta):
    """Não basta ser reconhecida: o passo não pode voltar partido em texto."""
    texto, formula = separar_texto_formula_passo(conta)

    assert formula, conta
    assert texto == "", f"sobrou prosa em {conta!r}: {texto!r}"


# A metade que protege o que já funcionava. A quinta porta é a mais larga das
# cinco -- é a única que não exige "=" nem comando LaTeX --, então é dela que
# se espera o próximo vazamento de prosa.
FRASES_QUE_NAO_PODEM_PASSAR = [
    "A resposta e 5 segundos",
    "identificar os valores",
    "Portanto o valor de x e positivo",
    "O triangulo tem lado 12 cm e altura 6 cm",
    "Total de 12 e 5",
    "Some 4 e 8 para achar 12",
    "a area do circulo de raio 3",
    "Compare 12 com 15",
    "Reduza 20 por cento de 50",
    "entre 10 e 20",
    "de 5 a 10",
    # sem operador: não é conta, é lista ou valor solto
    "1, 2, 3",
    "144",
    "x",
]


@pytest.mark.parametrize("frase", FRASES_QUE_NAO_PODEM_PASSAR)
def test_prosa_continua_fora(frase):
    assert not parece_formula_laboratorio(frase), frase


def test_a_quinta_porta_exige_operador_e_digito():
    """As duas exigências que separam conta de "número solto". Sem elas a
    porta aceitaria qualquer coisa que não tivesse palavra."""
    assert not parece_formula_laboratorio("144"), "número sozinho não é conta"
    assert not parece_formula_laboratorio("x y z"), "letras soltas não são conta"
    assert not parece_formula_laboratorio("7 8"), "dois números sem operador não são conta"
    assert parece_formula_laboratorio("7 + 8"), "com operador, é conta"


@pytest.mark.parametrize("valor", ["3 g/L", "4 g/L", "5 g/mL", "6 g/L", "x + 1"])
def test_um_digito_basta(valor):
    """O limiar era "dois dígitos", e era chute -- a mutação mostrou que
    nenhum teste o sustentava.

    Medido nos 5.784 passos dos bancos: baixar para um dígito aceita
    exatamente estes quatro valores com unidade a mais, e nenhuma frase de
    controle passa a entrar. Exigir dois recusava `x + 1`, que é fórmula."""
    assert parece_formula_laboratorio(valor), valor


# ====================== A GRAFIA COM BARRA ======================
#
# MELHORIA: estes três nasceram de um mutante que sobreviveu. Apagar o strip
# de comandos LaTeX de `_so_notacao_matematica` não quebrava teste nenhum,
# porque todos os meus casos usavam o "±" Unicode. Sem o strip, "\pm" vira a
# palavra "pm" -- que não está na lista de termos de fórmula -- e
# `(-8 \pm 12)/(-4)` voltava a ser prosa. A IA escreve das duas formas.


@pytest.mark.parametrize(
    "formula",
    [
        r"(-8 \pm 12)/(-4)",
        r"2 \cdot 3 + 1",
        r"12 \times 3",
        r"x \approx 3,14",
        r"\frac{18}{44} + 1",
    ],
)
def test_comando_latex_nao_conta_como_palavra(formula):
    assert parece_formula_laboratorio(formula), formula


def test_palavra_de_duas_letras_derruba_a_quinta_porta():
    """`_prosa_demais` conta palavras de 3+ letras, então "de", "em" e "ou"
    passavam por ela. A quinta porta olha 2+ letras justamente por isso."""
    assert not parece_formula_laboratorio("12 de 50")
    assert not parece_formula_laboratorio("(12 + 8) ou 20")


def test_nome_de_funcao_e_unidade_nao_derrubam():
    """O outro lado da regra de 2 letras: "cm", "kg", "sen" e "log" TEM duas
    letras ou mais e vivem dentro da fórmula."""
    assert parece_formula_laboratorio("12 cm + 8 cm")
    assert parece_formula_laboratorio("sen(30) · 2")


# ====================== A RAIZ ======================


@pytest.mark.parametrize(
    "grafia",
    ["sqrt(144)", "raiz(144)", "√(144)", "√144", "sqrt{144}"],
)
def test_toda_grafia_de_raiz_vira_sqrt_com_chave(grafia):
    """Com parêntese, o LaTeX desenha o radical sobre o VAZIO e escreve
    "(144)" ao lado. Só a chave cobre o número."""
    saida = preparar_formula_latex(grafia)

    assert r"\sqrt{144}" in saida, f"{grafia!r} virou {saida!r}"


def test_o_passo_da_tela_fica_correto_de_ponta_a_ponta():
    """O caso que abriu a investigação, do texto da IA até o LaTeX."""
    passo = "(-8 ± sqrt(144)) / (2*(-2))"

    assert parece_formula_laboratorio(passo), "continua sendo tratado como prosa"

    saida = preparar_formula_latex(passo)

    assert r"\pm" in saida, "o ± se perdeu"
    assert r"\sqrt{144}" in saida, "a raiz nao cobre o 144"
    assert r"\cdot" in saida, "o * continua literal"
    assert "sqrt(" not in saida and "*" not in saida


def test_a_raiz_do_delta_tambem_cobre():
    """A fórmula da primeira tela: x = (-b ± √Δ)/(2a)."""
    saida = preparar_formula_latex("x = (-b ± √Δ)/(2a)")

    assert r"\pm" in saida
    assert r"\sqrt{Δ}" in saida or r"\sqrt{\Delta}" in saida, saida


def test_raiz_ja_correta_nao_e_estragada():
    """A metade que protege: quem já escrevia certo continua certo."""
    assert preparar_formula_latex(r"\sqrt{25}").strip() == r"\sqrt{25}"


def test_multiplicacao_implicita_com_raiz_continua():
    """`2√3` é 2 vezes raiz de 3, e a regra de multiplicação implícita roda
    DEPOIS desta conversão -- a ordem importa."""
    saida = preparar_formula_latex("2√3")

    assert r"\cdot" in saida, f"perdeu a multiplicacao implicita: {saida!r}"
    assert r"\sqrt{3}" in saida, saida
