"""Par ordenado não é par de raízes.

Visto na investigação de 14/09/2026: a normalização apaga alternativa
"equivalente", e tratava (3, 4) e (4, 3) como o mesmo par de raízes. Nas 20
questões de vértice do Laboratório e nas 20 de sistemas lineares do banco do
Ensino Médio, uma alternativa sumia -- em 22 delas a CERTA, e outra passava a
ser marcada como certa: o vértice de (x - 3)^2 + 4 chegava ao aluno com
"(-3, 4)" como resposta.

Quem decide se o par entre parênteses é raiz ou ponto é a PERGUNTA: o mesmo
"(0.5, -3)" é conjunto em "Encontre as raízes" (ver
tests/test_normalizacao_alternativas.py) e ponto num vértice.
"""
from __future__ import annotations

import contextlib
import io
import re

import pytest

from core.answer_equivalence import (
    conjunto_raizes_quadraticas,
    respostas_equivalentes,
    tem_opcoes_equivalentes,
)
from services.ia.normalizacao import normalizar_payload_questao
from services.ia.validacao import validar_questao_gerada

VERTICE = ["(-3, 4)", "(4, 3)", "(3, 4)", "(3, -4)"]
PERGUNTA_VERTICE = "A função f(x) = (x - 3)^2 + 4 tem vértice em qual ponto?"
_PAR = re.compile(r"^\(\s*-?\d+(?:[.,]\d+)?\s*[,;]\s*-?\d+(?:[.,]\d+)?\s*\)$")


def _normalizar(questao: dict) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        return normalizar_payload_questao(dict(questao))


def _questoes_com_par_nas_alternativas() -> list[dict]:
    import services.banks.laboratorio as lab
    from services.banks.em import listar_questoes_em

    questoes = lab.listar_questoes_laboratorio("Matematica", "EM") + listar_questoes_em("Matematica")
    return [q for q in questoes if any(_PAR.match(str(o).strip()) for o in q.get("opcoes") or [])]


def test_coordenadas_trocadas_sao_alternativas_diferentes():
    assert tem_opcoes_equivalentes(VERTICE, PERGUNTA_VERTICE) is False


@pytest.mark.parametrize("texto", ["(3, 4)", "V = (3, 4)", "P(2; -1)"])
def test_sem_pergunta_o_par_entre_parenteses_fica_ordenado(texto):
    assert conjunto_raizes_quadraticas(texto) is None


@pytest.mark.parametrize(
    "pergunta",
    [
        PERGUNTA_VERTICE,
        "Qual é a solução do sistema formado pelas equações 2x + y = 7 e x - y = 2?",
        "Qual é o ponto médio do segmento de extremos A(1, 2) e B(5, 4)?",
        "Qual é a coordenada do centro da circunferência?",
        # fala em raízes, mas pergunta por um ponto
        "A parábola de raízes 1 e 5 tem vértice em qual ponto?",
    ],
)
def test_pergunta_de_ponto_vertice_ou_sistema_mantem_a_ordem(pergunta):
    """O Laboratório corrige com respostas_equivalentes: marcar (4, 3) quando
    a resposta é (3, 4) não pode contar como acerto."""
    assert not respostas_equivalentes("(4, 3)", "(3, 4)", pergunta)


@pytest.mark.parametrize(
    "pergunta",
    [
        "Encontre as raizes.",
        "Quais são as raízes de 2x^2 + 5x - 3 = 0?",
        "Quais são os zeros da função?",
    ],
)
def test_pergunta_de_raiz_trata_o_par_como_conjunto(pergunta):
    """O par obrigatório: raiz é conjunto, e a ordem não importa."""
    assert respostas_equivalentes("(0.5, -3)", "(-3, 0.5)", pergunta)


@pytest.mark.parametrize(
    "a, b",
    [
        ("x' = -3 e x'' = -2", "x' = -2 e x'' = -3"),
        ("-3 e -2", "-2 e -3"),
        ("{-1, 5}", "{5, -1}"),
        ("raízes (-1, 5)", "raízes (5, -1)"),
    ],
)
def test_raizes_escritas_como_raiz_continuam_equivalentes_sem_pergunta(a, b):
    assert respostas_equivalentes(a, b)


def test_nenhuma_questao_de_par_perde_alternativa_nem_troca_a_certa():
    questoes = _questoes_com_par_nas_alternativas()
    # o vértice, o ponto médio e os sistemas lineares estão entre elas
    assert len(questoes) >= 40

    for questao in questoes:
        normalizada = _normalizar(questao)
        certa_antes = str(questao["opcoes"][int(questao["correta"])]).strip()
        certa_depois = str(normalizada["opcoes"][int(normalizada["correta"])]).strip()
        assert len(normalizada["opcoes"]) == len(questao["opcoes"]), questao["pergunta"]
        assert certa_depois == certa_antes, questao["pergunta"]


def test_o_validador_ainda_recusa_raizes_repetidas_entre_parenteses():
    """A pergunta precisa chegar ao validador: sem ela, o par entre
    parênteses ficaria ordenado e as raízes repetidas passariam."""
    dados = {
        "pergunta": "Quais são as raízes de 2x^2 + 5x - 3 = 0?",
        "opcoes": ["(0.5, -3)", "(-1, 1.5)", "(-3, 0.5)", "(1, -1.5)"],
        "correta": 0,
    }

    with contextlib.redirect_stdout(io.StringIO()):
        _, aceita, motivo = validar_questao_gerada(dados, "Matematica", "laboratorio")

    assert not aceita
    assert motivo == "opcoes-equivalentes"


def test_o_laboratorio_aceita_a_questao_de_vertice_do_banco():
    import services.banks.laboratorio as lab

    vertice = next(
        q for q in lab.listar_questoes_laboratorio("Matematica", "EM") if "vertice" in q["pergunta"].lower()
    )
    assert len({str(o) for o in vertice["opcoes"]}) == 4

    with contextlib.redirect_stdout(io.StringIO()):
        _, aceita, motivo = validar_questao_gerada(dict(vertice), "Matematica", "laboratorio")

    assert aceita, motivo
