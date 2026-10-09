from __future__ import annotations

import re
import time

from flask import Blueprint, redirect, render_template, request, session, url_for

from core.answer_equivalence import respostas_equivalentes
from core.config import eh_ensino_medio, exibir_materia, filtrar_materias_por_serie, normalizar_materia
from core.formula_formatting import (
    formatar_formula_passo_latex,
    formatar_formula_principal_latex,
    formatar_subformulas_auxiliares_latex,
    separar_texto_formula_passo,
)
from core.text_cleanup import aplicar_acentos_pt
from core.utils import formatar_unidades_texto
from web.routes.flask_helpers_fla import (
    AVISO_QUESTAO_TROCADA,
    alunos_para_selecao,
    assinatura_da_questao,
    aviso_offline,
    contexto_aluno_template,
    expoentes_em_sobrescrito,
    formatar_pergunta_exatas,
    limpar_estado_flask,
    materias_para_template,
    obter_estado_flask,
    registrar_pontuacao_acerto,
    resposta_veio_de_outra_questao,
    salvar_estado_flask,
    sincronizar_aluno_da_requisicao,
)
from services.calculo_service import gerar_desafio_exatas
from services.dados_service import registrar_log_com_tempo
from services.ia_service import obter_ultimo_erro_ia
from services.banks.laboratorio import gerar_desafio_laboratorio_offline
from services.pedagogical_feedback import gerar_feedback_pedagogico

laboratorio_bp = Blueprint("laboratorio", __name__)

MATERIAS_LAB = ("Matematica", "Fisica", "Quimica", "Ciencias")


def _tempo_desde(inicio) -> float | None:
    """Quantos segundos o aluno levou desde que a questao apareceu."""
    if not isinstance(inicio, (int, float)):
        return None
    return max(0.0, time.time() - float(inicio))


def _serie_tipo_laboratorio(ano_escolar: str) -> str:
    return "EM" if eh_ensino_medio(ano_escolar) else "EF"


def _preparar_desafio_para_template(desafio: dict | None) -> dict:
    if not isinstance(desafio, dict):
        return {}

    preparado = dict(desafio)
    preparado["enigma"] = aplicar_acentos_pt(preparado.get("enigma", ""))
    preparado["pergunta"] = aplicar_acentos_pt(preparado.get("pergunta", ""))
    preparado["legenda_variaveis"] = aplicar_acentos_pt(preparado.get("legenda_variaveis", ""))
    preparado["pergunta_formatada"] = formatar_pergunta_exatas(preparado.get("pergunta", ""))
    preparado["formula_latex"] = formatar_formula_principal_latex(preparado.get("formula", ""))
    preparado["subformulas_latex"] = formatar_subformulas_auxiliares_latex(preparado.get("subformulas", []))
    preparado["opcoes_formatadas"] = [
        formatar_unidades_texto(opcao) for opcao in preparado.get("opcoes", []) or []
    ]

    passos = []
    for passo in preparado.get("passos_resolucao", []) or []:
        if not isinstance(passo, dict):
            continue
        conteudo = str(passo.get("conteudo", "") or "").strip()
        texto_passo, formula_passo = separar_texto_formula_passo(conteudo)
        formula_passo = re.sub(r"\s+e\s+(?=[A-Za-z]\s*=)", ", ", formula_passo).strip().rstrip(".")
        passos.append(
            {
                "titulo": aplicar_acentos_pt(str(passo.get("titulo", "Etapa") or "Etapa")),
                "conteudo": aplicar_acentos_pt(conteudo),
                # o passo que sobra como PROSA tambem carrega conta no meio
                # ("(x - 4)^2"); sem isto o expoente chega cru.
                "conteudo_texto": expoentes_em_sobrescrito(aplicar_acentos_pt(texto_passo)),
                "conteudo_latex": formatar_formula_passo_latex(formula_passo) if formula_passo else "",
                "final": bool(passo.get("final")),
            }
        )
    preparado["passos_template"] = passos

    return preparado


@laboratorio_bp.route("/", methods=["GET", "POST"])
def tela_laboratorio():
    if request.method == "POST":
        sincronizar_aluno_da_requisicao()
        materia = normalizar_materia(request.form.get("materia") or "Matematica")
        nivel = request.form.get("nivel") or "Médio"
        tema = request.form.get("tema") or ""
        ano_escolar = session.get("ano_escolar") or "1º EM"
        if materia not in filtrar_materias_por_serie(MATERIAS_LAB, ano_escolar):
            materia = "Matematica"

        try:
            desafio = gerar_desafio_exatas(materia, tema, ano_escolar, nivel) or {}
        except Exception as exc:
            print(f"[LAB] Falha ao gerar desafio; usando fallback offline seguro: {type(exc).__name__}: {exc}")
            desafio = gerar_desafio_laboratorio_offline(
                materia,
                tema,
                nivel,
                serie_tipo=_serie_tipo_laboratorio(ano_escolar),
            )
            # A marca é o que faz o aviso sobreviver: quem monta a frase é
            # `aviso_offline`, a partir dela. Aqui havia uma sexta redação
            # própria ("Falha temporária ao gerar por IA. Usando banco de
            # questões local."), e ela ainda vencia o funil por causa do
            # `erro_ia or ...` logo abaixo.
            desafio["_origem_geracao"] = "offline"
        desafio["materia"] = materia
        desafio["materia_label"] = exibir_materia(materia)
        desafio["ano_escolar"] = ano_escolar
        desafio["nivel"] = nivel
        desafio["tema"] = tema
        # MELHORIA: o Laboratorio nao registrava tempo de resposta -- medido,
        # 53 dos 107 logs reais, o modo MAIS usado, sem o dado que o painel
        # do professor mostra. A causa era so esta: nasce o desafio e
        # ninguem anota quando. O Treino ja fazia assim.
        desafio["_tempo_inicio"] = time.time()
        salvar_estado_flask("desafio_laboratorio", desafio)
        limpar_estado_flask("resultado_laboratorio")
        # MELHORIA: usa direto o desafio recem-gerado em memoria em vez de
        # depender de reler do Supabase na mesma requisicao. Se a releitura
        # falhar (rede, tabela ausente etc.), a pergunta que ja tinhamos na
        # mao nao pode ser jogada fora silenciosamente.
        desafio_salvo = desafio
    else:
        desafio_salvo = obter_estado_flask("desafio_laboratorio")

    ano_atual = session.get("ano_escolar") or "1º EM"
    if isinstance(desafio_salvo, dict) and desafio_salvo:
        serie_esperada = _serie_tipo_laboratorio(ano_atual)
        serie_desafio = str(desafio_salvo.get("serie_tipo") or "EM").upper()
        ano_desafio = str(desafio_salvo.get("ano_escolar") or "")
        if serie_desafio != serie_esperada or (ano_desafio and ano_desafio != str(ano_atual)):
            limpar_estado_flask("desafio_laboratorio")
            limpar_estado_flask("resultado_laboratorio")
            desafio_salvo = {}

    desafio = _preparar_desafio_para_template(desafio_salvo)
    materia_selecionada = desafio.get("materia") or "Matematica"
    nivel_selecionado = desafio.get("nivel") or "Médio"

    # MELHORIA: o aviso de "esta questão veio do banco" só era calculado no
    # ramo do POST. Responder redireciona para cá em GET, e o aluno lia a
    # explicação sem saber mais de onde a questão tinha vindo -- que é
    # justamente quando a origem importa, porque é quando ele decide se
    # confia nela. Agora o cálculo é um só, depois de o desafio estar
    # resolvido, e vale para os dois métodos.
    #
    # `obter_ultimo_erro_ia()` só entra no POST: é um valor global do
    # processo, e no GET ele poderia ser o erro da requisição de outro aluno.
    # No GET quem responde é a marca gravada junto do desafio.
    erro_ia = aviso_offline(
        desafio_salvo if isinstance(desafio_salvo, dict) else {},
        "desafio",
        obter_ultimo_erro_ia() if request.method == "POST" else "",
    )

    return render_template(
        "laboratorio.html",
        materias=materias_para_template(MATERIAS_LAB),
        materia_selecionada=materia_selecionada,
        nivel_selecionado=nivel_selecionado,
        alunos=alunos_para_selecao(),
        desafio=desafio,
        assinatura_questao=assinatura_da_questao(desafio_salvo),
        aviso_resposta=AVISO_QUESTAO_TROCADA if request.args.get("aviso") == "questao_trocada" else "",
        resultado=obter_estado_flask("resultado_laboratorio"),
        erro_ia=erro_ia,
        **contexto_aluno_template(),
    )


@laboratorio_bp.route("/nova", methods=["POST"])
def novo_experimento_laboratorio():
    limpar_estado_flask("desafio_laboratorio")
    limpar_estado_flask("resultado_laboratorio")
    return redirect(url_for("laboratorio.tela_laboratorio"))


@laboratorio_bp.route("/responder", methods=["POST"])
def responder_laboratorio():
    desafio = obter_estado_flask("desafio_laboratorio", {}) or {}
    if not desafio:
        return redirect(url_for("laboratorio.tela_laboratorio"))

    # A questao guardada pode ter trocado entre o desenho da tela e este
    # envio (pagina velha, botao voltar, duas abas). Pontuar o indice
    # contra a questao NOVA e o achado 3.4 do QA de 23/09/2026: o aluno
    # perdia ponto tendo acertado. Nao conta nem acerto nem erro.
    if resposta_veio_de_outra_questao(desafio):
        return redirect(url_for("laboratorio.tela_laboratorio", aviso="questao_trocada"))

    try:
        resposta_idx = int(request.form.get("resposta", "-1"))
    except ValueError:
        resposta_idx = -1

    opcoes = desafio.get("opcoes") or []
    correta_idx = int(desafio.get("correta", -1))

    resposta_aluno = opcoes[resposta_idx] if 0 <= resposta_idx < len(opcoes) else "Sem resposta"
    resposta_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""
    acertou = resposta_idx == correta_idx or respostas_equivalentes(
        resposta_aluno, resposta_correta, str(desafio.get("pergunta", "") or "")
    )

    pontos = 0
    if session.get("aluno_id") and session.get("escola_id"):
        registrar_log_com_tempo(
            {
                "aluno_id": session.get("aluno_id"),
                "escola_id": session.get("escola_id"),
                "materia": f"LAB-{desafio.get('materia', 'Matematica')}",
                "modo": "laboratorio-flask",
                "resultado": "Acertou" if acertou else "Errou",
                "pergunta_texto": desafio.get("pergunta", ""),
                "resposta_aluno": resposta_aluno,
                "resposta_correta": resposta_correta,
                # as alternativas vao para o log porque sem elas nao ha como
                # medir, contra dado real, se a explicacao contradiz o
                # gabarito (ver 20260910120000_logs_opcoes.sql)
                "opcoes": opcoes,
                "explicacao_ia": str(desafio.get("explicacao", "")),
                "dificuldade": desafio.get("nivel"),
                # Guardado para poder MEDIR validações da IA contra dado real
                # — ver a migração 20260903120000. Só o Laboratório tem passos:
                # os outros modos passam por _normalizar_questao_oraculo, que
                # os apaga de propósito.
                "passos_resolucao": desafio.get("passos_resolucao"),
                # Pelo mesmo motivo, e para a validação vizinha: a
                # `legenda-com-variavel-sem-formula` cruza os três, e sem eles
                # no log só dava para medi-la contra o banco offline — que
                # engana (ver a migração 20260909120000).
                "formula": desafio.get("formula"),
                "subformulas": desafio.get("subformulas"),
                "legenda_variaveis": desafio.get("legenda_variaveis"),
                # O Laboratorio era o unico modo de exatas sem BNCC no log.
                "area_bncc": desafio.get("area_bncc"),
                "competencia_bncc": desafio.get("competencia_bncc"),
                "habilidade_bncc": desafio.get("habilidade_bncc"),
                "codigo_bncc": desafio.get("codigo_bncc"),
            },
            _tempo_desde(desafio.get("_tempo_inicio")),
        )
        pontos = registrar_pontuacao_acerto(session.get("aluno_id"), acertou, desafio.get("nivel", "Médio"))

    salvar_estado_flask("resultado_laboratorio", {
        "acertou": acertou,
        "resposta_aluno": formatar_unidades_texto(resposta_aluno),
        "resposta_correta": formatar_unidades_texto(resposta_correta),
        "pontos": pontos,
        "feedback": None if acertou else gerar_feedback_pedagogico(
            dados=desafio,
            materia=desafio.get("materia", "Matematica"),
            resposta_aluno=resposta_aluno,
            resposta_correta=resposta_correta,
        ),
    })
    return redirect(url_for("laboratorio.tela_laboratorio"))
