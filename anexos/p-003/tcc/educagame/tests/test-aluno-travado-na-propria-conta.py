"""O aluno autenticado nao pode assumir a conta de outro aluno.

Antes do login por usuario e senha, o aluno_id vinha do formulario ou da
URL e sobrescrevia a sessao: bastava escolher outro nome no seletor (ou
mandar outro id na requisicao) para jogar, pontuar e ver o desempenho no
lugar do colega. Professor e desenvolvedor seguem podendo trocar.
"""

from __future__ import annotations

import pytest

from web.routes import flask_helpers_fla as helpers

EU = {"id": "aluno-eu", "nome": "Aluno 14", "ano_escolar": "1º Ano EM", "escola_id": "esc-1"}
OUTRO = {"id": "aluno-outro", "nome": "Aluno 16", "ano_escolar": "1º Ano EM", "escola_id": "esc-1"}
TODOS = [EU, OUTRO]


@pytest.fixture
def sessao_falsa(monkeypatch):
    estado: dict = {}
    monkeypatch.setattr(helpers, "session", estado, raising=False)
    monkeypatch.setattr(
        helpers,
        "buscar_aluno_por_id",
        lambda i: next((a for a in TODOS if a["id"] == str(i)), None),
        raising=False,
    )
    monkeypatch.setattr(helpers, "buscar_alunos", lambda _e: list(TODOS), raising=False)
    return estado


class _RequisicaoFalsa:
    def __init__(self, form=None):
        self.form = form or {}


def _entrar_como(estado, papel, aluno_id=""):
    estado["usuario_role"] = papel
    estado["escola_id"] = "esc-1"
    if aluno_id:
        estado["aluno_id"] = aluno_id
        estado["aluno_nome"] = EU["nome"]


def test_aluno_logado_fica_preso_a_propria_conta(monkeypatch, sessao_falsa):
    _entrar_como(sessao_falsa, "aluno", EU["id"])
    # O POST tenta se passar pelo colega.
    monkeypatch.setattr(
        helpers, "request", _RequisicaoFalsa({"aluno_id": OUTRO["id"]}), raising=False
    )

    aluno = helpers.sincronizar_aluno_da_requisicao()

    assert aluno["id"] == EU["id"], "aluno assumiu a conta de outro pelo formulario"
    assert sessao_falsa["aluno_id"] == EU["id"]
    assert sessao_falsa["aluno_nome"] == EU["nome"]


@pytest.mark.parametrize("papel", ["professor", "desenvolvedor"])
def test_professor_continua_podendo_abrir_outro_aluno(monkeypatch, sessao_falsa, papel):
    _entrar_como(sessao_falsa, papel)
    monkeypatch.setattr(
        helpers, "request", _RequisicaoFalsa({"aluno_id": OUTRO["id"]}), raising=False
    )

    aluno = helpers.sincronizar_aluno_da_requisicao()

    assert aluno["id"] == OUTRO["id"], "professor precisa acompanhar aluno especifico"


def test_seletor_so_lista_o_proprio_aluno(sessao_falsa):
    _entrar_como(sessao_falsa, "aluno", EU["id"])

    assert [a["id"] for a in helpers.alunos_para_selecao()] == [EU["id"]]


@pytest.mark.parametrize("papel", ["professor", "desenvolvedor"])
def test_seletor_lista_a_turma_para_gestao(sessao_falsa, papel):
    _entrar_como(sessao_falsa, papel)

    assert len(helpers.alunos_para_selecao()) == len(TODOS)


def test_template_recebe_o_aviso_de_conta_travada(sessao_falsa):
    _entrar_como(sessao_falsa, "aluno", EU["id"])
    assert helpers.contexto_aluno_template()["aluno_travado"] is True

    _entrar_como(sessao_falsa, "professor")
    sessao_falsa.pop("aluno_id", None)
    assert helpers.contexto_aluno_template()["aluno_travado"] is False


def test_conta_sem_papel_definido_nao_trava(sessao_falsa):
    # Sessao antiga, de antes do login: nao pode travar em ninguem.
    sessao_falsa["escola_id"] = "esc-1"
    assert helpers.aluno_travado_id() == ""
