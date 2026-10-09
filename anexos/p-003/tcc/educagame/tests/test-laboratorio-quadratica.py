"""Regressao dos enunciados de equacao do 2o grau do Laboratorio de Exatas.

Os defeitos abaixo passavam pela suite porque a resposta sempre estava
certa -- o que estava errado era o TEXTO ao redor dela.
"""

from __future__ import annotations

import re

import pytest

from services.banks.laboratorio import _matematica_equacao_2o_grau

# Cada caso do gerador aparece a cada 20 indices; 20 casos cobrem a lista toda.
INDICES = [i * 20 for i in range(20)]


def _questoes():
    return [_matematica_equacao_2o_grau(i, i // 20 + 1) for i in INDICES]


def _raizes_da_opcao(opcao: str) -> tuple[int, ...]:
    return tuple(sorted(int(n) for n in re.findall(r"-?\d+", opcao)))


def _coeficientes(pergunta: str) -> tuple[int, int, int]:
    """Le a, b e c do enunciado, aceitando "2x^2 - 14x + 12" com ou sem "= 0"."""
    corpo = re.search(r"(-?\d*)x\^2\s*([+-]\s*\d+)x\s*([+-]\s*\d+)", pergunta)
    assert corpo, f"nao achei a quadratica em: {pergunta}"
    a_txt = corpo.group(1)
    a = int(a_txt) if a_txt not in ("", "-") else (-1 if a_txt == "-" else 1)
    b = int(corpo.group(2).replace(" ", ""))
    c = int(corpo.group(3).replace(" ", ""))
    return a, b, c


@pytest.mark.parametrize("indice", INDICES)
def test_alternativas_nao_sao_equivalentes(indice):
    # Na raiz dupla os distratores (x1+1, x2) e (x1, x2+1) viravam o mesmo
    # par em ordem trocada: "x' = 4 e x'' = 3" e "x' = 3 e x'' = 4" na
    # mesma questao.
    q = _matematica_equacao_2o_grau(indice, indice // 20 + 1)
    opcoes = q["opcoes"]
    conjuntos = [_raizes_da_opcao(o) for o in opcoes]

    assert len(set(opcoes)) == len(opcoes), f"texto repetido: {opcoes}"
    assert len(set(conjuntos)) == len(conjuntos), (
        f"duas alternativas com as mesmas raizes: {opcoes}"
    )


@pytest.mark.parametrize("indice", INDICES)
def test_resposta_bate_com_a_equacao_do_enunciado(indice):
    q = _matematica_equacao_2o_grau(indice, indice // 20 + 1)
    a, b, c = _coeficientes(q["pergunta"])
    x1, x2 = _raizes_da_opcao(q["opcoes"][q["correta"]])

    # Soma e produto das raizes: x1 + x2 = -b/a e x1*x2 = c/a
    assert a * (x1 + x2) == -b, q["pergunta"]
    assert a * x1 * x2 == c, q["pergunta"]


@pytest.mark.parametrize("indice", INDICES)
def test_texto_do_grafico_combina_com_as_raizes(indice):
    # "cruza o eixo x" saia para x^2-6x+9=0, que tem raiz dupla e apenas
    # tangencia; e "toca o eixo x" saia para 3x^2-30x+48=0, de raizes
    # distintas. O verbo vinha da posicao na lista, nao das raizes.
    q = _matematica_equacao_2o_grau(indice, indice // 20 + 1)
    pergunta = q["pergunta"].lower()
    x1, x2 = _raizes_da_opcao(q["opcoes"][q["correta"]])
    raiz_dupla = x1 == x2

    if "tangencia" in pergunta or "toca o eixo" in pergunta:
        assert raiz_dupla, f"diz tangencia/toca mas as raizes diferem: {q['pergunta']}"
    if "cruza o eixo" in pergunta:
        assert not raiz_dupla, f"diz cruza mas a raiz e dupla: {q['pergunta']}"


@pytest.mark.parametrize("indice", INDICES)
def test_grandeza_modelada_nao_recebe_equacao_igualada_a_zero(indice):
    # "A altura de um projetil e modelada por 2x^2-14x+12 = 0" -- uma
    # grandeza descrita por algo que ja vale zero. Quem descreve altura,
    # largura ou area precisa da EXPRESSAO, sem "= 0".
    q = _matematica_equacao_2o_grau(indice, indice // 20 + 1)
    pergunta = q["pergunta"]
    trecho_antes_do_igual = pergunta.split("= 0")[0].lower()

    if "= 0" in pergunta:
        for grandeza in ("a altura de", "a largura de", "e dada por", "e descrita pela"):
            assert grandeza not in trecho_antes_do_igual, (
                f"grandeza modelada por equacao ja igualada a zero: {pergunta}"
            )
