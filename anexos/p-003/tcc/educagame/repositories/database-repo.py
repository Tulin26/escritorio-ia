from __future__ import annotations

from datetime import datetime, timedelta

from repositories.supabase_client import supabase
from repositories.log_repo import (
    buscar_logs,
    registrar_log,
    registrar_log_com_tempo,
    tempo_resposta_para_media,
)

from core.runtime_context import get_runtime

runtime = get_runtime()


# ====================== ALUNOS ======================

@runtime.cache_data(ttl=60)
def buscar_alunos(escola_id: str):
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
        print(f"Erro ao buscar alunos: {e}")
        return []


def buscar_aluno_por_id(aluno_id: str):
    try:
        res = supabase.table("alunos").select("*").eq("id", aluno_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao buscar aluno: {e}")
        return None


def limpar_caches_de_pontos() -> None:
    """Renova as leituras de pontos depois de uma resposta gravada.

    MELHORIA: aqui morava `somar_pontos_aluno`, que lia o total e gravava o
    total + pontos -- e o gatilho `trg_atualizar_pontos` do banco somava DE
    NOVO a cada log inserido. Medido em 13/09/2026: a conta de teste tinha 510
    pontos, 355 somados por esta funcao (por dificuldade) e 155 pelo gatilho
    (+10/-5). Quem soma agora e so o banco (ver a migracao
    20260913120000_pontos_por_dificuldade_no_banco.sql), numa conta so, sem o
    ler-e-gravar que perdia pontos quando duas respostas chegavam juntas.

    Sobra para o app o que so ele tem: as leituras em cache (30-60 s) do
    ranking e das turmas, que mostrariam o total velho logo depois da resposta.
    """
    try:
        buscar_alunos.clear()
        buscar_ranking.clear()
        buscar_ranking_guildas.clear()
        buscar_resumo_turma.clear()
    except Exception as e:
        print(f"Erro ao renovar os caches de pontos: {e}")


# ====================== RANKING ======================

@runtime.cache_data(ttl=30)
def buscar_ranking(escola_id: str, limite: int = 5):
    try:
        return (
            supabase.table("alunos")
            .select("*")
            .eq("escola_id", escola_id)
            .order("pontos_totais", desc=True)
            .limit(limite)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Erro ao buscar ranking: {e}")
        return []


@runtime.cache_data(ttl=30)
def buscar_ranking_guildas(escola_id: str):
    try:
        alunos = (
            supabase.table("alunos")
            .select("ano_escolar, periodo, pontos_totais")
            .eq("escola_id", escola_id)
            .execute()
            .data
            or []
        )
        guildas: dict[str, int] = {}
        for aluno in alunos:
            chave = f"{aluno.get('ano_escolar', '')} - {aluno.get('periodo', '')}"
            guildas[chave] = guildas.get(chave, 0) + int(aluno.get("pontos_totais") or 0)
        ranking = [{"guilda": k, "pontos_grupais": v} for k, v in guildas.items()]
        ranking.sort(key=lambda item: item["pontos_grupais"], reverse=True)
        return ranking
    except Exception as e:
        print(f"Erro ao buscar ranking de guildas: {e}")
        return []


# ====================== RESUMO TURMA ======================
# MELHORIA: usa view_resumo_turma do banco em vez de cruzar dados em Python,
# evitando carregar todos os logs em memÃ³ria de uma vez.

@runtime.cache_data(ttl=60)
def buscar_resumo_turma(escola_id: str):
    try:
        rows = (
            supabase.table("view_resumo_turma")
            .select("*")
            .eq("escola_id", escola_id)
            .execute()
            .data
            or []
        )
        # Adapta o formato da view para o esperado pela UI
        resumo = []
        for row in rows:
            total = int(row.get("total_questoes") or 0)
            acertos = int(row.get("acertos") or 0)
            erros = total - acertos
            percentual = float(row.get("percentual") or 0)
            tempo_medio_resposta = float(row.get("tempo_medio_resposta") or 0)
            resumo.append({
                "aluno_id": row.get("aluno_id"),
                "nome": row.get("nome", ""),
                "ano_escolar": row.get("ano_escolar", ""),
                "periodo": row.get("periodo", ""),
                "total_questoes": total,
                "acertos": acertos,
                "erros": erros,
                "percentual": int(percentual),
                "tempo_medio_resposta": tempo_medio_resposta,
                "baixo_desempenho": percentual < 50 and total >= 5,
            })
        resumo.sort(key=lambda item: item.get("nome", ""))
        return resumo
    except Exception as e:
        print(f"Erro ao buscar resumo da turma: {e}")
        return []


# ====================== PROGRESSO RPG â€” SUPABASE ======================
# MELHORIA: progresso migrado de JSON local para Supabase.
# JSON local pode ser apagado a cada redeploy em ambientes efemeros.

def salvar_progresso_rpg(
    escola_id: str,
    aluno_id: str,
    aventura_id: str,
    estado: dict,
    origem: str = "manual",
):
    import json
    try:
        estado_limpo = json.loads(json.dumps(estado, ensure_ascii=False))
        payload = {
            "escola_id": escola_id,
            "aluno_id": aluno_id,
            "aventura_id": aventura_id,
            "origem": origem,
            "salvo_em": datetime.now().isoformat(timespec="seconds"),
            "estado": estado_limpo,
        }
        supabase.table("rpg_progressos").upsert(
            payload,
            on_conflict="escola_id,aluno_id,aventura_id",
        ).execute()
        return True, payload
    except Exception as e:
        print(f"Erro ao salvar progresso RPG: {e}")
        return False, str(e)


def carregar_progresso_rpg(escola_id: str, aluno_id: str, aventura_id: str):
    try:
        res = (
            supabase.table("rpg_progressos")
            .select("*")
            .eq("escola_id", escola_id)
            .eq("aluno_id", aluno_id)
            .eq("aventura_id", aventura_id)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao carregar progresso RPG: {e}")
        return None


def listar_progressos_rpg_do_aluno(aluno_id: str):
    """Todo progresso de RPG de um aluno, em qualquer aventura.

    Existe para os pedidos de LGPD (services/dados_pessoais.py): acesso pede
    TUDO que o app guarda da pessoa, e carregar_progresso_rpg acima so
    responde quando ja se sabe a aventura.
    """
    try:
        return (
            supabase.table("rpg_progressos")
            .select("*")
            .eq("aluno_id", str(aluno_id))
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Erro ao listar progressos RPG do aluno: {e}")
        return []


def remover_progresso_rpg(escola_id: str, aluno_id: str, aventura_id: str):
    try:
        supabase.table("rpg_progressos").delete().eq(
            "escola_id", escola_id
        ).eq("aluno_id", aluno_id).eq("aventura_id", aventura_id).execute()
        return True
    except Exception as e:
        print(f"Erro ao remover progresso RPG: {e}")
        return False


# ====================== ESTADO TEMPORARIO DE SESSAO — SUPABASE ======================
# MELHORIA: cache de estado de fluxo (oraculo/treino/laboratorio) migrado do dict
# em memoria de processo (_ESTADOS_FLASK_LOCAIS) para Supabase. Um dict local nao
# sobrevive a reinicio, nao e compartilhado entre workers/instancias do Gunicorn
# e crescia sem limite enquanto o processo ficava de pe. As linhas expiram
# sozinhas (TTL) e sao removidas por uma faxina oportunista a cada gravacao.

TTL_ESTADO_SESSAO_HORAS = 6


def salvar_estado_temporario(chave: str, estado: dict) -> bool:
    import json
    try:
        estado_limpo = json.loads(json.dumps(estado, ensure_ascii=False))
        payload = {
            "chave": chave,
            "estado": estado_limpo,
            "atualizado_em": datetime.now().isoformat(timespec="seconds"),
        }
        supabase.table("estados_sessao").upsert(payload, on_conflict="chave").execute()
        _limpar_estados_sessao_expirados_lazy()
        return True
    except Exception as e:
        print(f"Erro ao salvar estado temporario: {e}")
        return False


def carregar_estado_temporario(chave: str):
    try:
        res = (
            supabase.table("estados_sessao")
            .select("*")
            .eq("chave", chave)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        linha = res.data[0]
        if _estado_sessao_expirado(linha.get("atualizado_em")):
            remover_estado_temporario(chave)
            return None
        return linha.get("estado")
    except Exception as e:
        print(f"Erro ao carregar estado temporario: {e}")
        return None


def remover_estado_temporario(chave: str) -> bool:
    try:
        supabase.table("estados_sessao").delete().eq("chave", chave).execute()
        return True
    except Exception as e:
        print(f"Erro ao remover estado temporario: {e}")
        return False


def _estado_sessao_expirado(atualizado_em: str | None) -> bool:
    if not atualizado_em:
        return False
    try:
        momento = datetime.fromisoformat(str(atualizado_em).replace("Z", "+00:00"))
    except ValueError:
        return False
    agora = datetime.now(momento.tzinfo) if momento.tzinfo else datetime.now()
    return momento < agora - timedelta(hours=TTL_ESTADO_SESSAO_HORAS)


def _limpar_estados_sessao_expirados_lazy() -> None:
    # Faxina oportunista: cerca de 1 a cada 50 gravacoes remove linhas
    # vencidas, evitando depender de um cron so pra isso.
    import random
    if random.randint(1, 50) != 1:
        return
    try:
        limite = (datetime.now() - timedelta(hours=TTL_ESTADO_SESSAO_HORAS)).isoformat(timespec="seconds")
        supabase.table("estados_sessao").delete().lt("atualizado_em", limite).execute()
    except Exception as e:
        print(f"Erro na faxina de estados de sessao: {e}")
