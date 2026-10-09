"""Um 502/503/504 do gateway do Supabase ganha UMA segunda tentativa -- quando repetir é seguro.

Visto em 13/09/2026: cinco "Gateway Timeout" num dia, em requisições mínimas.
Ver o comentário em repositories/supabase_client.py.
"""

from __future__ import annotations

import io
from urllib.error import HTTPError

import pytest

import repositories.supabase_client as sc


class _Resposta:
    def __init__(self, corpo: bytes):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def roteiro(monkeypatch):
    """Cada item é a resposta de uma chamada: um status de erro ou o corpo."""
    chamadas: list[str] = []

    def montar(*respostas):
        def falso_urlopen(request, timeout=None):
            chamadas.append(request.get_method())
            resposta = respostas[len(chamadas) - 1]
            if isinstance(resposta, int):
                raise HTTPError(request.full_url, resposta, "erro", {}, io.BytesIO(b'{"message":"Gateway Timeout"}'))
            return _Resposta(resposta)

        monkeypatch.setattr(sc, "urlopen", falso_urlopen)
        monkeypatch.setattr(sc, "_ESPERA_ANTES_DE_REPETIR", 0)
        return chamadas

    return montar


def _cliente():
    return sc._SupabaseRestClient("https://example.supabase.co", "chave-de-mentira")


@pytest.mark.parametrize(
    "consulta",
    [
        pytest.param(lambda c: c.table("escolas").select("*"), id="select"),
        pytest.param(lambda c: c.table("estados_sessao").upsert({"chave": "x"}, on_conflict="chave"), id="upsert"),
        pytest.param(lambda c: c.table("alunos").update({"nome": "A"}).eq("id", "1"), id="update"),
        pytest.param(lambda c: c.table("estados_sessao").delete().eq("chave", "x"), id="delete"),
    ],
)
@pytest.mark.parametrize("status", [502, 503, 504])
def test_erro_do_gateway_ganha_segunda_tentativa(roteiro, consulta, status):
    chamadas = roteiro(status, b'[{"ok": true}]')

    resultado = consulta(_cliente()).execute()

    assert resultado.data == [{"ok": True}]
    assert len(chamadas) == 2


def test_insert_nao_repete(roteiro):
    # Um log repetido seria uma resposta contada duas vezes pelo gatilho de pontos.
    chamadas = roteiro(504, b"[]")

    with pytest.raises(RuntimeError, match="Supabase REST erro 504"):
        _cliente().table("logs_pedagogicos").insert({"aluno_id": "1"}).execute()

    assert chamadas == ["POST"]


def test_erro_que_nao_e_do_gateway_nao_repete(roteiro):
    chamadas = roteiro(400, b"[]")

    with pytest.raises(RuntimeError, match="Supabase REST erro 400"):
        _cliente().table("estados_sessao").upsert({"chave": "x"}, on_conflict="chave").execute()

    assert len(chamadas) == 1


def test_so_uma_segunda_tentativa(roteiro):
    chamadas = roteiro(504, 504, b"[]")

    with pytest.raises(RuntimeError, match="Supabase REST erro 504"):
        _cliente().table("escolas").select("*").execute()

    assert len(chamadas) == 2
