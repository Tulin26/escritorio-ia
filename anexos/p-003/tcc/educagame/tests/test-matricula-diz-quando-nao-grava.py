"""Matrícula que não gravou não pode dizer "Aluno matriculado."

RF03 do TCC, cenário alternativo: "O RA já pertence a outro aluno da escola.
O sistema não grava a matrícula." As duas telas diziam sucesso mesmo assim:
`criar_aluno` engolia a exceção e devolvia None, e nenhuma delas olhava o
retorno. Com o Supabase fora do ar, o mesmo "matriculado".

O banco daqui é o cliente REST de verdade (repositories/supabase_client.py)
com o `urlopen` trocado: o 409 sai com o corpo que o PostgREST manda, e o
motivo atravessa cliente -> repositório -> serviço -> tela. Um dublê que
levantasse o motivo pronto provaria só que a tela lê o dublê.
"""

from __future__ import annotations

import importlib
import io
import json
import sys
from urllib.error import HTTPError, URLError

import pytest

import repositories.aluno_repo as aluno_repo
import repositories.gravacao as gravacao
import repositories.supabase_client as sc
import services.aluno_service as aluno_service

# Importado fora do dublê do Streamlit, como em test_adm_streamlit_por_papel:
# a cadeia de repositories precisa resolver o runtime de verdade no import.
import st.ui  # noqa: E402
import st.ui.professor_panel_st  # noqa: E402,F401

from tests.apoio_flask import carimbar_sessao
from tests.apoio_streamlit import StreamlitFalso

ESCOLA_ID = "esc-1"
RA = "20260917"

CORPO_RA_REPETIDO = json.dumps(
    {
        "code": "23505",
        "details": f"Key (escola_id, ra_identificacao)=({ESCOLA_ID}, {RA}) already exists.",
        "hint": None,
        "message": 'duplicate key value violates unique constraint "unique_ra_por_escola"',
    }
).encode()

# Outra restrição UNIQUE da mesma tabela (migração 20260810120000): também é
# 23505, mas não é o RA -- dizer "RA repetido" aqui seria mandar o professor
# corrigir o campo errado.
CORPO_OUTRA_UNICIDADE = json.dumps(
    {
        "code": "23505",
        "details": "Key (username)=(ana) already exists.",
        "hint": None,
        "message": 'duplicate key value violates unique constraint "idx_alunos_username"',
    }
).encode()

CORPO_NOT_NULL = json.dumps(
    {
        "code": "23502",
        "details": None,
        "hint": None,
        "message": 'null value in column "nome" of relation "alunos" violates not-null constraint',
    }
).encode()

FORMULARIO = {
    "nome": "  Ana Lima  ",
    "ra_identificacao": f" {RA} ",
    "serie": "9º Ano",
    "periodo": "Tarde",
    "ensino_religioso": "on",
}

# O que o Postgres responde e não pode chegar à tela.
DETALHES_INTERNOS = ("23505", "unique_ra_por_escola", "constraint", "Supabase REST", "already exists")


@pytest.fixture
def banco(monkeypatch, sem_rede_supabase):
    """aluno_repo fala com o cliente REST de verdade; a resposta é combinada.

    O resto (cache, escolas, logs) continua no banco em memória do conftest:
    nenhuma consulta sai para a rede.
    """
    pedidos: list[str] = []
    combinado: dict[str, object] = {}

    def falso_urlopen(request, timeout=None):
        pedidos.append(f"{request.get_method()} {request.full_url}")
        falha = combinado["falha"]
        if isinstance(falha, tuple):
            status, corpo = falha
            raise HTTPError(request.full_url, status, "erro", {}, io.BytesIO(corpo))
        raise falha

    monkeypatch.setattr(sc, "urlopen", falso_urlopen)
    monkeypatch.setattr(sc, "_ESPERA_ANTES_DE_REPETIR", 0)
    monkeypatch.setattr(
        aluno_repo, "supabase", sc._SupabaseRestClient("https://example.supabase.co", "chave-de-mentira")
    )

    def responder_com(falha) -> list[str]:
        combinado["falha"] = falha
        return pedidos

    return responder_com


def _dados_do_aluno() -> dict:
    return {
        "nome": "Ana Lima",
        "ra_identificacao": RA,
        "ano_escolar": "9º Ano",
        "periodo": "Tarde",
        "escola_id": ESCOLA_ID,
        "pontos_totais": 0,
        "ensino_religioso": False,
    }


FALHAS = [
    pytest.param((409, CORPO_RA_REPETIDO), aluno_repo.FALHA_RA_REPETIDO, id="ra-repetido"),
    pytest.param((409, CORPO_OUTRA_UNICIDADE), gravacao.FALHA_RECUSADA, id="outra-unicidade"),
    pytest.param(URLError("getaddrinfo failed"), gravacao.FALHA_SEM_CONEXAO, id="sem-rede"),
    pytest.param(ConnectionRefusedError("recusada"), gravacao.FALHA_SEM_CONEXAO, id="conexao-recusada"),
    pytest.param(TimeoutError("timed out"), gravacao.FALHA_SEM_CONEXAO, id="prazo-estourado"),
    pytest.param((503, b"<html>Service Unavailable</html>"), gravacao.FALHA_SEM_CONEXAO, id="gateway-503"),
    pytest.param((504, b'{"message":"Gateway Timeout"}'), gravacao.FALHA_SEM_CONEXAO, id="gateway-504"),
    pytest.param((401, b'{"message":"Invalid API key"}'), gravacao.FALHA_RECUSADA, id="chave-invalida"),
    pytest.param((400, CORPO_NOT_NULL), gravacao.FALHA_RECUSADA, id="not-null"),
    pytest.param((500, b"<html>erro</html>"), gravacao.FALHA_RECUSADA, id="500-sem-json"),
]


# ============================== REPOSITÓRIO ==============================


@pytest.mark.parametrize("falha, motivo_esperado", FALHAS)
def test_o_repositorio_diz_por_que_nao_gravou(banco, falha, motivo_esperado):
    pedidos = banco(falha)

    resultado, motivo = aluno_repo.criar_aluno(_dados_do_aluno())

    assert resultado is None
    assert motivo == motivo_esperado
    # insert não se repete nem no 503/504 (ver _pode_repetir): repetir poderia
    # gravar o aluno duas vezes -- ou, com o RA único, trocar "sem conexão"
    # por um "RA repetido" que o próprio primeiro pedido causou.
    assert len(pedidos) == 1


def test_supabase_sem_configuracao_conta_como_sem_conexao(monkeypatch):
    monkeypatch.setattr(aluno_repo, "supabase", sc._SupabaseIndisponivel())

    assert aluno_repo.criar_aluno(_dados_do_aluno()) == (None, gravacao.FALHA_SEM_CONEXAO)


class _Resposta:
    def __init__(self, corpo: bytes):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_insert_que_volta_sem_a_linha_nao_conta_como_gravado(monkeypatch, sem_rede_supabase):
    """Com return=representation o PostgREST devolve o aluno criado. Lista
    vazia é resposta que não confirma nada -- o mesmo critério de criar_conta."""
    monkeypatch.setattr(sc, "urlopen", lambda request, timeout=None: _Resposta(b"[]"))
    monkeypatch.setattr(
        aluno_repo, "supabase", sc._SupabaseRestClient("https://example.supabase.co", "chave-de-mentira")
    )

    assert aluno_repo.criar_aluno(_dados_do_aluno()) == (None, gravacao.FALHA_RECUSADA)


def test_o_repositorio_que_grava_nao_devolve_motivo(sem_rede_supabase):
    resultado, motivo = aluno_repo.criar_aluno(_dados_do_aluno())

    assert motivo == ""
    assert resultado.data[0]["ra_identificacao"] == RA


def test_o_erro_do_cliente_continua_sendo_o_de_antes():
    """Quem já capturava RuntimeError ou lia o texto não pode notar a troca."""
    erro = sc.ErroDoSupabase(409, CORPO_RA_REPETIDO.decode())

    assert isinstance(erro, RuntimeError)
    assert str(erro).startswith("Supabase REST erro 409: ")
    assert erro.violou_unicidade("unique_ra_por_escola")
    # o nome precisa bater inteiro: "unique_ra" não é a restrição
    assert not erro.violou_unicidade("unique_ra")
    assert isinstance(sc.SupabaseNaoConfigurado("x"), RuntimeError)


# ================================ SERVIÇO ================================


@pytest.mark.parametrize(
    "nome, ra",
    [("", RA), ("   ", RA), ("Ana Lima", ""), ("Ana Lima", "  ")],
)
def test_nome_ou_ra_em_branco_nao_vai_ao_banco(banco, nome, ra):
    pedidos = banco(AssertionError("não devia chegar ao banco"))

    ok, motivo = aluno_service.registrar_matricula(
        escola_id=ESCOLA_ID, nome=nome, ra_identificacao=ra,
        ano_escolar="9º Ano", periodo="Tarde", ensino_religioso=False,
    )

    assert (ok, motivo) == (False, aluno_service.MATRICULA_SEM_DADOS)
    assert pedidos == []


@pytest.mark.parametrize("escola_id", [None, "", "  "])
def test_sem_escola_nao_vai_ao_banco(banco, escola_id):
    pedidos = banco(AssertionError("não devia chegar ao banco"))

    ok, motivo = aluno_service.registrar_matricula(
        escola_id=escola_id, nome="Ana Lima", ra_identificacao=RA,
        ano_escolar="9º Ano", periodo="Tarde", ensino_religioso=False,
    )

    assert (ok, motivo) == (False, aluno_service.MATRICULA_SEM_ESCOLA)
    assert pedidos == []


def test_todo_motivo_tem_mensagem():
    motivos = {
        aluno_service.MATRICULA_SEM_ESCOLA,
        aluno_service.MATRICULA_SEM_DADOS,
        aluno_repo.FALHA_RA_REPETIDO,
        gravacao.FALHA_SEM_CONEXAO,
        gravacao.FALHA_RECUSADA,
    }

    assert set(aluno_service.MENSAGENS_DA_MATRICULA) == motivos


def test_as_mensagens_nao_se_confundem_nem_mostram_o_banco_por_dentro():
    mensagens = aluno_service.MENSAGENS_DA_MATRICULA

    assert len(set(mensagens.values())) == len(mensagens)
    assert "RA" in mensagens[aluno_repo.FALHA_RA_REPETIDO]
    assert "RA" not in mensagens[gravacao.FALHA_SEM_CONEXAO]
    # as três falhas de gravação avisam que o aluno não está garantido no banco
    assert "não foi gravada" in mensagens[aluno_repo.FALHA_RA_REPETIDO]
    assert "não foi confirmada" in mensagens[gravacao.FALHA_SEM_CONEXAO]
    assert "não aceitou" in mensagens[gravacao.FALHA_RECUSADA]
    for texto in mensagens.values():
        for interno in DETALHES_INTERNOS:
            assert interno not in texto, (interno, texto)


# ============================== TELA DO FLASK ==============================


def _entrar(client, sem_rede_supabase, papel="professor", escola_id=ESCOLA_ID):
    sem_rede_supabase.table("escolas").insert(
        {"id": ESCOLA_ID, "nome": "ETEC", "slug": "etec", "mostrar_ranking": True, "modo_guilda": True}
    ).execute()
    with client.session_transaction() as sess:
        sess["usuario_role"] = papel
        sess["escola_id"] = escola_id
        sess["escola_nome"] = "ETEC"
        carimbar_sessao(sess)


def _matricular(client) -> tuple[str, str]:
    """Posta o formulário e segue o redirect. Devolve (endereço, página)."""
    resposta = client.post("/professor/matricula", data=FORMULARIO)
    assert resposta.status_code == 302
    destino = resposta.headers["Location"]
    pagina = client.get(destino).get_data(as_text=True)
    return destino, pagina


@pytest.mark.parametrize(
    "falha, motivo",
    [
        pytest.param((409, CORPO_RA_REPETIDO), aluno_repo.FALHA_RA_REPETIDO, id="ra-repetido"),
        pytest.param(URLError("getaddrinfo failed"), gravacao.FALHA_SEM_CONEXAO, id="sem-rede"),
        pytest.param((400, CORPO_NOT_NULL), gravacao.FALHA_RECUSADA, id="recusada"),
    ],
)
def test_a_rota_mostra_por_que_nao_matriculou(client, sem_rede_supabase, banco, falha, motivo):
    _entrar(client, sem_rede_supabase)
    banco(falha)

    destino, pagina = _matricular(client)

    assert "Aluno matriculado" not in destino
    assert "Aluno matriculado" not in pagina
    assert f"erro={motivo}" in destino
    assert aluno_service.MENSAGENS_DA_MATRICULA[motivo] in pagina
    # só a mensagem deste motivo -- as outras não aparecem junto
    for outro, texto in aluno_service.MENSAGENS_DA_MATRICULA.items():
        if outro != motivo:
            assert texto not in pagina, outro
    for interno in DETALHES_INTERNOS:
        assert interno not in pagina, interno
    # nada do aluno na URL: ela vai parar no log de acesso
    assert RA not in destino
    assert "Ana" not in destino


def test_a_rota_que_grava_diz_matriculado(client, sem_rede_supabase):
    _entrar(client, sem_rede_supabase)

    destino, pagina = _matricular(client)

    assert "erro=" not in destino
    assert "Aluno matriculado." in pagina
    assert 'role="alert"' not in pagina
    gravados = sem_rede_supabase.table("alunos").select("*").eq("escola_id", ESCOLA_ID).execute().data
    assert [
        (a["nome"], a["ra_identificacao"], a["ano_escolar"], a["periodo"], a["ensino_religioso"], a["pontos_totais"])
        for a in gravados
    ] == [("Ana Lima", RA, "9º Ano", "Tarde", True, 0)]


def test_desenvolvedor_sem_escola_nao_ve_sucesso(client, sem_rede_supabase, banco):
    pedidos = banco(AssertionError("não devia chegar ao banco"))
    _entrar(client, sem_rede_supabase, papel="desenvolvedor", escola_id=None)

    resposta = client.post("/professor/matricula", data=FORMULARIO)

    assert resposta.status_code == 302
    assert f"erro={aluno_service.MATRICULA_SEM_ESCOLA}" in resposta.headers["Location"]
    assert "Aluno matriculado" not in resposta.headers["Location"]
    assert pedidos == []


@pytest.mark.parametrize("erro", ["<b>Sua conta foi bloqueada</b>", "Qualquer texto", "recusada "])
def test_chave_desconhecida_na_url_nao_vira_aviso(client, sem_rede_supabase, erro):
    """A faixa de erro só mostra texto do próprio sistema."""
    _entrar(client, sem_rede_supabase)

    pagina = client.get("/professor/", query_string={"aba": "matricula", "erro": erro}).get_data(as_text=True)

    assert 'role="alert"' not in pagina
    assert "bloqueada" not in pagina
    assert "Qualquer texto" not in pagina


# ============================ TELA DO STREAMLIT ============================


BOTAO = "Finalizar Matrícula"


@pytest.fixture
def tela_streamlit(monkeypatch):
    """Roda a aba de matrícula com o dublê; devolve (roteiro, sessão)."""
    # Outra bancada pode ter tirado o módulo do sys.modules sem devolver
    # (test_adm_streamlit_por_papel faz isso): importar aqui, fora do dublê,
    # e deixar o sys.modules como estava no fim.
    original = importlib.import_module("st.ui.professor_panel_st")
    monkeypatch.setitem(sys.modules, "st.ui.professor_panel_st", original)
    monkeypatch.setattr(st.ui, "professor_panel_st", original)

    def rodar(respostas: dict, sessao: dict | None = None):
        with StreamlitFalso(respostas=respostas, sessao=sessao) as fake:
            # monkeypatch devolve o módulo original ao sys.modules no fim
            monkeypatch.delitem(sys.modules, "st.ui.professor_panel_st")
            painel = importlib.import_module("st.ui.professor_panel_st")
            painel._renderizar_aba_matricula(ESCOLA_ID)
        return fake.roteiro(), dict(fake.session_state)

    return rodar


def _preenchido(**extra) -> dict:
    return {"Nome Completo *": "Ana Lima", "RA / Identificação *": RA, BOTAO: True, **extra}


def _avisos(roteiro: list[str]) -> list[str]:
    return [linha for linha in roteiro if linha.split(":")[0] in ("success", "error", "warning")]


@pytest.mark.parametrize(
    "falha, motivo",
    [
        pytest.param((409, CORPO_RA_REPETIDO), aluno_repo.FALHA_RA_REPETIDO, id="ra-repetido"),
        pytest.param(TimeoutError("timed out"), gravacao.FALHA_SEM_CONEXAO, id="prazo-estourado"),
        pytest.param((401, b'{"message":"Invalid API key"}'), gravacao.FALHA_RECUSADA, id="recusada"),
    ],
)
def test_streamlit_mostra_por_que_nao_matriculou(banco, tela_streamlit, falha, motivo):
    banco(falha)

    roteiro, sessao = tela_streamlit(_preenchido())

    esperado = StreamlitFalso._resumir(aluno_service.MENSAGENS_DA_MATRICULA[motivo])
    assert _avisos(roteiro) == [f"error: {esperado}"]
    assert "rerun" not in roteiro
    assert not sessao


def test_streamlit_avisa_nome_em_branco(banco, tela_streamlit):
    """Antes o botão com nome vazio não fazia nada, nem dizia nada."""
    pedidos = banco(AssertionError("não devia chegar ao banco"))

    roteiro, _ = tela_streamlit(_preenchido(**{"Nome Completo *": "  "}))

    esperado = StreamlitFalso._resumir(aluno_service.MENSAGENS_DA_MATRICULA[aluno_service.MATRICULA_SEM_DADOS])
    assert _avisos(roteiro) == [f"error: {esperado}"]
    assert pedidos == []


def test_streamlit_que_grava_mostra_o_sucesso_depois_do_rerun(sem_rede_supabase, tela_streamlit):
    """O st.success antes do st.rerun() sumia na hora; agora aparece na volta."""
    roteiro, sessao = tela_streamlit(_preenchido())

    assert "rerun" in roteiro
    assert _avisos(roteiro) == []

    # a volta do rerun: o botão já não está apertado
    roteiro, sessao_depois = tela_streamlit({}, sessao=sessao)

    assert _avisos(roteiro) == ["success: ✅ Aluno **Ana Lima** matriculado no **6º Ano**!"]
    assert not sessao_depois, "o aviso reaparece em toda interação seguinte"
    assert len(sem_rede_supabase.table("alunos").select("*").execute().data) == 1
