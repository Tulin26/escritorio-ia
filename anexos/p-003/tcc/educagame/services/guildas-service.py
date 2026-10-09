from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def guilda_de_aluno(aluno: dict) -> str:
    serie = str(aluno.get("ano_escolar", "") or "Série não informada").strip()
    periodo = str(aluno.get("periodo", "") or "Período não informado").strip()
    return f"{serie} - {periodo}"


def inicio_semana() -> datetime:
    hoje = datetime.now(FUSO_BRASILIA)
    inicio = hoje - timedelta(days=hoje.weekday())
    return inicio.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


def parse_data(valor) -> datetime | None:
    if not valor:
        return None
    texto = str(valor).replace("Z", "+00:00")
    try:
        data = datetime.fromisoformat(texto)
        if data.tzinfo is not None:
            data = data.astimezone(FUSO_BRASILIA)
        return data.replace(tzinfo=None)
    except Exception:
        return None


def montar_guildas(alunos: list[dict], logs: list[dict]) -> list[dict]:
    alunos_por_id = {str(aluno.get("id")): aluno for aluno in alunos or []}
    guildas: dict[str, dict] = {}

    for aluno in alunos or []:
        nome = guilda_de_aluno(aluno)
        item = guildas.setdefault(
            nome,
            {
                "guilda": nome,
                "pontos_totais": 0,
                "alunos": 0,
                "questoes_semana": 0,
                "acertos_semana": 0,
                "erros_semana": 0,
                "participantes_semana": set(),
            },
        )
        item["pontos_totais"] += int(aluno.get("pontos_totais") or 0)
        item["alunos"] += 1

    inicio = inicio_semana()
    for log in logs or []:
        aluno = alunos_por_id.get(str(log.get("aluno_id")))
        if not aluno:
            continue
        data = parse_data(log.get("data_hora") or log.get("created_at"))
        if data is not None and data < inicio:
            continue
        guilda = guilda_de_aluno(aluno)
        item = guildas.setdefault(
            guilda,
            {
                "guilda": guilda,
                "pontos_totais": 0,
                "alunos": 0,
                "questoes_semana": 0,
                "acertos_semana": 0,
                "erros_semana": 0,
                "participantes_semana": set(),
            },
        )
        item["questoes_semana"] += 1
        item["participantes_semana"].add(str(log.get("aluno_id")))
        if str(log.get("resultado", "")).lower() == "acertou":
            item["acertos_semana"] += 1
        else:
            item["erros_semana"] += 1

    resultado = []
    for item in guildas.values():
        participantes = len(item["participantes_semana"])
        bonus_participacao = participantes * 5
        penalidade = item["erros_semana"]
        pontos_semana = item["acertos_semana"] * 10 + bonus_participacao - penalidade
        total_semana = item["questoes_semana"]
        taxa = int((item["acertos_semana"] / total_semana) * 100) if total_semana else 0
        resultado.append(
            {
                **item,
                "participantes_semana": participantes,
                "bonus_participacao": bonus_participacao,
                "penalidade": penalidade,
                "pontos_semana": max(0, pontos_semana),
                "taxa_acerto": taxa,
            }
        )

    resultado.sort(key=lambda guilda: (guilda["pontos_semana"], guilda["pontos_totais"]), reverse=True)
    return resultado
