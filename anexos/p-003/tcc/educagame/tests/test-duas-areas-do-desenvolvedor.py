"""Quem entra como desenvolvedor cai no lugar de desenvolvedor.

O que estava errado
-------------------
Entrar com a conta `desenvolvedor` devolvia a **área do aluno**: a vitrine de
modos (Treino, ENEM, Oráculo, Laboratório, RPG, Escape Room). O ADM existia,
mas como **sétima aba do painel do professor** -- uma área de um papel
escondida dentro da área de outro.

Os dois frontends erravam de jeitos diferentes, o que é pior que errarem
igual:

- **Streamlit:** a home era a mesma para todo mundo (`_renderizar_dashboard`
  só checava `_eh_aluno`), então o desenvolvedor via a grade de jogos.
- **Flask:** `home_fla.index` já mandava professor e desenvolvedor direto para
  o painel de gestão -- mas os dois para o *mesmo* painel, com o ADM
  pendurado no fim da tira de abas.

Agora são duas áreas explícitas nos dois: **Professor** e **ADM**. E a área de
Professor ganhou o que faltava para acompanhar de verdade -- quem são os
professores cadastrados e em que escola cada um entra.

A regra de alcance
------------------
Ela mora em `services/usuario_service.py`, e não em cada tela, porque são duas
telas e é a mesma pergunta que `conta_pode_entrar` responde no login.

Errar para o lado frouxo aqui entrega a lista de contas de uma escola ao
professor da outra -- o mesmo defeito que a migração
20260831120000_usuarios_escola.sql veio consertar no login.
"""

from __future__ import annotations

import pytest

import services.usuario_service as contas_svc
from web.routes import professor_fla

from tests.apoio_flask import carimbar_sessao

ESCOLAS = [
    {"id": "esc-1", "nome": "ETEC", "slug": "etec"},
    {"id": "esc-2", "nome": "Delta", "slug": "delta"},
]

USUARIOS = [
    {"id": "u1", "username": "dev", "role": "desenvolvedor", "ativo": True, "escola_id": None},
    {"id": "u2", "username": "profetec", "role": "professor", "ativo": True, "escola_id": "esc-1"},
    {"id": "u3", "username": "profdelta", "role": "professor", "ativo": True, "escola_id": "esc-2"},
    {"id": "u4", "username": "profsolto", "role": "professor", "ativo": True, "escola_id": None},
    {"id": "u5", "username": "aluno", "role": "aluno", "ativo": True, "escola_id": "esc-1"},
]


@pytest.fixture
def contas_falsas(monkeypatch):
    monkeypatch.setattr(contas_svc, "listar_usuarios", lambda: [dict(u) for u in USUARIOS])
    monkeypatch.setattr(contas_svc, "listar_escolas", lambda: [dict(e) for e in ESCOLAS])


# ====================== A REGRA DE ALCANCE ======================


def test_desenvolvedor_ve_os_professores_de_todas_as_escolas(contas_falsas):
    vistos = contas_svc.listar_professores_visiveis({"role": "desenvolvedor", "escola_id": None})

    assert sorted(c["username"] for c in vistos) == ["profdelta", "profetec", "profsolto"]


def test_professor_ve_so_a_propria_escola(contas_falsas):
    vistos = contas_svc.listar_professores_visiveis({"role": "professor", "escola_id": "esc-1"})

    assert [c["username"] for c in vistos] == ["profetec"]


def test_professor_da_outra_escola_ve_a_dele(contas_falsas):
    """O par do teste acima. Sem ele, uma implementação que devolvesse sempre
    a esc-1 passaria."""
    vistos = contas_svc.listar_professores_visiveis({"role": "professor", "escola_id": "esc-2"})

    assert [c["username"] for c in vistos] == ["profdelta"]


def test_professor_sem_vinculo_nao_ve_ninguem(contas_falsas):
    """"Sem escola" era exatamente o estado que abria TODAS as escolas no
    login, antes da 20260831120000. Tratar como "pode tudo" aqui seria repetir
    o furo com outro nome."""
    assert contas_svc.listar_professores_visiveis({"role": "professor", "escola_id": None}) == []
    assert contas_svc.listar_professores_visiveis({"role": "professor", "escola_id": ""}) == []


@pytest.mark.parametrize(
    "usuario",
    [None, {}, "desenvolvedor", {"role": "aluno", "escola_id": "esc-1"}, {"role": ""}],
    ids=["none", "vazio", "string", "aluno", "sem-papel"],
)
def test_quem_nao_e_professor_nem_desenvolvedor_ve_nada(contas_falsas, usuario):
    assert contas_svc.listar_professores_visiveis(usuario) == []


def test_a_lista_traz_so_professor_e_nao_o_resto_das_contas(contas_falsas):
    vistos = contas_svc.listar_professores_visiveis({"role": "desenvolvedor"})

    papeis = {c["role"] for c in vistos}
    assert papeis == {"professor"}, f"vazou conta de outro papel: {papeis}"


def test_o_agrupamento_poe_quem_nao_entra_por_ultimo(contas_falsas):
    """Professor sem escola NÃO ENTRA em lugar nenhum. Perdido no meio de uma
    lista alfabética ele passa despercebido; no fim, com nome próprio, não."""
    grupos = contas_svc.agrupar_professores_por_escola(
        contas_svc.listar_professores_visiveis({"role": "desenvolvedor"})
    )

    nomes = [nome for nome, _ in grupos]
    assert nomes == ["Delta", "ETEC", contas_svc.SEM_ESCOLA], nomes
    assert [c["username"] for c in grupos[-1][1]] == ["profsolto"]


def test_o_agrupamento_marca_quem_nao_entra(contas_falsas):
    grupos = dict(
        contas_svc.agrupar_professores_por_escola(
            contas_svc.listar_professores_visiveis({"role": "desenvolvedor"})
        )
    )

    assert grupos[contas_svc.SEM_ESCOLA][0]["sem_vinculo"] is True
    assert grupos["ETEC"][0]["sem_vinculo"] is False


# ====================== O FLASK ======================


def _sem_rede(monkeypatch):
    monkeypatch.setattr(professor_fla, "buscar_alunos", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "buscar_logs", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "buscar_resumo_turma", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "listar_rpg_configs", lambda escola_id: [])
    monkeypatch.setattr(professor_fla, "listar_escolas", lambda: [dict(e) for e in ESCOLAS])
    monkeypatch.setattr(professor_fla, "listar_contas", lambda: [])
    monkeypatch.setattr(
        professor_fla,
        "listar_professores_visiveis",
        lambda usuario: contas_svc.listar_professores_visiveis(usuario),
    )


def _entrar(client, papel: str, escola_id: str = "esc-1"):
    with client.session_transaction() as sess:
        sess["usuario_role"] = papel
        sess["escola_id"] = escola_id
        sess["escola_nome"] = "ETEC"
        carimbar_sessao(sess)


def test_o_desenvolvedor_cai_nas_duas_areas(client, monkeypatch, contas_falsas):
    _sem_rede(monkeypatch)
    _entrar(client, "desenvolvedor")

    corpo = client.get("/professor/").get_data(as_text=True)

    assert "Professor" in corpo
    assert "ADM" in corpo
    # A prova de que é a home de DUAS áreas, e não o hub de professor: as
    # abas de dar aula não estão nesta tela.
    for aba in ("Análises", "Matrícula", "Resumo da Turma"):
        assert aba not in corpo, f"o hub do desenvolvedor ainda mostra '{aba}'"


def test_o_professor_continua_caindo_no_hub_de_sempre(client, monkeypatch, contas_falsas):
    """Separar as áreas do desenvolvedor não pode mexer no caminho do
    professor."""
    _sem_rede(monkeypatch)
    _entrar(client, "professor")

    corpo = client.get("/professor/").get_data(as_text=True)

    for aba in ("Análises", "Matrícula", "Resumo da Turma", "Ranking"):
        assert aba in corpo, f"a aba '{aba}' sumiu do hub do professor"
    assert "ADM" not in corpo


def test_do_hub_do_desenvolvedor_da_para_chegar_na_gestao(client, monkeypatch, contas_falsas):
    _sem_rede(monkeypatch)
    _entrar(client, "desenvolvedor")

    corpo = client.get("/professor/?area=gestao").get_data(as_text=True)

    for aba in ("Análises", "Matrícula", "Resumo da Turma"):
        assert aba in corpo, f"a aba '{aba}' nao aparece na area de gestao"


def test_professor_digitando_aba_adm_na_url_nao_entra(client, monkeypatch, contas_falsas):
    """O ADM saiu da tira de abas, mas a URL continua sendo porta."""
    _sem_rede(monkeypatch)
    _entrar(client, "professor")

    corpo = client.get("/professor/?aba=adm").get_data(as_text=True)

    assert "Painel do Desenvolvedor" not in corpo
    assert "Cadastrar Nova Escola" not in corpo
    assert "Contas de login" not in corpo


def test_desenvolvedor_alcanca_a_aba_adm(client, monkeypatch, contas_falsas):
    """O par do teste acima: barrar o professor não pode barrar o dono."""
    _sem_rede(monkeypatch)
    _entrar(client, "desenvolvedor")

    corpo = client.get("/professor/?aba=adm").get_data(as_text=True)

    assert "Cadastrar" in corpo or "Contas de login" in corpo, "o desenvolvedor perdeu o ADM"


# ====================== A ABA DE PROFESSORES, NO FLASK ======================


def test_a_aba_de_professores_mostra_todas_as_escolas_para_o_desenvolvedor(
    client, monkeypatch, contas_falsas
):
    _sem_rede(monkeypatch)
    _entrar(client, "desenvolvedor")

    corpo = client.get("/professor/?aba=professores").get_data(as_text=True)

    for username in ("profetec", "profdelta", "profsolto"):
        assert username in corpo, f"{username} nao aparece para o desenvolvedor"
    assert "ETEC" in corpo and "Delta" in corpo


def test_a_aba_de_professores_nao_vaza_a_outra_escola_para_o_professor(
    client, monkeypatch, contas_falsas
):
    """O defeito que a regra existe para impedir."""
    _sem_rede(monkeypatch)
    _entrar(client, "professor", escola_id="esc-1")

    corpo = client.get("/professor/?aba=professores").get_data(as_text=True)

    assert "profetec" in corpo, "o professor nao ve nem a propria escola"
    assert "profdelta" not in corpo, "vazou o professor da outra escola"
    assert "profsolto" not in corpo, "vazou a conta sem vinculo"


def test_a_aba_avisa_quando_ha_professor_que_nao_entra(client, monkeypatch, contas_falsas):
    _sem_rede(monkeypatch)
    _entrar(client, "desenvolvedor")

    corpo = client.get("/professor/?aba=professores").get_data(as_text=True)

    assert "não conseguem entrar" in corpo, "o aviso de conta sem escola sumiu"


def test_fora_da_aba_de_professores_ninguem_e_buscado(client, monkeypatch, contas_falsas):
    """Cada leitura é uma ida à rede -- até o cache mora no Supabase."""
    _sem_rede(monkeypatch)
    chamadas = []
    monkeypatch.setattr(
        professor_fla,
        "listar_professores_visiveis",
        lambda usuario: chamadas.append(usuario) or [],
    )
    _entrar(client, "desenvolvedor")

    client.get("/professor/?aba=analises")
    assert chamadas == [], "buscou professores numa aba que nao mostra professores"

    client.get("/professor/?aba=professores")
    assert len(chamadas) == 1, "a aba de professores parou de buscar"


# ====================== ENTRADA GLOBAL NO FLASK ======================
#
# O desenvolvedor tinha de escolher uma unidade e digitar o CÓDIGO dela para
# só então chegar ao ADM -- a chave de uma casa para entrar em outra. A conta
# dele não pertence a escola nenhuma: `conta_pode_entrar` devolve True sem
# sequer olhar a escola.
#
# Pior no caso que mais importa: para cadastrar a PRIMEIRA escola era preciso
# digitar o código de uma escola que ainda não existe.
#
# O código continua obrigatório para todo mundo. Ele é o combinado que o
# professor passa à turma; quem administra já lê todos eles na tela de ADM.


def _sem_rede_home(monkeypatch):
    from web.routes import home_fla

    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [dict(e) for e in ESCOLAS])
    monkeypatch.setattr(
        home_fla,
        "buscar_escola_por_slug",
        lambda slug: next((dict(e) for e in ESCOLAS if e["slug"] == slug), None),
    )


def _logar_sem_escola(client, papel: str):
    with client.session_transaction() as sess:
        sess["usuario_role"] = papel
        carimbar_sessao(sess)


def test_desenvolvedor_sem_escola_vai_para_o_painel_global(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)
    _logar_sem_escola(client, "desenvolvedor")

    resposta = client.get("/")

    assert resposta.status_code == 302
    assert "/professor" in resposta.headers["Location"], resposta.headers["Location"]


def test_professor_sem_escola_continua_escolhendo_escola(client, monkeypatch, contas_falsas):
    """O par. Ser global é da conta de desenvolvedor, não de quem administra
    uma turma: professor pertence a UMA escola."""
    _sem_rede_home(monkeypatch)
    _logar_sem_escola(client, "professor")

    corpo = client.get("/").get_data(as_text=True)

    assert "Escolha sua escola" in corpo


def test_aluno_sem_escola_continua_escolhendo_escola(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)
    _logar_sem_escola(client, "aluno")

    corpo = client.get("/").get_data(as_text=True)

    assert "Escolha sua escola" in corpo


def test_desenvolvedor_abre_a_escola_sem_digitar_o_codigo(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)
    _logar_sem_escola(client, "desenvolvedor")

    resposta = client.get("/entrar-escola/esc-2")

    assert resposta.status_code == 302, "ainda pediu o codigo ao desenvolvedor"
    with client.session_transaction() as sess:
        assert sess.get("escola_id") == "esc-2"
        assert sess.get("escola_slug") == "delta"
        assert sess.get("escola_nome") == "Delta"


@pytest.mark.parametrize("papel", ["professor", "aluno", None])
def test_quem_nao_e_desenvolvedor_continua_digitando_o_codigo(
    client, monkeypatch, contas_falsas, papel
):
    """O par que importa. Abrir a porta para o desenvolvedor não pode abri-la
    para os outros -- num aparelho compartilhado a escola do colega ficaria a
    um clique, que é exatamente o defeito que o código veio consertar."""
    _sem_rede_home(monkeypatch)
    if papel:
        _logar_sem_escola(client, papel)

    resposta = client.get("/entrar-escola/esc-2")

    assert resposta.status_code == 200, f"{papel} entrou sem o codigo"
    assert "Código da escola" in resposta.get_data(as_text=True) or "código" in resposta.get_data(as_text=True).lower()
    with client.session_transaction() as sess:
        assert not sess.get("escola_id"), f"{papel} entrou na escola sem digitar nada"


def test_a_lista_de_escolas_oferece_a_entrada_do_desenvolvedor(client, monkeypatch, contas_falsas):
    """Sem esta porta, a única forma de chegar ao ADM era escolher uma unidade
    qualquer e digitar o código dela."""
    _sem_rede_home(monkeypatch)

    corpo = client.get("/").get_data(as_text=True)

    assert "sem escolher escola" in corpo
    assert "adm=1" in corpo, "o link nao abre o formulario do ADM"


def test_o_formulario_do_adm_fica_atras_de_um_clique(client, monkeypatch, contas_falsas):
    """Quem chega nesta tela é aluno. Um par usuário/senha aberto no meio da
    entrada convida a turma a tentar."""
    _sem_rede_home(monkeypatch)

    fechado = client.get("/").get_data(as_text=True)
    aberto = client.get("/?adm=1").get_data(as_text=True)

    assert 'name="senha"' not in fechado, "o formulario do ADM nasce aberto"
    assert 'name="senha"' in aberto, "o formulario do ADM nao abre com ?adm=1"
    assert 'name="username"' in aberto


def test_o_formulario_do_adm_tem_csrf(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)

    corpo = client.get("/?adm=1").get_data(as_text=True)

    assert 'name="csrf_token"' in corpo


def test_com_o_formulario_aberto_a_tela_nao_se_redireciona_sozinha(client, monkeypatch, contas_falsas):
    """Com UMA escola cadastrada a tela redireciona sozinha depois de 2,85 s.
    Isso arrancaria a pessoa do formulário no meio da digitação."""
    from web.routes import home_fla

    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [dict(ESCOLAS[0])])

    corpo = client.get("/?adm=1").get_data(as_text=True)

    # `window.location.href`, e não `setTimeout`: o indicador de carregamento
    # do base.html também usa setTimeout, então procurá-lo aqui acusaria um
    # redirect que não existe. É a mesma armadilha que
    # tests/test_tela_selecionar_escola.py já documenta.
    assert "window.location.href" not in corpo, "o redirecionamento automatico continua armado"


def test_e_sem_o_formulario_o_redirecionamento_continua(client, monkeypatch, contas_falsas):
    """O par: desarmar o redirect para o formulário não pode desarmá-lo para
    o aluno, que é quem ganha o clique poupado."""
    from web.routes import home_fla

    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [dict(ESCOLAS[0])])

    corpo = client.get("/").get_data(as_text=True)

    assert "window.location.href" in corpo


def test_abrir_escola_e_so_do_desenvolvedor(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)

    for papel in ("professor", "aluno"):
        _logar_sem_escola(client, papel)
        resposta = client.get("/abrir-escola")
        assert resposta.status_code == 302, f"{papel} alcancou /abrir-escola"


def test_o_desenvolvedor_escolhe_a_unidade_em_abrir_escola(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)
    _logar_sem_escola(client, "desenvolvedor")

    corpo = client.get("/abrir-escola").get_data(as_text=True)

    assert "Qual escola você quer acompanhar?" in corpo
    for escola in ESCOLAS:
        assert escola["nome"] in corpo


def test_o_card_professor_leva_a_escolher_escola_quando_nao_ha_nenhuma(
    client, monkeypatch, contas_falsas
):
    _sem_rede(monkeypatch)
    _logar_sem_escola(client, "desenvolvedor")

    corpo = client.get("/professor/").get_data(as_text=True)

    assert "/abrir-escola" in corpo, "o card Professor nao leva a escolher escola"


def test_a_gestao_sem_escola_manda_escolher_em_vez_de_abrir_vazia(
    client, monkeypatch, contas_falsas
):
    """Sem turma, as abas de gestão renderizariam vazias sem dizer por quê."""
    _sem_rede(monkeypatch)
    _logar_sem_escola(client, "desenvolvedor")

    resposta = client.get("/professor/?area=gestao")

    assert resposta.status_code == 302
    assert "/abrir-escola" in resposta.headers["Location"]


def test_mas_o_adm_abre_sem_escola_nenhuma(client, monkeypatch, contas_falsas):
    """É onde se cadastra a PRIMEIRA escola: exigir uma escola aberta aqui
    seria pedir o que ainda não existe."""
    _sem_rede(monkeypatch)
    _logar_sem_escola(client, "desenvolvedor")

    resposta = client.get("/professor/?aba=adm")

    assert resposta.status_code == 200, "o ADM passou a exigir escola aberta"
    assert "Cadastrar" in resposta.get_data(as_text=True)


# ====================== A PORTA DO ADM, NO FLASK ======================
#
# O mesmo formulário que o Streamlit tem na tela inicial. Antes era um link
# para o /login de sempre: funcionava, mas a recusa aparecia noutra tela e a
# mensagem não distinguia "senha errada" de "não é desenvolvedor".


def _entrar_no_adm(client, monkeypatch, conta, explode=False):
    from web.routes import auth_fla

    if explode:
        def _autenticar(*_a, **_k):
            raise RuntimeError("conexao recusada")
    else:
        def _autenticar(*_a, **_k):
            return conta

    monkeypatch.setattr(auth_fla, "autenticar", _autenticar)
    monkeypatch.setattr(auth_fla, "listar_escolas", lambda: [dict(e) for e in ESCOLAS])
    return client.post("/adm/entrar", data={"username": "dev", "senha": "x"})


DEV = {"id": "u1", "username": "dev", "role": "desenvolvedor", "escola_id": None}


def test_a_conta_de_desenvolvedor_entra_pela_porta_do_adm(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)
    resposta = _entrar_no_adm(client, monkeypatch, DEV)

    assert resposta.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get("usuario_role") == "desenvolvedor"
        # Sem escola: é a entrada GLOBAL.
        assert not sess.get("escola_id")
        from core.sessao import CHAVE_INICIO, CHAVE_VISTO

        assert sess.get(CHAVE_INICIO), dict(sess)
        assert sess.get(CHAVE_VISTO), dict(sess)


def test_a_porta_do_adm_zera_o_relogio_da_sessao(client, monkeypatch, contas_falsas):
    """Só existir carimbo não prova nada: o `after_request` de flask_app.py
    carimba qualquer sessão nova. O que `marcar_login` faz é ZERAR os dois
    relógios -- sem isso, quem ficou meia hora na tela de escolher escola
    entra com a vida máxima já meio gasta e é derrubado no meio do trabalho.

    Este teste começou vazio: ele afirmava só que o carimbo existia, e o
    mutante que apagava `marcar_login` passava."""
    import time as _time

    from core.sessao import CHAVE_INICIO, CHAVE_VISTO

    _sem_rede_home(monkeypatch)
    antigo = _time.time() - 3600
    with client.session_transaction() as sess:
        sess[CHAVE_INICIO] = antigo
        sess[CHAVE_VISTO] = antigo

    _entrar_no_adm(client, monkeypatch, DEV)

    with client.session_transaction() as sess:
        assert sess[CHAVE_INICIO] > antigo + 60, "o relogio de vida maxima nao foi zerado"
        assert sess[CHAVE_VISTO] > antigo + 60, "o relogio de inatividade nao foi zerado"


@pytest.mark.parametrize(
    "conta",
    [
        None,
        {"id": "u2", "username": "prof", "role": "professor", "escola_id": "esc-1"},
        {"id": "u5", "username": "aluno", "role": "aluno", "escola_id": "esc-1"},
        {"id": "u9", "username": "x", "role": ""},
    ],
    ids=["senha-errada", "professor", "aluno", "sem-papel"],
)
def test_quem_nao_e_desenvolvedor_nao_passa_pela_porta_do_adm(
    client, monkeypatch, contas_falsas, conta
):
    """Esta porta é anterior a QUALQUER escolha de escola. Um professor que
    entrasse por aqui entraria sem unidade nenhuma -- exatamente o estado que
    conta_pode_entrar recusa."""
    _sem_rede_home(monkeypatch)
    resposta = _entrar_no_adm(client, monkeypatch, conta)

    assert resposta.status_code == 200, f"{conta} foi redirecionado para dentro"
    with client.session_transaction() as sess:
        assert not sess.get("usuario_role"), f"{conta} entrou no ADM"


def test_a_recusa_aparece_na_propria_tela_inicial(client, monkeypatch, contas_falsas):
    _sem_rede_home(monkeypatch)
    corpo = _entrar_no_adm(client, monkeypatch, None).get_data(as_text=True)

    from services.auth_service import MOTIVO_ADM_RECUSADO

    assert MOTIVO_ADM_RECUSADO in corpo
    # E com o formulário ainda aberto, para tentar de novo sem outro clique.
    assert 'name="senha"' in corpo


def test_a_recusa_nao_conta_qual_dos_dois_estava_errado_no_flask():
    """A mesma frase para senha errada e para conta que não é de
    desenvolvedor. Dizer "esse usuário não existe" conta a quem tenta que o
    OUTRO nome existe."""
    from services.auth_service import MOTIVO_ADM_RECUSADO

    motivo = MOTIVO_ADM_RECUSADO.lower()
    for palavra in ("não existe", "nao existe", "inexistente", "senha incorreta"):
        assert palavra not in motivo, f"a recusa entrega demais: {motivo!r}"


def test_os_dois_frontends_recusam_com_a_MESMA_frase():
    """Duas cópias divergem na primeira vez que alguém reescreve uma só."""
    import importlib

    from services.auth_service import MOTIVO_ADM_RECUSADO

    home_st = importlib.import_module("st.ui.home_st")
    assert home_st.MOTIVO_ADM_RECUSADO == MOTIVO_ADM_RECUSADO


def test_supabase_fora_do_ar_nao_vira_senha_errada_no_flask(client, monkeypatch, contas_falsas):
    """Sem isto a pessoa passa a tarde tentando lembrar a senha certa."""
    _sem_rede_home(monkeypatch)
    corpo = _entrar_no_adm(client, monkeypatch, None, explode=True).get_data(as_text=True)

    assert "conexao recusada" in corpo
    with client.session_transaction() as sess:
        assert not sess.get("usuario_role")


def test_a_porta_do_adm_tem_o_mesmo_limite_do_login():
    """Sem limite, esta rota seria um desvio em volta da tranca do login:
    quem quisesse tentar senhas em série usaria a porta sem contador."""
    from flask_app import app

    limites = {}
    for regra in app.url_map.iter_rules():
        if regra.endpoint in ("auth.tela_login", "auth.entrar_como_desenvolvedor"):
            funcao = app.view_functions[regra.endpoint]
            marcas = getattr(funcao, "_rate_limits", None) or getattr(
                funcao, "__wrapped__", funcao
            )
            limites[regra.endpoint] = marcas

    assert "auth.entrar_como_desenvolvedor" in limites, "a rota do ADM sumiu"

    # O limitador guarda as marcas por nome de funcao; comparar o texto do
    # decorador direto no fonte e o que sobrevive a versao da biblioteca.
    import inspect

    from web.routes import auth_fla

    fonte = inspect.getsource(auth_fla)
    trecho_adm = fonte[fonte.index("def entrar_como_desenvolvedor") - 400 : fonte.index("def entrar_como_desenvolvedor")]
    assert 'limiter.limit("20 per hour")' in trecho_adm, "a porta do ADM perdeu o limite de tentativas"
