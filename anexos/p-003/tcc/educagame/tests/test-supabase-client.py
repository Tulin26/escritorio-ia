from __future__ import annotations

from repositories.supabase_client import _SupabaseRestClient


def _params(query):
    return dict(query._params)


def test_lt_monta_filtro_postgrest_igual_ao_eq():
    # MELHORIA: regressao para um bug visto em producao. _SupabaseQuery
    # tinha eq/order/limit mas nunca teve .lt(), embora
    # repositories/database_repo.py:_limpar_estados_sessao_expirados_lazy
    # chamasse .lt("atualizado_em", limite) pra apagar estados_sessao
    # vencidos — todo AttributeError ali era engolido pelo try/except,
    # entao a faxina nunca rodou de verdade em producao.
    client = _SupabaseRestClient("https://exemplo.supabase.co", "chave-fake")
    query = client.table("estados_sessao").delete().lt("atualizado_em", "2026-01-01T00:00:00")

    assert _params(query)["atualizado_em"] == "lt.2026-01-01T00:00:00"
    assert query._metodo == "DELETE"


def test_lt_pode_ser_combinado_com_eq():
    client = _SupabaseRestClient("https://exemplo.supabase.co", "chave-fake")
    query = (
        client.table("logs_pedagogicos")
        .select("*")
        .eq("escola_id", "escola-1")
        .lt("data_hora", "2026-01-01")
    )

    parametros = _params(query)
    assert parametros["escola_id"] == "eq.escola-1"
    assert parametros["data_hora"] == "lt.2026-01-01"


def test_like_monta_filtro_postgrest_com_curinga():
    # MELHORIA: usado por repositories/cache_repo.py:limpar_prefixo pra
    # invalidar de uma vez todas as entradas de cache de uma funcao
    # (independente dos argumentos), via prefixo da chave.
    client = _SupabaseRestClient("https://exemplo.supabase.co", "chave-fake")
    query = client.table("cache_dados").delete().like("chave", "modulo.funcao:*")

    assert _params(query)["chave"] == "like.modulo.funcao:*"
    assert query._metodo == "DELETE"
