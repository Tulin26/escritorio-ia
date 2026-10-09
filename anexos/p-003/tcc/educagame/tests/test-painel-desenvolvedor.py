"""Painel do desenvolvedor: redefinicao de senha de aluno e diagnostico."""

from __future__ import annotations

import re

import pytest

from web.routes import professor_fla

from tests.apoio_flask import carimbar_sessao


def _sem_rede(monkeypatch, alunos=None):
    monkeypatch.setattr(professor_fla, "buscar_alunos", lambda escola_id: list(alunos or []))
    monkeypatch.setattr(professor_fla, "buscar_logs", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "buscar_resumo_turma", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "listar_rpg_configs", lambda escola_id: [])
    monkeypatch.setattr(
        professor_fla,
        "listar_escolas",
        lambda: [{"id": "esc-1", "nome": "ETEC", "slug": "etec"}],
    )


def _como_desenvolvedor(client):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "desenvolvedor"
        carimbar_sessao(sess)


# ====================== SENHA DE ALUNO ======================


def test_desenvolvedor_redefine_senha_e_ve_a_senha_uma_vez(client, monkeypatch):
    # MELHORIA: a recuperacao por e-mail nao serve para quem nao tem e-mail
    # cadastrado -- boa parte da turma. Sem isto, a unica saida era mexer no
    # Supabase na mao.
    _sem_rede(monkeypatch, alunos=[{"id": "a1", "nome": "Ronnie Rillo"}])
    trocas = []
    monkeypatch.setattr(
        professor_fla,
        "redefinir_senha_do_aluno",
        lambda aluno_id, *a, **k: (trocas.append(aluno_id) or (True, "", "ab3xy7")),
    )
    _como_desenvolvedor(client)

    resp = client.post(
        "/professor/adm/aluno/senha",
        data={"aluno_id": "a1", "escola_admin_id": "esc-1"},
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert trocas == ["a1"]
    # a senha volta na mensagem: e a unica vez que ela existe legivel
    assert "ab3xy7" in resp.headers["Location"]
    assert "Ronnie" in resp.headers["Location"]


def test_professor_nao_redefine_senha_de_aluno(client, monkeypatch):
    _sem_rede(monkeypatch)
    chamou = []
    monkeypatch.setattr(
        professor_fla,
        "redefinir_senha_do_aluno",
        lambda *a, **k: (chamou.append(1) or (True, "", "xxxxxx")),
    )
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        carimbar_sessao(sess)

    resp = client.post(
        "/professor/adm/aluno/senha", data={"aluno_id": "a1"}, follow_redirects=False
    )

    assert resp.status_code == 302
    assert not chamou, "professor nao pode trocar senha de aluno"
    assert "restrito" in resp.headers["Location"].lower()


def test_erro_do_servico_vira_mensagem_e_nao_500(client, monkeypatch):
    _sem_rede(monkeypatch)
    monkeypatch.setattr(
        professor_fla,
        "redefinir_senha_do_aluno",
        lambda *a, **k: (False, "Selecione um aluno.", ""),
    )
    _como_desenvolvedor(client)

    resp = client.post("/professor/adm/aluno/senha", data={"aluno_id": ""})

    assert resp.status_code == 302
    assert "Selecione" in resp.headers["Location"]


# ====================== GERADOR DE SENHA ======================


def test_senha_gerada_e_legivel_em_papel():
    # A senha vai impressa para o aluno: "i", "l", "o", "0" e "1" viram erro
    # de digitacao garantido na letra de forma.
    from services.aluno_auth_service import gerar_senha_legivel

    senhas = [gerar_senha_legivel() for _ in range(300)]

    assert all(len(s) == 6 for s in senhas)
    assert not any(c in s for s in senhas for c in "ilo01")
    assert all(any(c.isalpha() for c in s) for s in senhas)
    assert all(any(c.isdigit() for c in s) for s in senhas)
    assert len(set(senhas)) > 250, "gerador com pouca variacao"


def test_script_de_turma_usa_o_mesmo_gerador():
    # Duas copias do alfabeto divergiriam na primeira vez que alguem mexesse
    # numa so.
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "scripts" / "criar_alunos_teste.py"
    fonte = script.read_text(encoding="utf-8")

    assert "gerar_senha_legivel" in fonte
    assert "abcdefghjkmnpqrstuvwxyz" not in fonte, "alfabeto duplicado no script"


# ====================== DIAGNOSTICO ======================


def test_diagnostico_aparece_para_desenvolvedor(client, monkeypatch):
    # MELHORIA: "o Groq esta funcionando?" so era respondivel lendo o log do
    # Render. As pecas ja existiam no codigo, sem tela nenhuma.
    _sem_rede(monkeypatch)
    monkeypatch.setattr(
        professor_fla,
        "_diagnostico_do_sistema",
        lambda: {
            "config": [],
            "ultimo_provedor_ia": "groq",
            "ultimo_erro_ia": "",
            "supabase": {"projeto_ref": "abc123", "jwt_role": "service_role"},
        },
    )
    _como_desenvolvedor(client)

    resp = client.get("/professor/?aba=adm")
    corpo = resp.data.decode("utf-8")

    assert resp.status_code == 200
    assert "Diagnóstico do sistema" in corpo
    assert "groq" in corpo
    assert "service_role" in corpo


def test_diagnostico_mostra_erro_de_configuracao(client, monkeypatch):
    _sem_rede(monkeypatch)
    monkeypatch.setattr(
        professor_fla,
        "_diagnostico_do_sistema",
        lambda: {
            "config": [("erro", "GROQ_MODEL sem prefixo de fornecedor")],
            "ultimo_provedor_ia": "mistral",
            "ultimo_erro_ia": "",
            "supabase": {},
        },
    )
    _como_desenvolvedor(client)

    corpo = client.get("/professor/?aba=adm").data.decode("utf-8")

    assert "GROQ_MODEL sem prefixo" in corpo
    assert "ERRO" in corpo


def test_diagnostico_nao_vaza_para_professor(client, monkeypatch):
    _sem_rede(monkeypatch)
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        carimbar_sessao(sess)

    corpo = client.get("/professor/?aba=adm").data.decode("utf-8")

    assert "Diagnóstico do sistema" not in corpo


# ====================== PARIDADE COM O STREAMLIT ======================


def test_streamlit_tem_as_mesmas_duas_secoes():
    # MELHORIA: os dois frontends dividem core/ e services/ desde a
    # unificacao, mas a INTERFACE e separada -- funcionalidade nova so no
    # Flask recria a divergencia que a unificacao acabou de resolver.
    from pathlib import Path

    admin_st = Path(__file__).resolve().parent.parent / "st" / "ui" / "admin_st.py"
    if not admin_st.is_file():
        pytest.skip("frontend Streamlit ausente nesta branch")

    fonte = admin_st.read_text(encoding="utf-8-sig")

    assert "redefinir_senha_do_aluno" in fonte
    assert "verificar_configuracao" in fonte
    assert "obter_ultimo_provedor_ia" in fonte
    # as duas seccoes precisam estar LIGADAS na tela, nao so definidas
    assert fonte.count("_secao_senha_de_aluno") >= 2
    assert fonte.count("_secao_diagnostico") >= 2


def test_streamlit_nao_reimplementa_o_gerador_de_senha():
    from pathlib import Path

    admin_st = Path(__file__).resolve().parent.parent / "st" / "ui" / "admin_st.py"
    if not admin_st.is_file():
        pytest.skip("frontend Streamlit ausente nesta branch")

    fonte = admin_st.read_text(encoding="utf-8-sig")

    assert "abcdefghjkmnpqrstuvwxyz" not in fonte, "alfabeto de senha duplicado"


def test_fora_da_aba_adm_nao_busca_dados_do_adm(client, monkeypatch):
    # MELHORIA: alunos_admin, escolas e o diagnostico alimentam SO o
    # admin_panel.html, que renderiza apenas na aba "adm". Eram buscados em
    # toda carga do painel -- e cada leitura e uma ida a rede, porque ate o
    # cache mora no Supabase (ver core/runtime_context.py).
    _sem_rede(monkeypatch)
    chamadas = []
    monkeypatch.setattr(
        professor_fla, "listar_escolas", lambda: chamadas.append("escolas") or []
    )
    monkeypatch.setattr(
        professor_fla, "_diagnostico_do_sistema", lambda: chamadas.append("diagnostico") or {}
    )
    _como_desenvolvedor(client)

    client.get("/professor/?aba=analises")

    assert "diagnostico" not in chamadas, "montou o diagnostico fora da aba ADM"
    # _escola_atual precisa de listar_escolas em toda pagina, para resolver a
    # escola da sessao -- mas UMA vez, nao duas. A segunda era so do ADM.
    assert chamadas.count("escolas") <= 1, f"listou escolas mais de uma vez: {chamadas}"


def test_na_aba_adm_busca_os_dados(client, monkeypatch):
    _sem_rede(monkeypatch)
    chamadas = []
    monkeypatch.setattr(
        professor_fla,
        "listar_escolas",
        lambda: chamadas.append("escolas") or [{"id": "esc-1", "nome": "ETEC", "slug": "etec"}],
    )
    monkeypatch.setattr(
        professor_fla,
        "_diagnostico_do_sistema",
        lambda: chamadas.append("diagnostico")
        or {"config": [], "ultimo_provedor_ia": "", "ultimo_erro_ia": "", "supabase": {}},
    )
    _como_desenvolvedor(client)

    client.get("/professor/?aba=adm")

    assert "escolas" in chamadas
    assert "diagnostico" in chamadas
