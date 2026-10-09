from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from repositories.supabase_client import supabase


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(valor: str | None) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None


def buscar(chave: str) -> tuple[Any, bool]:
    """Retorna (valor, encontrado). encontrado=False se nao houver entrada
    ou se ela ja tiver expirado."""
    try:
        res = supabase.table("cache_dados").select("*").eq("chave", chave).limit(1).execute()
    except Exception as e:
        print(f"Erro ao ler cache '{chave}': {e}")
        return None, False
    if not res.data:
        return None, False
    linha = res.data[0]
    expira_em = _parse_datetime(linha.get("expira_em"))
    if expira_em is None or expira_em <= _agora():
        return None, False
    # Copia via ida-e-volta por JSON: garante que o chamador nunca receba
    # (nem consiga corromper com uma mutacao local) o mesmo objeto guardado
    # na linha, igual aconteceria com uma resposta HTTP de verdade.
    return json.loads(json.dumps(linha.get("valor"), ensure_ascii=False)), True


def salvar(chave: str, valor: Any, ttl: float) -> None:
    try:
        valor_serializavel = json.loads(json.dumps(valor, ensure_ascii=False))
        payload = {
            "chave": chave,
            "valor": valor_serializavel,
            "expira_em": (_agora() + timedelta(seconds=ttl)).isoformat(),
            "atualizado_em": _agora().isoformat(),
        }
        supabase.table("cache_dados").upsert(payload, on_conflict="chave").execute()
    except Exception as e:
        print(f"Erro ao gravar cache '{chave}': {e}")


def limpar_prefixo(prefixo: str) -> None:
    try:
        supabase.table("cache_dados").delete().like("chave", f"{prefixo}*").execute()
    except Exception as e:
        print(f"Erro ao limpar cache '{prefixo}': {e}")
