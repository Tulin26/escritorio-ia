from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash

from core.senhas import hash_senha, precisa_regravar_hash

from repositories.aluno_repo import (
    atualizar_aluno_por_id,
    buscar_aluno_por_email,
    buscar_aluno_por_username,
    confirmar_email_aluno,
    upsert_alunos,
)

# MELHORIA: flask e services.email_service so sao necessarios no fluxo de
# cadastro por e-mail (gerar link de confirmacao, redefinir senha) -- o
# login por usuario/senha e por e-mail/senha nao depende de nenhum dos
# dois. Com os imports no topo, este modulo inteiro ficava impossivel de
# usar fora do app Flask, e por isso o frontend Streamlit tinha ficado sem
# login nenhum (entrava digitando o slug da escola). Importando sob
# demanda, as duas interfaces compartilham a mesma autenticacao em vez de
# manter implementacoes separadas.

TOKEN_SALT = "confirmacao-email-aluno"
TOKEN_MAX_IDADE_SEGUNDOS = 60 * 60 * 24  # 24h

# MELHORIA: salt DIFERENTE do de confirmacao de e-mail de proposito -- um
# token de confirmacao nao pode ser reaproveitado como token de
# redefinicao de senha (e vice-versa), mesmo os dois sendo gerados a
# partir do mesmo aluno_id com o mesmo secret_key. Prazo mais curto (1h,
# nao 24h) porque um link de redefinicao de senha parado numa caixa de
# entrada e um risco maior do que um link de confirmacao de cadastro.
TOKEN_SALT_SENHA = "redefinicao-senha-aluno"
TOKEN_MAX_IDADE_SENHA_SEGUNDOS = 60 * 60  # 1h

_REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# MELHORIA: bloqueia de cara os provedores de e-mail descartavel mais
# conhecidos (usados pra burlar cadastros que exigem confirmacao). Nao e
# a defesa principal — isso e o link de confirmacao, que prova que a
# pessoa tem acesso real aquela caixa de entrada — mas rejeita a tentativa
# mais obvia sem nem gastar o envio de um e-mail.
DOMINIOS_DESCARTAVEIS = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.info", "10minutemail.com",
    "10minutemail.net", "tempmail.com", "temp-mail.org", "throwawaymail.com",
    "yopmail.com", "yopmail.fr", "trashmail.com", "getnada.com", "sharklasers.com",
    "dispostable.com", "maildrop.cc", "fakeinbox.com", "mintemail.com", "moakt.com",
    "discard.email", "discardmail.com", "spamgourmet.com", "mytemp.email",
    "mailnesia.com", "mohmal.com", "emailondeck.com", "tempinbox.com",
    "burnermail.io", "correotemporal.org", "einrot.com", "fakemailgenerator.com",
    "mailcatch.com", "mailsac.com", "tempr.email", "tmpmail.net", "tmpmail.org",
    "spam4.me", "grr.la", "trbvm.com", "0-mail.com",
}


def email_formato_valido(email: str) -> bool:
    return bool(_REGEX_EMAIL.match(str(email or "").strip()))


def dominio_descartavel(email: str) -> bool:
    email = str(email or "").strip().lower()
    if "@" not in email:
        return False
    dominio = email.rsplit("@", 1)[1]
    return dominio in DOMINIOS_DESCARTAVEIS


def validar_email_cadastro(email: str) -> str:
    """Retorna uma mensagem de erro, ou string vazia se o e-mail for aceitavel."""
    email = str(email or "").strip()
    if not email_formato_valido(email):
        return "Informe um e-mail válido."
    if dominio_descartavel(email):
        return "Não aceitamos e-mails de serviços temporários/descartáveis. Use um e-mail de verdade."
    return ""


def _chave_de_assinatura() -> str:
    """Segredo usado para assinar os tokens de e-mail.

    Dentro do app Flask e o secret_key dele; fora (Streamlit, scripts), cai
    para a variavel de ambiente. Os dois lados precisam usar o MESMO valor,
    senao um link gerado por uma interface nao valida na outra.
    """
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            return current_app.secret_key
    except Exception:
        pass
    import os

    chave = os.getenv("FLASK_SECRET_KEY")
    if not chave:
        raise RuntimeError(
            "FLASK_SECRET_KEY não configurada — necessária para assinar os tokens de e-mail."
        )
    return chave


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_chave_de_assinatura(), salt=TOKEN_SALT)


def gerar_token_confirmacao(aluno_id: str) -> str:
    return _serializer().dumps(str(aluno_id))


def verificar_token_confirmacao(token: str) -> str | None:
    try:
        return _serializer().loads(token, max_age=TOKEN_MAX_IDADE_SEGUNDOS)
    except (BadSignature, SignatureExpired):
        return None


def _serializer_senha() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_chave_de_assinatura(), salt=TOKEN_SALT_SENHA)


def gerar_token_redefinicao_senha(aluno_id: str) -> str:
    return _serializer_senha().dumps(str(aluno_id))


def verificar_token_redefinicao_senha(token: str) -> str | None:
    try:
        return _serializer_senha().loads(token, max_age=TOKEN_MAX_IDADE_SENHA_SEGUNDOS)
    except (BadSignature, SignatureExpired):
        return None


def _link_da_rota(endpoint: str, token: str) -> str:
    """Monta o link do e-mail. Fora do Flask, usa APP_BASE_URL."""
    try:
        from flask import has_app_context, url_for

        if has_app_context():
            return url_for(endpoint, token=token, _external=True)
    except Exception:
        pass
    import os

    caminho = {
        "auth.confirmar_email_rota": "confirmar-email",
        "auth.redefinir_senha_rota": "redefinir-senha",
    }[endpoint]
    base = (os.getenv("APP_BASE_URL") or "https://educagame.onrender.com").rstrip("/")
    return f"{base}/{caminho}/{token}"


def _enviar_email(destinatario: str, assunto: str, corpo: str, corpo_html: str) -> bool:
    from services.email_service import enviar_email

    return enviar_email(destinatario, assunto, corpo, corpo_html)


def _enviar_email_confirmacao(email: str, nome: str, aluno_id: str) -> bool:
    token = gerar_token_confirmacao(aluno_id)
    link = _link_da_rota("auth.confirmar_email_rota", token)
    corpo = (
        f"Olá, {nome or 'aluno'}!\n\n"
        "Confirme seu e-mail pra ativar sua conta no EducaGame:\n"
        f"{link}\n\n"
        "Se você não pediu esse cadastro, pode ignorar esta mensagem."
    )
    corpo_html = (
        f"<p>Olá, {nome or 'aluno'}!</p>"
        "<p>Confirme seu e-mail pra ativar sua conta no EducaGame:</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>Se você não pediu esse cadastro, pode ignorar esta mensagem.</p>"
    )
    return _enviar_email(email, "Confirme seu e-mail — EducaGame", corpo, corpo_html)


def cadastrar_aluno(
    *,
    escola_id: str,
    nome: str,
    ra_identificacao: str,
    ano_escolar: str,
    periodo: str,
    email: str,
    senha: str,
    consentimento: bool,
) -> tuple[bool, str]:
    email = str(email or "").strip().lower()
    erro_email = validar_email_cadastro(email)
    if erro_email:
        return False, erro_email
    if not str(nome or "").strip() or not str(ra_identificacao or "").strip():
        return False, "Informe nome e RA/identificação."
    if len(str(senha or "")) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."
    # MELHORIA (LGPD, Art. 8): sem isso o cadastro completava sem nenhum
    # registro de que a pessoa leu ou aceitou a politica de privacidade --
    # o parametro e obrigatorio (sem valor padrao) de proposito, pra um
    # caminho novo que esqueça de checar a caixa falhar ao rodar os testes,
    # em vez de cadastrar em silencio sem consentimento.
    if not consentimento:
        return False, "É necessário aceitar a política de privacidade para se cadastrar."

    existente_por_email = buscar_aluno_por_email(email)
    if existente_por_email and str(existente_por_email.get("escola_id")) != str(escola_id):
        return False, "Esse e-mail já está cadastrado em outra escola."
    if existente_por_email and existente_por_email.get("email_confirmado"):
        return False, "Esse e-mail já está cadastrado. Faça login ou recupere sua senha."

    dados_aluno = {
        "escola_id": escola_id,
        "nome": nome,
        "ra_identificacao": ra_identificacao,
        "ano_escolar": ano_escolar,
        "periodo": periodo,
        "email": email,
        "senha_hash": hash_senha(senha),
        "email_confirmado": False,
        "consentimento_dados_em": datetime.now(timezone.utc).isoformat(),
    }

    if existente_por_email:
        # MELHORIA: ja existe um cadastro pendente (nunca confirmado) com
        # esse e-mail. Fazer upsert por (escola_id, ra_identificacao) aqui
        # tentaria INSERIR uma linha nova sempre que o RA informado agora
        # for diferente do RA da tentativa anterior — e colidiria com a
        # restricao de e-mail unico da tabela (visto em producao: cadastro
        # falhava silenciosamente com "Nao foi possivel concluir o
        # cadastro"). Atualiza a mesma linha pendente em vez de tentar
        # criar outra.
        resultado = atualizar_aluno_por_id(existente_por_email["id"], dados_aluno)
    else:
        resultado = upsert_alunos([dados_aluno])

    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível concluir o cadastro. Tente novamente."

    aluno = resultado.data[0]
    # MELHORIA: bug visto em producao -- cadastrar_aluno sempre devolvia
    # (True, "") mesmo quando o envio do e-mail falhava (SMTP fora do ar,
    # Brevo bloqueando/colocando em quarentena etc.), entao a tela sempre
    # mostrava "Enviamos um link de confirmacao pro seu e-mail" mesmo
    # quando nenhum e-mail saiu. O aluno ficava esperando um e-mail que
    # nunca chegava, sem nenhum sinal de que algo deu errado. Agora o
    # texto de sucesso reflete se o envio realmente funcionou.
    if _enviar_email_confirmacao(email, nome, aluno.get("id")):
        return True, ""
    return True, (
        "Cadastro criado, mas não conseguimos enviar o e-mail de confirmação agora. "
        "Tente 'Não recebeu o e-mail de confirmação?' na tela de login em alguns minutos, "
        "ou peça pro seu professor confirmar sua conta manualmente."
    )


def _enviar_email_redefinicao_senha(email: str, nome: str, aluno_id: str) -> bool:
    token = gerar_token_redefinicao_senha(aluno_id)
    link = _link_da_rota("auth.redefinir_senha_rota", token)
    corpo = (
        f"Olá, {nome or 'aluno'}!\n\n"
        "Recebemos um pedido pra redefinir sua senha no EducaGame. Clique no link abaixo "
        "pra escolher uma senha nova (o link vale por 1 hora):\n"
        f"{link}\n\n"
        "Se você não pediu essa redefinição, pode ignorar esta mensagem — sua senha atual continua valendo."
    )
    corpo_html = (
        f"<p>Olá, {nome or 'aluno'}!</p>"
        "<p>Recebemos um pedido pra redefinir sua senha no EducaGame. Clique no link abaixo "
        "pra escolher uma senha nova (o link vale por 1 hora):</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>Se você não pediu essa redefinição, pode ignorar esta mensagem — sua senha atual continua valendo.</p>"
    )
    return _enviar_email(email, "Redefinir sua senha — EducaGame", corpo, corpo_html)


def solicitar_redefinicao_senha(email: str) -> bool:
    # MELHORIA: mesmo padrao de reenviar_confirmacao -- sempre "funciona"
    # do ponto de vista de quem chama quando o e-mail nao esta cadastrado
    # (nao revela quais e-mails tem conta), so retorna False quando existe
    # conta de verdade mas o envio falhou, pra tela poder avisar.
    aluno = buscar_aluno_por_email(str(email or "").strip().lower())
    if aluno:
        return _enviar_email_redefinicao_senha(aluno.get("email", ""), aluno.get("nome", ""), aluno.get("id"))
    return True


def redefinir_senha(token: str, nova_senha: str) -> tuple[bool, str]:
    aluno_id = verificar_token_redefinicao_senha(token)
    if not aluno_id:
        return False, "Link inválido ou expirado. Peça uma nova redefinição de senha."
    if len(str(nova_senha or "")) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."

    resultado = atualizar_aluno_por_id(aluno_id, {"senha_hash": hash_senha(nova_senha)})
    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível redefinir sua senha. Tente novamente."
    return True, ""


def reenviar_confirmacao(email: str) -> bool:
    # MELHORIA: sempre "funciona" do ponto de vista de quem chama (nao
    # revela se o e-mail existe ou nao na base), evitando que alguem use
    # esse endpoint pra descobrir quais e-mails ja tem conta. O retorno
    # (True = e-mail enviado com sucesso OU conta nao existe/ja
    # confirmada; False = existe conta pendente mas o envio falhou de
    # verdade) so serve pra tela mostrar um aviso quando o SMTP falhou --
    # nao revela qual dos dois motivos foi.
    aluno = buscar_aluno_por_email(str(email or "").strip().lower())
    if aluno and not aluno.get("email_confirmado"):
        return _enviar_email_confirmacao(aluno.get("email", ""), aluno.get("nome", ""), aluno.get("id"))
    return True


def confirmar_email(token: str) -> bool:
    aluno_id = verificar_token_confirmacao(token)
    if not aluno_id:
        return False
    return bool(confirmar_email_aluno(aluno_id))


def _regravar_hash_se_fraco(aluno: dict, senha: str) -> None:
    """Sobe o custo do hash no proximo login, sem pedir troca de senha.

    MELHORIA: e o formato autodescritivo do scrypt que permite isto -- o
    hash guarda os proprios parametros, entao da para reconhecer os antigos
    e regravar so eles. Melhor esforco: se a gravacao falhar, o login segue
    normal com o hash antigo, que continua valido.
    """
    if not precisa_regravar_hash(aluno.get("senha_hash", "")):
        return
    try:
        atualizar_aluno_por_id(aluno.get("id"), {"senha_hash": hash_senha(senha)})
    except Exception:  # noqa: BLE001
        pass


def autenticar_aluno_por_email(email: str, senha: str) -> dict | None:
    email = str(email or "").strip().lower()
    if "@" not in email:
        return None
    aluno = buscar_aluno_por_email(email)
    if not aluno or not aluno.get("senha_hash"):
        return None
    if not check_password_hash(aluno.get("senha_hash", ""), str(senha or "")):
        return None
    if not aluno.get("email_confirmado"):
        return None
    _regravar_hash_se_fraco(aluno, senha)
    return aluno


def autenticar_aluno_por_username(username: str, senha: str) -> dict | None:
    username = str(username or "").strip().lower()
    if not username:
        return None
    aluno = buscar_aluno_por_username(username)
    if not aluno or not aluno.get("senha_hash"):
        return None
    if not check_password_hash(aluno.get("senha_hash", ""), str(senha or "")):
        return None
    _regravar_hash_se_fraco(aluno, senha)
    return aluno


def criar_aluno_com_username(
    *,
    escola_id: str,
    nome: str,
    ra_identificacao: str,
    ano_escolar: str,
    periodo: str,
    username: str,
    senha: str,
    consentimento_responsavel: bool,
) -> tuple[bool, str]:
    # MELHORIA: caminho de criacao "manual" (professor/desenvolvedor
    # cadastrando por fora do autocadastro publico) — sem exigir e-mail,
    # ja que quem esta criando a conta ja garante a identidade da pessoa.
    # Nao usar pra contas que o proprio aluno cria sozinho: isso pertence
    # a services.aluno_auth_service.cadastrar_aluno (por e-mail confirmado).
    #
    # MELHORIA (LGPD, Art. 8): aqui quem aceita nao e o aluno digitando --
    # e quem esta criando a conta (professor/desenvolvedor), atestando que a
    # escola tem autorizacao pra tratar o dado desse aluno. Por isso o nome
    # do parametro e diferente do `consentimento` de cadastrar_aluno(), mas
    # o efeito e o mesmo: obrigatorio, sem valor padrao, pra um caminho novo
    # falhar ao chamar a funcao em vez de criar a conta em silencio sem essa
    # confirmacao.
    if not consentimento_responsavel:
        return False, "É necessário confirmar a autorização da escola para tratar os dados do aluno."
    username = str(username or "").strip().lower()
    if not username:
        return False, "Informe um usuário."
    if not str(nome or "").strip() or not str(ra_identificacao or "").strip():
        return False, "Informe nome e RA/identificação."
    if len(str(senha or "")) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."

    existente = buscar_aluno_por_username(username)
    if existente and str(existente.get("escola_id")) != str(escola_id):
        return False, "Esse usuário já está em uso em outra escola."

    dados_aluno = {
        "escola_id": escola_id,
        "nome": nome,
        "ra_identificacao": ra_identificacao,
        "ano_escolar": ano_escolar,
        "periodo": periodo,
        "username": username,
        "senha_hash": hash_senha(senha),
        "consentimento_dados_em": datetime.now(timezone.utc).isoformat(),
    }

    if existente:
        resultado = atualizar_aluno_por_id(existente["id"], dados_aluno)
    else:
        resultado = upsert_alunos([dados_aluno])

    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível concluir o cadastro. Tente novamente."
    return True, ""


# MELHORIA: sem "i", "l", "o", "0" nem "1". A senha e entregue impressa em
# papel para o aluno (ver scripts/criar_alunos_teste.py), e esses caracteres
# viram erro de digitacao garantido na letra de forma.
_LETRAS_SEM_AMBIGUIDADE = "abcdefghjkmnpqrstuvwxyz"
_DIGITOS_SEM_AMBIGUIDADE = "23456789"


def gerar_senha_legivel() -> str:
    """6 caracteres, com pelo menos uma letra e pelo menos um digito."""
    caracteres = [secrets.choice(_LETRAS_SEM_AMBIGUIDADE) for _ in range(4)]
    caracteres += [secrets.choice(_DIGITOS_SEM_AMBIGUIDADE) for _ in range(2)]
    secrets.SystemRandom().shuffle(caracteres)
    return "".join(caracteres)


def redefinir_senha_do_aluno(aluno_id: str, nova_senha: str = "") -> tuple[bool, str, str]:
    """Troca a senha sem token, pelo painel do desenvolvedor.

    MELHORIA: redefinir_senha() exige o token que chega por e-mail, e boa
    parte dos alunos da escola nao tem e-mail cadastrado -- para eles nao
    havia caminho nenhum de recuperacao a nao ser mexer no Supabase na mao.
    Aqui quem ja esta autenticado como desenvolvedor troca direto.

    Devolve (ok, mensagem_de_erro, senha_em_texto). A senha volta em texto
    porque e a unica vez que ela existe legivel: o banco guarda so o hash,
    entao quem redefiniu precisa anotar antes de sair da tela.
    """
    aluno_id = str(aluno_id or "").strip()
    if not aluno_id:
        return False, "Selecione um aluno.", ""

    senha = str(nova_senha or "").strip() or gerar_senha_legivel()
    if len(senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres.", ""

    resultado = atualizar_aluno_por_id(aluno_id, {"senha_hash": hash_senha(senha)})
    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível redefinir a senha. Verifique a conexão com o Supabase.", ""
    return True, "", senha
