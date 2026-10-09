from repositories.gravacao import FALHA_NAO_ENCONTRADA, FALHA_RECUSADA, gravar
from repositories.supabase_client import supabase


_ultimo_erro_listar_escolas = ""


def obter_ultimo_erro_listar_escolas() -> str:
    return _ultimo_erro_listar_escolas


def listar_escolas():
    global _ultimo_erro_listar_escolas
    _ultimo_erro_listar_escolas = ""
    try:
        return supabase.table("escolas").select("*").order("nome").execute().data or []
    except Exception as e:
        _ultimo_erro_listar_escolas = str(e)
        print(f"Erro ao listar escolas: {e}")
        return []


# MELHORIA: as tres gravacoes abaixo devolviam so None na falha. O Flask
# olhava, mas dizia "Verifique a conexao" ate para slug repetido; o
# Streamlit nem olhava, e dizia "criada com sucesso". Agora devolvem
# (resultado, motivo) -- ver repositories/gravacao.py.
FALHA_SLUG_REPETIDO = "slug_repetido"

# `slug text unique` em supabase/migrations/20260803120000_bootstrap.sql: o
# Postgres da o nome <tabela>_<coluna>_key.
_RESTRICAO_SLUG = "escolas_slug_key"


def _repetidos(dados: dict) -> dict[str, str]:
    # A restricao so pode estourar se o slug esta sendo gravado. Salvar as
    # preferencias da escola nunca devolve "slug repetido".
    return {_RESTRICAO_SLUG: FALHA_SLUG_REPETIDO} if "slug" in dados else {}


def criar_escola(nome: str, slug: str, cor_tema: str = "#003366", mostrar_ranking: bool = True, modo_guilda: bool = True):
    payload = {
        "nome": nome,
        "slug": slug.lower().strip(),
        "cor_tema": cor_tema,
        "mostrar_ranking": mostrar_ranking,
        "modo_guilda": modo_guilda,
    }
    return gravar(
        lambda: supabase.table("escolas").insert(payload).execute(),
        descricao="criar escola",
        sem_linha=FALHA_RECUSADA,
        repetidos=_repetidos(payload),
    )


def atualizar_escola(escola_id: str, dados: dict):
    return gravar(
        lambda: supabase.table("escolas").update(dados).eq("id", escola_id).execute(),
        descricao="atualizar escola",
        sem_linha=FALHA_NAO_ENCONTRADA,
        repetidos=_repetidos(dados),
    )


def excluir_escola(escola_id: str):
    return gravar(
        lambda: supabase.table("escolas").delete().eq("id", escola_id).execute(),
        descricao="excluir escola",
        sem_linha=FALHA_NAO_ENCONTRADA,
    )


def buscar_escola_por_slug(slug: str):
    try:
        res = supabase.table("escolas").select("*").eq("slug", slug.lower().strip()).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao buscar escola por slug: {e}")
        return None


def buscar_escola_por_id(escola_id: str):
    # Sem cache de proposito: e por aqui que as telas do aluno leem
    # mostrar_ranking e modo_guilda, e o professor que desliga uma opcao
    # espera ver o efeito na proxima tela, nao daqui a um TTL.
    try:
        res = supabase.table("escolas").select("*").eq("id", escola_id).limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao buscar escola por id: {e}")
        return None
