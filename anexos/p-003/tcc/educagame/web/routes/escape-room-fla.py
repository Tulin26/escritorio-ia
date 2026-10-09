from __future__ import annotations

import time

from flask import Blueprint, redirect, render_template, request, session, url_for

from core.config import MATERIAS, exibir_materia, filtrar_materias_por_serie, normalizar_materia
from web.routes.flask_helpers_fla import (
    alunos_para_selecao,
    assinatura_da_questao,
    aviso_offline,
    AVISO_QUESTAO_TROCADA,
    carregar_estado_persistido,
    contexto_aluno_template,
    limpar_estado_persistido,
    materias_para_template,
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
from services.ia_service import invocar_enigma, obter_ultimo_erro_ia
from services.pedagogical_feedback import gerar_feedback_pedagogico

escape_room_bp = Blueprint("escape_room", __name__)
ESCAPE_ROOM_PROGRESSO_ID = "escape_room_flask"


def _estado_escape_room() -> str:
    return nome_estado_por_aluno(ESCAPE_ROOM_PROGRESSO_ID)


def _questao_template(questao: dict | None) -> dict:
    if not isinstance(questao, dict):
        return {}
    dados = dict(questao)
    dados["materia_label"] = exibir_materia(dados.get("materia", ""))
    dados["explicacao_texto"] = texto_explicacao(dados.get("explicacao"))
    return dados


def _gerar_sala(estado: dict) -> dict:
    idx = int(estado.get("atual", 0))
    salas = estado.get("salas") or []
    if not salas:
        return {}
    sala = salas[idx]
    questao = invocar_enigma(sala["materia"], session.get("ano_escolar") or "1º EM", estado.get("nivel", "Medio"), sala.get("tema", "")) or {}
    questao["materia"] = sala["materia"]
    estado["questao"] = questao
    estado["resultado"] = None
    estado["aviso_ia"] = obter_ultimo_erro_ia()
    estado["tempo_inicio"] = time.time()
    salvar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, estado)
    return questao


def _materias_das_salas(valores: list[str], total: int, materia_padrao: str, materias_permitidas: list[str] | None = None) -> list[str]:
    """A materia de cada sala, na ordem das salas.

    MELHORIA: os seis campos do formulario dividiam o mesmo nome
    ("materias_salas") e a rota lia a lista por POSICAO. Campo que nao chega
    -- select desabilitado pelo script da tela, opcao que o navegador nao
    envia -- some da lista, e a sala 1 passa a receber a materia da sala 2,
    com todas as seguintes escorregando junto. Foi o achado 3.3 do QA de
    23/09/2026 ("Ciencias" descartada e as salas deslocadas). Agora cada sala
    tem o campo dela (materia_sala_1...), e esta funcao recebe a lista ja
    posicionada, com "" onde o campo faltou -- o que vira a materia padrao na
    propria posicao, sem empurrar ninguem.
    """
    permitidas = set(materias_permitidas or MATERIAS)
    materias = []
    for valor in valores[:total]:
        materia = normalizar_materia(valor)
        materias.append(materia if materia in permitidas else materia_padrao)

    while len(materias) < total:
        materias.append(materia_padrao)

    return materias


def _materias_enviadas(total: int) -> list[str]:
    """O que o formulario mandou, uma posicao por sala."""
    return [str(request.form.get(f"materia_sala_{numero}") or "") for numero in range(1, total + 1)]


@escape_room_bp.route("/")
def tela_escape_room():
    estado = carregar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, {}) or {}
    if estado and estado.get("fase") == "sala" and not estado.get("questao"):
        _gerar_sala(estado)
        estado = carregar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, {}) or {}
    salas = estado.get("salas") or []

    return render_template(
        "escape_room.html",
        materias=materias_para_template(MATERIAS),
        alunos=alunos_para_selecao(),
        estado=estado,
        sala=salas[int(estado.get("atual", 0))] if salas and int(estado.get("atual", 0)) < len(salas) else {},
        questao=_questao_template(estado.get("questao")),
        # A assinatura sai da questao GUARDADA, nao da versao que vai para a
        # tela: e ela que a rota de resposta compara (ver resposta_veio_de_
        # outra_questao em flask_helpers_fla.py).
        assinatura_questao=assinatura_da_questao(estado.get("questao")),
        aviso_resposta=AVISO_QUESTAO_TROCADA if request.args.get("aviso") == "questao_trocada" else "",
        resultado=estado.get("resultado"),
        resumo=resumo_historico(estado.get("historico", [])),
        # MELHORIA: o aviso ja era CALCULADO e guardado em estado["aviso_ia"]
        # (ver _gerar_sala) -- e morria ali, porque nao chegava ao template e
        # o template nao tinha onde mostrar. O aluno recebia questao do banco
        # proprio sem saber por que.
        #
        # Sem questao na tela, sem aviso: no relatorio final a questao ja
        # foi limpa por /proxima, mas o aviso_ia da ULTIMA sala fica -- e o
        # relatorio abria com "Esta questao veio do banco..." em cima de
        # questao nenhuma (visto em 30/09/2026, nas telas do TCC).
        erro_ia=(
            aviso_offline(estado.get("questao"), aviso_atual=estado.get("aviso_ia", ""))
            if estado.get("questao")
            else ""
        ),
        **contexto_aluno_template(),
    )


@escape_room_bp.route("/iniciar", methods=["POST"])
def iniciar_escape_room():
    sincronizar_aluno_da_requisicao()
    ano_escolar = session.get("ano_escolar") or "1º EM"
    materias_disponiveis = filtrar_materias_por_serie(MATERIAS, ano_escolar)
    materia = normalizar_materia(request.form.get("materia") or "Matematica")
    if materia not in materias_disponiveis:
        materia = "Matematica"
    nivel = request.form.get("nivel") or "Medio"
    tema = request.form.get("tema") or ""
    total = int(request.form.get("total") or 4)
    if total not in {3, 4, 5, 6}:
        total = 4
    materias_salas = _materias_das_salas(_materias_enviadas(total), total, materia, materias_disponiveis)

    salas = []
    for numero, materia_sala in enumerate(materias_salas, start=1):
        salas.append({"numero": numero, "materia": materia_sala, "tema": tema})

    salvar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, {
        "fase": "sala",
        "nivel": nivel,
        "salas": salas,
        "atual": 0,
        "historico": [],
        "pistas": [],
        "questao": None,
        "resultado": None,
        "tempo_inicio": None,
        "aviso_ia": "",
    })
    return redirect(url_for("escape_room.tela_escape_room"))


@escape_room_bp.route("/responder", methods=["POST"])
def responder_escape_room():
    estado = carregar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, {}) or {}
    questao = estado.get("questao") or {}
    salas = estado.get("salas") or []
    if not estado or not questao or not salas:
        return redirect(url_for("escape_room.tela_escape_room"))

    sala = salas[int(estado.get("atual", 0))]
    # A questao guardada pode ter trocado entre o desenho da tela e este
    # envio (pagina velha, botao voltar, duas abas). Pontuar o indice
    # contra a questao NOVA e o achado 3.4 do QA de 23/09/2026: o aluno
    # perdia ponto tendo acertado. Nao conta nem acerto nem erro.
    if resposta_veio_de_outra_questao(questao):
        return redirect(url_for("escape_room.tela_escape_room", aviso="questao_trocada"))

    opcoes = questao.get("opcoes") or []
    resposta_idx = int(request.form.get("resposta", "-1"))
    correta_idx = int(questao.get("correta", -1))
    acertou = resposta_idx == correta_idx
    resposta_aluno = opcoes[resposta_idx] if 0 <= resposta_idx < len(opcoes) else "Sem resposta"
    resposta_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""
    tempo = tempo_resposta(estado)
    pontos = 0

    if session.get("aluno_id") and session.get("escola_id"):
        registrar_log_com_tempo(
            {
                "aluno_id": session.get("aluno_id"),
                "escola_id": session.get("escola_id"),
                "materia": sala.get("materia", "Geral"),
                "modo": "escape_room-flask",
                "resultado": "Acertou" if acertou else "Errou",
                "pergunta_texto": questao.get("pergunta", ""),
                "resposta_aluno": resposta_aluno,
                "resposta_correta": resposta_correta,
                # as alternativas vao para o log porque sem elas nao ha como
                # medir, contra dado real, se a explicacao contradiz o
                # gabarito (ver 20260910120000_logs_opcoes.sql)
                "opcoes": opcoes,
                "explicacao_ia": str(questao.get("explicacao", "")),
                # O Escape Room nao gravava BNCC nenhuma.
                "area_bncc": questao.get("area_bncc"),
                "competencia_bncc": questao.get("competencia_bncc"),
                "habilidade_bncc": questao.get("habilidade_bncc"),
                "codigo_bncc": questao.get("codigo_bncc"),
                "dificuldade": questao.get("nivel") or estado.get("nivel"),
            },
            tempo,
        )
        pontos = registrar_pontuacao_acerto(session.get("aluno_id"), acertou, questao.get("nivel") or estado.get("nivel", "Medio"))

    historico = list(estado.get("historico", []))
    # MELHORIA: sala repetida (nova tentativa apos erro) aparecia na Revisao
    # e nas Pistas com o MESMO numero e nenhum jeito de distinguir qual
    # tentativa era qual -- "x Sala 3 / v Sala 3" (relatorio de QA de
    # 23/09/2026). Contar quantas vezes esta sala ja apareceu no historico
    # da o numero da tentativa atual.
    tentativa = sum(1 for item in historico if item.get("sala") == sala["numero"]) + 1
    sufixo_tentativa = f" (tentativa {tentativa})" if tentativa > 1 else ""
    pista = (
        f"Sala {sala['numero']} aberta em {exibir_materia(sala['materia'])}{sufixo_tentativa}."
        if acertou
        else f"Sala {sala['numero']}: revisar {exibir_materia(sala['materia'])}{sufixo_tentativa}."
    )
    historico.append(
        {
            "sala": sala["numero"],
            "tentativa": tentativa,
            "materia": sala["materia"],
            "pergunta": questao.get("pergunta", ""),
            "resposta_aluno": resposta_aluno,
            "resposta_correta": resposta_correta,
            "acertou": acertou,
        }
    )
    estado["historico"] = historico
    estado["pistas"] = list(estado.get("pistas", [])) + [pista]
    estado["resultado"] = {
        "acertou": acertou,
        "resposta_aluno": resposta_aluno,
        "resposta_correta": resposta_correta,
        "pontos": pontos,
        "feedback": None if acertou else gerar_feedback_pedagogico(
            dados=questao,
            materia=sala.get("materia", "Geral"),
            resposta_aluno=resposta_aluno,
            resposta_correta=resposta_correta,
        ),
    }
    salvar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, estado)
    return redirect(url_for("escape_room.tela_escape_room"))


@escape_room_bp.route("/proxima", methods=["POST"])
def proxima_sala():
    estado = carregar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, {}) or {}
    if not estado:
        return redirect(url_for("escape_room.tela_escape_room"))
    atual = int(estado.get("atual", 0))
    # Decidido com o usuario em 13/09/2026: errar NAO abre a sala. Antes a
    # porta abria de qualquer jeito (so anotava "revisar"), e o Escape era um
    # simulado com outro nome. Errou, vem outra questao da MESMA sala -- o
    # historico do Oraculo (invocar_enigma) evita repetir a que ele acabou de
    # ver. Sem resposta nenhuma tambem nao abre: antes, mandar /proxima direto
    # pulava a porta.
    acertou = bool((estado.get("resultado") or {}).get("acertou"))
    estado["questao"] = None
    estado["resultado"] = None
    if acertou:
        if atual + 1 >= len(estado.get("salas", [])):
            # Antes de trocar a fase: assim um POST repetido em /proxima com a
            # corrida já encerrada não conta a mesma partida duas vezes.
            if estado.get("fase") != "resultado":
                registrar_partida_concluida("escape_room", estado.get("historico"))
            estado["fase"] = "resultado"
        else:
            estado["atual"] = atual + 1
    salvar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID, estado)
    return redirect(url_for("escape_room.tela_escape_room"))


@escape_room_bp.route("/reiniciar", methods=["POST"])
def reiniciar_escape_room():
    limpar_estado_persistido(_estado_escape_room(), ESCAPE_ROOM_PROGRESSO_ID)
    return redirect(url_for("escape_room.tela_escape_room"))

