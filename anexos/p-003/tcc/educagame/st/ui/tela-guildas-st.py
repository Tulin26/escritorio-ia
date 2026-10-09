from __future__ import annotations

from html import escape

import streamlit as st

import services.relatorios as report
# MELHORIA: a tela tinha COPIA PROPRIA do placar -- _montar_guildas (68
# linhas), _parse_data e _inicio_semana, mais o fuso. Comparadas linha a
# linha com o servico, eram identicas: so mudavam o underscore do nome e a
# formatacao das chaves.
#
# Identicas era a hora certa de juntar. Depois que divergem, alguem precisa
# decidir qual esta certa -- e o placar decide quem ganha a semana, entao
# duas contas diferentes para a mesma turma nos dois frontends seria uma
# discussao sem resposta. Este projeto ja pagou isso duas vezes: "esta serie
# e de Ensino Medio?" em cinco lugares, e o nome da guilda logo aqui.
from services.escola_service import AVISO_GUILDAS_DESLIGADAS, mostra_guildas
from services.guildas_service import montar_guildas


COR_ACERTO = "#4ade80"
COR_GOLD = "#f4c76a"
COR_CYAN = "#67e8f9"
COR_ROSE = "#fb7185"


def _s(texto) -> str:
    return escape(str(texto or ""))


def _card(conteudo: str) -> str:
    return (
        "<div style='background:rgba(10,19,34,0.88);"
        "border:1px solid rgba(148,163,184,0.18);border-radius:18px;"
        "padding:1rem 1.1rem;margin:0.75rem 0;'>"
        f"{conteudo}</div>"
    )


def _badge(texto: str, cor: str = COR_GOLD) -> str:
    return (
        f"<span style='background:rgba(0,0,0,0.26);border:1px solid {cor}55;"
        f"color:{cor};border-radius:999px;padding:0.2rem 0.65rem;"
        f"font-size:0.78rem;font-weight:850;'>{_s(texto)}</span>"
    )


def _render_tabela_guildas(guildas: list[dict]):
    linhas = []
    for idx, guilda in enumerate(guildas, start=1):
        medalha = "1o" if idx == 1 else "2o" if idx == 2 else "3o" if idx == 3 else f"{idx}o"
        linhas.append(
            "<div style='display:grid;grid-template-columns:0.35fr 1.5fr 0.75fr 0.75fr 0.75fr;"
            "gap:0.7rem;align-items:center;padding:0.72rem 0;border-bottom:1px solid rgba(148,163,184,0.12);'>"
            f"<div style='color:{COR_GOLD};font-weight:900;'>{medalha}</div>"
            f"<div><div style='color:#f8fafc;font-weight:900;'>{_s(guilda['guilda'])}</div>"
            f"<div style='color:#94a3b8;font-size:0.84rem;'>{guilda['alunos']} alunos | {guilda['participantes_semana']} participaram</div></div>"
            f"<div style='color:#f8fafc;font-weight:900;'>{guilda['pontos_semana']} pts</div>"
            f"<div style='color:{COR_ACERTO};font-weight:900;'>{guilda['acertos_semana']} acertos</div>"
            f"<div style='color:#cbd5e1;font-weight:900;'>{guilda['taxa_acerto']}%</div>"
            "</div>"
        )
    st.markdown(
        _card(
            "<div style='color:#67e8f9;font-weight:900;font-size:0.78rem;letter-spacing:0.1em;text-transform:uppercase;'>Batalha semanal</div>"
            "<div style='color:#f8fafc;font-size:1.35rem;font-weight:900;margin-bottom:0.35rem;'>Ranking por guilda</div>"
            + "".join(linhas)
        ),
        unsafe_allow_html=True,
    )


def _render_duelos(guildas: list[dict]):
    if len(guildas) < 2:
        st.info("Cadastre alunos em pelo menos duas turmas para formar duelos.")
        return

    pares = []
    for i in range(0, len(guildas) - 1, 2):
        pares.append((guildas[i], guildas[i + 1]))

    cards = []
    for a, b in pares[:3]:
        diff = abs(a["pontos_semana"] - b["pontos_semana"])
        lider = a if a["pontos_semana"] >= b["pontos_semana"] else b
        cards.append(
            "<div style='border:1px solid rgba(148,163,184,0.14);border-radius:14px;"
            "padding:0.85rem;background:rgba(15,23,42,0.55);'>"
            f"<div style='color:#f8fafc;font-weight:900;'>{_s(a['guilda'])} vs {_s(b['guilda'])}</div>"
            f"<div style='display:flex;gap:0.45rem;flex-wrap:wrap;margin-top:0.55rem;'>"
            f"{_badge(str(a['pontos_semana']) + ' pts', COR_CYAN)}"
            f"{_badge(str(b['pontos_semana']) + ' pts', COR_GOLD)}"
            f"{_badge('lider: ' + lider['guilda'], COR_ACERTO)}"
            f"{_badge('dif: ' + str(diff), COR_ROSE if diff <= 10 else '#94a3b8')}"
            "</div></div>"
        )

    st.markdown(
        _card(
            "<div style='color:#67e8f9;font-weight:900;font-size:0.78rem;letter-spacing:0.1em;text-transform:uppercase;'>Duelos ativos</div>"
            "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:0.75rem;margin-top:0.75rem;'>"
            + "".join(cards)
            + "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_regras():
    st.markdown(
        _card(
            "<div style='color:#f8fafc;font-size:1.2rem;font-weight:900;'>Regras da semana</div>"
            "<div style='display:grid;gap:0.45rem;margin-top:0.7rem;color:#cbd5e1;'>"
            "<div>⚔️ Cada turma vira uma guilda: série + período.</div>"
            "<div>🏆 Acerto vale 10 pontos semanais.</div>"
            "<div>🔥 Cada participante ativo adiciona +5 pontos de bônus.</div>"
            "<div>🛡️ Erro desconta só 1 ponto, para não desmotivar.</div>"
            "<div>📅 O placar semanal considera os logs desde segunda-feira.</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def renderizar_tela_guildas(escola_id, db_repo, dados_escola):
    # MELHORIA: a tela desenhava o placar mesmo com modo_guilda desligado na
    # escola (RF14). A navegacao ja recusa a pagina (_pagina_permitida em
    # st/ui/home_st.py); esta e a segunda tranca, no ponto onde o placar e
    # montado -- e antes das consultas, para nao ler a turma a toa.
    # `dados_escola` e obrigatorio: sem ele a tela nao tem como saber a regra.
    if not mostra_guildas(dados_escola):
        st.info(AVISO_GUILDAS_DESLIGADAS)
        return

    alunos = db_repo.buscar_alunos(escola_id)
    logs = db_repo.buscar_logs(escola_id)
    guildas = montar_guildas(alunos, logs)

    st.markdown(
        _card(
            "<div style='color:#67e8f9;font-size:0.78rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:900;'>Modo coletivo</div>"
            "<div style='color:#f8fafc;font-size:2rem;font-weight:900;'>Duelo de Guildas</div>"
            "<div style='color:#cbd5e1;margin-top:0.35rem;'>"
            "Turmas competem por engajamento, acertos e participacao semanal."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if not guildas:
        st.info("Ainda não há alunos para montar guildas.")
        return

    col1, col2, col3 = st.columns(3)
    lider = guildas[0]
    col1.metric("Guildas", len(guildas))
    col2.metric("Lider semanal", lider["guilda"])
    col3.metric("Pontos do lider", lider["pontos_semana"])

    try:
        nome_escola = "EduGame"
        escola = st.session_state.get("escola")
        if isinstance(escola, dict):
            nome_escola = escola.get("nome", nome_escola)
        pdf_bytes = report.gerar_pdf_guildas(nome_escola, guildas)
        st.download_button(
            "Baixar relatório das Guildas (PDF)",
            data=pdf_bytes,
            file_name=f"Guildas_{str(nome_escola).replace(' ', '_')}.pdf",
            mime="application/pdf",
            width="stretch",
        )
    except Exception as e:
        st.warning(f"PDF indisponivel: {e}")

    _render_duelos(guildas)
    _render_tabela_guildas(guildas)
    _render_regras()
