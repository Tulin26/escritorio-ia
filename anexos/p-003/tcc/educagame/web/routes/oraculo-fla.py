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
    limpar_estado_flask,
    materias_para_template,
    obter_estado_flask,
    registrar_pontuacao_acerto,
    resposta_veio_de_outra_questao,
    salvar_estado_flask,
    sincronizar_aluno_da_requisicao,
    texto_explicacao,
)
from services.dados_service import registrar_log_com_tempo
from services.ia_service import invocar_enigma, obter_ultimo_erro_ia
from services.pedagogical_feedback import gerar_feedback_pedagogico

def _tempo_desde(inicio) -> float | None:
    """Quantos segundos o aluno levou desde que a questao apareceu."""
    if not isinstance(inicio, (int, float)):
        return None
    return max(0.0, time.time() - float(inicio))


oraculo_bp = Blueprint("oraculo", __name__)


@oraculo_bp.route("/", methods=["GET", "POST"])
def tela_oraculo():
    if request.method == "POST":
        sincronizar_aluno_da_requisicao()
        materia = normalizar_materia(request.form.get("materia") or "Matematica")
        ano_escolar = session.get("ano_escolar") or "1º EM"
        if materia not in filtrar_materias_por_serie(MATERIAS, ano_escolar):
            materia = "Matematica"
        nivel = request.form.get("nivel") or "Médio"
        tema = request.form.get("tema") or ""

        enigma = invocar_enigma(materia, ano_escolar, nivel, tema) or {}
        enigma["materia"] = materia
        enigma["materia_label"] = exibir_materia(materia)
        enigma["ano_escolar"] = ano_escolar
        enigma["nivel"] = nivel
        enigma["tema"] = tema
        enigma["explicacao_texto"] = texto_explicacao(enigma.get("explicacao"))
        # Mesmo motivo do Laboratorio: sem anotar quando a questao
        # apareceu, o painel do professor fica sem tempo de resposta.
        enigma["_tempo_inicio"] = time.time()
        salvar_estado_flask("enigma_atual", enigma)
        limpar_estado_flask("resultado_oraculo")
        # MELHORIA: usa direto o enigma recem-gerado em memoria em vez de
        # depender de reler do Supabase na mesma requisicao (ver mesma
        # correcao em laboratorio_fla.py).
        enigma_para_template = enigma
    else:
        enigma_para_template = obter_estado_flask("enigma_atual")

    # MELHORIA: mesmo defeito do Laboratório, mesma forma -- o aviso de "esta
    # questão veio do banco" só era calculado no ramo do POST, e a tela de
    # correção (um GET, depois do redirect) chegava sem ele. Um cálculo só,
    # depois do if/else, vale para os dois métodos.
    #
    # O erro global da cascata só conta no POST: no GET ele poderia ser de
    # outra requisição. No GET quem responde é a marca gravada no enigma.
    erro_ia = aviso_offline(
        enigma_para_template if isinstance(enigma_para_template, dict) else {},
        "questao",
        obter_ultimo_erro_ia() if request.method == "POST" else "",
    )

    # MELHORIA: o formulario continua na tela depois de gerar, logo acima do
    # enigma, e voltava com Matematica marcada -- a primeira opcao --, nao a
    # materia pedida. Visto em 11/09/2026: Biologia pedida e gerada, e a tela
    # dizendo "Materia: Matematica" em cima da questao. Um segundo clique em
    # "Gerar desafio" sem reparar pedia Matematica de verdade. O Laboratorio
    # ja devolvia a materia marcada; aqui faltava.
    enigma_marcado = enigma_para_template if isinstance(enigma_para_template, dict) else {}

    return render_template(
        "oraculo.html",
        materias=materias_para_template(MATERIAS),
        materia_selecionada=enigma_marcado.get("materia") or "",
        nivel_selecionado=enigma_marcado.get("nivel") or "Médio",
        alunos=alunos_para_selecao(),
        enigma=enigma_para_template,
        assinatura_questao=assinatura_da_questao(enigma_para_template),
        aviso_resposta=AVISO_QUESTAO_TROCADA if request.args.get("aviso") == "questao_trocada" else "",
        resultado=obter_estado_flask("resultado_oraculo"),
        erro_ia=erro_ia,
        **contexto_aluno_template(),
    )


@oraculo_bp.route("/nova", methods=["POST"])
def nova_pergunta_oraculo():
    limpar_estado_flask("enigma_atual")
    limpar_estado_flask("resultado_oraculo")
    return redirect(url_for("oraculo.tela_oraculo"))


@oraculo_bp.route("/responder", methods=["POST"])
def responder_oraculo():
    enigma = obter_estado_flask("enigma_atual", {}) or {}
    if not enigma:
        return redirect(url_for("oraculo.tela_oraculo"))

    # A questao guardada pode ter trocado entre o desenho da tela e este
    # envio (pagina velha, botao voltar, duas abas). Pontuar o indice
    # contra a questao NOVA e o achado 3.4 do QA de 23/09/2026: o aluno
    # perdia ponto tendo acertado. Nao conta nem acerto nem erro.
    if resposta_veio_de_outra_questao(enigma):
        return redirect(url_for("oraculo.tela_oraculo", aviso="questao_trocada"))

    try:
        resposta_idx = int(request.form.get("resposta", "-1"))
    except ValueError:
        resposta_idx = -1

    opcoes = enigma.get("opcoes") or []
    correta_idx = int(enigma.get("correta", -1))
    acertou = resposta_idx == correta_idx

    resposta_aluno = opcoes[resposta_idx] if 0 <= resposta_idx < len(opcoes) else "Sem resposta"
    resposta_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""

    pontos = 0
    if session.get("aluno_id") and session.get("escola_id"):
        registrar_log_com_tempo(
            {
                "aluno_id": session.get("aluno_id"),
                "escola_id": session.get("escola_id"),
                "materia": enigma.get("materia", "Geral"),
                "modo": "oraculo-flask",
                "resultado": "Acertou" if acertou else "Errou",
                "pergunta_texto": enigma.get("pergunta", ""),
                "resposta_aluno": resposta_aluno,
                "resposta_correta": resposta_correta,
                # as alternativas vao para o log porque sem elas nao ha como
                # medir, contra dado real, se a explicacao contradiz o
                # gabarito (ver 20260910120000_logs_opcoes.sql)
                "opcoes": opcoes,
                "explicacao_ia": str(enigma.get("explicacao", "")),
                "area_bncc": enigma.get("area_bncc"),
                "competencia_bncc": enigma.get("competencia_bncc"),
                "habilidade_bncc": enigma.get("habilidade_bncc"),
                "codigo_bncc": enigma.get("codigo_bncc"),
                "dificuldade": enigma.get("nivel"),
            },
            _tempo_desde(enigma.get("_tempo_inicio")),
        )
        pontos = registrar_pontuacao_acerto(session.get("aluno_id"), acertou, enigma.get("nivel", "Médio"))

    salvar_estado_flask("resultado_oraculo", {
        "acertou": acertou,
        "resposta_aluno": resposta_aluno,
        "resposta_correta": resposta_correta,
        "pontos": pontos,
        "feedback": None if acertou else gerar_feedback_pedagogico(
            dados=enigma,
            materia=enigma.get("materia", "Geral"),
            resposta_aluno=resposta_aluno,
            resposta_correta=resposta_correta,
        ),
    })
    return redirect(url_for("oraculo.tela_oraculo"))

