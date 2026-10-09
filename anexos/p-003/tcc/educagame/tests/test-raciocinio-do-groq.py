"""O gpt-oss raciocina pouco: reasoning_effort="low".

O modelo do Groq (gpt-oss-120b) raciocina antes de responder, e o raciocínio
come o MESMO max_tokens da resposta. Nos logs do Render de 13/09, 24/09 e
28/09/2026, ~1 em 3 chamadas terminava em json_validate_failed ("max
completion tokens reached before generating a valid document", ou o JSON
cortado no meio).

Medido em 02/10/2026, com o prompt real do Oráculo e do Laboratório, só o
Groq ligado, 34 chamadas válidas (17 de cada lado):

                          padrão        low
    JSON válido           13 de 17      16 de 17
    no teto de tokens      6             0
    aceitas pelo app       6 de 17      11 de 17
    raciocínio médio      826 tokens    212 tokens
    tempo mediano         3,5 s         1,8 s
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.ia import providers


def setup_function():
    providers._gemini_quota_bloqueado_ate = 0.0
    providers._registrar_ultimo_erro_ia("")


def test_gpt_oss_raciocina_pouco_sem_configurar_nada(monkeypatch):
    monkeypatch.delenv("IA_REASONING_EFFORT", raising=False)

    assert providers._extras_de_raciocinio("openai/gpt-oss-120b") == {"reasoning_effort": "low"}
    assert providers._extras_de_raciocinio("gpt-oss-120b") == {"reasoning_effort": "low"}


@pytest.mark.parametrize(
    "modelo", ["llama-3.3-70b-versatile", "Qwen/Qwen2.5-7B-Instruct", "openai/gpt-4o-mini", ""]
)
def test_modelo_que_nao_raciocina_nao_recebe_o_parametro(monkeypatch, modelo):
    # Mandar reasoning_effort para quem nao raciocina e erro 400 na API.
    monkeypatch.delenv("IA_REASONING_EFFORT", raising=False)

    assert providers._extras_de_raciocinio(modelo) == {}


@pytest.mark.parametrize("valor", ["padrao", "PADRAO", " nenhum ", "off"])
def test_da_para_desligar_pela_variavel_sem_deploy(monkeypatch, valor):
    monkeypatch.setenv("IA_REASONING_EFFORT", valor)

    assert providers._extras_de_raciocinio("openai/gpt-oss-120b") == {}


def test_da_para_trocar_o_nivel_pela_variavel(monkeypatch):
    monkeypatch.setenv("IA_REASONING_EFFORT", "medium")

    assert providers._extras_de_raciocinio("openai/gpt-oss-120b") == {"reasoning_effort": "medium"}


def test_a_chamada_ao_groq_leva_o_parametro_e_a_do_openrouter_nao(monkeypatch):
    monkeypatch.delenv("IA_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("GROQ_MODEL_RESERVA", raising=False)
    recebido: dict[str, dict] = {}

    # Gravado por MODELO: o Groq principal e a reserva usam o mesmo cliente.
    def cliente(nome, resposta):
        class _Completions:
            def create(self, **kwargs):
                recebido[kwargs["model"]] = kwargs
                if resposta is None:
                    raise RuntimeError("fora do ar")
                return resposta

        return SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))

    ok = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'), finish_reason="stop")])
    monkeypatch.setattr(providers, "_chamar_gemini_rest", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("503")))
    monkeypatch.setattr(providers, "_get_groq_client", lambda: cliente("groq", None))
    monkeypatch.setattr(providers, "_get_openrouter_client", lambda: cliente("openrouter", ok))

    assert providers.chamar_ia("Sistema", "Usuario", max_tokens=20) == {"ok": True}

    assert recebido["openai/gpt-oss-120b"]["reasoning_effort"] == "low"
    # A reserva (Qwen) vai com o raciocinio desligado, do jeito que foi medida.
    assert recebido["qwen/qwen3.8-27b"]["reasoning_effort"] == "none"
    assert "reasoning_effort" not in recebido["nvidia/nemotron-3-super-120b-a12b:free"]
