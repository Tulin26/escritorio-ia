import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .commons import FONT_BOLD, _on_page, _styles, _xml


def gerar_pdf_relatorio_turma(nome_escola, dados_turma, total_questoes, media_turma, tempo_medio_turma, alunos_baixo_desempenho):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    story = []

    styles = _styles()

    story.append(Paragraph(f"Relatorio da Turma - {_xml(nome_escola)}", styles["title"]))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y as %H:%M')}", styles["normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Metricas da Turma</b>", styles["heading"]))
    story.append(Paragraph(f"Total de alunos: {len(dados_turma)}", styles["normal"]))
    story.append(Paragraph(f"Total de questoes respondidas: {total_questoes}", styles["normal"]))
    story.append(Paragraph(f"Media de acertos da turma: {media_turma}%", styles["normal"]))
    story.append(Paragraph(f"Tempo medio de resposta: {tempo_medio_turma} segundos", styles["normal"]))
    story.append(Spacer(1, 10))

    if alunos_baixo_desempenho:
        story.append(Paragraph(f"<font color='red'><b>ALERTA! {len(alunos_baixo_desempenho)} alunos com baixo desempenho</b></font>", styles["heading"]))
        for aluno in alunos_baixo_desempenho:
            story.append(Paragraph(
                f"{_xml(aluno['nome'])} - {_xml(aluno['ano_escolar'])} - {aluno['percentual']}% de acerto ({aluno['acertos']}/{aluno['total_questoes']})",
                styles["normal"],
            ))
        story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Detalhamento por Aluno</b>", styles["heading"]))
    story.append(Spacer(1, 5))

    table_data = [["Aluno", "Serie", "Periodo", "Total", "Acertos", "%", "Tempo Medio"]]
    for aluno in dados_turma:
        table_data.append([
            aluno["nome"][:25],
            aluno["ano_escolar"],
            aluno.get("periodo", "-"),
            str(aluno["total_questoes"]),
            str(aluno["acertos"]),
            f"{aluno['percentual']}%",
            f"{aluno['tempo_medio_resposta']}s",
        ])

    estilos_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]

    for i, aluno in enumerate(dados_turma, 1):
        if aluno.get("baixo_desempenho", False):
            estilos_tabela.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#ffcccc")))

    table = Table(table_data, colWidths=[50 * mm, 25 * mm, 25 * mm, 18 * mm, 18 * mm, 18 * mm, 25 * mm])
    table.setStyle(TableStyle(estilos_tabela))

    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Relatorio gerado automaticamente pelo EducaGame</i>", styles["normal"]))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
