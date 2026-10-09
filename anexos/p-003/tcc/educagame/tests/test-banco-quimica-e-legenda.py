"""Banco de Química do Laboratório e legenda da IA (15/09/2026).

Achados no teste real pelo Chrome e medidos no banco inteiro antes de mexer:
pH de até 45 (só existe de 0 a 14), diluição partindo de 46 mol/L, "Na análise
de uma solução, uma solução…" e "…de uma amostra, uma amostra…" (88 questões),
gás "analisado como solução", "gas" e "diluida" sem acento, "e diluida" sem
verbo. E a legenda que a IA manda como dicionário escrito em texto, ou como
lista, chegando crua à tela.
"""
from __future__ import annotations

import contextlib
import copy
import io
import re

import pytest

import services.banks.laboratorio as lab
from core.text_cleanup import aplicar_acentos_pt
from services.ia.normalizacao import normalizar_payload_questao


def _quimica(tema):
    return [q for q in lab.listar_questoes_laboratorio("Quimica", "EM") if q["tema_usado"] == tema]


def _tela(questao):
    return aplicar_acentos_pt(questao["pergunta"])


# --------------------------------------------------------------------------
# valores possíveis
# --------------------------------------------------------------------------

def test_o_ph_fica_entre_1_e_13_e_a_resposta_e_o_expoente():
    questoes = _quimica("pH")

    assert len(questoes) == 44
    for q in questoes:
        expoente = int(re.search(r"10\^\{-(\d+)\}", q["pergunta"]).group(1))
        assert 1 <= expoente <= 13, q["pergunta"]
        assert q["opcoes"][q["correta"]] == str(expoente), q["pergunta"]


def test_o_ph_nao_repete_a_pergunta_e_explica_o_volume():
    """Com só 13 valores de pH, o volume da amostra é o que diferencia as
    perguntas -- e ele não entra na conta, então o passo precisa dizer isso."""
    questoes = _quimica("pH")
    perguntas = [q["pergunta"] for q in questoes]

    assert len(set(perguntas)) == len(perguntas)
    for q in questoes:
        assert "volume" in q["passos_resolucao"][0]["conteudo"], q["passos_resolucao"][0]


def test_a_diluicao_parte_de_uma_concentracao_possivel():
    for q in _quimica("diluicao"):
        inicial = float(re.search(r"(\d+(?:[.,]\d+)?)\s*mol/L", q["pergunta"]).group(1).replace(",", "."))
        assert 1 <= inicial <= 6, q["pergunta"]


# --------------------------------------------------------------------------
# texto da pergunta
# --------------------------------------------------------------------------

@pytest.mark.parametrize("sujeito", ["uma solução, uma solução", "uma amostra, uma amostra"])
def test_o_prefixo_nao_repete_o_sujeito(sujeito):
    for materia, serie in (("Quimica", "EM"), ("Ciencias", "EF")):
        for q in lab.listar_questoes_laboratorio(materia, serie):
            assert sujeito not in _tela(q).lower(), q["pergunta"]


def test_o_gas_nao_e_analisado_como_solucao_e_tem_acento():
    for q in _quimica("gases ideais"):
        tela = _tela(q)
        assert "análise de uma solução" not in tela, tela
        assert "gás" in tela and "há?" in tela, tela


def test_a_diluicao_tem_verbo_e_acento():
    for q in _quimica("diluicao"):
        tela = _tela(q)
        assert "foi diluída até" in tela, tela


def test_o_prefixo_continua_onde_combina():
    """O par: o prefixo só sai quando repete o sujeito ou não combina."""
    quimica = [_tela(q) for q in lab.listar_questoes_laboratorio("Quimica", "EM")]
    # a densidade trocou de prefixo, e não perdeu o prefixo
    assert any(p.startswith("Em um controle de qualidade, uma amostra tem massa") for p in quimica)
    assert any(p.startswith("Em uma bancada de laboratório,") for p in quimica)

    fisica = [q["pergunta"] for q in lab.listar_questoes_laboratorio("Fisica", "EM")]
    assert any(p.startswith("Em um experimento escolar,") for p in fisica)
    assert any(p.startswith("Na revisao de grandezas fisicas,") for p in fisica)


def test_nenhuma_pergunta_de_quimica_se_repete():
    perguntas = [q["pergunta"] for q in lab.listar_questoes_laboratorio("Quimica", "EM")]

    assert len(set(perguntas)) == len(perguntas)


def test_o_banco_de_quimica_continua_aceito_pelo_laboratorio():
    from services.calculo_service import _desafio_parece_calculo_laboratorio
    from services.ia.validacao import validar_questao_gerada

    for q in lab.listar_questoes_laboratorio("Quimica", "EM"):
        with contextlib.redirect_stdout(io.StringIO()):
            _, aceita, motivo = validar_questao_gerada(copy.deepcopy(q), "Quimica", "laboratorio")
            parece = _desafio_parece_calculo_laboratorio(copy.deepcopy(q), "Quimica")
        assert aceita, (motivo, q["pergunta"])
        assert parece, q["pergunta"]


# --------------------------------------------------------------------------
# legenda da IA
# --------------------------------------------------------------------------

def _legenda(valor):
    with contextlib.redirect_stdout(io.StringIO()):
        questao = normalizar_payload_questao({"pergunta": "p", "opcoes": ["1", "2", "3", "4"], "correta": 0, "legenda_variaveis": valor})
    return questao["legenda_variaveis"]


@pytest.mark.parametrize(
    "valor, esperado",
    [
        ({"P": "potência", "V": "tensão"}, "P: potência; V: tensão"),
        ("{'n': 'quantidade de matéria em mol', 'm': 'massa'}", "n: quantidade de matéria em mol; m: massa"),
        ('{"n": "mol"}', "n: mol"),
        (["a: primeiro termo", "r: razão"], "a: primeiro termo; r: razão"),
        ("['a: primeiro termo', 'r: razão']", "a: primeiro termo; r: razão"),
    ],
)
def test_a_legenda_estruturada_vira_texto(valor, esperado):
    assert _legenda(valor) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "C = concentração; m = massa; V = volume",
        "{P} é a potência",
        "x em [0, 1]",
        "{ nada fechado",
        # o Python lê como CONJUNTO, não como dicionário: continua o texto
        # escrito -- e fora de ordem, para um conjunto convertido de volta
        # ("{1, 2, 3}") não passar por igual
        "{3, 1, 2}",
    ],
)
def test_legenda_em_texto_comum_fica_como_esta(texto):
    assert _legenda(texto) == texto
