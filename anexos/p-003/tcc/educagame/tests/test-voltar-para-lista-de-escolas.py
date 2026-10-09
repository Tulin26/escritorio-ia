"""Escolhida a escola, ainda dá para voltar à lista antes de logar.

Visto em 11/09/2026: login e cadastro escondem menu e cabeçalho, e "/" com
escola na sessão manda quem não logou de volta para /login. Sem link na
tela, quem errou de escola não tinha como sair.
"""

from __future__ import annotations

import pytest


def _com_escola(client):
    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        sess["escola_slug"] = "etecata"
        sess["escola_nome"] = "Etec Araçatuba"
        carimbar_sessao(sess)


@pytest.mark.parametrize("rota", ["/login", "/cadastro"])
def test_a_tela_mostra_a_escola_e_o_caminho_de_volta(client, rota):
    _com_escola(client)

    resposta = client.get(rota)
    corpo = resposta.get_data(as_text=True)

    assert resposta.status_code == 200, corpo[:300]
    assert "Etec Araçatuba" in corpo
    assert 'href="/trocar-escola"' in corpo


def test_trocar_escola_esquece_a_escola_e_volta_para_o_inicio(client):
    _com_escola(client)

    resposta = client.get("/trocar-escola")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "escola_id" not in sess
        assert "escola_nome" not in sess
