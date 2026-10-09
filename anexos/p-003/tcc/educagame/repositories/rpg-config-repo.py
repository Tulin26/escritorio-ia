from repositories.gravacao import FALHA_NAO_ENCONTRADA, FALHA_RECUSADA, gravar
from repositories.supabase_client import supabase


RPG_CONFIG_COLUMNS = {
    "escola_id",
    "titulo",
    "heroi_nome",
    "poderes",
    "materia",
    "serie",
    "cenario",
    "objetivo_final",
    "descricao",
}


def _preparar_payload_rpg(dados: dict):
    payload = {chave: valor for chave, valor in dados.items() if chave in RPG_CONFIG_COLUMNS}
    for chave in ("titulo", "heroi_nome", "poderes", "materia", "serie", "cenario", "objetivo_final", "descricao"):
        if chave in payload and payload[chave] is not None:
            payload[chave] = str(payload[chave]).strip()
    return payload


def listar_rpg_configs(escola_id: str):
    try:
        res = (
            supabase.table("rpg_config")
            .select("*")
            .eq("escola_id", escola_id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Erro ao listar configs RPG: {e}")
        return []


# MELHORIA: as tres gravacoes abaixo devolviam so None na falha, e as duas
# telas diziam "Aventura salva." sem olhar. Agora devolvem (resultado, motivo)
# -- ver repositories/gravacao.py.
def criar_rpg_config(dados: dict):
    return gravar(
        lambda: supabase.table("rpg_config").insert(_preparar_payload_rpg(dados)).execute(),
        descricao="criar config RPG",
        sem_linha=FALHA_RECUSADA,
    )


# MELHORIA: editar e excluir filtravam so pelo id. Com a chave service_role
# o RLS nao protege nada, e o id vem de um campo hidden do formulario: quem
# postasse o id de uma aventura de OUTRA escola a alterava -- e, como o
# payload leva o escola_id da sessao, a puxava para a propria escola. O
# delete apagava a de qualquer uma. Agora o filtro tem a escola, e id de
# outra escola volta sem linha: FALHA_NAO_ENCONTRADA, como id inexistente.
def atualizar_rpg_config(escola_id: str, config_id: str, dados: dict):
    # A escola nao se troca por update: ela so entra no filtro.
    payload = {chave: valor for chave, valor in _preparar_payload_rpg(dados).items() if chave != "escola_id"}
    return gravar(
        lambda: (
            supabase.table("rpg_config")
            .update(payload)
            .eq("id", config_id)
            .eq("escola_id", escola_id)
            .execute()
        ),
        descricao="atualizar config RPG",
        sem_linha=FALHA_NAO_ENCONTRADA,
    )


def excluir_rpg_config(escola_id: str, config_id: str):
    return gravar(
        lambda: supabase.table("rpg_config").delete().eq("id", config_id).eq("escola_id", escola_id).execute(),
        descricao="excluir config RPG",
        sem_linha=FALHA_NAO_ENCONTRADA,
    )
