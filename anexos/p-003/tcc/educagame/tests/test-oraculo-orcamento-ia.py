from __future__ import annotations

import time

import services.ia.enigma as enigma


def test_orcamento_do_oraculo_encolhe_a_cada_tentativa(monkeypatch):
    # MELHORIA: regressao para um bug visto em producao. O loop de retry do
    # Oraculo (ate 5 tentativas) chamava gerar_json_ia sem "deadline_seconds",
    # entao cada tentativa usava o orcamento maximo do zero — no pior caso,
    # 5 tentativas podiam somar bem mais que os 60s do timeout do Gunicorn,
    # derrubando o worker com SIGKILL mesmo com o prazo rigido por provedor
    # ja em vigor. Agora o orcamento total e compartilhado entre as tentativas,
    # igual ja acontecia no Laboratorio.
    deadlines_recebidos = []

    def fake_gerar_json_ia(*args, **kwargs):
        deadlines_recebidos.append(kwargs.get("deadline_seconds"))
        return {"pergunta": "x", "opcoes": ["a", "b"], "correta": 99}

    monkeypatch.setattr(enigma, "gerar_json_ia", fake_gerar_json_ia)
    monkeypatch.setattr(enigma, "obter_ultimo_provedor_ia", lambda: "groq")

    enigma.invocar_enigma("Matematica", "3o Ano EM", "Medio", tema="funcoes")

    assert len(deadlines_recebidos) == 5
    assert all(d is not None for d in deadlines_recebidos)
    # cada tentativa deve receber um prazo igual ou menor que a anterior
    assert all(deadlines_recebidos[i] >= deadlines_recebidos[i + 1] for i in range(4))


def test_oraculo_para_de_tentar_quando_orcamento_se_esgota(monkeypatch):
    monkeypatch.setenv("ORACULO_IA_BUDGET_SECONDS", "6")

    chamadas = []

    def fake_gerar_json_ia(*args, **kwargs):
        chamadas.append(kwargs.get("deadline_seconds"))
        time.sleep(2.0)
        return {"pergunta": "x", "opcoes": ["a", "b"], "correta": 99}

    monkeypatch.setattr(enigma, "gerar_json_ia", fake_gerar_json_ia)
    monkeypatch.setattr(enigma, "obter_ultimo_provedor_ia", lambda: "groq")

    inicio = time.monotonic()
    enigma.invocar_enigma("Matematica", "3o Ano EM", "Medio", tema="funcoes")
    decorrido = time.monotonic() - inicio

    # com orcamento de 6s e cada chamada levando 2s, nao deve dar tempo de
    # completar as 5 tentativas (o que levaria 10s)
    assert len(chamadas) < 5
    assert decorrido < 8.0
