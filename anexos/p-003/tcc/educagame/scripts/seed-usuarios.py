"""Cria os 3 usuarios iniciais de login (um por papel).

Roda uma vez, depois de aplicar as migrations em supabase/migrations/.
Re-executavel: usa upsert por username, entao rodar de novo so atualiza
a senha/papel em vez de duplicar.

Uso:
    python scripts/seed_usuarios.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from repositories.usuario_repo import criar_usuario

USUARIOS_INICIAIS = (
    ("aluno", "aluno", "aluno"),
    ("professores", "professores", "professor"),
    ("desenvolvedor", "desenvolvedor", "desenvolvedor"),
)


def main() -> None:
    for username, senha, role in USUARIOS_INICIAIS:
        resultado = criar_usuario(username, senha, role)
        status = "ok" if resultado is not None else "falhou"
        print(f"[seed_usuarios] {username} ({role}): {status}")

    # MELHORIA: conta de professor sem escola nao entra em lugar nenhum (ver
    # services/auth_service.py::conta_pode_entrar) -- e de proposito: "sem
    # escola" era justamente o estado que abria TODAS. Este script nao tem
    # como adivinhar a unidade, entao avisa em vez de deixar a conta nascer
    # muda.
    print()
    print("[seed_usuarios] FALTA VINCULAR: a conta 'professores' nasce sem escola e")
    print("[seed_usuarios] nao entra ate ser vinculada. No SQL do Supabase:")
    print()
    print("    update public.usuarios")
    print("       set escola_id = (select id from public.escolas where slug = 'SEU-SLUG')")
    print("     where username = 'professores';")
    print()
    print("[seed_usuarios] 'desenvolvedor' e global de proposito e nao precisa.")


if __name__ == "__main__":
    main()
