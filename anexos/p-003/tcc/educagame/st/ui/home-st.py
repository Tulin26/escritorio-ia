import re

import streamlit as st
from html import escape
from urllib.parse import quote

import core.utils as core_utils
import services.dados_service as db
from repositories.escola_repo import obter_ultimo_erro_listar_escolas
from repositories.supabase_client import diagnostico_supabase_seguro
from services.escola_service import listar_escolas, mostra_guildas, mostra_ranking
from core.design_system import aplicar_estilo_global_edugame
from core.design_system_base import bloco_html as _bloco_html
from st.ui.mode_common_st import registrar_log_com_tempo_ui as _registrar_log_com_tempo_ui_base

formatar_latex = core_utils.formatar_latex
_tem_matriz = core_utils.tem_matriz


def _html_seguro(texto) -> str:
    return escape(str(texto or ""))


def _html_multilinha(texto) -> str:
    return _html_seguro(texto).replace("\n", "<br>")


def _classe_risco_rpg(risco: str) -> str:
    return {"baixo": "baixo", "medio": "medio", "alto": "alto"}.get(str(risco or "").lower(), "medio")


def _chip_rpg(texto: str, variante: str = "neutro") -> str:
    if not texto:
        return ""
    return f"<span class='rpg-chip rpg-chip--{variante}'>{_html_seguro(texto)}</span>"


def _formatar_texto_markdown(texto) -> str:
    texto_fmt = str(texto or "")
    texto_fmt = texto_fmt.replace("R$", "CURRENCYBRLTOKEN")
    texto_fmt = texto_fmt.replace("$", r"\$")
    return texto_fmt.replace("CURRENCYBRLTOKEN", r"R\$")


def _registrar_log_com_tempo_ui(dados: dict, tempo_resposta=None):
    return _registrar_log_com_tempo_ui_base(db, dados, tempo_resposta)


PAGINAS = [
    "🏠 Início", "🎮 Jogar", "🎓 ENEM", "👑 Boss Rush", "🔐 Escape Room",
    "🛡️ Guildas", "⚔️ RPG", "🧪 Laboratório", "👨‍🏫 Professor", "🏛️ ADM",
    "❓ Ajuda",
]

PAGINAS_POR_SLUG = {
    "inicio": "🏠 Início",
    "jogar": "🎮 Jogar",
    "enem": "🎓 ENEM",
    "bossrush": "👑 Boss Rush",
    "escape": "🔐 Escape Room",
    "guildas": "🛡️ Guildas",
    "rpg": "⚔️ RPG",
    "laboratorio": "🧪 Laboratório",
    "professor": "👨‍🏫 Professor",
    "adm": "🏛️ ADM",
    "ajuda": "❓ Ajuda",
}

# So professor e desenvolvedor entram no painel de gestao. Sem isto, um aluno
# logado chega la digitando "?pagina=professor" na URL -- o slug da pagina e
# lido direto de query_params em _renderizar_sidebar.
PAGINAS_SO_DE_GESTAO = {"👨‍🏫 Professor"}

# O ADM e mais restrito que o painel de gestao: professor tambem nao entra.
# Antes o ADM era uma ABA dentro do painel do professor, e a unica coisa que
# o separava de um professor era a Chave Mestra -- uma senha unica. Agora que
# ele e pagina, a URL vira porta ("?pagina=adm"), e a porta precisa de tranca.
PAGINAS_SO_DE_DESENVOLVEDOR = {"🏛️ ADM"}

# MELHORIA: a Batalha de Guildas abria mesmo com modo_guilda desligado na
# escola (RF14). Esconder o card nao basta: "?pagina=guildas" e porta, igual
# ao ADM. Esta tranca depende da ESCOLA, e nao do papel -- nem o professor ve
# a disputa que a propria escola desligou.
PAGINAS_DA_GUILDA = {"🛡️ Guildas"}


def _eh_aluno() -> bool:
    return (st.session_state.get("usuario") or {}).get("role") == "aluno"


def _pagina_permitida(pagina: str | None, dados_escola: dict | None = None) -> bool:
    if pagina in PAGINAS_SO_DE_DESENVOLVEDOR:
        return _eh_desenvolvedor()
    if pagina in PAGINAS_SO_DE_GESTAO:
        return not _eh_aluno()
    if pagina in PAGINAS_DA_GUILDA:
        # Sem escola informada, fechada: ver _opcao_ligada.
        return mostra_guildas(dados_escola)
    return True


def _renderizar_sidebar(dados_escola: dict | None, ranking: list[dict] | None, ranking_guildas: list[dict] | None):
    paginas = PAGINAS
    paginas_por_slug = PAGINAS_POR_SLUG
    pagina_query = st.query_params.get("pagina")
    if isinstance(pagina_query, list):
        pagina_query = pagina_query[0] if pagina_query else None
    if pagina_query in paginas_por_slug:
        alvo = paginas_por_slug[pagina_query]
        if _pagina_permitida(alvo, dados_escola):
            st.session_state.pagina_atual = alvo
        st.query_params.clear()

    destino_pendente = st.session_state.pop("pagina_destino", None)
    if destino_pendente in paginas and _pagina_permitida(destino_pendente, dados_escola):
        st.session_state.pagina_atual = destino_pendente
    if "pagina_atual" not in st.session_state:
        st.session_state.pagina_atual = "🏠 Início"
    # Cobre tambem a sessao que ja estava numa pagina de gestao antes de
    # alguem entrar como aluno -- e a que estava nas Guildas quando o
    # professor desligou o modo.
    if not _pagina_permitida(st.session_state.pagina_atual, dados_escola):
        st.session_state.pagina_atual = "🏠 Início"
    return st.session_state.pagina_atual


def _secao_de_cards_navegaveis(titulo: str, cards: list[tuple], colunas_por_linha: int = 3) -> None:
    """Renderiza uma secao do dashboard como BOTOES, nao como links.

    MELHORIA: estes cards eram ancoras (<a href="?escola=...&pagina=...">),
    ou seja, cada clique recarregava a pagina inteira. Isso funcionava
    quando nao havia login, porque o estado era reconstruido a partir da
    URL a cada carga. Com autenticacao isso quebra: o st.session_state (e
    portanto o usuario logado) morre no reload, e o aluno era jogado de
    volta para a tela de login a cada clique. Como botao, a navegacao usa
    _ir_para/st.rerun, sem recarregar -- a sessao sobrevive e nenhum token
    precisa viajar na URL.

    Cada item e (icone, titulo, texto, variante, acao), onde acao e o slug
    da pagina de destino ou um callable (usado pelo "Sair").
    """
    st.markdown(f"<div class='edu-kicker'>{_html_seguro(titulo)}</div>", unsafe_allow_html=True)
    with st.container(key=f"edu-cards-{_slug_css(titulo)}"):
        for inicio in range(0, len(cards), colunas_por_linha):
            linha = cards[inicio : inicio + colunas_por_linha]
            colunas = st.columns(colunas_por_linha)
            for coluna, (icone, titulo_card, texto, variante, acao) in zip(colunas, linha):
                with coluna:
                    # MELHORIA: o rotulo do botao do Streamlit aceita apenas
                    # um subconjunto de markdown -- cabecalhos ("#", "####")
                    # aparecem crus na tela. Usa negrito e quebra de linha,
                    # que sao suportados; o tamanho do emoji e do titulo vem
                    # do CSS (ver design_system_global).
                    rotulo = f"{icone}\n\n**{titulo_card}**\n\n{texto}"
                    clicou = st.button(
                        rotulo,
                        key=f"card_{_slug_css(titulo)}_{_slug_css(titulo_card)}",
                        width="stretch",
                    )
                    if clicou:
                        if callable(acao):
                            acao()
                        else:
                            _ir_para(PAGINAS_POR_SLUG.get(acao, "🏠 Início"))


def _slug_css(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(texto or "").lower()).strip("-")


def _sair_da_conta() -> None:
    st.query_params.clear()
    for chave in list(st.session_state.keys()):
        del st.session_state[chave]
    st.rerun()


def _missao_do_dia_html(total_questoes: int, taxa_acerto: int, mostrar_ranking: bool) -> str:
    progresso = min(100, max(12, total_questoes * 20 if total_questoes < 5 else 64))
    foco = "Matemática" if taxa_acerto < 60 else "Português"
    # Com o ranking desligado na escola, prometer "subir no ranking" aponta
    # para uma classificacao que o aluno nao tem onde ver.
    recompensa = "ganhe XP para subir no ranking" if mostrar_ranking else "ganhe XP"
    return _bloco_html(
        f"""
        <div class="edu-mission-card">
            <div class="edu-mission-top">
                <div>
                    <div class="edu-kicker">Missão do dia</div>
                    <div class="edu-mission-title">Complete 5 desafios de {foco}</div>
                    <div class="edu-mission-copy">
                        Resolva uma sequência curta, revise seus erros e {recompensa}.
                    </div>
                </div>
                <div class="edu-xp-badge">+80 XP</div>
            </div>
            <div class="edu-progress-track"><div class="edu-progress-fill" style="width:{progresso}%"></div></div>
            <div class="edu-sidebar-meta">{min(5, total_questoes % 6)}/5 etapas concluídas hoje</div>
        </div>
        """
    )


# O titulo acompanha o que sobrou: "Ranking e guildas" em cima de um card so
# anunciaria a metade que a escola desligou.
TITULO_RANKING_HOME = {
    (True, True): "Ranking e guildas",
    (True, False): "Ranking",
    (False, True): "Guildas",
}


def _ranking_home_html(
    ranking: list[dict] | None,
    ranking_guildas: list[dict] | None,
    *,
    mostrar_ranking: bool,
    mostrar_guildas: bool,
) -> str:
    """Os cards "Top Heróis" e "Guilda em destaque", só os que a escola ligou.

    MELHORIA: os dois saiam sempre, ignorando mostrar_ranking e modo_guilda
    (RF14). As opcoes sao obrigatorias e sem padrao de proposito: um padrao
    True mostraria a classificacao a quem esquecesse de passa-las.
    Com as duas desligadas devolve "", e a home nao desenha a secao.
    """
    cards = []
    if mostrar_ranking:
        medalhas = ["🥇", "🥈", "🥉"]
        linhas_alunos = "".join(
            "<div class='edu-ranking-row'>"
            "<div>"
            f"<div class='edu-ranking-name'>{_html_seguro(medalhas[idx])} {_html_seguro(aluno.get('nome', 'Aluno'))}</div>"
            "<div class='edu-ranking-meta'>Herói em destaque</div>"
            "</div>"
            f"<div class='edu-xp-badge'>{int(aluno.get('pontos_totais') or 0)} XP</div>"
            "</div>"
            for idx, aluno in enumerate((ranking or [])[:3])
        ) or "<div class='edu-ranking-meta'>Sem pontuação registrada ainda.</div>"
        cards.append(
            "<div class='edu-ranking-card'>"
            "<div class='edu-home-section-title' style='margin-top:0'>Top Heróis</div>"
            f"{linhas_alunos}"
            "</div>"
        )

    if mostrar_guildas:
        guilda = (ranking_guildas or [{}])[0]
        guilda_nome = guilda.get("guilda", "Nenhuma guilda")
        guilda_pts = int(guilda.get("pontos_grupais") or 0)
        cards.append(
            "<div class='edu-ranking-card'>"
            "<div class='edu-home-section-title' style='margin-top:0'>Guilda em destaque</div>"
            "<div class='edu-dashboard-icon'>🛡️</div>"
            f"<div class='edu-ranking-name'>{_html_seguro(guilda_nome)}</div>"
            f"<div class='edu-ranking-meta'>{guilda_pts} pontos grupais acumulados</div>"
            "</div>"
        )

    if not cards:
        return ""
    # Com um card so, o grid de duas colunas (1.2fr 0.8fr) deixaria um buraco
    # ao lado; uma coluna ocupa a largura toda.
    estilo = "" if len(cards) == 2 else " style='grid-template-columns:1fr'"
    return f"<div class='edu-ranking-grid'{estilo}>" + "".join(cards) + "</div>"


def _quem_somos_html() -> str:
    return _bloco_html(
        """
        <div class="edu-about-card">
            <div class="edu-about-grid">
                <div>
                    <div class="edu-kicker">Quem somos</div>
                    <div class="edu-about-title">EducaGame: aprender também pode ser uma jornada</div>
                    <div class="edu-about-copy">
                        Somos uma plataforma educacional gamificada criada para aproximar os alunos do estudo por meio de desafios,
                        feedback pedagógico, rankings, missões e narrativas interativas. A proposta une tecnologia, dados e inteligência
                        artificial para transformar conteúdos escolares em experiências mais claras, práticas e motivadoras.
                    </div>
                </div>
                <div class="edu-about-list">
                    <div class="edu-about-item"><strong>Missão:</strong> tornar o aprendizado mais envolvente e acessível.</div>
                    <div class="edu-about-item"><strong>Foco:</strong> ajudar o aluno a entender erros e evoluir com prática.</div>
                    <div class="edu-about-item"><strong>Para professores:</strong> oferecer dados, relatórios e acompanhamento da turma.</div>
                </div>
            </div>
        </div>
        """
    )


def _ir_para(pagina: str):
    st.query_params.clear()
    st.session_state.pagina_destino = pagina
    st.rerun()


def _renderizar_voltar_painel():
    voltar_col, _ = st.columns([1, 5])
    if voltar_col.button("🏠 Painel Inicial", width="stretch"):
        _ir_para("🏠 Início")


def _eh_desenvolvedor() -> bool:
    return str((st.session_state.get("usuario") or {}).get("role", "")) == "desenvolvedor"


# Reexportado de services/: o Flask mostra a MESMA frase na mesma porta, e
# duas copias divergem na primeira vez que alguem reescreve uma so.
from services.auth_service import MOTIVO_ADM_RECUSADO  # noqa: E402

# As duas areas do desenvolvedor, num lugar so: a home global (antes de
# escolher escola) e a home de dentro de uma escola desenham os MESMOS dois
# cards. Duplicar a lista era garantir que uma das duas ficasse para tras.
CARD_PROFESSOR = (
    "👨‍🏫",
    "Professor",
    "Acompanhe os alunos e veja os professores cadastrados de cada escola.",
    "professor",
)
CARD_ADM = (
    "🏛️",
    "ADM",
    "Escolas, contas de login, senhas de aluno e diagnóstico.",
    "adm",
)


def _renderizar_adm_inicio():
    """A porta do ADM, antes de escolher escola -- hoje por usuário e senha.

    MELHORIA: aqui se digitava a Chave Mestra, uma senha unica combinada entre
    pessoas. Ela e anterior a tabela de usuarios: a migracao
    20260803120100_usuarios.sql diz, na primeira linha, que veio "substituir a
    senha mestra unica por uma tabela real, com senha em hash". A troca parou
    no meio, e o argumento escrito para deixar assim era que "aqui nao ha
    usuario para consultar, porque ninguem escolheu escola ainda".

    O argumento estava errado. A conta de desenvolvedor e GLOBAL de proposito
    -- `services/auth_service.py::conta_pode_entrar` devolve True para ela sem
    sequer olhar a escola. Ou seja: da para autenticar antes de escolher
    unidade, e e o que esta tela faz agora.

    O que se perde: a senha unica servia de chave reserva se ninguem lembrasse
    a senha do desenvolvedor. A reserva agora e `scripts/seed_usuarios.py`,
    que faz upsert da conta -- exige a chave do Supabase, e nao uma senha
    combinada no WhatsApp. E uma porta mais estreita de proposito.
    """
    if _eh_desenvolvedor():
        _renderizar_home_global_do_desenvolvedor()
        st.stop()

    abrir_adm = st.query_params.get("abrir_adm", "")
    if isinstance(abrir_adm, list):
        abrir_adm = abrir_adm[0] if abrir_adm else ""

    st.markdown(
        _bloco_html(
            """
            <div class="edu-admin-gate">
                <a class="edu-admin-card" href="?abrir_adm=1" target="_self">
                    <span class="edu-admin-icon">🏫</span>
                    <span>
                        <span class="edu-kicker">ADM</span>
                        <span class="edu-admin-card-title">Gestão de Escolas</span>
                        <span class="edu-admin-card-copy">Entre com a conta de desenvolvedor para gerenciar as escolas sem acessar uma unidade específica.</span>
                    </span>
                    <span class="edu-admin-card-action">Acessar</span>
                </a>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    if str(abrir_adm) != "1":
        return

    st.markdown("<div class='edu-admin-form'>", unsafe_allow_html=True)
    with st.form("login_admin_inicio"):
        usuario_digitado = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        acessar = st.form_submit_button("Acessar ADM")
        if acessar:
            from services.auth_service import autenticar

            try:
                conta = autenticar(usuario_digitado, senha)
            except Exception as erro:  # noqa: BLE001
                # Supabase fora do ar aqui vira "senha errada" se nao tratar --
                # e a pessoa passa a tarde tentando lembrar a senha certa.
                st.error(f"Não foi possível verificar a conta agora: {erro}")
                return

            if conta and str(conta.get("role", "")) == "desenvolvedor":
                st.session_state.usuario = conta
                # Sem escola de proposito: e a entrada GLOBAL. Quem quiser o
                # painel de uma unidade escolhe qual, na propria home.
                st.query_params.clear()
                st.rerun()
            else:
                st.error(MOTIVO_ADM_RECUSADO)
    st.markdown("</div>", unsafe_allow_html=True)


def _renderizar_home_global_do_desenvolvedor() -> None:
    """Os dois cards do desenvolvedor que entrou sem escolher escola."""
    area = st.session_state.get("area_desenvolvedor") or ""

    if area == "adm":
        from st.ui.admin_st import tela_administrador

        if st.button("← Voltar", key="voltar_home_dev_adm"):
            st.session_state.pop("area_desenvolvedor", None)
            st.rerun()
        tela_administrador()
        return

    if area == "professor":
        _escolher_escola_do_desenvolvedor()
        return

    st.markdown(
        _bloco_html(
            """
            <div class="edu-panel-heading">
                <div>
                    <div class="edu-kicker">Desenvolvedor</div>
                    <div class="edu-panel-title">Painel global</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        "Esta conta não pertence a nenhuma escola: ela enxerga todas. "
        "Escolha por onde entrar."
    )

    def _abrir(area_alvo: str):
        def _acao():
            st.session_state.area_desenvolvedor = area_alvo
            st.rerun()

        return _acao

    _secao_de_cards_navegaveis(
        "Áreas",
        [
            (*CARD_PROFESSOR[:3], "professor", _abrir("professor")),
            (*CARD_ADM[:3], "professor", _abrir("adm")),
        ],
        colunas_por_linha=2,
    )
    _secao_de_cards_navegaveis(
        "Sessão",
        [("↔", "Sair", "Encerrar a sessão e voltar para a tela de login.", "professor", _sair_da_conta)],
        colunas_por_linha=2,
    )


def _escolher_escola_do_desenvolvedor() -> None:
    """Qual unidade o desenvolvedor quer acompanhar.

    Nao pede o codigo da escola: o codigo e a tranca voltada ao ALUNO, passada
    pelo professor na sala (ver _formulario_codigo_escola). Quem ja provou ser
    desenvolvedor le todos os codigos na propria tela de ADM -- exigir aqui
    seria atrito sem tranca nenhuma atras.
    """
    if st.button("← Voltar", key="voltar_home_dev_professor"):
        st.session_state.pop("area_desenvolvedor", None)
        st.rerun()

    st.subheader("👨‍🏫 Qual escola você quer acompanhar?")

    escolas = [e for e in (listar_escolas() or []) if e.get("id")]
    if not escolas:
        st.info("Nenhuma escola cadastrada ainda. Cadastre a primeira pelo ADM.")
        return

    for escola in escolas:
        if st.button(
            str(escola.get("nome") or "Escola"),
            key=f"dev_escola_{escola.get('id')}",
            width="stretch",
        ):
            st.session_state.escola = escola
            st.session_state.pop("area_desenvolvedor", None)
            # Entra direto no painel, e nao na home da escola: foi o que a
            # pessoa pediu ao clicar em "Professor".
            st.session_state.pagina_atual = "👨‍🏫 Professor"
            st.rerun()


# A escola cujo codigo ja foi digitado NESTA sessao. Guardar o id, e nao um
# booleano, e o que impede o codigo de uma escola liberar a outra: quem trocar
# de unidade digita de novo.
CHAVE_ESCOLA_LIBERADA = "escola_liberada_id"


def _escola_liberada(escola) -> bool:
    liberada = str(st.session_state.get(CHAVE_ESCOLA_LIBERADA, "") or "")
    return bool(liberada) and liberada == str((escola or {}).get("id", "") or "")


def _esquecer_codigo_da_escola() -> None:
    """Sair volta a pedir o codigo -- o computador da sala e compartilhado."""
    st.session_state.pop(CHAVE_ESCOLA_LIBERADA, None)


def _formulario_codigo_escola(escola) -> None:
    from services.escola_service import MOTIVO_CODIGO_INCORRETO, codigo_confere

    with st.form("codigo_escola"):
        st.markdown(
            f"**{_html_seguro(escola.get('nome', 'Escola'))}**",
            unsafe_allow_html=True,
        )
        st.caption(
            "Digite o código da escola para continuar. Ele é passado pelo professor — "
            "não é a sua senha."
        )
        codigo_informado = st.text_input("Código da escola")

        if st.form_submit_button("Continuar"):
            if codigo_confere(escola, codigo_informado):
                st.session_state[CHAVE_ESCOLA_LIBERADA] = str(escola.get("id", "") or "")
                st.rerun()
            else:
                st.error(MOTIVO_CODIGO_INCORRETO)


TITULO_DA_ESCOLHA = """
            <div style="text-align:center; margin: 1.7rem 0 1.4rem;">
                <div style="color:var(--edu-text); font-size:clamp(2rem, 4vw, 3rem); font-weight:900; line-height:1.08;">
                    Escolha sua escola
                </div>
                <div style="color:var(--edu-muted); margin-top:0.45rem; font-size:1rem;">
                    Selecione sua unidade, digite o código da escola e entre com seu usuário e senha.
                </div>
            </div>
            """


def escolas_com_slug(escolas) -> list[dict]:
    """As escolas que podem virar porta de entrada.

    Escola sem slug não entra na grade: o slug é o que identifica a unidade
    no resto do sistema, e um cartão sem ele levaria a uma tela que não sabe
    de que escola está falando.
    """
    return [escola for escola in (escolas or []) if escola.get("slug")]


def escola_pedida_na_url(escolas_validas, valor_do_parametro):
    """(id pedido, escola correspondente ou None).

    O `st.query_params` devolve ora texto, ora lista -- depende de a URL
    repetir o parâmetro. Ler o formato errado transformava um clique legítimo
    em "nenhuma escola escolhida", e a tela voltava para o começo sem
    explicar. Fora do render porque é normalização de entrada, e dá para
    conferir com um dicionário e nenhuma tela.
    """
    if isinstance(valor_do_parametro, list):
        valor_do_parametro = valor_do_parametro[0] if valor_do_parametro else ""
    pedido = str(valor_do_parametro or "")
    escola = next(
        (item for item in escolas_validas if str(item.get("id", "")) == pedido),
        None,
    )
    return pedido, escola


def html_dos_cartoes(escolas_validas, escola_selecionada_id: str) -> str:
    """A grade de escolas, em HTML.

    O nome da escola vem do banco e é escrito dentro de HTML cru, então passa
    por `_html_seguro` -- um nome com `<` ou aspas fecharia a tag e o resto da
    página viraria marcação de outra pessoa. O id vai por `quote`, porque
    entra numa URL.
    """
    return "".join(
        "<a class='edu-school-card{classe}' href='?selecionar_escola={escola_id}' target='_self'>"
        "<span class='edu-school-name'>{nome}</span>"
        "<span class='edu-school-hint'>Entrar</span>"
        "</a>".format(
            classe=" edu-school-card--selected"
            if str(escola.get("id", "")) == escola_selecionada_id
            else "",
            nome=_html_seguro(escola.get("nome", "Escola")),
            escola_id=quote(str(escola.get("id", ""))),
        )
        for escola in escolas_validas
    )


def _desenhar_grade_de_escolas(escolas_validas, escola_selecionada_id: str) -> None:
    st.markdown(
        _bloco_html(
            f"""
                <div class="edu-school-grid">
                    {html_dos_cartoes(escolas_validas, escola_selecionada_id)}
                </div>
                """
        ),
        unsafe_allow_html=True,
    )


def _explicar_a_falta_de_escolas() -> None:
    """Zero escolas tem duas causas muito diferentes, e a tela precisa dizer
    qual: a consulta falhou, ou funcionou e o banco está vazio. Sem separar as
    duas, "nenhuma escola" manda procurar cadastro quando o problema é a
    conexão.
    """
    erro_escolas = obter_ultimo_erro_listar_escolas()
    diagnostico = diagnostico_supabase_seguro()
    if erro_escolas:
        st.error("Não foi possível consultar as escolas no Supabase.")
        st.caption("Diagnóstico seguro de configuração:")
        st.json(diagnostico)
        st.code(erro_escolas, language="text")
    else:
        st.info("Nenhuma escola cadastrada foi encontrada.")
        st.caption(
            "A consulta funcionou, mas retornou 0 linhas. Confira se o projeto abaixo é o mesmo "
            "onde existem as escolas cadastradas."
        )
        st.json(diagnostico)


def _formulario_login(escola_selecionada) -> None:
    """MELHORIA: aqui se pedia o SLUG da escola -- um codigo unico
    compartilhado pela turma inteira, que nao identificava ninguem. Depois de
    entrar, qualquer pessoa escolhia num dropdown por qual aluno jogar (e
    pontuar). Agora e login de verdade, reusando o mesmo services.auth_service
    do frontend Flask: aluno entra com e-mail ou usuario,
    professor/desenvolvedor com usuario.
    """
    from services.auth_service import autenticar, conta_pode_entrar

    with st.form("login"):
        st.markdown(
            f"**{_html_seguro(escola_selecionada.get('nome', 'Escola'))}**",
            unsafe_allow_html=True,
        )
        st.caption("Aluno: use seu e-mail ou usuário. Professor ou diretor: use seu usuário.")
        usuario_informado = st.text_input("Usuário ou e-mail").strip()
        senha_informada = st.text_input("Senha", type="password")

        if not st.form_submit_button("Entrar"):
            return
        if not usuario_informado or not senha_informada:
            st.error("Informe usuário e senha.")
            return

        usuario = autenticar(usuario_informado, senha_informada)
        if not usuario:
            st.error("Usuário/e-mail ou senha inválidos.")
            return

        # MELHORIA: esta checagem existia so aqui, so para aluno. Professor
        # nao tinha escola nenhuma, entao entrava em qualquer unidade e abria
        # o painel de gestao dela. A regra virou uma so, em
        # services/auth_service.py, usada tambem pelo Flask.
        pode_entrar, motivo = conta_pode_entrar(usuario, escola_selecionada.get("id"))
        if not pode_entrar:
            st.error(motivo)
            return

        st.session_state.escola = escola_selecionada
        st.session_state.usuario = usuario
        # MELHORIA: aqui se escrevia st.query_params["escola"] = slug.
        # Ninguem lia esse parametro -- era escrita morta -- mas ela deixava o
        # slug na barra de enderecos com cara de link que escolhe a escola,
        # que e justamente o atalho removido do Flask. Um leitor
        # bem-intencionado o traria de volta.
        st.rerun()


def _selecionar_escola_inicial():
    _renderizar_adm_inicio()
    st.markdown(_bloco_html(TITULO_DA_ESCOLHA), unsafe_allow_html=True)

    escolas_validas = escolas_com_slug(listar_escolas())
    escola_selecionada_id, escola_selecionada = escola_pedida_na_url(
        escolas_validas, st.query_params.get("selecionar_escola", "")
    )

    if escolas_validas:
        _desenhar_grade_de_escolas(escolas_validas, escola_selecionada_id)
    else:
        _explicar_a_falta_de_escolas()

    if escola_selecionada and not _escola_liberada(escola_selecionada):
        # MELHORIA: aqui o clique no cartao ja abria o login. No Flask o
        # codigo da escola voltou a ser exigido, e este frontend ficou para
        # tras -- a mesma porta com duas regras. Pior: o papel entregue aos
        # alunos manda "escolha a escola -> codigo -> usuario e senha", e
        # esta tela nao tinha onde digitar o codigo.
        _formulario_codigo_escola(escola_selecionada)
    elif escola_selecionada:
        _formulario_login(escola_selecionada)
    elif escolas_validas:
        st.info("Clique na sua escola. Depois vêm o código da escola e o seu login.")




def _renderizar_dashboard(dados_escola: dict, ranking: list[dict] | None, ranking_guildas: list[dict] | None):
    escola_id = dados_escola.get("id") if isinstance(dados_escola, dict) else None

    if not escola_id:
        st.error("Não foi possível identificar a escola atual. Faça login novamente.")
        if st.button("Voltar para seleção de escola"):
            st.session_state.pop("escola", None)
            _esquecer_codigo_da_escola()
            st.rerun()
        return

    nome_escola = str(dados_escola.get("nome") or "Escola")
    st.markdown(
        _bloco_html(
            f"""
            <div class="edu-panel-heading">
                <div>
                    <div class="edu-kicker">Escola</div>
                    <div class="edu-panel-title">{_html_seguro(nome_escola)}</div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    # O desenvolvedor entra para administrar, nao para jogar: a home dele sao
    # as duas areas, e nao a vitrine de modos. Os modos continuam alcancaveis
    # pela URL ("?pagina=jogar"), que e como se testa um modo sem criar conta
    # de aluno -- _pagina_permitida nao barra isso, so o ADM e a gestao.
    #
    # Sai ANTES das consultas abaixo: alunos, logs e ranking so alimentam a
    # vitrine e o "missao do dia", que esta home nao desenha.
    if _eh_desenvolvedor():
        _secao_de_cards_navegaveis(
            "Áreas",
            [
                (*CARD_PROFESSOR[:3], "professor", CARD_PROFESSOR[3]),
                (*CARD_ADM[:3], "professor", CARD_ADM[3]),
            ],
            colunas_por_linha=2,
        )
        _secao_de_cards_navegaveis(
            "Sessão",
            [("↔", "Sair", "Encerrar a sessão e voltar para a tela de login.", "professor", _sair_da_conta)],
            colunas_por_linha=2,
        )
        return

    logs = db.buscar_logs(escola_id)
    total_questoes = len(logs or [])
    total_acertos = sum(1 for log in (logs or []) if log.get("resultado") == "Acertou")
    taxa_acerto = int((total_acertos / total_questoes) * 100) if total_questoes else 0

    _secao_de_cards_navegaveis(
        "Área do aluno",
        [
            ("🎮", "Treino Rápido", "Questões em sequência e controle de acertos.", "jogar", "jogar"),
            ("🎓", "ENEM", "Simulados, revisão e desempenho por área.", "enem", "enem"),
            ("🔮", "Desafio do Oráculo", "Desafios por matéria, tema e dificuldade.", "jogar", "jogar"),
            ("🧪", "Laboratório de Exatas", "Fórmulas, resolução guiada e aplicação no dia a dia.", "lab", "laboratorio"),
            ("⚔️", "RPG", "Campanha, chefes, XP, escolhas e recompensas.", "rpg", "rpg"),
            ("🔐", "Escape Room", "Salas em sequência, pistas e relatório final de revisão.", "lab", "escape"),
        ],
    )
    # MELHORIA: ranking e guildas ignoravam as opcoes da escola (RF14). Lidas
    # uma vez aqui, de `dados_escola` -- que app.py ja trouxe atualizada do
    # banco --, para o card, o bloco de ranking e a missao concordarem.
    exibir_ranking = mostra_ranking(dados_escola)
    exibir_guildas = mostra_guildas(dados_escola)

    cards_progressao = [
        ("🧑‍🎓", "Perfil do Aluno", "Badges, pontos, sequência de acertos e desempenho.", "guildas", "jogar"),
        ("📊", "Meu Progresso", "Histórico recente e aproveitamento por matéria.", "enem", "jogar"),
    ]
    if exibir_guildas:
        cards_progressao.append(
            ("🛡️", "Batalha de Guildas", "Duelo semanal entre turmas, participação e acertos.", "guildas", "guildas")
        )
    _secao_de_cards_navegaveis("Progressão", cards_progressao)
    _secao_de_cards_navegaveis(
        "Ajuda",
        [("❓", "Como usar o EducaGame", "Como entrar, o que faz cada modo e o que fazer quando algo parece travado.", "professor", "ajuda")],
        colunas_por_linha=2,
    )

    cards_gestao = []
    if not _eh_aluno():
        cards_gestao.append(
            ("👨‍🏫", "Painel do Professor", "Gestão de alunos, ranking, alertas e acompanhamento dos modos.", "professor", "professor")
        )
    cards_gestao.append(
        ("↔", "Sair", "Encerrar a sessão e voltar para a tela de login.", "professor", _sair_da_conta)
    )
    _secao_de_cards_navegaveis("Gestão", cards_gestao, colunas_por_linha=2)

    if exibir_ranking or exibir_guildas:
        titulo = TITULO_RANKING_HOME[(exibir_ranking, exibir_guildas)]
        st.markdown(f"<div class='edu-home-section-title'>{titulo}</div>", unsafe_allow_html=True)
        st.markdown(
            _ranking_home_html(
                ranking,
                ranking_guildas,
                mostrar_ranking=exibir_ranking,
                mostrar_guildas=exibir_guildas,
            ),
            unsafe_allow_html=True,
        )

    st.markdown(_quem_somos_html(), unsafe_allow_html=True)
    st.markdown(_missao_do_dia_html(total_questoes, taxa_acerto, exibir_ranking), unsafe_allow_html=True)



def renderizar_navegacao(dados_escola: dict | None = None):
    # A escola entra para a tranca das Guildas (_pagina_permitida). Sem ela a
    # pagina fica fechada, nao aberta.
    return _renderizar_sidebar(dados_escola, None, None)


def renderizar_dashboard(dados_escola: dict, ranking: list[dict] | None, ranking_guildas: list[dict] | None):
    _renderizar_dashboard(dados_escola, ranking, ranking_guildas)


def renderizar_voltar_painel():
    _renderizar_voltar_painel()


def selecionar_escola_inicial():
    _selecionar_escola_inicial()
