"""Depois de gerar, o formulário do Oráculo volta com a matéria pedida marcada.

Visto em 11/09/2026: Biologia pedida e gerada (o log gravou Biologia), e a
tela mostrando "Matéria: Matemática" logo acima da questão, porque o seletor
voltava na primeira opção. Um segundo "Gerar desafio" sem reparar pedia
Matemática de verdade.
"""

from __future__ import annotations

import re

import pytest


def _abrir_oraculo(client, monkeypatch, enigma):
    from tests.apoio_flask import carimbar_sessao
    from web.routes import oraculo_fla

    monkeypatch.setattr(
        oraculo_fla, "obter_estado_flask",
        lambda nome, padrao=None: dict(enigma) if (enigma and nome == "enigma_atual") else padrao,
    )
    monkeypatch.setattr(oraculo_fla, "alunos_para_selecao", lambda: [])
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        sess["aluno_id"] = "aluno-1"
        sess["ano_escolar"] = "3º Ano EM"
        carimbar_sessao(sess)
    return client.get("/oraculo/").get_data(as_text=True)


def _marcadas(corpo, nome):
    select = re.search(rf'<select id="{nome}" name="{nome}">(.*?)</select>', corpo, re.S)
    assert select, f"seletor {nome} sumiu da tela"
    return [
        (m.group(1) or m.group(2)).strip()
        for m in re.finditer(r'<option(?: value="([^"]*)")?[^>]*\bselected\b[^>]*>([^<]*)<', select.group(1))
    ]


ENIGMA = {
    "pergunta": "Qual organela produz ATP?",
    "opcoes": ["Mitocôndria", "Ribossomo", "Lisossomo", "Complexo golgiense"],
    "correta": 0,
    "materia": "Biologia",
    "materia_label": "Biologia",
    "nivel": "Difícil",
    "_origem_geracao": "ia",
}


def test_a_materia_pedida_volta_marcada(client, monkeypatch):
    corpo = _abrir_oraculo(client, monkeypatch, ENIGMA)

    assert _marcadas(corpo, "materia") == ["Biologia"]


def test_o_nivel_pedido_volta_marcado(client, monkeypatch):
    corpo = _abrir_oraculo(client, monkeypatch, ENIGMA)

    assert _marcadas(corpo, "nivel") == ["Difícil"]


def test_sem_enigma_o_nivel_padrao_e_medio(client, monkeypatch):
    corpo = _abrir_oraculo(client, monkeypatch, None)

    assert _marcadas(corpo, "materia") == []
    assert _marcadas(corpo, "nivel") == ["Médio"]


@pytest.mark.parametrize("modelo", ["oraculo.html"])
def test_nenhum_nivel_corrompido_no_modelo(modelo):
    from pathlib import Path

    texto = (Path(__file__).resolve().parents[1] / "web" / "templates" / modelo).read_text(encoding="utf-8")
    assert "Ã" not in texto
