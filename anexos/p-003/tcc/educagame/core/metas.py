"""Meta semanal de exercícios: quanto o aluno já fez, e quanto falta.

Pedido da coordenação em 28/09/2026: metas semanais por modo ("10 questões de
Oráculo, 10 de Laboratório"). O que está aqui é a regra; quem lê o banco é
`services/metas_service.py`, e as telas só desenham.

Por que a unidade muda de um modo para outro
--------------------------------------------
Oráculo, Treino e Laboratório entregam UMA questão por vez -- contar questões
é natural. Escape Room (6 salas), Batalha (4 chefes, 3 vidas) e RPG (15 fases)
são PARTIDAS. Se a meta contasse questões neles, bastaria abrir dez Escape
Rooms, responder a primeira sala de cada e ir embora: a cota fecharia sem
ninguém terminar nada. Por isso esses três contam partida CONCLUÍDA, que é o
que `repositories/conclusao_repo.py` grava no fim de cada corrida.

E são uma meta só, à escolha do aluno, não três. Esses modos são o que segura
o aluno no app; exigir os três toda semana transforma em dever de casa
justamente a parte que ele faz por vontade própria.

De onde saíram os números
-------------------------
Medidos nos 554 registros reais de `logs_pedagogicos` (28/09/2026), mediana do
tempo de resposta por modo: Oráculo 19,7 s, Laboratório 20,1 s (mas o quartil
superior é 55,4 s -- é o modo mais lento, por isso 5 e não 10), Escape Room
20,3 s, Batalha 17,6 s, RPG 15,0 s. Com os alvos abaixo, a semana fica entre
15 e 25 minutos somando a espera da geração.

**Esses números descrevem os MODOS, não ainda o ALUNO**: a maior parte do
corpus veio de sessões de teste, não de uma turma. Depois de duas semanas de
uso real vale recalcular e ajustar os alvos aqui -- é uma linha por meta.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple


class Meta(NamedTuple):
    chave: str
    label: str
    alvo: int
    unidade: str  # "questoes" ou "partidas"
    modos: tuple[str, ...]
    ajuda: str


METAS: tuple[Meta, ...] = (
    Meta(
        chave="conceito",
        label="Oráculo ou Treino Rápido",
        alvo=10,
        unidade="questoes",
        modos=("oraculo", "treino"),
        ajuda="Questões de conceito, em qualquer matéria.",
    ),
    Meta(
        chave="calculo",
        label="Laboratório de Exatas",
        alvo=5,
        unidade="questoes",
        modos=("laboratorio",),
        ajuda="Desafios de conta. São mais demorados que os de conceito.",
    ),
    Meta(
        chave="jornada",
        label="Uma jornada completa",
        alvo=1,
        unidade="partidas",
        modos=("escape_room", "boss_rush", "rpg"),
        ajuda="Escape Room, Batalha contra Chefes ou uma aventura de RPG — você escolhe qual.",
    ),
)

# O ENEM não aparece em `modos` acima de propósito, e é só por isso que ele
# fica fora da conta: é simulado, cansa e imita a prova. A recomendação à
# coordenação foi uma vez por quinzena, ou antes de prova -- uma cadência que
# não é semanal e não cabe nesta tela. (Houve aqui uma constante
# `MODOS_FORA_DA_META` listando o ENEM; ninguém a lia, então virou este
# comentário -- a regra sempre esteve na tabela de metas.)

# Resposta mais rápida que isto não conta. Meta por quantidade é exatamente o
# incentivo para clicar sem ler, e o log já traz o tempo. Medido antes de
# escolher o valor: das 554 respostas reais, NENHUMA saiu abaixo de 5 s (a
# mais rápida levou 6,5 s, e a mediana é 20,1 s) -- então hoje este piso não
# tira ninguém, e passa a existir para o dia em que a meta mudar o
# comportamento.
SEGUNDOS_MINIMOS_DE_RESPOSTA = 5.0

# Brasil não tem horário de verão desde 2019, então o deslocamento é fixo. Um
# ZoneInfo("America/Sao_Paulo") dependeria da base de fusos estar instalada no
# contêiner do Render, e a falha apareceria só na virada da semana.
FUSO_ESCOLAR = timezone(timedelta(hours=-3))


def normalizar_modo(valor: Any) -> str:
    """"escape_room-flask" -> "escape_room"; "boss_rush_enem" -> "boss_rush".

    O log grava o modo com o frontend no nome. Sem tirar esse sufixo, o dia em
    que alguém abrir o Streamlit o aluno começaria a semana do zero.
    """
    texto = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"-(?:flask|streamlit|st)$", "", texto)
    if texto.startswith("boss_rush"):
        return "boss_rush"
    return texto


def inicio_da_semana(agora: datetime | None = None) -> datetime:
    """Segunda-feira, 00:00 no horário de Brasília, devolvida em UTC."""
    momento = (agora or datetime.now(timezone.utc)).astimezone(FUSO_ESCOLAR)
    segunda = (momento - timedelta(days=momento.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return segunda.astimezone(timezone.utc)


def _quando(valor: Any) -> datetime | None:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        lido = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return lido if lido.tzinfo else lido.replace(tzinfo=timezone.utc)


def _desta_semana(registro: dict, campo: str, desde: datetime) -> bool:
    momento = _quando(registro.get(campo))
    return momento is not None and momento >= desde


def resposta_conta(log: dict) -> bool:
    """Respondeu de verdade? Tempo ausente conta -- só o rápido demais não."""
    bruto = log.get("tempo_resposta")
    if bruto in (None, ""):
        return True
    try:
        return float(bruto) >= SEGUNDOS_MINIMOS_DE_RESPOSTA
    except (TypeError, ValueError):
        return True


def progresso_semanal(
    logs: list[dict] | None,
    conclusoes: list[dict] | None,
    agora: datetime | None = None,
) -> dict:
    """Quanto o aluno já fez desta semana, meta a meta."""
    desde = inicio_da_semana(agora)

    questoes: dict[str, int] = {}
    for log in logs or []:
        if not _desta_semana(log, "data_hora", desde) or not resposta_conta(log):
            continue
        modo = normalizar_modo(log.get("modo"))
        questoes[modo] = questoes.get(modo, 0) + 1

    partidas: dict[str, int] = {}
    for conclusao in conclusoes or []:
        if not _desta_semana(conclusao, "concluido_em", desde):
            continue
        modo = normalizar_modo(conclusao.get("modo"))
        partidas[modo] = partidas.get(modo, 0) + 1

    itens = []
    for meta in METAS:
        contagem = questoes if meta.unidade == "questoes" else partidas
        feito = sum(contagem.get(modo, 0) for modo in meta.modos)
        itens.append(
            {
                "chave": meta.chave,
                "label": meta.label,
                "ajuda": meta.ajuda,
                "unidade": meta.unidade,
                "alvo": meta.alvo,
                "feito": feito,
                "faltam": max(0, meta.alvo - feito),
                "cumprida": feito >= meta.alvo,
                # A barra para na meta: 18 de 10 desenha 100%, não 180%.
                "percentual": min(100, int(feito * 100 / meta.alvo)) if meta.alvo else 0,
            }
        )

    return {
        "desde": desde,
        "itens": itens,
        "cumpridas": sum(1 for item in itens if item["cumprida"]),
        "total": len(itens),
        "tudo_feito": all(item["cumprida"] for item in itens) if itens else False,
    }
