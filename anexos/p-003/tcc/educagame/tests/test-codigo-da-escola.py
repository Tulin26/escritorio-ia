"""O slug volta a ser o codigo de entrada da escola.

Ele ja tinha sido exigido, e foi tirado: digitar parecia atrito sem ganho,
porque a lista de escolas e publica de qualquer jeito. So que sem ele um
clique bastava para entrar na porta de qualquer escola -- e num aparelho
compartilhado a escola do colega fica a um clique.

O que este codigo NAO e: um segredo. A lista continua publica (e o que ajuda
a pessoa a achar a sua escola) e nada impede alguem de tentar varios. Ele e o
combinado que o professor passa para a turma. Quem controla acesso de verdade
e a senha, no login.

Junto saiu o que fazia o codigo nunca ser digitado: "?escola=<slug>" na URL,
a rota "/e/<slug>" e o DEFAULT_ESCOLA_SLUG do ambiente -- os tres punham a
escola na sessao a partir do endereco. Isso esta coberto em
tests/test_slug_de_escola_envelhecido.py.
"""

from __future__ import annotations

import pytest

from web.routes import home_fla

from tests.apoio_flask import carimbar_sessao

ETEC = {"id": "1", "nome": "ETEC", "slug": "etecata"}
DELTA = {"id": "2", "nome": "Educacional Delta", "slug": "deltaata"}


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch):
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [ETEC, DELTA])
    monkeypatch.setattr(
        home_fla,
        "buscar_escola_por_slug",
        lambda slug: next((e for e in (ETEC, DELTA) if e["slug"] == slug), None),
    )


def _sem_escola_na_sessao(client) -> bool:
    with client.session_transaction() as sess:
        return not any(c in sess for c in ("escola_id", "escola_slug", "escola_nome"))


# ====================== CLICAR NAO ENTRA ======================


def test_clicar_na_escola_so_pede_o_codigo(client):
    resposta = client.get("/entrar-escola/1")

    assert resposta.status_code == 200
    corpo = resposta.data.decode("utf-8")
    assert "ETEC" in corpo
    assert "Código da escola" in corpo
    assert _sem_escola_na_sessao(client), "entrou so de clicar na escola"


def test_a_lista_leva_para_o_codigo_e_nao_para_dentro(client):
    corpo = client.get("/").data.decode("utf-8")

    assert "/entrar-escola/1" in corpo
    assert _sem_escola_na_sessao(client)


def test_o_formulario_do_codigo_tem_csrf(client):
    # Sem o token o POST volta 400 e a pessoa nao entra em lugar nenhum --
    # CSRFProtect vale para todo POST do app (ver flask_app.py).
    corpo = client.get("/entrar-escola/1").data.decode("utf-8")

    assert "csrf_token" in corpo


# ====================== O CODIGO ======================


def test_codigo_certo_entra(client):
    resposta = client.post("/entrar-escola/1", data={"slug": "etecata"}, follow_redirects=False)

    assert resposta.status_code == 302
    with client.session_transaction() as sess:
        assert sess["escola_slug"] == "etecata"
        assert sess["escola_id"] == "1"
        assert sess["escola_nome"] == "ETEC"


def test_codigo_errado_nao_entra_e_explica(client):
    resposta = client.post("/entrar-escola/1", data={"slug": "chutei"})

    assert resposta.status_code == 200
    assert "Código incorreto" in resposta.data.decode("utf-8")
    assert _sem_escola_na_sessao(client)


def test_codigo_vazio_nao_entra(client):
    # O "required" do HTML e so do navegador: um POST direto passa por cima.
    resposta = client.post("/entrar-escola/1", data={"slug": ""})

    assert resposta.status_code == 200
    assert _sem_escola_na_sessao(client)


def test_sem_o_campo_nenhum_nao_entra(client):
    resposta = client.post("/entrar-escola/1", data={})

    assert resposta.status_code == 200
    assert _sem_escola_na_sessao(client)


@pytest.mark.parametrize("digitado", ["ETECATA", "  etecata  ", "EtecAta", "\tetecata\n"])
def test_maiuscula_e_espaco_sobrando_nao_reprovam(client, digitado):
    # O codigo e passado de boca ou no quadro, e no celular a primeira letra
    # sai maiuscula sozinha. Reprovar por isso seria implicancia, nao
    # seguranca -- o codigo digitado continua tendo que ser o mesmo.
    resposta = client.post("/entrar-escola/1", data={"slug": digitado}, follow_redirects=False)

    assert resposta.status_code == 302, digitado
    with client.session_transaction() as sess:
        assert sess["escola_slug"] == "etecata"


def test_o_codigo_de_uma_escola_nao_abre_a_outra(client):
    # A razao de o codigo existir: sem isso, um clique levava a qualquer
    # escola da lista.
    resposta = client.post("/entrar-escola/2", data={"slug": ETEC["slug"]})

    assert resposta.status_code == 200
    assert _sem_escola_na_sessao(client)


def test_escola_inexistente_volta_para_a_lista(client):
    resposta = client.post(
        "/entrar-escola/nao-existe", data={"slug": "etecata"}, follow_redirects=False
    )

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"
    assert _sem_escola_na_sessao(client)


# ====================== O QUE VEM DEPOIS ======================


def test_depois_do_codigo_a_home_para_de_pedir_escola(client):
    client.post("/entrar-escola/1", data={"slug": "etecata"})

    resposta = client.get("/", follow_redirects=False)

    # sem login ainda, entao vai para /login -- mas ja nao pede escola
    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]


def test_o_codigo_carimba_a_sessao(client):
    # A escolha acontece dentro da view, depois do gate de prazo. Sem o
    # carimbo no fim da requisicao, a proxima chegaria "sem idade" e seria
    # expirada na hora (ver core/sessao.py).
    client.post("/entrar-escola/1", data={"slug": "etecata"})

    with client.session_transaction() as sess:
        assert sess["sessao_inicio"] > 0
        assert sess["sessao_visto_em"] > 0


def test_trocar_escola_faz_pedir_o_codigo_de_novo(client):
    client.post("/entrar-escola/1", data={"slug": "etecata"})

    client.get("/trocar-escola")

    assert _sem_escola_na_sessao(client)
    assert "Escolha sua escola" in client.get("/").data.decode("utf-8")


def test_o_caminho_do_cadastro_atravessa_o_codigo(client):
    # Aluno novo cai em "/?next=cadastro"; o destino tem que sobreviver ao
    # formulario, senao ele volta para a home e se perde.
    corpo = client.get("/entrar-escola/1?next=cadastro").data.decode("utf-8")
    assert 'value="cadastro"' in corpo

    resposta = client.post(
        "/entrar-escola/1",
        data={"slug": "etecata", "next": "cadastro"},
        follow_redirects=False,
    )

    assert resposta.headers["Location"] == "/cadastro"


def test_quem_ja_esta_logado_nao_escapa_do_codigo(client):
    # Sessao com login mas sem escola (trocou de escola, por exemplo): a
    # home tem que voltar a pedir, nao aproveitar o login para entrar.
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        carimbar_sessao(sess)

    corpo = client.get("/").data.decode("utf-8")

    assert "Escolha sua escola" in corpo
