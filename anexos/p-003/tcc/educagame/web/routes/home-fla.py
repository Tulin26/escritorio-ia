from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, session, url_for

from services.auth_service import conta_pode_entrar
from services.escola_service import (
    MOTIVO_CODIGO_INCORRETO,
    buscar_escola_por_slug,
    codigo_confere,
    listar_escolas,
    mostra_guildas,
    normalizar_codigo_escola,
)

home_bp = Blueprint("home", __name__)

_AVISOS = {
    "sessao_expirada": (
        "Sua sessão expirou por inatividade. Escolha a escola e entre de novo."
    ),
}


def _slug_da_sessao() -> str:
    # MELHORIA: o slug chegava tambem por "?escola=" na URL, pela rota
    # "/e/<slug>" e por um DEFAULT_ESCOLA_SLUG no ambiente. Os tres eram
    # atalho para dentro: bastava o endereco certo e a escola ficava
    # escolhida sem ninguem digitar nada. Agora a unica origem e a sessao, e
    # so entra na sessao quem digitou o codigo em /entrar-escola.
    #
    # (O DEFAULT_ESCOLA_SLUG, alias, ja nao surtia efeito: index() decidia
    # mostrar a lista antes de consultar o padrao, entao ele nunca vencia.
    # Saiu do codigo e do .env.example junto.)
    return normalizar_codigo_escola(session.get("escola_slug"))


def carregar_escola_por_slug():
    slug = _slug_da_sessao()
    escola = buscar_escola_por_slug(slug)
    if escola:
        session["escola_id"] = escola.get("id")
        session["escola_slug"] = escola.get("slug", slug)
        session["escola_nome"] = escola.get("nome", "")
    return escola


def _escola_por_id(escola_id: str) -> dict | None:
    escola_id = str(escola_id or "")
    for escola in listar_escolas():
        if str(escola.get("id", "")) == escola_id:
            return escola
    return None


def _abrir_escola_na_sessao(escola: dict) -> None:
    """As tres chaves que dizem "esta unidade esta aberta agora".

    Uma funcao so porque sao tres e precisam andar juntas: gravar duas e
    esquecer a terceira deixa a sessao meio aberta, e o defeito aparece longe
    daqui -- _slug_da_sessao consulta o slug, o painel consulta o id.
    """
    session["escola_id"] = escola.get("id")
    session["escola_slug"] = escola.get("slug", "")
    session["escola_nome"] = escola.get("nome", "")


@home_bp.route("/")
def index():
    # O gate de sessao (flask_app.py) manda para ca com ?aviso=... depois de
    # encerrar a sessao ociosa. Sem a mensagem, a pessoa so veria a tela de
    # escolher escola aparecer do nada no meio do que estava fazendo.
    aviso = _AVISOS.get(request.args.get("aviso", ""), "")
    proximo = request.args.get("next", "")
    papel = session.get("usuario_role")

    # MELHORIA: o desenvolvedor e GLOBAL -- conta_pode_entrar devolve True
    # para ele sem sequer olhar a escola. Mesmo assim, para chegar ao ADM ele
    # tinha de escolher uma unidade e digitar o CODIGO dela: a chave de uma
    # casa para entrar em outra. E o codigo e a tranca voltada ao ALUNO,
    # passada pelo professor na sala -- quem administra le todos eles na
    # propria tela de ADM.
    #
    # Sem escola na sessao, ele vai direto para o painel global (as duas
    # areas). Escolher unidade continua existindo, em /abrir-escola, para
    # quando ele quiser acompanhar uma turma.
    if papel == "desenvolvedor" and not _slug_da_sessao():
        return redirect(url_for("professor.tela_professor"))

    if not _slug_da_sessao():
        return render_template(
            "selecionar_escola.html",
            escolas=listar_escolas(),
            aviso=aviso,
            next=proximo,
            # O formulario do ADM fica atras de um clique ("?adm=1"): quem
            # chega nesta tela e aluno, e um par usuario/senha aberto no meio
            # da entrada convida a turma a tentar.
            abrir_adm=request.args.get("adm") == "1",
        )

    escola = carregar_escola_por_slug()
    if not escola:
        # MELHORIA: o slug guardado na sessao envelhece -- basta alguem
        # editar a escola no painel ADM. Visto em producao: o slug virou
        # "etecata" e toda sessao que ainda tinha "etec-aracatuba" batia
        # aqui, a cada visita, sem saida. Como a sessao nunca era limpa, o
        # erro se repetia ate a pessoa apagar os cookies -- algo que nenhum
        # aluno vai adivinhar.
        #
        # Agora que o slug e um codigo digitado, o aviso importa mais: sem
        # ele a pessoa voltaria para a lista e digitaria o codigo VELHO, que
        # falharia como "codigo incorreto" sem explicar por que.
        for chave in ("escola_id", "escola_slug", "escola_nome"):
            session.pop(chave, None)
        return render_template(
            "selecionar_escola.html",
            escolas=listar_escolas(),
            erro="O código dessa escola mudou. Escolha a escola e peça o código novo ao professor.",
            aviso=aviso,
            next=proximo,
        ), 200

    # MELHORIA: segunda tranca do vinculo conta-escola. A primeira e no login
    # (web/routes/auth_fla.py), mas da para logar ANTES de escolher escola --
    # basta abrir /login direto. Aqui a escola ja esta resolvida, entao este e
    # o ponto onde as duas pontas existem ao mesmo tempo.
    if papel:
        pode_entrar, motivo = conta_pode_entrar(
            {"role": papel, "escola_id": session.get("usuario_escola_id")},
            escola.get("id"),
        )
        if not pode_entrar:
            for chave in ("escola_id", "escola_slug", "escola_nome"):
                session.pop(chave, None)
            return render_template(
                "selecionar_escola.html",
                escolas=listar_escolas(),
                erro=motivo,
                aviso=aviso,
                next=proximo,
            ), 200

    # Escola resolvida e conta conferida: o que mostrar depende de quem logou.
    # Professor/desenvolvedor vao direto pro painel de gestao (nunca veem a
    # grade de jogos do aluno); quem ainda nao logou cai em /login.
    if papel in ("professor", "desenvolvedor"):
        return redirect(url_for("professor.tela_professor"))
    if not papel:
        return redirect(url_for("auth.tela_login"))

    # MELHORIA: o card da Batalha de Guildas aparecia mesmo com modo_guilda
    # desligado (RF14). `escola` acabou de vir do banco, entao a opcao ja esta
    # atualizada -- nao precisa de outra consulta.
    return render_template("home.html", escola=escola, mostrar_guildas=mostra_guildas(escola))


@home_bp.route("/e/<slug>")
def escola_slug(slug: str):
    # MELHORIA: esta rota punha o slug direto na sessao -- o mesmo atalho que
    # "?escola=" dava, e o motivo de o codigo nunca ser digitado. Ela deixa
    # de entrar, mas continua existindo para o link antigo cair na lista em
    # vez de virar 404 no meio de uma aula.
    return redirect(url_for("home.index"))


@home_bp.route("/entrar-escola/<escola_id>", methods=["GET", "POST"])
def entrar_escola(escola_id: str):
    # MELHORIA: por um tempo clicar na escola ja entrava, porque digitar o
    # slug parecia atrito sem ganho. Voltou a ser exigido: sem ele, quem
    # abre o endereco cai na porta de uma escola qualquer, e num aparelho
    # compartilhado a escola do colega fica a um clique.
    #
    # O que este codigo NAO e: um segredo. A lista de escolas continua
    # publica (e o que ajuda a pessoa a achar a sua), e nada impede alguem
    # de tentar varios. Ele e o combinado que o professor passa para a
    # turma; quem controla acesso de verdade e a senha, no login.
    escola = _escola_por_id(escola_id)
    if not escola:
        return redirect(url_for("home.index"))

    proximo = request.form.get("next", "") or request.args.get("next", "")
    erro = ""

    # O desenvolvedor abre qualquer unidade sem digitar o codigo. Nao e
    # excecao de conveniencia: o codigo e o combinado que o professor passa a
    # turma, e quem administra ja LE todos eles na tela de ADM. Pedi-lo aqui
    # seria atrito sem tranca nenhuma atras.
    if session.get("usuario_role") == "desenvolvedor":
        _abrir_escola_na_sessao(escola)
        return redirect(url_for("home.index"))

    if request.method == "POST":
        # A comparacao mora em services/escola_service.py: o Streamlit faz a
        # mesma pergunta, e ate agora nao fazia nenhuma.
        if codigo_confere(escola, request.form.get("slug")):
            _abrir_escola_na_sessao(escola)
            if proximo == "cadastro":
                return redirect(url_for("auth.tela_cadastro"))
            return redirect(url_for("home.index"))
        erro = MOTIVO_CODIGO_INCORRETO

    return render_template("codigo_escola.html", escola=escola, erro=erro, next=proximo)


@home_bp.route("/abrir-escola")
def abrir_escola():
    """Qual unidade o desenvolvedor quer acompanhar.

    Existe separada de "/" porque a home manda o desenvolvedor SEM escola
    direto para o painel global -- sem esta rota, pedir a lista de escolas
    voltaria para o painel, num vaivem sem saida.
    """
    if session.get("usuario_role") != "desenvolvedor":
        return redirect(url_for("home.index"))

    return render_template(
        "selecionar_escola.html",
        escolas=listar_escolas(),
        aviso="",
        next="",
        modo_desenvolvedor=True,
    )


@home_bp.route("/trocar-escola")
def trocar_escola():
    for chave in ("escola_id", "escola_slug", "escola_nome", "aluno_id", "aluno_nome", "ano_escolar"):
        session.pop(chave, None)
    return redirect(url_for("home.index"))


@home_bp.route("/healthz")
def healthz():
    return {"status": "ok"}, 200
