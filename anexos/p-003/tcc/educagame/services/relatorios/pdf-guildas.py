import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .commons import AZUL_INSTITUCIONAL, BRANCO, CINZA_BORDA, CINZA_FUNDO, FONT_BOLD, HRFlowable, _on_page, _styles, _xml


def gerar_pdf_guildas(nome_escola: str, guildas: list[dict]) -> bytes:
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

    guildas = guildas or []
    total_guildas = len(guildas)
    total_questoes = sum(int(g.get("questoes_semana") or 0) for g in guildas)
    total_acertos = sum(int(g.get("acertos_semana") or 0) for g in guildas)
    taxa = int(total_acertos / total_questoes * 100) if total_questoes else 0
    lider = guildas[0].get("guilda", "-") if guildas else "-"

    story.append(Paragraph("Relatorio Duelo de Guildas", styles["title"]))
    story.append(Paragraph(_xml(nome_escola or "EduGame"), styles["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M')}", styles["small"]))
    story.append(HRFlowable())
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Resumo semanal</b>", styles["heading"]))
    story.append(Paragraph(
        f"Guildas: {total_guildas} | Lider: {_xml(lider)} | Questoes: {total_questoes} | Acertos: {total_acertos} | Taxa geral: {taxa}%",
        styles["normal"],
    ))
    story.append(Spacer(1, 10))

    if not guildas:
        story.append(Paragraph("Ainda nao ha guildas com dados para o relatorio.", styles["normal"]))
    else:
        story.append(Paragraph("Ranking por Guilda", styles["section"]))
        tabela = [["Pos.", "Guilda", "Alunos", "Part.", "Questoes", "Acertos", "Erros", "Pts", "%"]]
        for idx, guilda in enumerate(guildas, 1):
            tabela.append([
                str(idx),
                _xml(guilda.get("guilda", "")),
                str(guilda.get("alunos", 0)),
                str(guilda.get("participantes_semana", 0)),
                str(guilda.get("questoes_semana", 0)),
                str(guilda.get("acertos_semana", 0)),
                str(guilda.get("erros_semana", 0)),
                str(guilda.get("pontos_semana", 0)),
                f"{int(guilda.get('taxa_acerto') or 0)}%",
            ])

        tabela_rank = Table(
            tabela,
            colWidths=[12 * mm, 48 * mm, 15 * mm, 15 * mm, 19 * mm, 18 * mm, 15 * mm, 16 * mm, 13 * mm],
        )
        tabela_rank.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), AZUL_INSTITUCIONAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRANCO),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.35, CINZA_BORDA),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_FUNDO]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tabela_rank)
        story.append(Spacer(1, 12))

        story.append(Paragraph("Duelos da semana", styles["section"]))
        pares = []
        for i in range(0, len(guildas) - 1, 2):
            a = guildas[i]
            b = guildas[i + 1]
            lider_duelo = a if int(a.get("pontos_semana") or 0) >= int(b.get("pontos_semana") or 0) else b
            diff = abs(int(a.get("pontos_semana") or 0) - int(b.get("pontos_semana") or 0))
            pares.append([
                _xml(a.get("guilda", "")),
                str(a.get("pontos_semana", 0)),
                _xml(b.get("guilda", "")),
                str(b.get("pontos_semana", 0)),
                _xml(lider_duelo.get("guilda", "")),
                str(diff),
            ])

        if pares:
            tabela_duelos = Table(
                [["Guilda A", "Pts", "Guilda B", "Pts", "Lider", "Dif."]] + pares,
                colWidths=[42 * mm, 15 * mm, 42 * mm, 15 * mm, 42 * mm, 15 * mm],
            )
            tabela_duelos.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), AZUL_INSTITUCIONAL),
                ("TEXTCOLOR", (0, 0), (-1, 0), BRANCO),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("ALIGN", (5, 0), (5, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.35, CINZA_BORDA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRANCO, CINZA_FUNDO]),
            ]))
            story.append(tabela_duelos)
        else:
            story.append(Paragraph("Cadastre alunos em pelo menos duas guildas para formar duelos.", styles["normal"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("<i>Relatorio gerado automaticamente pelo EducaGame</i>", styles["small"]))
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
