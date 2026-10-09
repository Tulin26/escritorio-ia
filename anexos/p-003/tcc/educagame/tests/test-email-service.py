from __future__ import annotations

from unittest.mock import MagicMock, patch

import services.email_service as email_service


def _limpar_env_provedores(monkeypatch):
    for chave in ("BREVO_API_KEY", "RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(chave, raising=False)


def test_enviar_email_usa_brevo_quando_configurado(monkeypatch):
    _limpar_env_provedores(monkeypatch)
    monkeypatch.setenv("BREVO_API_KEY", "chave-teste")
    monkeypatch.setenv("EMAIL_FROM", "remetente@hotmail.com")

    resposta_falsa = MagicMock()
    resposta_falsa.__enter__.return_value.read.return_value = b"{}"
    with patch.object(email_service, "urlopen", return_value=resposta_falsa) as urlopen_mock:
        ok = email_service.enviar_email("aluno@example.com", "Assunto", "corpo texto")

    assert ok is True
    chamada = urlopen_mock.call_args[0][0]
    assert chamada.full_url == "https://api.brevo.com/v3/smtp/email"
    assert chamada.get_header("Api-key") == "chave-teste"


def test_enviar_email_usa_resend_quando_brevo_nao_configurado(monkeypatch):
    _limpar_env_provedores(monkeypatch)
    monkeypatch.setenv("RESEND_API_KEY", "chave-teste")

    resposta_falsa = MagicMock()
    resposta_falsa.__enter__.return_value.read.return_value = b"{}"
    with patch.object(email_service, "urlopen", return_value=resposta_falsa) as urlopen_mock:
        ok = email_service.enviar_email("aluno@example.com", "Assunto", "corpo texto")

    assert ok is True
    chamada = urlopen_mock.call_args[0][0]
    assert chamada.full_url == "https://api.resend.com/emails"
    assert chamada.get_header("Authorization") == "Bearer chave-teste"


def test_enviar_email_prioriza_brevo_sobre_resend_e_smtp(monkeypatch):
    # MELHORIA: SMTP (porta 587) e bloqueado na rede de saida do Render
    # ("Network is unreachable", visto ao vivo em producao) -- entre os
    # provedores via API HTTP, Brevo vem primeiro por ja ter um remetente
    # verificado que entrega de verdade (testado ao vivo pra Gmail e
    # Hotmail); Resend sem dominio proprio so entrega pro dono da conta.
    _limpar_env_provedores(monkeypatch)
    monkeypatch.setenv("BREVO_API_KEY", "chave-brevo")
    monkeypatch.setenv("RESEND_API_KEY", "chave-resend")
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "conta@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "senha-app")

    resposta_falsa = MagicMock()
    resposta_falsa.__enter__.return_value.read.return_value = b"{}"
    with patch.object(email_service, "urlopen", return_value=resposta_falsa) as urlopen_mock:
        with patch.object(email_service.smtplib, "SMTP") as smtp_mock:
            ok = email_service.enviar_email("aluno@example.com", "Assunto", "corpo texto")

    assert ok is True
    smtp_mock.assert_not_called()
    chamada = urlopen_mock.call_args[0][0]
    assert chamada.full_url == "https://api.brevo.com/v3/smtp/email"


def test_enviar_email_usa_smtp_quando_nenhuma_api_configurada(monkeypatch):
    _limpar_env_provedores(monkeypatch)
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "conta@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "senha-app")

    servidor_falso = MagicMock()
    with patch.object(email_service.smtplib, "SMTP") as smtp_mock:
        smtp_mock.return_value.__enter__.return_value = servidor_falso
        ok = email_service.enviar_email("aluno@example.com", "Assunto", "corpo texto")

    assert ok is True
    servidor_falso.login.assert_called_once_with("conta@gmail.com", "senha-app")


def test_enviar_email_sem_nenhum_provedor_configurado(monkeypatch):
    _limpar_env_provedores(monkeypatch)

    ok = email_service.enviar_email("aluno@example.com", "Assunto", "corpo texto")

    assert ok is False


def test_brevo_falha_com_http_error_devolve_false(monkeypatch):
    from urllib.error import HTTPError

    _limpar_env_provedores(monkeypatch)
    monkeypatch.setenv("BREVO_API_KEY", "chave-teste")

    erro = HTTPError(
        url="https://api.brevo.com/v3/smtp/email",
        code=400,
        msg="Bad Request",
        hdrs=None,
        fp=MagicMock(read=lambda: b'{"message": "invalid sender"}'),
    )
    with patch.object(email_service, "urlopen", side_effect=erro):
        ok = email_service.enviar_email("aluno@example.com", "Assunto", "corpo texto")

    assert ok is False
