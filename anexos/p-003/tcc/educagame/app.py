import streamlit as st
import pytz

try:
    from streamlit_javascript import st_javascript
except ModuleNotFoundError:
    def st_javascript(_script: str):
        return None

import services.dados_service as db
from services.rpg_config_service import listar_rpg_configs
import services.relatorios as report
import services.rpg_service as rpg_engine
import st.ui.admin_st as admin_ui
import st.ui.ajuda_st as ajuda_ui
import st.ui.perfil_aluno_st as perfil_ui
import st.ui.tela_boss_rush_enem_st as boss_rush_ui
import st.ui.tela_escape_room_st as escape_room_ui
import st.ui.professor_panel_st as professor_ui
import st.ui.tela_enem_st as enem_ui
import st.ui.tela_guildas_st as guildas_ui
import st.ui.tela_laboratorio_st as laboratorio_ui
import st.ui.tela_oraculo_st as oraculo_ui
import st.ui.tela_rpg_st as rpg_ui
import st.ui.tela_treino_st as treino_ui
from core.config import get_curriculo_por_serie, get_materias_por_serie
from services.escola_service import escola_atualizada, mostra_guildas, mostra_ranking
from st.ui.home_st import (
    aplicar_estilo_global_edugame,
    renderizar_dashboard,
    renderizar_navegacao,
    renderizar_voltar_painel,
    selecionar_escola_inicial,
)
from st.ui.mode_common_st import (
    renderizar_cabecalho_modo,
    renderizar_cards_modo,
    selecionar_aluno,
)


st.set_page_config(page_title="Portal EducaGame IA", layout="wide", page_icon="🎮")

# MELHORIA: o deploy no Streamlit Cloud subiu uma vez sem SUPABASE_URL/KEY --
# tela normal, banco nenhum, e a falha so aparecia ao listar as escolas.
# Isto escreve o diagnostico no log da plataforma logo no boot. Roda uma vez
# por processo, nao a cada rerun.
if "config_verificada" not in st.session_state:
    from core.diagnostico_config import relatar_configuracao

    relatar_configuracao()
    st.session_state.config_verificada = True

aplicar_estilo_global_edugame()

if st.query_params.get("trocar_escola"):
    st.query_params.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

if "user_tz" not in st.session_state:
    try:
        tz_res = st_javascript("""Intl.DateTimeFormat().resolvedOptions().timeZone""")
        st.session_state.user_tz = (
            pytz.timezone(tz_res) if tz_res else pytz.timezone("America/Sao_Paulo")
        )
    except Exception:
        st.session_state.user_tz = pytz.timezone("America/Sao_Paulo")


# MELHORIA: antes bastava ter uma escola na sessao para entrar, e o
# "?escola=slug" da URL preenchia isso sozinho -- ou seja, o link pronto
# dava acesso ao app inteiro sem identificar ninguem. Hoje sao tres portas
# em fila, e nenhuma vem da URL: escolher a unidade, digitar o codigo da
# escola e entao usuario e senha (ver _selecionar_escola_inicial e
# _formulario_codigo_escola em st/ui/home_st.py).
if "usuario" not in st.session_state:
    selecionar_escola_inicial()
    st.stop()

if "escola" not in st.session_state:
    selecionar_escola_inicial()
    st.stop()

ID_ESC = st.session_state.escola["id"]
# MELHORIA: DADOS_ESC era a linha da escola guardada no LOGIN. Quando o
# professor desligava mostrar_ranking ou modo_guilda, o aluno ja logado
# seguia vendo ranking e guildas ate sair -- e o proprio painel do professor
# voltava a desenhar o interruptor na posicao antiga depois de salvar. Agora
# a escola vem do banco a cada execucao; se a leitura falhar, vale a da sessao.
DADOS_ESC = escola_atualizada(ID_ESC, reserva=st.session_state.escola)
USUARIO = st.session_state.usuario
EH_ALUNO = USUARIO.get("role") == "aluno"
aplicar_estilo_global_edugame(DADOS_ESC.get("cor_tema", "#f4c76a"))

# RF14: com a opcao desligada, a classificacao nem e consultada.
ranking = []
if mostra_ranking(DADOS_ESC):
    try:
        ranking = db.buscar_ranking(ID_ESC)
    except Exception:
        ranking = []

ranking_guildas = []
if mostra_guildas(DADOS_ESC):
    try:
        ranking_guildas = db.buscar_ranking_guildas(ID_ESC)
    except Exception:
        ranking_guildas = []

pagina = renderizar_navegacao(DADOS_ESC)


if pagina == "🏠 Início":
    renderizar_dashboard(DADOS_ESC, ranking, ranking_guildas)

elif pagina == "🎮 Jogar":
    renderizar_voltar_painel()
    renderizar_cabecalho_modo("🏛️ Desafio do Oráculo")
    renderizar_cards_modo([
        {
            "icone": "🔮",
            "titulo": "Oráculo",
            "texto": "Questões geradas por tema, série e dificuldade, com explicação ao final.",
            "tags": ["IA", "BNCC", "feedback"],
            "variante": "jogar",
        },
        {
            "icone": "🎯",
            "titulo": "Modo Treino",
            "texto": "Sequências curtas de questões para praticar, errar rápido e corrigir o raciocínio.",
            "tags": ["sessão", "progresso", "reforço"],
            "variante": "enem",
        },
        {
            "icone": "🏅",
            "titulo": "Perfil",
            "texto": "Conquistas, histórico e evolução do aluno em um painel simples de acompanhar.",
            "tags": ["badges", "ranking", "evolução"],
            "variante": "guildas",
        },
    ])
    alunos = db.buscar_alunos(ID_ESC)
    al_obj = selecionar_aluno(alunos, "Quem aceita o desafio?", "jogar_aluno")
    if al_obj:
        curriculo = get_curriculo_por_serie(al_obj["ano_escolar"])
        materias = get_materias_por_serie(al_obj["ano_escolar"])
        aba_oraculo, aba_treino, aba_perfil = st.tabs(
            ["🔮 Oráculo", "🎯 Modo Treino", "🏅 Perfil & Conquistas"]
        )
        with aba_oraculo:
            oraculo_ui.renderizar_aba_oraculo(al_obj, ID_ESC, curriculo)
        with aba_treino:
            treino_ui.renderizar_aba_treino(al_obj, ID_ESC, materias)
        with aba_perfil:
            try:
                logs_raw = db.buscar_logs(ID_ESC)
                logs_aluno = [
                    r for r in (logs_raw or []) if r.get("aluno_id") == al_obj["id"]
                ]
                perfil_ui.renderizar_perfil_aluno(al_obj, logs_aluno)
            except Exception as e:
                st.warning(f"Não foi possível carregar o perfil: {e}")

elif pagina == "🎓 ENEM":
    renderizar_voltar_painel()
    renderizar_cabecalho_modo(
        "🎓 Simulado ENEM",
        "Configure o simulado e acompanhe o desempenho do aluno nas áreas do exame.",
    )
    alunos = db.buscar_alunos(ID_ESC)
    al_obj = selecionar_aluno(alunos, "Quem vai fazer o simulado?", "enem_aluno")
    if al_obj:
        enem_ui.tela_enem(aluno=al_obj, escola=DADOS_ESC, db=db)
    else:
        st.info(
            "Nenhum aluno cadastrado ainda. Acesse o painel do professor para fazer a matrícula antes de iniciar o simulado."
        )

elif pagina == "👑 Boss Rush":
    renderizar_voltar_painel()
    renderizar_cabecalho_modo(
        "👑 Boss Rush ENEM",
        "Enfrente chefes por area BNCC: acertos tiram coracoes do boss, erros tiram suas vidas.",
    )
    alunos = db.buscar_alunos(ID_ESC)
    al_obj = selecionar_aluno(alunos, "Quem vai enfrentar os bosses?", "boss_rush_aluno")
    if al_obj:
        boss_rush_ui.renderizar_tela_boss_rush_enem(aluno=al_obj, escola=DADOS_ESC, db=db)
    else:
        st.info(
            "Nenhum aluno cadastrado ainda. Acesse o painel do professor para fazer a matrícula antes de iniciar o Boss Rush."
        )

elif pagina == "🔐 Escape Room":
    renderizar_voltar_painel()
    renderizar_cabecalho_modo(
        "🔐 Escape Room",
        "Monte salas por materia, escolha temas opcionais e transforme a jornada em relatorio PDF.",
    )
    alunos = db.buscar_alunos(ID_ESC)
    al_obj = selecionar_aluno(alunos, "Quem vai tentar escapar?", "escape_room_aluno")
    if al_obj:
        curriculo = get_curriculo_por_serie(al_obj["ano_escolar"])
        materias = get_materias_por_serie(al_obj["ano_escolar"])
        escape_room_ui.renderizar_tela_escape_room(aluno=al_obj, escola=DADOS_ESC, materias=materias)
    else:
        st.info(
            "Nenhum aluno cadastrado ainda. Acesse o painel do professor para fazer a matricula antes de iniciar o Escape Room."
        )

elif pagina == "🛡️ Guildas":
    renderizar_voltar_painel()
    renderizar_cabecalho_modo(
        "🛡️ Duelo de Guildas",
        "Turmas competem por pontos, acertos e participação semanal.",
    )
    guildas_ui.renderizar_tela_guildas(ID_ESC, db, DADOS_ESC)

elif pagina == "⚔️ RPG":
    renderizar_voltar_painel()
    rpg_ui.renderizar_tela_rpg(
        escola_id=ID_ESC,
        dados_escola=DADOS_ESC,
        db_repo=db,
        report_service=report,
        rpg_engine=rpg_engine,
        listar_rpg_configs_fn=listar_rpg_configs,
    )

elif pagina == "🧪 Laboratório":
    renderizar_voltar_painel()
    alunos_data = db.buscar_alunos(ID_ESC)
    laboratorio_ui.renderizar_tela_laboratorio(ID_ESC, alunos_data)

elif pagina == "❓ Ajuda":
    renderizar_voltar_painel()
    # Sem checagem de papel: a ajuda e para todo mundo, e o proprio
    # secoes_da_ajuda ja decide o que mostrar a professor e o que nao.
    ajuda_ui.renderizar_tela_ajuda()

elif pagina == "🏛️ ADM":
    renderizar_voltar_painel()
    # Segunda tranca, igual a do painel de gestao logo abaixo: a navegacao ja
    # recusa "?pagina=adm" para quem nao e desenvolvedor, mas o ADM cria e
    # apaga escolas e redefine senhas -- a checagem vale nos dois lugares.
    if USUARIO.get("role") != "desenvolvedor":
        st.warning("Esta área é restrita ao desenvolvedor.")
    else:
        admin_ui.tela_administrador()

else:
    renderizar_voltar_painel()
    # Segunda tranca: a navegacao ja recusa a pagina de gestao para aluno
    # (ver _pagina_permitida em st/ui/home_st.py), mas o painel expoe dados
    # da turma inteira -- vale checar tambem no ponto onde ele e desenhado.
    if EH_ALUNO:
        st.warning("Esta area e restrita a professores e a coordenacao.")
    else:
        professor_ui.renderizar_painel_professor(
            ID_ESC, DADOS_ESC, st.session_state.user_tz
        )
