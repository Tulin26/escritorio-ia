"""O ADM do Streamlit: uma porta só, e ela é usuário e senha.

O que este arquivo cobria antes
-------------------------------
Duas coisas erradas, uma escondendo a outra: o painel **pedia demais** de quem
já tinha entrado (o desenvolvedor logado ainda digitava a Chave Mestra) e
**protegia de menos** (a aba ADM era desenhada para todo mundo que chegasse ao
painel do professor, e só a Chave Mestra o separava do ADM).

A correção de então tirou a chave de quem entrava pelo papel e fez a aba
existir só para desenvolvedor. Mas ela **manteve a Chave Mestra** como porta
de quem não é desenvolvedor, com este argumento escrito:

    "A chave continua valendo onde ainda faz sentido: a tela de escolher
    escola oferece o ADM ANTES de qualquer login... Lá não existe usuário
    para consultar, então a chave é a única porta."

O argumento estava errado
-------------------------
A conta de desenvolvedor é **global**: `conta_pode_entrar` devolve True para
ela sem sequer olhar a escola. Ou seja, sempre deu para autenticar antes de
escolher unidade — não havia nada a consultar *sobre a escola*, mas a conta
estava lá o tempo todo.

Enquanto a chave existisse, ela era a porta mais fraca da casa, e é a porta
mais fraca que define a tranca: não adianta exigir o papel em
`_pagina_permitida` e de novo em `app.py` se uma senha combinada entre
pessoas abre do mesmo jeito.

Hoje são três mudanças que andam juntas:

1. A tela inicial pede **usuário e senha** de desenvolvedor, não a chave.
2. O ADM virou **página** (`🏛️ ADM`), com tranca em `_pagina_permitida` e a
   segunda em `app.py`. Ele era a sétima aba de um painel de *professor* —
   uma área de desenvolvedor escondida dentro da área de outro papel.
3. `_portao_do_painel` não tem mais senha nenhuma: ou o papel é
   desenvolvedor, ou `st.stop()`.

A reserva, se ninguém souber a senha do desenvolvedor, é
`scripts/seed_usuarios.py` (upsert da conta). Ela exige a chave do Supabase,
e não uma senha combinada por mensagem — é uma porta mais estreita de
propósito.
"""

from __future__ import annotations

import importlib
import sys

import pytest

from tests.apoio_streamlit import StreamlitFalso

# Importado AQUI, fora do dublê, de propósito. A tela puxa uma cadeia de
# services/repositories, e repositories/aluno_repo.py resolve
# `runtime = get_runtime()` no import -- com o dublê instalado ele pegaria o
# streamlit falso, que não tem cache_data, e o teste quebraria por causa da
# bancada. Importando antes, a cadeia fica presa ao runtime de verdade e a
# purga lá dentro só reexecuta a camada st.ui.
import st.ui.admin_st  # noqa: E402,F401
import st.ui.home_st  # noqa: E402,F401
import st.ui.professor_panel_st  # noqa: E402,F401

# So os modulos que precisam reexecutar "import streamlit as st" para pegar o
# duble. Purgar "st.ui*" inteiro -- como este arquivo fazia --
# derrubava um teste vizinho: tests/test_tela_guildas.py importa
# _montar_guildas no topo e depois faz monkeypatch por CAMINHO
# ("st.ui.tela_guildas_st._inicio_semana"). Com o modulo purgado, o caminho
# reimporta um objeto NOVO e o patch passa a nao alcancar a funcao que o teste
# ja tinha em maos. Verde sozinho, vermelho na suite -- a mesma armadilha de
# ordem de import que este projeto ja documentou.
MODULOS_DA_TELA = (
    "st.ui.admin_st",
    "st.ui.home_st",
    "st.ui.professor_panel_st",
)

DEV = {"id": "1", "username": "dev", "role": "desenvolvedor"}


def _reimportar_com_o_duble() -> None:
    for modulo in MODULOS_DA_TELA:
        sys.modules.pop(modulo, None)


def _rodar_adm(sessao: dict) -> list[str]:
    with StreamlitFalso(sessao=dict(sessao)) as fake:
        _reimportar_com_o_duble()
        tela = importlib.import_module("st.ui.admin_st")
        try:
            tela.tela_administrador()
        except Exception as erro:  # noqa: BLE001
            # depois do portão a tela fala com o Supabase; o que esta secao
            # mede é o portão, então o resto pode falhar sem atrapalhar
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:120]}")
    return fake.roteiro()


def _abriu_o_painel(roteiro: list[str]) -> bool:
    return any("Modo Desenvolvedor Ativo" in linha for linha in roteiro)


def _pediu_senha(roteiro: list[str]) -> bool:
    """Campo de senha NO PORTÃO -- antes de o painel abrir.

    Só o trecho anterior a "Modo Desenvolvedor Ativo" conta: depois dele o
    painel tem campos de senha de propósito (redefinir a de um aluno, a de uma
    conta de login). Varrer o roteiro inteiro reprovava justamente a tela
    correta -- foi o que este teste fez na primeira escrita.

    Amplo dentro desse trecho, de propósito: o ponto não é que a frase "Chave
    Mestra" sumiu do código, é que NENHUMA senha é pedida ali.
    """
    portao = []
    for linha in roteiro:
        if "Modo Desenvolvedor Ativo" in linha:
            break
        portao.append(linha)

    return any(
        "text_input" in linha and ("chave" in linha.lower() or "senha" in linha.lower())
        for linha in portao
    )


# ====================== O PORTÃO DO PAINEL ======================


def test_desenvolvedor_logado_nao_digita_mais_nada():
    roteiro = _rodar_adm({"usuario": DEV})

    assert not _pediu_senha(roteiro), "pediu senha para quem ja entrou como desenvolvedor"
    assert _abriu_o_painel(roteiro)


@pytest.mark.parametrize("papel", ["professor", "aluno"])
def test_quem_nao_e_desenvolvedor_nao_abre_o_painel(papel):
    # Vale principalmente para o professor: ele chega ao painel de gestao, e
    # antes desta mudanca so a Chave Mestra o separava do ADM.
    roteiro = _rodar_adm({"usuario": {"id": "2", "username": "p", "role": papel}})

    assert not _abriu_o_painel(roteiro), papel


@pytest.mark.parametrize("papel", ["professor", "aluno"])
def test_e_nao_ha_mais_chave_para_ele_tentar(papel):
    """A metade que faltava. Barrar sem tirar a chave só troca a porta de
    lugar: quem soubesse a senha combinada continuaria entrando."""
    roteiro = _rodar_adm({"usuario": {"id": "2", "username": "p", "role": papel}})

    assert not _pediu_senha(roteiro), f"{papel} ainda recebeu um campo de senha: {roteiro}"
    assert not any("Chave Mestra" in linha for linha in roteiro), papel


def test_sem_ninguem_logado_o_painel_nao_abre():
    roteiro = _rodar_adm({})

    assert not _abriu_o_painel(roteiro)
    assert not _pediu_senha(roteiro), "a chave voltou a ser oferecida na sessao vazia"


def test_sessao_com_usuario_estranho_nao_e_confundida_com_desenvolvedor():
    for usuario in ("desenvolvedor", None, [], {"role": None}, {"role": "Desenvolvedor "}):
        roteiro = _rodar_adm({"usuario": usuario})
        assert not _abriu_o_painel(roteiro), repr(usuario)


# ====================== A PORTA ANTES DO LOGIN ======================
#
# É por aqui que se cadastra a PRIMEIRA escola -- sem escola não há por onde
# entrar. Era o único lugar onde a Chave Mestra ainda se justificava, e é o
# que esta seção passa a cobrar por usuário e senha.


def _rodar_porta_inicial(respostas: dict, conta_devolvida, sessao: dict | None = None):
    """Roda a porta do ADM da tela inicial com o `autenticar` dublado."""
    import services.auth_service as auth

    original = auth.autenticar
    auth.autenticar = lambda *_a, **_k: conta_devolvida
    try:
        with StreamlitFalso(
            sessao=dict(sessao or {}),
            respostas=dict(respostas),
            parametros={"abrir_adm": "1"},
        ) as fake:
            _reimportar_com_o_duble()
            tela = importlib.import_module("st.ui.home_st")
            try:
                tela._renderizar_adm_inicio()
            except Exception as erro:  # noqa: BLE001
                if type(erro).__name__ != "ParouAqui":
                    fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:120]}")
    finally:
        auth.autenticar = original
    return fake


CREDENCIAIS = {"Acessar ADM": True, "Usuário": "dev", "Senha": "segredo"}


def test_a_porta_inicial_pede_usuario_e_senha_e_nao_a_chave():
    fake = _rodar_porta_inicial(CREDENCIAIS, DEV)
    roteiro = fake.roteiro()

    assert any("text_input: Usuário" in linha for linha in roteiro), roteiro
    assert any("text_input: Senha" in linha for linha in roteiro), roteiro
    assert not any("Chave Mestra" in linha for linha in roteiro), roteiro


def test_conta_de_desenvolvedor_entra_e_fica_na_sessao():
    fake = _rodar_porta_inicial(CREDENCIAIS, DEV)

    assert fake.session_state.get("usuario") == DEV, "o desenvolvedor nao entrou"
    # Sem escola de propósito: é a entrada GLOBAL.
    assert not fake.session_state.get("escola")


@pytest.mark.parametrize(
    "conta",
    [
        None,  # usuário ou senha errados
        {"id": "2", "username": "prof", "role": "professor"},
        {"id": "3", "username": "aluno", "role": "aluno"},
        {"id": "4", "username": "x", "role": ""},
    ],
    ids=["senha-errada", "professor", "aluno", "sem-papel"],
)
def test_quem_nao_e_desenvolvedor_nao_passa_pela_porta_inicial(conta):
    """O perigo específico: esta porta é anterior a QUALQUER escolha de
    escola. Uma conta de professor que entrasse por aqui entraria sem
    unidade nenhuma -- exatamente o estado que `conta_pode_entrar` recusa."""
    fake = _rodar_porta_inicial(CREDENCIAIS, conta)

    assert not fake.session_state.get("usuario"), f"{conta} entrou no ADM"
    assert any("error" in linha for linha in fake.roteiro()), fake.roteiro()


def test_a_recusa_nao_conta_qual_dos_dois_estava_errado():
    """Dizer "esse usuário não existe" conta a quem tenta que o OUTRO nome
    existe. A mensagem é a mesma para senha errada e para conta que não é de
    desenvolvedor."""
    tela = importlib.import_module("st.ui.home_st")
    motivo = tela.MOTIVO_ADM_RECUSADO.lower()

    assert "inválidos" in motivo or "invalidos" in motivo
    for palavra in ("não existe", "nao existe", "inexistente", "senha incorreta"):
        assert palavra not in motivo, f"a recusa entrega demais: {motivo!r}"


def test_supabase_fora_do_ar_nao_vira_senha_errada():
    """Sem isto a pessoa passa a tarde tentando lembrar a senha certa."""
    import services.auth_service as auth

    original = auth.autenticar

    def _explode(*_a, **_k):
        raise RuntimeError("conexao recusada")

    auth.autenticar = _explode
    try:
        with StreamlitFalso(
            sessao={}, respostas=dict(CREDENCIAIS), parametros={"abrir_adm": "1"}
        ) as fake:
            _reimportar_com_o_duble()
            tela = importlib.import_module("st.ui.home_st")
            try:
                tela._renderizar_adm_inicio()
            except Exception as erro:  # noqa: BLE001
                if type(erro).__name__ != "ParouAqui":
                    fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:120]}")
    finally:
        auth.autenticar = original

    roteiro = fake.roteiro()
    assert any("conexao recusada" in linha for linha in roteiro), roteiro
    assert not fake.session_state.get("usuario")


# ====================== A PÁGINA "🏛️ ADM" ======================
#
# O ADM deixou de ser aba e virou página. Página tem URL, e URL é porta:
# "?pagina=adm" é lido direto de query_params em _renderizar_sidebar.


def _pagina_permitida_para(papel: str | None, pagina: str) -> bool:
    sessao = {"usuario": {"id": "1", "role": papel}} if papel else {}
    with StreamlitFalso(sessao=sessao):
        _reimportar_com_o_duble()
        tela = importlib.import_module("st.ui.home_st")
        return tela._pagina_permitida(pagina)


def test_so_desenvolvedor_alcanca_a_pagina_adm():
    assert _pagina_permitida_para("desenvolvedor", "🏛️ ADM") is True


@pytest.mark.parametrize("papel", ["professor", "aluno", None])
def test_ninguem_mais_alcanca_a_pagina_adm(papel):
    assert _pagina_permitida_para(papel, "🏛️ ADM") is False, papel


def test_a_pagina_adm_esta_no_mapa_de_slugs():
    """Se o slug sumir, o card do desenvolvedor cai no "Início" silenciosamente
    (_secao_de_cards_navegaveis usa PAGINAS_POR_SLUG.get(acao, "🏠 Início"))."""
    tela = importlib.import_module("st.ui.home_st")

    assert tela.PAGINAS_POR_SLUG.get("adm") == "🏛️ ADM"
    assert "🏛️ ADM" in tela.PAGINAS


def test_o_painel_de_gestao_continua_barrado_para_aluno():
    """A tranca antiga não pode ter caído junto."""
    assert _pagina_permitida_para("aluno", "👨‍🏫 Professor") is False
    assert _pagina_permitida_para("professor", "👨‍🏫 Professor") is True
    assert _pagina_permitida_para("desenvolvedor", "👨‍🏫 Professor") is True


# ====================== AS ABAS DO PAINEL DE GESTÃO ======================


def _abas_do_painel(papel: str) -> list[str]:
    with StreamlitFalso(sessao={"usuario": {"id": "1", "role": papel}}) as fake:
        _reimportar_com_o_duble()
        painel = importlib.import_module("st.ui.professor_panel_st")
        # as abas de sempre falam com o Supabase; aqui so interessa QUAIS
        # abas existem
        for nome in (
            "renderizar_aba_analises",
            "_renderizar_aba_rpg_config",
            "_renderizar_aba_matricula",
            "_renderizar_aba_ranking",
            "_renderizar_aba_resumo_turma",
            "_renderizar_aba_professores",
            "_renderizar_aba_configuracoes",
        ):
            setattr(painel, nome, lambda *_a, **_k: None)
        try:
            painel.renderizar_painel_professor("escola-1", {"id": "escola-1", "nome": "E"}, None)
        except Exception:  # noqa: BLE001
            pass
        roteiro = fake.roteiro()

    linha = next((l for l in roteiro if l.startswith("tabs:")), "")
    return [rotulo.strip() for rotulo in linha[len("tabs:"):].split("|") if rotulo.strip()]


@pytest.mark.parametrize("papel", ["professor", "desenvolvedor"])
def test_a_aba_adm_nao_existe_mais_para_ninguem(papel):
    """Ela virou página. Manter as duas seria manter uma área de
    desenvolvedor dentro da área de outro papel."""
    abas = _abas_do_painel(papel)

    assert abas, "nao desenhou aba nenhuma"
    assert not any("ADM" in aba for aba in abas), f"{papel} ainda ve a aba ADM: {abas}"


def test_o_painel_e_o_mesmo_para_professor_e_desenvolvedor():
    de_professor = _abas_do_painel("professor")
    de_dev = _abas_do_painel("desenvolvedor")

    assert de_professor == de_dev, "o painel de gestao voltou a mudar por papel"
    assert len(de_professor) == 7, de_professor


def test_a_aba_de_professores_entrou_sem_levar_as_outras():
    abas = _abas_do_painel("professor")

    assert any("Professores" in aba for aba in abas), abas
    for esperada in ("Análises", "RPG", "Matrícula", "Ranking", "Resumo da Turma", "Configurações"):
        assert any(esperada in aba for aba in abas), f"a aba '{esperada}' sumiu: {abas}"


# ====================== A HOME DO DESENVOLVEDOR ======================


def _cards_da_home_global() -> list[str]:
    with StreamlitFalso(sessao={"usuario": DEV}) as fake:
        _reimportar_com_o_duble()
        tela = importlib.import_module("st.ui.home_st")
        try:
            tela._renderizar_home_global_do_desenvolvedor()
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:120]}")
        roteiro = fake.roteiro()

    return [l for l in roteiro if l.startswith("button:")]


def test_a_home_global_do_desenvolvedor_tem_as_duas_areas_e_o_sair():
    botoes = _cards_da_home_global()
    texto = " ".join(botoes)

    assert "Professor" in texto, botoes
    assert "ADM" in texto, botoes
    # Dois cards de área + Sair. Sem o Sair a pessoa fica presa: esta home não
    # tem a navegação lateral, que só existe depois de escolher escola.
    assert len(botoes) == 3, botoes
    assert "Sair" in texto, botoes


def test_a_home_global_nao_oferece_os_modos_de_jogo():
    """O desenvolvedor entra para administrar. A vitrine de modos era o que
    fazia a conta de ADM parecer conta de aluno."""
    texto = " ".join(_cards_da_home_global())

    for modo in ("Treino", "ENEM", "Oráculo", "Laboratório", "RPG", "Escape Room"):
        assert modo not in texto, f"a home global ainda oferece '{modo}': {texto}"


# ====================== E O CAMINHO ATÉ ELA ======================
#
# MELHORIA: os dois testes acima chamam a home DIRETO. Isso deixou passar um
# mutante: desligar o desvio que leva até ela (`if _eh_desenvolvedor()` em
# _renderizar_adm_inicio) mantinha tudo verde -- a função continuava certa, e
# ninguém chegava nela.
#
# Era justamente o defeito relatado: "entro como ADM e ele me devolve como
# aluno". O erro nunca esteve na tela de destino; esteve no caminho.


def _roteiro_da_tela_inicial(sessao: dict) -> list[str]:
    with StreamlitFalso(sessao=dict(sessao)) as fake:
        _reimportar_com_o_duble()
        tela = importlib.import_module("st.ui.home_st")
        try:
            tela._renderizar_adm_inicio()
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:120]}")
    return fake.roteiro()


# O título da home vive dentro de um bloco HTML, e o roteiro corta cada linha
# em 90 caracteres -- procurá-lo ali reprova a tela certa. Os BOTÕES aparecem
# inteiros, e são o que de fato distingue esta home.
MARCA_DA_HOME_GLOBAL = "**Professor**"
# Idem para a porta: o texto do cartão fica além do corte, a classe não.
MARCA_DA_PORTA = "edu-admin-gate"


def test_desenvolvedor_logado_e_desviado_para_a_home_dele():
    roteiro = _roteiro_da_tela_inicial({"usuario": DEV})
    texto = " ".join(roteiro)

    assert MARCA_DA_HOME_GLOBAL in texto, f"o desenvolvedor nao caiu na home dele: {roteiro}"
    assert "**ADM**" in texto, roteiro
    # Com a marca truncada este assert seria VAZIO -- verdadeiro porque a
    # frase nunca aparece no roteiro, e não porque a tela mudou.
    assert MARCA_DA_PORTA not in texto, "voltou a oferecer o cartao de entrar no ADM"


def test_quem_nao_e_desenvolvedor_ve_a_porta_e_nao_a_home():
    """O par: o desvio não pode valer para todo mundo."""
    for sessao in ({}, {"usuario": {"id": "9", "role": "professor"}}):
        texto = " ".join(_roteiro_da_tela_inicial(sessao))
        assert MARCA_DA_HOME_GLOBAL not in texto, f"{sessao} caiu na home do desenvolvedor"
        assert MARCA_DA_PORTA in texto, f"{sessao} perdeu a porta do ADM"


def _cards_da_home_com_escola(papel: str) -> list[str]:
    """A home de DENTRO de uma escola -- a que devolvia a vitrine de aluno."""
    sessao = {"usuario": {"id": "1", "role": papel}}
    with StreamlitFalso(sessao=sessao) as fake:
        _reimportar_com_o_duble()
        tela = importlib.import_module("st.ui.home_st")
        try:
            tela._renderizar_dashboard({"id": "esc-1", "nome": "ETEC"}, [], [])
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:120]}")
        roteiro = fake.roteiro()

    return [l for l in roteiro if l.startswith("button:")]


def test_a_home_da_escola_tambem_e_de_duas_areas_para_o_desenvolvedor():
    """Era ESTA a tela do print: 'ÁREA DO ALUNO' com seis modos, para quem
    entrou como desenvolvedor."""
    texto = " ".join(_cards_da_home_com_escola("desenvolvedor"))

    assert "Professor" in texto and "ADM" in texto, texto
    for modo in ("Treino Rápido", "Escape Room", "Perfil do Aluno"):
        assert modo not in texto, f"a home ainda devolve o modo '{modo}' ao desenvolvedor"


def test_a_home_da_escola_continua_inteira_para_o_aluno():
    """O par. Dar duas áreas ao desenvolvedor não pode tirar os modos de quem
    entra para jogar."""
    texto = " ".join(_cards_da_home_com_escola("aluno"))

    for modo in ("Treino Rápido", "ENEM", "Escape Room"):
        assert modo in texto, f"o aluno perdeu o modo '{modo}'"
    assert "ADM" not in texto
