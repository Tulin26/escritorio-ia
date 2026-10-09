"""A alternativa de Fisica/Quimica carrega uma unidade de verdade?

O Laboratorio exige conta, e uma conta de grandeza fisica termina com uma
unidade. Esta checagem confere isso nas alternativas.

O defeito que estes testes prendem: a unidade era procurada como PEDACO DE
TEXTO nas alternativas juntas, e a lista de Fisica tinha letras soltas --
"n", "j", "v", "a", "w". Nas duas direcoes ao mesmo tempo:

    "12 bananas"  passava   (tem a letra "a")
    "80 km/h"     era barrado (nao tem nenhuma daquelas letras)

Em Quimica, "l" na lista fazia passar "azul", "cristal", "sal".
"""

from __future__ import annotations

import pytest

from services.ia.validacao import _questao_exatas_sem_calculo_laboratorio

PERGUNTA_FISICA = "Um corpo de 4 kg sofre aceleracao de 3 m/s2. Qual o valor?"
PERGUNTA_VELOCIDADE = "Um carro percorre 240 km em 3 h. Qual a velocidade media?"
PERGUNTA_QUIMICA = "Dissolvem-se 20 g de sal em 4 L de agua. Qual a concentracao?"


def questao(pergunta, opcoes, formula="F = m * a", passos=("F = 4 * 3", "F = 12")):
    return {
        "pergunta": pergunta,
        "opcoes": opcoes,
        "formula": formula,
        "subformulas": [],
        "passos_resolucao": [{"conteudo": p} for p in passos],
    }


def quatro(unidade: str) -> list[str]:
    return [f"12 {unidade}", f"7 {unidade}", f"1 {unidade}", f"10 {unidade}"]


# --------------------------------------------------------------------------
# unidade de verdade: tem que passar
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unidade",
    [
        "m/s", "km/h", "cm/s", "m/s2",          # velocidade e aceleracao
        "m", "cm", "mm", "km",                   # comprimento
        "s", "min", "h",                         # tempo
        "kg", "g", "mg",                         # massa
        "N", "kN",                               # forca
        "J", "kJ", "cal",                        # energia
        "W", "kW",                               # potencia
        "V", "A", "ohm", "Ω",               # eletricidade
        "Pa", "atm",                             # pressao
        "°C", "K",                          # temperatura
        "g/cm3", "kg/m3",                        # densidade
        "L", "mL", "m3",                         # volume
    ],
)
def test_unidade_de_fisica_e_aceita(unidade):
    # km/h e o caso que motivou a correcao: e a unidade de velocidade mais
    # usada no Ensino Medio e era recusada.
    assert not _questao_exatas_sem_calculo_laboratorio(
        questao(PERGUNTA_VELOCIDADE, quatro(unidade)), "Fisica"
    ), unidade


@pytest.mark.parametrize(
    "unidade",
    ["mol", "mol/L", "g/L", "g/mL", "g/mol", "g", "kg", "L", "mL", "kJ", "cal", "atm", "%"],
)
def test_unidade_de_quimica_e_aceita(unidade):
    assert not _questao_exatas_sem_calculo_laboratorio(
        questao(PERGUNTA_QUIMICA, quatro(unidade), "C = m/V"), "Quimica"
    ), unidade


@pytest.mark.parametrize(
    "opcoes",
    [
        ["20m/s", "15m/s", "25m/s", "10m/s"],           # colada no numero
        ["1,5 m/s", "2,5 m/s", "3,5 m/s", "4,5 m/s"],   # decimal com virgula
        ["58,5 kg", "40 kg", "18 kg", "1 kg"],          # decimal, unidade simples
        ["12 M/S", "7 M/S", "1 M/S", "10 M/S"],         # maiuscula
        ["3 g/cm3", "2 g/cm3", "8 g/cm3", "1 g/cm3"],   # digito no fim
        # a IA escreve o expoente dos dois jeitos, e "g/cm3" passava
        # enquanto "g/cm³" era recusado
        ["3 g/cm³", "2 g/cm³", "8 g/cm³", "1 g/cm³"],
        ["12 m/s²", "7 m/s²", "1 m/s²", "10 m/s²"],
        ["5 cm²", "8 cm²", "2 cm²", "1 cm²"],
        ["5 m³", "8 m³", "2 m³", "1 m³"],
    ],
)
def test_a_forma_de_escrever_a_unidade_nao_importa(opcoes):
    assert not _questao_exatas_sem_calculo_laboratorio(
        questao(PERGUNTA_VELOCIDADE, opcoes), "Fisica"
    ), opcoes


def test_unidade_de_quimica_nao_vale_para_fisica():
    # g/mol e massa molar: nao aparece em questao de Fisica. As listas sao
    # separadas de proposito, e este teste existe porque eu mesmo escorreguei
    # nisso ao escrever os casos acima.
    assert _questao_exatas_sem_calculo_laboratorio(
        questao(PERGUNTA_VELOCIDADE, quatro("g/mol")), "Fisica"
    )


def test_ph_pode_ser_numero_puro():
    # pH e adimensional por definicao: cobrar unidade dele seria cobrar o que
    # nao existe -- e o prompt do Laboratorio pede pH como tema de Quimica.
    assert not _questao_exatas_sem_calculo_laboratorio(
        questao(
            "Uma solucao a 25 graus tem concentracao de 0,001 mol/L de H+. Qual o pH?",
            ["3", "7", "11", "1"],
            "pH = -log[H+]",
            passos=("pH = -log(0,001)", "pH = 3"),
        ),
        "Quimica",
    )


# --------------------------------------------------------------------------
# a metade que importa: afrouxar nao pode deixar passar lixo
# --------------------------------------------------------------------------


@pytest.mark.parametrize("inventada", ["bananas", "cavalos", "caixas", "pessoas", "vezes"])
def test_unidade_inventada_nao_passa_em_fisica(inventada):
    # Todas essas continham alguma das letras soltas da lista antiga.
    assert _questao_exatas_sem_calculo_laboratorio(
        questao(PERGUNTA_FISICA, quatro(inventada)), "Fisica"
    ), inventada


@pytest.mark.parametrize("inventada", ["azul", "cristais", "frascos", "gotas"])
def test_unidade_inventada_nao_passa_em_quimica(inventada):
    # "l" na lista antiga fazia qualquer palavra com L passar.
    assert _questao_exatas_sem_calculo_laboratorio(
        questao(PERGUNTA_QUIMICA, quatro(inventada), "C = m/V"), "Quimica"
    ), inventada


@pytest.mark.parametrize("materia, formula", [("Fisica", "F = m * a"), ("Quimica", "C = m/V")])
def test_alternativa_sem_grandeza_nenhuma_nao_passa(materia, formula):
    pergunta = PERGUNTA_FISICA if materia == "Fisica" else PERGUNTA_QUIMICA

    assert _questao_exatas_sem_calculo_laboratorio(
        questao(pergunta, ["12", "7", "1", "10"], formula), materia
    )


def test_alternativa_que_e_texto_nao_passa():
    assert _questao_exatas_sem_calculo_laboratorio(
        questao(PERGUNTA_FISICA, ["a maior de todas 1", "a menor 2", "a media 3", "nenhuma 4"]),
        "Fisica",
    )


# --------------------------------------------------------------------------
# as portas numericas continuam valendo antes da unidade
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rotulo, alterado",
    [
        ("sem formula", {"formula": ""}),
        ("formula sem igualdade", {"formula": "massa vezes aceleracao"}),
        ("enunciado sem dois valores", {"pergunta": "Qual a forca resultante?"}),
        ("passos sem conta", {"passos_resolucao": [{"conteudo": "aplique"}, {"conteudo": "pronto"}]}),
    ],
)
def test_unidade_certa_nao_salva_questao_sem_calculo(rotulo, alterado):
    # A unidade e a ULTIMA porta, nao a unica: alternativa em newton nao
    # transforma questao teorica em questao de laboratorio.
    dados = questao(PERGUNTA_FISICA, quatro("N"))
    dados.update(alterado)

    assert _questao_exatas_sem_calculo_laboratorio(dados, "Fisica"), rotulo
