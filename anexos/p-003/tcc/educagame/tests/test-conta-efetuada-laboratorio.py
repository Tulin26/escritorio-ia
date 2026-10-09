"""A resolucao mostra a conta FEITA, ou so anunciada?

E o que o Laboratorio existe para exigir de Matematica. Numero de
Matematica pura nao carrega unidade, entao aqui nao da para usar o mesmo
criterio de Fisica/Quimica -- o sinal tem que ser estrutural.

No lugar disto havia uma lista de doze palavras procuradas no ENUNCIADO:

    aceita   "Resolva a equacao 2x + 5 = 15."
    recusa   "Calcule o valor de x em 2x + 5 = 15."

A mesma conta, decidida por sorteio de palavra. Recusava 9 de 15 questoes
boas.

So remover aquela lista NAO bastaria: passariam a valer resolucoes que
apenas repetem o enunciado ou que so mostram o resultado. Os dois testes
em "a conta tem que aparecer feita" sao exatamente esses casos, e eles
falham se alguem trocar esta checagem por um `return False`.
"""

from __future__ import annotations

import pytest

from services.ia.validacao import (
    _questao_exatas_sem_calculo_laboratorio,
    _resolucao_efetua_alguma_conta,
)


def questao(pergunta, opcoes, formula, passos, subformulas=()):
    return {
        "pergunta": pergunta,
        "opcoes": opcoes,
        "formula": formula,
        "subformulas": list(subformulas),
        "passos_resolucao": [{"conteudo": p} for p in passos],
    }


# --------------------------------------------------------------------------
# o trecho que conta como "conta feita"
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "passo",
    [
        "15 - 5",
        "x = 10/2",
        "M = (6+8+10)/3",
        "P = 200 - 200*15/100",
        "A = 4*5",
        "a6 = 3 + (6-1)*4",
        "D = 25 - 24",
        "P = 2,5*8",              # decimal com virgula
        r"v = \frac{240}{3}",     # fracao em LaTeX
        r"v = 240 \div 3",
        r"A = 4 \times 5",
        "A = 4 × 5",
        "x = (3/4)*200",
        "J = 500*2/100*6",
        # funcao aplicada a numero ainda e valor calculado, nao incognita.
        # Trigonometria e tema que o proprio prompt do Laboratorio pede, e
        # foi um teste ja existente que pegou esta falta.
        "h = 50 * tan(60) = 86,6 metros",
        r"h = 50 \cdot tan(60)",
        "x = raiz(16+9)",
        r"x = \sqrt{16+9}",
        "y = 2 * log(100)",
        "c = 10 * sen(30)",
        # o coeficiente do x e descartado, mas a conta que veio ANTES dele
        # no mesmo trecho continua valendo
        "15 - 5 + 2x",
        # numero seguido de palavra (com espaco) nao e coeficiente
        "P = 2*15 reais",
    ],
)
def test_reconhece_a_conta_feita(passo):
    assert _resolucao_efetua_alguma_conta([passo]), passo


def test_funcao_sozinha_nao_e_conta():
    # Tirar o nome da funcao nao pode transformar "tan(60)" numa conta:
    # continua sendo um valor so.
    assert not _resolucao_efetua_alguma_conta(["h = tan(60)"])
    assert not _resolucao_efetua_alguma_conta(["x = raiz(25)"])


@pytest.mark.parametrize(
    "passo",
    [
        "2x + 5 = 15",        # ainda tem incognita: e o enunciado repetido
        "x = 5",              # so o resultado
        "isole o x",
        "aplique a formula",
        "",
        "an = a1 + (n-1)*r",  # a formula simbolica, sem numeros substituidos
        "-98",                # sinal de numero negativo nao e operacao
        "o valor e 12",
        # a conta so vale quando NAO ha mais incognita: aqui o x continua la,
        # e "3 + 2" e pedaco do enunciado, nao resultado de substituicao
        "3 + 2x = 15",
        "10 = 4 + 3y",
        # listar valores nao e calcular com eles
        "os valores sao 12 15 20",
        "temos 3 4 5 como medidas",
    ],
)
def test_nao_confunde_anuncio_com_conta(passo):
    assert not _resolucao_efetua_alguma_conta([passo]), passo


def test_basta_uma_linha_com_conta():
    passos = ["identifique os valores", "x = 10/2", "x = 5"]

    assert _resolucao_efetua_alguma_conta(passos)


def test_a_conta_pode_estar_na_subformula():
    # Bhaskara: o delta costuma vir como subformula.
    assert _resolucao_efetua_alguma_conta(["D = 25 - 24", "x' = 2 e x'' = 3"])


def test_a_questao_inteira_tambem_olha_a_subformula():
    # O teste acima chama a funcao direto; este confere a ligacao. Aqui a
    # UNICA conta feita esta na subformula -- se a ligacao se perder, uma
    # questao legitima de Bhaskara passa a ser recusada.
    assert not _questao_exatas_sem_calculo_laboratorio(
        questao(
            "Quais as raizes de x^2 - 5x + 6 = 0?",
            ["x' = 2 e x'' = 3", "x' = 1 e x'' = 6", "x' = -1 e x'' = -6", "x' = 0 e x'' = 5"],
            "x = (-b + raiz(D))/(2a)",
            ["D = b^2 - 4ac", "x' = 2 e x'' = 3"],
            subformulas=["D = 25 - 24"],
        ),
        "Matematica",
    )


# --------------------------------------------------------------------------
# a questao inteira: o que mudou de verdade
# --------------------------------------------------------------------------

CALCULOS_LEGITIMOS = [
    ("equacao do 1o grau sem a palavra 'equacao'",
     "Calcule o valor de x em 2x + 5 = 15.", ["5", "10", "3", "7"],
     "ax + b = c", ["2x = 15 - 5", "x = 10/2", "x = 5"]),
    ("media aritmetica",
     "As notas foram 6, 8 e 10. Qual a media?", ["8", "7", "9", "6"],
     "M = (a+b+c)/3", ["M = (6+8+10)/3", "M = 24/3", "M = 8"]),
    ("regra de tres",
     "Se 3 canetas custam 12 reais, quanto custam 7 canetas?", ["28", "21", "36", "14"],
     "x = (a*d)/b", ["x = (12*7)/3", "x = 84/3", "x = 28"]),
    ("razao entre dois valores",
     "Numa turma ha 12 meninas e 18 meninos. Qual a razao entre eles?",
     ["2/3", "3/2", "1/2", "2/1"], "r = a/b", ["r = 12/18", "r = 2/3"]),
    ("fracao do fundamental",
     "Quanto e 3/4 de 200?", ["150", "125", "175", "100"],
     "x = (a/b)*c", ["x = (3/4)*200", "x = 0,75*200", "x = 150"]),
    ("progressao aritmetica",
     "Numa PA o primeiro termo e 3 e a razao e 4. Qual o 6o termo?",
     ["23", "19", "27", "15"], "an = a1 + (n-1)*r",
     ["a6 = 3 + (6-1)*4", "a6 = 3 + 20", "a6 = 23"]),
    ("porcentagem, que a lista antiga ja aceitava",
     "Um produto de R$ 200 tem desconto de 15%. Qual o valor final?",
     ["170", "185", "160", "150"], "P = V - V*d/100",
     ["P = 200 - 200*15/100", "P = 200 - 30", "P = 170"]),
    ("trigonometria",
     "Um observador a 50 metros da base ve o topo a 60 graus. Qual a altura?",
     ["86,6 metros", "90,6 metros", "100 metros", "96,6 metros"],
     "h = d * tan(theta)",
     ["d = 50 m e theta = 60 graus", "h = 50 * tan(60) = 86,6 metros"]),
    ("raiz quadrada",
     "Qual a raiz quadrada da soma de 16 e 9?", ["5", "25", "7", "4"],
     "x = raiz(a+b)", ["x = raiz(16+9)", "x = raiz(25)", "x = 5"]),
]


@pytest.mark.parametrize(
    "rotulo, pergunta, opcoes, formula, passos",
    CALCULOS_LEGITIMOS,
    ids=[c[0] for c in CALCULOS_LEGITIMOS],
)
def test_calculo_legitimo_passa_sem_depender_de_palavra_no_enunciado(
    rotulo, pergunta, opcoes, formula, passos
):
    assert not _questao_exatas_sem_calculo_laboratorio(
        questao(pergunta, opcoes, formula, passos), "Matematica"
    ), rotulo


def test_a_mesma_conta_nao_depende_de_como_o_enunciado_e_escrito():
    # O defeito em uma linha: estas duas sao a mesma questao.
    com_palavra = questao("Resolva a equacao 2x + 5 = 15.", ["5", "10", "3", "7"],
                          "ax + b = c", ["2x = 15 - 5", "x = 10/2", "x = 5"])
    sem_palavra = questao("Calcule o valor de x em 2x + 5 = 15.", ["5", "10", "3", "7"],
                          "ax + b = c", ["2x = 15 - 5", "x = 10/2", "x = 5"])

    assert _questao_exatas_sem_calculo_laboratorio(
        com_palavra, "Matematica"
    ) == _questao_exatas_sem_calculo_laboratorio(sem_palavra, "Matematica")


# --------------------------------------------------------------------------
# a conta tem que aparecer FEITA -- e o que se perderia so removendo a porta
# --------------------------------------------------------------------------


def test_resolucao_que_so_repete_o_enunciado_nao_passa():
    assert _questao_exatas_sem_calculo_laboratorio(
        questao("Calcule o valor de x em 2x + 5 = 15.", ["5", "10", "3", "7"],
                "ax + b = c", ["2x + 5 = 15", "x = 5"]),
        "Matematica",
    )


def test_resolucao_que_so_mostra_o_resultado_nao_passa():
    assert _questao_exatas_sem_calculo_laboratorio(
        questao("Calcule o valor de x em 2x + 5 = 15.", ["5", "10", "3", "7"],
                "ax + b = c", ["x = 5", "x = 5"]),
        "Matematica",
    )


def test_resolucao_so_com_palavras_nao_passa():
    assert _questao_exatas_sem_calculo_laboratorio(
        questao("Calcule o valor de x em 2x + 5 = 15.", ["5", "10", "3", "7"],
                "ax + b = c", ["isole o x", "aplique a formula", "chegue ao resultado"]),
        "Matematica",
    )


@pytest.mark.parametrize(
    "rotulo, alterado",
    [
        ("sem formula", {"formula": ""}),
        ("formula sem igualdade", {"formula": "dois x mais cinco"}),
        ("enunciado sem dois valores", {"pergunta": "Qual o valor de x?"}),
        ("alternativas sem numeros", {"opcoes": ["cinco", "dez", "tres", "sete"]}),
    ],
)
def test_a_conta_feita_nao_salva_questao_que_falha_antes(rotulo, alterado):
    # Esta e a ULTIMA porta, nao a unica.
    dados = questao("Calcule o valor de x em 2x + 5 = 15.", ["5", "10", "3", "7"],
                    "ax + b = c", ["2x = 15 - 5", "x = 10/2", "x = 5"])
    dados.update(alterado)

    assert _questao_exatas_sem_calculo_laboratorio(dados, "Matematica"), rotulo
