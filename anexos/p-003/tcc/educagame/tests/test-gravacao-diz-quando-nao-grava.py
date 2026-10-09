"""Aventura, preferências e escola: gravação que falhou não diz "salvo".

O mesmo defeito da matrícula (tests/test_matricula_diz_quando_nao_grava.py),
em outras seis gravações: os repositórios engoliam a exceção e devolviam
None, e as telas davam sucesso sem olhar --

- Flask: "Aventura salva.", "Aventura excluida." e "Preferencias salvas."
  saíam sempre, até sem escola na sessão. O ADM olhava o retorno, mas dizia
  "Verifique a conexao" até para slug repetido.
- Streamlit: o `except` ao redor da gravação nunca rodava (ela não levanta),
  e o st.success vinha antes do st.rerun(), que o apagava na hora.

O banco é o cliente REST de verdade com o `urlopen` trocado: leitura
responde normalmente, gravação responde o que o teste combinar.
"""

from __future__ import annotations

import importlib
import io
import json
import sys
from urllib.error import HTTPError, URLError

import pytest

import repositories.aluno_repo as aluno_repo
import repositories.escola_repo as escola_repo
import repositories.rpg_config_repo as rpg_config_repo
import repositories.supabase_client as sc
from repositories.gravacao import FALHA_NAO_ENCONTRADA, FALHA_RECUSADA, FALHA_SEM_CONEXAO
from services import escola_service, rpg_config_service
from services.aluno_service import MENSAGENS_DA_MATRICULA
from services.avisos_de_gravacao import CONFIRMACAO_INVALIDA, FALTA_ESCOLA, FALTAM_DADOS

# Fora do dublê, de propósito (ver test_adm_streamlit_por_papel): a cadeia de
# repositories precisa resolver o runtime de verdade no import.
import st.ui  # noqa: E402
import st.ui.admin_st  # noqa: E402,F401
import st.ui.professor_panel_st  # noqa: E402,F401

from tests.apoio_flask import carimbar_sessao
from tests.apoio_streamlit import StreamlitFalso

MENSAGENS_DA_AVENTURA = rpg_config_service.MENSAGENS_DA_AVENTURA
MENSAGENS_DA_ESCOLA = escola_service.MENSAGENS_DA_ESCOLA
MENSAGENS_DAS_PREFERENCIAS = escola_service.MENSAGENS_DAS_PREFERENCIAS
SLUG_REPETIDO = escola_repo.FALHA_SLUG_REPETIDO

ESCOLA_ID = "esc-1"
AVENTURA_ID = "8f1c2a90-0000-4000-8000-000000000001"


def _corpo_409(restricao: str) -> bytes:
    return json.dumps(
        {
            "code": "23505",
            "details": "Key (slug)=(etec) already exists.",
            "hint": None,
            "message": f'duplicate key value violates unique constraint "{restricao}"',
        }
    ).encode()


CORPO_SLUG_REPETIDO = _corpo_409("escolas_slug_key")
CORPO_NOT_NULL = json.dumps(
    {"code": "23502", "details": None, "hint": None,
     "message": 'null value in column "titulo" of relation "rpg_config" violates not-null constraint'}
).encode()

# O que o banco responde e não pode chegar à tela.
DETALHES_INTERNOS = ("23505", "23502", "escolas_slug_key", "violates", "Supabase REST", "already exists")

FALHAS = [
    pytest.param(URLError("getaddrinfo failed"), FALHA_SEM_CONEXAO, id="sem-rede"),
    pytest.param(TimeoutError("timed out"), FALHA_SEM_CONEXAO, id="prazo-estourado"),
    pytest.param((503, b"<html>Service Unavailable</html>"), FALHA_SEM_CONEXAO, id="gateway"),
    pytest.param((401, b'{"message":"Invalid API key"}'), FALHA_RECUSADA, id="chave-invalida"),
    pytest.param((400, CORPO_NOT_NULL), FALHA_RECUSADA, id="not-null"),
]


class _Resposta:
    def __init__(self, corpo: bytes):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _Banco:
    def __init__(self):
        self.leitura: bytes = b"[]"
        self.resposta: object = b"[]"
        self.escritas: list[tuple[str, str, object]] = []

    def ler(self, linhas: list[dict]) -> None:
        self.leitura = json.dumps(linhas).encode()

    def gravar(self, resposta) -> None:
        """Uma exceção, um (status, corpo) de erro, ou o corpo de um 200."""
        self.resposta = resposta

    def urlopen(self, request, timeout=None):
        metodo = request.get_method()
        if metodo == "GET":
            return _Resposta(self.leitura)
        self.escritas.append((metodo, request.full_url, json.loads(request.data) if request.data else None))
        if isinstance(self.resposta, BaseException):
            raise self.resposta
        if isinstance(self.resposta, tuple):
            status, corpo = self.resposta
            raise HTTPError(request.full_url, status, "erro", {}, io.BytesIO(corpo))
        return _Resposta(self.resposta)


@pytest.fixture
def banco(monkeypatch, sem_rede_supabase):
    """Os repositórios de gravação falam com o cliente REST de verdade.

    O resto (cache, logs, usuários) segue no banco em memória do conftest:
    nenhuma consulta sai para a rede.
    """
    falso = _Banco()
    monkeypatch.setattr(sc, "urlopen", falso.urlopen)
    monkeypatch.setattr(sc, "_ESPERA_ANTES_DE_REPETIR", 0)
    cliente = sc._SupabaseRestClient("https://example.supabase.co", "chave-de-mentira")
    for modulo in (aluno_repo, escola_repo, rpg_config_repo):
        monkeypatch.setattr(modulo, "supabase", cliente)
    return falso


def _aventura(**campos) -> dict:
    return {"titulo": "O Cristal", "cenario": "Uma caverna", "materia": "Física", "serie": "9º Ano", **campos}


# ============================== REPOSITÓRIOS ==============================

GRAVACOES = [
    pytest.param(lambda: rpg_config_repo.criar_rpg_config(_aventura(escola_id=ESCOLA_ID)), FALHA_RECUSADA,
                 id="criar-aventura"),
    pytest.param(lambda: rpg_config_repo.atualizar_rpg_config(ESCOLA_ID, AVENTURA_ID, _aventura()),
                 FALHA_NAO_ENCONTRADA, id="atualizar-aventura"),
    pytest.param(lambda: rpg_config_repo.excluir_rpg_config(ESCOLA_ID, AVENTURA_ID), FALHA_NAO_ENCONTRADA,
                 id="excluir-aventura"),
    pytest.param(lambda: escola_repo.criar_escola("Colégio Novo", "colegio-novo"), FALHA_RECUSADA,
                 id="criar-escola"),
    pytest.param(lambda: escola_repo.atualizar_escola(ESCOLA_ID, {"nome": "ETEC"}), FALHA_NAO_ENCONTRADA,
                 id="atualizar-escola"),
    pytest.param(lambda: escola_repo.excluir_escola(ESCOLA_ID), FALHA_NAO_ENCONTRADA, id="excluir-escola"),
]


@pytest.mark.parametrize("falha, motivo", FALHAS)
@pytest.mark.parametrize("gravar, _sem_linha", GRAVACOES)
def test_a_gravacao_diz_por_que_falhou(banco, gravar, _sem_linha, falha, motivo):
    banco.gravar(falha)

    assert gravar() == (None, motivo)
    assert banco.escritas, "nem chegou a pedir"


@pytest.mark.parametrize("gravar, sem_linha", GRAVACOES)
def test_resposta_sem_linha_nao_conta_como_gravado(banco, gravar, sem_linha):
    """return=representation devolve a linha gravada. Num update ou delete,
    lista vazia é o filtro que não achou o registro -- apagado em outra tela."""
    banco.gravar(b"[]")

    assert gravar() == (None, sem_linha)


@pytest.mark.parametrize("gravar, _sem_linha", GRAVACOES)
def test_a_gravacao_que_grava_nao_devolve_motivo(banco, gravar, _sem_linha):
    banco.gravar(b'[{"id": "x"}]')

    resultado, motivo = gravar()

    assert motivo == ""
    assert resultado.data == [{"id": "x"}]


@pytest.mark.parametrize("gravar, _sem_linha", GRAVACOES)
def test_supabase_sem_configuracao_conta_como_sem_conexao(monkeypatch, gravar, _sem_linha):
    for modulo in (escola_repo, rpg_config_repo):
        monkeypatch.setattr(modulo, "supabase", sc._SupabaseIndisponivel())

    assert gravar() == (None, FALHA_SEM_CONEXAO)


@pytest.mark.parametrize(
    "gravar",
    [
        pytest.param(lambda: escola_repo.criar_escola("ETEC", "etec"), id="criar"),
        pytest.param(lambda: escola_repo.atualizar_escola(ESCOLA_ID, {"nome": "ETEC", "slug": "etec"}), id="editar"),
    ],
)
def test_slug_repetido_tem_motivo_proprio(banco, gravar):
    banco.gravar((409, CORPO_SLUG_REPETIDO))

    assert gravar() == (None, SLUG_REPETIDO)


def test_slug_repetido_so_quando_o_slug_e_gravado(banco):
    """As preferências não mexem no slug: ali "troque o slug" seria absurdo."""
    banco.gravar((409, CORPO_SLUG_REPETIDO))

    assert escola_repo.atualizar_escola(ESCOLA_ID, {"modo_guilda": True}) == (None, FALHA_RECUSADA)


def test_outra_restricao_unique_nao_vira_slug_repetido(banco):
    banco.gravar((409, _corpo_409("escolas_pkey")))

    assert escola_repo.criar_escola("ETEC", "etec") == (None, FALHA_RECUSADA)


def test_update_e_delete_repetem_no_gateway_e_insert_nao(banco):
    """A segunda tentativa do cliente (ver _pode_repetir) continua valendo."""
    banco.gravar((504, b'{"message":"Gateway Timeout"}'))

    rpg_config_repo.atualizar_rpg_config(ESCOLA_ID, AVENTURA_ID, _aventura())
    rpg_config_repo.excluir_rpg_config(ESCOLA_ID, AVENTURA_ID)
    rpg_config_repo.criar_rpg_config(_aventura())

    assert [metodo for metodo, _, _ in banco.escritas] == ["PATCH", "PATCH", "DELETE", "DELETE", "POST"]


# ================================ SERVIÇOS ================================


@pytest.mark.parametrize(
    "escola_id, dados, motivo",
    [
        pytest.param(None, _aventura(), FALTA_ESCOLA, id="sem-escola"),
        pytest.param("  ", _aventura(), FALTA_ESCOLA, id="escola-em-branco"),
        pytest.param(ESCOLA_ID, _aventura(titulo="  "), FALTAM_DADOS, id="sem-titulo"),
        pytest.param(ESCOLA_ID, _aventura(cenario=""), FALTAM_DADOS, id="sem-cenario"),
        pytest.param(ESCOLA_ID, _aventura(cenario=None), FALTAM_DADOS, id="cenario-none"),
    ],
)
def test_aventura_incompleta_nao_vai_ao_banco(banco, escola_id, dados, motivo):
    assert rpg_config_service.salvar_aventura(escola_id, "", dados) == (False, motivo)
    assert banco.escritas == []


def test_aventura_nova_e_criada_na_escola_da_sessao(banco):
    banco.gravar(b'[{"id": "novo"}]')

    assert rpg_config_service.salvar_aventura(ESCOLA_ID, "", _aventura(escola_id="outra")) == (True, "")

    [(metodo, _, corpo)] = banco.escritas
    assert metodo == "POST"
    assert corpo["escola_id"] == ESCOLA_ID


def test_aventura_aberta_e_atualizada_e_nao_duplicada(banco):
    banco.gravar(b'[{"id": "x"}]')

    assert rpg_config_service.salvar_aventura(ESCOLA_ID, AVENTURA_ID, _aventura()) == (True, "")

    [(metodo, endereco, corpo)] = banco.escritas
    assert metodo == "PATCH"
    assert f"id=eq.{AVENTURA_ID}" in endereco
    # a escola vai no filtro, não no corpo (tests/test_aventura_presa_a_escola.py)
    assert f"escola_id=eq.{ESCOLA_ID}" in endereco
    assert "escola_id" not in corpo


@pytest.mark.parametrize("escola_id", [None, "", "  "])
def test_preferencias_sem_escola_nao_vao_ao_banco(banco, escola_id):
    assert escola_service.salvar_preferencias(escola_id, mostrar_ranking=True, modo_guilda=False) == (
        False,
        FALTA_ESCOLA,
    )
    assert banco.escritas == []


def test_preferencias_gravam_so_as_duas_chaves(banco):
    banco.gravar(b'[{"id": "esc-1"}]')

    assert escola_service.salvar_preferencias(ESCOLA_ID, mostrar_ranking="on", modo_guilda="") == (True, "")

    [(metodo, endereco, corpo)] = banco.escritas
    assert metodo == "PATCH"
    assert f"id=eq.{ESCOLA_ID}" in endereco
    assert corpo == {"mostrar_ranking": True, "modo_guilda": False}


MAPAS = [
    pytest.param(
        MENSAGENS_DA_AVENTURA,
        {FALTA_ESCOLA, FALTAM_DADOS, FALHA_SEM_CONEXAO, FALHA_RECUSADA, FALHA_NAO_ENCONTRADA},
        "aventura",
        id="aventura",
    ),
    pytest.param(
        MENSAGENS_DA_ESCOLA,
        {FALTAM_DADOS, CONFIRMACAO_INVALIDA, SLUG_REPETIDO, FALHA_SEM_CONEXAO, FALHA_RECUSADA, FALHA_NAO_ENCONTRADA},
        "escola",
        id="escola",
    ),
    pytest.param(
        MENSAGENS_DAS_PREFERENCIAS,
        {FALTA_ESCOLA, FALHA_SEM_CONEXAO, FALHA_RECUSADA, FALHA_NAO_ENCONTRADA},
        "prefer",
        id="preferencias",
    ),
]


@pytest.mark.parametrize("mapa, motivos, assunto", MAPAS)
def test_todo_motivo_alcancavel_tem_mensagem(mapa, motivos, assunto):
    # Motivo sem texto seria o defeito de volta: o Flask não mostraria nada
    # (chave desconhecida), e o Streamlit quebraria no MENSAGENS[motivo].
    assert set(mapa) == motivos


@pytest.mark.parametrize("mapa, motivos, assunto", MAPAS)
def test_as_mensagens_dizem_do_que_falam_e_nao_mostram_o_banco(mapa, motivos, assunto):
    assert len(set(mapa.values())) == len(mapa)
    for motivo in (FALHA_SEM_CONEXAO, FALHA_RECUSADA, FALHA_NAO_ENCONTRADA):
        assert assunto in mapa[motivo], (motivo, mapa[motivo])
    assert "não foi confirmada" in mapa[FALHA_SEM_CONEXAO] or "não foram confirmadas" in mapa[FALHA_SEM_CONEXAO]
    for texto in mapa.values():
        for interno in DETALHES_INTERNOS:
            assert interno not in texto, (interno, texto)


# ============================== TELAS DO FLASK ==============================


def _entrar(client, sem_rede_supabase, papel="professor", escola_id=ESCOLA_ID):
    sem_rede_supabase.table("escolas").insert(
        {"id": ESCOLA_ID, "nome": "ETEC", "slug": "etec", "mostrar_ranking": True, "modo_guilda": True}
    ).execute()
    with client.session_transaction() as sess:
        sess["usuario_role"] = papel
        sess["escola_id"] = escola_id
        sess["escola_nome"] = "ETEC"
        carimbar_sessao(sess)


FORM_AVENTURA = {"titulo": "O Cristal", "cenario": "Uma caverna", "materia": "Física", "serie": "9º Ano"}
FORM_ESCOLA = {"nome": "Colégio Novo", "slug": "colegio-novo", "cor_tema": "#003366"}
FORM_EXCLUIR_ESCOLA = {
    "escola_id": ESCOLA_ID, "slug": "etec", "confirmar_slug": "etec", "confirmar_texto": "APAGAR",
}

ROTAS = {
    "criar-aventura": ("professor", "/professor/rpg/salvar", {**FORM_AVENTURA, "config_id": ""}, "rpg"),
    "editar-aventura": ("professor", "/professor/rpg/salvar", {**FORM_AVENTURA, "config_id": AVENTURA_ID}, "rpg"),
    "excluir-aventura": ("professor", "/professor/rpg/excluir", {**FORM_AVENTURA, "config_id": AVENTURA_ID}, "rpg"),
    "preferencias": ("professor", "/professor/configuracoes", {"mostrar_ranking": "on"}, "configuracoes"),
    "criar-escola": ("desenvolvedor", "/professor/adm/escola/criar", FORM_ESCOLA, "adm"),
    "editar-escola": ("desenvolvedor", "/professor/adm/escola/editar", {**FORM_ESCOLA, "escola_id": ESCOLA_ID}, "adm"),
    "excluir-escola": ("desenvolvedor", "/professor/adm/escola/excluir", FORM_EXCLUIR_ESCOLA, "adm"),
}
MAPA_DA_ABA = {
    "rpg": MENSAGENS_DA_AVENTURA,
    "configuracoes": MENSAGENS_DAS_PREFERENCIAS,
    "adm": MENSAGENS_DA_ESCOLA,
}
SUCESSOS = {
    "criar-aventura": "Aventura salva.",
    "editar-aventura": "Aventura salva.",
    "excluir-aventura": "Aventura excluida.",
    "preferencias": "Preferencias salvas.",
    "criar-escola": "Escola criada.",
    "editar-escola": "Escola atualizada.",
    "excluir-escola": "Escola excluida.",
}


def _casos_de_falha():
    for rota in ROTAS:
        for falha in FALHAS[:1] + FALHAS[-1:]:  # sem conexão e recusada
            yield pytest.param(rota, falha.values[0], falha.values[1], id=f"{rota}-{falha.id}")
    for rota in ("editar-aventura", "excluir-aventura", "preferencias", "editar-escola", "excluir-escola"):
        yield pytest.param(rota, b"[]", FALHA_NAO_ENCONTRADA, id=f"{rota}-nao-encontrada")
    for rota in ("criar-escola", "editar-escola"):
        yield pytest.param(rota, (409, CORPO_SLUG_REPETIDO), SLUG_REPETIDO, id=f"{rota}-slug-repetido")


def _postar(client, rota: str) -> tuple[str, str]:
    """Posta o formulário e segue o redirect. Devolve (endereço, página)."""
    _, caminho, form, _ = ROTAS[rota]
    resposta = client.post(caminho, data=form)
    assert resposta.status_code == 302
    destino = resposta.headers["Location"]
    return destino, client.get(destino).get_data(as_text=True)


def _postar_sem_sucesso(client, rota: str) -> tuple[str, str]:
    destino, pagina = _postar(client, rota)
    assert "msg=" not in destino
    assert SUCESSOS[rota] not in pagina
    return destino, pagina


@pytest.mark.parametrize("rota, falha, motivo", list(_casos_de_falha()))
def test_a_rota_mostra_por_que_nao_gravou(client, sem_rede_supabase, banco, rota, falha, motivo):
    papel, _, _, aba = ROTAS[rota]
    _entrar(client, sem_rede_supabase, papel=papel)
    banco.gravar(falha)

    destino, pagina = _postar_sem_sucesso(client, rota)

    assert f"aba={aba}" in destino
    assert f"erro={motivo}" in destino
    texto = MAPA_DA_ABA[aba][motivo]
    assert f'<p class="notice warn" role="alert">{texto}</p>' in pagina
    for interno in DETALHES_INTERNOS:
        assert interno not in pagina, interno


@pytest.mark.parametrize("rota", ["editar-aventura", "excluir-aventura"])
def test_a_aventura_aberta_continua_aberta_depois_do_erro(client, sem_rede_supabase, banco, rota):
    """Voltar em "Criar nova aventura" faria a próxima tentativa criar uma cópia."""
    _entrar(client, sem_rede_supabase)
    banco.ler([{"id": AVENTURA_ID, "escola_id": ESCOLA_ID, **_aventura()}])
    banco.gravar(URLError("getaddrinfo failed"))

    destino, pagina = _postar(client, rota)

    assert f"rpg_id={AVENTURA_ID}" in destino
    assert f'name="config_id" value="{AVENTURA_ID}"' in pagina


@pytest.mark.parametrize("rota", ["editar-escola", "excluir-escola"])
def test_a_escola_aberta_no_adm_continua_aberta_depois_do_erro(client, sem_rede_supabase, banco, rota):
    _entrar(client, sem_rede_supabase, papel="desenvolvedor")
    banco.gravar(URLError("getaddrinfo failed"))

    destino, _ = _postar(client, rota)

    assert f"escola_admin_id={ESCOLA_ID}" in destino


@pytest.mark.parametrize("rota", list(ROTAS))
def test_a_rota_que_grava_diz_que_gravou(client, sem_rede_supabase, rota):
    papel, _, _, _ = ROTAS[rota]
    _entrar(client, sem_rede_supabase, papel=papel)
    sem_rede_supabase.table("rpg_config").insert({"id": AVENTURA_ID, "escola_id": ESCOLA_ID, **_aventura()}).execute()

    destino, pagina = _postar(client, rota)

    assert "erro=" not in destino
    assert SUCESSOS[rota] in pagina
    assert 'role="alert"' not in pagina


def test_as_rotas_de_sucesso_gravaram_de_fato(client, sem_rede_supabase):
    _entrar(client, sem_rede_supabase)

    _postar(client, "criar-aventura")
    _postar(client, "preferencias")

    [aventura] = sem_rede_supabase.table("rpg_config").select("*").execute().data
    assert (aventura["titulo"], aventura["escola_id"]) == ("O Cristal", ESCOLA_ID)
    [escola] = sem_rede_supabase.table("escolas").select("*").execute().data
    assert (escola["mostrar_ranking"], escola["modo_guilda"]) == (True, False)


@pytest.mark.parametrize(
    "papel, escola_id, caminho, form, motivo",
    [
        pytest.param("desenvolvedor", None, "/professor/rpg/salvar", FORM_AVENTURA, FALTA_ESCOLA,
                     id="aventura-sem-escola"),
        pytest.param("professor", ESCOLA_ID, "/professor/rpg/salvar", {**FORM_AVENTURA, "cenario": " "}, FALTAM_DADOS,
                     id="aventura-sem-cenario"),
        pytest.param("professor", ESCOLA_ID, "/professor/rpg/excluir", FORM_AVENTURA, FALHA_NAO_ENCONTRADA,
                     id="excluir-sem-config-id"),
        pytest.param("desenvolvedor", None, "/professor/rpg/excluir", {**FORM_AVENTURA, "config_id": AVENTURA_ID},
                     FALTA_ESCOLA, id="excluir-aventura-sem-escola"),
        pytest.param("desenvolvedor", None, "/professor/configuracoes", {}, FALTA_ESCOLA,
                     id="preferencias-sem-escola"),
        pytest.param("desenvolvedor", None, "/professor/adm/escola/criar", {**FORM_ESCOLA, "nome": " "}, FALTAM_DADOS,
                     id="criar-escola-sem-nome"),
        pytest.param("desenvolvedor", None, "/professor/adm/escola/editar",
                     {**FORM_ESCOLA, "escola_id": ESCOLA_ID, "slug": "!!"}, FALTAM_DADOS,
                     id="editar-escola-sem-slug"),
        pytest.param("desenvolvedor", None, "/professor/adm/escola/editar",
                     {**FORM_ESCOLA, "escola_id": ESCOLA_ID, "nome": ""}, FALTAM_DADOS,
                     id="editar-escola-sem-nome"),
        pytest.param("desenvolvedor", None, "/professor/adm/escola/excluir",
                     {**FORM_EXCLUIR_ESCOLA, "confirmar_texto": "apagar"}, CONFIRMACAO_INVALIDA,
                     id="excluir-escola-sem-confirmar"),
    ],
)
def test_o_que_a_rota_recusa_sozinha_nao_vai_ao_banco(client, sem_rede_supabase, banco, papel, escola_id,
                                                      caminho, form, motivo):
    _entrar(client, sem_rede_supabase, papel=papel, escola_id=escola_id)

    resposta = client.post(caminho, data=form)

    assert resposta.status_code == 302
    assert f"erro={motivo}" in resposta.headers["Location"]
    assert "msg=" not in resposta.headers["Location"]
    assert banco.escritas == []


@pytest.mark.parametrize(
    "aba, chave",
    [
        ("rpg", "ra_repetido"),
        ("matricula", SLUG_REPETIDO),
        ("configuracoes", FALTAM_DADOS),
        ("rpg", "<b>Conta bloqueada</b>"),
    ],
)
def test_a_aba_escolhe_o_mapa_e_chave_de_outra_aba_nao_aparece(client, sem_rede_supabase, aba, chave):
    _entrar(client, sem_rede_supabase)

    pagina = client.get("/professor/", query_string={"aba": aba, "erro": chave}).get_data(as_text=True)

    assert 'role="alert"' not in pagina
    assert "bloqueada" not in pagina


def test_nao_encontrada_diz_aventura_na_aba_rpg(client, sem_rede_supabase):
    _entrar(client, sem_rede_supabase)

    pagina = client.get("/professor/", query_string={"aba": "rpg", "erro": FALHA_NAO_ENCONTRADA}).get_data(as_text=True)

    assert MENSAGENS_DA_AVENTURA[FALHA_NAO_ENCONTRADA] in pagina
    assert MENSAGENS_DA_ESCOLA[FALHA_NAO_ENCONTRADA] not in pagina


def test_toda_aba_com_formulario_tem_mapa_de_erros():
    from web.routes.professor_fla import MENSAGENS_DE_ERRO_POR_ABA

    assert MENSAGENS_DE_ERRO_POR_ABA == {
        "matricula": MENSAGENS_DA_MATRICULA,
        "rpg": MENSAGENS_DA_AVENTURA,
        "configuracoes": MENSAGENS_DAS_PREFERENCIAS,
        "adm": MENSAGENS_DA_ESCOLA,
    }


# ============================ TELAS DO STREAMLIT ============================

PAINEL = "st.ui.professor_panel_st"
ADM = "st.ui.admin_st"

SALVAR = "💾 Salvar Aventura"
SIM_EXCLUIR = "✅ Sim, excluir"
SALVAR_PREFERENCIAS = "💾 Salvar Preferências"


@pytest.fixture
def tela(monkeypatch):
    """Roda uma função de tela com o dublê; devolve (roteiro, sessão).

    O módulo é reimportado para pegar o dublê, e o monkeypatch devolve o
    original ao sys.modules (e ao pacote st.ui) no fim.
    """
    for nome in (PAINEL, ADM):
        # Outra bancada pode ter tirado o módulo do sys.modules sem devolver
        # (test_adm_streamlit_por_papel faz isso): importar aqui, fora do
        # dublê, e deixar o sys.modules como estava no fim.
        original = importlib.import_module(nome)
        monkeypatch.setitem(sys.modules, nome, original)
        monkeypatch.setattr(st.ui, nome.rsplit(".", 1)[1], original)

    def rodar(modulo: str, funcao: str, *args, respostas=None, sessao=None):
        with StreamlitFalso(respostas=respostas, sessao=sessao) as fake:
            monkeypatch.delitem(sys.modules, modulo)
            getattr(importlib.import_module(modulo), funcao)(*args)
        return fake.roteiro(), dict(fake.session_state)

    return rodar


def _avisos(roteiro: list[str]) -> list[str]:
    return [linha for linha in roteiro if linha.split(":")[0] in ("success", "error")]


def _erro(texto: str) -> str:
    return f"error: {StreamlitFalso._resumir(texto)}"


def _aventura_nova(**extra) -> dict:
    return {"📖 Título da Aventura": "O Cristal", "🗺️ Cenário da Aventura": "Uma caverna", SALVAR: True, **extra}


def _aventura_aberta(banco) -> dict:
    banco.ler([{"id": AVENTURA_ID, "escola_id": ESCOLA_ID, **_aventura()}])
    return {"selecionar_aventura": f"O Cristal (ID: {AVENTURA_ID[:8]}...)", SALVAR: True}


@pytest.mark.parametrize("falha, motivo", FALHAS)
def test_streamlit_aventura_nova_que_falha_diz_por_que(banco, tela, falha, motivo):
    banco.gravar(falha)

    roteiro, sessao = tela(PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID, respostas=_aventura_nova())

    assert _avisos(roteiro) == [_erro(MENSAGENS_DA_AVENTURA[motivo])]
    assert "rerun" not in roteiro
    assert not sessao


def test_streamlit_aventura_aberta_que_sumiu_diz_nao_encontrada(banco, tela):
    respostas = _aventura_aberta(banco)
    banco.gravar(b"[]")

    roteiro, _ = tela(PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID, respostas=respostas)

    assert _avisos(roteiro) == [_erro(MENSAGENS_DA_AVENTURA[FALHA_NAO_ENCONTRADA])]
    [(metodo, endereco, _)] = banco.escritas
    assert (metodo, f"id=eq.{AVENTURA_ID}" in endereco) == ("PATCH", True)


def test_streamlit_aventura_sem_cenario_nao_vai_ao_banco(banco, tela):
    roteiro, _ = tela(
        PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID,
        respostas=_aventura_nova(**{"🗺️ Cenário da Aventura": "   "}),
    )

    assert _avisos(roteiro) == [_erro(MENSAGENS_DA_AVENTURA[FALTAM_DADOS])]
    assert banco.escritas == []


@pytest.mark.parametrize(
    "respostas, esperado",
    [
        pytest.param(_aventura_nova, "✅ Nova aventura **O Cristal** criada com sucesso!", id="nova"),
        pytest.param(_aventura_aberta, "✅ Aventura **O Cristal** atualizada com sucesso!", id="aberta"),
    ],
)
def test_streamlit_aventura_salva_mostra_o_sucesso_depois_do_rerun(banco, tela, respostas, esperado):
    banco.gravar(b'[{"id": "x"}]')
    respostas = respostas(banco) if respostas is _aventura_aberta else respostas()

    roteiro, sessao = tela(PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID, respostas=respostas)

    assert "rerun" in roteiro
    assert _avisos(roteiro) == []

    volta, sessao_depois = tela(PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID, sessao=sessao)

    assert _avisos(volta) == [f"success: {esperado}"]
    assert not sessao_depois, "o aviso reaparece em toda interação seguinte"


def test_streamlit_exclusao_que_falha_mantem_a_confirmacao(banco, tela):
    banco.ler([{"id": AVENTURA_ID, "escola_id": ESCOLA_ID, **_aventura()}])
    banco.gravar(TimeoutError("timed out"))

    roteiro, sessao = tela(
        PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID,
        respostas={SIM_EXCLUIR: True}, sessao={"confirmar_exclusao": AVENTURA_ID},
    )

    assert _avisos(roteiro) == [_erro(MENSAGENS_DA_AVENTURA[FALHA_SEM_CONEXAO])]
    assert sessao == {"confirmar_exclusao": AVENTURA_ID}


def test_streamlit_exclusao_que_grava_avisa_na_volta(banco, tela):
    banco.ler([{"id": AVENTURA_ID, "escola_id": ESCOLA_ID, **_aventura()}])
    banco.gravar(b'[{"id": "x"}]')

    roteiro, sessao = tela(
        PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID,
        respostas={SIM_EXCLUIR: True}, sessao={"confirmar_exclusao": AVENTURA_ID},
    )

    assert "rerun" in roteiro
    assert "confirmar_exclusao" not in sessao
    volta, _ = tela(PAINEL, "_renderizar_aba_rpg_config", ESCOLA_ID, sessao=sessao)
    assert _avisos(volta) == ["success: Aventura **O Cristal** excluída com sucesso!"]


@pytest.mark.parametrize(
    "falha, motivo",
    FALHAS[:1] + FALHAS[-1:] + [pytest.param(b"[]", FALHA_NAO_ENCONTRADA, id="nao-encontrada")],
)
def test_streamlit_preferencias_que_falham_dizem_por_que(banco, tela, falha, motivo):
    banco.gravar(falha)

    roteiro, sessao = tela(
        PAINEL, "_renderizar_aba_configuracoes", ESCOLA_ID, {}, respostas={SALVAR_PREFERENCIAS: True}
    )

    assert _avisos(roteiro) == [_erro(MENSAGENS_DAS_PREFERENCIAS[motivo])]
    assert not sessao


def test_streamlit_preferencias_salvas_avisam_na_volta(banco, tela):
    banco.gravar(b'[{"id": "esc-1"}]')

    roteiro, sessao = tela(
        PAINEL, "_renderizar_aba_configuracoes", ESCOLA_ID, {}, respostas={SALVAR_PREFERENCIAS: True}
    )
    assert "rerun" in roteiro

    volta, _ = tela(PAINEL, "_renderizar_aba_configuracoes", ESCOLA_ID, {}, sessao=sessao)
    assert _avisos(volta) == ["success: Configurações salvas!"]


def test_streamlit_o_aviso_de_uma_aba_nao_sai_na_outra(banco, tela):
    """Todas as abas são desenhadas a cada execução: com uma chave só, o
    aviso da aventura sairia na primeira aba que olhasse a sessão."""
    guardado = {"aventura_salva": "✅ Nova aventura **O Cristal** criada com sucesso!"}

    matricula, sessao = tela(PAINEL, "_renderizar_aba_matricula", ESCOLA_ID, sessao=dict(guardado))
    preferencias, sessao = tela(PAINEL, "_renderizar_aba_configuracoes", ESCOLA_ID, {}, sessao=sessao)

    assert _avisos(matricula) == [] and _avisos(preferencias) == []
    assert sessao == guardado


ETEC = {"id": ESCOLA_ID, "nome": "ETEC", "slug": "etec", "cor_tema": "#003366",
        "mostrar_ranking": True, "modo_guilda": True}

SECOES_DO_ADM = {
    "cadastrar": ("_secao_cadastrar_escola", (), {"Nome da Instituição": "ETEC", "Confirmar Cadastro": True}),
    "editar": ("_secao_editar_escola", ([ETEC],), {"💾 Salvar alterações": True}),
    "excluir": (
        "_secao_excluir_escola",
        ([ETEC],),
        {
            "Digite exatamente o slug 'etec' para confirmar:": "etec",
            "Digite APAGAR para confirmar a exclusão definitiva:": "APAGAR",
            "🗑️ Excluir definitivamente": True,
        },
    ),
}


def _casos_do_adm():
    for secao in SECOES_DO_ADM:
        for falha in FALHAS[:1] + FALHAS[-1:]:
            yield pytest.param(secao, falha.values[0], falha.values[1], id=f"{secao}-{falha.id}")
    for secao in ("editar", "excluir"):
        yield pytest.param(secao, b"[]", FALHA_NAO_ENCONTRADA, id=f"{secao}-nao-encontrada")
    for secao in ("cadastrar", "editar"):
        yield pytest.param(secao, (409, CORPO_SLUG_REPETIDO), SLUG_REPETIDO, id=f"{secao}-slug-repetido")


@pytest.mark.parametrize("secao, falha, motivo", list(_casos_do_adm()))
def test_streamlit_adm_diz_por_que_nao_gravou(banco, tela, secao, falha, motivo):
    funcao, args, respostas = SECOES_DO_ADM[secao]
    banco.gravar(falha)

    roteiro, sessao = tela(ADM, funcao, *args, respostas=respostas)

    assert _avisos(roteiro) == [_erro(MENSAGENS_DA_ESCOLA[motivo])]
    assert "rerun" not in roteiro
    assert not sessao
    assert banco.escritas, "nem chegou a pedir"


@pytest.mark.parametrize(
    "secao, esperado",
    [
        ("cadastrar", "✅ Unidade 'ETEC' criada com sucesso!"),
        ("editar", "✅ Escola atualizada com sucesso!"),
        ("excluir", "🗑️ Escola excluída com sucesso!"),
    ],
)
def test_streamlit_adm_que_grava_avisa_na_volta(banco, tela, secao, esperado):
    funcao, args, respostas = SECOES_DO_ADM[secao]
    banco.gravar(b'[{"id": "x"}]')

    roteiro, sessao = tela(ADM, funcao, *args, respostas=respostas)

    assert "rerun" in roteiro
    assert _avisos(roteiro) == []

    # na volta, a lista pode ter ficado vazia (a escola foi excluída)
    volta, sessao_depois = tela(ADM, funcao, *(([],) if args else ()), sessao=sessao)

    assert _avisos(volta) == [f"success: {esperado}"]
    assert not sessao_depois
