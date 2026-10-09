"""Frase em português com tema em inglês continua sendo português.

Sobra do item 5.1 do relatório de QA de 23/09/2026, fechada em 28/09: duas
palavras ("possiveis" e "evidencia") ainda chegavam sem acento em alguns
textos do banco. O motivo não era o dicionário -- era o detector de idioma.

As questões de Inglês são escritas em português com o tema em inglês no meio:
"Qual raciocinio sobre future (will/going to) sustenta melhor a escolha?".
Bastavam dois marcadores ingleses ("will" e "to") para o dicionário desistir
do texto INTEIRO, e a frase perdia todos os acentos de uma vez.

Agora o português tem voto: só é inglês quando os marcadores ingleses superam
as palavras que não existem em inglês. Medido no banco: 250 textos voltaram a
receber acento, e nenhum texto em inglês mudou.
"""

from __future__ import annotations

import pytest

from core.text_cleanup import aplicar_acentos_pt, texto_parece_ingles

# Frases reais dos moldes de Inglês do RPG e do Escape Room.
PORTUGUES_COM_TEMA_EM_INGLES = [
    ("Escolher uma conclusao sobre verbo to be que contradiz as evidencias descritas na cena.",
     "Escolher uma conclusão sobre verbo to be que contradiz as evidências descritas na cena."),
    ("Qual raciocinio sobre future (will/going to) sustenta melhor a escolha?",
     "Qual raciocínio sobre future (will/going to) sustenta melhor a escolha?"),
    ("Antes de abrir a proxima passagem, a equipe revela duas interpretacoes possiveis para o mesmo sinal.",
     "Antes de abrir a próxima passagem, a equipe revela duas interpretações possíveis para o mesmo sinal."),
    ("O guardiao de a coded dialogue aceita apenas uma explicacao ligada ao que foi observado.",
     "O guardião de a coded dialogue aceita apenas uma explicação ligada ao que foi observado."),
    ("Desconsiderar o conceito de verbo to be e decidir apenas pela aparencia do objeto observado.",
     "Desconsiderar o conceito de verbo to be e decidir apenas pela aparência do objeto observado."),
]

INGLES_DE_VERDADE = [
    "The simple past of 'eat' is 'ate'. She ate lunch at school.",
    "Which word is a false cognate for Portuguese speakers?",
    "In the passage, what is the main purpose of the author's description?",
    # Inglês que CITA uma palavra portuguesa: continua inglês, senão o
    # dicionário transformaria "ate" (do verbo eat) em "até".
    "The Portuguese word 'para' means 'for' in English.",
    "The idea of 'atualmente' is expressed in English by 'currently' or 'nowadays'.",
]


@pytest.mark.parametrize(("bruto", "esperado"), PORTUGUES_COM_TEMA_EM_INGLES)
def test_portugues_com_tema_em_ingles_recebe_acento(bruto, esperado):
    assert not texto_parece_ingles(bruto)
    assert aplicar_acentos_pt(bruto) == esperado


@pytest.mark.parametrize("frase", INGLES_DE_VERDADE)
def test_ingles_continua_intocado(frase):
    assert texto_parece_ingles(frase)
    assert aplicar_acentos_pt(frase) == frase


def test_o_tema_em_ingles_nao_e_traduzido_nem_acentuado():
    # O pedaço em inglês fica exatamente como estava; só o português ao redor
    # muda.
    saida = aplicar_acentos_pt(
        "Escolher uma conclusao sobre there is/are que contradiz as evidencias descritas na cena."
    )
    assert "there is/are" in saida
    assert "conclusão" in saida and "evidências" in saida


def test_limite_conhecido_frase_curta_com_tema_de_tres_marcadores():
    # "there is/are" sozinho já traz três marcadores ingleses (there, is,
    # are). Numa frase curta em português eles superam as palavras que não
    # existem em inglês, e o texto continua tratado como inglês -- ou seja,
    # sem acento. Os moldes reais do banco são mais longos e não caem aqui
    # (medido em 28/09/2026: 250 textos corrigidos, nenhum inglês mexido).
    # Fica registrado para não parecer descuido, e para quem mexer na regra
    # saber o que está trocando.
    assert texto_parece_ingles("A licao sobre there is/are pede atencao ao numero do substantivo.")


def test_portugues_ja_acentuado_tambem_conta_como_portugues():
    # A comparação tira o acento dos dois lados: "são" conta igual a "sao".
    # Sem isso, todo texto já acentuado perderia os votos em português.
    assert not texto_parece_ingles("Estas são as frases sobre the verb to be que a prova pede.")


def test_frase_curta_em_ingles_continua_sendo_ingles():
    # Dois marcadores bastam quando não há português nenhum: era o caso que
    # a regra dos dois marcadores existe para pegar.
    assert texto_parece_ingles("She ate lunch at school")


def test_uma_palavra_inglesa_solta_nao_faz_a_frase_virar_ingles():
    assert not texto_parece_ingles("A prova de ingles pede o verbo to be na resposta")
