"""A tela onde o aluno entra: escolher escola, código, usuário e senha.

`_selecionar_escola_inicial` tinha 129 linhas e fazia a tela inteira -- a
grade de cartões em HTML cru, o diagnóstico de quando não há escola nenhuma, o
portão do código e o formulário de login. `test_codigo_no_streamlit.py` cobria
o portão do código, que foi onde apareceu um defeito.

O resto não tinha nada. Separadas as decisões do desenho, a mutação estragou
doze linhas e **dez passaram por toda a bateria** -- entre elas "senha errada
passa a entrar" e "conta de outra escola passa a entrar", que são as duas
coisas que esta tela existe para impedir.

O portão do código continua em `test_codigo_no_streamlit.py`; aqui está o que
vem antes e o que vem depois dele.
"""

from __future__ import annotations

import importlib
import sys

import pytest

import st.ui.home_st  # noqa: F401  (prende a cadeia ao runtime real)
from st.ui.home_st import escola_pedida_na_url, escolas_com_slug, html_dos_cartoes

from tests.apoio_streamlit import StreamlitFalso

ETEC = {"id": "1", "nome": "ETEC", "slug": "etecata"}
DELTA = {"id": "2", "nome": "Educacional Delta", "slug": "deltaata"}
SEM_SLUG = {"id": "3", "nome": "Escola Sem Slug", "slug": ""}

LIBERADA = "escola_liberada_id"
MODULOS_DA_TELA = ("st.ui.home_st",)

ALUNO = {"id": "u1", "username": "ronnie", "role": "aluno", "escola_id": "1"}


class _Bancada(StreamlitFalso):
    """A bancada de sempre, guardando o markdown inteiro.

    O roteiro corta em 90 caracteres, e a grade de escolas é um bloco de HTML
    cru -- todos os cartões começam igual, então o corte esconde justamente o
    que muda.
    """

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.blocos: list[str] = []

    @property
    def markdown(self):
        def escrever(conteudo="", *_a, **_k):
            self.blocos.append(str(conteudo))
            self._anotar(f"markdown: {self._resumir(conteudo)}")
        return escrever


def _rodar(escolas, sessao=None, parametros=None, respostas=None,
           erro_escolas="", usuario=None, pode_entrar=(True, "")):
    """Desenha a tela e devolve (roteiro, html, session_state, chamadas)."""
    import services.auth_service as auth

    chamadas: list[str] = []
    original = (auth.autenticar, auth.conta_pode_entrar)

    def _autenticar(_u, _s):
        chamadas.append("autenticar")
        return dict(usuario) if usuario else None

    def _pode_entrar(_u, _e):
        chamadas.append("conta_pode_entrar")
        return tuple(pode_entrar)

    auth.autenticar = _autenticar
    auth.conta_pode_entrar = _pode_entrar
    try:
        with _Bancada(
            respostas=dict(respostas or {}),
            sessao=dict(sessao or {}),
            parametros=dict(parametros or {}),
        ) as fake:
            for modulo in MODULOS_DA_TELA:
                sys.modules.pop(modulo, None)
            tela = importlib.import_module("st.ui.home_st")
            tela.listar_escolas = lambda: list(escolas)
            tela.obter_ultimo_erro_listar_escolas = lambda: erro_escolas
            tela.diagnostico_supabase_seguro = lambda: {"projeto": "demo"}
            try:
                tela._selecionar_escola_inicial()
            except Exception as erro:  # noqa: BLE001
                if type(erro).__name__ != "ParouAqui":
                    fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:150]}")
    finally:
        auth.autenticar, auth.conta_pode_entrar = original

    return fake.roteiro(), "".join(fake.blocos), dict(fake.session_state), chamadas


def _entrando(**extra):
    """Uma tentativa de login, com o código da escola já digitado."""
    base = dict(
        escolas=[ETEC, DELTA],
        parametros={"selecionar_escola": "1"},
        sessao={LIBERADA: "1"},
        respostas={"Entrar": True, "Usuário ou e-mail": "ronnie", "Senha": "boa"},
    )
    base.update(extra)
    return _rodar(**base)


# ====================== O LOGIN ======================


def test_senha_errada_nao_entra():
    """Nenhum teste segurava isto: apagar a checagem deixava qualquer senha
    entrar, e a tela continuava com a mesma cara."""
    roteiro, _html, sessao, _ch = _entrando(usuario=None)

    assert any("inválidos" in linha for linha in roteiro), roteiro[-4:]
    assert "usuario" not in sessao, "entrou com senha errada"
    assert "escola" not in sessao


def test_login_certo_entra():
    """O par que protege: apertar não pode fechar a porta de quem tem razão."""
    _roteiro, _html, sessao, chamadas = _entrando(usuario=ALUNO)

    assert sessao.get("usuario") == ALUNO
    assert sessao.get("escola") == ETEC
    assert chamadas == ["autenticar", "conta_pode_entrar"]


def test_conta_de_outra_escola_nao_entra_por_esta_porta():
    """A regra mora em `conta_pode_entrar` e vale nos dois frontends. Aqui se
    prova que esta tela a OBEDECE -- antes, professor sem escola entrava em
    qualquer unidade e abria o painel de gestão dela.
    """
    roteiro, _html, sessao, _ch = _entrando(
        usuario={"id": "u2", "username": "profdelta", "role": "professor", "escola_id": "2"},
        pode_entrar=(False, "Esta conta pertence a outra escola."),
    )

    assert any("outra escola" in linha for linha in roteiro), roteiro[-4:]
    assert "usuario" not in sessao, "entrou numa escola que não é a dele"


@pytest.mark.parametrize(
    "usuario_digitado,senha_digitada",
    [("", "boa"), ("ronnie", ""), ("", ""), ("   ", "boa")],
    ids=["sem-usuario", "sem-senha", "nada", "so-espacos"],
)
def test_campo_em_branco_nao_chega_a_consultar_o_banco(usuario_digitado, senha_digitada):
    """Pedir para preencher é melhor que "usuário ou senha inválidos" -- e
    poupa uma ida à rede por formulário vazio, que no plano gratuito conta."""
    roteiro, _html, sessao, chamadas = _entrando(
        usuario=ALUNO,
        respostas={"Entrar": True, "Usuário ou e-mail": usuario_digitado, "Senha": senha_digitada},
    )

    assert any("Informe usuário e senha" in linha for linha in roteiro), roteiro[-4:]
    assert chamadas == [], "foi ao banco com o formulário em branco"
    assert "usuario" not in sessao


def test_sem_clicar_em_entrar_nada_acontece():
    """O formulário é desenhado a cada recarga da página; só o clique age."""
    _roteiro, _html, sessao, chamadas = _entrando(
        usuario=ALUNO, respostas={"Usuário ou e-mail": "ronnie", "Senha": "boa"},
    )

    assert chamadas == []
    assert "usuario" not in sessao


# ====================== A GRADE DE ESCOLAS ======================


def test_escola_sem_slug_fica_fora_da_grade():
    """O slug identifica a unidade no resto do sistema. Um cartão sem ele
    levaria a uma tela que não sabe de que escola está falando."""
    assert escolas_com_slug([ETEC, SEM_SLUG, DELTA]) == [ETEC, DELTA]
    assert escolas_com_slug([SEM_SLUG]) == []
    assert escolas_com_slug(None) == []


def test_escola_sem_slug_nao_pode_ser_escolhida_nem_pela_url():
    """Digitar o id na barra de endereços não pode contornar a grade."""
    validas = escolas_com_slug([ETEC, SEM_SLUG])

    _pedido, escola = escola_pedida_na_url(validas, "3")

    assert escola is None


@pytest.mark.parametrize(
    "parametro,esperado",
    [("2", "2"), (["2"], "2"), (["2", "1"], "2"), ([], ""), ("", ""), (None, "")],
    ids=["texto", "lista", "lista-repetida", "lista-vazia", "vazio", "nulo"],
)
def test_o_parametro_da_url_vale_como_texto_ou_como_lista(parametro, esperado):
    """`st.query_params` devolve ora texto, ora lista -- depende de a URL
    repetir o parâmetro. Ler o formato errado transformava um clique legítimo
    em "nenhuma escola escolhida", e a tela voltava ao começo sem explicar."""
    pedido, escola = escola_pedida_na_url([ETEC, DELTA], parametro)

    assert pedido == esperado
    assert (escola or {}).get("id", "") == esperado


def test_o_nome_da_escola_nao_vira_marcacao():
    """O nome vem do banco e é escrito dentro de HTML cru. Um `<` fecharia a
    tag e o resto da página passaria a ser marcação de outra pessoa."""
    malicioso = {"id": "9", "nome": '<script>alert("x")</script>', "slug": "s"}

    html = html_dos_cartoes([malicioso], "9")

    assert "<script>" not in html, html
    assert "&lt;script&gt;" in html


def test_o_id_da_escola_e_escapado_para_a_url():
    """Ele entra num href. Sem escapar, um id com `&` ou espaço quebra o link
    ou pendura outro parâmetro nele."""
    html = html_dos_cartoes([{"id": "a b&c", "nome": "X", "slug": "s"}], "")

    assert "?selecionar_escola=a%20b%26c" in html, html


def test_so_o_cartao_escolhido_fica_destacado():
    """É o único retorno visual de que o clique funcionou."""
    html = html_dos_cartoes([ETEC, DELTA], "2")

    assert html.count("edu-school-card--selected") == 1
    marcado = html.split("edu-school-card--selected")[1]
    assert "Educacional Delta" in marcado.split("</a>")[0]


def test_sem_escolha_nenhum_cartao_fica_destacado():
    """O par: destacar sempre é o mesmo que não destacar."""
    assert "edu-school-card--selected" not in html_dos_cartoes([ETEC, DELTA], "")


# ====================== QUANDO NÃO HÁ ESCOLA NENHUMA ======================


def test_banco_vazio_e_falha_de_conexao_dao_recados_diferentes():
    """São duas causas muito diferentes com o mesmo sintoma. Sem separar,
    "nenhuma escola" manda procurar cadastro quando o problema é a conexão --
    e a pessoa vai cadastrar escola num banco que já tem escola."""
    vazio, _h1, _s1, _c1 = _rodar([], erro_escolas="")
    com_erro, _h2, _s2, _c2 = _rodar([], erro_escolas="connection refused")

    assert any("Nenhuma escola cadastrada" in linha for linha in vazio)
    assert not any("Não foi possível consultar" in linha for linha in vazio)

    assert any("Não foi possível consultar" in linha for linha in com_erro)
    assert any("connection refused" in linha for linha in com_erro), "o erro real não aparece"
