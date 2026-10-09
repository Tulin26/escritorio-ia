from __future__ import annotations

from werkzeug.security import check_password_hash

from repositories.usuario_repo import buscar_usuario_por_username


def autenticar(username: str, senha: str) -> dict | None:
    # MELHORIA: o mesmo campo "usuario" agora aceita tanto o username
    # compartilhado (professor/desenvolvedor) quanto o e-mail individual
    # de cada aluno (ver services/aluno_auth_service.py) — os dois vivem em
    # tabelas diferentes e nao ha colisao de valores entre eles.
    identificador = str(username or "").strip()
    if "@" in identificador:
        from services.aluno_auth_service import autenticar_aluno_por_email

        aluno = autenticar_aluno_por_email(identificador, senha)
        if not aluno:
            return None
        return {
            "id": aluno.get("id"),
            "username": aluno.get("email"),
            "role": "aluno",
            "aluno_id": aluno.get("id"),
            "aluno_nome": aluno.get("nome"),
            "ano_escolar": aluno.get("ano_escolar"),
            "escola_id": aluno.get("escola_id"),
        }

    usuario = buscar_usuario_por_username(identificador)
    if usuario and usuario.get("ativo", True) and check_password_hash(usuario.get("senha_hash", ""), str(senha or "")):
        return {
            "id": usuario.get("id"),
            "username": usuario.get("username"),
            "role": usuario.get("role"),
            # MELHORIA: a conta de professor nao trazia escola, e sem escola
            # ela abria TODAS -- bastava escolher outra unidade na lista de
            # entrada. Ver conta_pode_entrar() abaixo.
            "escola_id": usuario.get("escola_id"),
        }

    # MELHORIA: nao achou em usuarios (professor/desenvolvedor) -- tenta
    # como aluno com login simples (usuario/senha), pra contas criadas
    # diretamente pelo professor/desenvolvedor sem passar pelo cadastro
    # publico por e-mail (que exige confirmacao).
    from services.aluno_auth_service import autenticar_aluno_por_username

    aluno = autenticar_aluno_por_username(identificador, senha)
    if not aluno:
        return None
    return {
        "id": aluno.get("id"),
        "username": aluno.get("username"),
        "role": "aluno",
        "aluno_id": aluno.get("id"),
        "aluno_nome": aluno.get("nome"),
        "ano_escolar": aluno.get("ano_escolar"),
        "escola_id": aluno.get("escola_id"),
    }


# ====================== A QUAL ESCOLA A CONTA PERTENCE ======================

# MELHORIA: a regra existia so no Streamlit, so para aluno, escrita dentro da
# tela (st/ui/home_st.py). O Flask nao checava nada: copiava a escola da conta
# para a sessao e seguia. Resultado medido: a conta de professor entregue ao
# diretor de uma escola abria o painel de gestao da outra -- alunos, logs,
# ranking -- porque professor nao tinha escola nenhuma.
#
# Agora e uma regra so, chamada pelos dois frontends. Regra escrita em um
# lugar e a unica que nao diverge.

MOTIVO_SEM_VINCULO = (
    "Sua conta não está vinculada a nenhuma escola. "
    "Peça ao desenvolvedor para vincular sua conta antes de entrar."
)
MOTIVO_OUTRA_ESCOLA = "Sua conta pertence a outra escola. Selecione a unidade correta."

# A recusa da porta do ADM, nos DOIS frontends. Generica de proposito: dizer
# "esse usuario nao existe" conta a quem esta tentando que o OUTRO nome
# existe. A mesma frase serve para senha errada, usuario inexistente e conta
# que existe mas nao e de desenvolvedor.
MOTIVO_ADM_RECUSADO = "Usuário ou senha inválidos, ou esta conta não é de desenvolvedor."


def conta_pode_entrar(usuario: dict | None, escola_id) -> tuple[bool, str]:
    """Se esta conta pode entrar NESTA escola. Devolve (pode, motivo).

    O desenvolvedor e global de proposito: e a conta de manutencao, e o painel
    ADM existe justamente para agir sobre todas as escolas.

    Conta sem vinculo e RECUSADA, nao liberada. Fica registrado porque a
    tentacao e grande de fazer o contrario: "sem escola" era exatamente o
    estado que abria todas as escolas, entao tratar como "pode tudo" seria
    manter o furo com outro nome. O preco e uma transicao explicita -- ver
    supabase/migrations/20260831120000_usuarios_escola.sql, que traz o UPDATE
    pronto.
    """
    dados = usuario or {}
    if str(dados.get("role", "")) == "desenvolvedor":
        return True, ""

    escola_pedida = str(escola_id or "")
    if not escola_pedida:
        # Ninguem escolheu escola ainda (por exemplo, /login aberto direto):
        # nao ha o que comparar. Quem barra e a tela seguinte, que resolve a
        # escola e chama esta funcao de novo.
        return True, ""

    escola_da_conta = str(dados.get("escola_id") or "")
    if not escola_da_conta:
        return False, MOTIVO_SEM_VINCULO
    if escola_da_conta != escola_pedida:
        return False, MOTIVO_OUTRA_ESCOLA
    return True, ""
