import pandas as pd
import plotly.express as px
import streamlit as st

import services.dados_service as db
import services.relatorios as report
from core.config import exibir_dificuldade


# MELHORIA: a aba tinha 212 linhas com quatro assuntos misturados -- o
# filtro por modo, tres montadores de historico e a escolha do nome do
# arquivo. Nada disso desenha nada: e logica pura embrulhada em tela, e
# por isso nunca tinha sido testada. Extraidas, viram funcoes que se
# testam direto, sem bancada nenhuma.
OPCOES_TIPO = {
    "🔮 Oráculo": "oraculo",
    "🎯 Modo Treino": "treino",
    "🎓 ENEM": "enem",
    "👑 Boss Rush ENEM": "boss_rush_enem",
    "🔐 Escape Room": "escape_room",
    "🧪 Laboratório": "laboratorio",
    "⚔️ RPG": "rpg",
}


def filtrar_por_tipo(df_at, tipo_filtro):
    """As sete faixas de modo, cada uma com sua regra.

    A do ENEM e a unica que precisa EXCLUIR: boss_rush_enem tambem grava
    materia comecando com "ENEM-", entao sem o `!= boss_rush_enem` as duas
    faixas se misturariam.
    """
    modos = df_at["modo"].fillna("")
    materias = df_at["materia"].fillna("")
    if tipo_filtro == "oraculo":
        df_filtrado = df_at[modos.replace("", "oraculo") == "oraculo"]
    elif tipo_filtro == "treino":
        df_filtrado = df_at[modos == "treino"]
    elif tipo_filtro == "enem":
        df_filtrado = df_at[((modos == "enem") | materias.str.startswith("ENEM-")) & (modos != "boss_rush_enem")]
    elif tipo_filtro == "boss_rush_enem":
        df_filtrado = df_at[modos == "boss_rush_enem"]
    elif tipo_filtro == "escape_room":
        df_filtrado = df_at[modos == "escape_room"]
    elif tipo_filtro == "laboratorio":
        df_filtrado = df_at[materias.str.startswith("LAB-")]
    elif tipo_filtro == "rpg":
        df_filtrado = df_at[materias.str.startswith("RPG-")]
    else:
        df_filtrado = df_at

    return df_filtrado


def _tempo(row_pdf) -> float:
    """Segundos gastos na questao, ou 0 -- inclusive quando vem NaN.

    MELHORIA: era `row_pdf.get("tempo_resposta", 0) or 0`, e o `or 0` nao
    guardava nada. O ausente aqui nao e None: quando ALGUMA linha do log tem
    a coluna e outra nao, o pandas preenche a que falta com NaN -- e NaN e
    VERDADEIRO, entao ele atravessa o `or` inteiro.

    O destino e uma media: pdf_enem soma os tempos e divide pelo total. Um
    unico NaN contamina a soma, e o boletim entregue ao professor sai com
    "Tempo medio: nan".
    """
    valor = row_pdf.get("tempo_resposta", 0)
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return 0
    return 0 if valor != valor else valor   # NaN e o unico valor != a si mesmo


def _historico_enem(df_pdf) -> list[dict]:
    historico_enem_pdf = []
    for numero, (_, row_pdf) in enumerate(df_pdf.iterrows(), 1):
        area_label_pdf = row_pdf.get("area_bncc") or str(row_pdf.get("materia", "")).replace("ENEM-", "")
        historico_enem_pdf.append({
            "numero": numero,
            "area": row_pdf.get("area_bncc", ""),
            "area_label": area_label_pdf,
            "dificuldade": exibir_dificuldade(row_pdf.get("dificuldade", "")),
            "pergunta": row_pdf.get("pergunta_texto", ""),
            "correta": row_pdf.get("resposta_correta", ""),
            "resposta_aluno": row_pdf.get("resposta_aluno", ""),
            "acertou": row_pdf.get("resultado") == "Acertou",
            "explicacao": row_pdf.get("explicacao_ia", ""),
            "matriz_enem": row_pdf.get("matriz_enem", ""),
            "tempo": _tempo(row_pdf),
        })
    return historico_enem_pdf


def _historico_boss_rush(df_pdf) -> list[dict]:
    historico_boss_pdf = []
    for _, row_pdf in df_pdf.iterrows():
        area_label_pdf = row_pdf.get("area_bncc") or str(row_pdf.get("materia", "")).replace("ENEM-", "")
        historico_boss_pdf.append({
            "boss": "Boss Rush ENEM",
            "area": row_pdf.get("area_bncc", ""),
            "area_label": area_label_pdf,
            "dificuldade": exibir_dificuldade(row_pdf.get("dificuldade", "")),
            "pergunta": row_pdf.get("pergunta_texto", ""),
            "correta": row_pdf.get("resposta_correta", ""),
            "resposta_aluno": row_pdf.get("resposta_aluno", ""),
            "acertou": row_pdf.get("resultado") == "Acertou",
            "explicacao": row_pdf.get("explicacao_ia", ""),
            "matriz_enem": row_pdf.get("matriz_enem", ""),
            "tempo": _tempo(row_pdf),
        })
    return historico_boss_pdf


def _historico_escape_room(df_pdf) -> list[dict]:
    historico_escape_pdf = []
    for numero, (_, row_pdf) in enumerate(df_pdf.iterrows(), 1):
        historico_escape_pdf.append({
            "sala": numero,
            "materia": row_pdf.get("materia", ""),
            "tema": "",
            "pergunta": row_pdf.get("pergunta_texto", ""),
            "resposta_correta": row_pdf.get("resposta_correta", ""),
            "resposta_aluno": row_pdf.get("resposta_aluno", ""),
            "acertou": row_pdf.get("resultado") == "Acertou",
            "explicacao": row_pdf.get("explicacao_ia", ""),
            "tempo": _tempo(row_pdf),
        })
    return historico_escape_pdf


def rotulo_e_nome_do_pdf(tipo_filtro, al_sel, nome_materia_pdf, qtd_erros_info):
    """O texto do botao e o nome do arquivo baixado, por modo."""
    label_pdf = f"📥 Baixar PDF ({qtd_erros_info} erros)"
    nome_pdf = f"Revisao_{al_sel.replace(' ', '_')}_{nome_materia_pdf}.pdf"
    if tipo_filtro == "rpg":
        label_pdf = f"📥 Baixar PDF RPG ({qtd_erros_info} erros)"
        nome_pdf = f"RPG_{al_sel.replace(' ', '_')}_{nome_materia_pdf}.pdf"
    elif tipo_filtro == "enem":
        label_pdf = f"📥 Baixar PDF ENEM ({qtd_erros_info} erros)"
        nome_pdf = f"ENEM_{al_sel.replace(' ', '_')}_{nome_materia_pdf}.pdf"
    elif tipo_filtro == "boss_rush_enem":
        label_pdf = f"📥 Baixar PDF Boss Rush ({qtd_erros_info} erros)"
        nome_pdf = f"Boss_Rush_{al_sel.replace(' ', '_')}_{nome_materia_pdf}.pdf"
    elif tipo_filtro == "escape_room":
        label_pdf = f"📥 Baixar PDF Escape Room ({qtd_erros_info} erros)"
        nome_pdf = f"Escape_Room_{al_sel.replace(' ', '_')}_{nome_materia_pdf}.pdf"

    return label_pdf, nome_pdf


def rotulos_de_materia(df_filtrado) -> list[str]:
    """As opcoes do seletor, cada uma com a contagem entre parenteses."""
    materias_disponiveis = sorted(df_filtrado["materia"].unique().tolist())
    materias_com_contagem = [f"{m} ({len(df_filtrado[df_filtrado['materia'] == m])} questões)" for m in materias_disponiveis]
    return materias_com_contagem


def recorte_para_pdf(df_filtrado, filtro_pdf):
    """As linhas que vao para o PDF, e o rotulo que descreve o recorte.

    `criterio_pdf` NAO aparece aqui de proposito: ele era atribuido
    "materia" nos dois ramos do if, ou seja, nunca foi uma decisao. Fica
    no chamador, como a constante que sempre foi.
    """
    if filtro_pdf != "📚 Todas as matérias":
        materia_nome = filtro_pdf.rsplit(" (", 1)[0]
        df_pdf = df_filtrado[df_filtrado["materia"] == materia_nome]
        criterio_label = f"Matéria: {materia_nome}"
    else:
        df_pdf = df_filtrado
        criterio_label = "Todas as matérias"

    return df_pdf, criterio_label


def metricas_do_recorte(df_pdf) -> tuple[int, int, int, int]:
    """(total, acertos, erros, aproveitamento em %)."""
    total = len(df_pdf)
    acertos = len(df_pdf[df_pdf["resultado"] == "Acertou"])
    erros_pdf = len(df_pdf[df_pdf["resultado"] != "Acertou"])
    pct = int(acertos / total * 100) if total > 0 else 0
    return total, acertos, erros_pdf, pct


def renderizar_aba_analises(escola_id, dados_escola, user_tz):
    st.subheader("📊 Desempenho dos Alunos")
    logs = db.buscar_logs(escola_id)
    alunos = db.buscar_alunos(escola_id)

    if not alunos:
        st.info("Nenhum aluno cadastrado para esta escola ainda. Use a aba de matrícula para adicionar alunos.")
        return

    if not logs:
        st.info("Ainda não há respostas registradas para análise. Os dados aparecerão aqui depois que os alunos responderem atividades.")
        return

    df_logs = pd.DataFrame(logs)
    df_al = pd.DataFrame(alunos)

    if df_logs.empty:
        st.info("Os registros de atividade vieram vazios para esta escola.")
        return

    al_sel = st.selectbox("Selecione o aluno:", df_al["nome"].tolist())
    al_obj = df_al[df_al["nome"] == al_sel].iloc[0]
    df_at = df_logs[df_logs["aluno_id"] == al_obj["id"]]

    if df_at.empty:
        st.info(f"{al_sel} ainda não possui respostas registradas para exibir nesta aba.")
        return

    tipo_label = st.selectbox(
        "Filtrar por tipo:",
        options=list(OPCOES_TIPO.keys()),
        key="tipo_filtro_analises",
    )
    tipo_filtro = OPCOES_TIPO[tipo_label]

    df_filtrado = filtrar_por_tipo(df_at, tipo_filtro)

    if df_filtrado.empty:
        st.warning("⚠️ Nenhuma questão encontrada com o filtro selecionado.")
        return

    st.markdown("---")
    materias_com_contagem = rotulos_de_materia(df_filtrado)
    filtro_pdf = st.selectbox(
        "📖 Filtrar por matéria (para o PDF):",
        options=["📚 Todas as matérias"] + materias_com_contagem,
        key="filtro_materia_pdf",
    )

    df_pdf, criterio_label = recorte_para_pdf(df_filtrado, filtro_pdf)
    criterio_pdf = "materia"

    qtd_erros_info = len(df_pdf[df_pdf["resultado"] != "Acertou"])
    st.info(f"📄 O PDF usará **{len(df_pdf)} registros** no resumo e mostrará **{qtd_erros_info} erros** com filtro: {criterio_label}")

    total, acertos, erros_pdf, pct = metricas_do_recorte(df_pdf)
    col1, col2, col3 = st.columns(3)
    col1.metric("📝 Registros no recorte", total)
    col2.metric("❌ Erros no PDF", erros_pdf)
    col3.metric("🎯 Aproveitamento", f"{pct}%")

    st.markdown("---")
    fig2 = px.pie(
        df_pdf,
        names="resultado",
        hole=0.4,
        title=f"Desempenho: {al_sel} - {criterio_label}",
        color="resultado",
        color_discrete_map={"Acertou": "#2ecc71", "Errou": "#e74c3c"},
    )
    st.plotly_chart(fig2, width="stretch")

    try:
        nome_materia_pdf = "Todas" if filtro_pdf == "📚 Todas as matérias" else filtro_pdf.rsplit(" (", 1)[0].replace(" ", "_")
        if tipo_filtro == "enem":
            historico_enem_pdf = _historico_enem(df_pdf)
            pdf_bytes = report.gerar_pdf_enem(
                nome_aluno=al_sel,
                historico=historico_enem_pdf,
                dados_escola=dados_escola,
                acertos=len([item for item in historico_enem_pdf if item["acertou"]]),
                total=len(historico_enem_pdf),
            )
        elif tipo_filtro == "boss_rush_enem":
            historico_boss_pdf = _historico_boss_rush(df_pdf)
            pdf_bytes = report.gerar_pdf_boss_rush(
                nome_aluno=al_sel,
                historico=historico_boss_pdf,
                dados_escola=dados_escola,
            )
        elif tipo_filtro == "escape_room":
            historico_escape_pdf = _historico_escape_room(df_pdf)
            pdf_bytes = report.gerar_pdf_escape_room(
                nome_aluno=al_sel,
                historico=historico_escape_pdf,
                dados_escola=dados_escola,
            )
        else:
            pdf_bytes = report.gerar_pdf_revisao(
                al_sel,
                df_pdf,
                dados_escola,
                user_tz,
                materia_filtro=filtro_pdf,
                serie_aluno=al_obj["ano_escolar"],
                organizacao=criterio_pdf,
                criterio_label=criterio_label,
            )

        label_pdf, nome_pdf = rotulo_e_nome_do_pdf(
            tipo_filtro, al_sel, nome_materia_pdf, qtd_erros_info
        )

        st.download_button(
            label=label_pdf,
            data=pdf_bytes,
            file_name=nome_pdf,
            mime="application/pdf",
            width="stretch",
        )
    except Exception as e:
        st.warning(f"PDF indisponível: {e}")
