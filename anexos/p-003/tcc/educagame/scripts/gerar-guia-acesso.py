"""Gera o PDF do guia de acesso que acompanha uma avaliação externa.

Uso:
    # pergunta as duas senhas sem ecoar
    python scripts/gerar_guia_acesso.py --escola deltaata \
        --aluno alunodelta --professor professordelta

    # sorteia senhas NOVAS e grava o hash (é como se troca depois da avaliação)
    python scripts/gerar_guia_acesso.py --escola deltaata \
        --aluno alunodelta --professor professordelta --redefinir --confirmar

MELHORIA: o guia da Educacional Delta era um PDF avulso, montado uma vez e
sem fonte nenhuma no repositório. Quando o login mudou -- o `?escola=` na URL
deixou de escolher a escola, e passou a haver uma tela pedindo o código -- não
havia arquivo para atualizar nem teste para reclamar. O documento continuou
circulando com **três** afirmações erradas, e o diretor travaria na primeira
tela:

  1. mandava abrir `educagame.onrender.com/?escola=deltaata`, endereço cujo
     parâmetro hoje é ignorado (`web/routes/home_fla.py::_slug_da_sessao`);
  2. não mencionava o código da escola, que agora é obrigatório;
  3. dizia que "a conta de professor não está presa a uma escola -- quem
     define a escola é o endereço pelo qual se entra". Isso ficou EXATAMENTE
     invertido por `services/auth_service.py::conta_pode_entrar`: a conta é
     presa, e entrar por outra unidade é recusado. O guia descrevia como
     funcionalidade justamente o defeito que foi corrigido.

Por isso o texto do guia mora aqui como dado, e não dentro do PDF: assim
`tests/test_guia_de_acesso.py` consegue cobrar que ele continue batendo com o
que as rotas fazem.

As senhas: o banco guarda só o hash, então elas existem legíveis apenas neste
PDF. Ou você informa as que já valem -- o script pergunta, sem eco -- ou pede
`--redefinir`, que sorteia novas, grava o hash e imprime as novas aqui. É este
o caminho para trocar as senhas quando a avaliação terminar.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Sob o pytest nao: tests/test_guia_de_acesso.py importa este script, e o .env
# lido aqui valia para toda a suite dali em diante (chaves de IA reais).
if "pytest" not in sys.modules:
    load_dotenv(override=True)

import core.ajuda as ajuda  # noqa: E402
from core.sessao import MINUTOS_INATIVIDADE_PADRAO  # noqa: E402
from services.auth_service import conta_pode_entrar  # noqa: E402
from services.escola_service import listar_escolas  # noqa: E402

# O guia não pode citar um endereço que escolha a escola sozinho: os três
# atalhos (`?escola=`, `/e/<slug>` e DEFAULT_ESCOLA_SLUG) saíram justamente
# para que ninguém entre sem digitar o código. Ver o teste.
ENDERECO = ajuda.ENDERECO
URL_LIMPA = ajuda.URL_LIMPA


def passos_de_entrada(slug: str) -> list[tuple[str, str]]:
    """Os quatro passos da tela, na ordem em que aparecem.

    A ordem importa e é a razão de o guia antigo travar: escola e código vêm
    ANTES do usuário e da senha.

    MELHORIA: o texto vinha escrito aqui, e a ajuda dentro do app precisava
    dos mesmos quatro passos. Duas cópias das mesmas instruções é exatamente
    como este guia envelheceu da primeira vez -- então o texto passou a morar
    em core/ajuda.py, sem marcação, e este arquivo só embrulha para o
    ReportLab. O negrito é aplicado sobre tokens conhecidos (a URL e o
    código), e não escrito no meio da frase, senão o mesmo texto não serviria
    ao HTML.
    """
    passos = ajuda.passos_de_entrada(nome_escola="{nome}", codigo=f"o código da escola: {slug}")
    marcados = []
    for numero, texto in enumerate(passos, 1):
        texto = texto.replace(ajuda.URL_LIMPA, f"<b>{ajuda.URL_LIMPA}</b>")
        texto = texto.replace("{nome}", "<b>{nome}</b>")
        texto = texto.replace(slug, f"<font face='Courier-Bold'>{slug}</font>")
        marcados.append((str(numero), texto))
    return marcados


# Reexportados de core/ajuda.py: a ajuda DENTRO do app mostra os mesmos
# modos, o mesmo aviso de espera e o mesmo de sessao. Duas copias do mesmo
# texto foi exatamente como este guia envelheceu da primeira vez.
TEXTO_ESPERA = ajuda.TEXTO_ESPERA
TEXTO_SESSAO = ajuda.TEXTO_SESSAO
TEXTO_QUESTOES = ajuda.TEXTO_QUESTOES
MODOS = ajuda.MODOS
PAINEL_PROFESSOR = ajuda.PAINEL_PROFESSOR


def texto_conta_presa(nome: str) -> str:
    pode, motivo = conta_pode_entrar(
        {"role": "professor", "escola_id": "escola-da-conta"}, "outra-escola"
    )
    if pode:
        return (
            f"A conta de professor desta avaliação <b>não</b> está presa à {nome}: entrando "
            "pelo código de outra unidade, o painel daquela unidade abre do mesmo jeito. "
            "Entre sempre pelo código correto."
        )
    return (
        f"Cada conta pertence a uma escola. A conta de professor desta avaliação pertence à "
        f"{nome}: entrando pelo código de outra unidade, o sistema recusa o login com a "
        f"mensagem <i>“{motivo}”</i> — o painel de uma escola não alcança os alunos da outra."
    )


def roteiro(slug: str) -> list[str]:
    return [
        f"Abra {ENDERECO}, escolha a escola, digite o código <b>{slug}</b> e entre como aluno.",
        "Faça algumas questões no Treino Rápido — é o caminho mais curto para ver o sistema funcionando.",
        "Abra o Laboratório de Exatas para ver a resolução passo a passo, e o Oráculo ou o RPG para ver o lado de jogo.",
        "Saia, repita a escolha da escola e o código, e entre como professor: o painel já mostrará o que acabou de ser feito.",
    ]


# ====================== O PDF ======================


def gerar_pdf(escola: dict, contas: list[dict], caminho: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    from services.relatorios.commons import _localizar_logo

    nome = str(escola.get("nome") or "")
    slug = str(escola.get("slug") or "")

    titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=16, spaceAfter=3)
    secao = ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=12.5, spaceBefore=7, spaceAfter=4)
    corpo = ParagraphStyle("corpo", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=4)
    sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#555555"))
    aviso = ParagraphStyle(
        "aviso", parent=corpo, fontSize=9.5, leading=13,
        backColor=colors.HexColor("#FBF6E9"), borderColor=colors.HexColor("#C5BAA3"),
        borderWidth=0.5, borderPadding=6, spaceBefore=4, spaceAfter=6,
    )
    item_nome = ParagraphStyle("inome", fontName="Helvetica-Bold", fontSize=9.5, leading=12)
    item_txt = ParagraphStyle("itxt", fontName="Helvetica", fontSize=9.5, leading=12)

    doc = SimpleDocTemplate(
        str(caminho), pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=13 * mm,
        title=f"EducaGame - guia de acesso - {nome}",
    )

    cabecalho_texto = [
        Paragraph("EducaGame — guia de acesso", titulo),
        Paragraph(f"{nome} · material para avaliação da direção", sub),
    ]
    logo = _localizar_logo(nome)
    if logo:
        tabela_cab = Table(
            [[Image(logo, width=26 * mm, height=20 * mm, kind="proportional"), cabecalho_texto]],
            colWidths=[30 * mm, 148 * mm],
        )
        tabela_cab.setStyle(
            TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0)])
        )
        el = [tabela_cab, Spacer(1, 6 * mm)]
    else:
        el = [*cabecalho_texto, Spacer(1, 6 * mm)]

    # ---------- 1. Como entrar ----------
    el.append(Paragraph("1. Como entrar", secao))
    el.append(
        Paragraph(
            "O acesso é pelo navegador, no computador ou no celular. Não precisa instalar nada. "
            "São quatro passos, e os dois primeiros são novos — o endereço sozinho não abre mais "
            "a escola.",
            corpo,
        )
    )
    linhas_passos = [
        [Paragraph(f"<b>{n}</b>", item_nome), Paragraph(texto.format(nome=nome), item_txt)]
        for n, texto in passos_de_entrada(slug)
    ]
    tabela_passos = Table(linhas_passos, colWidths=[8 * mm, 170 * mm])
    tabela_passos.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    el += [tabela_passos, Spacer(1, 3 * mm)]
    el.append(Paragraph(f"<b>A primeira abertura demora.</b> {TEXTO_ESPERA}", aviso))
    el.append(
        Paragraph(TEXTO_SESSAO.format(minutos=int(MINUTOS_INATIVIDADE_PADRAO)), aviso)
    )

    # ---------- 2. Acessos ----------
    el.append(Paragraph("2. Acessos criados para esta avaliação", secao))
    el.append(
        Paragraph(
            "São duas contas: uma para ver o sistema como o aluno vê, outra para ver o painel do "
            "professor. Recomendamos começar pela de aluno — assim o painel do professor já terá "
            "dados para mostrar.",
            corpo,
        )
    )

    linhas = [["Perfil", "Código da escola", "Usuário", "Senha", "O que abre"]]
    for conta in contas:
        linhas.append(
            [conta["perfil"], slug, conta["username"], conta["senha"], conta["abre"]]
        )
    tabela = Table(linhas, colWidths=[24 * mm, 30 * mm, 32 * mm, 24 * mm, 68 * mm], repeatRows=1)
    tabela.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFE9DC")),
                ("FONTNAME", (1, 1), (3, -1), "Courier-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C5BAA3")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F5EC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    el += [tabela, Spacer(1, 3 * mm)]
    el.append(
        Paragraph(
            "As senhas foram sorteadas e não usam letras que se confundem no papel (sem i, l, o, "
            "zero ou um). Elas são guardadas cifradas no banco: <b>este documento é o único lugar "
            "onde aparecem legíveis</b>. Vale trocar depois da avaliação.",
            sub,
        )
    )
    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph(texto_conta_presa(nome), aviso))

    # ---------- 3. O aluno ----------
    el.append(PageBreak())
    el.append(Paragraph("3. O que o aluno encontra", secao))
    el.append(
        Paragraph(
            "Ao entrar, o aluno vê um menu dividido em três partes. Todas as questões respeitam a "
            "série da conta: o Ensino Médio recebe conteúdo de Ensino Médio, e o Fundamental tem "
            "regras próprias que impedem, por exemplo, equação do 2º grau aparecer para o 7º ano.",
            corpo,
        )
    )
    for grupo, itens in MODOS:
        el.append(Paragraph(grupo, ParagraphStyle("g", parent=corpo, fontName="Helvetica-Bold", spaceBefore=4)))
        el.append(_tabela_de_itens(itens, item_nome, item_txt))
    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph("<b>De onde vêm as questões.</b> " + TEXTO_QUESTOES, corpo))

    # ---------- 4. O professor ----------
    el.append(Paragraph("4. O painel do professor", secao))
    el.append(
        Paragraph(
            "Entrando com a conta de professor, a tela inicial é o painel de gestão da turma. Ele "
            "reúne o que foi feito pelos alunos daquela escola.",
            corpo,
        )
    )
    el.append(_tabela_de_itens(PAINEL_PROFESSOR, item_nome, item_txt))

    # ---------- Roteiro ----------
    # KeepTogether: sem ele o roteiro partia entre páginas e sobravam duas
    # linhas órfãs numa terceira página. São quatro passos numerados que a
    # pessoa segue com o computador na frente -- partidos ao meio, ela perde
    # o fio virando a folha.
    bloco_roteiro = [Paragraph("Sugestão de roteiro para a avaliação", secao)]
    bloco_roteiro += [
        Paragraph(f"{i}. {passo}", corpo) for i, passo in enumerate(roteiro(slug), start=1)
    ]
    bloco_roteiro += [
        Spacer(1, 4 * mm),
        Paragraph(
            "Em caso de dúvida ou de algo que não funcione como esperado, fale com "
            "Lucas Barbosa Nishigima.",
            sub,
        ),
    ]
    el.append(KeepTogether(bloco_roteiro))

    doc.build(el)


def _tabela_de_itens(itens, estilo_nome, estilo_texto):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    linhas = [
        [Paragraph(nome, estilo_nome), Paragraph(texto, estilo_texto)] for nome, texto in itens
    ]
    tabela = Table(linhas, colWidths=[42 * mm, 136 * mm])
    tabela.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDD5C4")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabela


# ====================== AS SENHAS ======================


def _redefinir_senhas(escola: dict, username_aluno: str, username_professor: str) -> dict[str, str]:
    """Sorteia senhas novas e grava o hash. Devolve {username: senha}."""
    from repositories.usuario_repo import listar_usuarios
    from services.aluno_auth_service import redefinir_senha_do_aluno
    from services.dados_service import buscar_alunos
    from services.usuario_service import redefinir_senha_de_conta

    senhas: dict[str, str] = {}

    aluno = next(
        (a for a in (buscar_alunos(escola["id"]) or []) if str(a.get("username")) == username_aluno),
        None,
    )
    if not aluno:
        raise SystemExit(f"Aluno '{username_aluno}' não encontrado em {escola['nome']}.")
    ok, erro, senha = redefinir_senha_do_aluno(aluno["id"])
    if not ok:
        raise SystemExit(f"Não deu para redefinir o aluno: {erro}")
    senhas[username_aluno] = senha

    conta = next(
        (u for u in (listar_usuarios() or []) if str(u.get("username")) == username_professor),
        None,
    )
    if not conta:
        raise SystemExit(f"Conta '{username_professor}' não encontrada.")
    ok, erro, senha = redefinir_senha_de_conta(conta["id"])
    if not ok:
        raise SystemExit(f"Não deu para redefinir o professor: {erro}")
    senhas[username_professor] = senha

    return senhas


def _senha_de(username: str) -> str:
    """Pergunta a senha sem ecoar. O banco só tem o hash; ela vem de quem sabe.

    No Windows o getpass lê do console direto e ignora stdin canalizado: num
    script ou pipe ele fica esperando para sempre. Por isso `--senha-aluno` e
    `--senha-professor` continuam existindo -- são o caminho não interativo.
    """
    from getpass import getpass

    return getpass(f"senha atual de '{username}': ").strip()


def _argumentos():
    import argparse

    p = argparse.ArgumentParser(description="Gera o guia de acesso em PDF.")
    p.add_argument("--escola", required=True, help="slug da escola (ex: deltaata)")
    p.add_argument("--aluno", required=True, help="username da conta de aluno da demonstração")
    p.add_argument("--professor", required=True, help="username da conta de professor")
    # MELHORIA: senha em argumento vai parar no histórico do shell. Sem o
    # argumento, o script pergunta sem eco (ver _senha_de).
    #
    # Variável de ambiente foi tentada primeiro e descartada: ela teria de
    # entrar no .env.example, porque tests/test_env_example.py cobra que toda
    # variável lida esteja documentada -- e ali significaria convidar alguém a
    # guardar a senha em texto num arquivo que fica. O teste estava certo; a
    # ideia é que era ruim.
    p.add_argument("--senha-aluno", default="", help="a senha que já vale; sem isto, é perguntada")
    p.add_argument("--senha-professor", default="", help="idem, para a conta de professor")
    p.add_argument(
        "--redefinir",
        action="store_true",
        help="sorteia senhas NOVAS para as duas contas e grava o hash",
    )
    p.add_argument("--confirmar", action="store_true", help="sem isto, --redefinir só mostra o que faria")
    return p.parse_args()


def main() -> None:
    args = _argumentos()

    escolas = listar_escolas()
    escola = next((e for e in (escolas or []) if str(e.get("slug")) == args.escola), None)
    if not escola:
        disponiveis = ", ".join(str(e.get("slug")) for e in (escolas or []))
        raise SystemExit(f"Escola '{args.escola}' não encontrada. Slugs: {disponiveis}")

    if args.redefinir:
        print(f"vai TROCAR a senha de '{args.aluno}' e '{args.professor}'.")
        print("  as senhas atuais deixam de valer, inclusive as impressas no guia anterior.")
        if not args.confirmar:
            raise SystemExit("  ENSAIO: nada foi alterado. Repita com --confirmar para valer.")
        senhas = _redefinir_senhas(escola, args.aluno, args.professor)
    else:
        senhas = {
            args.aluno: args.senha_aluno or _senha_de(args.aluno),
            args.professor: args.senha_professor or _senha_de(args.professor),
        }
        if not all(senhas.values()):
            raise SystemExit(
                "Sem as senhas não dá para montar o guia, e o banco guarda só o hash: "
                "não há como o script descobrir a atual. Use --redefinir para sortear novas."
            )

    contas = [
        {
            "perfil": "Aluno",
            "username": args.aluno,
            "senha": senhas[args.aluno],
            "abre": "Os modos de estudo e de jogo",
        },
        {
            "perfil": "Professor",
            "username": args.professor,
            "senha": senhas[args.professor],
            "abre": "O painel de gestão da turma",
        },
    ]

    nome_arquivo = f"EducaGame_guia_acesso_{str(escola['nome']).replace(' ', '_').replace('-', '')}.pdf"
    destino = Path(__file__).resolve().parent.parent / nome_arquivo
    gerar_pdf(escola, contas, destino)
    print(f"PDF gerado: {destino}")


if __name__ == "__main__":
    main()
