"""Regressao das duas falhas silenciosas que este projeto ja teve."""

from __future__ import annotations

import pytest

from core.diagnostico_config import verificar_configuracao


@pytest.fixture
def ambiente_limpo(monkeypatch):
    """Zera tudo que o diagnostico le, para o teste nao depender do .env."""
    from core import diagnostico_config as dc

    nomes = {n for grupo in dc.OBRIGATORIAS for n in grupo}
    nomes |= set(dc.CHAVES_DE_IA) | set(dc.MODELOS_COM_FORNECEDOR)
    for nome in nomes:
        monkeypatch.delenv(nome, raising=False)
    # secrets vazio: fora do Streamlit o contexto neutro ja devolve nada
    monkeypatch.setattr(dc, "_lido", lambda nome: "", raising=False)
    return monkeypatch


def _mensagens(achados, nivel=None):
    return " | ".join(m for n, m in achados if nivel is None or n == nivel)


def test_acusa_supabase_ausente(ambiente_limpo):
    # MELHORIA: o deploy no Streamlit Cloud subiu assim -- tela normal, banco
    # nenhum, e a falha so aparecia ao tentar listar as escolas.
    achados = verificar_configuracao()

    assert any(nivel == "erro" for nivel, _ in achados)
    assert "SUPABASE_URL" in _mensagens(achados, "erro")


def test_acusa_modelo_sem_prefixo_de_fornecedor(monkeypatch):
    # MELHORIA: GROQ_MODEL="gpt-oss-120b" (sem "openai/") fazia o Groq
    # responder 404 a cada questao e a cascata cair no proximo provedor,
    # em silencio. Passou semanas assim.
    from core import diagnostico_config as dc

    valores = {
        "SUPABASE_URL": "https://x.supabase.co",
        "SUPABASE_KEY": "eyJ...",
        "GROQ_API_KEY": "gsk_...",
        "GROQ_MODEL": "gpt-oss-120b",
    }
    monkeypatch.setattr(dc, "_lido", lambda nome: valores.get(nome, ""), raising=False)

    erros = _mensagens(verificar_configuracao(), "erro")

    assert "GROQ_MODEL" in erros
    assert "openai/gpt-oss-120b" in erros


def test_modelo_com_prefixo_nao_e_acusado(monkeypatch):
    from core import diagnostico_config as dc

    valores = {
        "SUPABASE_URL": "https://x.supabase.co",
        "SUPABASE_KEY": "eyJ...",
        "GROQ_API_KEY": "gsk_...",
        "GROQ_MODEL": "openai/gpt-oss-120b",
    }
    monkeypatch.setattr(dc, "_lido", lambda nome: valores.get(nome, ""), raising=False)

    assert verificar_configuracao() == []


def test_a_reserva_do_groq_sem_prefixo_tambem_e_acusada(monkeypatch):
    # A mesma armadilha vale para o segundo modelo do Groq (09/10/2026):
    # "qwen3.8-27b" sem o "qwen/" responde 404, e a reserva some em silencio.
    from core import diagnostico_config as dc

    valores = {
        "SUPABASE_URL": "https://x.supabase.co",
        "SUPABASE_KEY": "eyJ...",
        "GROQ_API_KEY": "gsk_...",
        "GROQ_MODEL_RESERVA": "qwen3.8-27b",
    }
    monkeypatch.setattr(dc, "_lido", lambda nome: valores.get(nome, ""), raising=False)

    erros = _mensagens(verificar_configuracao(), "erro")

    assert "GROQ_MODEL_RESERVA" in erros
    assert "qwen/qwen3.8-27b" in erros


@pytest.mark.parametrize(
    "nome_da_chave",
    ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY"],
)
def test_aceita_os_tres_nomes_da_chave(monkeypatch, nome_da_chave):
    # O app aceita os tres (repositories/supabase_client.py). Checar so um
    # faria o diagnostico acusar falta de configuracao num app que funciona
    # -- e verificador que grita a toa ensina a ignorar o log.
    from core import diagnostico_config as dc

    valores = {
        "SUPABASE_URL": "https://x.supabase.co",
        nome_da_chave: "eyJ...",
        "GEMINI_API_KEY": "AIza...",
    }
    monkeypatch.setattr(dc, "_lido", lambda nome: valores.get(nome, ""), raising=False)

    assert verificar_configuracao() == []


def test_avisa_quando_nao_ha_nenhuma_chave_de_ia(monkeypatch):
    from core import diagnostico_config as dc

    valores = {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_KEY": "eyJ..."}
    monkeypatch.setattr(dc, "_lido", lambda nome: valores.get(nome, ""), raising=False)

    achados = verificar_configuracao()

    assert [n for n, _ in achados] == ["aviso"]
    assert "offline" in _mensagens(achados)
