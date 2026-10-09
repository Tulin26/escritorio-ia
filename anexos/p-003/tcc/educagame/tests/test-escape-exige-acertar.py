"""Escape Room: errar não abre a sala.

Decidido com o usuário em 13/09/2026. Antes a porta abria de qualquer jeito
(só anotava "revisar"), e mandar /proxima sem responder pulava a sala.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

import web.routes.escape_room_fla as escape


def _estado(resultado, atual: int = 0, total: int = 3) -> dict:
    return {
        "fase": "sala",
        "nivel": "Medio",
        "salas": [{"numero": n, "materia": "Historia", "tema": ""} for n in range(1, total + 1)],
        "atual": atual,
        "historico": [],
        "pistas": [],
        "questao": {"pergunta": "Pergunta?", "opcoes": ["a", "b"], "correta": 0},
        "resultado": resultado,
    }


@pytest.fixture
def proxima(monkeypatch):
    from flask_app import app

    def rodar(estado: dict) -> dict:
        gravado: dict = {}
        monkeypatch.setattr(escape, "carregar_estado_persistido", lambda *a, **k: copy.deepcopy(estado))
        monkeypatch.setattr(escape, "salvar_estado_persistido", lambda _nome, _id, novo: gravado.update(copy.deepcopy(novo)))
        monkeypatch.setattr(escape, "_estado_escape_room", lambda: "estado-de-teste")
        with app.test_request_context("/escape-room/proxima", method="POST"):
            escape.proxima_sala()
        return gravado

    return rodar


def test_errou_continua_na_mesma_sala_e_vem_outra_questao(proxima):
    novo = proxima(_estado({"acertou": False}))

    assert novo["atual"] == 0 and novo["fase"] == "sala"
    # A tela gera a questão nova quando encontra a sala sem questão.
    assert novo["questao"] is None and novo["resultado"] is None


def test_acertou_abre_a_proxima_sala(proxima):
    novo = proxima(_estado({"acertou": True}))

    assert novo["atual"] == 1 and novo["fase"] == "sala"


def test_acertou_a_ultima_sala_vai_para_o_relatorio(proxima):
    assert proxima(_estado({"acertou": True}, atual=2, total=3))["fase"] == "resultado"


def test_sem_responder_nao_pula_a_sala(proxima):
    novo = proxima(_estado(None))

    assert novo["atual"] == 0 and novo["fase"] == "sala"


def test_a_tela_diz_que_a_porta_nao_abriu_e_conta_tentativas():
    template = (Path(__file__).resolve().parents[1] / "web" / "templates" / "escape_room.html").read_text(encoding="utf-8")

    assert "Tentar outra questão desta sala" in template
    assert "A porta continua fechada" in template
    # O plural ("1 sala aberta em 1 tentativa") está em tests/test_defeitos_visiveis.py.
    assert "salas abertas" in template
    assert "tentativas" in template
