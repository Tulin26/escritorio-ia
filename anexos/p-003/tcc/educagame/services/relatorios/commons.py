from datetime import datetime
import ast
import json
import re
import unicodedata
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Image, KeepTogether, Paragraph, Spacer, Table, TableStyle

from core.config import get_area_da_materia, get_competencias_area, get_serie_tipo, materia_base as _materia_base_relatorio
from repositories.log_repo import tempo_resposta_para_media


try:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    FONT_NORMAL = "DejaVu"
    FONT_BOLD = "DejaVu-Bold"
except Exception:
    FONT_NORMAL = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"


AZUL_INSTITUCIONAL = colors.HexColor("#133C8B")
AZUL_ESCURO = colors.HexColor("#0B2C6B")
AZUL_CLARO = colors.HexColor("#EAF1FF")
VERMELHO_INSTITUCIONAL = colors.HexColor("#ED1C24")
VERMELHO_CLARO = colors.HexColor("#FFF0F1")
CINZA_TEXTO = colors.HexColor("#2C3440")
CINZA_MEDIO = colors.HexColor("#6B7280")
CINZA_BORDA = colors.HexColor("#D8E0EF")
CINZA_FUNDO = colors.HexColor("#F7F9FD")
VERDE = colors.HexColor("#15803D")
VERDE_CLARO = colors.HexColor("#ECFDF3")
BRANCO = colors.white


def _converter_latex_para_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = re.sub(r"\$\$(.*?)\$\$", r"\1", texto)
    texto = re.sub(r"\$(.*?)\$", r"\1", texto)
    texto = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1/\2)", texto)
    texto = texto.replace("\\cdot", " x ")
    texto = texto.replace("\\times", " x ")
    texto = texto.replace("\\div", " / ")
    texto = texto.replace("\\pm", " +/- ")
    texto = re.sub(r"\\sqrt\{([^}]+)\}", r"raiz(\1)", texto)
    texto = re.sub(r"\\[a-zA-Z]+(?:\{[^}]*\})?", "", texto)
    texto = re.sub(r"[{}]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


_SUPER_MAP = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
_SUB_MAP = str.maketrans("0123456789+-=()n", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙ")


def _formatar_notacao_matematica_texto(texto: str) -> str:
    def _super(match: re.Match) -> str:
        return match.group(1).translate(_SUPER_MAP)

    def _sub(match: re.Match) -> str:
        return match.group(1).translate(_SUB_MAP)

    texto = re.sub(r"\^\{([0-9+\-=()n]{1,5})\}", _super, texto)
    texto = re.sub(r"\^([+-]?\d+|n)", _super, texto)
    texto = re.sub(r"_\{([0-9+\-=()n]{1,5})\}", _sub, texto)
    texto = re.sub(r"_([+-]?\d+|n)", _sub, texto)
    return texto


def preparar_texto_pdf(txt):
    if txt is None:
        return " "
    txt = _converter_latex_para_texto(str(txt))
    txt = _formatar_notacao_matematica_texto(txt)
    txt = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", txt)
    return txt.strip() or " "


def _xml(txt) -> str:
    txt = preparar_texto_pdf(txt)
    return (
        txt.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _blocos_para_texto(exp):
    if isinstance(exp, str):
        try:
            exp = json.loads(exp)
        except Exception:
            try:
                exp = ast.literal_eval(exp)
            except Exception:
                return preparar_texto_pdf(str(exp))
    if not isinstance(exp, list):
        return preparar_texto_pdf(str(exp))

    partes = []
    for bloco in exp:
        if not isinstance(bloco, dict):
            continue
        tipo = bloco.get("tipo", "texto")
        conteudo = str(bloco.get("conteudo", "")).strip()
        if not conteudo or conteudo.upper() in ("N/A", "NA", "-", "NONE"):
            continue
        if tipo == "bold":
            partes.append(f"\n{conteudo}")
        elif tipo == "latex":
            conteudo = _converter_latex_para_texto(conteudo)
            if conteudo:
                partes.append(conteudo)
        elif tipo == "resultado":
            partes.append(f"Resultado: {conteudo}")
        elif tipo == "final":
            partes.append(f"Resultado Final: {conteudo}")
        else:
            partes.append(conteudo)
    return "\n".join(p for p in partes if p.strip())


def _competencias_relatorio(row, serie_aluno: str) -> list[str]:
    materia = _materia_base_relatorio(row.get("materia", ""))
    area = get_area_da_materia(materia, serie_aluno)
    return get_competencias_area(area, serie_aluno)


def _agrupar_questoes(df_aluno, organizacao: str, serie_aluno: str):
    grupos = []
    if organizacao == "competencia" and serie_aluno:
        competencias = []
        for _, row in df_aluno.iterrows():
            for competencia in _competencias_relatorio(row, serie_aluno):
                if competencia not in competencias:
                    competencias.append(competencia)
        for competencia in competencias:
            itens = df_aluno[
                df_aluno.apply(lambda row: competencia in _competencias_relatorio(row, serie_aluno), axis=1)
            ]
            if not itens.empty:
                grupos.append((competencia, itens))
        return grupos

    df_tmp = df_aluno.copy()
    df_tmp["_materia_base"] = df_tmp["materia"].apply(_materia_base_relatorio)
    for materia in df_tmp["_materia_base"].unique().tolist():
        grupos.append((materia, df_tmp[df_tmp["_materia_base"] == materia]))
    return grupos


def _inferir_modo_relatorio(row) -> str:
    modo = str(row.get("modo", "") or "").strip().lower()
    if modo:
        return modo

    materia = str(row.get("materia", "") or "").strip().upper()
    if materia.startswith("RPG-"):
        return "rpg"
    if materia.startswith("LAB-"):
        return "laboratorio"
    return "oraculo"


def _rotulo_modo_relatorio(modo: str) -> str:
    mapa = {
        "oraculo": "Oraculo",
        "treino": "Modo Treino",
        "laboratorio": "Laboratorio",
        "rpg": "RPG",
    }
    return mapa.get(str(modo or "").strip().lower(), "Geral")


def _texto_periodo_relatorio(df_aluno) -> str:
    if "data_hora" not in df_aluno.columns or df_aluno.empty:
        return "Periodo nao disponivel"

    valores = [str(v).strip() for v in df_aluno["data_hora"].tolist() if str(v).strip()]
    if not valores:
        return "Periodo nao disponivel"

    datas = []
    for valor in valores:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                datas.append(datetime.strptime(valor, fmt))
                break
            except Exception:
                continue

    if not datas:
        return "Periodo nao disponivel"

    inicio = min(datas).strftime("%d/%m/%Y")
    fim = max(datas).strftime("%d/%m/%Y")
    return f"{inicio} a {fim}"


def _tempo_medio_relatorio(df_aluno) -> float:
    if "tempo_resposta" not in df_aluno.columns or df_aluno.empty:
        return 0.0
    valores = []
    for valor in df_aluno["tempo_resposta"].tolist():
        tempo = tempo_resposta_para_media(valor)
        if tempo is not None:
            valores.append(tempo)
    return round(sum(valores) / len(valores), 1) if valores else 0.0


def _contagem_modos_relatorio(df_aluno) -> dict[str, int]:
    contagens = {"oraculo": 0, "treino": 0, "laboratorio": 0, "rpg": 0}
    if df_aluno.empty:
        return contagens
    for _, row in df_aluno.iterrows():
        modo = _inferir_modo_relatorio(row)
        if modo in contagens:
            contagens[modo] += 1
    return contagens


def _resumo_materias_relatorio(df_aluno) -> list[tuple[str, int, int]]:
    if df_aluno.empty:
        return []

    resumo = {}
    for _, row in df_aluno.iterrows():
        materia = _materia_base_relatorio(row.get("materia", "")) or "Geral"
        bucket = resumo.setdefault(materia, {"total": 0, "acertos": 0})
        bucket["total"] += 1
        if str(row.get("resultado", "")).strip() == "Acertou":
            bucket["acertos"] += 1

    itens = []
    for materia, dados in resumo.items():
        total = dados["total"]
        pct = int(dados["acertos"] / total * 100) if total > 0 else 0
        itens.append((materia, pct, total))
    itens.sort(key=lambda item: (-item[1], item[0]))
    return itens


def _listas_destaque_relatorio(df_aluno, pct: int, erros: int) -> tuple[list[str], list[str]]:
    fortes: list[str] = []
    atencao: list[str] = []

    if pct >= 85:
        fortes.append("Aproveitamento excelente no recorte selecionado.")
    elif pct >= 70:
        fortes.append("Bom desempenho geral dentro do periodo filtrado.")
    else:
        atencao.append("Aproveitamento abaixo do ideal neste recorte.")

    tempo_medio = _tempo_medio_relatorio(df_aluno)
    if tempo_medio and tempo_medio <= 35:
        fortes.append(f"Boa agilidade de resposta: media de {tempo_medio}s por questao.")
    elif tempo_medio and tempo_medio >= 90:
        atencao.append(f"Tempo medio alto de resposta: {tempo_medio}s por questao.")

    materias = _resumo_materias_relatorio(df_aluno)
    if materias:
        melhor = materias[0]
        fortes.append(f"Melhor desempenho em {melhor[0]} ({melhor[1]}% de acertos).")
        pior = sorted(materias, key=lambda item: (item[1], item[0]))[0]
        if pior[1] < 70:
            atencao.append(f"Revisar {pior[0]}: aproveitamento atual de {pior[1]}%.")

    if erros == 0:
        fortes.append("Nenhuma questao errada no filtro selecionado.")
    elif erros >= max(3, len(df_aluno) // 2):
        atencao.append("Ha varias questoes para revisao guiada neste recorte.")

    if not fortes:
        fortes.append("Participacao registrada nas atividades filtradas.")
    if not atencao:
        atencao.append("Manter a consistencia e seguir praticando os temas do periodo.")

    return fortes[:3], atencao[:3]


_EXTENSOES_LOGO = (".png", ".jpg", ".jpeg")


def _compactar(texto: str) -> str:
    """"ETEC - Araçatuba" -> "etecaracatuba"."""
    limpo = unicodedata.normalize("NFKD", str(texto or ""))
    limpo = "".join(c for c in limpo if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", limpo.lower())


def _palavras_do_nome(texto: str) -> frozenset[str]:
    """"Educacional Delta" -> {"educacional", "delta"}.

    Compara por CONJUNTO porque a ordem em que o arquivo foi nomeado nao
    tem por que coincidir com a ordem do nome cadastrado: a logo da
    Educacional Delta chegou como "DeltaEducacional.jpg".

    Palavras de ate 2 letras saem fora ("de", "da"): nao identificam escola
    nenhuma e so atrapalhariam a comparacao.
    """
    limpo = unicodedata.normalize("NFKD", str(texto or ""))
    limpo = "".join(c for c in limpo if not unicodedata.combining(c))
    # nome de arquivo costuma vir grudado em CamelCase, sem separador:
    # "DeltaEducacional" precisa virar duas palavras para casar com
    # "Educacional Delta".
    limpo = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", limpo)
    return frozenset(p for p in re.split(r"[^a-z0-9]+", limpo.lower()) if len(p) > 2)


def _pastas_de_assets() -> list[Path]:
    base_dir = Path(__file__).resolve().parent
    return [base_dir / "assets", base_dir.parent / "assets", base_dir.parent.parent / "assets", Path("assets")]


def _localizar_logo(escola_nome: str = "") -> str | None:
    """A logo DA ESCOLA deste relatorio -- ou nenhuma.

    MELHORIA: antes isto procurava um arquivo unico, "logo_escola.png", e
    devolvia o mesmo para todo mundo. Com uma escola cadastrada ninguem
    notava; com duas, o relatorio da Educacional Delta sairia carimbado com
    a marca da ETEC. O arquivo, alias, ERA a logo da ETEC -- com um nome
    generico que escondia isso.

    Este arquivo ja carrega a cicatriz da mesma falha uma vez: havia um
    "SALESIANO" fixo como texto de reserva, que aparecia no relatorio de
    qualquer outra escola (ver _cabecalho). E a terceira vez que a marca de
    uma escola vaza para a de outra por aqui.

    Nao ha reserva generica de proposito: quando nao existe logo da escola,
    devolver None e melhor que devolver a logo de OUTRA escola. Quem chama
    ja trata a ausencia -- escreve o nome da propria escola no lugar.

    O arquivo e reconhecido pelo nome: "EtecAracatuba.png" para
    "ETEC - Araçatuba", "DeltaEducacional.jpg" para "Educacional Delta".
    """
    alvo_compacto = _compactar(escola_nome)
    alvo_palavras = _palavras_do_nome(escola_nome)
    if not alvo_compacto:
        return None

    for pasta in _pastas_de_assets():
        try:
            if not pasta.is_dir():
                continue
            for arquivo in sorted(pasta.iterdir()):
                if arquivo.suffix.lower() not in _EXTENSOES_LOGO:
                    continue
                if _compactar(arquivo.stem) == alvo_compacto:
                    return str(arquivo)
                if alvo_palavras and _palavras_do_nome(arquivo.stem) == alvo_palavras:
                    return str(arquivo)
        except Exception:
            continue
    return None


def _data_local(user_tz=None):
    try:
        import pytz

        if user_tz:
            tz = pytz.timezone(str(user_tz)) if isinstance(user_tz, str) else user_tz
            return datetime.now(tz)
    except Exception:
        pass
    return datetime.now()


def _pct(valor, total):
    return int((valor / total) * 100) if total else 0


def _nivel_desempenho(pct: int) -> str:
    if pct >= 85:
        return "Excelente"
    if pct >= 70:
        return "Muito bom"
    if pct >= 50:
        return "Em desenvolvimento"
    return "Precisa de reforco"


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("RelatorioTitle", parent=styles["Title"], fontName=FONT_BOLD, fontSize=22, leading=26, textColor=AZUL_ESCURO, alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("RelatorioSubtitle", parent=styles["Normal"], fontName=FONT_NORMAL, fontSize=10, leading=13, textColor=AZUL_INSTITUCIONAL, alignment=TA_LEFT),
        "section": ParagraphStyle("RelatorioSection", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=12, leading=15, textColor=VERMELHO_INSTITUCIONAL, spaceBefore=10, spaceAfter=7),
        "group": ParagraphStyle("RelatorioGroup", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=11, leading=14, textColor=AZUL_ESCURO, spaceBefore=8, spaceAfter=4),
        "heading": ParagraphStyle("RelatorioHeading", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=11, leading=14, textColor=AZUL_ESCURO, spaceBefore=6, spaceAfter=4),
        "normal": ParagraphStyle("RelatorioNormal", parent=styles["Normal"], fontName=FONT_NORMAL, fontSize=8.7, leading=11.5, textColor=CINZA_TEXTO, alignment=TA_LEFT),
        "small": ParagraphStyle("RelatorioSmall", parent=styles["Normal"], fontName=FONT_NORMAL, fontSize=7.5, leading=9.5, textColor=CINZA_MEDIO, alignment=TA_LEFT),
        "label": ParagraphStyle("RelatorioLabel", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.2, leading=10.5, textColor=AZUL_ESCURO),
        "metric_value": ParagraphStyle("RelatorioMetricValue", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=17, leading=20, textColor=AZUL_ESCURO, alignment=TA_CENTER),
        "metric_label": ParagraphStyle("RelatorioMetricLabel", parent=styles["Normal"], fontName=FONT_NORMAL, fontSize=8, leading=10, textColor=CINZA_TEXTO, alignment=TA_CENTER),
        "metric_note": ParagraphStyle("RelatorioMetricNote", parent=styles["Normal"], fontName=FONT_NORMAL, fontSize=7, leading=8.5, textColor=AZUL_INSTITUCIONAL, alignment=TA_CENTER),
    }


class HRFlowable(Flowable):
    def __init__(self, color=CINZA_BORDA, width=1):
        super().__init__()
        self.color = color
        self.width = width
        self.height = 6

    def wrap(self, availWidth, availHeight):
        self._availWidth = availWidth
        return availWidth, self.height

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.width)
        self.canv.line(0, 3, self._availWidth, 3)


def _on_page(canvas: Canvas, doc):
    largura, altura = A4
    canvas.saveState()
    canvas.setFillColor(AZUL_ESCURO)
    canvas.rect(largura - 23 * mm, altura - 42 * mm, 23 * mm, 42 * mm, stroke=0, fill=1)
    canvas.setFillColor(VERMELHO_INSTITUCIONAL)
    canvas.circle(largura - 13 * mm, altura - 10 * mm, 26 * mm, stroke=0, fill=1)
    canvas.setFillColor(BRANCO)
    canvas.circle(largura - 18 * mm, altura - 15 * mm, 25 * mm, stroke=0, fill=1)
    canvas.setFillColor(AZUL_ESCURO)
    canvas.rect(0, 0, largura, 14 * mm, stroke=0, fill=1)
    canvas.setFillColor(VERMELHO_INSTITUCIONAL)
    canvas.rect(0, 13.5 * mm, largura, 1.1 * mm, stroke=0, fill=1)
    canvas.setFont(FONT_BOLD, 8)
    canvas.setFillColor(BRANCO)
    canvas.drawString(15 * mm, 5 * mm, "EducaGame IA")
    canvas.setFont(FONT_NORMAL, 7)
    canvas.drawCentredString(largura / 2, 5 * mm, "Aprender e uma jornada. Vamos juntos?")
    canvas.drawRightString(largura - 15 * mm, 5 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def _cabecalho(titulo: str, subtitulo: str, escola_nome: str):
    styles = _styles()
    logo_path = _localizar_logo(escola_nome)
    if logo_path:
        logo = Image(logo_path, width=34 * mm, height=27 * mm, kind="proportional")
    else:
        # MELHORIA: aqui havia "SALESIANO" fixo como texto de fallback --
        # a marca da escola antiga apareceria no relatorio de qualquer
        # outra escola sempre que a logo nao fosse encontrada. Usa o nome
        # da propria escola do relatorio.
        logo = Paragraph(f"<b>{_xml(escola_nome)}</b>", styles["group"])
    bloco_titulo = [
        Paragraph(_xml(titulo), styles["title"]),
        Paragraph(_xml(subtitulo), styles["subtitle"]),
        Paragraph(f"<font color='#6B7280'>{_xml(escola_nome)}</font>", styles["small"]),
    ]
    tabela = Table([[logo, bloco_titulo]], colWidths=[42 * mm, 123 * mm])
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabela


def _info_box(esquerda: list[tuple[str, str]], direita: list[tuple[str, str]]):
    styles = _styles()

    def linhas(itens):
        return [Paragraph(f"<b>{_xml(label)}</b><br/><font color='#133C8B'>{_xml(valor)}</font>", styles["normal"]) for label, valor in itens]

    tabela = Table([[linhas(esquerda), linhas(direita)]], colWidths=[82 * mm, 82 * mm])
    tabela.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, CINZA_BORDA),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LINEBEFORE", (1, 0), (1, 0), 0.8, CINZA_BORDA),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return tabela


def _metric_card(valor: str, rotulo: str, detalhe: str = "", cor_valor=AZUL_ESCURO, fundo=BRANCO):
    styles = _styles()
    value_style = ParagraphStyle("metricValueCustom", parent=styles["metric_value"], textColor=cor_valor)
    data = [[Paragraph(_xml(valor), value_style)], [Paragraph(_xml(rotulo), styles["metric_label"])], [Paragraph(_xml(detalhe), styles["metric_note"])]]
    table = Table(data, colWidths=[38 * mm], rowHeights=[10 * mm, 7 * mm, 7 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, CINZA_BORDA),
        ("BACKGROUND", (0, 0), (-1, -1), fundo),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _linha_metricas(cards):
    tabela = Table([cards], colWidths=[40 * mm] * len(cards))
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tabela


def _status_badge(resultado: str):
    styles = _styles()
    acertou = str(resultado).strip().lower() == "acertou"
    cor = VERDE if acertou else VERMELHO_INSTITUCIONAL
    fundo = VERDE_CLARO if acertou else VERMELHO_CLARO
    texto = "CORRETA" if acertou else "ERRADA"
    p = Paragraph(f"<b>{texto}</b>", ParagraphStyle("badge", parent=styles["small"], textColor=cor, alignment=TA_CENTER))
    t = Table([[p]], colWidths=[24 * mm], rowHeights=[6 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fundo),
        ("BOX", (0, 0), (-1, -1), 0.6, cor),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _questao_card(contador: int, row):
    styles = _styles()
    resultado = str(row.get("resultado", "")).strip()
    acertou = resultado.lower() == "acertou"
    materia_base = _materia_base_relatorio(row.get("materia", ""))
    modo_label_item = _rotulo_modo_relatorio(_inferir_modo_relatorio(row))
    tempo_txt = ""
    try:
        tempo_val = float(row.get("tempo_resposta", 0) or 0)
        if tempo_val > 0:
            tempo_txt = f" | Tempo: {round(tempo_val, 1)}s"
    except Exception:
        tempo_txt = ""

    pergunta = _xml(row.get("pergunta_texto", ""))
    resposta_aluno = _xml(row.get("resposta_aluno", ""))
    resposta_correta = _xml(row.get("resposta_correta", ""))
    exp_raw = row.get("explicacao_ia", "")
    exp_txt = _xml(_blocos_para_texto(exp_raw) if isinstance(exp_raw, (list, str)) else str(exp_raw))

    titulo = Paragraph(f"<b>Questao {contador}</b> <font color='#6B7280'>| {_xml(materia_base)} | {_xml(modo_label_item + tempo_txt)}</font>", styles["label"])
    resposta_cor = VERDE if acertou else VERMELHO_INSTITUCIONAL
    resposta_style = ParagraphStyle("resp", parent=styles["normal"], textColor=resposta_cor)
    conteudo = [
        [titulo, _status_badge(resultado)],
        [Paragraph(f"<b>Pergunta:</b> {pergunta}", styles["normal"]), ""],
        [Paragraph(f"<b>Sua resposta:</b> {resposta_aluno}", resposta_style), ""],
        [Paragraph(f"<b>Gabarito:</b> <font color='#15803D'>{resposta_correta}</font>", styles["normal"]), ""],
        [Paragraph(f"<b>Explicacao:</b> {exp_txt}", styles["small"]), ""],
    ]
    table = Table(conteudo, colWidths=[132 * mm, 28 * mm])
    table.setStyle(TableStyle([
        ("SPAN", (0, 1), (1, 1)),
        ("SPAN", (0, 2), (1, 2)),
        ("SPAN", (0, 3), (1, 3)),
        ("SPAN", (0, 4), (1, 4)),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.7, CINZA_BORDA),
        ("LINEABOVE", (0, 1), (-1, 1), 0.5, CINZA_BORDA),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return KeepTogether([table, Spacer(1, 5)])


def _tabela_resumo_materias(df_aluno):
    styles = _styles()
    if df_aluno is None or df_aluno.empty:
        return None
    df_tmp = df_aluno.copy()
    df_tmp["_materia_base"] = df_tmp["materia"].apply(_materia_base_relatorio)
    data = [[Paragraph("<b>Materia</b>", styles["small"]), Paragraph("<b>Acertos</b>", styles["small"]), Paragraph("<b>Total</b>", styles["small"]), Paragraph("<b>Aproveitamento</b>", styles["small"])]]
    for materia in df_tmp["_materia_base"].unique().tolist():
        df_m = df_tmp[df_tmp["_materia_base"] == materia]
        total = len(df_m)
        acertos = len(df_m[df_m["resultado"] == "Acertou"])
        pct = _pct(acertos, total)
        data.append([
            Paragraph(_xml(materia), styles["small"]),
            Paragraph(str(acertos), styles["small"]),
            Paragraph(str(total), styles["small"]),
            Paragraph(f"{pct}%", styles["small"]),
        ])
    tabela = Table(data, colWidths=[76 * mm, 27 * mm, 22 * mm, 39 * mm], repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
        ("TEXTCOLOR", (0, 0), (-1, 0), AZUL_ESCURO),
        ("GRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_FUNDO]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tabela


def _tabela_insights(fortes: list[str], atencao: list[str]):
    styles = _styles()
    fortes_html = "<br/>".join(f"• {_xml(item)}" for item in fortes) if fortes else "• Sem destaques"
    atencao_html = "<br/>".join(f"• {_xml(item)}" for item in atencao) if atencao else "• Sem alertas"
    tabela = Table([[
        Paragraph(f"<b>Pontos fortes</b><br/><br/>{fortes_html}", styles["small"]),
        Paragraph(f"<b>Pontos a desenvolver</b><br/><br/>{atencao_html}", styles["small"]),
    ]], colWidths=[82 * mm, 82 * mm])
    tabela.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, CINZA_BORDA),
        ("LINEBEFORE", (1, 0), (1, 0), 0.8, CINZA_BORDA),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return tabela


def _resumo_areas_bncc_em(df_aluno, serie_aluno: str) -> list[tuple[str, int]]:
    if df_aluno is None or df_aluno.empty or get_serie_tipo(serie_aluno) != "EM":
        return []

    resumo: dict[str, dict[str, int]] = {}
    for _, row in df_aluno.iterrows():
        area = get_area_da_materia(_materia_base_relatorio(row.get("materia", "")), serie_aluno)
        if not area or area == "Area nao identificada":
            continue
        bucket = resumo.setdefault(area, {"total": 0, "acertos": 0})
        bucket["total"] += 1
        if str(row.get("resultado", "")).strip() == "Acertou":
            bucket["acertos"] += 1

    itens = []
    for area, dados in resumo.items():
        pct = _pct(dados["acertos"], dados["total"])
        itens.append((area, pct))
    itens.sort(key=lambda item: item[0])
    return itens


class RadarBNCCFlowable(Flowable):
    def __init__(self, areas_pct: list[tuple[str, int]], meta_pct: int = 90):
        super().__init__()
        self.areas_pct = areas_pct[:]
        self.meta_pct = meta_pct
        self.width = 170 * mm
        self.height = 95 * mm

    def draw(self):
        if not self.areas_pct:
            return

        drawing = Drawing(self.width, self.height)
        cx = 45 * mm
        cy = 42 * mm
        radius = 24 * mm
        axes = len(self.areas_pct)
        step = 360 / axes if axes else 0

        def point_for(idx: int, pct: float, extra: float = 0):
            import math

            angle_deg = -90 + idx * step
            angle = math.radians(angle_deg)
            r = radius * (pct / 100.0) + extra
            return (cx + r * math.cos(angle), cy + r * math.sin(angle))

        for level in (25, 50, 75, 100):
            pts = []
            for idx in range(axes):
                x, y = point_for(idx, level)
                pts.extend([x, y])
            drawing.add(Polygon(pts, strokeColor=CINZA_BORDA, fillColor=None, strokeWidth=0.6))

        for idx, (area, pct) in enumerate(self.areas_pct):
            x, y = point_for(idx, 100)
            drawing.add(Line(cx, cy, x, y, strokeColor=CINZA_BORDA, strokeWidth=0.6))
            lx, ly = point_for(idx, 100, 8 * mm)
            rotulo = area.replace(" e suas Tecnologias", "").replace(" e Sociais Aplicadas", "")
            drawing.add(String(lx, ly, rotulo, fontName=FONT_NORMAL, fontSize=7.5, fillColor=CINZA_TEXTO, textAnchor="middle"))
            vx, vy = point_for(idx, pct, 4 * mm)
            drawing.add(String(vx, vy, f"{pct}%", fontName=FONT_BOLD, fontSize=8, fillColor=AZUL_ESCURO, textAnchor="middle"))

        meta_pts = []
        desempenho_pts = []
        for idx, (_, pct) in enumerate(self.areas_pct):
            mx, my = point_for(idx, self.meta_pct)
            dx, dy = point_for(idx, pct)
            meta_pts.extend([mx, my])
            desempenho_pts.extend([dx, dy])
            drawing.add(Circle(dx, dy, 2.2, fillColor=AZUL_ESCURO, strokeColor=AZUL_ESCURO))

        drawing.add(Polygon(meta_pts, strokeColor=CINZA_MEDIO, fillColor=None, strokeWidth=1, strokeDashArray=[3, 2]))
        drawing.add(Polygon(desempenho_pts, strokeColor=VERMELHO_INSTITUCIONAL, fillColor=None, strokeWidth=1.6))

        legenda_x = 88 * mm
        legenda_y = 22 * mm
        drawing.add(Line(legenda_x, legenda_y, legenda_x + 12 * mm, legenda_y, strokeColor=VERMELHO_INSTITUCIONAL, strokeWidth=1.6))
        drawing.add(String(legenda_x + 15 * mm, legenda_y - 2, "Desempenho", fontName=FONT_NORMAL, fontSize=8, fillColor=CINZA_TEXTO))
        drawing.add(Line(legenda_x, legenda_y - 8 * mm, legenda_x + 12 * mm, legenda_y - 8 * mm, strokeColor=CINZA_MEDIO, strokeWidth=1, strokeDashArray=[3, 2]))
        drawing.add(String(legenda_x + 15 * mm, legenda_y - 8 * mm - 2, f"Meta {self.meta_pct}%", fontName=FONT_NORMAL, fontSize=8, fillColor=CINZA_TEXTO))

        renderPDF.draw(drawing, self.canv, 0, 0)


def _bloco_radar_bncc(df_aluno, serie_aluno: str):
    areas_pct = _resumo_areas_bncc_em(df_aluno, serie_aluno)
    if not areas_pct:
        return None

    styles = _styles()
    radar = RadarBNCCFlowable(areas_pct, meta_pct=90)
    resumo_linhas = []
    for area, pct in areas_pct:
        status = "Atingiu a meta" if pct >= 90 else f"Faltam {90 - pct} p.p. para a meta"
        resumo_linhas.append(Paragraph(f"<b>{_xml(area)}</b>: {_xml(str(pct) + '%')}<br/><font color='#6B7280'>{_xml(status)}</font>", styles["small"]))

    tabela = Table([[radar, resumo_linhas]], colWidths=[92 * mm, 72 * mm])
    tabela.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, CINZA_BORDA),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LINEBEFORE", (1, 0), (1, 0), 0.8, CINZA_BORDA),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tabela
