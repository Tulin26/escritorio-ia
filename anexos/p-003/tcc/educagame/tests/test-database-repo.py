from __future__ import annotations

from datetime import datetime, timedelta

import repositories.database_repo as database_repo


def test_faxina_de_estados_sessao_remove_linhas_vencidas_sem_estourar(monkeypatch, sem_rede_supabase):
    # MELHORIA: regressao para o bug do .lt() ausente (ver
    # tests/test_supabase_client.py). Antes, essa faxina sempre estourava
    # AttributeError (engolido em silencio pelo try/except), entao nenhuma
    # linha vencida era removida de verdade.
    monkeypatch.setattr("random.randint", lambda a, b: 1)  # forca a faxina a rodar

    agora = datetime.now()
    vencida = {
        "chave": "vencida",
        "estado": {},
        "atualizado_em": (agora - timedelta(hours=10)).isoformat(timespec="seconds"),
    }
    recente = {
        "chave": "recente",
        "estado": {},
        "atualizado_em": agora.isoformat(timespec="seconds"),
    }
    tabela = sem_rede_supabase.table("estados_sessao")._tabela
    tabela.linhas.extend([dict(vencida), dict(recente)])

    database_repo._limpar_estados_sessao_expirados_lazy()

    chaves_restantes = {linha["chave"] for linha in tabela.linhas}
    assert chaves_restantes == {"recente"}
