"""A resposta conta para a questão que estava na tela, e não para outra.

Relatório de QA de 23/09/2026, achado 3.4: no Escape Room o aluno marcou a 3ª
alternativa -- a correta -- e o sistema registrou a 2ª, contou erro e tirou 10
pontos. Não reproduziu numa segunda tentativa, e ficou como "não reproduzido".

A causa está no formato do envio, e vale para todos os modos: o formulário
manda só o ÍNDICE da alternativa, e a rota compara esse índice com a questão
guardada no estado NAQUELE instante. Se a questão guardada trocar entre o
desenho da tela e o envio -- página velha reenviada, botão voltar, duas abas
--, o índice 2 do que o aluno viu vira o índice 2 de outra questão.

Aqui o defeito é reproduzido com as duas questões do próprio relatório, e a
correção é a assinatura da questão viajando junto da resposta.
"""

from __future__ import annotations

import copy

import pytest

import web.routes.escape_room_fla as escape
from web.routes.flask_helpers_fla import assinatura_da_questao

# A questão que o aluno viu (Escape Room · Matemática · 08:34:06 do relatório).
NA_TELA = {
    "pergunta": "O que é probabilidade condicional?",
    "opcoes": [
        "probabilidade de A ou B",
        "probabilidade conjunta de A e B",
        "probabilidade de A ocorrer sabendo que B já ocorreu",
        "probabilidade de A menos B",
    ],
    "correta": 2,
    "nivel": "Medio",
}

# A questão que já estava no lugar dela quando a resposta chegou.
TROCADA = {
    "pergunta": "Qual é a chance de sair cara em uma moeda honesta?",
    "opcoes": ["25%", "50%", "75%", "100%"],
    "correta": 1,
    "nivel": "Medio",
}


def _estado(questao: dict) -> dict:
    return {
        "fase": "sala",
        "nivel": "Medio",
        "salas": [{"numero": 1, "materia": "Matematica", "tema": ""}],
        "atual": 0,
        "historico": [],
        "pistas": [],
        "questao": copy.deepcopy(questao),
        "resultado": None,
    }


@pytest.fixture
def responder(monkeypatch):
    """Envia uma resposta e devolve o estado gravado (vazio se nada gravou)."""
    from flask_app import app

    def rodar(estado: dict, resposta: int, assinatura: str | None) -> dict:
        gravado: dict = {}
        monkeypatch.setattr(escape, "carregar_estado_persistido", lambda *a, **k: copy.deepcopy(estado))
        monkeypatch.setattr(escape, "salvar_estado_persistido", lambda _n, _i, novo: gravado.update(copy.deepcopy(novo)))
        monkeypatch.setattr(escape, "_estado_escape_room", lambda: "estado-de-teste")
        monkeypatch.setattr(escape, "registrar_log_com_tempo", lambda *a, **k: None)
        monkeypatch.setattr(escape, "registrar_pontuacao_acerto", lambda *a, **k: 10)
        dados = {"resposta": str(resposta)}
        if assinatura is not None:
            dados["assinatura_questao"] = assinatura
        with app.test_request_context("/escape-room/responder", method="POST", data=dados):
            escape.responder_escape_room()
        return gravado

    return rodar


def test_resposta_da_questao_que_esta_na_tela_conta_normalmente(responder):
    gravado = responder(_estado(NA_TELA), resposta=2, assinatura=assinatura_da_questao(NA_TELA))

    assert gravado["resultado"]["acertou"] is True
    assert gravado["resultado"]["resposta_aluno"] == NA_TELA["opcoes"][2]


def test_resposta_de_pagina_velha_nao_vira_erro_nem_tira_ponto(responder):
    # O aluno marcou a alternativa certa da questão ANTERIOR; quando o envio
    # chegou, o estado já guardava outra questão.
    gravado = responder(_estado(TROCADA), resposta=2, assinatura=assinatura_da_questao(NA_TELA))

    assert gravado == {}, "nada pode ser gravado: nem erro, nem acerto, nem histórico"


def test_sem_assinatura_a_resposta_continua_sendo_aceita(responder):
    # Página aberta antes desta versão subir: não é para punir o aluno por um
    # deploy no meio da questão.
    gravado = responder(_estado(NA_TELA), resposta=2, assinatura=None)

    assert gravado["resultado"]["acertou"] is True


def test_a_assinatura_muda_quando_a_questao_muda():
    assert assinatura_da_questao(NA_TELA) != assinatura_da_questao(TROCADA)


def test_a_assinatura_nao_muda_entre_duas_leituras_da_mesma_questao():
    # É o que garante que uma resposta legítima nunca seja recusada: a
    # assinatura sai sempre da questão guardada, não do texto renderizado.
    assert assinatura_da_questao(NA_TELA) == assinatura_da_questao(copy.deepcopy(NA_TELA))


def test_alternativa_reordenada_muda_a_assinatura():
    # O caso do relatório: as mesmas alternativas em outra ordem são, para o
    # índice enviado, outra questão.
    outra_ordem = copy.deepcopy(NA_TELA)
    outra_ordem["opcoes"] = list(reversed(NA_TELA["opcoes"]))
    assert assinatura_da_questao(outra_ordem) != assinatura_da_questao(NA_TELA)


def test_sem_questao_nao_ha_assinatura():
    assert assinatura_da_questao(None) == "" and assinatura_da_questao({}) == ""


def test_o_formulario_manda_a_assinatura():
    from pathlib import Path

    molde = (Path(__file__).resolve().parents[1] / "web/templates/partials/options_form.html").read_text(encoding="utf-8")
    assert 'name="assinatura_questao"' in molde, "sem o campo, a rota não tem como saber de que questão é a resposta"


# ------------------------------------------------ os sete modos

OUTRA = {"pergunta": "Outra questão, de outra tela", "opcoes": ["a", "b", "c", "d"], "correta": 0}


def _preparar_modo(nome: str, monkeypatch):
    """Deixa o módulo do modo com NA_TELA guardada e devolve (responder, chamadas)."""
    import importlib

    questao = copy.deepcopy(NA_TELA)
    if nome in ("enem", "boss_rush"):
        # O ENEM e a Batalha chamam a lista de "alternativas".
        questao = {"pergunta": NA_TELA["pergunta"], "alternativas": NA_TELA["opcoes"], "correta": 2}

    modulo = importlib.import_module(f"web.routes.{nome}_fla")
    estados = {
        "escape_room": {"fase": "sala", "nivel": "Medio", "atual": 0, "historico": [], "pistas": [],
                        "salas": [{"numero": 1, "materia": "Matematica", "tema": ""}], "questao": questao, "resultado": None},
        "enem": {"questao": questao, "respondidas": 0, "acertos": 0, "historico": []},
        "boss_rush": {"fase": "battle", "questao": questao, "chefe": 0, "historico": []},
        "treino": {"questao": questao, "materia": "Matematica", "nivel": "Medio", "indice": 0, "total": 5, "historico": []},
        "rpg": {"desafio_atual": questao, "fase": 1, "historico": []},
    }
    if nome in ("escape_room", "enem", "boss_rush"):
        monkeypatch.setattr(modulo, "carregar_estado_persistido", lambda *a, **k: copy.deepcopy(estados[nome]))
        monkeypatch.setattr(modulo, "salvar_estado_persistido", lambda *a, **k: None)
    elif nome == "rpg":
        monkeypatch.setattr(modulo, "_estado_atual", lambda: copy.deepcopy(estados["rpg"]))
    else:
        guardado = {"treino": estados["treino"], "oraculo": questao, "laboratorio": questao}[nome]
        monkeypatch.setattr(modulo, "obter_estado_flask", lambda chave, padrao=None: copy.deepcopy(guardado))
    for enfeite in ("registrar_log_com_tempo", "registrar_pontuacao_acerto", "salvar_estado_flask"):
        if hasattr(modulo, enfeite):
            monkeypatch.setattr(modulo, enfeite, lambda *a, **k: 0)

    responder = {
        "escape_room": "responder_escape_room", "enem": "responder_enem", "boss_rush": "responder_boss_rush",
        "treino": "responder_treino", "oraculo": "responder_oraculo", "laboratorio": "responder_laboratorio",
        "rpg": "responder_desafio",
    }[nome]
    return getattr(modulo, responder), questao


MODOS = ["escape_room", "enem", "boss_rush", "treino", "oraculo", "laboratorio", "rpg"]


@pytest.mark.parametrize("modo", MODOS)
def test_resposta_de_pagina_velha_nao_e_pontuada_em_nenhum_modo(modo, monkeypatch):
    from flask_app import app

    responder, _ = _preparar_modo(modo, monkeypatch)
    with app.test_request_context(
        f"/{modo}/responder", method="POST",
        data={"resposta": "2", "assinatura_questao": assinatura_da_questao(OUTRA)},
    ):
        resposta = responder()

    destino = resposta.headers.get("Location", "") if hasattr(resposta, "headers") else ""
    assert "aviso=questao_trocada" in destino, (
        f"{modo}: pontuou um índice vindo de outra questão (QA de 23/09/2026, achado 3.4)"
    )


@pytest.mark.parametrize("modo", MODOS)
def test_resposta_da_questao_na_tela_passa_em_todos_os_modos(modo, monkeypatch):
    from flask_app import app

    responder, questao = _preparar_modo(modo, monkeypatch)
    with app.test_request_context(
        f"/{modo}/responder", method="POST",
        data={"resposta": "2", "assinatura_questao": assinatura_da_questao(questao)},
    ):
        resposta = responder()

    destino = resposta.headers.get("Location", "") if hasattr(resposta, "headers") else ""
    assert "aviso=questao_trocada" not in destino, f"{modo}: recusou uma resposta legítima"


def test_mesmas_alternativas_com_pergunta_diferente_mudam_a_assinatura():
    outra_pergunta = copy.deepcopy(NA_TELA)
    outra_pergunta["pergunta"] = "Outra pergunta com as mesmas alternativas"
    assert assinatura_da_questao(outra_pergunta) != assinatura_da_questao(NA_TELA)


RAIZ = __import__("pathlib").Path(__file__).resolve().parents[1]


def _rotas_que_recebem_resposta() -> list:
    return sorted(
        caminho for caminho in (RAIZ / "web" / "routes").glob("*_fla.py")
        if 'request.form.get("resposta"' in caminho.read_text(encoding="utf-8-sig")
    )


def test_encontrou_as_rotas_de_resposta():
    # Sem isto, um erro de caminho faria a varredura achar zero rotas e o
    # teste passaria verde cobrindo nada.
    assert len(_rotas_que_recebem_resposta()) == len(MODOS)


def _telas_com_alternativas() -> list:
    return sorted(
        caminho for caminho in (RAIZ / "web" / "templates").glob("*.html")
        if 'name="resposta"' in caminho.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("caminho", _telas_com_alternativas(), ids=lambda c: c.name)
def test_toda_tela_com_alternativas_manda_a_assinatura(caminho):
    fonte = caminho.read_text(encoding="utf-8")
    assert "assinatura_questao" in fonte, f"{caminho.name} desenha alternativas sem mandar a assinatura"
