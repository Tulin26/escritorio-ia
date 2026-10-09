import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .commons import (
    _agrupar_questoes,
    _bloco_radar_bncc,
    _cabecalho,
    _contagem_modos_relatorio,
    _data_local,
    _info_box,
    _linha_metricas,
    _listas_destaque_relatorio,
    _metric_card,
    _nivel_desempenho,
    _on_page,
    _pct,
    _questao_card,
    _rotulo_modo_relatorio,
    _styles,
    _tabela_insights,
    _tabela_resumo_materias,
    _texto_periodo_relatorio,
    _xml,
    preparar_texto_pdf,
    AZUL_CLARO,
    AZUL_ESCURO,
    VERDE,
    VERDE_CLARO,
    VERMELHO_CLARO,
    VERMELHO_INSTITUCIONAL,
)


def gerar_pdf_revisao(
    nome_aluno,
    df_aluno,
    dados_escola,
    user_tz,
    materia_filtro="Todas as materias",
    serie_aluno="",
    organizacao="materia",
    criterio_label="",
):
    df_base = df_aluno.copy() if df_aluno is not None else df_aluno
    df_erros = df_base[df_base["resultado"] != "Acertou"].copy() if df_base is not None and not df_base.empty else df_base

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
        title=f"Relatorio de Revisao - {preparar_texto_pdf(nome_aluno)}",
        author="EducaGame IA",
    )
    story = []
    styles = _styles()

    escola_nome = preparar_texto_pdf(dados_escola.get("nome", "EducaGame")) if isinstance(dados_escola, dict) else "EducaGame"
    agora = _data_local(user_tz)
    data_geracao = agora.strftime("%d/%m/%Y as %H:%M")

    total = len(df_base) if df_base is not None else 0
    acertos = len(df_base[df_base["resultado"] == "Acertou"]) if total > 0 and "resultado" in df_base.columns else 0
    erros = len(df_erros) if df_erros is not None else 0
    pct = _pct(acertos, total)
    desempenho = _nivel_desempenho(pct)
    fortes, atencao = _listas_destaque_relatorio(df_base, pct, erros) if total > 0 else ([], [])
    modos = _contagem_modos_relatorio(df_base) if total > 0 else {"oraculo": 0, "treino": 0, "laboratorio": 0, "rpg": 0}
    modos_ativos = [_rotulo_modo_relatorio(modo) for modo, qtd in modos.items() if qtd > 0]
    modo_label = ", ".join(modos_ativos) if modos_ativos else "Sem registros"

    story.append(_cabecalho("Relatorio de Revisao", "EducaGame IA - Painel de aprendizagem", escola_nome))
    story.append(Spacer(1, 4))
    story.append(_info_box(
        [("Aluno", nome_aluno), ("Serie/Turma", serie_aluno or "Nao informado"), ("Escola", escola_nome)],
        [("Periodo", _texto_periodo_relatorio(df_base) if total > 0 else "Nao disponivel"), ("Filtro", criterio_label or materia_filtro), ("Data de geracao", data_geracao)],
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("RESUMO DE DESEMPENHO", styles["section"]))
    story.append(_linha_metricas([
        _metric_card(f"{pct}%", "Aproveitamento", desempenho, AZUL_ESCURO, AZUL_CLARO),
        _metric_card(str(total), "Questoes", "registros no filtro", AZUL_ESCURO),
        _metric_card(str(acertos), "Acertos", "respostas corretas", VERDE, VERDE_CLARO),
        _metric_card(str(erros), "Erros", "questoes para revisar", VERMELHO_INSTITUCIONAL, VERMELHO_CLARO),
    ]))
    story.append(Spacer(1, 8))
    story.append(_linha_metricas([
        _metric_card(str(modos.get("oraculo", 0)), "Oraculo", modo_label if modo_label != "Sem registros" else "atividade registrada", AZUL_ESCURO),
        _metric_card(str(modos.get("treino", 0)), "Treino", "pratica guiada", AZUL_ESCURO),
        _metric_card(str(modos.get("laboratorio", 0)), "Laboratorio", "desafios praticos", AZUL_ESCURO),
        _metric_card(str(modos.get("rpg", 0)), "RPG", "missoes gamificadas", AZUL_ESCURO),
    ]))
    story.append(Spacer(1, 10))

    tabela_materias = _tabela_resumo_materias(df_base) if total > 0 else None
    if tabela_materias:
        story.append(Paragraph("RESUMO POR MATERIA", styles["section"]))
        story.append(tabela_materias)
        story.append(Spacer(1, 10))

    radar_bncc = _bloco_radar_bncc(df_base, serie_aluno) if total > 0 else None
    if radar_bncc:
        story.append(Paragraph("DESEMPENHO POR AREAS BNCC (ENSINO MEDIO)", styles["section"]))
        story.append(Paragraph("Meta de referencia: 90% de aproveitamento em cada area do Ensino Medio.", styles["small"]))
        story.append(Spacer(1, 4))
        story.append(radar_bncc)
        story.append(Spacer(1, 10))

    if fortes or atencao:
        story.append(Paragraph("LEITURA PEDAGOGICA DO RECORTE", styles["section"]))
        story.append(_tabela_insights(fortes, atencao))
        story.append(Spacer(1, 10))

    story.append(Paragraph("REVISAO DAS QUESTOES ERRADAS", styles["section"]))
    if df_erros is None or df_erros.empty:
        story.append(Paragraph("Nenhuma questao errada no filtro selecionado. Este relatorio mostra apenas os erros para revisao.", styles["normal"]))
    else:
        grupos = _agrupar_questoes(df_erros, organizacao, serie_aluno)
        contador = 1
        for nome_grupo, df_grupo in grupos:
            story.append(Paragraph(_xml(nome_grupo), styles["group"]))
            for _, row in df_grupo.iterrows():
                story.append(_questao_card(contador, row))
                contador += 1

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
