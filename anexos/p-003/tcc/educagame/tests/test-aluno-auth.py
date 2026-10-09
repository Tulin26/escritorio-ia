from __future__ import annotations

import services.aluno_auth_service as aluno_auth_service
from repositories.aluno_repo import upsert_alunos

from tests.apoio_flask import carimbar_sessao


def test_email_formato_valido():
    assert aluno_auth_service.email_formato_valido("aluno@escola.com")
    assert not aluno_auth_service.email_formato_valido("nao-e-email")
    assert not aluno_auth_service.email_formato_valido("sem-arroba.com")
    assert not aluno_auth_service.email_formato_valido("")


def test_dominio_descartavel_bloqueia_conhecidos():
    assert aluno_auth_service.dominio_descartavel("teste@mailinator.com")
    assert aluno_auth_service.dominio_descartavel("teste@yopmail.com")
    assert not aluno_auth_service.dominio_descartavel("teste@gmail.com")
    assert not aluno_auth_service.dominio_descartavel("teste@escola.edu.br")


def test_validar_email_cadastro_rejeita_descartavel_com_mensagem_clara():
    erro = aluno_auth_service.validar_email_cadastro("aluno@mailinator.com")
    assert "descart" in erro.lower()


def test_token_confirmacao_ida_e_volta(client):
    with client.application.test_request_context():
        token = aluno_auth_service.gerar_token_confirmacao("aluno-123")
        assert aluno_auth_service.verificar_token_confirmacao(token) == "aluno-123"


def test_token_invalido_nao_verifica(client):
    with client.application.test_request_context():
        assert aluno_auth_service.verificar_token_confirmacao("token-forjado") is None


def test_cadastro_recusa_email_descartavel(client, sem_rede_supabase):
    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    resp = client.post(
        "/cadastro",
        data={
            "nome": "Aluno Teste",
            "ra_identificacao": "RA-1",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno@mailinator.com",
            "senha": "senha123",
            "consentimento": "on",
        },
    )
    assert resp.status_code == 200
    assert "descart".encode() in resp.data.lower()


def test_cadastro_sem_marcar_consentimento_e_recusado(client, sem_rede_supabase):
    """LGPD Art. 8: sem a caixa marcada, o cadastro nao pode completar --
    nem silenciosamente gravar o aluno sem o consentimento."""
    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    resp = client.post(
        "/cadastro",
        data={
            "nome": "Aluno Sem Consentimento",
            "ra_identificacao": "RA-sem-consentimento",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno.semconsentimento@gmail.com",
            "senha": "senha123",
            # "consentimento" de proposito ausente -- e o que o teste cobra.
        },
    )
    assert resp.status_code == 200
    assert "aceitar a pol".encode() in resp.data.lower()

    tabela = sem_rede_supabase.table("alunos")._tabela
    assert not any(linha["email"] == "aluno.semconsentimento@gmail.com" for linha in tabela.linhas)


def test_cadastrar_aluno_exige_o_parametro_de_consentimento():
    """Sem valor padrao de proposito: um caminho novo que esqueca de checar
    a caixa tem de quebrar ao chamar a funcao, nao cadastrar em silencio."""
    import inspect

    parametros = inspect.signature(aluno_auth_service.cadastrar_aluno).parameters
    assert "consentimento" in parametros
    assert parametros["consentimento"].default is inspect.Parameter.empty


def test_cadastro_com_consentimento_grava_a_data(client, sem_rede_supabase, monkeypatch):
    """O consentimento vira timestamp na linha do aluno -- prova de quando
    a pessoa aceitou, nao so um booleano sem data."""
    monkeypatch.setattr(aluno_auth_service, "_enviar_email", lambda *a, **k: None)
    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    client.post(
        "/cadastro",
        data={
            "nome": "Aluno Consentiu",
            "ra_identificacao": "RA-consentiu",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno.consentiu@gmail.com",
            "senha": "senha123",
            "consentimento": "on",
        },
    )

    tabela = sem_rede_supabase.table("alunos")._tabela
    aluno = next(linha for linha in tabela.linhas if linha["email"] == "aluno.consentiu@gmail.com")
    assert aluno["consentimento_dados_em"], "o cadastro nao gravou quando o consentimento foi dado"


def test_cadastro_sem_escola_na_sessao_redireciona_para_escolher_escola(client, sem_rede_supabase):
    resp = client.post(
        "/cadastro",
        data={
            "nome": "Aluno Teste",
            "ra_identificacao": "RA-1",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno@gmail.com",
            "senha": "senha123",
            "consentimento": "on",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/?next=cadastro"


def test_cadastro_cria_aluno_pendente_e_dispara_email(client, sem_rede_supabase, monkeypatch):
    enviados = []
    monkeypatch.setattr(
        aluno_auth_service, "_enviar_email", lambda destinatario, assunto, corpo, corpo_html=None: enviados.append(destinatario)
    )

    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    resp = client.post(
        "/cadastro",
        data={
            "nome": "Aluno Teste",
            "ra_identificacao": "RA-1",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno.novo@gmail.com",
            "senha": "senha123",
            "consentimento": "on",
        },
    )
    assert resp.status_code == 200
    assert enviados == ["aluno.novo@gmail.com"]

    tabela = sem_rede_supabase.table("alunos")._tabela
    aluno = next(linha for linha in tabela.linhas if linha["email"] == "aluno.novo@gmail.com")
    assert aluno["email_confirmado"] is False


def test_login_bloqueado_antes_de_confirmar_email(client, sem_rede_supabase, monkeypatch):
    monkeypatch.setattr(aluno_auth_service, "_enviar_email", lambda *a, **k: None)
    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)
    client.post(
        "/cadastro",
        data={
            "nome": "Aluno Teste",
            "ra_identificacao": "RA-1",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno.pendente@gmail.com",
            "senha": "senha123",
            "consentimento": "on",
        },
    )

    resp = client.post("/login", data={"username": "aluno.pendente@gmail.com", "senha": "senha123"})
    assert resp.status_code == 200
    assert "invalid".encode() in resp.data.lower() or "inv\xe1lid".encode("utf-8") in resp.data


def test_cadastro_com_mesmo_email_e_ra_diferente_atualiza_em_vez_de_colidir(client, sem_rede_supabase, monkeypatch):
    # MELHORIA: regressao para um bug visto em producao -- um cadastro
    # pendente (nunca confirmado) ja existia com um e-mail, e uma nova
    # tentativa de cadastro com o MESMO e-mail mas RA diferente tentava
    # inserir outra linha via upsert por (escola_id, ra_identificacao),
    # colidindo com a restricao de e-mail unico e falhando com "Nao foi
    # possivel concluir o cadastro" sem nenhum e-mail ser enviado.
    monkeypatch.setattr(aluno_auth_service, "_enviar_email", lambda *a, **k: None)

    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)
    client.post(
        "/cadastro",
        data={
            "nome": "Aluno Duplicado",
            "ra_identificacao": "RA-primeira-tentativa",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno.duplicado@gmail.com",
            "senha": "senha123",
            "consentimento": "on",
        },
    )

    resp = client.post(
        "/cadastro",
        data={
            "nome": "Aluno Duplicado",
            "ra_identificacao": "RA-segunda-tentativa",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno.duplicado@gmail.com",
            "senha": "outrasenha456",
            "consentimento": "on",
        },
    )
    assert resp.status_code == 200
    assert "Nao foi possivel".encode() not in resp.data

    tabela = sem_rede_supabase.table("alunos")._tabela
    linhas = [linha for linha in tabela.linhas if linha["email"] == "aluno.duplicado@gmail.com"]
    assert len(linhas) == 1
    assert linhas[0]["ra_identificacao"] == "RA-segunda-tentativa"


def test_cadastro_preserva_pontos_de_aluno_ja_matriculado(client, sem_rede_supabase, monkeypatch):
    # MELHORIA: regressao para o motivo de usar upsert por (escola_id,
    # ra_identificacao) em vez de sempre inserir um aluno novo -- se o
    # professor ja matriculou o aluno antes (com pontos acumulados), o
    # autocadastro por e-mail precisa completar esse registro, nao duplicar.
    upsert_alunos([
        {
            "escola_id": "escola-1",
            "nome": "Aluno Antigo",
            "ra_identificacao": "RA-99",
            "ano_escolar": "7º Ano",
            "periodo": "Tarde",
            "pontos_totais": 500,
        }
    ])

    capturado = {}
    monkeypatch.setattr(
        aluno_auth_service,
        "_enviar_email",
        lambda destinatario, assunto, corpo, corpo_html=None: capturado.setdefault("corpo", corpo),
    )

    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)
    client.post(
        "/cadastro",
        data={
            "nome": "Aluno Antigo",
            "ra_identificacao": "RA-99",
            "ano_escolar": "7º Ano",
            "periodo": "Tarde",
            "email": "aluno.antigo@gmail.com",
            "senha": "senha123",
            "consentimento": "on",
        },
    )

    tabela = sem_rede_supabase.table("alunos")._tabela
    linhas_ra99 = [linha for linha in tabela.linhas if linha["ra_identificacao"] == "RA-99"]
    assert len(linhas_ra99) == 1
    assert linhas_ra99[0]["pontos_totais"] == 500
    assert linhas_ra99[0]["email"] == "aluno.antigo@gmail.com"

    # extrai o link de confirmacao mandado por "e-mail" e confirma
    import re

    link = re.search(r"http\S+/confirmar-email/(\S+)", capturado["corpo"])
    token = link.group(1)
    resp = client.get(f"/confirmar-email/{token}", follow_redirects=False)
    assert resp.status_code == 302

    resp_login = client.post(
        "/login", data={"username": "aluno.antigo@gmail.com", "senha": "senha123"}, follow_redirects=False
    )
    assert resp_login.status_code == 302
    with client.session_transaction() as sess:
        assert sess["aluno_id"] == linhas_ra99[0]["id"]
        assert sess["usuario_role"] == "aluno"


def test_criar_aluno_com_username_exige_o_parametro_de_consentimento():
    """Sem valor padrao de proposito, igual a cadastrar_aluno(): um caminho
    novo que esqueca de confirmar a autorizacao da escola tem de quebrar ao
    chamar a funcao, nao criar a conta em silencio."""
    import inspect

    parametros = inspect.signature(aluno_auth_service.criar_aluno_com_username).parameters
    assert "consentimento_responsavel" in parametros
    assert parametros["consentimento_responsavel"].default is inspect.Parameter.empty


def test_criar_aluno_com_username_sem_consentimento_e_recusado(sem_rede_supabase):
    ok, erro = aluno_auth_service.criar_aluno_com_username(
        escola_id="escola-1",
        nome="Aluno Sem Consentimento",
        ra_identificacao="SC-1",
        ano_escolar="6º Ano",
        periodo="Manhã",
        username="semconsentimento",
        senha="senha123",
        consentimento_responsavel=False,
    )
    assert not ok
    assert "autorização" in erro.lower()
    assert aluno_auth_service.buscar_aluno_por_username("semconsentimento") is None


def test_criar_aluno_com_username_com_consentimento_grava_a_data(sem_rede_supabase):
    ok, erro = aluno_auth_service.criar_aluno_com_username(
        escola_id="escola-1",
        nome="Aluno Consentido",
        ra_identificacao="CC-1",
        ano_escolar="6º Ano",
        periodo="Manhã",
        username="alunoconsentido",
        senha="senha123",
        consentimento_responsavel=True,
    )
    assert ok, erro

    aluno = aluno_auth_service.buscar_aluno_por_username("alunoconsentido")
    assert aluno["consentimento_dados_em"], "a criacao nao gravou quando o consentimento foi confirmado"


def test_criar_aluno_com_username_e_login_direto_sem_confirmacao(client, sem_rede_supabase):
    ok, erro = aluno_auth_service.criar_aluno_com_username(
        escola_id="escola-1",
        nome="Lucas Nishigima",
        ra_identificacao="LN-1",
        ano_escolar="3º Ano EM",
        periodo="Manhã",
        username="Lucas",
        senha="Nishigima",
        consentimento_responsavel=True,
    )
    assert ok, erro

    resp = client.post("/login", data={"username": "Lucas", "senha": "Nishigima"}, follow_redirects=False)
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["usuario_role"] == "aluno"
        assert sess["aluno_nome"] == "Lucas Nishigima"


def test_login_com_username_de_aluno_e_case_insensitive(sem_rede_supabase):
    ok, erro = aluno_auth_service.criar_aluno_com_username(
        escola_id="escola-1",
        nome="Teste Case",
        ra_identificacao="TC-1",
        ano_escolar="6º Ano",
        periodo="Manhã",
        username="TesteUsuario",
        senha="senha123",
        consentimento_responsavel=True,
    )
    assert ok, erro
    aluno = aluno_auth_service.autenticar_aluno_por_username("testeusuario", "senha123")
    assert aluno is not None
    assert aluno["nome"] == "Teste Case"


def test_criar_aluno_com_username_recusa_senha_curta(sem_rede_supabase):
    ok, erro = aluno_auth_service.criar_aluno_com_username(
        escola_id="escola-1",
        nome="Teste",
        ra_identificacao="TS-1",
        ano_escolar="6º Ano",
        periodo="Manhã",
        username="teste2",
        senha="123",
        consentimento_responsavel=True,
    )
    assert not ok
    assert "senha" in erro.lower()


def test_token_redefinicao_senha_ida_e_volta(client):
    with client.application.test_request_context():
        token = aluno_auth_service.gerar_token_redefinicao_senha("aluno-123")
        assert aluno_auth_service.verificar_token_redefinicao_senha(token) == "aluno-123"


def test_token_confirmacao_nao_serve_como_token_de_redefinicao(client):
    # MELHORIA: salt diferente de proposito -- um token de confirmacao de
    # e-mail nao pode ser reaproveitado pra redefinir senha, mesmo sendo
    # gerado a partir do mesmo aluno_id com o mesmo secret_key.
    with client.application.test_request_context():
        token_confirmacao = aluno_auth_service.gerar_token_confirmacao("aluno-123")
        assert aluno_auth_service.verificar_token_redefinicao_senha(token_confirmacao) is None


def test_solicitar_redefinicao_para_email_inexistente_nao_revela_nada(sem_rede_supabase):
    ok = aluno_auth_service.solicitar_redefinicao_senha("ninguem-cadastrado@example.com")
    assert ok is True


def test_fluxo_completo_de_redefinicao_de_senha(client, sem_rede_supabase, monkeypatch):
    monkeypatch.setattr(aluno_auth_service, "_enviar_email", lambda *a, **k: None)
    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)
    client.post(
        "/cadastro",
        data={
            "nome": "Aluno Redefine",
            "ra_identificacao": "RA-redefine",
            "ano_escolar": "6º Ano",
            "periodo": "Manhã",
            "email": "aluno.redefine@gmail.com",
            "senha": "senhaAntiga1",
            "consentimento": "on",
        },
    )
    tabela = sem_rede_supabase.table("alunos")._tabela
    aluno = next(linha for linha in tabela.linhas if linha["email"] == "aluno.redefine@gmail.com")
    aluno["email_confirmado"] = True

    capturado = {}
    monkeypatch.setattr(
        aluno_auth_service,
        "_enviar_email",
        lambda destinatario, assunto, corpo, corpo_html=None: capturado.setdefault("corpo", corpo),
    )
    resp = client.post("/esqueci-senha", data={"email": "aluno.redefine@gmail.com"}, follow_redirects=False)
    assert resp.status_code == 302
    assert "redefinicao_enviada" in resp.headers["Location"]

    import re

    link = re.search(r"http\S+/redefinir-senha/(\S+)", capturado["corpo"])
    token = link.group(1)

    resp_form = client.get(f"/redefinir-senha/{token}")
    assert resp_form.status_code == 200

    resp_redefinir = client.post(
        f"/redefinir-senha/{token}",
        data={"senha": "senhaNova2", "confirmar_senha": "senhaNova2"},
        follow_redirects=False,
    )
    assert resp_redefinir.status_code == 302
    assert "senha_redefinida" in resp_redefinir.headers["Location"]

    resp_login_antigo = client.post(
        "/login", data={"username": "aluno.redefine@gmail.com", "senha": "senhaAntiga1"}
    )
    assert "invalid".encode() in resp_login_antigo.data.lower() or "inv\xe1lid".encode("utf-8") in resp_login_antigo.data

    resp_login_novo = client.post(
        "/login", data={"username": "aluno.redefine@gmail.com", "senha": "senhaNova2"}, follow_redirects=False
    )
    assert resp_login_novo.status_code == 302


def test_redefinir_senha_com_confirmacao_diferente_mostra_erro(client, sem_rede_supabase, monkeypatch):
    with client.application.test_request_context():
        token = aluno_auth_service.gerar_token_redefinicao_senha("aluno-inexistente")

    resp = client.post(
        f"/redefinir-senha/{token}",
        data={"senha": "senhaNova2", "confirmar_senha": "outraCoisa"},
    )
    assert resp.status_code == 200
    assert "nao coincidem".encode() in resp.data.lower() or "n\xe3o coincidem".encode("utf-8") in resp.data


def test_redefinir_senha_com_token_invalido_redireciona_com_aviso(client, sem_rede_supabase):
    resp = client.get("/redefinir-senha/token-forjado", follow_redirects=False)
    assert resp.status_code == 302
    assert "redefinicao_invalida" in resp.headers["Location"]


def test_modulo_de_auth_funciona_sem_flask_instalado(monkeypatch):
    # MELHORIA: este modulo importava flask no topo, entao so dava pra usar
    # dentro do app Flask -- por isso o frontend Streamlit tinha ficado sem
    # login nenhum (entrava digitando o slug da escola). Agora flask e
    # services.email_service sao importados sob demanda, e as duas
    # interfaces compartilham a mesma autenticacao. Este teste simula a
    # ausencia do pacote para garantir que ninguem reintroduza o import no
    # topo sem perceber.
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def sem_flask(nome, *args, **kwargs):
        if nome == "flask" or nome.startswith(("flask.", "flask_")):
            raise ImportError(f"No module named {nome!r} (simulado)")
        return real_import(nome, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", sem_flask)
    monkeypatch.setenv("FLASK_SECRET_KEY", "chave-de-teste")
    for modulo in [m for m in list(sys.modules) if m.startswith("flask")]:
        monkeypatch.delitem(sys.modules, modulo, raising=False)

    modulo = importlib.reload(importlib.import_module("services.aluno_auth_service"))

    assert callable(modulo.autenticar_aluno_por_username)
    assert callable(modulo.autenticar_aluno_por_email)
    token = modulo.gerar_token_confirmacao("aluno-1")
    assert modulo.verificar_token_confirmacao(token) == "aluno-1"
