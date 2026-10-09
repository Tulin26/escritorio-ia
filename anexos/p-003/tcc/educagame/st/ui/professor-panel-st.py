import pandas as pd
import plotly.express as px
import streamlit as st

import services.dados_service as db
from services.aluno_service import MENSAGENS_DA_MATRICULA, registrar_matricula
from services.escola_service import MENSAGENS_DAS_PREFERENCIAS, salvar_preferencias
from services.usuario_service import (
    agrupar_professores_por_escola,
    listar_professores_visiveis,
)
from services.rpg_config_service import (
    MENSAGENS_DA_AVENTURA,
    excluir_aventura,
    listar_rpg_configs,
    salvar_aventura,
)
import services.relatorios as report
from core.config import exibir_materia, get_materias_por_serie, normalizar_materia
from st.ui.professor_analises_st import renderizar_aba_analises

# MELHORIA: st.rerun() recomeca a tela na hora, entao o st.success que vinha
# logo antes dele sumia antes de alguem ler. O aviso atravessa o rerun
# guardado na sessao -- uma chave por aba, porque todas as abas sao desenhadas
# a cada execucao e, com uma chave so, o aviso sairia na primeira que olhasse.
_CHAVE_AVENTURA_SALVA = "aventura_salva"
_CHAVE_MATRICULA_FEITA = "matricula_feita"
_CHAVE_PREFERENCIAS_SALVAS = "preferencias_salvas"


def _sucesso_depois_do_rerun(chave: str, texto: str) -> None:
    st.session_state[chave] = texto
    st.rerun()


def _mostrar_sucesso_guardado(chave: str) -> None:
    texto = st.session_state.pop(chave, None)
    if texto:
        st.success(texto)


def _renderizar_aba_rpg_config(escola_id):
    st.subheader("⚔️ Configurar Aventura RPG")
    st.markdown("Configure o cenário que a IA usará para narrar a aventura dos alunos.")
    _mostrar_sucesso_guardado(_CHAVE_AVENTURA_SALVA)

    try:
        todas_aventuras = listar_rpg_configs(escola_id)
    except Exception as e:
        st.error(f"Erro ao buscar aventuras: {e}")
        todas_aventuras = []

    if todas_aventuras:
        opcoes_aventuras = ["➕ Criar nova aventura"] + [f"{a.get('titulo', 'Sem título')} (ID: {a['id'][:8]}...)" for a in todas_aventuras]
        aventura_selecionada = st.selectbox("📖 Selecionar aventura para editar:", options=opcoes_aventuras, key="selecionar_aventura")
        if aventura_selecionada == "➕ Criar nova aventura":
            cfg_atual = {}
            editando = False
        else:
            idx = opcoes_aventuras.index(aventura_selecionada) - 1
            cfg_atual = todas_aventuras[idx]
            editando = True
            st.info(f"✏️ Editando aventura: **{cfg_atual.get('titulo', 'Sem título')}**")
    else:
        st.info("📝 Nenhuma aventura cadastrada. Crie a primeira abaixo!")
        cfg_atual = {}
        editando = False

    series = ["6º Ano", "7º Ano", "8º Ano", "9º Ano", "1º Ano EM", "2º Ano EM", "3º Ano EM"]
    materias = ["Matemática", "Física", "Química", "Biologia", "Português", "História", "Geografia", "Inglês", "Arte", "Educação Física", "Filosofia", "Sociologia", "Ensino Religioso", "Ciências"]

    with st.form("form_rpg_config", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            titulo = st.text_input("📖 Título da Aventura", value=cfg_atual.get("titulo", ""), placeholder="Ex: O Cristal do Conhecimento")
            heroi_nome = st.text_input("🦸 Nome do Herói/Classe", value=cfg_atual.get("heroi_nome", ""), placeholder="Ex: Mago Sábio, Guerreiro das Equações")
            poderes = st.text_input("⚡ Poderes do Herói", value=cfg_atual.get("poderes", ""), placeholder="Ex: Feitiços matemáticos, Escudo de fórmulas")
        with col2:
            serie_idx = series.index(cfg_atual["serie"]) if cfg_atual.get("serie") in series else 3
            serie_base = cfg_atual.get("serie") if cfg_atual.get("serie") in series else series[serie_idx]
            materias = [exibir_materia(materia) for materia in get_materias_por_serie(serie_base)]
            materia_atual = exibir_materia(normalizar_materia(cfg_atual.get("materia", "")))
            mat_idx = materias.index(materia_atual) if materia_atual in materias else 0
            materia = st.selectbox("📚 Matéria Integrada", materias, index=mat_idx)
            serie = st.selectbox("🎓 Série Alvo", series, index=serie_idx)

        cenario = st.text_area("🗺️ Cenário da Aventura", value=cfg_atual.get("cenario", ""), height=80)
        objetivo_final = st.text_area("🎯 Objetivo Final da Missão", value=cfg_atual.get("objetivo_final", ""), height=60)
        descricao = st.text_area("📝 Descrição curta (para aluno)", value=cfg_atual.get("descricao", ""), height=60)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Salvar Aventura", width="stretch"):
                # MELHORIA: o retorno da gravacao era ignorado, e ela nunca
                # levanta excecao (devolve None) -- o `except` daqui era
                # codigo morto e a tela dizia "salva" com o banco fora do ar.
                ok, motivo = salvar_aventura(
                    escola_id,
                    cfg_atual.get("id"),
                    {
                        "titulo": titulo,
                        "heroi_nome": heroi_nome,
                        "poderes": poderes,
                        "materia": materia,
                        "serie": serie,
                        "cenario": cenario,
                        "objetivo_final": objetivo_final,
                        "descricao": descricao,
                    },
                )
                if ok:
                    _sucesso_depois_do_rerun(
                        _CHAVE_AVENTURA_SALVA,
                        f"✅ Aventura **{titulo.strip()}** atualizada com sucesso!"
                        if cfg_atual.get("id")
                        else f"✅ Nova aventura **{titulo.strip()}** criada com sucesso!",
                    )
                else:
                    st.error(MENSAGENS_DA_AVENTURA[motivo])
        with col_btn2:
            if editando and st.form_submit_button("🗑️ Excluir Aventura", width="stretch"):
                st.session_state.confirmar_exclusao = cfg_atual["id"]
                st.rerun()

    if st.session_state.get("confirmar_exclusao"):
        aventura_id = st.session_state.confirmar_exclusao
        aventura_titulo = next((a.get("titulo") for a in todas_aventuras if a.get("id") == aventura_id), "esta aventura")
        st.warning(f"⚠️ Tem certeza que deseja excluir **{aventura_titulo}**?")
        col_sim, col_nao = st.columns(2)
        with col_sim:
            if st.button("✅ Sim, excluir", width="stretch"):
                # MELHORIA: excluia pelo id sozinho. A confirmacao fica na
                # sessao e sobrevive a troca de escola (o desenvolvedor abre
                # outra unidade com ela pendente): o "Sim" apagaria a aventura
                # da escola anterior. Ver repositories/rpg_config_repo.py.
                excluiu, motivo = excluir_aventura(escola_id, aventura_id)
                if excluiu:
                    del st.session_state.confirmar_exclusao
                    _sucesso_depois_do_rerun(
                        _CHAVE_AVENTURA_SALVA, f"Aventura **{aventura_titulo}** excluída com sucesso!"
                    )
                else:
                    # a confirmacao continua aberta: tentar de novo ou cancelar
                    st.error(MENSAGENS_DA_AVENTURA[motivo])
        with col_nao:
            if st.button("❌ Cancelar", width="stretch"):
                del st.session_state.confirmar_exclusao
                st.rerun()

    if todas_aventuras:
        st.markdown("---")
        st.subheader("📚 Aventuras disponíveis")
        for aventura in todas_aventuras:
            with st.expander(f"🎮 {aventura.get('titulo', 'Sem título')}"):
                st.markdown(f"**📖 Descrição:** {aventura.get('descricao', '-')}")
                st.markdown(f"**📚 Matéria:** {aventura.get('materia', '-')}")
                st.markdown(f"**🎓 Série:** {aventura.get('serie', '-')}")
                st.markdown(f"**🦸 Herói:** {aventura.get('heroi_nome', '-')}")
                st.markdown(f"**⚡ Poderes:** {aventura.get('poderes', '-')}")
                st.markdown(f"**🗺️ Cenário:** {aventura.get('cenario', '-')[:200]}...")
                st.caption(f"🆔 ID: {aventura['id']} | 📅 Criado em: {aventura.get('created_at', '-')[:10]}")


def _renderizar_aba_matricula(escola_id):
    st.subheader("📝 Matrícula de Novo Aluno")
    tipo = st.radio("Tipo de Ensino", ["Ensino Fundamental", "Ensino Médio"], horizontal=True)
    series_opcoes = ["6º Ano", "7º Ano", "8º Ano", "9º Ano"] if tipo == "Ensino Fundamental" else ["1º Ano EM", "2º Ano EM", "3º Ano EM"]
    serie = st.selectbox("Série/Ano", series_opcoes)
    periodo = st.selectbox("Período", ["Manhã", "Tarde", "Noite"])
    _mostrar_sucesso_guardado(_CHAVE_MATRICULA_FEITA)
    with st.form("mat_heroi", clear_on_submit=True):
        nome = st.text_input("Nome Completo *")
        ra = st.text_input("RA / Identificação *")
        ensino_religioso = st.checkbox("Optar por cursar Ensino Religioso (facultativo)")
        if st.form_submit_button("Finalizar Matrícula"):
            # MELHORIA: o retorno de criar_aluno era ignorado, e ele nunca
            # levanta excecao (devolve None) -- o `except` daqui era codigo
            # morto e a tela dizia "matriculado" com RA repetido ou banco
            # fora do ar. Nome ou RA em branco nao dava aviso nenhum.
            ok, motivo = registrar_matricula(
                escola_id=escola_id,
                nome=nome,
                ra_identificacao=ra,
                ano_escolar=serie,
                periodo=periodo,
                ensino_religioso=ensino_religioso,
            )
            if ok:
                _sucesso_depois_do_rerun(
                    _CHAVE_MATRICULA_FEITA, f"✅ Aluno **{nome.strip()}** matriculado no **{serie}**!"
                )
            else:
                st.error(MENSAGENS_DA_MATRICULA[motivo])


def _renderizar_aba_ranking(escola_id):
    st.subheader("🏆 Ranking dos Alunos")
    st.markdown("Consulte os melhores desempenhos por série/ano.")
    alunos_ranking = db.buscar_alunos(escola_id)
    series_opcoes = sorted({str(aluno.get("ano_escolar", "")).strip() for aluno in alunos_ranking if str(aluno.get("ano_escolar", "")).strip()})
    serie_selecionada = st.selectbox("📚 Filtrar por Série/Ano:", options=["Todas as séries"] + series_opcoes, key="filtro_serie_ranking")
    if not alunos_ranking:
        st.info("Nenhum aluno cadastrado na escola.")
        return
    alunos_filtrados = [a for a in alunos_ranking if serie_selecionada == "Todas as séries" or a.get("ano_escolar", "") == serie_selecionada]
    if not alunos_filtrados:
        st.warning(f"Nenhum aluno encontrado para a série: {serie_selecionada}")
        return

    logs_ranking = db.buscar_logs(escola_id)
    ranking_data = []
    for aluno in alunos_filtrados:
        logs_aluno = [log for log in logs_ranking if log.get("aluno_id") == aluno["id"]] if logs_ranking else []
        total_questoes = len(logs_aluno)
        acertos = sum(1 for log in logs_aluno if log.get("resultado") == "Acertou")
        percentual = int(acertos / total_questoes * 100) if total_questoes > 0 else 0
        pontuacao = int(aluno.get("pontos_totais") or 0)
        ranking_data.append({"nome": aluno["nome"], "serie": aluno.get("ano_escolar", ""), "total": total_questoes, "acertos": acertos, "percentual": percentual, "pontuacao": pontuacao})

    ranking_data.sort(key=lambda x: x["pontuacao"], reverse=True)
    top_10 = ranking_data[:10]
    if not top_10:
        st.info("Nenhum aluno encontrado para exibir no ranking.")
        return

    st.markdown("---")
    for pos, aluno in enumerate(top_10, 1):
        medalha, cor = ("🥇", "#FFD700") if pos == 1 else ("🥈", "#C0C0C0") if pos == 2 else ("🥉", "#CD7F32") if pos == 3 else (f"{pos}º", "#3498db")
        col1, col2, col3, col4, col5 = st.columns([1, 3, 1.5, 1.5, 1.5])
        with col1:
            st.markdown(f"<h2 style='color:{cor}; margin:0'>{medalha}</h2>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"**{aluno['nome']}**")
            st.caption(f"{aluno['serie']}")
        with col3:
            st.metric("📝 Questões", aluno["total"])
        with col4:
            st.metric("✅ Acertos", aluno["acertos"], delta=f"{aluno['percentual']}%")
        with col5:
            st.metric("🏆 Pontos", aluno["pontuacao"])
        st.markdown("---")

    st.markdown("### 📊 Comparativo de Pontuação")
    df_rank = pd.DataFrame(top_10)
    df_rank["nome_curto"] = df_rank["nome"].apply(lambda x: x[:15] + "..." if len(x) > 15 else x)
    fig = px.bar(
        df_rank,
        x="nome_curto",
        y="pontuacao",
        text="pontuacao",
        title=f"Top 10 Alunos - {serie_selecionada}",
        color="pontuacao",
        color_continuous_scale="Viridis",
        labels={"nome_curto": "Aluno", "pontuacao": "Pontuação Total"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, width="stretch")


# Quanto cada barra ocupa, e o piso para não achatar uma turma de dois.
PIXELS_POR_BARRA = 26
ALTURA_MINIMA_DO_GRAFICO = 320

# A altura dos gráficos de turma grande, que não crescem com a turma -- é o
# ponto deles.
ALTURA_CONSTANTE = 380

# Acima disto, uma barra por aluno deixa de caber e de servir. Não é estética:
# com 100 alunos a barra horizontal daria 26 x 100 = 2.600px de altura, e a
# vertical empilharia 100 nomes ilegíveis no eixo. Os dois formatos falham,
# porque a pergunta muda de tamanho junto com a turma.
MAX_ALUNOS_NO_GRAFICO = 15

# Quantos mostrar quando a turma é grande. Dez cabe na tela e é quanto um
# professor consegue de fato acompanhar de perto numa semana.
QUANTOS_PRECISAM_DE_ATENCAO = 10

FAIXAS_DE_APROVEITAMENTO = (
    (0, 25, "0–25%"),
    (25, 50, "25–50%"),
    (50, 75, "50–75%"),
    (75, 101, "75–100%"),
)


def faixas_de_aproveitamento(df_responderam) -> list[tuple[str, int]]:
    """Quantos alunos em cada faixa de acerto.

    O gráfico que serve a uma turma de 100: tamanho constante, e responde a
    pergunta que o professor faz de verdade -- "como está a turma?" --, que
    cem barras individuais não respondem.

    A última faixa vai até 101 porque 100% é aproveitamento válido e ficaria
    de fora de um `< 100`.
    """
    contagem = []
    for minimo, maximo, rotulo in FAIXAS_DE_APROVEITAMENTO:
        alunos = df_responderam[
            (df_responderam["%"] >= minimo) & (df_responderam["%"] < maximo)
        ]
        contagem.append((rotulo, len(alunos)))
    return contagem


def precisam_de_atencao(df_responderam, limite: int = QUANTOS_PRECISAM_DE_ATENCAO):
    """Os de menor aproveitamento, do pior para o melhor.

    A outra pergunta do professor -- "quem eu preciso olhar?" -- e a única
    que leva a uma ação. Uma lista de dez é acionável; cem barras não são.
    """
    return df_responderam.sort_values("%", ascending=True).head(limite)


def separar_quem_respondeu(df_turma):
    """(quem tem resposta, quantos ficaram de fora).

    O gráfico de desempenho plotava TODO MUNDO, e "não respondeu" saía
    desenhado como "acertou 0%" -- em vermelho, na escala vermelho→verde, que
    é a cor de quem vai mal. Visto no painel da ETEC: 43 das 45 barras eram
    alunos sem nenhuma resposta, e os dois com dado sumiam no meio.

    A guarda já existia em três lugares (o alerta de baixo desempenho, o
    destaque da tabela e o gráfico de tempo ao lado). Faltava só no gráfico
    de desempenho -- e era também o motivo de os dois gráficos lado a lado
    mostrarem populações diferentes.

    Fora do render de propósito: dá para testar sem montar meia tela de
    Streamlit, e é a decisão que importa aqui.
    """
    respondeu = df_turma[df_turma["Total"] > 0]
    return respondeu, len(df_turma) - len(respondeu)


def filtrar_turma(resumo_turma, serie: str, periodo: str) -> list[dict]:
    """Os alunos que passam pelos dois filtros da tela.

    Fora do render porque é decisão, não desenho: "Todas" e "Todos" querem
    dizer *não filtrar*, e isso dá para conferir sem montar meia tela de
    Streamlit.
    """
    return [
        a
        for a in resumo_turma
        if (serie == "Todas" or a["ano_escolar"] == serie)
        and (periodo == "Todos" or a["periodo"] == periodo)
    ]


def metricas_da_turma(dados_filtrados) -> dict:
    """Os quatro números do topo da aba.

    O tempo médio só conta quem tem tempo medido. Somar os zeros de quem
    nunca respondeu puxaria a média para baixo e faria a tela mentir do mesmo
    jeito que o gráfico mentia ao desenhar "não respondeu" como "acertou 0%".
    """
    total_questoes = sum(a["total_questoes"] for a in dados_filtrados)
    total_acertos = sum(a["acertos"] for a in dados_filtrados)
    tempos = [
        a.get("tempo_medio_resposta", 0)
        for a in dados_filtrados
        if isinstance(a.get("tempo_medio_resposta", 0), (int, float))
        and a.get("tempo_medio_resposta", 0) > 0
    ]
    return {
        "total_alunos": len(dados_filtrados),
        "total_questoes": total_questoes,
        "media_turma": int(total_acertos / total_questoes * 100) if total_questoes > 0 else 0,
        "tempo_medio_turma": round(sum(tempos) / len(tempos), 1) if tempos else 0,
    }


# (campo que vem da view, rótulo que o professor lê na tela)
COLUNAS_DA_TABELA = (
    ("nome", "Aluno"),
    ("ano_escolar", "Série"),
    ("periodo", "Período"),
    ("total_questoes", "Total"),
    ("acertos", "Acertos"),
    ("erros", "Erros"),
    ("percentual", "%"),
    ("tempo_medio_resposta", "Tempo Médio (s)"),
)


def tabela_por_aluno(dados_filtrados) -> pd.DataFrame:
    """A tabela da tela, já com os nomes de coluna que o professor lê.

    Campo que a view não trouxe entra como 0: é melhor a tabela aparecer com
    uma coluna vazia do que a aba inteira sumir num KeyError.
    """
    df = pd.DataFrame(dados_filtrados)
    for campo, _rotulo in COLUNAS_DA_TABELA:
        if campo not in df.columns:
            df[campo] = 0
    df = df[[campo for campo, _rotulo in COLUNAS_DA_TABELA]]
    df.columns = [rotulo for _campo, rotulo in COLUNAS_DA_TABELA]
    return df


def _desenhar_filtros(resumo_turma):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        series_disponiveis = sorted(set(a["ano_escolar"] for a in resumo_turma))
        serie_filtro = st.selectbox("🎓 Filtrar por Série:", ["Todas"] + series_disponiveis)
    with col_f2:
        periodos_disponiveis = sorted(set(a["periodo"] for a in resumo_turma if a["periodo"]))
        periodo_filtro = st.selectbox("⏰ Filtrar por Período:", ["Todos"] + periodos_disponiveis)
    return filtrar_turma(resumo_turma, serie_filtro, periodo_filtro)


def _desenhar_metricas(metricas):
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("👨‍🎓 Alunos", metricas["total_alunos"])
    col_m2.metric("📝 Questões", metricas["total_questoes"])
    col_m3.metric("✅ Média da Turma", f"{metricas['media_turma']}%")
    col_m4.metric("⏱️ Tempo Médio", f"{metricas['tempo_medio_turma']} seg")
    st.markdown("---")


def _desenhar_alerta_de_baixo_desempenho(dados_filtrados) -> list[dict]:
    """Avisa na tela e devolve a lista -- o PDF leva a mesma."""
    alunos = [a for a in dados_filtrados if a.get("baixo_desempenho", False)]
    if alunos:
        st.error(f"⚠️ **ALERTA! {len(alunos)} alunos com baixo desempenho** (menos de 50% de acerto)")
        for aluno in alunos:
            st.warning(f"🔴 **{aluno['nome']}** - {aluno['ano_escolar']} - {aluno['percentual']}% de acerto ({aluno['acertos']}/{aluno['total_questoes']}) - Tempo médio: {aluno.get('tempo_medio_resposta', 0)}s")
        st.markdown("---")
    return alunos


def _desenhar_tabela(dados_filtrados) -> pd.DataFrame:
    st.markdown("### 📊 Detalhamento por Aluno")
    df_turma = tabela_por_aluno(dados_filtrados)

    def destacar_baixo_desempenho(row):
        try:
            if row["%"] < 50 and row["Total"] >= 5:
                return ["background-color: #ffcccc"] * len(row)
        except Exception:
            pass
        return [""] * len(row)

    st.dataframe(df_turma.style.apply(destacar_baixo_desempenho, axis=1), width="stretch", height=400)
    st.markdown("---")
    return df_turma


def _barra_horizontal(df, coluna, titulo, escala, altura, faixa_de_cor=None):
    """Uma barra por aluno, deitada.

    Deitada porque em pé os nomes saem rotacionados e ilegíveis. Os três
    gráficos por aluno desta aba têm exatamente esta forma -- muda a coluna, a
    escala de cor e a altura.
    """
    fig = px.bar(
        df, x=coluna, y="Aluno", orientation="h", title=titulo,
        color=coluna, color_continuous_scale=escala,
        range_color=faixa_de_cor, text=coluna,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=altura)
    st.plotly_chart(fig, width="stretch")


def _altura_por_aluno(quantos: int) -> int:
    """Cresce com a turma, com um piso para não achatar uma turma de dois."""
    return max(ALTURA_MINIMA_DO_GRAFICO, PIXELS_POR_BARRA * quantos)


def _graficos_aluno_a_aluno(df_responderam):
    """Turma pequena: uma barra por aluno cabe e é o mais informativo."""
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        df_grafico = df_responderam.sort_values("%", ascending=True)
        _barra_horizontal(
            df_grafico, "%", "Desempenho por Aluno (%)",
            ["red", "yellow", "green"], _altura_por_aluno(len(df_grafico)),
            faixa_de_cor=[0, 100],
        )
    with col_g2:
        df_tempo = df_responderam[df_responderam["Tempo Médio (s)"] > 0]
        if df_tempo.empty:
            st.info("Nenhum dado de tempo de resposta disponível")
        else:
            df_tempo = df_tempo.sort_values("Tempo Médio (s)", ascending=True)
            _barra_horizontal(
                df_tempo, "Tempo Médio (s)", "Tempo Médio de Resposta (segundos)",
                "Blues", _altura_por_aluno(len(df_tempo)),
            )


def _graficos_de_turma_grande(df_responderam):
    """Turma grande: uma barra por aluno para de responder qualquer pergunta.

    Com 100 alunos seriam 2.600px de altura deitado, ou 100 nomes ilegíveis em
    pé. Aqui os dois gráficos têm tamanho CONSTANTE e respondem as duas
    perguntas que o professor faz de verdade: "como vai a turma?" e "quem eu
    preciso olhar?".
    """
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        faixas = faixas_de_aproveitamento(df_responderam)
        df_faixas = pd.DataFrame(faixas, columns=["Faixa", "Alunos"])
        fig_dist = px.bar(
            df_faixas, x="Faixa", y="Alunos",
            title=f"Distribuição do aproveitamento ({len(df_responderam)} alunos)",
            color="Faixa",
            color_discrete_sequence=["#d62728", "#ff7f0e", "#bcbd22", "#2ca02c"],
            text="Alunos",
        )
        fig_dist.update_traces(textposition="outside")
        fig_dist.update_layout(height=ALTURA_CONSTANTE, showlegend=False)
        st.plotly_chart(fig_dist, width="stretch")
    with col_g2:
        df_atencao = precisam_de_atencao(df_responderam)
        _barra_horizontal(
            df_atencao.sort_values("%", ascending=False), "%",
            f"Precisam de atenção — {len(df_atencao)} menores",
            ["red", "yellow", "green"], ALTURA_CONSTANTE, faixa_de_cor=[0, 100],
        )
    st.caption(
        f"Turma com mais de {MAX_ALUNOS_NO_GRAFICO} alunos: o gráfico por aluno vira "
        "uma parede de barras. A tabela acima tem todos, um a um, e o PDF também."
    )


def _desenhar_graficos(df_turma):
    # Quem nunca respondeu fica de fora do gráfico: o porquê está em
    # `separar_quem_respondeu`, junto do defeito que isto conserta.
    df_responderam, sem_resposta = separar_quem_respondeu(df_turma)

    if df_responderam.empty:
        st.info("Nenhum aluno respondeu questões ainda.")
    elif len(df_responderam) <= MAX_ALUNOS_NO_GRAFICO:
        _graficos_aluno_a_aluno(df_responderam)
    else:
        _graficos_de_turma_grande(df_responderam)

    if sem_resposta and not df_responderam.empty:
        # Dizer quantos ficaram de fora, senão o gráfico passa a esconder
        # informação em vez de mostrar -- o professor precisa saber que a
        # turma é maior que o gráfico.
        st.caption(
            f"{sem_resposta} aluno(s) fora do gráfico por ainda não terem respondido. "
            "Eles aparecem na tabela acima."
        )


def _desenhar_botao_do_pdf(dados_escola, dados_filtrados, metricas, alunos_baixo_desempenho):
    st.markdown("---")
    if st.button("📥 Baixar Relatório da Turma (PDF)", width="stretch"):
        with st.spinner("Gerando relatório da turma..."):
            pdf_bytes = report.gerar_pdf_relatorio_turma(
                nome_escola=dados_escola.get("nome", "EduGame"),
                dados_turma=dados_filtrados,
                total_questoes=metricas["total_questoes"],
                media_turma=metricas["media_turma"],
                tempo_medio_turma=metricas["tempo_medio_turma"],
                alunos_baixo_desempenho=alunos_baixo_desempenho,
            )
            st.download_button(
                label="✅ Clique aqui para baixar o PDF",
                data=pdf_bytes,
                file_name=f"Relatorio_Turma_{dados_escola.get('nome', 'Escola').replace(' ', '_')}.pdf",
                mime="application/pdf",
                width="stretch",
            )


def _renderizar_aba_resumo_turma(escola_id, dados_escola):
    st.subheader("📋 Resumo da Turma")
    st.markdown("Visão geral do desempenho de todos os alunos")
    resumo_turma = db.buscar_resumo_turma(escola_id)
    if not resumo_turma:
        st.info("Nenhum dado disponível. Os alunos precisam responder algumas questões primeiro.")
        return

    dados_filtrados = _desenhar_filtros(resumo_turma)
    if not dados_filtrados:
        st.info("Nenhum aluno encontrado com os filtros selecionados.")
        return

    metricas = metricas_da_turma(dados_filtrados)
    _desenhar_metricas(metricas)
    alunos_baixo_desempenho = _desenhar_alerta_de_baixo_desempenho(dados_filtrados)
    df_turma = _desenhar_tabela(dados_filtrados)
    _desenhar_graficos(df_turma)
    _desenhar_botao_do_pdf(dados_escola, dados_filtrados, metricas, alunos_baixo_desempenho)




def _renderizar_aba_configuracoes(escola_id, dados_escola):
    st.subheader("⚙️ Configurações")
    _mostrar_sucesso_guardado(_CHAVE_PREFERENCIAS_SALVAS)
    ri = st.toggle("Habilitar Ranking Individual (Top 5 Heróis)", value=dados_escola.get("mostrar_ranking", True))
    rg = st.toggle("Habilitar Batalha de Guildas", value=dados_escola.get("modo_guilda", True))
    if st.button("💾 Salvar Preferências"):
        # MELHORIA: "Configurações salvas!" saia sem olhar o retorno.
        ok, motivo = salvar_preferencias(escola_id, mostrar_ranking=ri, modo_guilda=rg)
        if ok:
            _sucesso_depois_do_rerun(_CHAVE_PREFERENCIAS_SALVAS, "Configurações salvas!")
        else:
            st.error(MENSAGENS_DAS_PREFERENCIAS[motivo])


def _renderizar_aba_professores():
    """Quem sao os professores cadastrados, e em que escola cada um entra.

    Quem ve o que nao e decidido aqui: a regra mora em
    services/usuario_service.py::listar_professores_visiveis, porque e a mesma
    pergunta que conta_pode_entrar responde no login -- desenvolvedor enxerga
    todas as escolas, professor so a propria.
    """
    st.subheader("👥 Professores cadastrados")

    try:
        professores = listar_professores_visiveis(st.session_state.get("usuario"))
    except Exception as erro:  # noqa: BLE001
        st.error(f"Não foi possível listar os professores: {erro}")
        return

    if not professores:
        st.info("Nenhum professor cadastrado ainda.")
        st.caption("Contas de login são criadas no ADM, pelo desenvolvedor.")
        return

    grupos = agrupar_professores_por_escola(professores)
    sem_vinculo = [c for c in professores if c.get("sem_vinculo")]
    if sem_vinculo:
        # Nao e detalhe de cadastro: professor sem escola NAO ENTRA em lugar
        # nenhum (services/auth_service.py::conta_pode_entrar).
        st.warning(
            f"{len(sem_vinculo)} conta(s) de professor sem escola — elas não conseguem entrar. "
            "Vincule pelo ADM, em Contas de login."
        )

    for nome_escola, contas in grupos:
        st.markdown(f"**{nome_escola}** — {len(contas)} professor(es)")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Usuário": c.get("username", ""),
                        "Situação": (
                            "não entra: sem escola"
                            if c.get("sem_vinculo")
                            else ("ativa" if c.get("ativo", True) else "desativada")
                        ),
                    }
                    for c in contas
                ]
            ),
            width="stretch",
            hide_index=True,
        )


def renderizar_painel_professor(escola_id, dados_escola, user_tz):
    st.title("👨‍🏫 Painel de Gestão")

    # MELHORIA: a aba ADM era desenhada para todo mundo que chega ao painel --
    # professor inclusive (app.py so barra aluno). O unico obstaculo para um
    # professor entrar no ADM era a Chave Mestra, uma senha unica combinada
    # entre pessoas. No Flask isso ja e por papel, e ha teste cobrando que
    # professor nao alcance a aba nem digitando na URL
    # (tests/test_painel_desenvolvedor.py).
    #
    # Hoje a aba nao existe mais para ninguem: o ADM virou PAGINA propria
    # ("🏛️ ADM"), com a tranca em _pagina_permitida e a segunda em app.py.
    # Ele era a setima aba de um painel de professor, o que escondia uma area
    # de desenvolvedor dentro da area de outro papel.
    titulos = [
        "📊 Análises", "⚔️ RPG", "📝 Matrícula", "🏆 Ranking",
        "📋 Resumo da Turma", "👥 Professores", "⚙️ Configurações",
    ]

    abas = st.tabs(titulos)
    with abas[0]:
        renderizar_aba_analises(escola_id, dados_escola, user_tz)
    with abas[1]:
        _renderizar_aba_rpg_config(escola_id)
    with abas[2]:
        _renderizar_aba_matricula(escola_id)
    with abas[3]:
        _renderizar_aba_ranking(escola_id)
    with abas[4]:
        _renderizar_aba_resumo_turma(escola_id, dados_escola)
    with abas[5]:
        _renderizar_aba_professores()
    with abas[6]:
        _renderizar_aba_configuracoes(escola_id, dados_escola)
