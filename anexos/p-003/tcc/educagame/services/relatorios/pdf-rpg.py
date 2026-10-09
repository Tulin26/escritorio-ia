import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .commons import HRFlowable, _blocos_para_texto, _on_page, _styles, _xml, preparar_texto_pdf


def gerar_pdf_rpg(nome_aluno, titulo_aventura, historico_desafios, dados_escola, hp_final, xp_final):
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
    escola_nome = preparar_texto_pdf(dados_escola.get("nome", "EduGame")) if isinstance(dados_escola, dict) else "EduGame"

    story.append(Paragraph(f"Relatorio de Aventura RPG - {escola_nome}", styles["title"]))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"Heroi: {_xml(nome_aluno)}", styles["normal"]))
    story.append(Paragraph(f"Aventura: {_xml(titulo_aventura)}", styles["normal"]))
    story.append(Spacer(1, 10))

    total = len(historico_desafios)
    acertos = sum(1 for d in historico_desafios if d.get("acertou"))
    pct = int(acertos / total * 100) if total > 0 else 0

    story.append(Paragraph("<b>Resumo Final da Aventura</b>", styles["heading"]))
    story.append(Paragraph(f"HP Final: {hp_final}/100 | XP Total: {xp_final}", styles["normal"]))
    story.append(Paragraph(f"Desafios: {total} | Acertos: {acertos} | Erros: {total - acertos} | Aproveitamento: {pct}%", styles["normal"]))
    story.append(Spacer(1, 10))

    if not historico_desafios:
        story.append(Paragraph("Nenhum desafio academico foi respondido nesta aventura.", styles["normal"]))
    else:
        for idx, d in enumerate(historico_desafios, 1):
            acertou = d.get("acertou", False)
            status = "ACERTOU" if acertou else "ERROU"
            cor = "green" if acertou else "red"

            story.append(Paragraph(
                f"<b>Desafio {idx} - Fase {_xml(str(d.get('fase', '?')))} | <font color='{cor}'>{status}</font></b>",
                styles["heading"],
            ))
            story.append(Paragraph(f"Pergunta: {_xml(d.get('pergunta', ''))}", styles["normal"]))

            if acertou:
                story.append(Paragraph(
                    f"<font color='green'>Sua resposta: {_xml(d.get('resposta_aluno', ''))} [CORRETA]</font>",
                    styles["normal"],
                ))
            else:
                story.append(Paragraph(
                    f"<font color='red'>Sua resposta: {_xml(d.get('resposta_aluno', ''))} [ERRADA]</font>",
                    styles["normal"],
                ))
                story.append(Paragraph(
                    f"<font color='green'>Resposta correta: {_xml(d.get('resposta_correta', ''))}</font>",
                    styles["normal"],
                ))

            exp = d.get("explicacao", "")
            exp_txt = _blocos_para_texto(exp) if isinstance(exp, (list, str)) else str(exp)
            story.append(Paragraph(f"Explicacao: {_xml(exp_txt)}", styles["normal"]))
            story.append(Spacer(1, 10))
            story.append(HRFlowable())
            story.append(Spacer(1, 5))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
