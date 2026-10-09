"""O log diz em quanto tempo a questão saiu, e não só quem respondeu.

Item 10 do relatório de QA de 23/09/2026 (desempenho): a espera passava de 20
segundos com regularidade, e o relatório pediu para rever o prazo da cascata.
Medindo os logs do Render em 28/09 deu para contar quantas questões desceram
a cascata (cada falha vira uma linha), mas não quanto o aluno esperou: a
PRIMEIRA tentativa, que é a mais cara, não deixava marca nenhuma. Decidir o
prazo sem isso seria palpite.

Agora as três saídas da cascata carregam o tempo: quem respondeu, o orçamento
estourado e a desistência quando ninguém responde.
"""

from __future__ import annotations

import re
import threading
import time
from types import SimpleNamespace

from services.ia import providers

TEMPO = re.compile(r" em \d+\.\d s")


def setup_function():
    providers._gemini_quota_bloqueado_ate = 0.0
    providers._registrar_ultimo_erro_ia("")


def _groq_que_responde():
    def create(**_kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'), finish_reason="stop")]
        )

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def _sem_provedores(monkeypatch, com_groq=False):
    monkeypatch.setattr(providers, "_chamar_gemini_rest",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("gemini-off")))
    monkeypatch.setattr(providers, "_get_groq_client", (lambda: _groq_que_responde()) if com_groq else (lambda: None))
    for nome in ("_get_openrouter_client",):
        monkeypatch.setattr(providers, nome, lambda: None)


def test_quem_respondeu_vem_com_o_tempo(monkeypatch, capsys):
    _sem_provedores(monkeypatch, com_groq=True)

    assert providers.chamar_ia("Sistema", "Usuario", max_tokens=20) == {"ok": True}

    linha = next(l for l in capsys.readouterr().out.splitlines() if l.startswith("[IA] OK"))
    assert TEMPO.search(linha), f"linha sem o tempo: {linha!r}"


def test_desistencia_da_cascata_vira_linha_com_tempo(monkeypatch, capsys):
    _sem_provedores(monkeypatch)

    assert providers.chamar_ia("Sistema", "Usuario", max_tokens=20) is None

    saida = capsys.readouterr().out
    linha = next(l for l in saida.splitlines() if "nenhum provedor respondeu" in l)
    assert TEMPO.search(linha), f"linha sem o tempo: {linha!r}"
    assert "usando offline" in linha, "a linha precisa dizer o desfecho, e não só o tempo"


def test_orcamento_estourado_diz_o_tempo(monkeypatch, capsys):
    _sem_provedores(monkeypatch)
    # Prazo curto e um provedor que gasta tempo: o orçamento estoura logo
    # depois dele. Com todos falhando instantaneamente nada é consumido, e a
    # linha nem chega a existir.
    monkeypatch.setattr(providers, "_timeout_cadeia_ia_segundos", lambda: 3.0)
    monkeypatch.setattr(providers, "_get_groq_client", lambda: time.sleep(0.2))

    providers.chamar_ia("Sistema", "Usuario", max_tokens=20, deadline_seconds=3.0)

    saida = capsys.readouterr().out
    esgotado = [l for l in saida.splitlines() if "Orcamento de tempo esgotado" in l]
    assert esgotado, f"sem essa linha o teste não estaria conferindo nada. Saída:\n{saida}"
    for linha in esgotado:
        assert TEMPO.search(linha), f"linha sem o tempo: {linha!r}"
        assert "usando offline" in linha


def test_o_relogio_e_por_thread(monkeypatch):
    # gunicorn roda com gthread: duas questões podem ser geradas ao mesmo
    # tempo no mesmo processo. Uma thread não pode marcar o relógio da outra.
    _sem_provedores(monkeypatch, com_groq=True)
    providers.chamar_ia("Sistema", "Usuario", max_tokens=20)

    de_outra_thread = []

    def sem_cadeia():
        de_outra_thread.append(providers._tempo_da_cadeia())

    t = threading.Thread(target=sem_cadeia)
    t.start()
    t.join()

    assert de_outra_thread == [""], "thread que não rodou a cascata não pode herdar o relógio de outra"
    assert providers._tempo_da_cadeia() != "", "a thread que rodou a cascata mantém o próprio relógio"


def test_fora_da_cascata_nao_inventa_tempo(monkeypatch):
    # _registrar_sucesso_provedor é chamado de dentro da cascata; se algum dia
    # for usado fora, a linha sai sem tempo em vez de sair com um número solto.
    monkeypatch.delattr(providers._relogio_da_cadeia, "inicio", raising=False)
    assert providers._tempo_da_cadeia() == ""
