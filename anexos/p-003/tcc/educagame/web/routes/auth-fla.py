from __future__ import annotations

import time

from flask import Blueprint, redirect, render_template, request, session, url_for

from core.rate_limit import limiter
from core.sessao import encerrar, marcar_login
from services.auth_service import MOTIVO_ADM_RECUSADO, autenticar, conta_pode_entrar
from services.escola_service import listar_escolas
from services.aluno_auth_service import (
    cadastrar_aluno,
    confirmar_email,
    reenviar_confirmacao,
    redefinir_senha,
    solicitar_redefinicao_senha,
    verificar_token_redefinicao_senha,
)
from services.professor_service import SERIES_GERAIS

auth_bp = Blueprint("auth", __name__)

_MENSAGENS_LOGIN = {
    "confirmado": "E-mail confirmado! Já pode fazer login.",
    "confirmacao_invalida": "Link de confirmação inválido ou expirado. Peça um novo abaixo.",
    "reenviado": "Se esse e-mail estiver cadastrado, reenviamos o link de confirmação.",
    "reenvio_falhou": "Não conseguimos enviar o e-mail agora. Tente novamente em alguns minutos ou peça ajuda ao seu professor.",
    "redefinicao_enviada": "Se esse e-mail estiver cadastrado, enviamos um link pra redefinir sua senha.",
    "redefinicao_envio_falhou": "Não conseguimos enviar o e-mail agora. Tente novamente em alguns minutos ou peça ajuda ao seu professor.",
    "redefinicao_invalida": "Link de redefinição de senha inválido ou expirado. Peça um novo abaixo.",
    "senha_redefinida": "Senha redefinida! Já pode fazer login com a senha nova.",
}
_AVISOS_LOGIN_ALERTA = {"confirmacao_invalida", "reenvio_falhou", "redefinicao_envio_falhou", "redefinicao_invalida"}


def abrir_sessao_de_usuario(usuario: dict) -> None:
    """Grava na sessao quem acabou de entrar.

    Uma funcao so porque sao duas portas -- o login de sempre e a do ADM na
    tela inicial -- e sao seis chaves que precisam andar juntas. Duplicar o
    bloco era garantir que uma das portas esquecesse uma delas; esquecer
    marcar_login, por exemplo, deixa a sessao sem idade e o gate de
    inatividade a derruba na primeira volta.
    """
    session["usuario_id"] = usuario.get("id")
    session["usuario_username"] = usuario.get("username")
    session["usuario_role"] = usuario.get("role")
    # A escola DA CONTA, que nao se confunde com a escola aberta agora
    # ("escola_id"): esta ultima e reescrita a cada visita a home, entao
    # guardar o vinculo la faria a checagem comparar a escola consigo mesma e
    # nunca reprovar nada.
    session["usuario_escola_id"] = usuario.get("escola_id")
    if usuario.get("role") == "aluno" and usuario.get("aluno_id"):
        session["aluno_id"] = usuario.get("aluno_id")
        session["aluno_nome"] = usuario.get("aluno_nome")
        session["ano_escolar"] = usuario.get("ano_escolar")
        if usuario.get("escola_id"):
            session["escola_id"] = usuario.get("escola_id")
    # Zera os dois relogios da sessao: a vida maxima conta a partir daqui, nao
    # de quando a escola foi escolhida.
    marcar_login(session, time.time())


@auth_bp.route("/adm/entrar", methods=["POST"])
# MESMO limite do login. Sem ele esta rota seria um desvio em volta da
# tranca: quem quisesse tentar senhas em serie usaria a porta sem contador.
@limiter.limit("20 per hour")
def entrar_como_desenvolvedor():
    """A porta do ADM na tela inicial, por usuario e senha.

    Fica aqui, e nao em home_fla, porque e autenticacao: e onde o limitador
    de tentativas e o abrir_sessao_de_usuario ja moram.

    Recusa tudo que nao seja desenvolvedor -- inclusive conta valida de
    professor. Esta porta e anterior a QUALQUER escolha de escola, entao um
    professor que entrasse por aqui entraria sem unidade nenhuma: exatamente
    o estado que conta_pode_entrar recusa.
    """
    try:
        conta = autenticar(request.form.get("username", ""), request.form.get("senha", ""))
    except Exception as erro:  # noqa: BLE001
        # Supabase fora do ar viraria "senha errada" se nao tratar -- e a
        # pessoa passa a tarde tentando lembrar a senha certa.
        return _tela_de_escolas(erro=f"Não foi possível verificar a conta agora: {erro}")

    if not conta or str(conta.get("role", "")) != "desenvolvedor":
        return _tela_de_escolas(erro=MOTIVO_ADM_RECUSADO)

    # Sem escola de proposito: e a entrada GLOBAL. A home manda o
    # desenvolvedor sem escola para o painel das duas areas.
    abrir_sessao_de_usuario(conta)
    return redirect(url_for("home.index"))


def _tela_de_escolas(erro: str):
    """A tela inicial de volta, com o formulario do ADM aberto e o motivo."""
    return render_template(
        "selecionar_escola.html",
        escolas=listar_escolas(),
        erro_adm=erro,
        abrir_adm=True,
        aviso="",
        next="",
    ), 200


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def tela_login():
    erro = ""
    aviso_chave = request.args.get("aviso", "")
    mensagem = _MENSAGENS_LOGIN.get(aviso_chave, "")
    mensagem_alerta = aviso_chave in _AVISOS_LOGIN_ALERTA
    if request.method == "POST":
        username = request.form.get("username", "")
        senha = request.form.get("senha", "")
        usuario = autenticar(username, senha)
        if not usuario:
            erro = "Usuário/e-mail ou senha inválidos."
        else:
            # MELHORIA: senha certa nao bastava -- a conta entrava em QUALQUER
            # escola que a pessoa tivesse escolhido antes. A regra mora em
            # services/auth_service.py e vale para os dois frontends.
            pode_entrar, motivo = conta_pode_entrar(usuario, session.get("escola_id"))
            if not pode_entrar:
                erro = motivo
            else:
                abrir_sessao_de_usuario(usuario)
                return redirect(url_for("home.index"))

    return render_template("login.html", erro=erro, mensagem=mensagem, mensagem_alerta=mensagem_alerta)


@auth_bp.route("/cadastro", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def tela_cadastro():
    if not session.get("escola_id"):
        return redirect(url_for("home.index", next="cadastro"))

    erro = ""
    sucesso = False
    aviso_sucesso = ""
    if request.method == "POST":
        ok, mensagem = cadastrar_aluno(
            escola_id=session.get("escola_id"),
            nome=request.form.get("nome", ""),
            ra_identificacao=request.form.get("ra_identificacao", ""),
            ano_escolar=request.form.get("ano_escolar", ""),
            periodo=request.form.get("periodo", "Manhã"),
            email=request.form.get("email", ""),
            senha=request.form.get("senha", ""),
            consentimento=bool(request.form.get("consentimento")),
        )
        if ok:
            sucesso = True
            aviso_sucesso = mensagem
        else:
            erro = mensagem

    return render_template(
        "cadastro.html", erro=erro, sucesso=sucesso, aviso_sucesso=aviso_sucesso, series=SERIES_GERAIS
    )


@auth_bp.route("/confirmar-email/<token>")
def confirmar_email_rota(token: str):
    aviso = "confirmado" if confirmar_email(token) else "confirmacao_invalida"
    return redirect(url_for("auth.tela_login", aviso=aviso))


@auth_bp.route("/reenviar-confirmacao", methods=["POST"])
@limiter.limit("5 per hour")
def reenviar_confirmacao_rota():
    ok = reenviar_confirmacao(request.form.get("email", ""))
    return redirect(url_for("auth.tela_login", aviso="reenviado" if ok else "reenvio_falhou"))


@auth_bp.route("/esqueci-senha", methods=["POST"])
@limiter.limit("5 per hour")
def esqueci_senha_rota():
    ok = solicitar_redefinicao_senha(request.form.get("email", ""))
    return redirect(url_for("auth.tela_login", aviso="redefinicao_enviada" if ok else "redefinicao_envio_falhou"))


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def redefinir_senha_rota(token: str):
    if not verificar_token_redefinicao_senha(token):
        return redirect(url_for("auth.tela_login", aviso="redefinicao_invalida"))

    erro = ""
    if request.method == "POST":
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        if senha != confirmar_senha:
            erro = "As senhas não coincidem."
        else:
            ok, mensagem = redefinir_senha(token, senha)
            if ok:
                return redirect(url_for("auth.tela_login", aviso="senha_redefinida"))
            erro = mensagem

    return render_template("redefinir_senha.html", erro=erro, token=token)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    # Sair pela porta e ser expirado por inatividade limpam a MESMA coisa --
    # dai a funcao unica. Duas listas separadas viravam duas definicoes de
    # "sair", uma esquecendo a escola e a outra nao.
    encerrar(session)
    return redirect(url_for("auth.tela_login"))
