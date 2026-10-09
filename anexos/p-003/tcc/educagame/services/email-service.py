from __future__ import annotations

import json
import os
import smtplib
from email.message import EmailMessage
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def _smtp_configurado() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))


def _resend_configurado() -> bool:
    return bool(os.getenv("RESEND_API_KEY"))


def _brevo_configurado() -> bool:
    return bool(os.getenv("BREVO_API_KEY"))


def _enviar_via_smtp(destinatario: str, assunto: str, corpo_texto: str, corpo_html: str | None) -> bool:
    remetente = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER")
    host = os.getenv("SMTP_HOST", "")
    porta = int(os.getenv("SMTP_PORT", "587"))
    usuario = os.getenv("SMTP_USER", "")
    senha = os.getenv("SMTP_PASSWORD", "")

    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = remetente
    mensagem["To"] = destinatario
    mensagem.set_content(corpo_texto)
    if corpo_html:
        mensagem.add_alternative(corpo_html, subtype="html")

    try:
        with smtplib.SMTP(host, porta, timeout=10) as servidor:
            servidor.starttls()
            servidor.login(usuario, senha)
            servidor.send_message(mensagem)
        return True
    except Exception as e:
        print(f"[EMAIL] Falha ao enviar (SMTP) para {destinatario}: {type(e).__name__}: {e}")
        return False


def _enviar_via_resend(destinatario: str, assunto: str, corpo_texto: str, corpo_html: str | None) -> bool:
    # MELHORIA: SMTP (porta 587) e bloqueado pela rede de saida do Render
    # ("OSError: [Errno 101] Network is unreachable", visto ao vivo em
    # producao) -- tanto Brevo quanto Gmail via SMTP falhavam sempre que
    # rodava no Render, mesmo funcionando em teste local, porque o
    # problema nunca foi credencial/remetente, era a porta em si sendo
    # bloqueada. A API HTTP do Resend usa HTTPS (porta 443), a mesma porta
    # que Groq/Gemini/Supabase ja usam sem problema nenhum no Render.
    api_key = os.getenv("RESEND_API_KEY", "")
    remetente = os.getenv("EMAIL_FROM") or "onboarding@resend.dev"

    payload: dict = {
        "from": remetente,
        "to": [destinatario],
        "subject": assunto,
        "text": corpo_texto,
    }
    if corpo_html:
        payload["html"] = corpo_html

    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # MELHORIA: sem um User-Agent proprio, o urllib manda um generico
            # ("Python-urllib/3.12") que o Cloudflare na frente da API do
            # Resend bloqueia direto (403, "error code: 1010" -- visto ao
            # vivo em teste real). Testado: so adicionar este header resolve.
            "User-Agent": "EducaGame/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            response.read()
        return True
    except HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="ignore")
        print(f"[EMAIL] Falha ao enviar (Resend) para {destinatario}: HTTP {e.code}: {detalhe}")
        return False
    except Exception as e:
        print(f"[EMAIL] Falha ao enviar (Resend) para {destinatario}: {type(e).__name__}: {e}")
        return False


def _enviar_via_brevo(destinatario: str, assunto: str, corpo_texto: str, corpo_html: str | None) -> bool:
    # MELHORIA: mesma razao do Resend (SMTP bloqueado no Render) -- usa a
    # API HTTP "Transactional Email" do Brevo (v3/smtp/email), nao o SMTP
    # relay antigo. Diferente do Resend, o Brevo deixa verificar so um
    # remetente avulso (sem precisar de dominio proprio) -- visto ao vivo:
    # remetente @hotmail.com verificado (nao autenticado por DKIM) ainda
    # assim entregou com sucesso (201) tanto pra Gmail quanto pra Hotmail
    # em teste real. Sem dominio autenticado a entrega nao tem garantia
    # total pra alto volume, mas funciona bem pro volume desta aplicacao.
    api_key = os.getenv("BREVO_API_KEY", "")
    remetente_email = os.getenv("EMAIL_FROM") or os.getenv("SMTP_FROM") or ""
    remetente_nome = os.getenv("EMAIL_FROM_NOME") or "EducaGame"

    payload: dict = {
        "sender": {"name": remetente_nome, "email": remetente_email},
        "to": [{"email": destinatario}],
        "subject": assunto,
        "textContent": corpo_texto,
    }
    if corpo_html:
        payload["htmlContent"] = corpo_html

    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "EducaGame/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            response.read()
        return True
    except HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="ignore")
        print(f"[EMAIL] Falha ao enviar (Brevo) para {destinatario}: HTTP {e.code}: {detalhe}")
        return False
    except Exception as e:
        print(f"[EMAIL] Falha ao enviar (Brevo) para {destinatario}: {type(e).__name__}: {e}")
        return False


def enviar_email(destinatario: str, assunto: str, corpo_texto: str, corpo_html: str | None = None) -> bool:
    # MELHORIA: SMTP nao funciona no Render (porta 587 bloqueada na rede
    # de saida -- "OSError: [Errno 101] Network is unreachable", visto ao
    # vivo em producao), entao qualquer provedor via API HTTP (porta 443)
    # tem prioridade. Brevo vem primeiro por ja ter um remetente verificado
    # de verdade que entrega (testado ao vivo pra Gmail e Hotmail); Resend
    # so entrega pro proprio dono da conta sem dominio verificado. SMTP
    # continua disponivel como ultimo recurso pra quem roda fora do Render.
    if _brevo_configurado():
        return _enviar_via_brevo(destinatario, assunto, corpo_texto, corpo_html)
    if _resend_configurado():
        return _enviar_via_resend(destinatario, assunto, corpo_texto, corpo_html)
    if _smtp_configurado():
        return _enviar_via_smtp(destinatario, assunto, corpo_texto, corpo_html)
    print(f"[EMAIL] Nenhum provedor de e-mail configurado; e-mail para {destinatario} nao enviado. Assunto: {assunto}")
    return False
