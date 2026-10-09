"""Frase com conta dentro não é fórmula — e expoente cru não chega à tela.

Dois defeitos vistos na mesma questão do RPG, e **nenhum dos dois é do RPG**:
os dois caminhos são compartilhados por Laboratório, Oráculo e ENEM.

**1. O enunciado chegava com o acento circunflexo.**

    A funcao f(x) = (x - 4)^2 + 5 tem vertice em qual ponto?

O padrão que transforma equação em LaTeX já tinha sido alargado duas vezes,
sempre acrescentando *um* formato: primeiro a equação com `= n`, depois a
expressão quadrática sozinha. O quadrado da binomial é um terceiro — o `^2`
vem depois de `)`, não de `x`. Perseguir formato por formato não termina;
agora o que sobrar com `^n` vira sobrescrito de verdade.

**2. O passo da resolução saía com as palavras coladas.**

    Compare f(x) = (x - 4)^2 + 5 com f(x) = a(x - h)^2 + k

`parece_formula_laboratorio` dizia *"tem `^` ou `=` em algum lugar? então é
fórmula"* — sem olhar quanta prosa vinha junto. A frase inteira ia para o
MathJax e voltava tipografada como matemática, sem espaço:

    Comparef(x)=(x−4)²+5comf(x)=a(x−h)²+k

A última linha daquela função já tinha a guarda certa (no máximo 14
palavras); aquela não tinha nenhuma.
"""

from __future__ import annotations

import pytest

from core.formula_formatting import parece_formula_laboratorio, separar_texto_formula_passo
from web.routes.flask_helpers_fla import expoentes_em_sobrescrito, formatar_pergunta_exatas

PASSO_DO_RPG = "Compare f(x) = (x - 4)^2 + 5 com f(x) = a(x - h)^2 + k"
PERGUNTA_DO_RPG = "A funcao f(x) = (x - 4)^2 + 5 tem vertice em qual ponto?"


# ====================== O ENUNCIADO ======================


def test_o_enunciado_do_rpg_chega_legivel():
    texto = formatar_pergunta_exatas(PERGUNTA_DO_RPG)["texto"]

    assert "^" not in texto, "expoente cru na tela"
    assert "(x - 4)² + 5" in texto
    assert "função" in texto and "vértice" in texto


@pytest.mark.parametrize(
    "cru, esperado",
    [
        ("x^2", "x²"),
        ("(x - 4)^2", "(x - 4)²"),
        ("2^10", "2¹⁰"),
        ("10^-3", "10⁻³"),
        ("[H+] = 10^-7", "[H+] = 10⁻⁷"),
    ],
)
def test_expoente_vira_sobrescrito(cru, esperado):
    assert expoentes_em_sobrescrito(cru) == esperado


@pytest.mark.parametrize("intacto", ["10^{-3}", "^2", "e^{x}", "a ^ 2"])
def test_o_que_nao_e_expoente_simples_fica_como_esta(intacto):
    # "10^{-3}" com chave é LaTeX e tem dono: o padrão de pH em
    # formatar_pergunta_exatas. "^2" solto não tem base à esquerda.
    assert expoentes_em_sobrescrito(intacto) == intacto


# ====================== O PASSO DA RESOLUÇÃO ======================


def test_a_frase_do_passo_nao_vira_formula():
    texto, formula = separar_texto_formula_passo(PASSO_DO_RPG)

    assert formula == "", "a frase inteira foi para o MathJax"
    assert texto == PASSO_DO_RPG


def test_a_frase_do_passo_chega_com_expoente_legivel():
    # As duas correções se encontram aqui: sobrando como prosa, o passo ainda
    # carrega conta no meio, e o expoente precisa estar legível.
    import web.routes.rpg_fla as rpg_fla

    passos = rpg_fla._preparar_passos_resolucao(
        [{"titulo": "1o Passo", "conteudo": PASSO_DO_RPG}]
    )

    assert passos[0]["conteudo_latex"] == ""
    assert "^" not in passos[0]["conteudo_texto"]
    assert "(x - 4)² + 5" in passos[0]["conteudo_texto"]
    assert "com f(x)" in passos[0]["conteudo_texto"], "as palavras têm que sobreviver"


FORMULAS_DE_VERDADE = [
    "x = (-5 + 1)/2",
    "Delta = b^2 - 4ac",
    "A = pi * r^2",
    "razao = (27-7)/4",
    "sen(30) = 0,5",
    "v = 10 * 2",
    "\\frac{a}{b} = 5",
    "Q = m * c * 25",
    # MELHORIA: estas duas nao comecam com "nome =", entao passam pela
    # guarda de prosa em vez de serem aceitas antes dela. Uma palavra de
    # verdade no meio da conta ("raio", "altura") e normal; e por isso
    # que o limiar e DUAS, e nao uma. Sem elas aqui, baixar para uma
    # passaria despercebido.
    "2 * pi * raio = 31,4",
    "3 * altura = 15",
]


@pytest.mark.parametrize("formula", FORMULAS_DE_VERDADE)
def test_formula_de_verdade_continua_sendo_formula(formula):
    # A metade que não pode se perder: apertar o critério não vale nada se
    # jogar fora as fórmulas que já iam bem para o MathJax.
    assert parece_formula_laboratorio(formula), formula
    texto, extraida = separar_texto_formula_passo(formula)
    assert extraida, formula
    assert texto == "", formula


FRASES = [
    "Compare f(x) = (x - 4)^2 + 5 com f(x) = a(x - h)^2 + k",
    "Some os dois lados e depois divida tudo por 2 para achar x = 5",
    "Observe que o valor encontrado corresponde ao vertice da parabola x^2",
]


@pytest.mark.parametrize("frase", FRASES)
def test_frase_com_conta_dentro_nao_e_formula(frase):
    assert not parece_formula_laboratorio(frase), frase


def test_nome_de_funcao_matematica_nao_conta_como_prosa():
    # "sen", "log" e "raiz" vivem DENTRO da fórmula; se contassem como
    # palavras, duas delas na mesma linha derrubariam a detecção.
    assert parece_formula_laboratorio("sen(x) = cos(x)")
    assert parece_formula_laboratorio("log(x) + raiz(y) = 10")


# ====================== AS QUATRO PORTAS ======================
#
# MELHORIA: `parece_formula_laboratorio` tem QUATRO caminhos que devolvem
# "isto e formula", e a guarda de prosa foi entrando um de cada vez -- por
# isso o mesmo defeito voltou duas vezes, com outra questao.
#
# A segunda volta foi vista no Laboratorio em producao, na questao de
# trigonometria do banco offline:
#
#     c = 50 m e o seno de 30 graus vale 0,5.
#         -> c = 50 meosenode30grausvale0,5
#
# Ela entrava pela PRIMEIRA porta ("comeca com nome =") e, depois que essa
# fechou, pela QUARTA ("letra =, no maximo 14 palavras" -- a frase tem 12).


FRASES_QUE_ENTRAVAM_POR_CADA_PORTA = [
    # 1a porta: "nome =" com dois digitos no texto
    ("c = 50 m e o seno de 30 graus vale 0,5.", "nome = ... com frase depois"),
    # 4a porta: "letra =" e menos de 14 palavras
    ("Procure x tal que 2^x = 8.", "letra = em frase curta"),
    # 3a porta: tem "=" ou "^" (esta ja estava fechada, fica de guarda)
    ("Compare f(x) = (x - 4)^2 + 5 com f(x) = a(x - h)^2 + k", "simbolo solto"),
]


@pytest.mark.parametrize("frase, porta", FRASES_QUE_ENTRAVAM_POR_CADA_PORTA)
def test_nenhuma_das_portas_aceita_frase(frase, porta):
    assert not parece_formula_laboratorio(frase), f"entrou pela porta: {porta}"


@pytest.mark.parametrize("frase, _porta", FRASES_QUE_ENTRAVAM_POR_CADA_PORTA)
def test_a_frase_chega_inteira_na_tela(frase, _porta):
    texto, formula = separar_texto_formula_passo(frase)

    assert formula == "", "foi para o MathJax"
    assert texto == frase


# ====================== UNIDADE NAO E PROSA ======================


UNIDADES_EM_FORMULA = [
    r"n = \frac{18 g}{44 g/mol} = 0,41 mol",
    r"Q = 250 g \cdot 1 cal/gC \cdot 20 C = 5000 cal",
    "n = 0,5 mol, M = 44 g/mol",
    "m = 28 kg, a = 27 m/s^2",
    # Aqui o "mol" DECIDE: sem ele na lista de unidades, "mol" e
    # "proporcao" viram duas palavras de prosa e o passo cai para texto.
    "n_A = 3 mol, proporcao = 2",
    r"n = \frac{2 atm \cdot 5 L}{0,082 \cdot 300 K} = 0,4 mol",
]


@pytest.mark.parametrize("formula", UNIDADES_EM_FORMULA)
def test_unidade_de_medida_nao_conta_como_prosa(formula):
    """A metade que se perdeu na primeira tentativa de corrigir isto.

    "mol", "cal" e "atm" tem tres letras e nao vivem na lista de palavras de
    formula. Contadas como prosa, derrubavam 348 passos do banco (5%) --
    quimica e fisica sao feitas de unidade.
    """
    assert parece_formula_laboratorio(formula), formula
    _, extraida = separar_texto_formula_passo(formula)
    assert extraida, formula


def test_palavra_depois_de_numero_nao_vira_unidade_por_estar_ali():
    """A segunda tentativa, que errou para o outro lado.

    Tratar QUALQUER palavra depois de um numero como unidade fazia o "com" de
    "... + 5 com f(x) = ..." sumir da contagem, e a frase do RPG voltava
    inteira para o MathJax. So conta como unidade o que ESTA na lista.
    """
    from core.formula_formatting import _prosa_demais

    assert _prosa_demais("Compare f(x) = (x - 4)^2 + 5 com f(x) = a(x - h)^2 + k")
    assert not _prosa_demais("m = 28 kg, a = 27 m/s^2")


def test_a_lista_de_unidades_e_a_mesma_da_validacao():
    """Uma copia so: `core/unidades.py`.

    A lista existia dentro de services/ia/validacao.py, onde cobra que a
    alternativa de Fisica ou Quimica carregue unidade. Passou a servir tambem
    para separar formula de prosa. Duas copias divergiriam na primeira unidade
    nova que alguem acrescentasse de um lado so.
    """
    import services.ia.validacao as validacao
    from core.unidades import UNIDADES_FISICA, UNIDADES_QUIMICA

    assert validacao.UNIDADES_FISICA is UNIDADES_FISICA
    assert validacao.UNIDADES_QUIMICA is UNIDADES_QUIMICA
