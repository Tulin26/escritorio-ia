"""Slug guardado na sessao envelhece quando a escola e editada.

MELHORIA: regressao de um caso real. O slug da escola foi editado no painel
ADM ("etec-aracatuba" virou "etecata"). A partir dali, toda sessao que ainda
guardava o slug antigo batia em "Escola nao encontrada" a cada visita -- e
como a sessao nunca era limpa, o erro se repetia ate a pessoa apagar os
cookies. Nenhum aluno vai adivinhar isso.

O padrao no codigo tambem era o slug de uma escola especifica, escrito a
mao, e envelheceu junto.
"""

from __future__ import annotations

import io

import pytest

from web.routes import home_fla

from tests.apoio_flask import carimbar_sessao

ESCOLA = {"id": "1", "nome": "ETEC", "slug": "etecata"}


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch):
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [ESCOLA])
    monkeypatch.setattr(
        home_fla,
        "buscar_escola_por_slug",
        lambda slug: ESCOLA if slug == ESCOLA["slug"] else None,
    )


def test_slug_velho_na_sessao_e_descartado(client):
    with client.session_transaction() as sess:
        sess["escola_slug"] = "etec-aracatuba"
        sess["escola_id"] = "1"
        sess["escola_nome"] = "Nome Antigo"
        carimbar_sessao(sess)

    resposta = client.get("/")

    assert resposta.status_code == 200
    with client.session_transaction() as sess:
        assert "escola_slug" not in sess, "manteve o slug morto e repetiria o erro"
        assert "escola_id" not in sess
        assert "escola_nome" not in sess


def test_apos_descartar_a_visita_seguinte_e_limpa(client):
    with client.session_transaction() as sess:
        sess["escola_slug"] = "etec-aracatuba"
        carimbar_sessao(sess)

    client.get("/")
    corpo = client.get("/").data.decode("utf-8")

    # sem slug na sessao, cai na lista de escolas -- sem erro nenhum
    assert "código dessa escola mudou" not in corpo
    assert "Escolha sua escola" in corpo
    assert "ETEC" in corpo


def test_a_primeira_visita_explica_que_o_codigo_mudou(client):
    # Com o slug virando codigo digitado, o aviso passou a valer a pena:
    # sem ele a pessoa voltaria para a lista e digitaria o codigo VELHO,
    # que falharia como "codigo incorreto" sem dizer por que.
    with client.session_transaction() as sess:
        sess["escola_slug"] = "etec-aracatuba"
        carimbar_sessao(sess)

    corpo = client.get("/").data.decode("utf-8")

    assert "código dessa escola mudou" in corpo
    assert "ETEC" in corpo, "precisa oferecer a escola certa junto do aviso"


def test_slug_na_url_nao_entra_mais(client):
    # MELHORIA: "?escola=<slug>" punha a escola na sessao direto -- era o
    # atalho que fazia o codigo nunca ser digitado. O parametro passa a ser
    # ignorado; a URL nao decide mais escola nenhuma.
    resposta = client.get("/?escola=" + ESCOLA["slug"])

    assert resposta.status_code == 200
    assert "Escolha sua escola" in resposta.data.decode("utf-8")
    with client.session_transaction() as sess:
        assert "escola_slug" not in sess


def test_a_rota_e_slug_tambem_nao_entra_mais(client):
    # A gemea de "?escola=": punha o slug na sessao a partir do endereco.
    # Continua existindo para o link antigo cair na lista em vez de 404.
    resposta = client.get("/e/" + ESCOLA["slug"], follow_redirects=False)

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"
    with client.session_transaction() as sess:
        assert "escola_slug" not in sess


def test_nenhuma_escola_escrita_no_codigo():
    # O padrao antigo era "etec-aracatuba", escrito a mao. Escola especifica
    # no codigo envelhece em silencio: ninguem percebe ate parar de
    # resolver. Depois virou DEFAULT_ESCOLA_SLUG, por ambiente -- que ja
    # nao surtia efeito (index() mostrava a lista antes de consultar o
    # padrao) e, com o codigo obrigatorio, seria outro jeito de entrar sem
    # digitar. Saiu.
    import inspect
    import tokenize

    # So o CODIGO. Os comentarios contam a historia ("etec-aracatuba" virou
    # "etecata") e precisam poder citar os nomes -- proibir a palavra
    # apagaria justamente o registro de por que a regra existe.
    fonte = inspect.getsource(home_fla)
    codigo = " ".join(
        tok.string
        for tok in tokenize.generate_tokens(io.StringIO(fonte).readline)
        if tok.type != tokenize.COMMENT
    )

    for slug in ("etec-aracatuba", "etecata", "deltaata"):
        assert slug not in codigo, f"escola especifica escrita no codigo: {slug}"
    assert "os.getenv" not in codigo, "voltou a existir escola padrao por ambiente"
