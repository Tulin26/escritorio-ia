from __future__ import annotations

from collections import defaultdict

from flask import Blueprint, redirect, render_template, request, session, url_for

from web.routes.flask_helpers_fla import (
    aluno_travado_id,
    calcular_percentual,
    contexto_aluno_template,
)
from services.dados_service import buscar_aluno_por_id, buscar_alunos, buscar_logs
from services.gamification_service import BADGES, calcular_badges, streak_acertos

perfil_bp = Blueprint("perfil", __name__)


def _materia_log(log: dict) -> str:
    materia = str(log.get("materia") or "Geral")
    for prefixo in ("ENEM-", "LAB-", "RPG-"):
        if materia.upper().startswith(prefixo):
            return materia[len(prefixo):] or "Geral"
    return materia


def _montar_materias(logs: list[dict]) -> list[dict]:
    dados = defaultdict(lambda: {"total": 0, "acertos": 0})
    for log in logs:
        materia = _materia_log(log)
        dados[materia]["total"] += 1
        if log.get("resultado") == "Acertou":
            dados[materia]["acertos"] += 1

    materias = []
    for nome, stats in dados.items():
        materias.append(
            {
                "nome": nome,
                "total": stats["total"],
                "acertos": stats["acertos"],
                "percentual": calcular_percentual(stats["acertos"], stats["total"]),
            }
        )
    return sorted(materias, key=lambda item: (-item["total"], item["nome"]))


def _montar_perfil(aluno: dict, logs: list[dict]) -> dict:
    total = len(logs)
    acertos = sum(1 for log in logs if log.get("resultado") == "Acertou")
    badges = calcular_badges(logs, aluno)
    badges_ids = {badge.get("id") for badge in badges}
    return {
        "aluno": aluno,
        "total": total,
        "acertos": acertos,
        "erros": total - acertos,
        "percentual": calcular_percentual(acertos, total),
        "streak": streak_acertos(logs),
        "pontos": int(aluno.get("pontos_totais") or 0),
        "badges": BADGES,
        "badges_ids": badges_ids,
        "badges_total": len(badges),
        "materias": _montar_materias(logs),
        "recentes": logs[:8],
    }


@perfil_bp.route("/")
def tela_perfil():
    escola_id = session.get("escola_id")

    # "?aluno_id=<outro>" trocava a sessao para outro aluno, e "?trocar"
    # soltava a sessao do aluno -- os dois davam acesso ao perfil e ao
    # desempenho de um colega. Quem entrou como aluno fica na propria conta.
    travado = aluno_travado_id()

    if request.args.get("trocar") and not travado:
        session.pop("aluno_id", None)
        session.pop("aluno_nome", None)
        session.pop("ano_escolar", None)
        return redirect(url_for("perfil.tela_perfil"))

    aluno_id = travado or request.args.get("aluno_id") or session.get("aluno_id")

    if request.args.get("aluno_id") and not travado:
        aluno = buscar_aluno_por_id(str(aluno_id))
        if aluno:
            session["aluno_id"] = aluno.get("id") or aluno_id
            session["aluno_nome"] = aluno.get("nome", "")
            session["ano_escolar"] = aluno.get("ano_escolar", "")
        return redirect(url_for("perfil.tela_perfil"))

    alunos = buscar_alunos(escola_id) if escola_id and not aluno_id else []
    aluno = buscar_aluno_por_id(str(aluno_id)) if aluno_id else None
    logs = buscar_logs(escola_id, str(aluno_id)) if escola_id and aluno_id else []

    return render_template(
        "perfil.html",
        alunos=alunos,
        perfil=_montar_perfil(aluno, logs) if aluno else None,
        **contexto_aluno_template(),
    )


