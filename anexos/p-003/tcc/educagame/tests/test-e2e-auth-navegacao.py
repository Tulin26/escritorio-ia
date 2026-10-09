from __future__ import annotations

import pytest

import web.routes.auth_fla as auth_fla
import web.routes.home_fla as home_fla
import web.routes.professor_fla as professor_fla

from tests.apoio_flask import carimbar_sessao


def _usuario_fake(role: str) -> dict:
    return {"id": "1", "username": f"usuario-{role}", "role": role}


def _sem_dados_do_painel(monkeypatch):
    """Evita qualquer chamada real ao Supabase a partir do painel do professor."""
    monkeypatch.setattr(professor_fla, "buscar_alunos", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "buscar_logs", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "buscar_resumo_turma", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "listar_escolas", lambda: [])
    monkeypatch.setattr(professor_fla, "listar_rpg_configs", lambda escola_id: [])


# ====================== LOGIN ======================


def test_login_get_renderiza(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Entrar" in resp.data


def test_login_post_senha_errada_mostra_erro_e_nao_loga(client, monkeypatch):
    monkeypatch.setattr(auth_fla, "autenticar", lambda username, senha: None)

    resp = client.post("/login", data={"username": "aluno", "senha": "errada"})

    assert resp.status_code == 200
    assert "invalidos".encode() in resp.data or "inválidos".encode() in resp.data
    with client.session_transaction() as sess:
        assert "usuario_role" not in sess


@pytest.mark.parametrize("role", ["aluno", "professor", "desenvolvedor"])
def test_login_post_sucesso_seta_sessao_por_papel(client, monkeypatch, role):
    monkeypatch.setattr(auth_fla, "autenticar", lambda username, senha: _usuario_fake(role))

    resp = client.post("/login", data={"username": f"usuario-{role}", "senha": "x"}, follow_redirects=False)

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["usuario_role"] == role
        assert sess["usuario_username"] == f"usuario-{role}"


def test_logout_limpa_sessao_e_redireciona_para_login(client):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["usuario_id"] = "1"
        sess["escola_id"] = "escola-1"
        sess["aluno_id"] = "aluno-1"
        carimbar_sessao(sess)

    resp = client.post("/logout", follow_redirects=False)

    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    with client.session_transaction() as sess:
        assert "usuario_role" not in sess
        assert "escola_id" not in sess
        assert "aluno_id" not in sess


# ====================== GATE CENTRAL ======================


@pytest.mark.parametrize(
    "rota",
    [
        "/oraculo/",
        "/treino/",
        "/enem/",
        "/laboratorio/",
        "/rpg/",
        "/boss-rush/",
        "/escape-room/",
        "/guildas/",
        "/progresso/",
        "/perfil/",
        "/professor/",
    ],
)
def test_rota_protegida_sem_login_redireciona_para_login(client, rota):
    resp = client.get(rota, follow_redirects=False)

    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_home_e_login_ficam_publicos_sem_sessao(client):
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/healthz").status_code == 200


# ====================== GATE POR PAPEL ======================


def test_aluno_e_bloqueado_do_painel_do_professor(client):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        carimbar_sessao(sess)

    resp = client.get("/professor/", follow_redirects=False)

    assert resp.status_code == 302
    assert "/professor" not in resp.headers["Location"]


@pytest.mark.parametrize("role", ["professor", "desenvolvedor"])
def test_home_redireciona_professor_e_desenvolvedor_para_o_painel(client, monkeypatch, role):
    monkeypatch.setattr(
        home_fla,
        "buscar_escola_por_slug",
        lambda slug: {"id": "escola-1", "slug": slug, "nome": "Escola Teste"},
    )
    with client.session_transaction() as sess:
        sess["usuario_role"] = role
        # a escola vem da sessao: "?escola=" na URL deixou de escolher escola
        sess["escola_slug"] = "etec-aracatuba"
        # a conta precisa ser DESTA escola; desenvolvedor e global
        sess["usuario_escola_id"] = "escola-1"
        carimbar_sessao(sess)

    resp = client.get("/", follow_redirects=False)

    assert resp.status_code == 302
    assert "/professor" in resp.headers["Location"]


def test_home_mostra_grade_de_jogos_para_aluno(client, monkeypatch):
    monkeypatch.setattr(
        home_fla,
        "buscar_escola_por_slug",
        lambda slug: {"id": "escola-1", "slug": slug, "nome": "Escola Teste"},
    )
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_slug"] = "etec-aracatuba"
        sess["usuario_escola_id"] = "escola-1"
        carimbar_sessao(sess)

    resp = client.get("/")

    assert resp.status_code == 200
    assert "Treino Rápido".encode() in resp.data


# ====================== HUB DE CARDS DO PROFESSOR ======================


@pytest.mark.parametrize("role", ["professor", "desenvolvedor"])
def test_painel_sem_aba_mostra_hub_de_cards(client, monkeypatch, role):
    _sem_dados_do_painel(monkeypatch)
    with client.session_transaction() as sess:
        sess["usuario_role"] = role
        carimbar_sessao(sess)

    resp = client.get("/professor/")

    assert resp.status_code == 200
    assert b'class="mode-grid"' in resp.data


def test_hub_nao_mostra_card_adm_para_professor(client, monkeypatch):
    _sem_dados_do_painel(monkeypatch)
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        carimbar_sessao(sess)

    resp = client.get("/professor/")

    assert "ADM".encode() not in resp.data


def test_hub_mostra_card_adm_para_desenvolvedor(client, monkeypatch):
    _sem_dados_do_painel(monkeypatch)
    with client.session_transaction() as sess:
        sess["usuario_role"] = "desenvolvedor"
        carimbar_sessao(sess)

    resp = client.get("/professor/")

    assert "ADM".encode() in resp.data


def test_painel_com_aba_mostra_a_secao_escolhida(client, monkeypatch):
    _sem_dados_do_painel(monkeypatch)
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        carimbar_sessao(sess)

    resp = client.get("/professor/?aba=analises")

    assert resp.status_code == 200
    assert b'class="mode-grid"' not in resp.data
    assert "Desempenho dos Alunos".encode() in resp.data


def test_professor_nao_acessa_aba_adm_mesmo_pedindo_na_url(client, monkeypatch):
    _sem_dados_do_painel(monkeypatch)
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        carimbar_sessao(sess)

    resp = client.get("/professor/?aba=adm")

    assert resp.status_code == 200
    assert "Painel do Desenvolvedor".encode() not in resp.data


# ====================== SPLASH / TRANSICAO DE ESCOLA ======================


def test_splash_com_uma_escola_redireciona_automatico_sem_clique(client, monkeypatch):
    # MELHORIA: com uma unica escola cadastrada, exigir um clique na tela
    # "Escolha sua escola" toda vez que a sessao reinicia (login, trocar de
    # conta) e um clique sem escolha real nenhuma pra fazer. A splash passa
    # a servir de transicao automatica direto pra essa unica escola.
    escola = {"id": "escola-1", "slug": "etec-aracatuba", "nome": "Escola Unica"}
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [escola])

    resp = client.get("/")

    assert resp.status_code == 200
    assert b"school-splash" in resp.data
    assert b"setTimeout" in resp.data
    assert b"/entrar-escola/escola-1" in resp.data
    assert b"school-entry-oculta" in resp.data


def test_splash_com_varias_escolas_nao_redireciona_automatico(client, monkeypatch):
    escolas = [
        {"id": "escola-1", "slug": "etec-aracatuba", "nome": "Escola A"},
        {"id": "escola-2", "slug": "outra", "nome": "Escola B"},
    ]
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: escolas)

    resp = client.get("/")

    assert resp.status_code == 200
    assert b"school-splash" in resp.data
    # MELHORIA: era "setTimeout not in resp.data". Isso deixou de servir
    # quando a splash ganhou uma rede propria, que tambem usa setTimeout
    # para se remover -- e essa rede nao redireciona ninguem. O que o teste
    # quer dizer e "nao ha redirecionamento automatico", entao passa a
    # cobrar exatamente isso.
    assert b"window.location.href" not in resp.data
    assert b"/entrar-escola/" not in resp.data.split(b"<section")[0]
    assert b"Escola A" in resp.data
    assert b"Escola B" in resp.data


def test_splash_sem_nenhuma_escola_nao_redireciona_automatico(client, monkeypatch):
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [])

    resp = client.get("/")

    assert resp.status_code == 200
    assert b"window.location.href" not in resp.data
    assert "Nenhuma escola cadastrada".encode() in resp.data


# ====================== SELECAO DE ESCOLA ======================


def test_clicar_na_escola_pede_o_codigo_e_nao_entra(client, monkeypatch):
    # MELHORIA: clicar na escola entrava direto. O slug voltou a ser o
    # codigo de entrada -- ver tests/test_codigo_da_escola.py.
    escola = {"id": "escola-1", "slug": "etec-aracatuba", "nome": "Escola Teste"}
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [escola])

    resp = client.get("/entrar-escola/escola-1")

    assert resp.status_code == 200
    assert "Codigo da escola".encode() in resp.data or "Código da escola".encode() in resp.data
    with client.session_transaction() as sess:
        assert "escola_slug" not in sess, "entrou so de clicar"
        assert "escola_id" not in sess


def test_codigo_certo_entra_na_escola(client, monkeypatch):
    escola = {"id": "escola-1", "slug": "etec-aracatuba", "nome": "Escola Teste"}
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [escola])

    resp = client.post(
        "/entrar-escola/escola-1", data={"slug": "etec-aracatuba"}, follow_redirects=False
    )

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["escola_slug"] == "etec-aracatuba"
        assert sess["escola_id"] == "escola-1"


def test_entrar_escola_com_id_invalido_volta_para_selecao(client, monkeypatch):
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [])

    resp = client.get("/entrar-escola/escola-inexistente", follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers["Location"] == "/"


def test_entrar_escola_com_next_cadastro_redireciona_para_cadastro(client, monkeypatch):
    escola = {"id": "escola-1", "slug": "etec-aracatuba", "nome": "Escola Teste"}
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [escola])

    resp = client.post(
        "/entrar-escola/escola-1",
        data={"slug": "etec-aracatuba", "next": "cadastro"},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert resp.headers["Location"] == "/cadastro"
