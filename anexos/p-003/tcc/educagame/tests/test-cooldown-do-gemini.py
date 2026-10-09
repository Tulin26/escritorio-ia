"""O Gemini para de ser tentado enquanto está sobrecarregado, não só sem cota.

MELHORIA: o cooldown existia só para cota (`429`). Medido em 02/09/2026,
rodando a cascata com a configuração do Render:

    [IA] Gemini falhou (RuntimeError): Gemini erro 503:
         "This model is currently experiencing high demand"       ← 3 de 4
    [IA] Gemini falhou (TimeoutError): prazo de 8,0s excedido      ← 1 de 4

Ele é o **primeiro** da fila e gastava até 8 s antes de passar a vez — quase
metade do orçamento de 20 s da cadeia. E, sem cooldown para o 503, era tentado
de novo na requisição seguinte, e na outra, perdendo 8 s de cada vez.

A duração é menor que a da cota de propósito: 503 é sobrecarga passageira do
lado deles; cota diária só volta quando a janela vira.
"""

from __future__ import annotations

import pytest

import services.ia.providers as provedores


@pytest.fixture(autouse=True)
def _cooldown_limpo():
    """O cooldown é estado de processo: sem limpar, um teste contamina o outro."""
    provedores._gemini_quota_bloqueado_ate = 0.0
    provedores._gemini_motivo_bloqueio = ""
    yield
    provedores._gemini_quota_bloqueado_ate = 0.0
    provedores._gemini_motivo_bloqueio = ""


# ====================== O QUE CONTA COMO SOBRECARGA ======================


MENSAGENS_DE_503 = [
    'Gemini erro 503: {"error": {"code": 503, "message": "This model is '
    'currently experiencing high demand. Spikes in demand are usually '
    'temporary. Please try again later.", "status": "UNAVAILABLE"}}',
    "Error code: 503 - Service Unavailable",
    "The model is overloaded. Please try again later.",
]


@pytest.mark.parametrize("mensagem", MENSAGENS_DE_503)
def test_o_503_do_gemini_e_reconhecido(mensagem):
    assert provedores._erro_de_indisponibilidade_ia(mensagem)


@pytest.mark.parametrize(
    "mensagem",
    [
        "Error code: 429 - rate_limit_exceeded",
        "quota exceeded for this project",
        "invalid api key",
        "",
    ],
)
def test_o_que_nao_e_sobrecarga_nao_e_confundido(mensagem):
    assert not provedores._erro_de_indisponibilidade_ia(mensagem)


def test_cota_e_sobrecarga_sao_coisas_diferentes():
    """As duas param o Gemini, mas por motivos e prazos distintos.

    Confundi-las faria o 429 herdar o prazo curto -- e a cota não volta em 30
    segundos.
    """
    cota = "Error code: 429 - rate limit reached, tokens per day"
    sobrecarga = "Gemini erro 503: high demand"

    assert provedores._erro_de_quota_ia(cota)
    assert not provedores._erro_de_indisponibilidade_ia(cota)

    assert provedores._erro_de_indisponibilidade_ia(sobrecarga)
    assert not provedores._erro_de_quota_ia(sobrecarga)


# ====================== O EFEITO ======================


def test_depois_de_um_503_o_gemini_e_pulado():
    """É o ponto todo: sem isto, a requisição seguinte perde 8 s de novo."""
    assert not provedores._gemini_em_cooldown_quota()

    provedores._registrar_cooldown_indisponivel_gemini()

    assert provedores._gemini_em_cooldown_quota()


def test_o_log_diz_qual_foi_o_motivo():
    """A mensagem dizia "por quota recente" para qualquer caso.

    Quem ler o log precisa distinguir "estourou a cota do dia" de "o Google
    está sobrecarregado agora" — são ações diferentes.
    """
    provedores._registrar_cooldown_indisponivel_gemini()
    assert provedores._motivo_do_cooldown_gemini() == "sobrecarga"

    provedores._gemini_quota_bloqueado_ate = 0.0
    provedores._registrar_cooldown_quota_gemini()
    assert provedores._motivo_do_cooldown_gemini() == "quota"


def test_a_sobrecarga_espera_menos_que_a_cota():
    assert (
        provedores._cooldown_indisponivel_gemini_segundos()
        < provedores._cooldown_quota_gemini_segundos()
    )


def test_o_cooldown_mais_longo_vence_o_mais_curto():
    """Um 503 logo depois de um 429 não pode encurtar a espera da cota.

    O registro é `max`, não sobrescrita: quem já está de castigo por cota
    continua até o fim dele.
    """
    provedores._registrar_cooldown_quota_gemini()
    fim_da_cota = provedores._gemini_quota_bloqueado_ate

    provedores._registrar_cooldown_indisponivel_gemini()

    assert provedores._gemini_quota_bloqueado_ate == fim_da_cota


def test_cooldown_zerado_desliga_a_trava(monkeypatch):
    """`0` desliga, explicitamente -- é a convenção do resto do projeto."""
    monkeypatch.setattr(provedores, "_cooldown_indisponivel_gemini_segundos", lambda: 0.0)

    provedores._registrar_cooldown_indisponivel_gemini()

    assert not provedores._gemini_em_cooldown_quota()


def test_os_dois_prazos_sao_ajustaveis_por_variavel(monkeypatch):
    monkeypatch.setenv("GEMINI_INDISPONIVEL_COOLDOWN_SECONDS", "5")
    monkeypatch.setenv("GEMINI_QUOTA_COOLDOWN_SECONDS", "600")

    assert provedores._cooldown_indisponivel_gemini_segundos() == 5.0
    assert provedores._cooldown_quota_gemini_segundos() == 600.0


def test_valor_absurdo_e_aparado():
    """Uma hora é o teto: um cooldown eterno tiraria o Gemini da cascata."""
    import os

    os.environ["GEMINI_INDISPONIVEL_COOLDOWN_SECONDS"] = "999999"
    try:
        assert provedores._cooldown_indisponivel_gemini_segundos() == 3600.0
    finally:
        os.environ.pop("GEMINI_INDISPONIVEL_COOLDOWN_SECONDS", None)


# ====================== O CAMINHO DE VERDADE ======================


def test_um_503_na_cascata_registra_o_cooldown(monkeypatch):
    """A ligação, e não só a peça.

    Os testes acima chamam `_registrar_cooldown_indisponivel_gemini` direto —
    passavam mesmo com o `elif` do 503 arrancado de `chamar_ia`. Este exercita
    o caminho que a cascata usa de verdade.
    """
    def gemini_sobrecarregado(*_args, **_kwargs):
        raise RuntimeError('Gemini erro 503: "This model is currently experiencing high demand"')

    monkeypatch.setattr(provedores, "_chamar_gemini_rest", gemini_sobrecarregado)
    monkeypatch.setattr(provedores, "_get_secret", lambda nome: "chave" if "KEY" in nome else None)
    # os dois seguintes ficam sem cliente: a cadeia inteira falha e cai offline
    for obter in ("_get_groq_client", "_get_openrouter_client"):
        monkeypatch.setattr(provedores, obter, lambda: None)

    provedores.chamar_ia("sistema", "usuario", max_tokens=50)

    assert provedores._gemini_em_cooldown_quota(), "o 503 não gerou cooldown"
    assert provedores._motivo_do_cooldown_gemini() == "sobrecarga"


def test_um_429_na_cascata_registra_como_cota(monkeypatch):
    """O par do teste acima: o motivo não pode virar 'sobrecarga' para tudo."""
    def gemini_sem_cota(*_args, **_kwargs):
        raise RuntimeError("Gemini erro 429: quota exceeded")

    monkeypatch.setattr(provedores, "_chamar_gemini_rest", gemini_sem_cota)
    monkeypatch.setattr(provedores, "_get_secret", lambda nome: "chave" if "KEY" in nome else None)
    for obter in ("_get_groq_client", "_get_openrouter_client"):
        monkeypatch.setattr(provedores, obter, lambda: None)

    provedores.chamar_ia("sistema", "usuario", max_tokens=50)

    assert provedores._gemini_em_cooldown_quota()
    assert provedores._motivo_do_cooldown_gemini() == "quota"


# ====================== CADA MARCADOR SOZINHO ======================


@pytest.mark.parametrize(
    "mensagem",
    [
        "erro 503",                       # só o código
        "Service Unavailable",            # só a palavra
        "The model is overloaded",        # só "overloaded"
        "experiencing high demand",       # só "high demand"
        "Please try again later",         # só a frase
    ],
)
def test_cada_marcador_sozinho_ja_identifica_a_sobrecarga(mensagem):
    """Sem isto, tirar um marcador da lista passava despercebido: as mensagens
    reais trazem vários ao mesmo tempo, e os outros seguravam o teste."""
    assert provedores._erro_de_indisponibilidade_ia(mensagem), mensagem


def test_cooldown_zero_nao_marca_nem_o_motivo(monkeypatch):
    """`0` desliga de verdade: nem a trava, nem o rótulo do log."""
    monkeypatch.setattr(provedores, "_cooldown_indisponivel_gemini_segundos", lambda: 0.0)

    provedores._registrar_cooldown_indisponivel_gemini()

    assert not provedores._gemini_em_cooldown_quota()
    assert provedores._motivo_do_cooldown_gemini() == "quota", "marcou motivo sem ter travado"
