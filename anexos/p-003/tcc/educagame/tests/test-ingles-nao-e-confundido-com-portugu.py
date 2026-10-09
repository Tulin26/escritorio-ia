"""Inglês legítimo deixa de ser confundido com português.

MELHORIA: `_texto_parece_portugues` guarda ~30 marcadores e casa por `any` —
uma palavra basta. Todos são inequívocos, **menos um**: `"observe"` também é
palavra inglesa, e das mais comuns em instrução pedagógica ("Observe the verb
form", "Observe that the adjective is short").

O estrago não era recusar a questão, era pior: quando o campo principal
"parecia português", `_normalizar_resposta_ingles` **descartava a resposta
inteira da IA** e devolvia a do banco offline — em silêncio, sem passar por
`_motivo_rejeicao`, sem aparecer no log. Não havia como notar olhando os
motivos de rejeição, porque nunca houve rejeição.

Atinge os **quatro** modos que geram Inglês pela IA — Treino, Oráculo, Escape
Room e RPG —, porque os quatro passam por `invocar_enigma`. O Laboratório
não: só tem exatas.

A correção não remove o marcador (português com "observe" tem de continuar
sendo pego). Ele passa a exigir companhia: uma palavra que **não existe em
inglês**. Por isso `"do"`, `"no"`, `"a"`, `"as"`, `"e"` e `"com"` ficaram de
fora da lista de reforço — todas são palavras inglesas válidas.

Nota histórica: a pendência registrada dizia que o problema do Inglês era a
regra dos 4 caracteres de `_texto_menciona_opcao`, que rejeitaria metade dos
formatos. Medido de novo aqui, com payload completo pela cascata: os seis
formatos passam. Aquilo foi resolvido quando
`_explicacao_aponta_para_outra_alternativa` deixou de cobrar prova e passou a
cobrar contradição. A nota é que estava velha.
"""

from __future__ import annotations

import pytest

from services.ia.enigma import (
    _motivo_rejeicao,
    _normalizar_resposta_ingles,
    _texto_parece_portugues,
)


def payload_ingles(opcoes, correta, explicacao):
    """O formato completo que a IA devolve para Inglês."""
    return {
        "enigma": "A riddle in English.",
        "enigma_traducao": "Um enigma em portugues.",
        "pergunta": "Choose the correct option.",
        "pergunta_traducao": "Escolha a alternativa correta.",
        "opcoes": opcoes,
        "opcoes_traducao": ["a", "b", "c", "d"],
        "correta": correta,
        "explicacao": [{"tipo": "texto", "conteudo": explicacao}],
        "explicacao_traducao": [{"tipo": "texto", "conteudo": "Explicacao em portugues."}],
        "passos_resolucao": [{"titulo": "Step 1", "conteudo": "Look at the subject."}],
        "passos_resolucao_traducao": [{"titulo": "Passo 1", "conteudo": "Olhe o sujeito."}],
    }


# ====================== INGLÊS NÃO É PORTUGUÊS ======================


@pytest.mark.parametrize(
    "frase",
    [
        "Observe the verb form before choosing.",
        "Observe that the adjective is short.",
        "Please observe the difference between the two tenses.",
        "Observe how the preposition changes the meaning.",
        "Observe a pattern in the irregular verbs.",
    ],
)
def test_observe_em_ingles_nao_e_portugues(frase):
    """Era o único marcador da lista que também é palavra inglesa — e das
    mais comuns em instrução pedagógica."""
    assert not _texto_parece_portugues(frase)


@pytest.mark.parametrize(
    "frase",
    [
        "The past tense of go is went.",
        "Read the sentence and choose the best option.",
        "Note that 'she' requires the third person singular.",
        "The context of the sentence shows a past action.",
        "This is an alternative way to express the same idea.",
        "Use the preposition 'at' when talking about a place.",
        "Short adjectives form the comparative by adding -er.",
        "A library is a place where you borrow books.",
    ],
)
def test_ingles_pedagogico_atravessa_limpo(frase):
    """Os outros ~30 marcadores são inequívocos ("alternativa" é
    "alternative" em inglês, "contexto" é "context"). Este teste é a rede
    contra acrescentar um novo marcador ambíguo sem perceber.
    """
    assert not _texto_parece_portugues(frase)


# ====================== PORTUGUÊS CONTINUA SENDO PEGO ======================


@pytest.mark.parametrize(
    "frase",
    [
        "Observe a frase e escolha a alternativa correta.",
        "Observe que o verbo concorda com o sujeito.",
        "Observe cada palavra da oracao.",
        "Observe a palavra destacada na frase.",
        "Observe a frase em ingles.",
    ],
)
def test_portugues_com_observe_continua_sendo_pego(frase):
    """A correção não pode virar buraco: o campo principal do Inglês em
    português tem de continuar caindo para o offline."""
    assert _texto_parece_portugues(frase)


@pytest.mark.parametrize(
    "frase",
    [
        "Qual e a alternativa correta?",
        "Leia a frase e escolha a resposta.",
        "A explicacao mostra o passo a passo.",
        "Traducao do enunciado para o portugues.",
        "Voce deve identificar o contexto.",
    ],
)
def test_portugues_sem_observe_continua_sendo_pego(frase):
    assert _texto_parece_portugues(frase)


def test_observe_sozinho_nao_basta_e_e_essa_a_mudanca():
    """O par exato do defeito: a mesma palavra, os dois idiomas."""
    assert not _texto_parece_portugues("Observe the verb.")
    assert _texto_parece_portugues("Observe o verbo da frase.")


# ====================== O EFEITO NO CAMINHO REAL ======================


def test_a_resposta_da_ia_deixa_de_ser_descartada_em_silencio():
    """O ponto todo. Antes, "Observe the subject" fazia
    `_normalizar_resposta_ingles` jogar fora a resposta inteira da IA e
    devolver a do banco offline — sem passar por `_motivo_rejeicao`, sem
    log, sem sinal nenhum de que aconteceu.
    """
    da_ia = payload_ingles(
        ["She is happy", "She are happy", "She am happy", "She be happy"], 0,
        "Observe the subject: 'she' is third person singular, so the verb becomes 'is'.",
    )

    saida = _normalizar_resposta_ingles(da_ia, "verb to be")

    assert saida["pergunta"] == da_ia["pergunta"], "a resposta da IA foi descartada"


def test_resposta_realmente_em_portugues_ainda_cai_para_o_offline():
    """O par obrigatório: a porta continua existindo para o que ela protege."""
    em_portugues = payload_ingles(["a", "b", "c", "d"], 0, "Explicacao")
    em_portugues["pergunta"] = "Qual e a alternativa correta?"

    saida = _normalizar_resposta_ingles(em_portugues, "verb to be")

    assert saida["pergunta"] != em_portugues["pergunta"], "o português passou"


def test_resposta_incompleta_ainda_cai_para_o_offline():
    incompleta = payload_ingles(["a", "b", "c", "d"], 0, "Explanation")
    del incompleta["passos_resolucao_traducao"]

    saida = _normalizar_resposta_ingles(incompleta, "verb to be")

    assert saida["pergunta"] != incompleta["pergunta"]


# ====================== A PENDÊNCIA ANTIGA, REMEDIDA ======================


@pytest.mark.parametrize(
    "rotulo,opcoes,explicacao",
    [
        ("is/are/am/be", ["is", "are", "am", "be"],
         "The verb to be with she takes the form is."),
        ("frase inteira", ["She is happy", "She are happy", "She am happy", "She be happy"],
         "With she, the correct form of the verb to be is is, so the sentence is She is happy."),
        ("preposicao", ["at school", "in school", "on school", "to school"],
         "We use at with school when talking about the place, so the answer is at school."),
        ("verbo irregular", ["went", "goed", "gone", "going"],
         "The past simple of the irregular verb go is went, not goed."),
        ("comparativo", ["bigger", "more big", "biggest", "most big"],
         "Short adjectives form the comparative with -er, so big becomes bigger."),
        ("vocabulario", ["a place with books", "a bookstore", "a school", "a museum"],
         "A library is a place where you can borrow books, so it is a place with books."),
    ],
)
def test_os_seis_formatos_da_pendencia_antiga_passam(rotulo, opcoes, explicacao):
    """A nota dizia que a regra dos 4 caracteres de `_texto_menciona_opcao`
    rejeitava metade destes. Medido de novo, com payload completo pela
    cascata: os seis passam. Aquilo foi resolvido quando
    `_explicacao_aponta_para_outra_alternativa` deixou de cobrar prova (a
    explicação apontar para UMA alternativa) e passou a cobrar contradição
    (apontar para OUTRA que não a marcada).

    Fica como rede: se alguém voltar a cobrar prova, estes seis caem juntos.
    """
    _, motivo = _motivo_rejeicao(payload_ingles(opcoes, 0, explicacao), "Ingles", "oraculo")

    assert not motivo, f"{rotulo} foi recusado por {motivo}"
