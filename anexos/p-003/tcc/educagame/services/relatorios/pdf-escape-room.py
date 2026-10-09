import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .commons import (
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


def gerar_pdf_escape_room(nome_aluno: str, historico: list[dict], dados_escola: dict) -> bytes:
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

    historico = historico or []
    total = len(historico)
    acertos = sum(1 for item in historico if item.get("acertou"))
    pct = int(acertos / total * 100) if total else 0
    tempo_medio = round(sum(float(item.get("tempo") or 0) for item in historico) / total, 1) if total else 0

    story.append(Paragraph("Relatorio Escape Room", styles["title"]))
    story.append(Paragraph(escola_nome, styles["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Aluno: {_xml(nome_aluno)}   |   Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M')}",
        styles["small"],
    ))
    story.append(HRFlowable())
    story.append(Spacer(1, 8))

    metricas = [
        ["Salas", "Portas abertas", "Aproveitamento", "Tempo medio"],
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

    story.append(Paragraph("Percurso por Sala", styles["section"]))
    if not historico:
        story.append(Paragraph("Nenhuma sala respondida neste Escape Room.", styles["normal"]))
    else:
        tabela = [["Sala", "Materia", "Tema", "Status", "Tempo"]]
        for item in historico:
            tabela.append([
                str(item.get("sala", "")),
                _xml(item.get("materia", "")),
                _xml(item.get("tema") or "BNCC aleatorio"),
                "Aberta" if item.get("acertou") else "Revisar",
                f"{item.get('tempo', 0)}s",
            ])
        tabela_salas = Table(tabela, colWidths=[13 * mm, 38 * mm, 58 * mm, 25 * mm, 22 * mm])
        tabela_salas.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRANCO),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 0), (2, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.35, CINZA_BORDA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_FUNDO]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tabela_salas)
        story.append(Spacer(1, 12))

    story.append(Paragraph("Questoes para revisao", styles["section"]))
    for idx, item in enumerate(historico, 1):
        acertou = bool(item.get("acertou"))
        cor = "green" if acertou else "red"
        status = "ABRIU A PORTA" if acertou else "PRECISA REVISAR"
        story.append(Paragraph(
            f"<b>Sala {item.get('sala', idx)} - {_xml(item.get('materia', ''))} | <font color='{cor}'>{status}</font></b>",
            styles["heading"],
        ))
        story.append(Paragraph(f"<b>Tema:</b> {_xml(item.get('tema') or 'BNCC aleatorio')}", styles["small"]))
        story.append(Paragraph(f"<b>Enunciado:</b> {preparar_texto_pdf(item.get('pergunta', ''))}", styles["normal"]))
        story.append(Paragraph(f"<font color='red'>Resposta do aluno: {preparar_texto_pdf(item.get('resposta_aluno', ''))}</font>", styles["normal"]))
        story.append(Paragraph(f"<font color='green'>Resposta correta: {preparar_texto_pdf(item.get('resposta_correta', ''))}</font>", styles["normal"]))
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
