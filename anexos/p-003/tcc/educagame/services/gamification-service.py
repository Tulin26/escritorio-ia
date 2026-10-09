from __future__ import annotations

from core.config import MATERIAS, materia_base


def streak_acertos(logs):
    if not logs:
        return 0
    maior = atual = 0
    for registro in logs:
        if registro.get("resultado") == "Acertou":
            atual += 1
            maior = max(maior, atual)
        else:
            atual = 0
    return maior


def _materias_acertadas(logs) -> set[str]:
    return {
        materia_base(registro.get("materia", ""))
        for registro in logs
        if registro.get("resultado") == "Acertou"
    }


# MELHORIA: o campo "emoji" de cada badge era, na verdade, pontuacao
# comum (*, !, #, $ etc.), nao emoji nenhum -- visivel na tela de Perfil
# do aluno como simbolos genericos em vez de icones. Nunca foi corrigido
# desde a criacao das badges.
BADGES = [
    {
        "id": "primeiro_acerto",
        "emoji": "⭐",
        "nome": "Primeira Estrela",
        "desc": "Acertou sua primeira questão",
        "cond": lambda logs, al: any(r.get("resultado") == "Acertou" for r in logs),
    },
    {
        "id": "dez_acertos",
        "emoji": "🔥",
        "nome": "Em Chamas",
        "desc": "Acertou 10 questões no total",
        "cond": lambda logs, al: sum(1 for r in logs if r.get("resultado") == "Acertou") >= 10,
    },
    {
        "id": "cinquenta_acertos",
        "emoji": "💎",
        "nome": "Diamante",
        "desc": "Acertou 50 questões no total",
        "cond": lambda logs, al: sum(1 for r in logs if r.get("resultado") == "Acertou") >= 50,
    },
    {
        "id": "sem_errar",
        "emoji": "🎯",
        "nome": "Mira Perfeita",
        "desc": "Acertou 5 questões seguidas sem errar",
        "cond": lambda logs, al: streak_acertos(logs) >= 5,
    },
    {
        "id": "streak_10",
        "emoji": "⚡",
        "nome": "Relâmpago",
        "desc": "Acertou 10 questões seguidas sem errar",
        "cond": lambda logs, al: streak_acertos(logs) >= 10,
    },
    {
        "id": "multimateria",
        "emoji": "📚",
        "nome": "Enciclopédia",
        "desc": "Acertou questões em 4 matérias diferentes",
        "cond": lambda logs, al: len(_materias_acertadas(logs)) >= 4,
    },
    {
        "id": "rpg_completo",
        "emoji": "🦸",
        "nome": "Herói Lendário",
        "desc": "Completou uma aventura RPG",
        "cond": lambda logs, al: any(
            str(r.get("materia", "")).startswith("RPG-") and r.get("resultado") == "Acertou"
            for r in logs
        ),
    },
    {
        "id": "lab_mestre",
        "emoji": "⚗️",
        "nome": "Alquimista",
        "desc": "Acertou 10 questões no Laboratório",
        "cond": lambda logs, al: sum(
            1
            for r in logs
            if str(r.get("materia", "")).startswith("LAB-") and r.get("resultado") == "Acertou"
        )
        >= 10,
    },
    {
        "id": "cem_questoes",
        "emoji": "💯",
        "nome": "Centenário",
        "desc": "Respondeu 100 questões no total",
        "cond": lambda logs, al: len(logs) >= 100,
    },
    {
        "id": "persistente",
        "emoji": "💪",
        "nome": "Persistente",
        "desc": "Respondeu 20 questões mesmo errando algumas",
        "cond": lambda logs, al: len(logs) >= 20,
    },
    {
        "id": "mestre_todas",
        "emoji": "👑",
        "nome": "Mestre Supremo",
        # MELHORIA: a descricao e a condicao eram fixas em "9 materias" --
        # sobrou de quando o curriculo tinha 9 materias. Hoje tem 14
        # (ver core/config.py::MATERIAS), entao a badge desbloqueava com
        # 64% das materias, nao "todas" como o nome promete.
        "desc": f"Acertou questões em todas as {len(MATERIAS)} matérias",
        "cond": lambda logs, al: len(_materias_acertadas(logs)) >= len(MATERIAS),
    },
    {
        "id": "duzentas_questoes",
        "emoji": "🎖️",
        "nome": "Veterano",
        "desc": "Respondeu 200 questões no total",
        "cond": lambda logs, al: len(logs) >= 200,
    },
]


def calcular_badges(logs_aluno, aluno):
    desbloqueadas = []
    for badge in BADGES:
        try:
            if badge["cond"](logs_aluno, aluno):
                desbloqueadas.append(badge)
        except Exception:
            pass
    return desbloqueadas
