"""RF14: ranking e Batalha de Guildas só aparecem se a escola deixar.

MELHORIA: `mostrar_ranking` e `modo_guilda` eram gravados pelos dois painéis
(configurações do professor e ADM, nos dois frontends), mas nenhuma tela os
lia antes de desenhar. O "Ranking da escola" do Meu Progresso, o card e a
página da Batalha de Guildas e o bloco "Ranking e guildas" da home do
Streamlit saíam iguais com a opção ligada ou desligada.

O TCC documenta o contrário (RF14): o ranking individual só aparece com
`mostrar_ranking` habilitado, a disputa entre turmas só com `modo_guilda`
habilitado, e com a opção desligada o aluno mantém a pontuação, mas não vê a
classificação.

Cada opção é conferida LIGADA e DESLIGADA, nas duas interfaces. Só o par
prova alguma coisa: um teste só com a opção desligada passaria também numa
tela que nunca mostra ranking nenhum.
"""

from __future__ import annotations

import importlib
import runpy
import sys
from pathlib import Path

import pytest

import services.escola_service as escola_service
import web.routes.guildas_fla as guildas_fla
import web.routes.perfil_fla as perfil_fla
import web.routes.progresso_fla as progresso_fla
from services.escola_service import (
    AVISO_GUILDAS_DESLIGADAS,
    atualizar_escola,
    escola_atualizada,
    mostra_guildas,
    mostra_ranking,
)
from tests.apoio_flask import carimbar_sessao
from tests.apoio_streamlit import StreamlitFalso

# Importados AQUI, fora do dublê: a cadeia services/repositories resolve
# `get_runtime()` no import e, com o dublê instalado, pegaria um streamlit sem
# cache_data (ver tests/test_adm_streamlit_por_papel.py). O app.py puxa todas
# estas telas; importando antes, só a camada purgada abaixo pega o dublê.
try:
    import streamlit_javascript  # noqa: F401
except ModuleNotFoundError:  # o app.py tem o mesmo desvio
    pass
import core.design_system  # noqa: E402,F401
import services.rpg_config_service  # noqa: E402,F401
import services.rpg_service  # noqa: E402,F401
import st.ui.home_st  # noqa: E402,F401
import st.ui.tela_guildas_st  # noqa: E402,F401
import st.ui.admin_st  # noqa: E402,F401
import st.ui.ajuda_st  # noqa: E402,F401
import st.ui.mode_common_st  # noqa: E402,F401
import st.ui.perfil_aluno_st  # noqa: E402,F401
import st.ui.professor_panel_st  # noqa: E402,F401
import st.ui.tela_boss_rush_enem_st  # noqa: E402,F401
import st.ui.tela_enem_st  # noqa: E402,F401
import st.ui.tela_escape_room_st  # noqa: E402,F401
import st.ui.tela_laboratorio_st  # noqa: E402,F401
import st.ui.tela_oraculo_st  # noqa: E402,F401
import st.ui.tela_rpg_st  # noqa: E402,F401
import st.ui.tela_treino_st  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parents[1]

ESCOLA_ID = "escola-rf14"
SLUG = "escola-rf14"
ALUNO = {"id": "u-1", "username": "aluno", "role": "aluno", "escola_id": ESCOLA_ID}

RANKING = [{"id": "a9", "nome": "Colega Campeao", "pontos_totais": 999}]
GUILDAS = [{"guilda": "Guilda Vencedora", "pontos_grupais": 500}]
ALUNOS_DAS_GUILDAS = [
    {"id": "a1", "nome": "Ana", "ano_escolar": "1 Ano EM", "periodo": "Manha", "pontos_totais": 40},
    {"id": "a2", "nome": "Bia", "ano_escolar": "2 Ano EM", "periodo": "Tarde", "pontos_totais": 70},
]

# As quatro combinações: uma opção não pode arrastar a outra.
COMBINACOES = [(True, True), (True, False), (False, True), (False, False)]


def _escola(ranking: bool, guilda: bool) -> dict:
    return {
        "id": ESCOLA_ID,
        "nome": "Escola RF14",
        "slug": SLUG,
        "cor_tema": "#003366",
        "mostrar_ranking": ranking,
        "modo_guilda": guilda,
    }


def _gravar_escola(banco, ranking: bool, guilda: bool) -> None:
    banco.table("escolas").insert(_escola(ranking, guilda)).execute()


# ====================== A REGRA ======================


@pytest.mark.parametrize("ranking,guilda", COMBINACOES)
def test_cada_opcao_decide_so_o_que_e_dela(ranking, guilda):
    escola = _escola(ranking, guilda)

    assert mostra_ranking(escola) is ranking
    assert mostra_guildas(escola) is guilda


@pytest.mark.parametrize("escola", [None, {}, "escola-rf14", []])
def test_sem_escola_lida_nada_aparece(escola):
    # "Só é exibido se estiver habilitado": o que não se leu não está.
    assert mostra_ranking(escola) is False
    assert mostra_guildas(escola) is False


def test_escola_sem_a_coluna_segue_o_default_do_schema():
    # 20260803120000_bootstrap.sql: DEFAULT true -- o mesmo `.get(campo, True)` dos painéis.
    assert mostra_ranking({"id": ESCOLA_ID}) is True
    assert mostra_guildas({"id": ESCOLA_ID}) is True


def test_null_gravado_no_banco_conta_como_desligado():
    # Os dois painéis desenham o interruptor DESLIGADO para null; a tela do
    # aluno não pode discordar do que o professor vê.
    escola = {"id": ESCOLA_ID, "mostrar_ranking": None, "modo_guilda": None}

    assert mostra_ranking(escola) is False
    assert mostra_guildas(escola) is False


def test_escola_atualizada_le_o_banco_e_nao_a_copia_do_login(sem_rede_supabase):
    _gravar_escola(sem_rede_supabase, ranking=True, guilda=True)
    copia_do_login = _escola(ranking=True, guilda=True)

    # o professor desliga depois que o aluno entrou
    atualizar_escola(ESCOLA_ID, {"mostrar_ranking": False, "modo_guilda": False})
    atual = escola_atualizada(ESCOLA_ID, reserva=copia_do_login)

    assert mostra_ranking(atual) is False
    assert mostra_guildas(atual) is False


def test_escola_atualizada_so_usa_a_reserva_quando_o_banco_nao_tem_a_escola(sem_rede_supabase):
    reserva = _escola(ranking=True, guilda=False)

    assert escola_atualizada("nao-existe", reserva=reserva) is reserva
    assert escola_atualizada(None, reserva=reserva) is reserva
    assert escola_atualizada("nao-existe") is None


# ====================== FLASK ======================


def _logar_aluno(cliente) -> None:
    with cliente.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["usuario_escola_id"] = ESCOLA_ID
        sess["escola_id"] = ESCOLA_ID
        sess["escola_slug"] = SLUG
        sess["escola_nome"] = "Escola RF14"
        sess["aluno_id"] = "aluno-1"
        sess["aluno_nome"] = "Aluno Teste"
        sess["ano_escolar"] = "1º EM"
        carimbar_sessao(sess)


def _logar_professor(cliente) -> None:
    with cliente.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["usuario_escola_id"] = ESCOLA_ID
        sess["escola_id"] = ESCOLA_ID
        sess["escola_slug"] = SLUG
        carimbar_sessao(sess)


@pytest.fixture
def consultas_do_progresso(monkeypatch):
    consultas: list[str] = []

    def ranking(escola_id, limite=5):
        consultas.append(escola_id)
        return [dict(item) for item in RANKING]

    log = {"resultado": "Acertou", "materia": "Matematica", "modo": "treino", "pergunta_texto": "Quanto vale 2+2?"}
    monkeypatch.setattr(progresso_fla, "buscar_ranking", ranking)
    monkeypatch.setattr(progresso_fla, "buscar_logs", lambda escola_id, aluno_id=None: [dict(log)])
    monkeypatch.setattr(progresso_fla, "buscar_alunos", lambda escola_id: [])
    return consultas


@pytest.mark.parametrize("ranking", [True, False])
def test_meu_progresso_mostra_o_ranking_so_com_a_opcao_ligada(
    client, sem_rede_supabase, consultas_do_progresso, ranking
):
    _gravar_escola(sem_rede_supabase, ranking=ranking, guilda=True)
    _logar_aluno(client)

    resposta = client.get("/progresso/")
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert ("Ranking da escola" in html) is ranking
    assert ("Colega Campeao" in html) is ranking
    # desligado, a classificação nem é consultada
    assert consultas_do_progresso == ([ESCOLA_ID] if ranking else [])
    # o progresso do próprio aluno continua lá nos dois casos
    assert "Progresso do aluno" in html
    assert "Quanto vale 2+2?" in html


@pytest.mark.parametrize("ranking", [True, False])
def test_meu_progresso_nao_deixa_meia_tela_vazia_sem_o_ranking(
    client, sem_rede_supabase, consultas_do_progresso, ranking
):
    _gravar_escola(sem_rede_supabase, ranking=ranking, guilda=True)
    _logar_aluno(client)

    html = client.get("/progresso/").get_data(as_text=True)
    secao_do_progresso = html.split("<h2>Progresso do aluno</h2>")[0].rsplit("<section", 1)[1]

    assert ('class="grid two"' in secao_do_progresso) is ranking


def test_o_professor_desliga_e_o_aluno_ja_logado_deixa_de_ver(
    client, sem_rede_supabase, consultas_do_progresso
):
    """O caminho inteiro: o formulário de configurações do professor, e a
    PRÓXIMA tela do aluno que já estava logado -- sem sair e entrar de novo."""
    _gravar_escola(sem_rede_supabase, ranking=True, guilda=True)
    _logar_aluno(client)
    assert "Ranking da escola" in client.get("/progresso/").get_data(as_text=True)

    professor = client.application.test_client()
    _logar_professor(professor)
    # checkbox desmarcado não vai no formulário
    resposta = professor.post("/professor/configuracoes", data={"modo_guilda": "on"})
    assert resposta.status_code == 302

    html = client.get("/progresso/").get_data(as_text=True)
    assert "Ranking da escola" not in html
    assert "Colega Campeao" not in html


def test_com_o_ranking_desligado_o_aluno_mantem_a_pontuacao(client, sem_rede_supabase, monkeypatch):
    """RF14: esconder a classificação não apaga os pontos do aluno."""
    _gravar_escola(sem_rede_supabase, ranking=False, guilda=False)
    aluno = {"id": "aluno-1", "nome": "Aluno Teste", "ano_escolar": "1º EM", "pontos_totais": 120}
    monkeypatch.setattr(perfil_fla, "buscar_aluno_por_id", lambda aluno_id: dict(aluno))
    monkeypatch.setattr(perfil_fla, "buscar_logs", lambda escola_id, aluno_id=None: [])
    _logar_aluno(client)

    html = client.get("/perfil/").get_data(as_text=True)

    assert "Pontos" in html
    assert "<strong>120</strong>" in html


@pytest.fixture
def consultas_das_guildas(monkeypatch):
    consultas: list[str] = []

    def alunos(escola_id):
        consultas.append("alunos")
        return [dict(item) for item in ALUNOS_DAS_GUILDAS]

    def logs(escola_id, aluno_id=None):
        consultas.append("logs")
        return []

    monkeypatch.setattr(guildas_fla, "buscar_alunos", alunos)
    monkeypatch.setattr(guildas_fla, "buscar_logs", logs)
    monkeypatch.setattr(guildas_fla, "gerar_pdf_guildas", lambda nome, guildas: b"%PDF-falso")
    return consultas


@pytest.mark.parametrize("guilda", [True, False])
def test_tela_das_guildas_so_abre_com_modo_guilda(client, sem_rede_supabase, consultas_das_guildas, guilda):
    _gravar_escola(sem_rede_supabase, ranking=True, guilda=guilda)
    _logar_aluno(client)

    resposta = client.get("/guildas/")
    html = resposta.get_data(as_text=True)

    # 200 nos dois casos: quem chega por link antigo precisa ler o porquê
    assert resposta.status_code == 200
    assert ("Ranking por guilda" in html) is guilda
    assert ("Duelos ativos" in html) is guilda
    assert ("Batalha de Guildas desligada" in html) is (not guilda)
    assert (AVISO_GUILDAS_DESLIGADAS in html) is (not guilda)
    assert (consultas_das_guildas != []) is guilda


@pytest.mark.parametrize("guilda", [True, False])
def test_pdf_das_guildas_segue_a_mesma_tranca(client, sem_rede_supabase, consultas_das_guildas, guilda):
    """A URL do PDF é porta também: entregaria o placar inteiro."""
    _gravar_escola(sem_rede_supabase, ranking=True, guilda=guilda)
    _logar_aluno(client)

    resposta = client.get("/guildas/pdf")

    assert (resposta.mimetype == "application/pdf") is guilda
    if not guilda:
        assert AVISO_GUILDAS_DESLIGADAS in resposta.get_data(as_text=True)
        assert consultas_das_guildas == []


@pytest.mark.parametrize("guilda", [True, False])
def test_card_das_guildas_na_home_segue_modo_guilda(client, sem_rede_supabase, guilda):
    _gravar_escola(sem_rede_supabase, ranking=True, guilda=guilda)
    _logar_aluno(client)

    resposta = client.get("/")
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Meu Progresso" in html  # a home de aluno foi mesmo desenhada
    assert ("Batalha de Guildas" in html) is guilda
    assert ('href="/guildas/"' in html) is guilda


def test_sem_escola_no_banco_as_guildas_ficam_fechadas(client, sem_rede_supabase, consultas_das_guildas):
    _logar_aluno(client)

    html = client.get("/guildas/").get_data(as_text=True)

    assert "Batalha de Guildas desligada" in html
    assert consultas_das_guildas == []


# ====================== STREAMLIT ======================

MODULOS_DA_TELA = ("st.ui.home_st", "st.ui.tela_guildas_st")


def _reimportar_com_o_duble() -> None:
    for modulo in MODULOS_DA_TELA:
        sys.modules.pop(modulo, None)


def _streamlit_sem_corte(**kwargs) -> StreamlitFalso:
    """O dublê corta cada linha do roteiro em 90 caracteres, e o bloco de
    ranking da home só chega em "Top Heróis" depois de três <div>. Aqui o
    texto vai inteiro, para a asserção olhar o que a tela de fato escreveu."""
    fake = StreamlitFalso(**kwargs)
    fake._resumir = lambda valor, limite=90: " ".join(str(valor or "").split())
    return fake


def _rodar(fake: StreamlitFalso, acao) -> list[str]:
    with fake:
        _reimportar_com_o_duble()
        try:
            acao()
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:150]}")
    roteiro = fake.roteiro()
    assert not any(linha.startswith("!!") for linha in roteiro), roteiro
    return roteiro


def _home_st():
    return importlib.import_module("st.ui.home_st")


@pytest.mark.parametrize("guilda", [True, False])
def test_pagina_das_guildas_segue_a_escola_e_nao_o_papel(guilda):
    resultado = {}

    def acao():
        tela = _home_st()
        resultado["guildas"] = tela._pagina_permitida("🛡️ Guildas", _escola(True, guilda))
        resultado["jogar"] = tela._pagina_permitida("🎮 Jogar", _escola(True, guilda))
        resultado["sem_escola"] = tela._pagina_permitida("🛡️ Guildas")

    for papel in ("aluno", "professor", "desenvolvedor"):
        _rodar(StreamlitFalso(sessao={"usuario": {"id": "1", "role": papel}}), acao)
        assert resultado["guildas"] is guilda, papel
        assert resultado["jogar"] is True, papel
        assert resultado["sem_escola"] is False, papel


@pytest.mark.parametrize("guilda", [True, False])
def test_url_com_pagina_guildas_respeita_modo_guilda(guilda):
    resultado = {}
    fake = StreamlitFalso(sessao={"usuario": ALUNO}, parametros={"pagina": "guildas"})

    _rodar(fake, lambda: resultado.update(pagina=_home_st().renderizar_navegacao(_escola(True, guilda))))

    assert resultado["pagina"] == ("🛡️ Guildas" if guilda else "🏠 Início")


@pytest.mark.parametrize("guilda", [True, False])
def test_card_clicado_so_leva_as_guildas_com_modo_guilda(guilda):
    # _ir_para grava pagina_destino e pede rerun; a próxima execução decide
    resultado = {}
    fake = StreamlitFalso(sessao={"usuario": ALUNO, "pagina_destino": "🛡️ Guildas"})

    _rodar(fake, lambda: resultado.update(pagina=_home_st().renderizar_navegacao(_escola(True, guilda))))

    assert resultado["pagina"] == ("🛡️ Guildas" if guilda else "🏠 Início")


def test_quem_ja_estava_nas_guildas_volta_ao_inicio_quando_desligam():
    resultado = {}
    fake = StreamlitFalso(sessao={"usuario": ALUNO, "pagina_atual": "🛡️ Guildas"})

    _rodar(fake, lambda: resultado.update(pagina=_home_st().renderizar_navegacao(_escola(True, False))))

    assert resultado["pagina"] == "🏠 Início"


def _roteiro_da_home(monkeypatch, escola: dict) -> str:
    monkeypatch.setattr("services.dados_service.buscar_logs", lambda escola_id: [])
    fake = _streamlit_sem_corte(sessao={"usuario": ALUNO})
    roteiro = _rodar(fake, lambda: _home_st()._renderizar_dashboard(escola, RANKING, GUILDAS))
    return "\n".join(roteiro)


@pytest.mark.parametrize("ranking,guilda", COMBINACOES)
def test_home_do_streamlit_mostra_so_o_que_a_escola_ligou(monkeypatch, ranking, guilda):
    texto = _roteiro_da_home(monkeypatch, _escola(ranking, guilda))

    # os modos de estudo aparecem sempre
    assert "Treino Rápido" in texto
    assert "Meu Progresso" in texto
    # ranking individual
    assert ("Top Heróis" in texto) is ranking
    assert ("Colega Campeao" in texto) is ranking
    assert ("subir no ranking" in texto) is ranking
    # disputa entre turmas: o card do menu e o destaque
    assert ("button: 🛡️ **Batalha de Guildas**" in texto) is guilda
    assert ("Guilda em destaque" in texto) is guilda
    assert ("Guilda Vencedora" in texto) is guilda


@pytest.mark.parametrize(
    "ranking,guilda,titulo",
    [(True, True, "Ranking e guildas"), (True, False, "Ranking"), (False, True, "Guildas"), (False, False, None)],
)
def test_titulo_do_bloco_acompanha_o_que_sobrou(monkeypatch, ranking, guilda, titulo):
    texto = _roteiro_da_home(monkeypatch, _escola(ranking, guilda))
    titulos = [
        linha.split(">", 1)[1].split("<", 1)[0]
        for linha in texto.splitlines()
        if linha.startswith("markdown: <div class='edu-home-section-title'>")
    ]

    assert titulos == ([titulo] if titulo else [])


@pytest.mark.parametrize("ranking,guilda", COMBINACOES)
def test_bloco_de_ranking_nao_deixa_buraco_no_grid(ranking, guilda):
    # função pura: não fala com o Streamlit, dublê nenhum é preciso
    html = _home_st()._ranking_home_html(RANKING, GUILDAS, mostrar_ranking=ranking, mostrar_guildas=guilda)

    if not (ranking or guilda):
        assert html == ""
        return
    assert html.count("edu-ranking-card") == int(ranking) + int(guilda)
    assert ("grid-template-columns:1fr" in html) is (ranking != guilda)


class _RepoDasGuildas:
    def __init__(self):
        self.consultas: list[str] = []

    def buscar_alunos(self, _escola):
        self.consultas.append("alunos")
        return [dict(item) for item in ALUNOS_DAS_GUILDAS]

    def buscar_logs(self, _escola):
        self.consultas.append("logs")
        return []


@pytest.mark.parametrize("guilda", [True, False])
def test_tela_das_guildas_do_streamlit_tem_a_propria_tranca(guilda):
    repo = _RepoDasGuildas()
    fake = _streamlit_sem_corte()

    def acao():
        tela = importlib.import_module("st.ui.tela_guildas_st")
        tela.renderizar_tela_guildas(ESCOLA_ID, repo, _escola(True, guilda))

    texto = "\n".join(_rodar(fake, acao))

    assert ("Lider semanal" in texto) is guilda
    assert ("Ranking por guilda" in texto) is guilda
    assert (f"info: {AVISO_GUILDAS_DESLIGADAS}" in texto) is (not guilda)
    # desligada, a turma nem é lida
    assert (repo.consultas != []) is guilda


# ------------------------------------------------ o app.py de ponta a ponta


def _executar_app(monkeypatch, fake: StreamlitFalso, **run_path_kwargs) -> list[str]:
    """runpy.run_path("app.py") com o dublê também nos módulos que não são purgados.

    O app.py chama o CSS global (core/design_system_global.py) e o cabeçalho
    dos modos (st/ui/mode_common_st.py). Os dois guardaram o streamlit de
    verdade no import, e ele, com o dublê em sys.modules, quebra ao procurar
    `streamlit.config`. Purgá-los trocaria o objeto que outros testes já têm
    em mãos (a armadilha descrita em tests/test_adm_streamlit_por_papel.py);
    o monkeypatch troca só o `st` deles, e desfaz no fim do teste.
    """
    import core.design_system_global
    import st.ui.mode_common_st

    def acao():
        for modulo in (core.design_system_global, sys.modules["st.ui.mode_common_st"]):
            monkeypatch.setattr(modulo, "st", sys.modules["streamlit"])
        runpy.run_path(str(RAIZ / "app.py"), **run_path_kwargs)

    return _rodar(fake, acao)


def _rodar_app(monkeypatch, *, no_banco: dict, no_login: dict, pagina: str) -> tuple[str, list[str]]:
    """Executa o app.py inteiro com o dublê, como `streamlit run` faria.

    A escola do LOGIN e a do BANCO vêm diferentes de propósito: é assim que
    se prova que o app lê a opção atual, e não a guardada quando o aluno
    entrou.
    """
    consultas: list[str] = []

    def anotar(nome, valor):
        def buscar(*_args, **_kwargs):
            consultas.append(nome)
            return [dict(item) for item in valor]
        return buscar

    monkeypatch.setattr(escola_service, "buscar_escola_por_id", lambda escola_id: dict(no_banco))
    monkeypatch.setattr("services.dados_service.buscar_ranking", anotar("ranking", RANKING))
    monkeypatch.setattr("services.dados_service.buscar_ranking_guildas", anotar("ranking_guildas", GUILDAS))
    monkeypatch.setattr("services.dados_service.buscar_alunos", anotar("alunos", ALUNOS_DAS_GUILDAS))
    monkeypatch.setattr("services.dados_service.buscar_logs", anotar("logs", []))

    sessao = {
        "usuario": dict(ALUNO),
        "escola": dict(no_login),
        "config_verificada": True,
        "user_tz": "America/Sao_Paulo",
        "pagina_atual": pagina,
    }
    roteiro = _executar_app(monkeypatch, _streamlit_sem_corte(sessao=sessao), run_name="app_rf14")
    return "\n".join(roteiro), consultas


@pytest.mark.parametrize("ranking,guilda", COMBINACOES)
def test_app_streamlit_usa_as_opcoes_do_banco_na_home(monkeypatch, ranking, guilda):
    # login com tudo ao contrário do banco
    texto, consultas = _rodar_app(
        monkeypatch,
        no_banco=_escola(ranking, guilda),
        no_login=_escola(not ranking, not guilda),
        pagina="🏠 Início",
    )

    assert ("Top Heróis" in texto) is ranking
    assert ("Batalha de Guildas" in texto) is guilda
    assert ("Guilda em destaque" in texto) is guilda
    # desligada, a classificação nem é consultada
    assert ("ranking" in consultas) is ranking
    assert ("ranking_guildas" in consultas) is guilda


@pytest.mark.parametrize("guilda", [True, False])
def test_app_streamlit_so_abre_a_pagina_das_guildas_com_modo_guilda(monkeypatch, guilda):
    texto, consultas = _rodar_app(
        monkeypatch,
        no_banco=_escola(True, guilda),
        no_login=_escola(True, not guilda),
        pagina="🛡️ Guildas",
    )

    # ligada: a tela monta o placar; desligada: a navegação volta ao início
    assert ("Lider semanal" in texto) is guilda
    assert ("alunos" in consultas) is guilda
    assert ("Top Heróis" in texto) is (not guilda)


def test_app_streamlit_usa_a_escola_do_login_se_o_banco_nao_responder(monkeypatch):
    monkeypatch.setattr(escola_service, "buscar_escola_por_id", lambda escola_id: None)
    monkeypatch.setattr("services.dados_service.buscar_ranking", lambda *_a, **_k: [dict(RANKING[0])])
    monkeypatch.setattr("services.dados_service.buscar_ranking_guildas", lambda *_a, **_k: [])
    monkeypatch.setattr("services.dados_service.buscar_logs", lambda *_a, **_k: [])
    sessao = {
        "usuario": dict(ALUNO),
        "escola": _escola(ranking=False, guilda=False),
        "config_verificada": True,
        "user_tz": "America/Sao_Paulo",
        "pagina_atual": "🏠 Início",
    }

    texto = "\n".join(_executar_app(monkeypatch, _streamlit_sem_corte(sessao=sessao)))

    assert "Treino Rápido" in texto
    assert "Top Heróis" not in texto
    assert "Batalha de Guildas" not in texto
