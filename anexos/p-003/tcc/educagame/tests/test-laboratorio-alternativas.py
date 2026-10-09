"""Nenhuma questao do Laboratorio pode mostrar a mesma alternativa duas vezes.

Varias formulas do banco produzem exatamente o valor da resposta para
certos numeros. Como _opcoes montava [correta, *distratores] sem conferir
nada, a alternativa certa aparecia duas vezes e so uma contava como acerto:

  - "Na sequencia que comeca em r e aumenta de r em r, qual e o 5o termo?"
    O distrator "inicio * posicao" e igual ao 5o termo em TODOS os casos.
  - "Um cubo tem aresta a cm" -- o distrator 6*a^2 e igual a a^3 em a = 6.
  - "Um objeto de m kg tem aceleracao de a" -- (m + a) colide com (m*a - 1).
"""

from __future__ import annotations

import re

import pytest

from services.banks.laboratorio import (
    BANCO_LAB_EF_OFFLINE,
    BANCO_LAB_OFFLINE,
    MATERIAS_LAB_EF_OFFLINE,
    MATERIAS_LAB_OFFLINE,
    _opcoes,
)


def _texto(opcao: str) -> str:
    # Preserva acento e unidade: sao eles que separam "15" de "15 m".
    return re.sub(r"\s+", " ", str(opcao)).strip().rstrip(".")


BANCOS = [
    pytest.param(BANCO_LAB_OFFLINE, MATERIAS_LAB_OFFLINE, id="lab-em"),
    pytest.param(BANCO_LAB_EF_OFFLINE, MATERIAS_LAB_EF_OFFLINE, id="lab-ef"),
]


@pytest.mark.parametrize("banco,materias", BANCOS)
def test_banco_inteiro_sem_alternativa_repetida(banco, materias):
    problemas = []
    for materia in materias:
        for q in banco[materia] or []:
            opcoes = list(q.get("opcoes") or [])
            textos = [_texto(o) for o in opcoes]
            if len(set(textos)) != len(textos):
                problemas.append((materia, q.get("pergunta"), opcoes))

    assert not problemas, f"{len(problemas)} questoes repetem alternativa: {problemas[:3]}"


@pytest.mark.parametrize("banco,materias", BANCOS)
def test_banco_inteiro_com_4_opcoes_e_indice_valido(banco, materias):
    for materia in materias:
        for q in banco[materia] or []:
            opcoes = list(q.get("opcoes") or [])
            correta = q.get("correta")
            assert len(opcoes) == 4, (materia, q.get("pergunta"), opcoes)
            assert isinstance(correta, int) and 0 <= correta < 4, (
                materia,
                q.get("pergunta"),
                correta,
            )


def test_distrator_igual_a_resposta_e_substituido():
    opcoes, correta = _opcoes("216 cm^3", ["36 cm^3", "216 cm^3", "222 cm^3"], "semente")

    assert len(opcoes) == 4
    assert len(set(opcoes)) == 4, opcoes
    assert opcoes[correta] == "216 cm^3"
    # a unidade tem de sobreviver na reposicao
    assert all(o.endswith("cm^3") for o in opcoes), opcoes


def test_distratores_iguais_entre_si_sao_substituidos():
    opcoes, correta = _opcoes("6 N", ["8 N", "5 N", "5 N"], "semente")

    assert len(set(opcoes)) == 4, opcoes
    assert opcoes[correta] == "6 N"


@pytest.mark.parametrize("banco,materias", BANCOS)
def test_nenhuma_alternativa_com_numero_impossivel_de_ler(banco, materias):
    # A PG crescia com razao E posicao ao mesmo tempo (q = 2+k, n = 3+k):
    # em k = 18 a resposta tinha 23 digitos e os distratores diferiam so
    # nos ultimos algarismos, virando comparacao de digitos.
    gigantes = []
    for materia in materias:
        for q in banco[materia] or []:
            for opcao in q.get("opcoes") or []:
                if re.search(r"\d{10,}", str(opcao)):
                    gigantes.append((materia, q.get("pergunta"), opcao))

    assert not gigantes, f"{len(gigantes)} alternativas com 10+ digitos: {gigantes[:3]}"


def test_reposicao_nao_inventa_numero_negativo():
    # A reserva varia o numero da resposta; nao pode gerar "-1 N" numa
    # grandeza que so faz sentido positiva.
    opcoes, _ = _opcoes("1 N", ["1 N", "1 N", "1 N"], "semente")

    assert len(set(opcoes)) == len(opcoes)
    for opcao in opcoes:
        numero = re.search(r"-?\d+", opcao)
        assert numero and int(numero.group(0)) >= 0, opcoes
