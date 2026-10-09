from __future__ import annotations

from repositories.gravacao import FALHA_RECUSADA, gravar
from repositories.supabase_client import supabase
from core.runtime_context import get_runtime

runtime = get_runtime()


ALUNO_COLUMNS = {
    "id", "nome", "ra_identificacao", "ano_escolar",
    "periodo", "pontos_totais", "ensino_religioso", "escola_id",
    "email", "senha_hash", "email_confirmado", "username",
    "consentimento_dados_em",
}


def _preparar_payload_aluno(dados: dict):
    payload = {chave: valor for chave, valor in dados.items() if chave in ALUNO_COLUMNS}
    if "ra_identificacao" in payload and payload["ra_identificacao"] is not None:
        payload["ra_identificacao"] = str(payload["ra_identificacao"]).strip()
    if "nome" in payload and payload["nome"] is not None:
        payload["nome"] = str(payload["nome"]).strip()
    return payload


@runtime.cache_data(ttl=60)
def listar_alunos(escola_id: str):
    try:
        return (
            supabase.table("alunos")
            .select("*")
            .eq("escola_id", escola_id)
            .order("nome")
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Erro ao listar alunos: {e}")
        return []


def buscar_aluno_por_id(aluno_id: str):
    try:
        res = supabase.table("alunos").select("*").eq("id", aluno_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao buscar aluno por id: {e}")
        return None


def buscar_aluno_por_email(email: str):
    try:
        res = (
            supabase.table("alunos")
            .select("*")
            .eq("email", str(email or "").strip().lower())
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao buscar aluno por email: {e}")
        return None


def buscar_aluno_por_username(username: str):
    try:
        res = (
            supabase.table("alunos")
            .select("*")
            .eq("username", str(username or "").strip().lower())
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao buscar aluno por username: {e}")
        return None


def confirmar_email_aluno(aluno_id: str):
    try:
        result = (
            supabase.table("alunos")
            .update({"email_confirmado": True})
            .eq("id", aluno_id)
            .execute()
        )
        _limpar_caches_alunos()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Erro ao confirmar email do aluno: {e}")
        return None


def _limpar_caches_alunos() -> None:
    listar_alunos.clear()
    try:
        from repositories.database_repo import buscar_alunos as _buscar_alunos_dados_service

        _buscar_alunos_dados_service.clear()
    except Exception:
        pass


# MELHORIA: criar_aluno engolia a excecao e devolvia so None, e as duas telas
# de matricula diziam "Aluno matriculado." sem olhar o retorno -- o professor
# via sucesso com o aluno fora do banco. Agora o motivo volta junto, porque
# as saidas sao diferentes para quem esta na tela: RA repetido se resolve
# corrigindo o RA; banco fora do ar, tentando de novo.
FALHA_RA_REPETIDO = "ra_repetido"

# supabase/migrations/20260803120000_bootstrap.sql
_RESTRICAO_RA_POR_ESCOLA = "unique_ra_por_escola"


def criar_aluno(dados: dict) -> tuple[object | None, str]:
    """Insere um aluno. Devolve (resultado, "") ou (None, FALHA_*)."""
    resultado, motivo = gravar(
        lambda: supabase.table("alunos").insert(_preparar_payload_aluno(dados)).execute(),
        descricao="criar aluno",
        sem_linha=FALHA_RECUSADA,
        repetidos={_RESTRICAO_RA_POR_ESCOLA: FALHA_RA_REPETIDO},
    )
    if resultado is not None:
        _limpar_caches_alunos()
    return resultado, motivo


def atualizar_aluno_por_id(aluno_id: str, dados: dict):
    try:
        payload = _preparar_payload_aluno(dados)
        result = supabase.table("alunos").update(payload).eq("id", aluno_id).execute()
        _limpar_caches_alunos()
        return result
    except Exception as e:
        print(f"Erro ao atualizar aluno por id: {e}")
        return None


def upsert_alunos(alunos: list[dict]):
    try:
        payload = [_preparar_payload_aluno(aluno) for aluno in alunos]
        result = supabase.table("alunos").upsert(
            payload, on_conflict="escola_id,ra_identificacao"
        ).execute()
        _limpar_caches_alunos()
        return result
    except Exception as e:
        print(f"Erro ao fazer upsert de alunos: {e}")
        return None


def excluir_aluno(aluno_id: str):
    """Apaga um aluno. Os logs e o progresso de RPG dele vao junto.

    O CASCADE esta nas migracoes 20260803120200 (logs_pedagogicos) e
    20260803120300 (rpg_progressos): sem ele sobrariam linhas apontando para
    um aluno que nao existe mais, e o painel do professor contaria respostas
    sem dono.

    Nao ha tela para isto de proposito. Quem usa e script, onde a escolha do
    que apagar fica escrita e revisavel -- ver scripts/criar_alunos_teste.py.
    """
    try:
        result = supabase.table("alunos").delete().eq("id", str(aluno_id)).execute()
        _limpar_caches_alunos()
        return result
    except Exception as e:
        print(f"Erro ao excluir aluno: {e}")
        return None
