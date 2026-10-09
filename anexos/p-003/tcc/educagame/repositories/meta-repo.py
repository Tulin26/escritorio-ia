"""Partidas concluídas e foco de estudo -- as duas tabelas da meta semanal.

Ver `supabase/migrations/20260929120000_metas_e_foco.sql` para o porquê de
serem duas, e `core/metas.py` para a regra que as usa.

Toda leitura devolve lista vazia em caso de erro, como o resto de
`repositories/`: o app funciona sem a meta, e uma tela de progresso que
estoura porque a migração ainda não foi aplicada seria pior que uma tela
mostrando 0 de 10.
"""

from __future__ import annotations

from datetime import datetime, timezone

from repositories.supabase_client import supabase


def registrar_conclusao(
    aluno_id: str,
    escola_id: str,
    modo: str,
    acertos: int | None = None,
    total: int | None = None,
) -> bool:
    """Grava que uma partida terminou. Sem aluno ou escola, não grava nada."""
    if not str(aluno_id or "").strip() or not str(escola_id or "").strip():
        return False
    try:
        supabase.table("conclusoes_modo").insert(
            {
                "aluno_id": str(aluno_id),
                "escola_id": str(escola_id),
                "modo": str(modo or "").strip().lower(),
                # Explicito, e nao o default do banco: a linha fica completa
                # mesmo que a migracao nao tenha sido aplicada com o default,
                # e quem le a tabela nao depende do relogio do Postgres.
                "concluido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "acertos": int(acertos) if acertos is not None else None,
                "total": int(total) if total is not None else None,
            }
        ).execute()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao registrar conclusao de modo: {e}")
        return False


def listar_conclusoes_do_aluno(aluno_id: str, desde: datetime | None = None) -> list[dict]:
    try:
        consulta = supabase.table("conclusoes_modo").select("*").eq("aluno_id", str(aluno_id))
        if desde is not None:
            consulta = consulta.gte("concluido_em", desde.isoformat())
        return consulta.execute().data or []
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao listar conclusoes do aluno: {e}")
        return []


def listar_conclusoes_da_escola(escola_id: str, desde: datetime | None = None) -> list[dict]:
    try:
        consulta = supabase.table("conclusoes_modo").select("*").eq("escola_id", str(escola_id))
        if desde is not None:
            consulta = consulta.gte("concluido_em", desde.isoformat())
        return consulta.execute().data or []
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao listar conclusoes da escola: {e}")
        return []


# ====================== FOCO DE ESTUDO ======================


def salvar_foco(
    aluno_id: str,
    escola_id: str,
    materia: str,
    tema: str,
    observacao: str = "",
    definido_por: str = "",
) -> tuple[bool, str]:
    """Um foco por aluno e matéria: o upsert troca o tema, não empilha."""
    if not str(aluno_id or "").strip() or not str(escola_id or "").strip():
        return False, "Selecione o aluno."
    if not str(materia or "").strip() or not str(tema or "").strip():
        return False, "Escolha a matéria e o tema."
    try:
        supabase.table("foco_do_aluno").upsert(
            {
                "aluno_id": str(aluno_id),
                "escola_id": str(escola_id),
                "materia": str(materia).strip(),
                "tema": str(tema).strip(),
                "observacao": str(observacao or "").strip() or None,
                "definido_por": str(definido_por or "").strip() or None,
                "definido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            on_conflict="aluno_id,materia",
        ).execute()
        return True, ""
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao salvar foco do aluno: {e}")
        return False, "Não foi possível salvar o foco. Verifique a conexão com o Supabase."


def remover_foco(aluno_id: str, materia: str) -> bool:
    try:
        supabase.table("foco_do_aluno").delete().eq("aluno_id", str(aluno_id)).eq(
            "materia", str(materia)
        ).execute()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao remover foco do aluno: {e}")
        return False


def listar_focos_do_aluno(aluno_id: str) -> list[dict]:
    try:
        return (
            supabase.table("foco_do_aluno").select("*").eq("aluno_id", str(aluno_id)).execute().data
            or []
        )
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao listar foco do aluno: {e}")
        return []


def listar_focos_da_escola(escola_id: str) -> list[dict]:
    try:
        return (
            supabase.table("foco_do_aluno").select("*").eq("escola_id", str(escola_id)).execute().data
            or []
        )
    except Exception as e:  # noqa: BLE001
        print(f"Erro ao listar foco da escola: {e}")
        return []
