"""Cria contas de aluno para teste de carga e gera um PDF com as credenciais.

Uso:
    python scripts/criar_alunos_teste.py --escola etecata [--quantidade 40]
    python scripts/criar_alunos_teste.py --escola etecata --recriar --confirmar

As senhas sao geradas aqui, gravadas no banco apenas como hash (via
services.aluno_auth_service.criar_aluno_com_username) e escritas em texto
plano SOMENTE no PDF, que serve para imprimir e entregar aos alunos.

MELHORIA: a escola era `listar_escolas()[0]` -- a primeira que o banco
devolvesse. Com uma escola so isso passava; com duas virou cara ou coroa, e o
erro so apareceria depois de 40 contas criadas na unidade errada. Agora o slug
e obrigatorio.

--recriar apaga as contas que este script criaria ANTES de criar de novo. Isso
leva junto os logs e o progresso de RPG delas (o CASCADE esta nas migracoes), e
por isso exige --confirmar: sem ele o script so MOSTRA o que faria. O alvo e
sempre o conjunto exato que o script gera -- nunca "todos os alunos da escola".
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Sob o pytest nao: um teste que importe este script levaria o .env (banco de
# producao, chaves de IA reais) para toda a suite dali em diante.
if "pytest" not in sys.modules:
    load_dotenv(override=True)

from flask_app import criar_app  # noqa: E402
from services.aluno_auth_service import criar_aluno_com_username, gerar_senha_legivel  # noqa: E402
from services.escola_service import listar_escolas  # noqa: E402

# Sem caracteres ambiguos no papel: nada de 0/O, 1/l/I.
SERIE = "1º Ano EM"
PERIODOS = ["Manhã", "Tarde"]


# MELHORIA: o gerador vivia aqui e o painel do desenvolvedor precisava do
# MESMO alfabeto (sem caracteres ambiguos, porque a senha vai impressa).
# Duas copias divergiriam na primeira vez que alguem mexesse numa so.
def gerar_senha() -> str:
    return gerar_senha_legivel()


def montar_alunos(
    quantidade: int,
    escola_id: str,
    *,
    primeiro: int = 1,
    serie: str = SERIE,
    periodo: str = "",
) -> list[dict]:
    """As contas que este script cria, numeradas a partir de `primeiro`.

    MELHORIA: comecava sempre em 1 e alternava Manha/Tarde. Uma SEGUNDA turma
    na mesma escola precisa das duas coisas que faltavam: continuar a
    numeracao -- senao colide com as contas que ja existem -- e ficar toda no
    mesmo periodo.

    Cuidado com `serie`: ela precisa conter "EM" para valer como Ensino
    Medio. Nao e capricho de formato -- sao TRES lugares lendo esse texto, e
    eles discordam:

        core.config.eh_ensino_medio("1º Ano A")        -> True   (Medio)
        core.config.get_materias_por_serie("1º Ano A") -> lista do Fundamental
        student_selector.html, etapaDoAno()            -> "ef"

    Ou seja, uma turma chamada "1º Ano A" perde Fisica, Quimica, Biologia,
    Filosofia e Sociologia, e ganha Ciencias e Ensino Religioso. Para separar
    turmas, escreva "1º Ano EM - A": a etapa continua certa e o nome da turma
    aparece no painel do professor do mesmo jeito.
    """
    alunos = []
    for i in range(primeiro, primeiro + quantidade):
        nome = f"Aluno {i:02d}"
        alunos.append(
            {
                "escola_id": escola_id,
                "nome": nome,
                "ra_identificacao": f"TESTE-{i:03d}",
                "ano_escolar": serie,
                "periodo": periodo or PERIODOS[(i - 1) % len(PERIODOS)],
                "username": nome.lower().replace(" ", ""),
                "senha": gerar_senha(),
                # Dado de teste sintetico ("Aluno 01", "Aluno 02"...), nao de
                # aluno real -- a autorizacao aqui e a de quem roda o script.
                "consentimento_responsavel": True,
            }
        )
    return alunos


def gerar_pdf(alunos: list[dict], escola_nome: str, escola_slug: str, caminho: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    estilo_titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=16, spaceAfter=4)
    estilo_sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#555555"))
    estilo_cartao_nome = ParagraphStyle("cnome", fontName="Helvetica-Bold", fontSize=11, spaceAfter=2)
    estilo_cartao_dado = ParagraphStyle("cdado", fontName="Helvetica", fontSize=10, leading=14)
    estilo_cartao_rodape = ParagraphStyle(
        "crod", fontName="Helvetica-Oblique", fontSize=7.5, textColor=colors.HexColor("#666666")
    )

    doc = SimpleDocTemplate(
        str(caminho),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title="EducaGame - Acessos dos alunos",
    )

    from reportlab.platypus import Image

    from services.relatorios.commons import _localizar_logo

    cabecalho_texto = [
        Paragraph("EducaGame — acessos dos alunos", estilo_titulo),
        Paragraph(
            f"{escola_nome} · {len(alunos)} contas · "
            f"educagame.onrender.com → escolha a escola → código <b>{escola_slug}</b> → usuário e senha",
            estilo_sub,
        ),
    ]
    # a logo e a DA ESCOLA do PDF -- ver services/relatorios/commons.py
    logo_path = _localizar_logo(escola_nome)
    if logo_path:
        cabecalho = Table(
            [[Image(logo_path, width=26 * mm, height=20 * mm, kind="proportional"), cabecalho_texto]],
            colWidths=[30 * mm, 152 * mm],
        )
        cabecalho.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
        elementos = [cabecalho, Spacer(1, 8 * mm)]
    else:
        elementos = [*cabecalho_texto, Spacer(1, 8 * mm)]

    # Tabela de controle do professor.
    linhas = [["#", "Nome", "Usuário", "Senha", "Série", "Período"]]
    for i, aluno in enumerate(alunos, start=1):
        linhas.append(
            [str(i), aluno["nome"], aluno["username"], aluno["senha"], aluno["ano_escolar"], aluno["periodo"]]
        )

    tabela = Table(linhas, colWidths=[10 * mm, 34 * mm, 30 * mm, 26 * mm, 30 * mm, 24 * mm], repeatRows=1)
    tabela.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE9DC")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#14161C")),
                ("FONTNAME", (3, 1), (3, -1), "Courier-Bold"),
                ("FONTNAME", (2, 1), (2, -1), "Courier"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C5BAA3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elementos += [
        tabela,
        Spacer(1, 4 * mm),
        Paragraph(
            f"O código da escola é o mesmo para todos: <b>{escola_slug}</b>. "
            "Ele é pedido depois de escolher a escola na lista, antes do usuário e da senha.",
            estilo_sub,
        ),
        PageBreak(),
    ]

    # Cartoes para recortar e entregar (2 colunas x 5 linhas por pagina).
    elementos.append(Paragraph("Recorte e entregue a cada aluno", estilo_titulo))
    elementos.append(Spacer(1, 5 * mm))

    def cartao(aluno: dict) -> list:
        # MELHORIA: o cartao dava usuario e senha e parava ai. Desde que o
        # slug voltou a ser exigido como codigo da escola, quem recebesse
        # este papel travaria na PRIMEIRA tela -- e nao teria como adivinhar.
        # A ordem abaixo e a ordem das telas: escola, depois conta.
        return [
            Paragraph(aluno["nome"], estilo_cartao_nome),
            Paragraph(
                f"<b>Código da escola:</b> <font face='Courier'>{escola_slug}</font>",
                estilo_cartao_dado,
            ),
            Paragraph(f"<b>Usuário:</b> <font face='Courier'>{aluno['username']}</font>", estilo_cartao_dado),
            Paragraph(f"<b>Senha:</b> <font face='Courier'>{aluno['senha']}</font>", estilo_cartao_dado),
            Paragraph("educagame.onrender.com", estilo_cartao_rodape),
        ]

    por_pagina = 10
    for inicio in range(0, len(alunos), por_pagina):
        bloco = alunos[inicio : inicio + por_pagina]
        linhas_cartoes = []
        for j in range(0, len(bloco), 2):
            par = bloco[j : j + 2]
            linhas_cartoes.append([cartao(par[0]), cartao(par[1]) if len(par) > 1 else ""])
        grade = Table(linhas_cartoes, colWidths=[91 * mm, 91 * mm], rowHeights=48 * mm)
        grade.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C5BAA3")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C5BAA3")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elementos.append(grade)
        if inicio + por_pagina < len(alunos):
            elementos.append(PageBreak())

    doc.build(elementos)


def _argumentos():
    import argparse

    parser = argparse.ArgumentParser(description="Cria contas de aluno de teste.")
    parser.add_argument("--escola", required=True, help="slug da escola (ex: etecata)")
    parser.add_argument("--quantidade", type=int, default=40)
    parser.add_argument(
        "--de",
        type=int,
        default=1,
        help="numero da primeira conta (ex: 41 para continuar depois de aluno40)",
    )
    parser.add_argument(
        "--serie",
        default=SERIE,
        help='serie das contas; mantenha "EM" para Ensino Medio (ex: "1º Ano EM - B")',
    )
    parser.add_argument(
        "--periodo",
        default="",
        help="periodo de TODAS as contas; sem isto, alterna Manha/Tarde",
    )
    parser.add_argument(
        "--recriar",
        action="store_true",
        help="apaga antes as contas que este script criaria (leva logs e RPG junto)",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="sem isto, --recriar apenas mostra o que faria",
    )
    return parser.parse_args()


def _apagar_existentes(escola: dict, alunos: list[dict], confirmar: bool) -> int:
    """Apaga so o conjunto que ESTE script cria, e so nesta escola.

    O alvo nunca e "todos os alunos da escola": as contas que entraram por
    e-mail, ou criadas a mao, ficam de fora por construcao.
    """
    from repositories.aluno_repo import excluir_aluno
    from services.dados_service import buscar_alunos

    alvo = {a["username"] for a in alunos}
    existentes = [
        a for a in (buscar_alunos(escola["id"]) or []) if str(a.get("username") or "") in alvo
    ]

    if not existentes:
        print("nada a apagar: nenhuma dessas contas existe ainda.")
        return 0

    print()
    print(f"vai APAGAR {len(existentes)} conta(s) em {escola['nome']}:")
    for aluno in existentes[:5]:
        print(f"    {aluno.get('username')}  ({aluno.get('nome')})")
    if len(existentes) > 5:
        print(f"    ... mais {len(existentes) - 5}")
    print("  os logs e o progresso de RPG dessas contas vao junto (CASCADE).")

    if not confirmar:
        print()
        print("  ENSAIO: nada foi apagado. Repita com --confirmar para valer.")
        raise SystemExit(0)

    apagados = 0
    for aluno in existentes:
        if excluir_aluno(aluno["id"]) is not None:
            apagados += 1
    print(f"  apagados: {apagados}")
    return apagados


# Erros de rede que passam sozinhos. O Supabase devolve 504 de vez em quando,
# e uma fila de 40 criacoes tem 40 chances de encontrar um.
_PASSAGEIROS = ("504", "502", "503", "timeout", "timed out", "gateway")


def _criar_insistindo(aluno: dict, tentativas: int = 4) -> tuple[bool, str]:
    """Cria a conta, insistindo enquanto o erro parecer de rede.

    MELHORIA: era uma chamada seca dentro do laco. Um 504 no meio do caminho
    deixava a conta sem criar e seguia em frente -- e a senha daquele aluno,
    que so existe em memoria ate virar PDF, ia embora com ele. Agora um
    tropeco de rede custa alguns segundos em vez de uma conta.
    """
    import time

    for tentativa in range(1, tentativas + 1):
        try:
            ok, erro = criar_aluno_com_username(**aluno)
        except Exception as exc:  # noqa: BLE001
            ok, erro = False, f"{type(exc).__name__}: {exc}"

        if ok or not any(m in str(erro).lower() for m in _PASSAGEIROS):
            return ok, erro
        if tentativa < tentativas:
            espera = 2 * tentativa
            print(f"  {aluno['username']}: erro passageiro; nova tentativa em {espera}s")
            time.sleep(espera)
    return False, erro


def main() -> None:
    args = _argumentos()

    escolas = listar_escolas()
    if not escolas:
        raise SystemExit("Nenhuma escola cadastrada.")
    escola = next((e for e in escolas if str(e.get("slug")) == args.escola), None)
    if not escola:
        disponiveis = ", ".join(str(e.get("slug")) for e in escolas)
        raise SystemExit(f"Escola '{args.escola}' nao encontrada. Slugs: {disponiveis}")

    alunos = montar_alunos(
        args.quantidade,
        escola["id"],
        primeiro=args.de,
        serie=args.serie,
        periodo=args.periodo,
    )
    print(
        f"escola: {escola['nome']} ({escola['slug']})  |  contas: {len(alunos)}"
        f"  |  {alunos[0]['username']} a {alunos[-1]['username']}"
        f"  |  {args.serie} | {args.periodo or 'Manhã/Tarde alternado'}"
    )
    if "EM" not in str(args.serie).upper() and "MEDIO" not in str(args.serie).upper():
        print(
            "  AVISO: a serie nao contem \"EM\". get_materias_por_serie vai entregar a\n"
            "  lista do Fundamental -- sem Fisica, Quimica, Biologia, Filosofia e\n"
            "  Sociologia. Ver o comentario em montar_alunos()."
        )

    if args.recriar:
        _apagar_existentes(escola, alunos, args.confirmar)

    app = criar_app()
    criados, falhas = [], []
    with app.test_request_context("/"):
        for aluno in alunos:
            ok, erro = _criar_insistindo(aluno)
            (criados if ok else falhas).append((aluno["username"], erro))

    print(f"criados: {len(criados)} | falhas: {len(falhas)}")
    for username, erro in falhas[:10]:
        print(f"  falhou {username}: {erro}")

    if criados:
        destino = Path(__file__).resolve().parent.parent / f"acessos_alunos_{escola['slug']}.pdf"
        usernames_ok = {u for u, _ in criados}
        gerar_pdf(
            [a for a in alunos if a["username"] in usernames_ok],
            escola["nome"],
            str(escola.get("slug") or ""),
            destino,
        )
        print(f"PDF gerado: {destino}")


if __name__ == "__main__":
    main()
