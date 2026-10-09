"""O histórico de perguntas já vistas mora no banco, e o cookie fica pequeno.

Medido em 13/09/2026: 38 avisos "The 'session' cookie is too large" no Render
em uma semana. Laboratório, Oráculo e ENEM guardavam no cookie o TEXTO de cada
pergunta mostrada, numa chave por tema -- e o tema em branco é sorteado a cada
questão. Nada apagava essas chaves, nem o logout. Acima de 4.093 bytes o
navegador ignora o cookie, e o aluno perde o login ou a questão.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from core.runtime_context import get_runtime
from services import historico_perguntas as hp

RAIZ = Path(__file__).resolve().parents[1]
PERGUNTA_LONGA = "Um projétil é lançado verticalmente com velocidade inicial de 20 m/s. " * 4


def _como_jsonb(valor):
    """O jsonb do Postgres não guarda a ordem das chaves de um objeto: ordena
    por tamanho e depois pelos bytes. O banco falso faz o mesmo, senão um teste
    de ordem passaria aqui e falharia no banco de verdade."""
    if isinstance(valor, dict):
        return {k: _como_jsonb(valor[k]) for k in sorted(valor, key=lambda c: (len(c.encode()), c.encode()))}
    if isinstance(valor, list):
        return [_como_jsonb(item) for item in valor]
    return valor


class BancoFalso:
    """estados_sessao em memória, com a ida e volta que o banco faz."""

    def __init__(self):
        self.linhas: dict[str, object] = {}
        self.leituras = 0
        self.gravacoes = 0

    def carregar(self, chave):
        self.leituras += 1
        valor = self.linhas.get(chave)
        return json.loads(json.dumps(valor)) if valor is not None else None

    def salvar(self, chave, estado):
        self.gravacoes += 1
        self.linhas[chave] = _como_jsonb(json.loads(json.dumps(estado)))
        return True


@pytest.fixture
def banco(monkeypatch):
    falso = BancoFalso()
    monkeypatch.setattr(hp, "carregar_estado_temporario", falso.carregar)
    monkeypatch.setattr(hp, "salvar_estado_temporario", falso.salvar)
    return falso


@pytest.fixture
def app():
    from flask_app import app as aplicacao

    return aplicacao


def _requisicao(app, sid="sid-1"):
    contexto = app.test_request_context("/")
    contexto.push()
    if sid is not None:
        from flask import session

        session["_estado_sid"] = sid
    return contexto


def _funcao(caminho):
    modulo, atributo = caminho.split(":")
    return getattr(importlib.import_module(modulo), atributo)


# ====================== O DEFEITO ======================


def test_o_cookie_nao_cresce_com_as_perguntas(banco, app):
    """40 temas sorteados, pergunta longa em cada: antes, ~4 KB no cookie."""
    serializador = app.session_interface.get_signing_serializer(app)
    contexto = _requisicao(app)
    try:
        from flask import session

        for i in range(40):
            hp.gravar(f"oraculo_hist_Matematica__tema {i}__Médio", [PERGUNTA_LONGA + str(i)])

        assert [k for k in session if "_hist_" in k] == []
        assert len(serializador.dumps(dict(session))) < 200
    finally:
        contexto.pop()


MODOS = [
    ("services.calculo_service:_set_historico", "services.calculo_service:_get_historico", "calc_hist_"),
    ("services.enem_service:_set_historico_sessao", "services.enem_service:_get_historico_sessao", "enem_hist_"),
    ("services.ia.enigma:_set_historico_oraculo", "services.ia.enigma:_get_historico_oraculo", "oraculo_hist_"),
]


@pytest.mark.parametrize("gravar, ler, prefixo", MODOS)
def test_os_tres_modos_guardam_no_banco(banco, app, gravar, ler, prefixo):
    chave = ("Fisica", "cinematica", "Médio")
    contexto = _requisicao(app)
    try:
        from flask import session

        _funcao(gravar)(chave, [PERGUNTA_LONGA])
        assert not [k for k in session if k.startswith(prefixo)], "voltou a gravar no cookie"
    finally:
        contexto.pop()

    contexto = _requisicao(app)
    try:
        assert _funcao(ler)(chave) == [PERGUNTA_LONGA]
    finally:
        contexto.pop()


def test_nenhum_modo_escreve_historico_na_sessao():
    """Guarda contra a volta do defeito por outro caminho."""
    for relativo in ("services/calculo_service.py", "services/enem_service.py", "services/ia/enigma.py"):
        fonte = (RAIZ / relativo).read_text(encoding="utf-8")
        assert "session[k]" not in fonte and "session[chave_sessao]" not in fonte, relativo


# ====================== O ARMAZENAMENTO ======================


def test_sobrevive_de_uma_requisicao_para_outra(banco, app):
    contexto = _requisicao(app)
    try:
        hp.gravar("calc_hist_Quimica__solucoes__Médio", ["lab_q_1", "lab_q_2"])
    finally:
        contexto.pop()

    contexto = _requisicao(app)
    try:
        assert hp.ler("calc_hist_Quimica__solucoes__Médio") == ["lab_q_1", "lab_q_2"]
    finally:
        contexto.pop()


def test_sessao_sem_id_ganha_um_e_o_historico_usa_o_mesmo(banco, app):
    contexto = _requisicao(app, sid=None)
    try:
        from flask import session

        hp.gravar("calc_hist_Quimica__solucoes__Médio", ["lab_q_1"])

        sid = session.get("_estado_sid")
        assert sid, "sem id na sessao, a proxima requisicao nao acharia o historico"
        assert list(banco.linhas) == [f"{sid}:historicos"]
    finally:
        contexto.pop()


def test_outra_sessao_nao_ve_o_historico(banco, app):
    """O logout apaga o _estado_sid: sem ele, o histórico de quem saiu some."""
    contexto = _requisicao(app, sid="sid-de-quem-saiu")
    try:
        hp.gravar("calc_hist_Quimica__solucoes__Médio", ["lab_q_1"])
    finally:
        contexto.pop()

    contexto = _requisicao(app, sid="sid-de-quem-chegou")
    try:
        assert hp.ler("calc_hist_Quimica__solucoes__Médio") == []
    finally:
        contexto.pop()


def test_le_o_banco_uma_vez_por_requisicao(banco, app):
    contexto = _requisicao(app)
    try:
        for _ in range(5):
            hp.ler("calc_hist_A__b__Médio")
        hp.gravar("calc_hist_A__b__Médio", ["x"])
        hp.gravar("calc_hist_C__d__Médio", ["y"])
        assert banco.leituras == 1
        assert banco.gravacoes == 2
    finally:
        contexto.pop()


def test_sai_a_chave_usada_ha_mais_tempo_mesmo_depois_de_ir_ao_banco(banco, app):
    """A ordem vai como lista: o jsonb do Postgres não guarda a ordem de objeto.

    E usar de novo uma chave ainda guardada a leva para o fim da fila. (A versão
    anterior deste teste reusava a chave DEPOIS de ela sair -- ela voltava como
    nova de qualquer jeito, e um mutante sem o "volta para o fim" passava.)
    """
    total = hp.MAX_CHAVES + 3
    for i in range(total):
        contexto = _requisicao(app)
        try:
            hp.gravar(f"oraculo_hist_tema_{i}", [f"p{i}"])
            if i == hp.MAX_CHAVES - 1:
                # Fila cheia e nada saiu ainda: reusar a mais antiga a salva.
                hp.gravar("oraculo_hist_tema_0", ["p0", "de novo"])
        finally:
            contexto.pop()

    contexto = _requisicao(app)
    try:
        assert hp.ler("oraculo_hist_tema_0") == ["p0", "de novo"]
        assert [hp.ler(f"oraculo_hist_tema_{i}") for i in (1, 2, 3)] == [[], [], []]
        assert hp.ler("oraculo_hist_tema_4") == ["p4"]
        assert hp.ler(f"oraculo_hist_tema_{total - 1}") == [f"p{total - 1}"]
        assert len(banco.linhas["sid-1:historicos"]["historicos"]) == hp.MAX_CHAVES
    finally:
        contexto.pop()


def test_item_vazio_nao_entra(banco, app):
    contexto = _requisicao(app)
    try:
        hp.gravar("enem_hist_x", ["a", "", "   ", "b"])
        assert hp.ler("enem_hist_x") == ["a", "b"]
    finally:
        contexto.pop()


def test_fora_do_flask_usa_a_memoria_de_antes(monkeypatch):
    estado = {}
    monkeypatch.setattr(get_runtime(), "session_state", estado)

    hp.gravar("calc_hist_fora", ["q1"])

    assert estado == {"calc_hist_fora": ["q1"]}
    assert hp.ler("calc_hist_fora") == ["q1"]


def test_fora_do_flask_o_oraculo_continua_sem_historico(monkeypatch):
    """Antes da mudança o Oráculo só guardava dentro de uma requisição. Guardar
    agora na memória do processo faria uma pergunta de um teste virar
    "pergunta-repetida" no teste seguinte."""
    from services.ia import enigma

    estado = {}
    monkeypatch.setattr(get_runtime(), "session_state", estado)

    enigma._set_historico_oraculo(("Historia", "Imperialismo", "Médio"), ["q1"])

    assert estado == {}
    assert enigma._get_historico_oraculo(("Historia", "Imperialismo", "Médio")) == []


# ====================== QUEM JÁ TEM O COOKIE INCHADO ======================


def test_a_limpeza_tira_so_os_historicos():
    from core.sessao import remover_historicos_do_cookie

    sessao = {
        "calc_hist_Matematica__porcentagem__Médio": ["p"],
        "oraculo_hist_Historia__Imperialismo__Médio": ["p"],
        "enem_hist_Linguagens_Medio": ["p"],
        "aluno_id": "a1",
        "escola_nome": "Etec",
    }

    assert remover_historicos_do_cookie(sessao) == 3
    assert sessao == {"aluno_id": "a1", "escola_nome": "Etec"}


def test_o_cookie_inchado_encolhe_no_primeiro_acesso(client):
    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sess:
        sess["escola_nome"] = "Etec Araçatuba"
        sess["oraculo_hist_Matematica__PA__Médio"] = [PERGUNTA_LONGA] * 12
        sess["calc_hist_Fisica__Newton__Difícil"] = [PERGUNTA_LONGA] * 12
        carimbar_sessao(sess)

    client.get("/healthz")

    with client.session_transaction() as sess:
        assert not [k for k in sess if "_hist_" in k]
        assert sess.get("escola_nome") == "Etec Araçatuba"
