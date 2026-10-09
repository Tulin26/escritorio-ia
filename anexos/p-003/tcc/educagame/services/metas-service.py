"""Meta semanal e foco de estudo, prontos para as duas telas.

`core/metas.py` tem a regra, `repositories/meta_repo.py` lê o banco, e aqui
os dois se encontram: o card do aluno em `/progresso` e a lista do professor
no painel.

O foco é um TEMA da própria lista do app (`core.config.get_temas_rpg`), e não
texto livre. Dois motivos: o professor escolhe numa lista em vez de digitar
"progressão aritimética" com erro, e o tema escolhido é exatamente um dos que
o gerador de questões conhece -- então o botão "treinar este tema" na tela do
aluno abre o Oráculo ou o Laboratório já naquele assunto, sem inventar
caminho novo (as duas rotas já aceitam `tema` no formulário).

O foco NÃO muda sozinho o que o aluno recebe. Um professor anotar um tema não
pode fazer o app parar de sortear o resto em silêncio -- o aluno veria sempre
o mesmo assunto sem entender por quê. Ele aparece na tela, com um botão que o
aluno clica se quiser.
"""

from __future__ import annotations

from datetime import datetime

from core.config import get_temas_rpg, normalizar_materia
from core.metas import METAS, inicio_da_semana, progresso_semanal
from repositories.meta_repo import (
    listar_conclusoes_da_escola,
    listar_conclusoes_do_aluno,
    listar_focos_da_escola,
    listar_focos_do_aluno,
)

# As matérias que o professor pode usar no foco. É a mesma lista de temas que
# o gerador conhece; fora dela não há tema para escolher.
MATERIAS_COM_TEMA = (
    "Matematica", "Fisica", "Quimica", "Biologia", "Geografia", "Historia",
    "Portugues", "Ingles", "Filosofia", "Sociologia", "Arte", "Ensino Religioso",
    "Educacao Fisica", "Ciencias",
)


def temas_da_materia(materia: str, ano_escolar: str) -> list[str]:
    return list(get_temas_rpg(normalizar_materia(materia), str(ano_escolar or "")))


def opcoes_de_foco(ano_escolar: str) -> list[dict]:
    """[{materia, temas}] para montar os dois selects encadeados da tela."""
    opcoes = []
    for materia in MATERIAS_COM_TEMA:
        temas = temas_da_materia(materia, ano_escolar)
        if temas and temas != ["conteudo geral da disciplina"]:
            opcoes.append({"materia": materia, "temas": temas})
    return opcoes


def meta_do_aluno(aluno_id: str, logs: list[dict] | None, agora: datetime | None = None) -> dict:
    """O card da tela do aluno: progresso da semana e o foco anotado."""
    if not str(aluno_id or "").strip():
        return {"itens": [], "cumpridas": 0, "total": len(METAS), "tudo_feito": False, "focos": []}

    desde = inicio_da_semana(agora)
    conclusoes = listar_conclusoes_do_aluno(aluno_id, desde)
    progresso = progresso_semanal(logs, conclusoes, agora)
    progresso["focos"] = listar_focos_do_aluno(aluno_id)
    return progresso


def metas_da_turma(
    escola_id: str,
    alunos: list[dict],
    logs: list[dict] | None,
    agora: datetime | None = None,
) -> list[dict]:
    """Uma linha por aluno: quanto já fez desta semana, e o foco dele."""
    if not str(escola_id or "").strip():
        return []

    desde = inicio_da_semana(agora)
    conclusoes = listar_conclusoes_da_escola(escola_id, desde)
    focos = listar_focos_da_escola(escola_id)

    logs_por_aluno: dict[str, list[dict]] = {}
    for log in logs or []:
        logs_por_aluno.setdefault(str(log.get("aluno_id")), []).append(log)

    conclusoes_por_aluno: dict[str, list[dict]] = {}
    for conclusao in conclusoes:
        conclusoes_por_aluno.setdefault(str(conclusao.get("aluno_id")), []).append(conclusao)

    focos_por_aluno: dict[str, list[dict]] = {}
    for foco in focos:
        focos_por_aluno.setdefault(str(foco.get("aluno_id")), []).append(foco)

    linhas = []
    for aluno in alunos or []:
        aluno_id = str(aluno.get("id"))
        progresso = progresso_semanal(
            logs_por_aluno.get(aluno_id, []), conclusoes_por_aluno.get(aluno_id, []), agora
        )
        linhas.append(
            {
                "aluno_id": aluno_id,
                "nome": aluno.get("nome") or "(sem nome)",
                "ano_escolar": aluno.get("ano_escolar") or "",
                "periodo": aluno.get("periodo") or "",
                "itens": progresso["itens"],
                "cumpridas": progresso["cumpridas"],
                "total": progresso["total"],
                "tudo_feito": progresso["tudo_feito"],
                "focos": sorted(
                    focos_por_aluno.get(aluno_id, []), key=lambda f: str(f.get("materia", ""))
                ),
            }
        )

    # Quem está mais longe da meta aparece primeiro: é a lista que o professor
    # precisa olhar, e não a de quem já terminou.
    return sorted(linhas, key=lambda linha: (linha["cumpridas"], linha["nome"]))


def resumo_da_turma(linhas: list[dict]) -> dict:
    total = len(linhas)
    completos = sum(1 for linha in linhas if linha["tudo_feito"])
    sem_nada = sum(1 for linha in linhas if linha["cumpridas"] == 0 and not any(
        item["feito"] for item in linha["itens"]
    ))
    return {
        "alunos": total,
        "completos": completos,
        "sem_nada": sem_nada,
        "percentual": int(completos * 100 / total) if total else 0,
        "desde": inicio_da_semana(),
    }
