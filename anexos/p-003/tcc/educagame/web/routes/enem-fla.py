from __future__ import annotations

import time
from collections import defaultdict

from flask import Blueprint, redirect, render_template, request, session, url_for

from web.routes.flask_helpers_fla import (
    AVISO_QUESTAO_TROCADA,
    alunos_para_selecao,
    assinatura_da_questao,
    aviso_offline,
    carregar_estado_persistido,
    contexto_aluno_template,
    limpar_estado_persistido,
    nome_estado_por_aluno,
    registrar_pontuacao_acerto,
    resposta_veio_de_outra_questao,
    salvar_estado_persistido,
    sincronizar_aluno_da_requisicao,
    tempo_resposta,
    texto_explicacao,
)
from services.dados_service import registrar_log_com_tempo
from services.enem_service import AREAS_ENEM, DIFICULDADES, LABEL_AREA, gerar_questao_enem, montar_sequencia_questoes
from services.pedagogical_feedback import gerar_feedback_pedagogico

enem_bp = Blueprint("enem", __name__)
ENEM_PROGRESSO_ID = "enem_flask"


def _estado_enem() -> str:
    return nome_estado_por_aluno(ENEM_PROGRESSO_ID)


def _areas_para_template() -> list[dict[str, str]]:
    return [{"valor": area, "label": LABEL_AREA.get(area, area)} for area in AREAS_ENEM]


def _questao_para_template(questao: dict | None) -> dict:
    if not isinstance(questao, dict):
        return {}
    dados = dict(questao)
    dados["area_label"] = LABEL_AREA.get(dados.get("area_bncc", ""), dados.get("area_bncc", ""))
    from web.routes.flask_helpers_fla import explicacao_sem_frase_generica, passos_para_template

    dados["passos_texto"] = passos_para_template(dados.get("passos_resolucao"))
    dados["explicacao_texto"] = texto_explicacao(explicacao_sem_frase_generica(dados))
    # MELHORIA: a pilula mostrava "offline" em ingles, numa interface toda em
    # portugues (relatorio de QA de 23/09/2026, secao 5.3/6).
    dados["origem_label"] = "Banco" if dados.get("_origem") == "offline" else "IA"
    return dados


def _gerar_atual(simulado: dict) -> dict:
    idx = int(simulado.get("idx", 0))
    sequencia = simulado.get("sequencia") or []
    if not sequencia:
        return {}
    area, dificuldade = sequencia[idx]
    questao = gerar_questao_enem(area, dificuldade) or {}
    simulado["questao"] = questao
    simulado["resultado"] = None
    simulado["tempo_inicio"] = time.time()
    salvar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, simulado)
    return questao


def _resumo_simulado(historico: list[dict]) -> dict:
    total = len(historico)
    acertos = sum(1 for item in historico if item.get("acertou"))
    por_area = defaultdict(lambda: {"total": 0, "acertos": 0})
    for item in historico:
        area = item.get("area_label") or item.get("area") or "Area"
        por_area[area]["total"] += 1
        if item.get("acertou"):
            por_area[area]["acertos"] += 1

    areas = []
    for area, stats in por_area.items():
        total_area = stats["total"]
        acertos_area = stats["acertos"]
        areas.append(
            {
                "area": area,
                "total": total_area,
                "acertos": acertos_area,
                "percentual": int(acertos_area / total_area * 100) if total_area else 0,
            }
        )

    return {
        "total": total,
        "acertos": acertos,
        "erros": total - acertos,
        "percentual": int(acertos / total * 100) if total else 0,
        "areas": areas,
        "erradas": [item for item in historico if not item.get("acertou")],
    }


@enem_bp.route("/", methods=["GET"])
def tela_enem():
    simulado = carregar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, {}) or {}
    if simulado and not simulado.get("questao") and simulado.get("fase") == "quiz":
        _gerar_atual(simulado)
        simulado = carregar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, {}) or {}

    questao = _questao_para_template(simulado.get("questao"))
    resumo = _resumo_simulado(simulado.get("historico", [])) if simulado.get("fase") == "resultado" else {}

    return render_template(
        "enem.html",
        areas=_areas_para_template(),
        dificuldades=DIFICULDADES,
        alunos=alunos_para_selecao(),
        simulado=simulado,
        questao=questao,
        assinatura_questao=assinatura_da_questao(simulado.get("questao")),
        aviso_resposta=AVISO_QUESTAO_TROCADA if request.args.get("aviso") == "questao_trocada" else "",
        resultado=simulado.get("resultado"),
        resumo=resumo,
        # MELHORIA: aqui a origem aparecia como uma PILULA escrita "offline"
        # ao lado da questao. Isso e rotulo, nao explicacao: o aluno lia uma
        # palavra tecnica e nao ficava sabendo nem por que, nem se a questao
        # valia. A pilula continua (serve ao professor que olha por cima do
        # ombro); o aviso explica.
        erro_ia=aviso_offline(questao),
        **contexto_aluno_template(),
    )


@enem_bp.route("/iniciar", methods=["POST"])
def iniciar_enem():
    sincronizar_aluno_da_requisicao()
    areas = request.form.getlist("areas") or list(AREAS_ENEM.keys())
    areas = [area for area in areas if area in AREAS_ENEM] or list(AREAS_ENEM.keys())
    dificuldade = request.form.get("dificuldade") or "Medio"
    if dificuldade not in DIFICULDADES:
        dificuldade = "Medio"
    total = int(request.form.get("total") or 10)
    if total not in {5, 10, 15, 20, 30}:
        total = 10

    sequencia = montar_sequencia_questoes(areas, total, dificuldade)
    salvar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, {
        "fase": "quiz",
        "sequencia": sequencia,
        "idx": 0,
        "total": total,
        "historico": [],
        "questao": None,
        "resultado": None,
        "tempo_inicio": None,
    })
    return redirect(url_for("enem.tela_enem"))


@enem_bp.route("/responder", methods=["POST"])
def responder_enem():
    simulado = carregar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, {}) or {}
    questao = simulado.get("questao") or {}
    if not simulado or not questao:
        return redirect(url_for("enem.tela_enem"))

    # A questao guardada pode ter trocado entre o desenho da tela e este
    # envio (pagina velha, botao voltar, duas abas). Pontuar o indice
    # contra a questao NOVA e o achado 3.4 do QA de 23/09/2026: o aluno
    # perdia ponto tendo acertado. Nao conta nem acerto nem erro.
    if resposta_veio_de_outra_questao(simulado.get("questao")):
        return redirect(url_for("enem.tela_enem", aviso="questao_trocada"))

    alternativas = questao.get("alternativas") or []
    resposta_idx = int(request.form.get("resposta", "-1"))
    resposta_aluno = alternativas[resposta_idx] if 0 <= resposta_idx < len(alternativas) else "Sem resposta"
    resposta_correta = str(questao.get("correta", ""))
    acertou = resposta_aluno == resposta_correta
    tempo = tempo_resposta(simulado)

    pontos = 0
    if session.get("aluno_id") and session.get("escola_id"):
        registrar_log_com_tempo(
            {
                "aluno_id": session.get("aluno_id"),
                "escola_id": session.get("escola_id"),
                "materia": f"ENEM-{questao.get('area_bncc', '')}",
                "modo": "enem-flask",
                "resultado": "Acertou" if acertou else "Errou",
                "pergunta_texto": questao.get("pergunta", ""),
                "resposta_aluno": resposta_aluno,
                "resposta_correta": resposta_correta,
                # as alternativas vao para o log porque sem elas nao ha como
                # medir, contra dado real, se a explicacao contradiz o
                # gabarito (ver 20260910120000_logs_opcoes.sql)
                "opcoes": alternativas,
                "explicacao_ia": str(questao.get("explicacao", "")),
                "area_bncc": questao.get("area_bncc", ""),
                "competencia_bncc": questao.get("competencia_bncc", ""),
                "habilidade_bncc": questao.get("habilidade_bncc", ""),
                "codigo_bncc": questao.get("codigo_bncc", ""),
                "matriz_enem": questao.get("matriz_enem", ""),
                "dificuldade": questao.get("dificuldade", ""),
            },
            tempo,
        )
        pontos = registrar_pontuacao_acerto(session.get("aluno_id"), acertou, questao.get("dificuldade", "Medio"))

    area_label = LABEL_AREA.get(questao.get("area_bncc", ""), questao.get("area_bncc", ""))
    historico = list(simulado.get("historico", []))
    historico.append(
        {
            "numero": int(simulado.get("idx", 0)) + 1,
            "area": questao.get("area_bncc", ""),
            "area_label": area_label,
            "dificuldade": questao.get("dificuldade", ""),
            "matriz_enem": questao.get("matriz_enem", ""),
            "pergunta": questao.get("pergunta", ""),
            "resposta_aluno": resposta_aluno,
            "resposta_correta": resposta_correta,
            "acertou": acertou,
            "tempo": tempo or 0,
        }
    )
    simulado["historico"] = historico
    simulado["resultado"] = {
        "acertou": acertou,
        "resposta_aluno": resposta_aluno,
        "resposta_correta": resposta_correta,
        "pontos": pontos,
        "feedback": None if acertou else gerar_feedback_pedagogico(
            dados=questao,
            materia=questao.get("materia") or questao.get("area_bncc", "ENEM"),
            resposta_aluno=resposta_aluno,
            resposta_correta=resposta_correta,
        ),
    }
    salvar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, simulado)
    return redirect(url_for("enem.tela_enem"))


@enem_bp.route("/proxima", methods=["POST"])
def proxima_enem():
    simulado = carregar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, {}) or {}
    if not simulado:
        return redirect(url_for("enem.tela_enem"))

    idx = int(simulado.get("idx", 0))
    total = int(simulado.get("total", 0))
    if idx + 1 >= total:
        simulado["fase"] = "resultado"
        simulado["questao"] = None
        simulado["resultado"] = None
        salvar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, simulado)
        return redirect(url_for("enem.tela_enem"))

    simulado["idx"] = idx + 1
    simulado["questao"] = None
    simulado["resultado"] = None
    salvar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID, simulado)
    return redirect(url_for("enem.tela_enem"))


@enem_bp.route("/reiniciar", methods=["POST"])
def reiniciar_enem():
    limpar_estado_persistido(_estado_enem(), ENEM_PROGRESSO_ID)
    return redirect(url_for("enem.tela_enem"))


