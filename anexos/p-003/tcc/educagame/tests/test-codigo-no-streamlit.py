"""O Streamlit passa a pedir o código da escola, como o Flask já pedia.

MELHORIA: o código voltou a ser exigido, mas **só em um dos dois frontends**.
No `educagameai.streamlit.app`, clicar no cartão da escola continuava abrindo
o login direto.

É a mesma forma de `conta_pode_entrar`: uma checagem que morava numa tela só,
e por isso valia para metade do produto. A diferença é que ali a metade
desprotegida deixava um professor alcançar a outra escola; aqui o efeito é
mais brando, porque `conta_pode_entrar` já recusa o login cruzado. O que
sobrava era pior de outro jeito: **o papel entregue aos 40 alunos manda
"escolha a escola → código → usuário e senha", e esta tela não tinha onde
digitar o código.** Instrução impressa que não corresponde à tela é o mesmo
defeito do guia da Delta, uma semana depois.

A comparação foi para `services/escola_service.py`, e agora as duas telas
chamam a mesma função — que é a única forma de elas não voltarem a divergir.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from services.escola_service import codigo_confere

# Importado fora do dublê, de propósito: a tela puxa services/repositories, e
# repositories/aluno_repo.py resolve `runtime = get_runtime()` no import. Com
# o dublê instalado ele pegaria o streamlit falso e o teste quebraria por
# causa da bancada. Ver a mesma nota em test_adm_streamlit_por_papel.py.
import st.ui.home_st  # noqa: E402,F401

from tests.apoio_streamlit import StreamlitFalso  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

ETEC = {"id": "1", "nome": "ETEC", "slug": "etecata"}
DELTA = {"id": "2", "nome": "Educacional Delta", "slug": "deltaata"}

# Só os módulos que precisam reexecutar "import streamlit as st".
MODULOS_DA_TELA = ("st.ui.home_st",)


def _rodar_selecao(sessao=None, parametros=None, respostas=None):
    """Desenha a tela de escolher escola e devolve (roteiro, session_state)."""
    with StreamlitFalso(
        respostas=dict(respostas or {}),
        sessao=dict(sessao or {}),
        parametros=dict(parametros or {}),
    ) as fake:
        for modulo in MODULOS_DA_TELA:
            sys.modules.pop(modulo, None)
        tela = importlib.import_module("st.ui.home_st")
        tela.listar_escolas = lambda: [ETEC, DELTA]
        try:
            tela._selecionar_escola_inicial()
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:150]}")
    return fake.roteiro(), fake.session_state


def _pediu_o_codigo(roteiro) -> bool:
    return any("Código da escola" in linha for linha in roteiro)


def _abriu_o_login(roteiro) -> bool:
    return any("Usuário ou e-mail" in linha for linha in roteiro)


# ====================== O PORTÃO ======================


def test_clicar_na_escola_pede_o_codigo_antes_do_login():
    # O defeito: aqui o login abria direto.
    roteiro, _ = _rodar_selecao(parametros={"selecionar_escola": "1"})

    assert _pediu_o_codigo(roteiro), "clicou na escola e caiu no login sem código"
    assert not _abriu_o_login(roteiro)


def test_codigo_errado_nao_libera_e_explica():
    roteiro, sessao = _rodar_selecao(
        parametros={"selecionar_escola": "1"},
        respostas={"Código da escola": "chutei", "Continuar": True},
    )

    assert any("Código incorreto" in linha for linha in roteiro)
    assert not sessao.get("escola_liberada_id")


def test_codigo_certo_libera_a_escola():
    _, sessao = _rodar_selecao(
        parametros={"selecionar_escola": "1"},
        respostas={"Código da escola": "etecata", "Continuar": True},
    )

    assert sessao.get("escola_liberada_id") == "1"


def test_depois_do_codigo_o_login_aparece():
    roteiro, _ = _rodar_selecao(
        sessao={"escola_liberada_id": "1"},
        parametros={"selecionar_escola": "1"},
    )

    assert _abriu_o_login(roteiro), "o código foi aceito e o login não apareceu"
    assert not _pediu_o_codigo(roteiro), "pediu o código de novo"


def test_o_codigo_de_uma_escola_nao_abre_a_outra():
    """Por isso o que se guarda é o id da escola, e não um booleano.

    Num aparelho compartilhado, quem digitou o código da ETEC voltaria à
    lista e entraria na Delta com um clique.
    """
    roteiro, _ = _rodar_selecao(
        sessao={"escola_liberada_id": "1"},
        parametros={"selecionar_escola": "2"},
    )

    assert _pediu_o_codigo(roteiro), "a liberação de uma escola valeu para a outra"
    assert not _abriu_o_login(roteiro)


def test_sem_escola_escolhida_nao_ha_codigo_nem_login():
    roteiro, _ = _rodar_selecao()

    assert not _pediu_o_codigo(roteiro)
    assert not _abriu_o_login(roteiro)


# ====================== SAIR TEM QUE ESQUECER ======================


def test_sair_esquece_o_codigo_digitado():
    """O computador da sala é compartilhado -- é o motivo da trava de sessão.

    Se a liberação sobrevivesse, o próximo aluno pularia o código.
    """
    import st.ui.home_st as tela

    sessao = {"escola_liberada_id": "1"}
    original = tela.st.session_state
    tela.st.session_state = sessao
    try:
        tela._esquecer_codigo_da_escola()
    finally:
        tela.st.session_state = original

    assert "escola_liberada_id" not in sessao


def test_sair_da_conta_limpa_tudo():
    # A outra porta de saída: ela apaga o session_state inteiro, então a
    # liberação vai junto. Prende o comportamento para o dia em que alguém
    # trocar a limpeza total por uma lista de chaves.
    fonte = (RAIZ / "st/ui/home_st.py").read_text(encoding="utf-8-sig")
    corpo = fonte.split("def _sair_da_conta")[1].split("def ")[0]

    assert "del st.session_state[chave]" in corpo


# ====================== A REGRA É UMA SÓ ======================


@pytest.mark.parametrize("digitado", ["etecata", "ETECATA", "  EtecAta  "])
def test_o_codigo_ignora_caixa_e_espaco(digitado):
    # Digitado à mão, muitas vezes no celular, que gosta de maiúscula inicial.
    assert codigo_confere(ETEC, digitado)


@pytest.mark.parametrize("digitado", ["", "   ", "deltaata", "etec", None])
def test_o_que_nao_e_o_codigo_nao_entra(digitado):
    assert not codigo_confere(ETEC, digitado)


def test_escola_sem_slug_nao_vira_a_porta_aberta():
    # Senão a unidade mal cadastrada seria a que qualquer um abre sem digitar.
    assert not codigo_confere({"id": "9", "nome": "Sem slug", "slug": ""}, "")
    assert not codigo_confere({"id": "9", "nome": "Sem slug"}, "qualquer")


def test_os_dois_frontends_chamam_a_mesma_funcao():
    """A garantia estrutural: sem cópia, não há como divergir de novo."""
    tela = (RAIZ / "st/ui/home_st.py").read_text(encoding="utf-8-sig")
    rota = (RAIZ / "web/routes/home_fla.py").read_text(encoding="utf-8-sig")

    for onde, fonte in (("streamlit", tela), ("flask", rota)):
        assert "codigo_confere" in fonte, onde

    # A comparação à mão que existia na rota do Flask não pode voltar.
    assert "== _normalizar_slug(escola" not in rota
    assert "def _normalizar_slug" not in rota, "a cópia do normalizador voltou"


def _sem_comentarios(fonte: str) -> str:
    """Só as linhas de código.

    O comentário que explica a remoção cita o trecho removido — sem isto o
    teste acusaria a própria explicação.
    """
    return "\n".join(
        linha for linha in fonte.splitlines() if not linha.lstrip().startswith("#")
    )


def test_o_slug_nao_volta_para_a_barra_de_enderecos():
    """Escrita morta que parecia o atalho removido do Flask.

    Ninguém lia `?escola=` no Streamlit, mas o slug ficava na URL com cara de
    link que escolhe a escola -- convite para alguém implementar a leitura.
    """
    tela = (RAIZ / "st/ui/home_st.py").read_text(encoding="utf-8-sig")

    assert 'query_params["escola"]' not in _sem_comentarios(tela)
