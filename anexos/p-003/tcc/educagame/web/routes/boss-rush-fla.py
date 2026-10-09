from __future__ import annotations

import time

from flask import Blueprint, redirect, render_template, request, session, url_for

from web.routes.flask_helpers_fla import (
    alunos_para_selecao,
    assinatura_da_questao,
    aviso_offline,
    AVISO_QUESTAO_TROCADA,
    carregar_estado_persistido,
    contexto_aluno_template,
    limpar_estado_persistido,
    nome_estado_por_aluno,
    registrar_partida_concluida,
    registrar_pontuacao_acerto,
    resposta_veio_de_outra_questao,
    resumo_historico,
    salvar_estado_persistido,
    sincronizar_aluno_da_requisicao,
    tempo_resposta,
    texto_explicacao,
)
from services.dados_service import registrar_log_com_tempo
from services.enem_service import AREAS_ENEM, DIFICULDADES, LABEL_AREA, gerar_questao_enem
from services.pedagogical_feedback import gerar_feedback_pedagogico

boss_rush_bp = Blueprint("boss_rush", __name__)
BOSS_RUSH_PROGRESSO_ID = "boss_rush_flask"


def _estado_boss_rush() -> str:
    return nome_estado_por_aluno(BOSS_RUSH_PROGRESSO_ID)


def _bosses(dificuldade: str) -> list[dict[str, str]]:
    nomes = {
        "Linguagens e suas Tecnologias": "Guardião das Linguagens",
        "Matematica e suas Tecnologias": "Titã da Matemática",
        "Ciencias da Natureza e suas Tecnologias": "Núcleo da Natureza",
        "Ciencias Humanas e Sociais Aplicadas": "Sentinela das Humanas",
    }
    return [{"area": area, "nome": nomes.get(area, LABEL_AREA.get(area, area)), "dificuldade": dificuldade} for area in AREAS_ENEM]


def _questao_template(questao: dict | None) -> dict:
    if not isinstance(questao, dict):
        return {}
    dados = dict(questao)
    dados["area_label"] = LABEL_AREA.get(dados.get("area_bncc", ""), dados.get("area_bncc", ""))
    from web.routes.flask_helpers_fla import explicacao_sem_frase_generica, passos_para_template

    dados["passos_texto"] = passos_para_template(dados.get("passos_resolucao"))
    dados["explicacao_texto"] = texto_explicacao(explicacao_sem_frase_generica(dados))
    dados["origem_label"] = "offline" if dados.get("_origem") == "offline" else "IA"
    return dados


def _carregar_questao(estado: dict) -> dict:
    idx = int(estado.get("idx", 0))
    bosses = estado.get("bosses") or []
    if not bosses:
        return {}
    boss = bosses[idx]
    questao = gerar_questao_enem(boss["area"], boss["dificuldade"]) or {}
    estado["questao"] = questao
    estado["resultado"] = None
    estado["tempo_inicio"] = time.time()
    salvar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, estado)
    return questao

@boss_rush_bp.route("/")
def tela_boss_rush():
    estado = carregar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, {}) or {}
    if estado and estado.get("fase") == "battle" and not estado.get("questao"):
        _carregar_questao(estado)
        estado = carregar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, {}) or {}

    return render_template(
        "boss_rush.html",
        alunos=alunos_para_selecao(),
        dificuldades=DIFICULDADES,
        estado=estado,
        boss=(estado.get("bosses") or [{}])[int(estado.get("idx", 0))] if estado.get("bosses") else {},
        questao=_questao_template(estado.get("questao")),
        assinatura_questao=assinatura_da_questao(estado.get("questao")),
        aviso_resposta=AVISO_QUESTAO_TROCADA if request.args.get("aviso") == "questao_trocada" else "",
        resultado=estado.get("resultado"),
        resumo=resumo_historico(estado.get("historico", [])),
        # MELHORIA: este modo ja MONTAVA um "origem_label" com o valor
        # "offline" (ver _questao_template) e nao o mostrava em lugar nenhum.
        # A informacao existia e morria aqui.
        erro_ia=aviso_offline(estado.get("questao")),
        **contexto_aluno_template(),
    )


@boss_rush_bp.route("/iniciar", methods=["POST"])
def iniciar_boss_rush():
    sincronizar_aluno_da_requisicao()
    dificuldade = request.form.get("dificuldade") or "Medio"
    if dificuldade not in DIFICULDADES:
        dificuldade = "Medio"

    salvar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, {
        "fase": "battle",
        "bosses": _bosses(dificuldade),
        "idx": 0,
        "vidas": 3,
        "historico": [],
        "questao": None,
        "resultado": None,
        "tempo_inicio": None,
    })
    return redirect(url_for("boss_rush.tela_boss_rush"))


@boss_rush_bp.route("/responder", methods=["POST"])
def responder_boss_rush():
    estado = carregar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, {}) or {}
    questao = estado.get("questao") or {}
    if not estado or not questao:
        return redirect(url_for("boss_rush.tela_boss_rush"))

    # A questao guardada pode ter trocado entre o desenho da tela e este
    # envio (pagina velha, botao voltar, duas abas). Pontuar o indice
    # contra a questao NOVA e o achado 3.4 do QA de 23/09/2026: o aluno
    # perdia ponto tendo acertado. Nao conta nem acerto nem erro.
    if resposta_veio_de_outra_questao(estado.get("questao")):
        return redirect(url_for("boss_rush.tela_boss_rush", aviso="questao_trocada"))

    alternativas = questao.get("alternativas") or []
    resposta_idx = int(request.form.get("resposta", "-1"))
    resposta_aluno = alternativas[resposta_idx] if 0 <= resposta_idx < len(alternativas) else "Sem resposta"
    resposta_correta = str(questao.get("correta", ""))
    acertou = resposta_aluno == resposta_correta
    tempo = tempo_resposta(estado)
    pontos = 0

    if session.get("aluno_id") and session.get("escola_id"):
        registrar_log_com_tempo(
            {
                "aluno_id": session.get("aluno_id"),
                "escola_id": session.get("escola_id"),
                "materia": f"ENEM-{questao.get('area_bncc', '')}",
                "modo": "boss_rush_enem-flask",
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

    boss = (estado.get("bosses") or [{}])[int(estado.get("idx", 0))]
    historico = list(estado.get("historico", []))
    historico.append(
        {
            "boss": boss.get("nome", "Boss"),
            "area_label": LABEL_AREA.get(questao.get("area_bncc", ""), questao.get("area_bncc", "")),
            "pergunta": questao.get("pergunta", ""),
            "resposta_aluno": resposta_aluno,
            "resposta_correta": resposta_correta,
            "acertou": acertou,
        }
    )

    estado["historico"] = historico
    estado["vidas"] = int(estado.get("vidas", 3)) - (0 if acertou else 1)
    estado["resultado"] = {
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
    if estado["vidas"] <= 0:
        # Perder tambem conclui a partida: o aluno jogou a batalha inteira.
        if estado.get("fase") != "resultado":
            registrar_partida_concluida("boss_rush", estado.get("historico"))
        estado["fase"] = "resultado"
        estado["questao"] = None
        estado["resultado"] = None
    salvar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, estado)
    return redirect(url_for("boss_rush.tela_boss_rush"))


@boss_rush_bp.route("/proximo", methods=["POST"])
def proximo_boss():
    estado = carregar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, {}) or {}
    if not estado:
        return redirect(url_for("boss_rush.tela_boss_rush"))
    idx = int(estado.get("idx", 0))
    if idx + 1 >= len(estado.get("bosses", [])):
        if estado.get("fase") != "resultado":
            registrar_partida_concluida("boss_rush", estado.get("historico"))
        estado["fase"] = "resultado"
        estado["questao"] = None
        estado["resultado"] = None
    else:
        estado["idx"] = idx + 1
        estado["questao"] = None
        estado["resultado"] = None
    salvar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID, estado)
    return redirect(url_for("boss_rush.tela_boss_rush"))


@boss_rush_bp.route("/reiniciar", methods=["POST"])
def reiniciar_boss_rush():
    limpar_estado_persistido(_estado_boss_rush(), BOSS_RUSH_PROGRESSO_ID)
    return redirect(url_for("boss_rush.tela_boss_rush"))


