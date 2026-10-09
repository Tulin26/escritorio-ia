"""A letra citada na explicacao do Oraculo/Escape Room/RPG/Laboratorio tem
de ser a da alternativa exibida -- mesmo bug do ENEM (ver
tests/test_letra_citada_no_enem.py), so que aqui a questao usa o formato
"opcoes" (lista simples) + "correta" (indice inteiro), gerado por
`services.ia.questoes.embaralhar_opcoes_questao` e usado por Oraculo,
Escape Room, RPG e Laboratorio de Exatas.

Relatorio de QA de 23/09/2026, achado 3.1: 29 ocorrencias, a maioria fora
do ENEM/Batalha contra Chefes -- por exemplo Escape Room/Quimica
(08:58:14, "a alternativa C descreve exatamente o processo ionico" quando
a certa era a D) e Oraculo/Filosofia Q21, que vazou um indice interno de
array ("Somente a alternativa B (indice 1) descreve corretamente...").
"""
from __future__ import annotations

import itertools

import services.ia.questoes as questoes_mod
from services.ia.questoes import embaralhar_opcoes_questao

LETRAS = "ABCD"


def questao_base(frase_final: str = "A alternativa C descreve exatamente o processo.") -> dict:
    return {
        "pergunta": "Qual das alternativas descreve corretamente a ligacao ionica?",
        "opcoes": [
            "A ligacao ionica ocorre entre dois nao-metais",
            "Ha compartilhamento de eletrons entre os atomos",
            "Ha transferencia de eletrons e atracao eletrostatica entre ions",
            "Ocorre apenas em metais puros",
        ],
        "correta": 2,
        "explicacao": [
            {"tipo": "resultado", "conteudo": frase_final},
        ],
    }


def na_ordem(ordem):
    def embaralhar(itens):
        itens[:] = [itens[i] for i in ordem]

    return embaralhar


def letra_da_certa(questao: dict) -> str:
    return LETRAS[questao["correta"]]


def test_a_letra_acompanha_a_certa_em_todas_as_ordens(monkeypatch):
    for ordem in itertools.permutations(range(4)):
        monkeypatch.setattr(questoes_mod.random, "shuffle", na_ordem(ordem))

        questao = embaralhar_opcoes_questao(questao_base())

        esperado = f"A alternativa {letra_da_certa(questao)} descreve exatamente o processo."
        assert questao["explicacao"][-1]["conteudo"] == esperado, ordem


def test_reproduz_o_caso_do_escape_room_quimica(monkeypatch):
    """A correta comeca na posicao C (indice 2) e vai parar na D (indice 3)."""
    monkeypatch.setattr(questoes_mod.random, "shuffle", na_ordem((0, 1, 3, 2)))

    questao = embaralhar_opcoes_questao(questao_base())

    assert letra_da_certa(questao) == "D"
    assert questao["explicacao"][-1]["conteudo"] == "A alternativa D descreve exatamente o processo."


def test_os_passos_de_resolucao_tambem_acompanham(monkeypatch):
    monkeypatch.setattr(questoes_mod.random, "shuffle", na_ordem((3, 2, 1, 0)))
    original = questao_base()
    original["passos_resolucao"] = [
        {"titulo": "1o Passo", "conteudo": "Compara as ligacoes."},
        {"titulo": "Resultado Final", "conteudo": "Portanto, a alternativa C esta correta.", "final": True},
    ]

    questao = embaralhar_opcoes_questao(original)

    assert questao["passos_resolucao"][-1]["conteudo"] == "Portanto, a alternativa B esta correta."


def test_indice_interno_nao_e_a_causa_mas_a_troca_ainda_funciona(monkeypatch):
    """Caso Oraculo/Filosofia Q21: a explicacao vazava "(indice 1)" junto da
    letra. A troca de letra deve funcionar igual; o vazamento do indice em
    si e um problema de prompt, fora do escopo deste modulo."""
    monkeypatch.setattr(questoes_mod.random, "shuffle", na_ordem((3, 2, 1, 0)))
    original = questao_base("Somente a alternativa C (indice 2) descreve corretamente o processo.")

    questao = embaralhar_opcoes_questao(original)

    assert letra_da_certa(questao) == "B"
    assert questao["explicacao"][-1]["conteudo"] == (
        "Somente a alternativa B (indice 2) descreve corretamente o processo."
    )


def test_enunciado_que_usa_alternativa_na_historia_nao_e_mexido(monkeypatch):
    monkeypatch.setattr(questoes_mod.random, "shuffle", na_ordem((3, 2, 1, 0)))
    original = questao_base("A alternativa C do plano e a mais barata.")
    original["pergunta"] = (
        "A prefeitura avalia a alternativa A (onibus) e a alternativa B (metro). "
        + original["pergunta"]
    )

    questao = embaralhar_opcoes_questao(dict(original))

    assert questao["explicacao"] == original["explicacao"]


def test_traducao_pareada_continua_alinhada_com_a_letra_trocada(monkeypatch):
    monkeypatch.setattr(questoes_mod.random, "shuffle", na_ordem((0, 1, 3, 2)))
    original = questao_base()
    original["opcoes_traducao"] = ["nonmetal bond", "shared electrons", "ionic bond", "pure metal"]

    questao = embaralhar_opcoes_questao(original)

    idx = questao["correta"]
    assert questao["opcoes_traducao"][idx] == "ionic bond"
    assert questao["explicacao"][-1]["conteudo"] == "A alternativa D descreve exatamente o processo."
