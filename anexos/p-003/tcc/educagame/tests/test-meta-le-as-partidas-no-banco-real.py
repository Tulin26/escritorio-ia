"""Uma leitura que só o banco falso dos testes sabia fazer.

Visto em 30/09/2026, no log do Render: desde ff71702 (29/09), toda tela que
mostra a meta semanal registrava

    Erro ao listar conclusoes do aluno: '_SupabaseQuery' object has no attribute 'gte'

`repositories/meta_repo.py` filtra as partidas concluídas "desde segunda" com
`.gte(...)`, e o cliente de verdade (`_SupabaseQuery`) não tinha esse método.
O `except` do repositório engolia o erro e devolvia lista vazia: "Uma jornada
completa" ficava em 0/1 para todo aluno -- e na aba "Metas e foco" do
professor --, por mais partidas que ele terminasse. A GRAVAÇÃO funcionava; só
a leitura quebrava.

A suíte passou inteira porque o `gte` foi acrescentado ao banco FALSO dos
testes (`tests/conftest.py::_SupabaseQueryFalsa`), e não ao cliente real. É a
segunda vez que um método ausente no cliente some dentro de um `except` (a
primeira foi o `.lt()`, contada em `test_supabase_client.py`). Por isso o
primeiro teste aqui não olha o `gte`: olha a classe de defeito. O falso não
pode saber fazer nada que o real não faz.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

import repositories.meta_repo as meta_repo
import repositories.supabase_client as sc


def _metodos_publicos(classe) -> set[str]:
    return {nome for nome in dir(classe) if not nome.startswith("_") and callable(getattr(classe, nome))}


def test_o_banco_falso_nao_sabe_fazer_o_que_o_cliente_real_nao_faz(sem_rede_supabase):
    falsa = type(sem_rede_supabase.table("qualquer_tabela"))

    so_no_falso = _metodos_publicos(falsa) - _metodos_publicos(sc._SupabaseQuery)

    assert so_no_falso == set(), (
        f"o banco falso dos testes sabe {sorted(so_no_falso)} e o cliente real não: "
        "um repositório que use isso passa na suíte e quebra em produção"
    )


# --------------------------------------------------------------------------
# A leitura da meta, com o cliente de verdade e só a rede trocada


class _Resposta:
    def __init__(self, corpo: bytes):
        self._corpo = corpo

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


PARTIDAS = [{"modo": "escape_room", "concluido_em": "2026-09-29T21:28:40+00:00", "acertos": 6, "total": 6}]

# Segunda-feira, 00:00 em Brasília -- o que core/metas.py::inicio_da_semana devolve.
SEGUNDA = datetime(2026, 9, 28, 3, 0, tzinfo=timezone.utc)


@pytest.fixture
def urls_pedidas(monkeypatch):
    urls: list[str] = []

    def falso_urlopen(request, timeout=None):
        urls.append(request.full_url)
        return _Resposta(json.dumps(PARTIDAS).encode("utf-8"))

    monkeypatch.setattr(sc, "urlopen", falso_urlopen)
    monkeypatch.setattr(
        meta_repo, "supabase", sc._SupabaseRestClient("https://example.supabase.co", "chave-de-mentira")
    )
    return urls


@pytest.mark.parametrize(
    ("listar", "dono"),
    [
        pytest.param(meta_repo.listar_conclusoes_do_aluno, "aluno_id", id="aluno"),
        pytest.param(meta_repo.listar_conclusoes_da_escola, "escola_id", id="escola"),
    ],
)
def test_a_meta_le_as_partidas_da_semana_com_o_cliente_real(urls_pedidas, listar, dono):
    assert listar("id-1", desde=SEGUNDA) == PARTIDAS

    filtros = parse_qs(urlsplit(urls_pedidas[0]).query)
    assert filtros[dono] == ["eq.id-1"]
    # O "+" do fuso: cru na URL, o PostgREST o leria como espaço e recusaria a data.
    assert filtros["concluido_em"] == ["gte.2026-09-28T03:00:00+00:00"]
