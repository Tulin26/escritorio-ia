from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv
import flask
from flask import redirect, request, session, url_for
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from core.config import exibir_materia, materia_base
from core.text_cleanup import aplicar_acentos_pt
from core.expoentes_html import expoentes_html, formula_html
from core.formatters import formatar_data_local
from core.rate_limit import limiter
from core.sessao import carimbar_se_novo, remover_historicos_do_cookie, revisar
from core.utils import formatar_unidades_texto
from services.enem_service import exibir_dificuldade
from web.routes.flask_helpers_fla import exibir_modo
from web.routes.auth_fla import auth_bp
from web.routes.boss_rush_fla import boss_rush_bp
from web.routes.enem_fla import enem_bp
from web.routes.escape_room_fla import escape_room_bp
from web.routes.ajuda_fla import ajuda_bp
from web.routes.guildas_fla import guildas_bp
from web.routes.home_fla import home_bp
from web.routes.laboratorio_fla import laboratorio_bp
from web.routes.oraculo_fla import oraculo_bp
from web.routes.perfil_fla import perfil_bp
from web.routes.privacidade_fla import privacidade_bp
from web.routes.professor_fla import professor_bp
from web.routes.progresso_fla import progresso_bp
from web.routes.rpg_fla import rpg_bp
from web.routes.treino_fla import treino_bp

# "ajuda" e "privacidade" sao publicas de proposito: metade das duvidas que a
# ajuda responde ("o que e o codigo da escola?", "por que a primeira tela
# demora tanto?") acontece ANTES do login -- exatamente quando uma pagina
# presa atras dele nao seria alcancavel. A privacidade precisa do mesmo: e o
# link que a caixa de aceite do cadastro abre, ANTES de a conta existir, e um
# responsavel que nunca teve conta tambem precisa achar sem senha nenhuma.
# Nenhuma das duas le dado de aluno.
BLUEPRINTS_PUBLICOS = {"home", "auth", "ajuda", "privacidade", "static"}


def criar_app() -> flask.Flask:
    # Sob o pytest nao. Sem override ele nao trocava as chaves de mentira do
    # conftest, mas trazia as que o conftest nao define: Gemini, Mistral,
    # Cerebras, HF, a service_role do Supabase e a do Brevo, que manda e-mail.
    if "pytest" not in sys.modules:
        load_dotenv()

    app = flask.Flask(__name__, template_folder="web/templates", static_folder="web/static")
    # MELHORIA: no Render o app roda atras de um proxy, entao
    # request.remote_addr trazia o IP DO PROXY, igual para todo mundo. Como
    # o Flask-Limiter usa esse endereco como chave (ver core/rate_limit.py),
    # a turma inteira dividia um unico balde de limite: com "20 per hour" no
    # login, o 21o aluno a entrar levaria 429 mesmo sendo o primeiro acesso
    # dele -- justamente no cenario de uma sala inteira acessando junto.
    # ProxyFix le o X-Forwarded-For e devolve o IP real do aluno.
    # x_for=1 usa apenas a ultima entrada do cabecalho (a que o proxy do
    # Render acrescenta): valores que o cliente tente injetar ficam a
    # esquerda dela e sao ignorados, entao nao da pra forjar o proprio IP.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    # MELHORIA: antes, sem FLASK_SECRET_KEY configurada, o app usava
    # silenciosamente uma string fixa ("educagame-flask-dev") como chave de
    # sessao. Essa string agora esta neste codigo publico, entao qualquer
    # pessoa que a conhecesse poderia forjar sessoes (se passar por outro
    # aluno, escola, ou ate admin). Falhar rapido no boot e mais seguro do
    # que continuar rodando com uma chave conhecida.
    secret_key = os.getenv("FLASK_SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "FLASK_SECRET_KEY nao configurada. Defina essa variavel de ambiente "
            "antes de iniciar o app — nunca use um valor padrao fixo aqui."
        )
    app.secret_key = secret_key
    # MELHORIA: o cookie de sessao saia sem SameSite (perde uma segunda
    # linha de defesa contra CSRF, alem do CSRFProtect) e sem Secure --
    # podia ir por HTTP puro se algum dia uma requisicao caisse fora do
    # HTTPS que o Render forca. HttpOnly ja era o padrao do Flask; fica
    # explicito aqui pra nao depender de ninguem lembrar disso. Secure fica
    # ligado por padrao e so desliga sob pytest (o cliente de teste do
    # Flask fala HTTP) ou se alguem exportar SESSION_COOKIE_SECURE=0 pra
    # testar fora de HTTPS/localhost.
    cookie_secure_padrao = "0" if "pytest" in sys.modules else "1"
    cookie_secure = os.getenv(
        "SESSION_COOKIE_SECURE", cookie_secure_padrao
    ).strip().lower() in {"1", "true", "sim", "yes"}
    # Por kwarg, e nao por chave de string, pra nao acionar o scanner de
    # tests/test_env_example.py: HTTPONLY e SAMESITE sao config do Flask,
    # fixos aqui, nunca lidos de variavel de ambiente.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
    )
    app.jinja_env.filters["data_local"] = formatar_data_local
    app.jinja_env.filters["modo_label"] = exibir_modo
    # "Facil"/"Medio"/"Dificil" sao chave; o aluno lia a chave crua, sem
    # acento, no seletor do ENEM e do Boss Rush.
    app.jinja_env.filters["dificuldade_label"] = exibir_dificuldade
    # "Matematica" e chave; a tela do foco de estudo mostra "Matemática".
    app.jinja_env.filters["materia_label"] = exibir_materia
    # O log grava a materia com o modo na frente ("LAB-Matematica"); o
    # historico do Perfil e do Progresso mostrava assim, cru. Tira o prefixo
    # ANTES do rotulo: `|materia_base|materia_label`.
    app.jinja_env.filters["materia_base"] = materia_base
    # O tema tambem e chave ("equacoes do 2o grau e formula de Bhaskara"):
    # vai assim para o prompt e para o banco, e so a TELA ganha o acento.
    app.jinja_env.filters["tema_label"] = aplicar_acentos_pt
    # MELHORIA: enunciados e alternativas chegavam ao aluno com o expoente
    # cru ("Qual e a area em m^2?"), porque so o Laboratorio aplicava
    # formatar_unidades_texto -- e mesmo la, so nas alternativas, nao na
    # pergunta: na mesma tela as opcoes mostravam "48 m²" e o enunciado
    # "m^2". Como filtro Jinja, fica disponivel para todos os modos.
    app.jinja_env.filters["unidades"] = formatar_unidades_texto
    # So para tela SEM MathJax (hoje, o Oraculo): ver core/expoentes_html.py.
    app.jinja_env.filters["expoentes_html"] = expoentes_html
    # Expoente E indice ("m_soluto", "10^{-3}") onde a formula chega como texto
    # corrido: ENEM, Batalha, legenda e passos, cartao de resultado.
    app.jinja_env.filters["formula_html"] = formula_html
    limiter.init_app(app)
    CSRFProtect(app)

    # MELHORIA: as duas piores falhas do projeto tinham a mesma assinatura --
    # o app subia bem e funcionava errado, sem nada no log (GROQ_MODEL sem
    # prefixo, Supabase inacessivel). Isto olha a configuracao e fala, no log
    # do Render, antes de servir a primeira requisicao.
    from core.diagnostico_config import relatar_configuracao

    relatar_configuracao()

    @app.before_request
    def encerrar_sessao_ociosa():
        # MELHORIA: a sessao nao tinha prazo nenhum. O cookie saia sem
        # Expires e sem Max-Age, o que deixa a validade toda nas maos do
        # navegador -- e Chrome/Edge com "continuar de onde parei" restauram
        # cookie de sessao, entao abrir o site caia direto no perfil do aluno
        # ou do professor dias depois, sem pedir escola nem senha. Num
        # laboratorio de escola, onde a maquina e compartilhada, quem senta
        # depois herda a conta de quem levantou. Ver core/sessao.py.
        if request.blueprint == "static":
            return None
        # Os historicos de perguntas sairam do cookie (ver
        # services/historico_perguntas.py); quem ja tinha um cookie inchado
        # encolhe aqui, no primeiro acesso depois do deploy.
        remover_historicos_do_cookie(session)
        if not revisar(session, time.time()):
            return None
        # Sessao encerrada agora: em vez de largar a pessoa numa tela de erro
        # (ou, pior, numa tela vazia), manda para a porta de entrada com o
        # motivo. Sem risco de laco: a sessao acabou de ser limpa, entao a
        # requisicao seguinte nao expira de novo.
        return redirect(url_for("home.index", aviso="sessao_expirada"))

    @app.after_request
    def adicionar_headers_seguranca(resposta):
        # MELHORIA: o app nao mandava nenhum header de seguranca -- sem
        # protecao contra clickjacking, sem impedir o navegador de tentar
        # "adivinhar" o tipo de um arquivo estatico, e sem CSP nenhuma. A
        # CSP abaixo foi montada a partir do que o app REALMENTE carrega
        # (grep em web/templates/): fontes do Google (fonts.googleapis.com
        # e fonts.gstatic.com) e o MathJax do jsdelivr (ENEM e Batalha, ver
        # partials/result_card.html). 'unsafe-inline' em script-src fica
        # porque varios templates tem <script> inline (inclusive a
        # configuracao do MathJax) e o app nao tem infraestrutura de nonce
        # -- e uma CSP mais fraca que o ideal, mas ainda bloqueia script de
        # qualquer host que nao esteja nesta lista.
        #
        # MELHORIA: sem 'unsafe-inline' em style-src (de proposito -- o app
        # nao tem nenhum estilo embutido proprio), o proprio tex-svg.js do
        # MathJax injeta <style> em tempo de execucao e o navegador bloqueia.
        # Os quatro hashes abaixo sao os blocos exatos que o Chrome reportou
        # ao carregar uma questao real; se uma atualizacao do MathJax mudar
        # esse CSS, o console volta a acusar e eles precisam ser refeitos.
        #
        # CORRIGIDO EM 29/09/2026, e o custo do erro foi maior do que se
        # pensava: dizia-se aqui que o bloqueio "nao quebra o desenho, so
        # suja o console". Quebrava. Um dos blocos e o que esconde a copia
        # em MathML que o MathJax poe ao lado do SVG para leitor de tela;
        # bloqueado, o Chrome desenhava essa copia, e TODA formula aparecia
        # duas vezes no Laboratorio, no Treino e no RPG.
        #
        # Dois defeitos somados: um hash tinha "0" (zero) onde o certo e "O"
        # (letra), e o quarto nunca foi incluido -- os dois porque a lista
        # foi transcrita de uma imagem do console. CSP compara byte a byte.
        # Hash daqui em diante so com o texto COPIADO do DevTools.
        #
        # A duplicacao tambem esta consertada por outro caminho, em
        # web/static/css/flask.css (mjx-assistive-mml), servido de /static/
        # e portanto imune a esta lista: se um hash quebrar de novo, volta o
        # erro no console, mas nao volta a formula dobrada na tela.
        estilos_mathjax = (
            "'sha256-JLEjeN9e5dGsz5475WyRaoA4eQOdNPxDIeUhclnJDCE='",
            "'sha256-mQyxHEuwZJqpxCw3SLmc4YOySNKXunyu2Oiz1r3/wAE='",
            "'sha256-OCf+kv5Asiwp++8PIevKBYSgnNLNUZvxAp4a7wMLuKA='",
            "'sha256-h5LOiLhk6wiJrGsG5ItM0KimwzWQH/yAcmoJDJL//bY='",
        )
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resposta.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            f"style-src 'self' https://fonts.googleapis.com {' '.join(estilos_mathjax)}; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        # So quando a requisicao chegou por HTTPS de verdade (ProxyFix ja le
        # o X-Forwarded-Proto do Render): HSTS mandado por HTTP puro nao
        # tem efeito nenhum, e so serve de ruido no dev local.
        if request.is_secure:
            resposta.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return resposta

    @app.after_request
    def carimbar_sessao_nova(resposta):
        # Escolher a escola e logar acontecem DENTRO da view, depois que o
        # gate acima ja rodou. Este carimbo fecha a volta: sem ele a sessao
        # recem-criada chegaria a proxima requisicao sem idade conhecida, e
        # sessao sem idade conhecida e expirada por definicao.
        if request.blueprint != "static":
            carimbar_se_novo(session, time.time())
        return resposta

    @app.before_request
    def exigir_login():
        # MELHORIA: gate central de autenticacao. Antes so a area "adm" do
        # professor tinha alguma protecao (senha mestra unica); o resto do
        # app (inclusive o painel do professor inteiro) ficava acessivel
        # sem login nenhum. Qualquer blueprint fora de home/auth/static
        # agora exige um usuario logado (com papel definido em
        # session["usuario_role"]); quem nao esta logado cai direto em
        # /login.
        if request.blueprint in BLUEPRINTS_PUBLICOS or request.blueprint is None:
            return None
        if not session.get("usuario_role"):
            return redirect(url_for("auth.tela_login"))
        return None

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(oraculo_bp, url_prefix="/oraculo")
    app.register_blueprint(laboratorio_bp, url_prefix="/laboratorio")
    app.register_blueprint(treino_bp, url_prefix="/treino")
    app.register_blueprint(enem_bp, url_prefix="/enem")
    app.register_blueprint(progresso_bp, url_prefix="/progresso")
    app.register_blueprint(perfil_bp, url_prefix="/perfil")
    app.register_blueprint(professor_bp, url_prefix="/professor")
    app.register_blueprint(boss_rush_bp, url_prefix="/boss-rush")
    app.register_blueprint(escape_room_bp, url_prefix="/escape-room")
    app.register_blueprint(rpg_bp, url_prefix="/rpg")
    app.register_blueprint(guildas_bp, url_prefix="/guildas")
    app.register_blueprint(ajuda_bp, url_prefix="/ajuda")
    app.register_blueprint(privacidade_bp, url_prefix="/privacidade")

    _registrar_retorno_de_metodo_errado(app)

    return app


def _tela_de_volta(app: flask.Flask, caminho: str) -> str:
    """A tela GET mais curta do mesmo modo que o caminho pedido.

    "/laboratorio/responder" devolve "/laboratorio/". Sai do proprio url_map,
    entao um modo novo passa a ser atendido sem ninguem lembrar disto aqui.
    """
    candidatas = [
        str(regra)
        for regra in app.url_map.iter_rules()
        if "GET" in regra.methods and not regra.arguments
    ]
    do_modo = [rota for rota in candidatas if caminho.startswith(rota.rstrip("/") + "/")]
    if not do_modo:
        return "/"
    # A MAIS LONGA, e nao a mais curta: "/" tambem e prefixo de tudo, e pegar a
    # mais curta mandava todo mundo para a home em vez da tela do modo.
    return max(do_modo, key=len)


def _registrar_retorno_de_metodo_errado(app: flask.Flask) -> None:
    """GET numa rota que so aceita POST volta para a tela do modo.

    MELHORIA: o aluno via a pagina branca do Werkzeug com "Method Not Allowed"
    no meio da atividade. Visto no Laboratorio, em producao.

    As rotas de responder ja fazem POST-Redirect-GET certo -- o problema nao e
    o envio, e o HISTORICO: depois de responder, voltar ou atualizar faz o
    navegador reemitir "/laboratorio/responder" como GET, e ai sao 41 rotas do
    app em que isso da 405.

    Tratar aqui, e nao acrescentar "GET" em cada uma, e o que evita esquecer a
    quadragesima segunda: o handler nao precisa saber quais rotas existem.
    """

    @app.errorhandler(405)
    def _metodo_nao_permitido(erro):  # noqa: ANN001
        # Só o GET vindo do historico. Um POST barrado continua sendo 405, que
        # e o que um cliente errado precisa receber.
        if request.method != "GET":
            return erro
        return redirect(_tela_de_volta(app, request.path))


app = criar_app()


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "sim", "yes"}
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug)
