from __future__ import annotations

import io
import re
import time

from flask import Blueprint, redirect, render_template, request, send_file, session, url_for

from core.config import exibir_materia, normalizar_materia
from core.formula_formatting import formatar_formula_passo_latex, separar_texto_formula_passo
from core.text_cleanup import aplicar_acentos_pt
from web.routes.flask_helpers_fla import (
    alunos_para_selecao,
    assinatura_da_questao,
    aviso_offline,
    AVISO_QUESTAO_TROCADA,
    contexto_aluno_template,
    expoentes_em_sobrescrito,
    formatar_pergunta_exatas,
    formatar_texto_simples_pergunta,
    latex,
    registrar_partida_concluida,
    registrar_pontuacao_acerto,
    resposta_veio_de_outra_questao,
    sincronizar_aluno_da_requisicao,
    texto_explicacao,
)
from services import rpg_service
from services.dados_service import (
    carregar_progresso_rpg,
    registrar_log_com_tempo,
    remover_progresso_rpg,
    salvar_progresso_rpg,
)
from services.pedagogical_feedback import gerar_feedback_pedagogico
from services.relatorios import gerar_pdf_rpg
from services.rpg_config_service import listar_rpg_configs

rpg_bp = Blueprint("rpg", __name__)
_RPG_ESTADOS_LOCAIS: dict[str, dict] = {}


def _configs() -> list[dict]:
    escola_id = session.get("escola_id")
    return listar_rpg_configs(escola_id) if escola_id else []


def _config_por_id(config_id: str) -> dict:
    return next((cfg for cfg in _configs() if str(cfg.get("id")) == str(config_id)), {})


def _estado_key(aluno_id: str, aventura_id: str) -> str:
    escola_id = str(session.get("escola_id") or "")
    return f"{escola_id}:{aluno_id}:{aventura_id}"


def _estado_atual() -> dict:
    aluno_id = str(session.get("aluno_id") or "")
    aventura_id = str(session.get("rpg_aventura_id") or "")
    if not aluno_id or not aventura_id:
        return {}
    chave = _estado_key(aluno_id, aventura_id)
    escola_id = str(session.get("escola_id") or "")
    if escola_id:
        salvo = carregar_progresso_rpg(escola_id, aluno_id, aventura_id)
        estado_salvo = (salvo or {}).get("estado") if isinstance(salvo, dict) else None
        if isinstance(estado_salvo, dict):
            _RPG_ESTADOS_LOCAIS[chave] = estado_salvo
            return estado_salvo
    return _RPG_ESTADOS_LOCAIS.get(chave, {})


def _salvar_estado_sessao(estado: dict, origem: str = "auto") -> None:
    aluno_id = str(session.get("aluno_id") or "")
    aventura_id = str(estado.get("aventura_id") or session.get("rpg_aventura_id") or "")
    if aluno_id and aventura_id:
        session["rpg_aventura_id"] = aventura_id
        chave = _estado_key(aluno_id, aventura_id)
        _RPG_ESTADOS_LOCAIS[chave] = estado
        escola_id = str(session.get("escola_id") or "")
        if escola_id:
            salvar_progresso_rpg(escola_id, aluno_id, aventura_id, estado, origem=origem)


def _montar_estado(cena: dict, config: dict, estado_salvo: dict | None = None) -> dict:
    estado_salvo = estado_salvo or {}
    cena_salva = estado_salvo.get("cena") or cena
    jornada_salva = estado_salvo.get("jornada")
    jornada_inicial = rpg_service.criar_jornada_inicial(
        config.get("materia", "Matematica"),
        config.get("titulo") or estado_salvo.get("titulo") or "Aventura RPG",
    )
    return {
        "aventura_id": str(config.get("id") or estado_salvo.get("aventura_id") or ""),
        "titulo": estado_salvo.get("titulo") or cena.get("titulo") or config.get("titulo") or "Aventura RPG",
        "config_rpg": config or estado_salvo.get("config_rpg") or {},
        "cena": rpg_service.normalizar_textos_cena(cena_salva),
        "hp": int(estado_salvo.get("hp", 100) or 100),
        "xp": int(estado_salvo.get("xp", 0) or 0),
        "fase": int(estado_salvo.get("fase", 1) or 1),
        "historico": list(estado_salvo.get("historico") or []),
        "temas_usados": list(estado_salvo.get("temas_usados") or []),
        "jornada": jornada_salva if isinstance(jornada_salva, dict) else jornada_inicial,
        "ultima_escolha": estado_salvo.get("ultima_escolha"),
        "ultima_checagem_escolha": estado_salvo.get("ultima_checagem_escolha"),
        "desafio_atual": estado_salvo.get("desafio_atual"),
        "resultado": estado_salvo.get("resultado"),
        "status": estado_salvo.get("status") or "em_andamento",
        "tempo_inicio": estado_salvo.get("tempo_inicio"),
    }


def _preparar_passos_resolucao(passos_resolucao) -> list[dict]:
    # O preparo mora em flask_helpers_fla.passos_para_template desde que o
    # ENEM e a Batalha passaram a mostrar os passos com o mesmo desenho.
    from web.routes.flask_helpers_fla import passos_para_template

    return passos_para_template(passos_resolucao)


def _preparar_desafio(desafio: dict | None, materia: str) -> dict:
    if not isinstance(desafio, dict):
        return {}
    preparado = dict(desafio)
    preparado["explicacao_texto"] = texto_explicacao(preparado.get("explicacao"))
    preparado["formula_latex"] = latex(preparado.get("formula", ""))
    preparado["subformulas_latex"] = [latex(item) for item in preparado.get("subformulas", []) or [] if str(item).strip()]
    preparado["passos_template"] = _preparar_passos_resolucao(preparado.get("passos_resolucao"))
    pergunta = str(preparado.get("pergunta", "") or "")
    if normalizar_materia(materia) in {"Matematica", "Fisica", "Quimica"}:
        preparado["pergunta_formatada"] = formatar_pergunta_exatas(pergunta)
    else:
        preparado["pergunta_formatada"] = {
            "texto": formatar_texto_simples_pergunta(pergunta),
            "latex": "",
            "sufixo": "",
        }
    return preparado


def _preparar_resultado_rpg(resultado: dict | None) -> dict | None:
    if not isinstance(resultado, dict):
        return resultado
    preparado = dict(resultado)
    preparado["formula_latex"] = latex(preparado.get("formula", ""))
    preparado["subformulas_latex"] = [latex(item) for item in preparado.get("subformulas", []) or [] if str(item).strip()]
    preparado["passos_template"] = _preparar_passos_resolucao(preparado.get("passos_resolucao"))
    return preparado


def _avancar_cena(estado: dict, resultado: str | None) -> dict:
    config = estado.get("config_rpg") or {}
    fase_atual = int(estado.get("fase", 1) or 1)
    if fase_atual >= rpg_service.FASES_TOTAIS:
        # So na virada: _avancar_cena pode ser chamada de novo com a aventura
        # ja encerrada, e a meta contaria a mesma partida duas vezes.
        if not estado.get("status"):
            registrar_partida_concluida("rpg", estado.get("historico"))
        estado["status"] = "vitoria" if int(estado.get("hp", 0) or 0) > 0 else "derrota"
        estado["desafio_atual"] = None
        return estado

    nova_cena = rpg_service.continuar_aventura(
        config,
        estado.get("historico"),
        (estado.get("ultima_escolha") or {}).get("texto", "avancar"),
        resultado,
        estado.get("ultima_checagem_escolha"),
        estado.get("jornada"),
        estado.get("ultima_escolha"),
    )
    estado["fase"] = fase_atual + 1
    estado["cena"] = nova_cena
    estado["desafio_atual"] = None
    estado["tempo_inicio"] = None
    return estado


@rpg_bp.route("/")
def tela_rpg():
    configs = _configs()
    estado = _estado_atual()
    if isinstance(estado, dict) and isinstance(estado.get("resultado"), dict):
        estado = dict(estado)
        estado["resultado"] = _preparar_resultado_rpg(estado.get("resultado"))
    config_id = str(request.args.get("aventura_id") or session.get("rpg_aventura_id") or (configs[0].get("id") if configs else ""))
    config = _config_por_id(config_id) if config_id else {}
    salvo = None
    if session.get("escola_id") and session.get("aluno_id") and config_id:
        salvo = carregar_progresso_rpg(session["escola_id"], session["aluno_id"], config_id)
    materia = config.get("materia") or (estado.get("config_rpg") or {}).get("materia", "")
    desafio = _preparar_desafio(estado.get("desafio_atual"), materia)
    erro_ia = aviso_offline(desafio, "questao", desafio.get("aviso_ia", ""))

    return render_template(
        "rpg.html",
        configs=configs,
        config=config,
        config_id=config_id,
        estado=estado,
        desafio=desafio,
        assinatura_questao=assinatura_da_questao(estado.get("desafio_atual") if estado else {}),
        aviso_resposta=AVISO_QUESTAO_TROCADA if request.args.get("aviso") == "questao_trocada" else "",
        salvo=salvo,
        fases_totais=rpg_service.FASES_TOTAIS,
        resumo=rpg_service.resumir_jornada(estado.get("jornada") if estado else None),
        alunos=alunos_para_selecao(),
        erro_ia=erro_ia,
        **contexto_aluno_template(),
    )


@rpg_bp.route("/iniciar", methods=["POST"])
def iniciar_rpg():
    sincronizar_aluno_da_requisicao()
    config_id = request.form.get("aventura_id") or ""
    config = _config_por_id(config_id)
    if not config:
        return redirect(url_for("rpg.tela_rpg"))
    cena = rpg_service.iniciar_aventura(config)
    estado = _montar_estado(cena, config)
    remover_progresso_rpg(session.get("escola_id", ""), session.get("aluno_id", ""), config_id)
    _salvar_estado_sessao(estado, origem="iniciar")
    return redirect(url_for("rpg.tela_rpg"))


@rpg_bp.route("/continuar", methods=["POST"])
def continuar_rpg():
    sincronizar_aluno_da_requisicao()
    config_id = request.form.get("aventura_id") or ""
    config = _config_por_id(config_id)
    salvo = None
    if session.get("escola_id") and session.get("aluno_id") and config_id:
        salvo = carregar_progresso_rpg(session["escola_id"], session["aluno_id"], config_id)
    estado_salvo = (salvo or {}).get("estado") if isinstance(salvo, dict) else None
    if config and isinstance(estado_salvo, dict):
        estado = _montar_estado(estado_salvo.get("cena") or {}, config, estado_salvo)
        _salvar_estado_sessao(estado, origem="continuar")
    return redirect(url_for("rpg.tela_rpg"))


@rpg_bp.route("/salvar", methods=["POST"])
def salvar_rpg():
    estado = _estado_atual()
    if estado and session.get("escola_id") and session.get("aluno_id"):
        _salvar_estado_sessao(estado, origem="manual")
    return redirect(url_for("rpg.tela_rpg"))


@rpg_bp.route("/escolher", methods=["POST"])
def escolher_rota():
    estado = _estado_atual()
    if not estado or estado.get("status") != "em_andamento":
        return redirect(url_for("rpg.tela_rpg"))
    try:
        opcao_id = int(request.form.get("opcao_id", "0"))
    except ValueError:
        opcao_id = 0

    opcoes = (estado.get("cena") or {}).get("opcoes") or []
    opcao = next((item for item in opcoes if int(item.get("id", -1)) == opcao_id), None)
    if not opcao:
        return redirect(url_for("rpg.tela_rpg"))

    fase = int(estado.get("fase", 1) or 1)
    estado["resultado"] = None
    checagem = rpg_service.resolver_tentativa_acao(opcao, estado.get("jornada"), fase)
    estado["ultima_escolha"] = opcao
    estado["ultima_checagem_escolha"] = checagem
    estado["jornada"] = rpg_service.registrar_escolha_jornada(estado.get("jornada"), opcao, fase)
    estado["xp"] = int(estado.get("xp", 0) or 0) + int(checagem.get("xp_imediato", 0) or 0)
    estado["hp"] = max(0, int(estado.get("hp", 100) or 100) - int(checagem.get("hp_perda_imediata", 0) or 0))
    estado["historico"].append(
        {
            "fase": fase,
            "acao": opcao.get("texto", ""),
            "rota": opcao.get("rota", ""),
            "status": "Sucesso" if checagem.get("sucesso") else "Falha",
            "narracao": (
                f"{opcao.get('texto', '')} "
                f"{'A ação funcionou' if checagem.get('sucesso') else 'A ação falhou'}, "
                f"com rolagem {checagem.get('rolagem')} contra chance {checagem.get('chance_sucesso')}%. "
                f"{opcao.get('consequencia_imediata', '')}"
            ),
        }
    )

    if estado["hp"] <= 0:
        estado["status"] = "derrota"
    elif rpg_service.deve_gerar_desafio(fase, opcao):
        desafio = rpg_service.gerar_desafio_academico(
            estado.get("config_rpg"),
            (estado.get("cena") or {}).get("local_atual", ""),
            (estado.get("cena") or {}).get("narracao", ""),
            estado.get("temas_usados"),
            estado.get("jornada"),
            opcao,
        )
        estado["desafio_atual"] = desafio
        estado["temas_usados"].append(desafio.get("tema_usado", ""))
        estado["tempo_inicio"] = time.time()
    else:
        estado = _avancar_cena(estado, None)

    _salvar_estado_sessao(estado, origem="escolha")
    return redirect(url_for("rpg.tela_rpg"))


@rpg_bp.route("/responder", methods=["POST"])
def responder_desafio():
    estado = _estado_atual()
    desafio = estado.get("desafio_atual") if estado else {}
    if not estado or not desafio:
        return redirect(url_for("rpg.tela_rpg"))

    # A questao guardada pode ter trocado entre o desenho da tela e este
    # envio (pagina velha, botao voltar, duas abas). Pontuar o indice
    # contra a questao NOVA e o achado 3.4 do QA de 23/09/2026: o aluno
    # perdia ponto tendo acertado. Nao conta nem acerto nem erro.
    if resposta_veio_de_outra_questao(estado.get("desafio_atual")):
        return redirect(url_for("rpg.tela_rpg", aviso="questao_trocada"))
    try:
        resposta_idx = int(request.form.get("resposta", "-1"))
    except ValueError:
        resposta_idx = -1
    opcoes = desafio.get("opcoes") or []
    correta_idx = int(desafio.get("correta", -1))
    acertou = resposta_idx == correta_idx
    resposta_aluno = opcoes[resposta_idx] if 0 <= resposta_idx < len(opcoes) else "Sem resposta"
    resposta_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""

    risco = rpg_service.calcular_resultado_desafio(
        estado.get("ultima_escolha"),
        acertou,
        bool((estado.get("ultima_checagem_escolha") or {}).get("bonus_risco_ativo", True)),
    )
    estado["xp"] = int(estado.get("xp", 0) or 0) + int(risco.get("xp_ganho", 0) or 0)
    estado["hp"] = max(0, int(estado.get("hp", 100) or 100) - int(risco.get("hp_perda", 0) or 0))
    pontos = 0
    if session.get("aluno_id") and session.get("escola_id"):
        registrar_log_com_tempo(
            {
                "aluno_id": session.get("aluno_id"),
                "escola_id": session.get("escola_id"),
                "materia": f"RPG-{(estado.get('config_rpg') or {}).get('materia', 'Geral')}",
                "modo": "rpg-flask",
                "resultado": "Acertou" if acertou else "Errou",
                "pergunta_texto": desafio.get("pergunta", ""),
                "resposta_aluno": resposta_aluno,
                "resposta_correta": resposta_correta,
                # as alternativas vao para o log porque sem elas nao ha como
                # medir, contra dado real, se a explicacao contradiz o
                # gabarito (ver 20260910120000_logs_opcoes.sql)
                "opcoes": opcoes,
                "explicacao_ia": texto_explicacao(desafio.get("explicacao")),
                "dificuldade": (estado.get("config_rpg") or {}).get("nivel", "Medio"),
                # MELHORIA: a questao do RPG JA trazia estes campos, e a rota
                # simplesmente nao os gravava -- 17 de 17 logs de RPG saiam
                # sem BNCC nenhum, enquanto o dado estava ali do lado.
                "area_bncc": desafio.get("area_bncc"),
                "competencia_bncc": desafio.get("competencia_bncc"),
                "habilidade_bncc": desafio.get("habilidade_bncc"),
                "codigo_bncc": desafio.get("codigo_bncc"),
            },
            max(0.0, time.time() - float(estado.get("tempo_inicio") or time.time())),
        )
        pontos = registrar_pontuacao_acerto(
            session.get("aluno_id"),
            acertou,
            (estado.get("config_rpg") or {}).get("nivel", "Medio"),
        )

    estado["resultado"] = {
        "acertou": acertou,
        "resposta_aluno": resposta_aluno,
        "resposta_correta": resposta_correta,
        "pontos": pontos,
        "xp_ganho": risco.get("xp_ganho", 0),
        "hp_perda": risco.get("hp_perda", 0),
        "explicacao_texto": texto_explicacao(desafio.get("explicacao")),
        "formula": desafio.get("formula", ""),
        "subformulas": desafio.get("subformulas", []),
        "passos_resolucao": desafio.get("passos_resolucao", []),
        "feedback": None if acertou else gerar_feedback_pedagogico(
            dados=desafio,
            materia=(estado.get("config_rpg") or {}).get("materia", "Geral"),
            resposta_aluno=resposta_aluno,
            resposta_correta=resposta_correta,
        ),
    }
    estado["historico"].append(
        {
            "fase": estado.get("fase", 1),
            "acao": f"Desafio: {desafio.get('tema_usado', 'tema')}",
            "rota": (estado.get("ultima_escolha") or {}).get("rota", ""),
            "status": "Acertou" if acertou else "Errou",
            "narracao": desafio.get("pergunta", ""),
            "acertou": acertou,
            "pergunta": desafio.get("pergunta", ""),
            "resposta_aluno": resposta_aluno,
            "resposta_correta": resposta_correta,
            "explicacao": desafio.get("explicacao", ""),
        }
    )

    if estado["hp"] <= 0:
        estado["status"] = "derrota"
        estado["desafio_atual"] = None
    else:
        estado = _avancar_cena(estado, "acertou" if acertou else "errou")

    _salvar_estado_sessao(estado, origem="resposta")
    return redirect(url_for("rpg.tela_rpg"))


@rpg_bp.route("/reiniciar", methods=["POST"])
def reiniciar_rpg():
    estado = _estado_atual()
    if estado:
        _RPG_ESTADOS_LOCAIS.pop(_estado_key(str(session.get("aluno_id") or ""), str(estado.get("aventura_id") or "")), None)
        remover_progresso_rpg(session.get("escola_id", ""), session.get("aluno_id", ""), estado.get("aventura_id", ""))
    return redirect(url_for("rpg.tela_rpg"))


@rpg_bp.route("/pdf")
def baixar_pdf_rpg():
    estado = _estado_atual()
    if not estado:
        return redirect(url_for("rpg.tela_rpg"))
    pdf = gerar_pdf_rpg(
        session.get("aluno_nome", "Aluno"),
        estado.get("titulo", "Aventura RPG"),
        [item for item in estado.get("historico", []) if item.get("pergunta")],
        {"nome": session.get("escola_nome", "EducaGame")},
        estado.get("hp", 0),
        estado.get("xp", 0),
    )
    nome = f"RPG_{str(session.get('aluno_nome') or 'Aluno').replace(' ', '_')}.pdf"
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name=nome)
