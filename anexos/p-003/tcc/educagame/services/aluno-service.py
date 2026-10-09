from __future__ import annotations

from repositories.aluno_repo import (
    FALHA_RA_REPETIDO,
    buscar_aluno_por_id,
    criar_aluno,
    listar_alunos,
)
from repositories.gravacao import FALHA_RECUSADA, FALHA_SEM_CONEXAO
from services.avisos_de_gravacao import FALTA_ESCOLA, FALTAM_DADOS

MATRICULA_SEM_ESCOLA = FALTA_ESCOLA
MATRICULA_SEM_DADOS = FALTAM_DADOS

# MELHORIA: as duas telas de matricula (Flask e Streamlit) mostram o mesmo
# texto para o mesmo motivo. Nenhum deles repete o erro do banco: o que o
# Postgres responde (nome de restricao, codigo, id da escola) fica no log.
# O do RA repetido e o cenario alternativo do RF03 no TCC.
MENSAGENS_DA_MATRICULA = {
    MATRICULA_SEM_ESCOLA: "Escolha a escola antes de matricular.",
    MATRICULA_SEM_DADOS: "Informe nome e RA/identificação.",
    FALHA_RA_REPETIDO: (
        "O RA informado já pertence a outro aluno da escola. "
        "A matrícula não foi gravada."
    ),
    # "nao confirmada", e nao "nao gravada": num prazo estourado o pedido
    # pode ter chegado ao banco depois que a resposta desistiu.
    FALHA_SEM_CONEXAO: (
        "O banco de dados não respondeu, e a matrícula não foi confirmada. "
        "Tente de novo em instantes."
    ),
    FALHA_RECUSADA: (
        "O banco de dados não aceitou a matrícula. "
        "Se isso se repetir, avise o desenvolvedor."
    ),
}


def registrar_matricula(
    *,
    escola_id: str | None,
    nome: str,
    ra_identificacao: str,
    ano_escolar: str,
    periodo: str,
    ensino_religioso: bool,
) -> tuple[bool, str]:
    """Matricula feita pelo professor. Devolve (True, "") ou (False, motivo).

    O motivo e uma chave de MENSAGENS_DA_MATRICULA, e nao o texto: o Flask
    leva o motivo na URL do redirect, e para la so vai a chave (ver
    tela_professor em web/routes/professor_fla.py).
    """
    if not str(escola_id or "").strip():
        return False, MATRICULA_SEM_ESCOLA
    nome = str(nome or "").strip()
    ra_identificacao = str(ra_identificacao or "").strip()
    if not nome or not ra_identificacao:
        return False, MATRICULA_SEM_DADOS

    resultado, motivo = criar_aluno(
        {
            "nome": nome,
            "ra_identificacao": ra_identificacao,
            "ano_escolar": ano_escolar,
            "periodo": periodo,
            "escola_id": escola_id,
            "pontos_totais": 0,
            "ensino_religioso": bool(ensino_religioso),
        }
    )
    if resultado is None:
        return False, motivo
    return True, ""
