"""Meta semanal de exercícios e foco de estudo por aluno.

Pedido da coordenação em 28/09/2026: metas semanais por modo, o professor
vendo quanto cada aluno já fez, zerando toda semana; e um tema anotado por
aluno ("Aluno X fica com progressão aritmética").

As três decisões de projeto que estes testes prendem:

1. **A unidade muda de modo para modo.** Oráculo, Treino e Laboratório contam
   QUESTÕES; Escape Room, Batalha e RPG contam PARTIDA CONCLUÍDA. Se
   contassem questões, bastaria abrir dez Escape Rooms e responder a primeira
   sala de cada para fechar a cota sem terminar nada.
2. **A semana zera na segunda, no horário de Brasília.** Sem fuso, a semana
   viraria às 21h de domingo -- `data_hora` é gravado em UTC.
3. **Resposta rápida demais não conta.** Meta por quantidade é o incentivo
   exato para clicar sem ler. Medido nas 554 respostas reais: a mais rápida
   levou 6,5 s e a mediana é 20,1 s, então o piso de 5 s não tira ninguém
   hoje -- ele existe para o dia em que a meta mudar o comportamento.

O foco é um tema da lista que o próprio gerador usa (`core.config`), não
texto livre, e NÃO muda sozinho o que o aluno recebe: aparece na tela com um
botão que o aluno clica se quiser.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.metas import (
    FUSO_ESCOLAR,
    METAS,
    inicio_da_semana,
    normalizar_modo,
    progresso_semanal,
    resposta_conta,
)

# Quarta-feira, 30/09/2026, 10h em Brasília.
AGORA = datetime(2026, 9, 30, 10, 0, tzinfo=FUSO_ESCOLAR)


def _log(modo: str, quando: datetime, tempo: float = 20.0) -> dict:
    return {"modo": modo, "data_hora": quando.isoformat(), "tempo_resposta": tempo}


def _conclusao(modo: str, quando: datetime) -> dict:
    return {"modo": modo, "concluido_em": quando.isoformat()}


def _item(progresso: dict, chave: str) -> dict:
    return next(item for item in progresso["itens"] if item["chave"] == chave)


# --------------------------------------------------------------------------
# A semana


def test_semana_comeca_na_segunda_de_brasilia():
    inicio = inicio_da_semana(AGORA)

    assert inicio.astimezone(FUSO_ESCOLAR).weekday() == 0
    assert inicio.astimezone(FUSO_ESCOLAR).hour == 0
    # Segunda 00:00 em Brasília é segunda 03:00 em UTC -- é essa hora que a
    # consulta manda ao banco, onde data_hora está em UTC.
    assert inicio.astimezone(timezone.utc).hour == 3


def test_domingo_a_noite_ainda_e_a_semana_que_passou():
    # 22h de domingo em Brasília já é segunda em UTC. Sem fuso, a resposta
    # desse aluno cairia na semana seguinte e a meta dele zeraria cedo demais.
    domingo = datetime(2026, 9, 27, 22, 0, tzinfo=FUSO_ESCOLAR)

    assert domingo < inicio_da_semana(AGORA)


def test_o_que_e_de_antes_da_segunda_nao_conta():
    passada = AGORA - timedelta(days=7)
    progresso = progresso_semanal([_log("oraculo-flask", passada)] * 10, [], AGORA)

    assert _item(progresso, "conceito")["feito"] == 0


# --------------------------------------------------------------------------
# Contagem por questão


def test_oraculo_e_treino_somam_na_mesma_meta():
    logs = [_log("oraculo-flask", AGORA)] * 6 + [_log("treino-flask", AGORA)] * 4
    progresso = progresso_semanal(logs, [], AGORA)

    conceito = _item(progresso, "conceito")
    assert conceito["feito"] == 10
    assert conceito["cumprida"] is True
    assert conceito["faltam"] == 0


def test_laboratorio_tem_meta_propria_e_menor():
    # 5 e não 10: é o modo mais lento medido (quartil superior de 55,4 s).
    logs = [_log("laboratorio-flask", AGORA)] * 5
    progresso = progresso_semanal(logs, [], AGORA)

    assert _item(progresso, "calculo")["alvo"] == 5
    assert _item(progresso, "calculo")["cumprida"] is True
    assert _item(progresso, "conceito")["feito"] == 0


def test_enem_nao_entra_em_meta_nenhuma():
    # Simulado tem cadência própria (uma vez por quinzena), não semanal.
    progresso = progresso_semanal([_log("enem-flask", AGORA)] * 20, [], AGORA)

    assert all(item["feito"] == 0 for item in progresso["itens"])


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("oraculo-flask", "oraculo"),
        ("laboratorio-flask", "laboratorio"),
        ("escape_room-flask", "escape_room"),
        ("boss_rush_enem-flask", "boss_rush"),
        ("rpg-flask", "rpg"),
        ("oraculo-streamlit", "oraculo"),
        ("Oraculo", "oraculo"),
    ],
)
def test_o_sufixo_do_frontend_sai_do_nome_do_modo(bruto, esperado):
    # O log grava o frontend junto. Sem tirar, o dia em que alguém abrir o
    # Streamlit o aluno começaria a semana do zero.
    assert normalizar_modo(bruto) == esperado


# --------------------------------------------------------------------------
# Clique sem ler


@pytest.mark.parametrize("tempo", [0, 0.5, 4.9])
def test_resposta_rapida_demais_nao_conta(tempo):
    assert resposta_conta({"tempo_resposta": tempo}) is False


@pytest.mark.parametrize("tempo", [5.0, 6.5, 20.1, None, ""])
def test_resposta_com_tempo_de_gente_conta(tempo):
    # Tempo ausente conta: linha antiga, de antes de o campo existir, não
    # pode virar dívida para o aluno.
    assert resposta_conta({"tempo_resposta": tempo}) is True


def test_dez_cliques_rapidos_nao_fecham_a_meta():
    progresso = progresso_semanal([_log("oraculo-flask", AGORA, tempo=1.0)] * 10, [], AGORA)

    assert _item(progresso, "conceito")["feito"] == 0


# --------------------------------------------------------------------------
# Partida concluída


def test_jornada_conta_partida_e_nao_questao():
    # 30 questões de Escape Room sem terminar nenhuma corrida: a meta da
    # jornada continua zerada.
    logs = [_log("escape_room-flask", AGORA)] * 30
    progresso = progresso_semanal(logs, [], AGORA)

    assert _item(progresso, "jornada")["feito"] == 0


@pytest.mark.parametrize("modo", ["escape_room", "boss_rush", "rpg"])
def test_qualquer_um_dos_tres_fecha_a_jornada(modo):
    # É uma meta só, à escolha do aluno: exigir os três transformaria em
    # dever de casa justamente a parte que ele faz por vontade própria.
    progresso = progresso_semanal([], [_conclusao(modo, AGORA)], AGORA)

    assert _item(progresso, "jornada")["cumprida"] is True


def test_partida_da_semana_passada_nao_conta():
    progresso = progresso_semanal([], [_conclusao("rpg", AGORA - timedelta(days=8))], AGORA)

    assert _item(progresso, "jornada")["feito"] == 0


# --------------------------------------------------------------------------
# A barra


def test_barra_para_na_meta():
    progresso = progresso_semanal([_log("oraculo-flask", AGORA)] * 25, [], AGORA)
    conceito = _item(progresso, "conceito")

    assert conceito["feito"] == 25
    assert conceito["percentual"] == 100, "18 de 10 desenha 100%, não 180%"


def test_tudo_feito_exige_as_tres():
    logs = [_log("oraculo-flask", AGORA)] * 10 + [_log("laboratorio-flask", AGORA)] * 5
    parcial = progresso_semanal(logs, [], AGORA)
    completo = progresso_semanal(logs, [_conclusao("rpg", AGORA)], AGORA)

    assert parcial["tudo_feito"] is False
    assert parcial["cumpridas"] == 2
    assert completo["tudo_feito"] is True
    assert completo["cumpridas"] == len(METAS)


def test_semana_sem_nada_nao_estoura():
    progresso = progresso_semanal(None, None, AGORA)

    assert progresso["cumpridas"] == 0
    assert [item["feito"] for item in progresso["itens"]] == [0, 0, 0]
