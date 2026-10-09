"""A frase do dicionário de acentos só troca palavra inteira.

Visto em 11/09/2026, numa questão de Biologia do Oráculo:

    Qual éstrutura do neurônio recebe os estímulos provenientes de outras células?

A entrada "qual e" -> "qual é" era procurada sem limite de palavra, e casava
com o começo de "Qual estrutura".
"""

from __future__ import annotations

import pytest

from core.text_cleanup import aplicar_acentos_pt


def test_o_caso_da_tela():
    frase = "Qual estrutura do neurônio recebe os estímulos provenientes de outras células?"

    assert aplicar_acentos_pt(frase) == frase


@pytest.mark.parametrize(
    "frase, estragado",
    [
        ("Qual elemento é mais leve?", "élemento"),
        ("Qual especie vive no cerrado?", "éspecie"),
        ("Qual equação descreve o movimento?", "équação"),
        ("O principal estudo do século.", "éstudo"),
        ("Com o objetivo educacional de revisar.", "éducacional"),
        ("Os preços mudaram depois da crise.", "mudarám"),
    ],
)
def test_frase_nao_entra_no_meio_da_palavra(frase, estragado):
    assert estragado not in aplicar_acentos_pt(frase)


@pytest.mark.parametrize(
    "frase, esperado",
    [
        ("Qual e a velocidade?", "Qual é a velocidade?"),
        ("Qual e f(x) para x = 2?", "Qual é f(x) para x = 2?"),
        ("Qual e o valor?", "Qual é o valor?"),
        ("Se a tensão e 12 V, qual e a corrente?", "qual é a corrente?"),
        ("O risco e alto.", "O risco é alto."),
        ("O preço mudara amanhã.", "O preço mudará amanhã."),
        ("apos a aula", "após a aula"),
        ("O objetivo e revisar.", "O objetivo é revisar."),
    ],
)
def test_as_frases_continuam_trocando(frase, esperado):
    assert esperado in aplicar_acentos_pt(frase)


def test_e_entre_dois_nomes_e_conjuncao():
    """Enquanto a entrada era " e a corrente" (sem "qual"), isto virava "A
    tensão é a corrente" -- e um teste daqui chegou a exigir isso. Ali o "e"
    liga duas grandezas: é conjunção."""
    assert aplicar_acentos_pt("A tensão e a corrente") == "A tensão e a corrente"


def test_frase_nao_casa_com_o_fim_de_outra_palavra():
    """"apos " está dentro de "trapos " -- sem limite no começo, viraria "trapós"."""
    assert aplicar_acentos_pt("Juntou os trapos velhos.") == "Juntou os trapos velhos."


@pytest.mark.parametrize(
    "frase",
    [
        # Os dois textos do banco (20 cópias cada) em que a frase " e a nova" /
        # " e sua velocidade" pegava uma CONJUNÇÃO. Antes saía "baseé a nova";
        # com o espaço de volta sairia "base é a nova", que parece certo.
        "O programa priorizou energia, transporte, indústria de base e a nova capital, atraindo capital estrangeiro.",
        "No mesmo meio, quando a frequência de uma onda aumenta e sua velocidade permanece constante.",
        # "principal e" -> "principal é" agia 29 vezes no banco, todas nesta forma.
        "Bacia hidrográfica é a área drenada por um rio principal e seus afluentes.",
    ],
)
def test_conjuncao_no_meio_da_frase_continua_e(frase):
    assert aplicar_acentos_pt(frase) == frase


@pytest.mark.parametrize(
    "frase, esperado",
    [
        ("Qual e a forca resultante?", "Qual é a força resultante?"),
        ("Qual e sua area?", "Qual é sua área?"),
        ("Qual e a velocidade media?", "Qual é a velocidade"),
        ("Qual e o termo geral?", "Qual é o termo geral?"),
    ],
)
def test_na_pergunta_a_frase_continua_acentuando(frase, esperado):
    assert esperado in aplicar_acentos_pt(frase)


def test_forca_fora_da_pergunta_fica_como_esta():
    """"forca" também é a da execução: não pode virar "força" em qualquer lugar."""
    frase = "Tiradentes foi condenado à forca em 1792."

    assert aplicar_acentos_pt(frase) == frase


def test_e_depois_de_ponto_e_conjuncao():
    """Depois de pontuação o "E" começa frase nova: é conjunção, não verbo."""
    frase = "Calcule a tensão. E a corrente, quanto vale?"

    assert aplicar_acentos_pt(frase) == frase
