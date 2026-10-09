import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .commons import (
    AZUL_INSTITUCIONAL,
    BRANCO,
    CINZA_BORDA,
    CINZA_FUNDO,
    FONT_BOLD,
    HRFlowable,
    _blocos_para_texto,
    _on_page,
    _styles,
    _xml,
    preparar_texto_pdf,
)


def gerar_pdf_boss_rush(nome_aluno: str, historico: list[dict], dados_escola: dict) -> bytes:
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

    total = len(historico or [])
    acertos = sum(1 for item in historico or [] if item.get("acertou"))
    pct = int(acertos / total * 100) if total else 0
    tempo_medio = round(sum(float(item.get("tempo") or 0) for item in historico or []) / total, 1) if total else 0

    story.append(Paragraph("Relatorio Boss Rush ENEM", styles["title"]))
    story.append(Paragraph(escola_nome, styles["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Aluno: {_xml(nome_aluno)}   |   Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M')}",
        styles["small"],
    ))
    story.append(HRFlowable())
    story.append(Spacer(1, 8))

    metricas = [
        ["Questoes", "Acertos", "Aproveitamento", "Tempo medio"],
        [str(total), str(acertos), f"{pct}%", f"{tempo_medio}s"],
    ]
    tabela_metricas = Table(metricas, colWidths=[43 * mm] * 4)
    tabela_metricas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
        ("BACKGROUND", (0, 1), (-1, 1), BRANCO),
        ("BOX", (0, 0), (-1, -1), 0.6, CINZA_BORDA),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(tabela_metricas)
    story.append(Spacer(1, 12))

    por_boss: dict[str, dict[str, int]] = {}
    for item in historico or []:
        boss = str(item.get("boss") or "Boss")
        stats = por_boss.setdefault(boss, {"total": 0, "acertos": 0})
        stats["total"] += 1
        if item.get("acertou"):
            stats["acertos"] += 1

    if por_boss:
        story.append(Paragraph("Resumo por Boss", styles["section"]))
        dados_boss = [["Boss", "Questoes", "Acertos", "%"]]
        for boss, stats in por_boss.items():
            total_boss = stats["total"]
            acertos_boss = stats["acertos"]
            pct_boss = int(acertos_boss / total_boss * 100) if total_boss else 0
            dados_boss.append([_xml(boss), str(total_boss), str(acertos_boss), f"{pct_boss}%"])
        tabela_boss = Table(dados_boss, colWidths=[90 * mm, 25 * mm, 25 * mm, 25 * mm])
        tabela_boss.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL_INSTITUCIONAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRANCO),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_FUNDO]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tabela_boss)
        story.append(Spacer(1, 12))

    story.append(Paragraph("Questoes Respondidas", styles["section"]))
    if not historico:
        story.append(Paragraph("Nenhuma questao registrada no Boss Rush.", styles["normal"]))
    for idx, item in enumerate(historico or [], 1):
        acertou = bool(item.get("acertou"))
        cor = "green" if acertou else "red"
        status = "ACERTOU" if acertou else "ERROU"
        meta = f"Questao {idx} | {_xml(item.get('boss', 'Boss'))}"
        if item.get("area_label") or item.get("area"):
            meta += f" | {_xml(item.get('area_label') or item.get('area'))}"
        story.append(Paragraph(f"<b>{meta} | <font color='{cor}'>{status}</font></b>", styles["heading"]))
        story.append(Paragraph(f"<b>Enunciado:</b> {preparar_texto_pdf(item.get('pergunta', ''))}", styles["normal"]))
        story.append(Paragraph(f"<font color='red'>Resposta do aluno: {preparar_texto_pdf(item.get('resposta_aluno', ''))}</font>", styles["normal"]))
        story.append(Paragraph(f"<font color='green'>Resposta correta: {preparar_texto_pdf(item.get('correta', ''))}</font>", styles["normal"]))
        if item.get("tempo") is not None:
            story.append(Paragraph(f"Tempo de resposta: {_xml(item.get('tempo'))}s", styles["small"]))
        exp = item.get("explicacao", "")
        exp_txt = _blocos_para_texto(exp) if isinstance(exp, (list, str)) else str(exp)
        if exp_txt:
            story.append(Paragraph(f"<b>Explicacao:</b> {preparar_texto_pdf(exp_txt)}", styles["normal"]))
        story.append(Spacer(1, 5))
        story.append(HRFlowable())
        story.append(Spacer(1, 5))

    story.append(Paragraph("<i>Relatorio gerado automaticamente pelo EducaGame</i>", styles["small"]))
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()

