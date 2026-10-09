"""Os defeitos cosmeticos do relatorio de QA de 23/09/2026 (secao 6, item 11).

Cada teste aqui prende um dos achados de interface: sinal duplicado no
placar do RPG, numero de fase interno vazando no titulo da sala, texto de
outro modo ("Oraculo") vazando dentro do Escape Room, salas repetidas sem
indicador de tentativa na Revisao final, e o selo de origem em ingles numa
interface em portugues.
"""

from __future__ import annotations

import re

from services.ia.enigma import _enigma_oracular
from services.rpg_service import continuar_aventura


# ====================== RPG · "Pontos: +-10" ======================


def test_template_do_rpg_nao_concatena_mais_e_menos():
    texto = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "web" / "templates" / "rpg.html"
    ).read_text(encoding="utf-8")

    assert "Pontos: +{{" not in texto


# ====================== RPG · numero de fase interno vazando ======================


def test_titulo_da_sala_bate_com_a_fase_que_o_hud_vai_mostrar():
    # MELHORIA: era len(historico) + 2. Uma fase com desafio grava DOIS
    # registros no historico (a escolha e a resposta), entao apos 5 fases
    # concluidas -- todas com desafio -- o titulo da proxima sala dizia
    # "fase 11" enquanto o HUD (estado["fase"], incrementado uma vez por
    # fase de verdade) ia mostrar "Fase 6". Ver web/routes/rpg_fla.py::
    # _avancar_cena, que faz estado["fase"] = fase_atual + 1.
    historico = []
    for fase in range(1, 6):
        historico.append({"fase": fase, "acao": "escolha"})
        historico.append({"fase": fase, "acao": "desafio", "acertou": True})

    cena = continuar_aventura(
        {"materia": "Matematica"}, historico, "avancar", None, {}, None, None
    )

    assert "fase 6" in cena["local_atual"].lower(), cena["local_atual"]


def test_titulo_da_sala_bate_sem_desafio_nenhum():
    # O caso sem desafio (so escolhas) ja batia antes -- continua batendo.
    historico = [{"fase": fase, "acao": "escolha"} for fase in range(1, 4)]

    cena = continuar_aventura(
        {"materia": "Matematica"}, historico, "avancar", None, {}, None, None
    )

    assert "fase 4" in cena["local_atual"].lower(), cena["local_atual"]


# ====================== "Oraculo" vazando no enigma generico ======================


def test_enigma_generico_nao_cita_o_nome_de_nenhum_modo():
    # Achado de interface do relatorio de QA: o par generico do enigma
    # citava "o Oraculo" e vazava pro Escape Room, RPG e Treino Rapido, que
    # reaproveitam a mesma funcao (invocar_enigma). "sinais de cidadania" e
    # "sinais de producao artistica" foram vistos dentro do Escape Room.
    for _ in range(30):
        frase = _enigma_oracular("Arte", "producao artistica")
        assert "oraculo" not in frase.lower(), frase


# ====================== Escape Room · salas repetidas sem indicador ======================


def test_segunda_tentativa_na_mesma_sala_fica_marcada_no_historico(monkeypatch):
    import copy

    import web.routes.escape_room_fla as escape
    from flask_app import app

    estado = {
        "atual": 0,
        "salas": [{"numero": 1, "materia": "Historia", "tema": ""}],
        "questao": {"pergunta": "P?", "opcoes": ["a", "b"], "correta": 0},
        "historico": [],
        "pistas": [],
    }
    gravado: dict = {}

    def responder(indice_marcado: int) -> dict:
        monkeypatch.setattr(escape, "carregar_estado_persistido", lambda *a, **k: copy.deepcopy(estado))
        monkeypatch.setattr(escape, "salvar_estado_persistido", lambda _nome, _id, novo: gravado.update(copy.deepcopy(novo)))
        monkeypatch.setattr(escape, "_estado_escape_room", lambda: "estado-de-teste")
        with app.test_request_context("/escape-room/responder", method="POST", data={"resposta": str(indice_marcado)}):
            escape.responder_escape_room()
        estado.update(gravado)
        return gravado

    primeira = responder(1)  # errou -- indice 1 nao e o 0 correto
    assert primeira["historico"][-1]["tentativa"] == 1
    assert "tentativa" not in primeira["pistas"][-1]

    segunda = responder(0)  # acertou na segunda tentativa da MESMA sala
    assert segunda["historico"][-1]["tentativa"] == 2
    assert "tentativa 2" in segunda["pistas"][-1]


def test_template_desenha_a_tentativa_quando_repete_sala():
    template = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "web" / "templates" / "escape_room.html"
    ).read_text(encoding="utf-8")

    assert "item.tentativa" in template


# ====================== Selo de origem em portugues ======================


def test_selo_de_origem_offline_do_enem_esta_em_portugues():
    from web.routes.enem_fla import _questao_para_template

    pronta = _questao_para_template({"pergunta": "?", "_origem": "offline", "explicacao": []})

    assert pronta["origem_label"] != "offline"
    assert re.search(r"[a-zA-ZÀ-ÿ]", pronta["origem_label"])
