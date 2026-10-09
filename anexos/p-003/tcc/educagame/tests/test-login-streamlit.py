from __future__ import annotations

import pytest

import services.aluno_auth_service as aluno_auth_service
from services.auth_service import autenticar
from services.usuario_service import criar_usuario


def test_aluno_entra_com_usuario_e_senha(sem_rede_supabase):
    # MELHORIA: antes o Streamlit nao tinha login -- entrava-se digitando o
    # SLUG da escola (um codigo compartilhado pela turma inteira, que nao
    # identifica ninguem) e depois escolhia-se num dropdown por qual aluno
    # jogar. Agora usa o mesmo services.auth_service do frontend Flask.
    ok, erro = aluno_auth_service.criar_aluno_com_username(
        escola_id="escola-1",
        nome="Aluno Streamlit",
        ra_identificacao="ST-1",
        ano_escolar="1º Ano EM",
        periodo="Manhã",
        username="alunost",
        senha="senha123",
        consentimento_responsavel=True,
    )
    assert ok, erro

    usuario = autenticar("alunost", "senha123")

    assert usuario is not None
    assert usuario["role"] == "aluno"
    assert usuario["aluno_nome"] == "Aluno Streamlit"
    assert usuario["escola_id"] == "escola-1"
    assert usuario["aluno_id"]


def test_senha_errada_nao_entra(sem_rede_supabase):
    aluno_auth_service.criar_aluno_com_username(
        escola_id="escola-1",
        nome="Aluno Streamlit",
        ra_identificacao="ST-2",
        ano_escolar="1º Ano EM",
        periodo="Manhã",
        username="alunost2",
        senha="senha123",
        consentimento_responsavel=True,
    )

    assert autenticar("alunost2", "errada") is None
    assert autenticar("nao-existe", "senha123") is None


def test_professor_entra_e_nao_vira_aluno(sem_rede_supabase):
    criar_usuario("prof_st", "senhaProf1", "professor")

    usuario = autenticar("prof_st", "senhaProf1")

    assert usuario is not None
    assert usuario["role"] == "professor"
    # professor nao carrega aluno_id: e isso que faz o seletor de aluno
    # continuar aparecendo para ele (ver selecionar_aluno em mode_common_st)
    assert "aluno_id" not in usuario


@pytest.mark.parametrize("papel", ["aluno", "professor", "desenvolvedor"])
def test_seletor_de_aluno_so_trava_para_aluno(monkeypatch, papel):
    # O seletor deixava qualquer um jogar (e pontuar) no nome de outro. Com
    # login, o aluno fica preso a propria conta; professor e desenvolvedor
    # seguem podendo abrir a tela de um aluno especifico.
    import streamlit as st

    from st.ui import mode_common_st

    alunos = [
        {"id": "a1", "nome": "Aluno Um"},
        {"id": "a2", "nome": "Aluno Dois"},
    ]
    estado = {"usuario": {"role": papel, "aluno_id": "a2"}}
    monkeypatch.setattr(mode_common_st.st, "session_state", estado, raising=False)
    monkeypatch.setattr(mode_common_st.st, "caption", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(mode_common_st.st, "warning", lambda *a, **k: None, raising=False)

    chamou_selectbox = {"sim": False}

    def _selectbox(label, opcoes, key=None):
        chamou_selectbox["sim"] = True
        return opcoes[0]

    monkeypatch.setattr(mode_common_st.st, "selectbox", _selectbox, raising=False)

    escolhido = mode_common_st.selecionar_aluno(alunos, "Quem joga?", "k")

    if papel == "aluno":
        assert chamou_selectbox["sim"] is False, "aluno nao pode escolher outro nome"
        assert escolhido["id"] == "a2"
    else:
        assert chamou_selectbox["sim"] is True, "professor precisa do seletor"


def test_aluno_de_outra_escola_nao_cai_no_seletor(monkeypatch):
    # Conta de aluno que nao esta na lista desta escola: nao pode cair no
    # dropdown (isso deixaria jogar no nome de outro).
    import streamlit as st

    from st.ui import mode_common_st

    alunos = [{"id": "a1", "nome": "Aluno Um"}]
    estado = {"usuario": {"role": "aluno", "aluno_id": "fora-da-escola"}}
    monkeypatch.setattr(mode_common_st.st, "session_state", estado, raising=False)
    monkeypatch.setattr(mode_common_st.st, "caption", lambda *a, **k: None, raising=False)

    avisos = []
    monkeypatch.setattr(mode_common_st.st, "warning", lambda m, *a, **k: avisos.append(m), raising=False)
    monkeypatch.setattr(
        mode_common_st.st, "selectbox", lambda *a, **k: pytest.fail("nao deveria oferecer seletor"), raising=False
    )

    assert mode_common_st.selecionar_aluno(alunos, "Quem joga?", "k") is None
    assert avisos, "deveria avisar o aluno"


class _QueryParamsFalso(dict):
    def clear(self):
        super().clear()


class _EstadoFalso(dict):
    """st.session_state aceita chave E atributo; o codigo usa os dois."""

    def __getattr__(self, nome):
        try:
            return self[nome]
        except KeyError as erro:
            raise AttributeError(nome) from erro

    def __setattr__(self, nome, valor):
        self[nome] = valor


@pytest.mark.parametrize(
    "papel,esperado",
    [("aluno", False), ("professor", True), ("desenvolvedor", True)],
)
def test_painel_do_professor_so_para_gestao(monkeypatch, papel, esperado):
    from st.ui import home_st

    estado = _EstadoFalso(usuario={"role": papel})
    monkeypatch.setattr(home_st.st, "session_state", estado, raising=False)

    assert home_st._pagina_permitida("👨‍🏫 Professor") is esperado
    # as paginas de aluno seguem livres para todos
    assert home_st._pagina_permitida("🎮 Jogar") is True


def test_aluno_nao_entra_no_painel_pela_url(monkeypatch):
    # O slug da pagina vem de st.query_params, entao "?pagina=professor"
    # levava o aluno direto ao painel de gestao, sem passar por card nenhum.
    from st.ui import home_st

    estado = _EstadoFalso(usuario={"role": "aluno"})
    monkeypatch.setattr(home_st.st, "session_state", estado, raising=False)
    monkeypatch.setattr(
        home_st.st, "query_params", _QueryParamsFalso(pagina="professor"), raising=False
    )

    assert home_st._renderizar_sidebar({}, None, None) == "🏠 Início"


def test_professor_entra_no_painel_pela_url(monkeypatch):
    from st.ui import home_st

    estado = _EstadoFalso(usuario={"role": "professor"})
    monkeypatch.setattr(home_st.st, "session_state", estado, raising=False)
    monkeypatch.setattr(
        home_st.st, "query_params", _QueryParamsFalso(pagina="professor"), raising=False
    )

    assert home_st._renderizar_sidebar({}, None, None) == "👨‍🏫 Professor"


def test_sessao_ja_aberta_no_painel_cai_para_inicio_se_for_aluno(monkeypatch):
    from st.ui import home_st

    estado = _EstadoFalso(usuario={"role": "aluno"}, pagina_atual="👨‍🏫 Professor")
    monkeypatch.setattr(home_st.st, "session_state", estado, raising=False)
    monkeypatch.setattr(home_st.st, "query_params", _QueryParamsFalso(), raising=False)

    assert home_st._renderizar_sidebar({}, None, None) == "🏠 Início"
