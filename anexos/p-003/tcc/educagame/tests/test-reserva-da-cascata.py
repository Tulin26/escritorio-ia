"""A reserva da cascata de IA, medida em 08/10/2026.

Toda questão do Groq que o validador recusa é refeita PULANDO o Groq: quem
responde é a reserva. Em 07/10/2026, no ENEM, o Groq respondeu, a questão foi
recusada e a reserva inteira falhou -- o aluno ficou com o banco offline.
Cada provedor tinha o seu motivo:

  - Gemini: o "gemini-flash-latest" vive sobrecarregado na faixa gratuita
    (503 "high demand"). O lite respondeu 8 de 8, todas aceitas pelo
    validador, em 1,6 a 3 s.
  - OpenRouter: "openrouter/free" sorteia um gratuito por pedido, e os
    gratuitos raciocinam até gastar os tokens -- a resposta volta vazia. O
    Nemotron fixo, com o raciocínio desligado, deu 7 de 10.
"""

from __future__ import annotations

from types import SimpleNamespace

from services.ia import providers


def setup_function():
    providers._gemini_quota_bloqueado_ate = 0.0
    providers._registrar_ultimo_erro_ia("")


def test_o_gemini_usa_o_lite_sem_configurar_nada(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    enderecos = []

    def urlopen_falso(pedido, timeout=None):
        enderecos.append(getattr(pedido, "full_url", pedido))
        raise RuntimeError("parou aqui")

    monkeypatch.setattr(providers, "urlopen", urlopen_falso)

    try:
        providers._chamar_gemini_rest("Sistema", "Usuario", max_tokens=10, temperature=0.5)
    except RuntimeError:
        pass

    assert enderecos, "o Gemini nem chegou a montar o pedido"
    assert "/models/gemini-flash-lite-latest:generateContent" in enderecos[0]


def test_o_openrouter_vai_no_nemotron_com_o_raciocinio_desligado(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("IA_REASONING_EFFORT", raising=False)
    recebido: dict = {}

    class _Completions:
        def create(self, **kwargs):
            recebido.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'), finish_reason="stop")]
            )

    monkeypatch.setattr(providers, "_chamar_gemini_rest",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("gemini-off")))
    monkeypatch.setattr(providers, "_get_groq_client", lambda: None)
    monkeypatch.setattr(providers, "_get_openrouter_client",
                        lambda: SimpleNamespace(chat=SimpleNamespace(completions=_Completions())))

    assert providers.chamar_ia("Sistema", "Usuario", max_tokens=20) == {"ok": True}

    assert recebido["model"] == "nvidia/nemotron-3-super-120b-a12b:free"
    # Preso ao servidor da NVIDIA: em 09/10/2026 outro servidor do mesmo
    # modelo devolveu 400 "Reasoning is mandatory ... cannot be disabled".
    assert recebido["extra_body"] == {
        "reasoning": {"enabled": False},
        "provider": {"order": ["nvidia"], "allow_fallbacks": False},
    }
    # O parâmetro do gpt-oss não vai junto: só o Groq o recebe.
    assert "reasoning_effort" not in recebido


def test_modelo_de_fora_da_nvidia_nao_fica_preso_ao_servidor_dela():
    # Preso a um servidor que não o serve, ele falharia sempre -- e calado.
    assert providers._corpo_do_openrouter("google/gemma-4-31b-it:free") == {"reasoning": {"enabled": False}}
    assert "provider" in providers._corpo_do_openrouter("NVIDIA/nemotron-3-super-120b-a12b:free")


def test_um_gpt_oss_posto_na_reserva_recebe_um_reasoning_effort_so(monkeypatch):
    """A reserva do Groq vai com reasoning_effort="none" (o Qwen foi medido
    assim). Se o painel trocar o modelo dela por um gpt-oss, o "low" do gpt-oss
    tem de vencer -- e não chegar dois reasoning_effort, que é TypeError."""
    monkeypatch.setenv("GROQ_MODEL_RESERVA", "openai/gpt-oss-20b")
    monkeypatch.delenv("IA_REASONING_EFFORT", raising=False)
    recebido: dict = {}

    class _Completions:
        def create(self, **kwargs):
            if kwargs["model"] == "openai/gpt-oss-20b":
                recebido.update(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'), finish_reason="stop")]
                )
            raise RuntimeError("principal fora do ar")

    monkeypatch.setattr(providers, "_chamar_gemini_rest",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("gemini-off")))
    monkeypatch.setattr(providers, "_get_groq_client",
                        lambda: SimpleNamespace(chat=SimpleNamespace(completions=_Completions())))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: None)

    assert providers.chamar_ia("Sistema", "Usuario", max_tokens=20) == {"ok": True}
    assert recebido["reasoning_effort"] == "low"
