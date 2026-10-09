"""Gestao das contas de login -- a unica tabela que nao tinha tela.

MELHORIA: `usuarios` ficou sem interface desde que substituiu a senha mestra.
Dava para viver assim enquanto a conta nao tinha escola: criar professor era
rodar `scripts/seed_usuarios.py` uma vez e pronto.

Isso mudou quando o vinculo com a escola passou a decidir em que unidade a
conta entra (`services/auth_service.py::conta_pode_entrar`). A partir dali,
vincular um professor virou UPDATE na mao no Supabase -- e a conta nasce SEM
vinculo, ou seja, nasce sem conseguir entrar em lugar nenhum.

As regras dificeis moram aqui, e nao nas telas, porque sao duas telas.
"""

from __future__ import annotations

from repositories.usuario_repo import (
    atualizar_usuario,
    buscar_usuario_por_username,
    criar_usuario,
    listar_usuarios,
)
from services.aluno_auth_service import gerar_senha_legivel
from services.escola_service import listar_escolas

PAPEIS = ("aluno", "professor", "desenvolvedor")

# Papeis que so fazem sentido presos a uma escola. "desenvolvedor" fica de
# fora: e a conta de manutencao, global de proposito.
#
# MELHORIA: "aluno" faltava aqui, e a tela de contas prometia o contrario no
# proprio texto dela -- "Conta sem vinculo aparece marcada, porque ela nao
# entra em lugar nenhum". So cumpria para professor.
#
# Visto no painel da ETEC: a conta `aluno` aparecia com escola "—" e situacao
# "ativa", enquanto `conta_pode_entrar` a RECUSA (a regra la nao olha o papel:
# quem nao e desenvolvedor e nao tem vinculo nao entra). O desenvolvedor
# olhava a lista, via "ativa", e nao tinha como saber que aquela conta estava
# morta.
PAPEIS_COM_ESCOLA = ("professor", "aluno")

# Rotulo do grupo de quem nao esta vinculado a escola nenhuma. Nao e uma
# escola: e o estado em que a conta nao consegue entrar em lugar nenhum.
SEM_ESCOLA = "Sem escola"


def _nome_das_escolas() -> dict[str, str]:
    return {str(e.get("id")): str(e.get("nome") or "") for e in (listar_escolas() or [])}


def listar_contas() -> list[dict]:
    """As contas com o nome da escola ja resolvido, prontas para a tela."""
    nomes = _nome_das_escolas()
    contas = []
    for usuario in listar_usuarios():
        escola_id = str(usuario.get("escola_id") or "")
        contas.append(
            {
                **usuario,
                "escola_id": escola_id,
                "escola_nome": nomes.get(escola_id, ""),
                # MELHORIA: o que a tela precisa destacar nao e "tem escola?",
                # e "esta conta consegue entrar?". Professor sem vinculo passa
                # despercebido numa lista -- e ele simplesmente nao entra.
                "sem_vinculo": bool(
                    str(usuario.get("role", "")) in PAPEIS_COM_ESCOLA and not escola_id
                ),
            }
        )
    return contas


def listar_professores_visiveis(usuario: dict | None) -> list[dict]:
    """Os professores que ESTA conta pode ver, ja com o nome da escola.

    A regra de alcance mora aqui, e nao na tela, porque e a mesma pergunta que
    `conta_pode_entrar` responde no login -- e porque errar para o lado
    frouxo entrega a lista de contas de uma escola para o professor da outra.

    - desenvolvedor: todas as escolas. E a conta de manutencao, global de
      proposito (`conta_pode_entrar` devolve True sem olhar escola).
    - professor: so a propria escola. Sem vinculo, ve nada -- que e o mesmo
      que ele consegue fazer no login.
    - qualquer outro papel (aluno, ou sessao sem usuario): nada.
    """
    dados = usuario if isinstance(usuario, dict) else {}
    papel = str(dados.get("role", ""))

    professores = [c for c in listar_contas() if str(c.get("role", "")) == "professor"]

    if papel == "desenvolvedor":
        return professores
    if papel != "professor":
        return []

    escola_da_conta = str(dados.get("escola_id") or "")
    if not escola_da_conta:
        return []
    return [c for c in professores if str(c.get("escola_id") or "") == escola_da_conta]


def agrupar_professores_por_escola(professores: list[dict]) -> list[tuple[str, list[dict]]]:
    """(nome da escola, professores), em ordem de nome.

    Os sem vinculo vem por ultimo, num grupo proprio: sao os que NAO conseguem
    entrar em lugar nenhum, e a tela precisa que eles saltem aos olhos em vez
    de se perderem no meio da lista.
    """
    por_escola: dict[str, list[dict]] = {}
    for conta in professores or []:
        nome = str(conta.get("escola_nome") or "") or SEM_ESCOLA
        por_escola.setdefault(nome, []).append(conta)

    for contas in por_escola.values():
        contas.sort(key=lambda c: str(c.get("username", "")))

    with_school = sorted((n for n in por_escola if n != SEM_ESCOLA), key=str.lower)
    ordenadas = [(nome, por_escola[nome]) for nome in with_school]
    if SEM_ESCOLA in por_escola:
        ordenadas.append((SEM_ESCOLA, por_escola[SEM_ESCOLA]))
    return ordenadas


def _ultimo_desenvolvedor_ativo(usuario_id: str) -> bool:
    ativos = [
        u
        for u in listar_usuarios()
        if str(u.get("role", "")) == "desenvolvedor" and u.get("ativo", True)
    ]
    return len(ativos) == 1 and str(ativos[0].get("id")) == str(usuario_id)


def vincular_escola(usuario_id: str, escola_id: str) -> tuple[bool, str]:
    """Prende a conta a uma escola (ou solta, com escola_id vazio)."""
    usuario_id = str(usuario_id or "").strip()
    if not usuario_id:
        return False, "Selecione uma conta."

    escola_id = str(escola_id or "").strip()
    if escola_id and escola_id not in _nome_das_escolas():
        return False, "Essa escola não existe."

    resultado = atualizar_usuario(usuario_id, {"escola_id": escola_id or None})
    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível salvar. Verifique a conexão com o Supabase."
    return True, ""


def definir_ativo(usuario_id: str, ativo: bool) -> tuple[bool, str]:
    usuario_id = str(usuario_id or "").strip()
    if not usuario_id:
        return False, "Selecione uma conta."

    # MELHORIA: desativar o ultimo desenvolvedor tranca todo mundo do lado de
    # fora do ADM, e a porta reserva (a Chave Mestra da tela inicial) depende
    # de uma SENHA_MESTRA que pode nem estar configurada. Um clique bastaria,
    # e nao haveria tela nenhuma para desfazer -- so SQL.
    if not ativo and _ultimo_desenvolvedor_ativo(usuario_id):
        return False, "Esta é a última conta de desenvolvedor ativa. Desativá-la trancaria o ADM."

    resultado = atualizar_usuario(usuario_id, {"ativo": bool(ativo)})
    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível salvar. Verifique a conexão com o Supabase."
    return True, ""


def criar_conta(username: str, papel: str, escola_id: str = "", senha: str = "") -> tuple[bool, str, str]:
    """Cria uma conta de login. Devolve (ok, erro, senha_em_texto).

    A senha volta em texto porque e a unica vez que ela existe legivel: o
    banco guarda so o hash. Quem criou precisa anotar antes de sair da tela.
    """
    username = str(username or "").strip().lower()
    if not username:
        return False, "Informe um usuário.", ""
    if " " in username:
        return False, "O usuário não pode ter espaço.", ""

    papel = str(papel or "").strip()
    if papel not in PAPEIS:
        return False, "Papel inválido.", ""

    escola_id = str(escola_id or "").strip()
    # Conta de professor sem escola nasce muda: nao entra em unidade nenhuma
    # (services/auth_service.py::conta_pode_entrar). Melhor recusar aqui, com
    # o motivo na tela, do que criar e a pessoa descobrir no login.
    if papel in PAPEIS_COM_ESCOLA and not escola_id:
        return False, "Escolha a escola desta conta.", ""
    if escola_id and escola_id not in _nome_das_escolas():
        return False, "Essa escola não existe.", ""

    if buscar_usuario_por_username(username):
        return False, "Já existe uma conta com esse usuário.", ""

    senha = str(senha or "").strip() or gerar_senha_legivel()
    if len(senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres.", ""

    resultado = criar_usuario(username, senha, papel, escola_id=escola_id or None)
    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível criar a conta. Verifique a conexão com o Supabase.", ""
    return True, "", senha


def redefinir_senha_de_conta(usuario_id: str, nova_senha: str = "") -> tuple[bool, str, str]:
    """Troca a senha de uma conta de login, pelo painel do desenvolvedor.

    O par de `redefinir_senha_do_aluno`, que ja existia: sem isto, professor
    que esquece a senha so tem saida pelo SQL.
    """
    from core.senhas import hash_senha

    usuario_id = str(usuario_id or "").strip()
    if not usuario_id:
        return False, "Selecione uma conta.", ""

    senha = str(nova_senha or "").strip() or gerar_senha_legivel()
    if len(senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres.", ""

    resultado = atualizar_usuario(usuario_id, {"senha_hash": hash_senha(senha)})
    if resultado is None or not getattr(resultado, "data", None):
        return False, "Não foi possível redefinir a senha. Verifique a conexão com o Supabase.", ""
    return True, "", senha
