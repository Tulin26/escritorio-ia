from __future__ import annotations

import time

from flask import Blueprint, redirect, render_template, request, session, url_for

from core.config import MATERIAS, exibir_materia, filtrar_materias_por_serie, normalizar_materia
from web.routes.flask_helpers_fla import (
    AVISO_QUESTAO_TROCADA,
    alunos_para_selecao,
    assinatura_da_questao,
    aviso_offline,
    contexto_aluno_template,
    formatar_pergunta_exatas,
    formatar_texto_simples_pergunta,
    latex,
    limpar_estado_flask,
    materias_para_template,
    obter_estado_flask,
    registrar_pontuacao_acerto,
    resposta_veio_de_outra_questao,
    salvar_estado_flask,
    sincronizar_aluno_da_requisicao,
    tempo_resposta,
    texto_explicacao,
)
from services.dados_service import registrar_log_com_tempo
from services.banks.em import gerar_questao_offline_em
from services.ia_service import invocar_enigma, obter_ultimo_erro_ia
from services.pedagogical_feedback import gerar_feedback_pedagogico

treino_bp = Blueprint("treino", __name__)

MATERIAS_EXATAS = {"Matematica", "Fisica", "Quimica"}


def _preparar_questao_para_template(questao: dict | None, materia: str = "") -> dict:
    if not isinstance(questao, dict):
        return {}

    preparado = dict(questao)
    materia_norm = normalizar_materia(materia or preparado.get("materia", ""))
    preparado["materia"] = materia_norm or preparado.get("materia", "")
    preparado["materia_label"] = exibir_materia(preparado.get("materia", ""))
    preparado["formula_latex"] = latex(preparado.get("formula", ""))
    preparado["subformulas_latex"] = [latex(item) for item in preparado.get("subformulas", []) or [] if str(item).strip()]
    preparado["explicacao_texto"] = texto_explicacao(preparado.get("explicacao"))

    pergunta = str(preparado.get("pergunta", "") or "")
    if materia_norm in MATERIAS_EXATAS:
        preparado["pergunta_formatada"] = formatar_pergunta_exatas(pergunta)
    else:
        preparado["pergunta_formatada"] = {
            "texto": formatar_texto_simples_pergunta(pergunta),
            "latex": "",
            "sufixo": "",
        }

    return preparado


def _gerar_questao_treino(
    materia: str,
    ano_escolar: str,
    nivel: str,
    tema: str,
    evitar_ids: list[str] | None = None,
) -> dict:
    questao = invocar_enigma(materia, ano_escolar, nivel, tema) or {}
    if questao.get("_origem_geracao") == "offline" and questao.get("id_offline") in set(evitar_ids or []):
        questao = gerar_questao_offline_em(materia, tema, nivel, evitar_ids=evitar_ids)
    questao["materia"] = materia
    questao["materia_label"] = exibir_materia(materia)
    questao["ano_escolar"] = ano_escolar
    questao["nivel"] = nivel
    questao["tema"] = tema
    return questao


@treino_bp.route("/", methods=["GET"])
def tela_treino():
    treino = obter_estado_flask("treino_flask", {}) or {}
    questao = _preparar_questao_para_template(treino.get("questao"), treino.get("materia", ""))
    erro_ia = aviso_offline(questao, "questao", treino.get("aviso_ia", ""))

    return render_template(
        "treino.html",
        materias=materias_para_template(MATERIAS),
        alunos=alunos_para_selecao(),
        treino=treino,
        questao=questao,
        assinatura_questao=assinatura_da_questao(treino.get("questao")),
        aviso_resposta=AVISO_QUESTAO_TROCADA if request.args.get("aviso") == "questao_trocada" else "",
        resultado=treino.get("resultado"),
        erro_ia=erro_ia,
        **contexto_aluno_template(),
    )


@treino_bp.route("/iniciar", methods=["POST"])
def iniciar_treino():
    sincronizar_aluno_da_requisicao()
    materia = normalizar_materia(request.form.get("materia") or "Matematica")
    nivel = request.form.get("nivel") or "Medio"
    tema = request.form.get("tema") or ""
    total = int(request.form.get("total") or 5)
    if total not in {3, 5, 7, 10}:
        total = 5
    ano_escolar = session.get("ano_escolar") or "1º EM"
    if materia not in filtrar_materias_por_serie(MATERIAS, ano_escolar):
        materia = "Matematica"

    questao = _gerar_questao_treino(materia, ano_escolar, nivel, tema)
    salvar_estado_flask("treino_flask", {
        "materia": materia,
        "materia_label": exibir_materia(materia),
        "nivel": nivel,
        "tema": tema,
        "total": total,
        "atual": 1,
        "acertos": 0,
        "erros": 0,
        "historico": [],
        "questao": questao,
        "resultado": None,
        "aviso_ia": obter_ultimo_erro_ia(),
        "tempo_inicio": time.time(),
    })
    return redirect(url_for("treino.tela_treino"))


@treino_bp.route("/responder", methods=["POST"])
def responder_treino():
    treino = obter_estado_flask("treino_flask", {}) or {}
    questao = treino.get("questao") or {}
    if not treino or not questao:
        return redirect(url_for("treino.tela_treino"))

    # A questao guardada pode ter trocado entre o desenho da tela e este
    # envio (pagina velha, botao voltar, duas abas). Pontuar o indice
    # contra a questao NOVA e o achado 3.4 do QA de 23/09/2026: o aluno
    # perdia ponto tendo acertado. Nao conta nem acerto nem erro.
    if resposta_veio_de_outra_questao(treino.get("questao")):
        return redirect(url_for("treino.tela_treino", aviso="questao_trocada"))

    try:
        resposta_idx = int(request.form.get("resposta", "-1"))
    except ValueError:
        resposta_idx = -1

    opcoes = questao.get("opcoes") or []
    correta_idx = int(questao.get("correta", -1))
    acertou = resposta_idx == correta_idx
    resposta_aluno = opcoes[resposta_idx] if 0 <= resposta_idx < len(opcoes) else "Sem resposta"
    resposta_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""

    pontos = 0
    if session.get("aluno_id") and session.get("escola_id"):
        registrar_log_com_tempo(
            {
                "aluno_id": session.get("aluno_id"),
                "escola_id": session.get("escola_id"),
                "materia": treino.get("materia", "Geral"),
                "modo": "treino-flask",
                "resultado": "Acertou" if acertou else "Errou",
                "pergunta_texto": questao.get("pergunta", ""),
                "resposta_aluno": resposta_aluno,
                "resposta_correta": resposta_correta,
                # as alternativas vao para o log porque sem elas nao ha como
                # medir, contra dado real, se a explicacao contradiz o
                # gabarito (ver 20260910120000_logs_opcoes.sql)
                "opcoes": opcoes,
                "explicacao_ia": str(questao.get("explicacao", "")),
                "area_bncc": questao.get("area_bncc"),
                "competencia_bncc": questao.get("competencia_bncc"),
                "habilidade_bncc": questao.get("habilidade_bncc"),
                "codigo_bncc": questao.get("codigo_bncc"),
                "dificuldade": questao.get("nivel") or treino.get("nivel"),
            },
            tempo_resposta(treino),
        )
        pontos = registrar_pontuacao_acerto(session.get("aluno_id"), acertou, questao.get("nivel") or treino.get("nivel", "Medio"))

    historico = list(treino.get("historico", []))
    historico.append(
        {
            "numero": treino.get("atual", 1),
            "pergunta": questao.get("pergunta", ""),
            "resposta_aluno": resposta_aluno,
            "resposta_correta": resposta_correta,
            "acertou": acertou,
            "id_offline": questao.get("id_offline", ""),
        }
    )

    treino["historico"] = historico
    treino["acertos"] = int(treino.get("acertos", 0)) + (1 if acertou else 0)
    treino["erros"] = int(treino.get("erros", 0)) + (0 if acertou else 1)
    treino["resultado"] = {
        "acertou": acertou,
        "resposta_aluno": resposta_aluno,
        "resposta_correta": resposta_correta,
        "pontos": pontos,
        "feedback": None if acertou else gerar_feedback_pedagogico(
            dados=questao,
            materia=treino.get("materia", "Geral"),
            resposta_aluno=resposta_aluno,
            resposta_correta=resposta_correta,
        ),
    }
    salvar_estado_flask("treino_flask", treino)
    return redirect(url_for("treino.tela_treino"))


@treino_bp.route("/proxima", methods=["POST"])
def proxima_questao():
    treino = obter_estado_flask("treino_flask", {}) or {}
    if not treino:
        return redirect(url_for("treino.tela_treino"))

    atual = int(treino.get("atual", 1))
    total = int(treino.get("total", 1))
    if atual >= total:
        return redirect(url_for("treino.tela_treino"))

    questao = _gerar_questao_treino(
        treino.get("materia", "Matematica"),
        session.get("ano_escolar") or "1º EM",
        treino.get("nivel", "Medio"),
        treino.get("tema", ""),
        [str(item.get("id_offline", "")) for item in treino.get("historico", [])],
    )
    treino["atual"] = atual + 1
    treino["questao"] = questao
    treino["resultado"] = None
    treino["aviso_ia"] = obter_ultimo_erro_ia()
    treino["tempo_inicio"] = time.time()
    salvar_estado_flask("treino_flask", treino)
    return redirect(url_for("treino.tela_treino"))


@treino_bp.route("/reiniciar", methods=["POST"])
def reiniciar_treino():
    limpar_estado_flask("treino_flask")
    return redirect(url_for("treino.tela_treino"))

