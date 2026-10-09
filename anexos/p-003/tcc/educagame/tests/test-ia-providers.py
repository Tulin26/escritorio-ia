from __future__ import annotations

from types import SimpleNamespace

from services.ia import providers


def setup_function():
    providers._gemini_quota_bloqueado_ate = 0.0
    providers._registrar_ultimo_erro_ia("")


# Ordem da cascata: Groq, Gemini (prazo curto), Groq reserva, OpenRouter.
# O Gemini era o primeiro e falhava em quase toda chamada, gastando ate 8 s
# antes de o Groq ter a vez (15/09/2026). A reserva do Groq entrou em
# 09/10/2026: outro modelo na mesma chave, com cota propria. Sairam da fila em
# 08 e 09/10/2026: Mistral (limite zero no plano), Cerebras (sem chave no
# Render) e Hugging Face (sem credito).

MODELO_DA_RESERVA = "qwen/qwen3.8-27b"


class _FakeCompletions:
    def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None),
                    finish_reason="stop",
                )
            ]
        )


class _FakeOpenRouterClient:
    chat = SimpleNamespace(completions=_FakeCompletions())


def _resposta_ok():
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content='{"ok": true}'),
                finish_reason="stop",
            )
        ]
    )


def _cliente(nome, chamadas, falha=None):
    """Cliente no formato chat.completions.create: anota a chamada e responde
    ou falha com `falha`."""
    class _Completions:
        def create(self, **_kwargs):
            chamadas.append(nome)
            if falha:
                raise RuntimeError(falha)
            return _resposta_ok()

    class _Cliente:
        chat = SimpleNamespace(completions=_Completions())

    return _Cliente()


def _groq(chamadas, principal=None, reserva="Rate limit reached for model qwen"):
    """O MESMO cliente serve aos dois degraus do Groq; o modelo pedido diz quem
    e quem. `principal` e `reserva`: None responde, texto vira erro."""
    class _Completions:
        def create(self, **kwargs):
            degrau = "groq_reserva" if kwargs.get("model") == MODELO_DA_RESERVA else "groq"
            chamadas.append(degrau)
            falha = reserva if degrau == "groq_reserva" else principal
            if falha:
                raise RuntimeError(falha)
            return _resposta_ok()

    class _Cliente:
        chat = SimpleNamespace(completions=_Completions())

    return _Cliente()


def _gemini_em_quota(chamadas, mensagem="QuotaFailure"):
    def gemini(*_args, **_kwargs):
        chamadas.append("gemini")
        raise RuntimeError(mensagem)

    return gemini


def test_openrouter_com_content_none_falha_sem_attribute_error(monkeypatch):
    monkeypatch.setattr(providers, "_chamar_gemini_rest", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("gemini-off")))
    monkeypatch.setattr(providers, "_get_groq_client", lambda: None)
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: _FakeOpenRouterClient())

    resposta = providers.chamar_ia(
        "Responda somente em JSON.",
        "Retorne um objeto JSON simples.",
        max_tokens=20,
    )

    assert resposta is None
    assert "IA indisponivel" in providers.obter_ultimo_erro_ia()


def test_chamar_ia_usa_groq_primeiro_sem_chamar_o_gemini(monkeypatch):
    chamadas = []

    def gemini_nao_deve_ser_chamado(*_args, **_kwargs):
        chamadas.append("gemini")
        return {"gemini": True}

    monkeypatch.setattr(providers, "_chamar_gemini_rest", gemini_nao_deve_ser_chamado)
    monkeypatch.setattr(providers, "_get_groq_client", lambda: _groq(chamadas))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: chamadas.append("openrouter") or None)

    resposta = providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    assert resposta == {"ok": True}
    assert chamadas == ["groq"]


def test_chamar_ia_tenta_o_gemini_logo_depois_do_groq(monkeypatch):
    chamadas = []

    def gemini_fake(*_args, **_kwargs):
        chamadas.append("gemini")
        return {"ok": True}

    monkeypatch.setattr(providers, "_chamar_gemini_rest", gemini_fake)
    monkeypatch.setattr(providers, "_get_groq_client", lambda: _groq(chamadas, principal="groq-off"))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: chamadas.append("openrouter") or None)

    resposta = providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    assert resposta == {"ok": True}
    assert chamadas == ["groq", "gemini"]


def test_a_reserva_do_groq_vem_depois_do_gemini(monkeypatch):
    chamadas = []
    monkeypatch.setattr(providers, "_chamar_gemini_rest", _gemini_em_quota(chamadas))
    monkeypatch.setattr(providers, "_get_groq_client",
                        lambda: _groq(chamadas, principal="Rate limit reached: tokens per day", reserva=None))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: chamadas.append("openrouter") or None)

    resposta = providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    assert resposta == {"ok": True}
    assert chamadas == ["groq", "gemini", "groq_reserva"]


def test_a_reserva_do_groq_nao_e_pulada_junto_com_o_groq(monkeypatch):
    """O caso que mais importa: a questao do Groq foi RECUSADA pelo validador e
    e refeita pulando o "groq". A reserva e outro modelo -- ela ainda tenta."""
    chamadas = []
    monkeypatch.setattr(providers, "_chamar_gemini_rest", _gemini_em_quota(chamadas))
    monkeypatch.setattr(providers, "_get_groq_client", lambda: _groq(chamadas, reserva=None))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: chamadas.append("openrouter") or None)

    resposta = providers.chamar_ia("Sistema", "Usuario", max_tokens=20, pular_provedores={"groq"})

    assert resposta == {"ok": True}
    assert chamadas == ["gemini", "groq_reserva"]


def test_chamar_ia_usa_openrouter_quando_a_reserva_tambem_falha(monkeypatch):
    chamadas = []
    monkeypatch.setattr(providers, "_chamar_gemini_rest", _gemini_em_quota(chamadas))
    monkeypatch.setattr(providers, "_get_groq_client", lambda: _groq(chamadas, principal="groq-off"))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: _cliente("openrouter", chamadas))

    resposta = providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    assert resposta == {"ok": True}
    assert chamadas == ["groq", "gemini", "groq_reserva", "openrouter"]


def test_chamar_ia_pula_gemini_temporariamente_depois_de_quota(monkeypatch):
    chamadas = []
    monkeypatch.setattr(providers, "_chamar_gemini_rest",
                        _gemini_em_quota(chamadas, "QuotaFailure: GenerateRequestsPerMinutePerProjectPerModel-FreeTier"))
    monkeypatch.setattr(providers, "_get_groq_client", lambda: _groq(chamadas, principal="groq-off", reserva=None))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: chamadas.append("openrouter") or None)

    primeira = providers.chamar_ia("Sistema", "Usuario", max_tokens=20)
    segunda = providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    assert primeira == {"ok": True}
    assert segunda == {"ok": True}
    assert chamadas == ["groq", "gemini", "groq_reserva", "groq", "groq_reserva"]


def test_a_cascata_inteira_falhando_cai_no_offline(monkeypatch):
    chamadas = []
    monkeypatch.setattr(providers, "_chamar_gemini_rest", _gemini_em_quota(chamadas))
    monkeypatch.setattr(providers, "_get_groq_client",
                        lambda: _groq(chamadas, principal="Rate limit reached: tokens per day"))
    monkeypatch.setattr(providers, "_get_openrouter_client",
                        lambda: _cliente("openrouter", chamadas, falha="openrouter-off"))

    resposta = providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    # A cascata inteira, na ordem, e mais ninguem: um provedor que volte para a
    # lista sem decisao (como o Mistral, que so recusava) aparece aqui.
    assert resposta is None
    assert chamadas == ["groq", "gemini", "groq_reserva", "openrouter"]
    assert "limite" in providers.obter_ultimo_erro_ia().lower()


def test_gemini_recusado_nesta_questao_nao_e_chamado_de_novo(monkeypatch):
    """O Laboratório pede de novo pulando quem já foi recusado: o Gemini também
    precisa respeitar a lista, agora que ele vem depois do Groq."""
    chamadas = []

    def gemini_nao_deve_ser_chamado(*_args, **_kwargs):
        chamadas.append("gemini")
        return {"gemini": True}

    monkeypatch.setattr(providers, "_chamar_gemini_rest", gemini_nao_deve_ser_chamado)
    monkeypatch.setattr(providers, "_get_groq_client", lambda: _groq(chamadas, principal="groq-off", reserva=None))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: chamadas.append("openrouter") or None)

    resposta = providers.chamar_ia("Sistema", "Usuario", max_tokens=20, pular_provedores={"gemini"})

    assert resposta == {"ok": True}
    assert chamadas == ["groq", "groq_reserva"]


def test_quem_saiu_da_cascata_saiu_do_codigo():
    """Mistral e Cerebras saíram em 08/10/2026; o Hugging Face, em 09/10. Sem
    cliente, chave nem SDK: se um deles voltar, volta por decisão, com o
    requirements, o .env.example e a página de privacidade junto."""
    for cliente in ("_get_mistral_client", "_get_cerebras_client", "_get_huggingface_client"):
        assert not hasattr(providers, cliente), cliente


# ====================== O PRAZO CURTO DO GEMINI ======================


def test_o_gemini_espera_so_o_prazo_proprio(monkeypatch):
    """Visto nos logs de 08 a 15/09/2026: o Gemini estourava 8 s em quase toda
    chamada. Agora, quando chega a vez dele, o prazo é o dele -- não o de todos."""
    prazos = []

    def prazo_rigido(_func, timeout):
        prazos.append(timeout)
        raise TimeoutError("simulado")

    monkeypatch.setattr(providers, "_com_prazo_rigido", prazo_rigido)
    monkeypatch.setattr(providers, "_timeout_gemini_segundos", lambda: 2.5)
    for obter in ("_get_groq_client", "_get_openrouter_client"):
        monkeypatch.setattr(providers, obter, lambda: None)

    providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    assert prazos == [2.5]


def test_o_prazo_do_gemini_e_menor_que_o_dos_outros_e_ajustavel(monkeypatch):
    monkeypatch.delenv("GEMINI_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("IA_PROVIDER_TIMEOUT_SECONDS", raising=False)
    assert providers._timeout_gemini_segundos() < providers._timeout_ia_segundos()

    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "3")
    assert providers._timeout_gemini_segundos() == 3.0

    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "999")
    assert providers._timeout_gemini_segundos() == 25.0

    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "0")
    assert providers._timeout_gemini_segundos() == 1.0
