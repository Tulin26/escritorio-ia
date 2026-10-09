from __future__ import annotations

from core.senhas import hash_senha

from repositories.supabase_client import supabase


def criar_usuario(username: str, senha: str, role: str, ativo: bool = True, escola_id=None):
    try:
        payload = {
            "username": username.strip().lower(),
            "senha_hash": hash_senha(senha),
            "role": role,
            "ativo": ativo,
        }
        # So entra no payload quando foi informado: o upsert atualiza apenas as
        # colunas enviadas, entao omitir preserva o vinculo que a conta ja tem.
        # Mandar None apagaria a escola e devolveria a conta ao estado global.
        if escola_id is not None:
            payload["escola_id"] = escola_id
        return supabase.table("usuarios").upsert(payload, on_conflict="username").execute()
    except Exception as e:
        print(f"Erro ao criar usuario: {e}")
        return None


def buscar_usuario_por_username(username: str):
    try:
        res = (
            supabase.table("usuarios")
            .select("*")
            .eq("username", username.strip().lower())
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Erro ao buscar usuario: {e}")
        return None


def listar_usuarios() -> list[dict]:
    """Todas as contas de login, sem o hash da senha.

    MELHORIA: `usuarios` era a unica tabela sem interface. Enquanto o vinculo
    com a escola nao existia dava para viver assim; depois que ele passou a
    decidir em que escola a conta entra (services/auth_service.py
    ::conta_pode_entrar), vincular professor virou UPDATE na mao no Supabase.

    O senha_hash fica FORA do select de proposito: ele nao serve para tela
    nenhuma, e o que nao e buscado nao vaza por descuido de template.
    """
    try:
        res = (
            supabase.table("usuarios")
            .select("id,username,role,ativo,escola_id,criado_em")
            .order("role")
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"Erro ao listar usuarios: {e}")
        return []


def atualizar_usuario(usuario_id: str, dados: dict):
    try:
        return supabase.table("usuarios").update(dados).eq("id", str(usuario_id)).execute()
    except Exception as e:
        print(f"Erro ao atualizar usuario: {e}")
        return None
