"""Vários alunos ao mesmo tempo: um aluno esperando a IA não trava os outros.

Medido em 13/09/2026: o app rodava com UM processo síncrono. Durante as
chamadas de IA do RPG (27 a 70 s) o /healthz parou de responder e o Render
reiniciou o app às 22:35:39, derrubando a tela de quem estava usando.

O Gunicorn não roda no Windows, então o que se prende aqui é o que torna as
threads SEGURAS e o que garante que elas estão ligadas.
"""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.ia import providers

RAIZ = Path(__file__).resolve().parents[1]


def _config_gunicorn() -> dict:
    conf: dict = {}
    exec((RAIZ / "gunicorn.conf.py").read_text(encoding="utf-8"), conf)
    return conf


def test_gunicorn_atende_com_threads():
    conf = _config_gunicorn()

    assert conf["worker_class"] == "gthread"
    assert conf["threads"] >= 4, "com poucas threads a checagem de saúde volta a esperar na fila"


@pytest.mark.parametrize("arquivo", ["Procfile", "render.yaml"])
def test_o_comando_de_inicio_nao_desfaz_as_threads(arquivo):
    """Opção passada na linha de comando vence o gunicorn.conf.py."""
    linhas = [l for l in (RAIZ / arquivo).read_text(encoding="utf-8").splitlines() if "gunicorn" in l and not l.strip().startswith("#")]

    assert linhas, f"{arquivo} não tem mais o comando do gunicorn"
    for linha in linhas:
        for opcao in ("--worker-class", " -k ", "--threads", "--workers", " -w "):
            assert opcao not in f" {linha} ", f"{arquivo}: {opcao.strip()} na linha de comando anula gunicorn.conf.py"


def test_as_vagas_de_chamada_de_ia_cabem_todos_os_alunos():
    """Chamada que estoura o prazo continua ocupando vaga até a conexão cair."""
    assert providers._executor_ia._max_workers >= 2 * _config_gunicorn()["threads"]


def test_o_provedor_e_o_aviso_de_um_aluno_nao_vazam_para_outro():
    """Os dois gravam, e só DEPOIS os dois leem -- o pior caso de corrida.

    Com o dicionário único de antes, quem gravasse por último apareceria para
    os dois: o aviso "IA indisponível" de um aluno na tela do outro.
    """
    from flask_app import app

    barreira = threading.Barrier(2, timeout=10)
    lidos: dict[str, tuple[str, str]] = {}
    erros: list[BaseException] = []

    def aluno(nome: str, provedor: str, aviso: str) -> None:
        try:
            with app.test_request_context("/"):
                providers._registrar_ultimo_provedor_ia(provedor)
                providers._registrar_ultimo_erro_ia(aviso)
                barreira.wait()
                lidos[nome] = (providers.obter_ultimo_provedor_ia(), providers.obter_ultimo_erro_ia())
        except BaseException as exc:  # noqa: BLE001 -- a falha precisa chegar ao teste
            erros.append(exc)

    ana = threading.Thread(target=aluno, args=("ana", "groq", ""))
    bia = threading.Thread(target=aluno, args=("bia", "", "IA indisponivel no momento."))
    ana.start()
    bia.start()
    ana.join(15)
    bia.join(15)

    assert not erros, erros
    assert lidos == {"ana": ("groq", ""), "bia": ("", "IA indisponivel no momento.")}


def test_requisicao_que_nao_chamou_a_ia_le_o_ultimo_do_processo():
    """O painel do desenvolvedor mostra o último provedor como diagnóstico geral."""
    from flask_app import app

    with app.test_request_context("/"):
        providers._registrar_ultimo_provedor_ia("mistral")
        providers._registrar_ultimo_erro_ia("limite de uso")

    with app.test_request_context("/"):
        assert providers.obter_ultimo_provedor_ia() == "mistral"
        assert providers.obter_ultimo_erro_ia() == "limite de uso"


def test_fora_do_flask_continua_na_sessao_do_runtime(monkeypatch):
    """Streamlit: st.session_state já é de cada usuário."""
    estado: dict = {}
    monkeypatch.setattr(providers, "runtime", SimpleNamespace(session_state=estado))

    providers._registrar_ultimo_provedor_ia("gemini")
    providers._registrar_ultimo_erro_ia("")

    assert estado == {"ultimo_provedor_ia": "gemini", "ultimo_erro_ia": ""}
    assert providers.obter_ultimo_provedor_ia() == "gemini"
