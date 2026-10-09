from __future__ import annotations

import pytest

import web.routes.treino_fla as treino_fla

from tests.apoio_flask import carimbar_sessao


def _logar_como_aluno(client) -> None:
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        sess["aluno_id"] = "aluno-1"
        sess["aluno_nome"] = "Aluno Teste"
        sess["ano_escolar"] = "1º EM"
        carimbar_sessao(sess)


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
    ],
)
def test_rota_de_jogo_carrega_sem_erro_para_aluno_logado(client, sem_rede_supabase, rota):
    _logar_como_aluno(client)

    resp = client.get(rota)

    assert resp.status_code == 200


def test_treino_fluxo_completo_iniciar_ver_responder_resultado(client, monkeypatch, sem_rede_supabase):
    questao_fake = {
        "pergunta": "Quanto vale a soma de 2 mais 2?",
        "opcoes": ["3", "4", "5", "6"],
        "correta": 1,
        "explicacao": [],
        "passos_resolucao": [],
        "formula": "",
        "subformulas": [],
    }
    monkeypatch.setattr(treino_fla, "invocar_enigma", lambda *args, **kwargs: dict(questao_fake))
    monkeypatch.setattr(treino_fla, "obter_ultimo_erro_ia", lambda: "")

    _logar_como_aluno(client)

    resp_iniciar = client.post(
        "/treino/iniciar",
        data={"materia": "Matematica", "nivel": "Medio", "total": "5"},
        follow_redirects=False,
    )
    assert resp_iniciar.status_code == 302

    resp_tela = client.get("/treino/")
    assert resp_tela.status_code == 200
    assert "Quanto vale a soma de 2 mais 2".encode() in resp_tela.data

    resp_responder = client.post("/treino/responder", data={"resposta": "1"}, follow_redirects=True)
    assert resp_responder.status_code == 200
    assert b"Acertou" in resp_responder.data


def test_treino_resposta_errada_mostra_errou(client, monkeypatch, sem_rede_supabase):
    questao_fake = {
        "pergunta": "Quanto vale a soma de 2 mais 2?",
        "opcoes": ["3", "4", "5", "6"],
        "correta": 1,
        "explicacao": [],
        "passos_resolucao": [],
        "formula": "",
        "subformulas": [],
    }
    monkeypatch.setattr(treino_fla, "invocar_enigma", lambda *args, **kwargs: dict(questao_fake))
    monkeypatch.setattr(treino_fla, "obter_ultimo_erro_ia", lambda: "")

    _logar_como_aluno(client)
    client.post("/treino/iniciar", data={"materia": "Matematica", "nivel": "Medio", "total": "5"})

    resp = client.post("/treino/responder", data={"resposta": "0"}, follow_redirects=True)

    assert resp.status_code == 200
    assert b"Errou" in resp.data


def test_treino_reiniciar_limpa_o_estado(client, monkeypatch, sem_rede_supabase):
    questao_fake = {
        "pergunta": "Pergunta de teste",
        "opcoes": ["a", "b"],
        "correta": 0,
        "explicacao": [],
        "passos_resolucao": [],
    }
    monkeypatch.setattr(treino_fla, "invocar_enigma", lambda *args, **kwargs: dict(questao_fake))
    monkeypatch.setattr(treino_fla, "obter_ultimo_erro_ia", lambda: "")

    _logar_como_aluno(client)
    client.post("/treino/iniciar", data={"materia": "Matematica", "nivel": "Medio"})
    resp_com_questao = client.get("/treino/")
    assert b"Pergunta de teste" in resp_com_questao.data

    client.post("/treino/reiniciar")
    resp_apos_reiniciar = client.get("/treino/")

    assert b"Pergunta de teste" not in resp_apos_reiniciar.data
