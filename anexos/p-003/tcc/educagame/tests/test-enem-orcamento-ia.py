from __future__ import annotations

import time

import services.enem_service as enem_service


def test_orcamento_do_enem_encolhe_a_cada_tentativa(monkeypatch):
    # MELHORIA: regressao para o mesmo bug ja corrigido no Oraculo e no
    # Laboratorio. O loop de retry do ENEM (ate 5 tentativas, tambem usado
    # pela Batalha contra Chefes) chamava gerar_json_ia sem "deadline_seconds",
    # entao cada tentativa usava o orcamento maximo do zero, podendo somar
    # bem mais que os 60s do timeout do Gunicorn no pior caso.
    deadlines_recebidos = []

    def fake_gerar_json_ia(*args, **kwargs):
        deadlines_recebidos.append(kwargs.get("deadline_seconds"))
        time.sleep(0.01)
        return None

    monkeypatch.setattr(enem_service, "gerar_json_ia", fake_gerar_json_ia)
    monkeypatch.setattr(enem_service, "obter_ultimo_provedor_ia", lambda: "groq")

    enem_service.gerar_questao_enem("Matematica e suas Tecnologias", "Medio")

    assert len(deadlines_recebidos) == 5
    assert all(d is not None for d in deadlines_recebidos)
    assert all(deadlines_recebidos[i] >= deadlines_recebidos[i + 1] for i in range(4))


def test_enem_para_de_tentar_quando_orcamento_se_esgota(monkeypatch):
    monkeypatch.setenv("ENEM_IA_BUDGET_SECONDS", "6")

    chamadas = []

    def fake_gerar_json_ia(*args, **kwargs):
        chamadas.append(kwargs.get("deadline_seconds"))
        time.sleep(2.0)
        return None

    monkeypatch.setattr(enem_service, "gerar_json_ia", fake_gerar_json_ia)
    monkeypatch.setattr(enem_service, "obter_ultimo_provedor_ia", lambda: "groq")

    inicio = time.monotonic()
    enem_service.gerar_questao_enem("Matematica e suas Tecnologias", "Medio")
    decorrido = time.monotonic() - inicio

    assert len(chamadas) < 5
    assert decorrido < 8.0
