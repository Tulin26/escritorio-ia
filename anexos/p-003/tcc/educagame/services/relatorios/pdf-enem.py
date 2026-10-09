import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .commons import (
    AZUL_CLARO,
    AZUL_INSTITUCIONAL,
    BRANCO,
    CINZA_BORDA,
    CINZA_FUNDO,
    HRFlowable,
    VERMELHO_INSTITUCIONAL,
    _blocos_para_texto,
    _on_page,
    _styles,
    _xml,
    preparar_texto_pdf,
    FONT_BOLD,
)


def gerar_pdf_enem(
    nome_aluno: str,
    historico: list[dict],
    dados_escola: dict,
    acertos: int,
    total: int,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
    )
    story = []
    styles = _styles()
    escola_nome = _xml(dados_escola.get("nome", "EduGame")) if isinstance(dados_escola, dict) else "EduGame"
    pct = int(acertos / total * 100) if total else 0

    story.append(Paragraph("Relatorio de Simulado ENEM", styles["title"]))
    story.append(Paragraph(escola_nome, styles["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Aluno: {_xml(nome_aluno)}   |   Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M')}",
        styles["small"],
    ))
    story.append(HRFlowable())
    story.append(Spacer(1, 8))

    erradas = [q for q in historico if not q.get("acertou")]
    tempo_medio = round(sum(q.get("tempo", 0) for q in historico) / total, 1) if total else 0

    metricas = [
        [
            Paragraph("<b>Questoes</b>", styles["metric_label"]),
            Paragraph("<b>Acertos</b>", styles["metric_label"]),
            Paragraph("<b>Aproveitamento</b>", styles["metric_label"]),
            Paragraph("<b>Tempo medio</b>", styles["metric_label"]),
        ],
        [
            Paragraph(str(total), styles["metric_value"]),
            Paragraph(str(acertos), styles["metric_value"]),
            Paragraph(f"{pct}%", styles["metric_value"]),
            Paragraph(f"{tempo_medio}s", styles["metric_value"]),
        ],
    ]
    t_metricas = Table(metricas, colWidths=[43 * mm] * 4)
    t_metricas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
        ("BACKGROUND", (0, 1), (-1, 1), BRANCO),
        ("BOX", (0, 0), (-1, -1), 0.6, CINZA_BORDA),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(t_metricas)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Desempenho por Area do Conhecimento", styles["section"]))

    areas_stats: dict[str, dict] = {}
    for q in historico:
        area = q.get("area_label") or q.get("area", "Outra")
        if area not in areas_stats:
            areas_stats[area] = {"total": 0, "acertos": 0}
        areas_stats[area]["total"] += 1
        if q.get("acertou"):
            areas_stats[area]["acertos"] += 1

    tabela_areas = [["Area", "Total", "Acertos", "%"]]
    for area, st_a in areas_stats.items():
        t_a = st_a["total"]
        ac_a = st_a["acertos"]
        p_a = int(ac_a / t_a * 100) if t_a else 0
        tabela_areas.append([_xml(area), str(t_a), str(ac_a), f"{p_a}%"])

    t_areas = Table(tabela_areas, colWidths=[95 * mm, 20 * mm, 20 * mm, 22 * mm])
    estilos_areas = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_INSTITUCIONAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRANCO),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_FUNDO]),
    ]
    for i, row in enumerate(tabela_areas[1:], 1):
        pct_row = int(row[3].replace("%", "") or 0)
        if pct_row < 50:
            estilos_areas.append(("TEXTCOLOR", (3, i), (3, i), VERMELHO_INSTITUCIONAL))
    t_areas.setStyle(TableStyle(estilos_areas))
    story.append(t_areas)
    story.append(Spacer(1, 12))

    if not erradas:
        story.append(Paragraph("Parabens! Todas as questoes foram respondidas corretamente.", styles["normal"]))
    else:
        story.append(Paragraph(f"Questoes para Revisar ({len(erradas)})", styles["section"]))

        for idx, q in enumerate(erradas, 1):
            bloco = []
            area_txt = _xml(q.get("area_label") or q.get("area", ""))
            matriz = _xml(q.get("matriz_enem", ""))
            dific = _xml(q.get("dificuldade", ""))

            meta = f"Questao {q.get('numero', idx)}  |  {area_txt}"
            if matriz:
                meta += f"  |  {matriz}"
            if dific:
                meta += f"  |  Nivel: {dific}"

            bloco.append(Paragraph(meta, styles["label"]))
            bloco.append(Paragraph(
                f"<b>Enunciado:</b> {preparar_texto_pdf(q.get('pergunta', ''))}",
                styles["normal"],
            ))
            bloco.append(Paragraph(
                f"<font color='red'>Sua resposta: {preparar_texto_pdf(q.get('resposta_aluno', ''))}</font>",
                styles["normal"],
            ))
            bloco.append(Paragraph(
                f"<font color='green'>Resposta correta: {preparar_texto_pdf(q.get('correta', ''))}</font>",
                styles["normal"],
            ))

            exp = q.get("explicacao", [])
            if exp:
                exp_txt = _blocos_para_texto(exp) if isinstance(exp, (list, str)) else str(exp)
                bloco.append(Paragraph(
                    f"<b>Explicacao:</b> {preparar_texto_pdf(exp_txt)}",
                    styles["normal"],
                ))

            bloco.append(HRFlowable())
            bloco.append(Spacer(1, 4))
            story.extend(bloco)

    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Relatorio gerado automaticamente pelo EducaGame</i>", styles["small"]))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
