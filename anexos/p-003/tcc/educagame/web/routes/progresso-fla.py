from __future__ import annotations

from collections import defaultdict

from flask import Blueprint, redirect, render_template, request, session, url_for

from core.config import materia_base
from web.routes.flask_helpers_fla import (
    aluno_travado_id,
    calcular_percentual,
    contexto_aluno_template,
    exibir_modo,
)
from services.dados_service import buscar_aluno_por_id, buscar_alunos, buscar_logs, buscar_ranking
from services.escola_service import escola_atualizada, mostra_ranking
from services.metas_service import meta_do_aluno

progresso_bp = Blueprint("progresso", __name__)


def _montar_progresso(logs: list[dict]) -> dict:
    total = len(logs)
    acertos = sum(1 for log in logs if log.get("resultado") == "Acertou")
    por_materia = defaultdict(lambda: {"total": 0, "acertos": 0})
    por_modo = defaultdict(lambda: {"total": 0, "acertos": 0})

    for log in logs:
        materia = materia_base(log.get("materia") or "Geral")
        modo = exibir_modo(log.get("modo")) or "Oráculo"
        por_materia[materia]["total"] += 1
        por_modo[modo]["total"] += 1
        if log.get("resultado") == "Acertou":
            por_materia[materia]["acertos"] += 1
            por_modo[modo]["acertos"] += 1

    def itens(dados):
        lista = []
        for nome, stats in dados.items():
            lista.append(
                {
                    "nome": nome,
                    "total": stats["total"],
                    "acertos": stats["acertos"],
                    "percentual": calcular_percentual(stats["acertos"], stats["total"]),
                }
            )
        return sorted(lista, key=lambda item: (-item["total"], item["nome"]))

    return {
        "total": total,
        "acertos": acertos,
        "erros": total - acertos,
        "percentual": calcular_percentual(acertos, total),
        "materias": itens(por_materia),
        "modos": itens(por_modo),
        "recentes": logs[:10],
    }


@progresso_bp.route("/", methods=["GET", "POST"])
def tela_progresso():
    escola_id = session.get("escola_id")

    # O POST trocava a sessao para o aluno_id enviado -- so conferia a
    # escola, nao quem estava logado. Um aluno via o historico do colega.
    travado = aluno_travado_id()

    if request.method == "POST":
        aluno_id_form = travado or request.form.get("aluno_id", "")
        aluno = buscar_aluno_por_id(aluno_id_form) if aluno_id_form else None
        if aluno and str(aluno.get("escola_id")) == str(escola_id):
            session["aluno_id"] = aluno.get("id") or aluno_id_form
            session["aluno_nome"] = aluno.get("nome", "")
            session["ano_escolar"] = aluno.get("ano_escolar", "")
        return redirect(url_for("progresso.tela_progresso"))

    aluno_id = travado or session.get("aluno_id")
    logs = buscar_logs(escola_id, aluno_id) if escola_id and aluno_id else []

    # MELHORIA: o "Ranking da escola" saia sempre, mesmo com a escola tendo
    # desligado mostrar_ranking no painel (RF14). Com a opcao desligada o
    # ranking nem e consultado: o que nao vai ao template nao tem como vazar
    # para a tela. Os pontos do aluno continuam sendo somados pelo banco.
    exibir_ranking = mostra_ranking(escola_atualizada(escola_id))
    ranking = buscar_ranking(escola_id, limite=10) if escola_id and exibir_ranking else []
    alunos = buscar_alunos(escola_id) if escola_id else []
    if travado:
        alunos = [a for a in alunos if str(a.get("id")) == travado]

    return render_template(
        "progresso.html",
        # A meta usa os MESMOS logs que o resto da tela: nenhuma consulta
        # nova ao banco por causa dela (só as partidas concluídas da semana).
        meta=meta_do_aluno(aluno_id, logs),
        progresso=_montar_progresso(logs),
        ranking=ranking,
        mostrar_ranking=exibir_ranking,
        alunos=alunos,
        **contexto_aluno_template(),
    )


