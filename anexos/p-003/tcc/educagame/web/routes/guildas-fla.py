from __future__ import annotations

import io

from flask import Blueprint, redirect, render_template, send_file, session, url_for

from services.dados_service import buscar_alunos, buscar_logs
from services.escola_service import AVISO_GUILDAS_DESLIGADAS, escola_atualizada, mostra_guildas
from services.guildas_service import montar_guildas
from services.relatorios import gerar_pdf_guildas

guildas_bp = Blueprint("guildas", __name__)


@guildas_bp.before_request
def exigir_modo_guilda():
    # MELHORIA: a Batalha de Guildas abria mesmo com modo_guilda desligado na
    # escola (RF14). Esconder o card da home nao basta: a URL continua sendo
    # porta, e "/guildas/pdf" entregaria o placar inteiro em PDF. A tranca
    # fica no blueprint para valer nas duas rotas de uma vez, como a do
    # painel do professor.
    #
    # Responde com a tela explicando, e nao com redirect: quem chega por um
    # link antigo precisa saber que a disputa foi desligada, senao so ve a
    # home aparecer sem motivo.
    if mostra_guildas(escola_atualizada(session.get("escola_id"))):
        return None
    return render_template(
        "guildas.html",
        desligada=True,
        aviso=AVISO_GUILDAS_DESLIGADAS,
        guildas=[],
        lider={},
        duelos=[],
        escola_nome=session.get("escola_nome", "EducaGame"),
    )


def _guildas_atuais() -> list[dict]:
    escola_id = session.get("escola_id")
    if not escola_id:
        return []
    return montar_guildas(buscar_alunos(escola_id), buscar_logs(escola_id))


@guildas_bp.route("/")
def tela_guildas():
    guildas = _guildas_atuais()
    lider = guildas[0] if guildas else {}
    duelos = []
    for idx in range(0, len(guildas) - 1, 2):
        a = guildas[idx]
        b = guildas[idx + 1]
        lider_duelo = a if a["pontos_semana"] >= b["pontos_semana"] else b
        duelos.append({"a": a, "b": b, "lider": lider_duelo, "diferenca": abs(a["pontos_semana"] - b["pontos_semana"])})
    return render_template(
        "guildas.html",
        guildas=guildas,
        lider=lider,
        duelos=duelos[:3],
        escola_nome=session.get("escola_nome", "EducaGame"),
    )


@guildas_bp.route("/pdf")
def baixar_pdf_guildas():
    guildas = _guildas_atuais()
    if not guildas:
        return redirect(url_for("guildas.tela_guildas"))
    escola_nome = session.get("escola_nome", "EducaGame")
    pdf = gerar_pdf_guildas(escola_nome, guildas)
    nome = f"Guildas_{str(escola_nome).replace(' ', '_')}.pdf"
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True, download_name=nome)


