"""A aventura do RPG só é editada ou excluída pela escola dona dela.

Editar e excluir filtravam só pelo id, que vem de um campo hidden do
formulário, e o cliente usa a chave service_role (o RLS não protege). Um
professor da escola A que postasse o id de uma aventura da escola B:

- editando, a alterava -- e, como o payload levava o escola_id da sessão,
  a aventura passava a ser da escola A;
- excluindo, a apagava.

O id não aparece na lista de outra escola, mas o Streamlit o mostra inteiro
na legenda de cada aventura. Aqui o banco é o de memória do conftest, que
aplica os filtros: dá para ver a aventura da B continuar como estava.
"""

from __future__ import annotations

import importlib
import json
import sys

import pytest

import repositories.rpg_config_repo as rpg_config_repo
import repositories.supabase_client as sc
from repositories.gravacao import FALHA_NAO_ENCONTRADA
from services import rpg_config_service
from services.avisos_de_gravacao import FALTA_ESCOLA

# Fora do dublê, de propósito (ver test_adm_streamlit_por_papel).
import st.ui  # noqa: E402
import st.ui.professor_panel_st  # noqa: E402,F401

from tests.apoio_flask import carimbar_sessao
from tests.apoio_streamlit import StreamlitFalso

MENSAGENS = rpg_config_service.MENSAGENS_DA_AVENTURA

ESCOLA_A = "esc-a"
ESCOLA_B = "esc-b"
AVENTURA_A = "aaaaaaaa-0000-4000-8000-00000000000a"
AVENTURA_B = "bbbbbbbb-0000-4000-8000-00000000000b"

DA_B = {
    "id": AVENTURA_B, "escola_id": ESCOLA_B, "titulo": "Masmorra da B", "cenario": "Cenário secreto da B",
    "materia": "Física", "serie": "9º Ano",
}
DA_A = {
    "id": AVENTURA_A, "escola_id": ESCOLA_A, "titulo": "Floresta da A", "cenario": "Cenário da A",
    "materia": "Química", "serie": "1º Ano EM",
}
INVASAO = {"titulo": "Invadida", "cenario": "Trocado pela A", "materia": "Física", "serie": "9º Ano"}


@pytest.fixture
def banco(sem_rede_supabase):
    for escola in (ESCOLA_A, ESCOLA_B):
        sem_rede_supabase.table("escolas").insert(
            {"id": escola, "nome": escola.upper(), "slug": escola, "mostrar_ranking": True, "modo_guilda": True}
        ).execute()
    for aventura in (DA_A, DA_B):
        sem_rede_supabase.table("rpg_config").insert(dict(aventura)).execute()
    return sem_rede_supabase


def _aventuras(banco) -> dict[str, dict]:
    return {linha["id"]: linha for linha in banco.table("rpg_config").select("*").execute().data}


def _intactas(banco) -> None:
    """As duas aventuras exatamente como nasceram -- nenhuma a mais."""
    assert _aventuras(banco) == {AVENTURA_A: DA_A, AVENTURA_B: DA_B}


# ============================== REPOSITÓRIO ==============================


def test_outra_escola_nao_altera_a_aventura(banco):
    assert rpg_config_repo.atualizar_rpg_config(ESCOLA_A, AVENTURA_B, INVASAO) == (None, FALHA_NAO_ENCONTRADA)
    _intactas(banco)


def test_outra_escola_nao_puxa_a_aventura_pelo_payload(banco):
    """Nem com o escola_id no próprio payload: a escola só entra no filtro."""
    resultado, motivo = rpg_config_repo.atualizar_rpg_config(ESCOLA_B, AVENTURA_B, {**INVASAO, "escola_id": ESCOLA_A})

    assert motivo == ""
    assert resultado.data[0]["escola_id"] == ESCOLA_B
    assert _aventuras(banco)[AVENTURA_B]["escola_id"] == ESCOLA_B


def test_outra_escola_nao_exclui_a_aventura(banco):
    assert rpg_config_repo.excluir_rpg_config(ESCOLA_A, AVENTURA_B) == (None, FALHA_NAO_ENCONTRADA)
    _intactas(banco)


def test_a_dona_altera_e_exclui_a_propria(banco):
    resultado, motivo = rpg_config_repo.atualizar_rpg_config(ESCOLA_B, AVENTURA_B, {"titulo": "Masmorra nova"})
    assert (motivo, resultado.data[0]["titulo"]) == ("", "Masmorra nova")

    resultado, motivo = rpg_config_repo.excluir_rpg_config(ESCOLA_B, AVENTURA_B)
    assert (motivo, [linha["id"] for linha in resultado.data]) == ("", [AVENTURA_B])
    assert _aventuras(banco) == {AVENTURA_A: DA_A}


class _Resposta:
    def __init__(self, corpo: bytes):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_o_pedido_ao_supabase_leva_os_dois_filtros(monkeypatch):
    """O banco de memória imita o filtro; este confere o que sai de verdade."""
    pedidos = []

    def falso_urlopen(request, timeout=None):
        pedidos.append((request.get_method(), request.full_url, json.loads(request.data or b"null")))
        return _Resposta(b'[{"id": "x"}]')

    monkeypatch.setattr(sc, "urlopen", falso_urlopen)
    monkeypatch.setattr(rpg_config_repo, "supabase", sc._SupabaseRestClient("https://example.supabase.co", "k"))

    rpg_config_repo.atualizar_rpg_config(ESCOLA_A, AVENTURA_B, {**INVASAO, "escola_id": ESCOLA_A})
    rpg_config_repo.excluir_rpg_config(ESCOLA_A, AVENTURA_B)

    [(patch, url_patch, corpo), (delete, url_delete, _)] = pedidos
    assert (patch, delete) == ("PATCH", "DELETE")
    for url in (url_patch, url_delete):
        assert f"id=eq.{AVENTURA_B}" in url
        assert f"escola_id=eq.{ESCOLA_A}" in url
    assert "escola_id" not in corpo


# ================================ SERVIÇO ================================


def test_servico_nao_salva_aventura_de_outra_escola(banco):
    assert rpg_config_service.salvar_aventura(ESCOLA_A, AVENTURA_B, INVASAO) == (False, FALHA_NAO_ENCONTRADA)
    _intactas(banco)


def test_servico_nao_exclui_aventura_de_outra_escola(banco):
    assert rpg_config_service.excluir_aventura(ESCOLA_A, AVENTURA_B) == (False, FALHA_NAO_ENCONTRADA)
    _intactas(banco)


@pytest.mark.parametrize(
    "escola_id, config_id, motivo",
    [
        pytest.param(None, AVENTURA_B, FALTA_ESCOLA, id="sem-escola"),
        pytest.param("  ", AVENTURA_B, FALTA_ESCOLA, id="escola-em-branco"),
        pytest.param(ESCOLA_B, "", FALHA_NAO_ENCONTRADA, id="sem-id"),
        pytest.param(ESCOLA_B, None, FALHA_NAO_ENCONTRADA, id="id-none"),
    ],
)
def test_exclusao_incompleta_nao_vai_ao_banco(monkeypatch, banco, escola_id, config_id, motivo):
    monkeypatch.setattr(rpg_config_service, "excluir_rpg_config", lambda *_: pytest.fail("foi ao banco"))

    assert rpg_config_service.excluir_aventura(escola_id, config_id) == (False, motivo)
    _intactas(banco)


# ============================== TELA DO FLASK ==============================


def _entrar(client, escola_id: str, papel: str = "professor"):
    with client.session_transaction() as sess:
        sess["usuario_role"] = papel
        sess["escola_id"] = escola_id
        sess["escola_nome"] = escola_id.upper()
        carimbar_sessao(sess)


def _postar(client, caminho: str, config_id: str) -> tuple[str, str]:
    resposta = client.post(caminho, data={**INVASAO, "config_id": config_id})
    assert resposta.status_code == 302
    destino = resposta.headers["Location"]
    return destino, client.get(destino).get_data(as_text=True)


@pytest.mark.parametrize(
    "caminho, sucesso",
    [("/professor/rpg/salvar", "Aventura salva."), ("/professor/rpg/excluir", "Aventura excluida.")],
)
def test_professor_da_a_nao_mexe_na_aventura_da_b(client, banco, caminho, sucesso):
    _entrar(client, ESCOLA_A)

    destino, pagina = _postar(client, caminho, AVENTURA_B)

    assert f"erro={FALHA_NAO_ENCONTRADA}" in destino
    assert sucesso not in pagina
    assert MENSAGENS[FALHA_NAO_ENCONTRADA] in pagina
    # nem cópia criada na A, nem o conteúdo da B na tela da A
    _intactas(banco)
    assert "Cenário secreto da B" not in pagina
    assert "Masmorra da B" not in pagina


def test_professor_da_b_edita_a_propria(client, banco):
    _entrar(client, ESCOLA_B)

    destino, pagina = _postar(client, "/professor/rpg/salvar", AVENTURA_B)

    assert "Aventura salva." in pagina
    assert "erro=" not in destino
    aventuras = _aventuras(banco)
    assert (aventuras[AVENTURA_B]["titulo"], aventuras[AVENTURA_B]["escola_id"]) == ("Invadida", ESCOLA_B)
    assert aventuras[AVENTURA_A] == DA_A


def test_professor_da_b_exclui_a_propria(client, banco):
    _entrar(client, ESCOLA_B)

    _, pagina = _postar(client, "/professor/rpg/excluir", AVENTURA_B)

    assert "Aventura excluida." in pagina
    assert _aventuras(banco) == {AVENTURA_A: DA_A}


def test_desenvolvedor_sem_escola_nao_exclui_aventura(client, banco):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "desenvolvedor"
        carimbar_sessao(sess)

    resposta = client.post("/professor/rpg/excluir", data={"config_id": AVENTURA_B})

    assert f"erro={FALTA_ESCOLA}" in resposta.headers["Location"]
    _intactas(banco)


# ============================ TELA DO STREAMLIT ============================

PAINEL = "st.ui.professor_panel_st"


@pytest.fixture
def tela(monkeypatch):
    # Outra bancada pode ter tirado o módulo do sys.modules sem devolver
    # (test_adm_streamlit_por_papel faz isso): importar aqui, fora do dublê,
    # e deixar o sys.modules como estava no fim.
    original = importlib.import_module(PAINEL)
    monkeypatch.setitem(sys.modules, PAINEL, original)
    monkeypatch.setattr(st.ui, "professor_panel_st", original)

    def rodar(escola_id: str, respostas=None, sessao=None):
        with StreamlitFalso(respostas=respostas, sessao=sessao) as fake:
            monkeypatch.delitem(sys.modules, PAINEL)
            importlib.import_module(PAINEL)._renderizar_aba_rpg_config(escola_id)
        return fake.roteiro(), dict(fake.session_state)

    return rodar


def _avisos(roteiro: list[str]) -> list[str]:
    return [linha for linha in roteiro if linha.split(":")[0] in ("success", "error")]


def test_streamlit_da_a_nao_exclui_a_aventura_da_b(banco, tela):
    """O id da exclusão mora na sessão; a tela não pode confiar que é da escola."""
    roteiro, sessao = tela(
        ESCOLA_A, respostas={"✅ Sim, excluir": True}, sessao={"confirmar_exclusao": AVENTURA_B}
    )

    assert _avisos(roteiro) == [f"error: {StreamlitFalso._resumir(MENSAGENS[FALHA_NAO_ENCONTRADA])}"]
    assert "rerun" not in roteiro
    assert sessao == {"confirmar_exclusao": AVENTURA_B}
    _intactas(banco)


def test_streamlit_da_b_exclui_a_propria(banco, tela):
    roteiro, sessao = tela(
        ESCOLA_B, respostas={"✅ Sim, excluir": True}, sessao={"confirmar_exclusao": AVENTURA_B}
    )

    assert "rerun" in roteiro
    assert "confirmar_exclusao" not in sessao
    assert _aventuras(banco) == {AVENTURA_A: DA_A}


def test_streamlit_edita_a_aventura_da_propria_escola(banco, tela):
    roteiro, _ = tela(
        ESCOLA_B,
        respostas={
            "selecionar_aventura": f"Masmorra da B (ID: {AVENTURA_B[:8]}...)",
            "📖 Título da Aventura": "Masmorra editada",
            "💾 Salvar Aventura": True,
        },
    )

    assert "rerun" in roteiro
    aventuras = _aventuras(banco)
    assert (aventuras[AVENTURA_B]["titulo"], aventuras[AVENTURA_B]["escola_id"]) == ("Masmorra editada", ESCOLA_B)
    assert aventuras[AVENTURA_A] == DA_A


def test_streamlit_so_lista_as_aventuras_da_escola(banco, tela):
    roteiro, _ = tela(ESCOLA_A)

    texto = "\n".join(roteiro)
    assert "Floresta da A" in texto
    assert "Masmorra da B" not in texto
    assert AVENTURA_B not in texto
