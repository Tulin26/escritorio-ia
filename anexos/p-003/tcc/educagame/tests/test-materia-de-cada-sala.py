"""Cada sala do Escape Room recebe a matéria que foi escolhida para ela.

Relatório de QA de 23/09/2026, achado 3.3: ao escolher "Ciências" para uma
sala, essa sala recebia a matéria da sala seguinte e todas as demais
escorregavam uma posição. Na Run 5 o aluno montou "Ciências, Arte, Matemática,
Biologia" e jogou "Arte, Matemática, Biologia, Matemática" -- nunca viu
Ciências, e a sala 4 cobrou uma matéria que ele não tinha escolhido.

A função do servidor sozinha nunca reproduziu: ela substitui a matéria
inválida na mesma posição. O que desloca é o formulário -- os seis campos
dividiam o mesmo nome e a rota lia a lista por posição, então qualquer campo
que não chegasse ao servidor sumia da lista.
"""

from __future__ import annotations

import pytest

import web.routes.escape_room_fla as escape

PERMITIDAS = ["Matematica", "Arte", "Biologia", "Geografia", "Ingles", "Filosofia", "Sociologia"]


def _montar(dados: dict, total: int = 4, padrao: str = "Matematica") -> list[str]:
    """Roda a rota do jeito que o navegador manda: um campo por sala."""
    from flask_app import app

    with app.test_request_context("/escape-room/iniciar", method="POST", data=dados):
        return escape._materias_das_salas(escape._materias_enviadas(total), total, padrao, PERMITIDAS)


def test_cada_sala_fica_com_a_materia_escolhida_para_ela():
    salas = _montar({
        "materia_sala_1": "Geografia",
        "materia_sala_2": "Ingles",
        "materia_sala_3": "Filosofia",
        "materia_sala_4": "Sociologia",
    })

    assert salas == ["Geografia", "Ingles", "Filosofia", "Sociologia"]


def test_campo_que_nao_chega_nao_desloca_as_salas_seguintes():
    # O caso da Run 5 do relatório: o campo da sala 1 não chega ao servidor.
    # Antes, a sala 1 recebia Arte e todas escorregavam; agora a sala 1 cai na
    # matéria padrão e as outras três ficam onde estavam.
    salas = _montar({
        "materia_sala_2": "Arte",
        "materia_sala_3": "Matematica",
        "materia_sala_4": "Biologia",
    })

    assert salas == ["Matematica", "Arte", "Matematica", "Biologia"]
    assert salas[1] == "Arte" and salas[3] == "Biologia", "as salas seguintes não podem escorregar"


def test_materia_fora_do_ano_escolar_vira_a_padrao_na_propria_posicao():
    # "Ciencias" não existe no Ensino Médio: a sala recebe a matéria padrão,
    # sem empurrar as outras.
    salas = _montar({
        "materia_sala_1": "Ciencias",
        "materia_sala_2": "Arte",
        "materia_sala_3": "Matematica",
        "materia_sala_4": "Biologia",
    })

    assert salas == ["Matematica", "Arte", "Matematica", "Biologia"]


def test_formulario_vazio_usa_a_materia_padrao_em_todas():
    assert _montar({}, total=3, padrao="Geografia") == ["Geografia"] * 3


@pytest.mark.parametrize("total", [3, 4, 5, 6])
def test_o_numero_de_salas_manda_no_tamanho(total):
    dados = {f"materia_sala_{n}": "Arte" for n in range(1, 7)}
    assert _montar(dados, total=total) == ["Arte"] * total


def test_a_tela_da_um_nome_proprio_a_cada_sala():
    from pathlib import Path

    tela = (Path(__file__).resolve().parents[1] / "web/templates/escape_room.html").read_text(encoding="utf-8")
    assert 'name="materia_sala_{{ numero }}"' in tela
    assert 'name="materias_salas"' not in tela, (
        "campo compartilhado volta a ser lido por posição, e some junto com a sala que o navegador não enviar"
    )
