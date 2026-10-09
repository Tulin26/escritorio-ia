"""A meta e o foco dentro do app: o que grava, o que a tela mostra.

`tests/test_metas_da_semana.py` prende a REGRA (o que conta, quando zera).
Aqui é o encanamento: a partida que termina vira linha no banco, o professor
vê a lista, e o foco anotado chega à tela do aluno.

O ponto mais delicado é o registro da partida concluída. Ele mora nos ramos
que encerram a corrida em `escape_room_fla`, `boss_rush_fla` e `rpg_fla`, e
tem de contar **uma vez só**: `_avancar_cena` do RPG pode ser chamada de novo
com a aventura já encerrada, e um POST repetido em `/proxima` chegaria no
mesmo ramo do Escape Room.
"""

from __future__ import annotations

import pytest

from repositories.meta_repo import (
    listar_conclusoes_da_escola,
    listar_conclusoes_do_aluno,
    listar_focos_do_aluno,
    registrar_conclusao,
    remover_foco,
    salvar_foco,
)
from services.metas_service import MATERIAS_COM_TEMA, metas_da_turma, opcoes_de_foco

ESCOLA = "escola-1"
ALUNO = "aluno-1"


@pytest.fixture
def banco(sem_rede_supabase):
    alunos = sem_rede_supabase.table("alunos")._tabela
    alunos.linhas.extend(
        [
            {"id": ALUNO, "escola_id": ESCOLA, "nome": "Ana Ribeiro", "ano_escolar": "1º Ano EM", "periodo": "Manhã"},
            {"id": "aluno-2", "escola_id": ESCOLA, "nome": "Bruno Sá", "ano_escolar": "7º Ano", "periodo": "Tarde"},
        ]
    )
    return sem_rede_supabase


# --------------------------------------------------------------------------
# Gravar a partida


def test_conclusao_gravada_aparece_para_o_aluno_e_para_a_escola(banco):
    assert registrar_conclusao(ALUNO, ESCOLA, "escape_room", acertos=5, total=6) is True

    do_aluno = listar_conclusoes_do_aluno(ALUNO)
    assert len(do_aluno) == 1
    assert do_aluno[0]["modo"] == "escape_room"
    assert do_aluno[0]["acertos"] == 5
    assert len(listar_conclusoes_da_escola(ESCOLA)) == 1


@pytest.mark.parametrize(("aluno", "escola"), [("", ESCOLA), (ALUNO, ""), ("", "")])
def test_sem_aluno_ou_escola_nao_grava(banco, aluno, escola):
    # O aluno não logado (Escape Room aberto direto pela URL) não pode criar
    # linha órfã: ela nunca seria contada nem apagada por pedido de LGPD.
    assert registrar_conclusao(aluno, escola, "rpg") is False
    assert listar_conclusoes_da_escola(ESCOLA) == []


def test_helper_do_flask_conta_os_acertos_do_historico(banco, client):
    from web.routes.flask_helpers_fla import registrar_partida_concluida

    with client.session_transaction() as sessao:
        sessao["aluno_id"] = ALUNO
        sessao["escola_id"] = ESCOLA

    with client.application.test_request_context():
        from flask import session

        session["aluno_id"] = ALUNO
        session["escola_id"] = ESCOLA
        historico = [{"acertou": True}, {"acertou": False}, {"acertou": True}]
        assert registrar_partida_concluida("boss_rush", historico) is True

    gravada = listar_conclusoes_do_aluno(ALUNO)[0]
    assert (gravada["acertos"], gravada["total"]) == (2, 3)


def test_helper_sem_sessao_nao_grava(banco, client):
    from web.routes.flask_helpers_fla import registrar_partida_concluida

    with client.application.test_request_context():
        assert registrar_partida_concluida("rpg", [{"acertou": True}]) is False


@pytest.mark.parametrize(
    ("arquivo", "guarda"),
    [
        ("web/routes/escape_room_fla.py", 'if estado.get("fase") != "resultado":'),
        ("web/routes/boss_rush_fla.py", 'if estado.get("fase") != "resultado":'),
        ("web/routes/rpg_fla.py", 'if not estado.get("status"):'),
    ],
)
def test_o_registro_tem_guarda_contra_contar_duas_vezes(arquivo, guarda):
    # Sem a guarda, um POST repetido (ou uma segunda chamada de _avancar_cena
    # com a aventura já encerrada) contaria a mesma partida de novo, e a meta
    # da semana fecharia sozinha.
    from pathlib import Path

    texto = (Path(__file__).resolve().parents[1] / arquivo).read_text(encoding="utf-8")
    assert "registrar_partida_concluida" in texto
    assert guarda in texto


# --------------------------------------------------------------------------
# Foco de estudo


def test_foco_salvo_e_lido(banco):
    ok, erro = salvar_foco(ALUNO, ESCOLA, "Matematica", "progressao aritmetica", "revisar antes da prova", "prof")

    assert (ok, erro) == (True, "")
    focos = listar_focos_do_aluno(ALUNO)
    assert len(focos) == 1
    assert focos[0]["tema"] == "progressao aritmetica"
    assert focos[0]["observacao"] == "revisar antes da prova"


def test_um_foco_por_materia_o_segundo_troca_o_tema(banco):
    salvar_foco(ALUNO, ESCOLA, "Matematica", "progressao aritmetica")
    salvar_foco(ALUNO, ESCOLA, "Matematica", "funcao do 2o grau")

    focos = listar_focos_do_aluno(ALUNO)
    assert len(focos) == 1, "o mesmo aluno não pode ficar com dois focos da mesma matéria"
    assert focos[0]["tema"] == "funcao do 2o grau"


def test_materias_diferentes_convivem(banco):
    salvar_foco(ALUNO, ESCOLA, "Matematica", "progressao aritmetica")
    salvar_foco(ALUNO, ESCOLA, "Historia", "Era Vargas")

    assert {foco["tema"] for foco in listar_focos_do_aluno(ALUNO)} == {
        "progressao aritmetica",
        "Era Vargas",
    }


@pytest.mark.parametrize(
    ("aluno", "escola", "materia", "tema"),
    [
        ("", ESCOLA, "Matematica", "tema"),
        (ALUNO, "", "Matematica", "tema"),
        (ALUNO, ESCOLA, "", "tema"),
        (ALUNO, ESCOLA, "Matematica", "   "),
    ],
)
def test_foco_incompleto_e_recusado_com_motivo(banco, aluno, escola, materia, tema):
    ok, erro = salvar_foco(aluno, escola, materia, tema)

    assert ok is False
    assert erro, "recusar em silêncio deixaria o professor achando que salvou"


def test_remover_foco_tira_so_a_materia_pedida(banco):
    salvar_foco(ALUNO, ESCOLA, "Matematica", "progressao aritmetica")
    salvar_foco(ALUNO, ESCOLA, "Historia", "Era Vargas")

    remover_foco(ALUNO, "Matematica")

    assert [foco["materia"] for foco in listar_focos_do_aluno(ALUNO)] == ["Historia"]


def test_os_temas_oferecidos_sao_os_que_o_gerador_conhece():
    # Texto livre deixaria o professor anotar um tema que o gerador não sorteia
    # nunca -- e o botão "treinar este tema" abriria o Oráculo num assunto
    # que ele não conhece.
    opcoes = opcoes_de_foco("1º Ano EM")
    assert opcoes, "nenhuma matéria com tema: o formulário do professor ficaria vazio"

    matematica = next(op for op in opcoes if op["materia"] == "Matematica")
    assert "progressao aritmetica (PA)" in matematica["temas"] or any(
        "progressao" in tema for tema in matematica["temas"]
    )
    assert all(op["materia"] in MATERIAS_COM_TEMA for op in opcoes)


def test_a_serie_do_aluno_muda_a_lista_de_temas():
    # O 7º ano não pode receber a lista do Ensino Médio.
    em = next(op for op in opcoes_de_foco("1º Ano EM") if op["materia"] == "Matematica")["temas"]
    ef = next(op for op in opcoes_de_foco("7º Ano") if op["materia"] == "Matematica")["temas"]

    assert em != ef
    assert any("Bhaskara" in tema or "2o grau" in tema for tema in em)
    assert not any("Bhaskara" in tema for tema in ef)


# --------------------------------------------------------------------------
# A lista do professor


def test_lista_do_professor_traz_cada_aluno_com_o_que_ja_fez(banco):
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc)
    logs = [
        {"aluno_id": ALUNO, "modo": "oraculo-flask", "data_hora": agora.isoformat(), "tempo_resposta": 20}
        for _ in range(4)
    ]
    registrar_conclusao(ALUNO, ESCOLA, "rpg")
    salvar_foco(ALUNO, ESCOLA, "Matematica", "progressao aritmetica")

    linhas = metas_da_turma(ESCOLA, banco.table("alunos")._tabela.linhas, logs)

    por_nome = {linha["nome"]: linha for linha in linhas}
    ana = por_nome["Ana Ribeiro"]
    assert next(i for i in ana["itens"] if i["chave"] == "conceito")["feito"] == 4
    assert next(i for i in ana["itens"] if i["chave"] == "jornada")["cumprida"] is True
    assert ana["focos"][0]["tema"] == "progressao aritmetica"
    # Bruno não fez nada: tem de aparecer, e zerado.
    assert por_nome["Bruno Sá"]["cumpridas"] == 0


def test_quem_esta_mais_longe_da_meta_aparece_primeiro(banco):
    registrar_conclusao(ALUNO, ESCOLA, "rpg")

    linhas = metas_da_turma(ESCOLA, banco.table("alunos")._tabela.linhas, [])

    assert linhas[0]["nome"] == "Bruno Sá", "a lista serve para achar quem precisa de empurrão"


def test_sem_escola_nao_lista_ninguem(banco):
    assert metas_da_turma("", banco.table("alunos")._tabela.linhas, []) == []
