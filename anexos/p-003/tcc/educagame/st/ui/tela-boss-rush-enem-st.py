from __future__ import annotations

import time
from html import escape

import streamlit as st

import services.relatorios as report
from services.enem_service import LABEL_AREA, exibir_dificuldade, gerar_questao_enem
from st.ui.mode_common_st import (
    _escapar_moeda_markdown,
    registrar_resposta_modo,
    renderizar_feedback_resposta,
    renderizar_origem_questao,
    renderizar_resolucao_detalhada,
    tempo_decorrido,
)


BOSSES = [
    {
        "nome": "Boss 1 - Linguagens",
        "area": "Linguagens e suas Tecnologias",
        "icone": "Cerebro",
        "hp": 3,
        "vidas": 3,
        "dificuldade": "Medio",
    },
    {
        "nome": "Boss 2 - Matemática",
        "area": "Matematica e suas Tecnologias",
        "icone": "Esquadro",
        "hp": 3,
        "vidas": 3,
        "dificuldade": "Medio",
    },
    {
        "nome": "Boss 3 - Ciências da Natureza",
        "area": "Ciencias da Natureza e suas Tecnologias",
        "icone": "Foguete",
        "hp": 3,
        "vidas": 3,
        "dificuldade": "Medio",
    },
    {
        "nome": "Boss 4 - Ciências Humanas",
        "area": "Ciencias Humanas e Sociais Aplicadas",
        "icone": "Globo",
        "hp": 3,
        "vidas": 3,
        "dificuldade": "Medio",
    },
    {
        "nome": "Boss Final - Mistao ENEM",
        "area": "Misto",
        "icone": "Trofeu",
        "hp": 5,
        "vidas": 4,
        "dificuldade": "Dificil",
    },
]

AREAS_MISTAS = [
    "Linguagens e suas Tecnologias",
    "Matematica e suas Tecnologias",
    "Ciencias da Natureza e suas Tecnologias",
    "Ciencias Humanas e Sociais Aplicadas",
]

LETRAS = ["A", "B", "C", "D", "E"]
COR_ACERTO = "#4ade80"
COR_ERRO = "#fb7185"
COR_GOLD = "#f4c76a"
COR_CYAN = "#67e8f9"


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
        f"color:{cor};border-radius:999px;padding:0.22rem 0.7rem;"
        f"font-size:0.8rem;font-weight:800;'>{_s(texto)}</span>"
    )


def _barra(rotulo: str, atual: int, total: int, cor: str) -> str:
    total = max(1, int(total or 1))
    atual = max(0, min(total, int(atual or 0)))
    pct = int((atual / total) * 100)
    return (
        "<div style='margin:0.45rem 0;'>"
        "<div style='display:flex;justify-content:space-between;color:#cbd5e1;"
        "font-size:0.82rem;font-weight:700;margin-bottom:0.25rem;'>"
        f"<span>{_s(rotulo)}</span><span>{atual}/{total}</span></div>"
        "<div style='height:10px;border-radius:999px;background:rgba(15,23,42,0.9);"
        "border:1px solid rgba(148,163,184,0.16);overflow:hidden;'>"
        f"<div style='height:100%;width:{pct}%;background:{cor};border-radius:999px;'></div>"
        "</div></div>"
    )


def _boss_atual() -> dict:
    return BOSSES[st.session_state.boss_idx]


def _resetar():
    for key in [k for k in st.session_state if k.startswith("boss_")]:
        del st.session_state[key]
    _init_estado()


def _init_estado():
    defaults = {
        "boss_fase": "config",
        "boss_idx": 0,
        "boss_hp": BOSSES[0]["hp"],
        "boss_vidas": BOSSES[0]["vidas"],
        "boss_questao": None,
        "boss_respondida": False,
        "boss_resposta_aluno": "",
        "boss_acertou": None,
        "boss_tempo_inicio": None,
        "boss_historico": [],
        "boss_area_mista_idx": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _iniciar_boss(indice: int):
    boss = BOSSES[indice]
    st.session_state.boss_idx = indice
    st.session_state.boss_hp = boss["hp"]
    st.session_state.boss_vidas = boss["vidas"]
    st.session_state.boss_questao = None
    st.session_state.boss_respondida = False
    st.session_state.boss_resposta_aluno = ""
    st.session_state.boss_acertou = None
    st.session_state.boss_tempo_inicio = None
    st.session_state.boss_fase = "quiz"


def _area_da_questao(boss: dict) -> str:
    if boss["area"] != "Misto":
        return boss["area"]
    area = AREAS_MISTAS[st.session_state.boss_area_mista_idx % len(AREAS_MISTAS)]
    st.session_state.boss_area_mista_idx += 1
    return area


def _carregar_questao():
    if st.session_state.boss_questao is not None:
        return
    boss = _boss_atual()
    area = _area_da_questao(boss)
    with st.spinner(f"Gerando desafio de {LABEL_AREA.get(area, area)}..."):
        questao = gerar_questao_enem(area, boss["dificuldade"])
    st.session_state.boss_questao = questao
    st.session_state.boss_respondida = False
    st.session_state.boss_resposta_aluno = ""
    st.session_state.boss_acertou = None
    st.session_state.boss_tempo_inicio = time.time()


def _registrar_log(aluno: dict, escola: dict, questao: dict, resposta: str, acertou: bool, tempo: float, db):
    area = questao.get("area_bncc", "")
    registrar_resposta_modo(
        db,
        aluno_id=aluno["id"],
        escola_id=escola["id"],
        materia=f"ENEM-{LABEL_AREA.get(area, area)}",
        modo="boss_rush_enem",
        acertou=acertou,
        pergunta_texto=questao.get("pergunta", ""),
        resposta_aluno=resposta,
        resposta_correta=questao.get("correta", ""),
        explicacao_ia=questao.get("explicacao", []),
        tempo_resposta=tempo,
        extras={
            "area_bncc": area,
            "competencia_bncc": questao.get("competencia_bncc", ""),
            "habilidade_bncc": questao.get("habilidade_bncc", ""),
            "matriz_enem": questao.get("matriz_enem", ""),
            "dificuldade": questao.get("dificuldade", ""),
        },
    )


def _render_config():
    st.markdown(
        _card(
            "<div style='color:#67e8f9;font-size:0.78rem;letter-spacing:0.12em;"
            "text-transform:uppercase;font-weight:900;'>Modo desafio</div>"
            "<div style='color:#f8fafc;font-size:2rem;font-weight:900;'>Boss Rush ENEM</div>"
            "<div style='color:#cbd5e1;margin-top:0.35rem;'>"
            "Enfrente chefes por area BNCC. Acertos tiram coracoes do boss; erros tiram suas vidas."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    html_bosses = "".join(
        f"<div style='display:flex;justify-content:space-between;gap:0.8rem;"
        "padding:0.62rem 0;border-bottom:1px solid rgba(148,163,184,0.12);'>"
        f"<span style='color:#f8fafc;font-weight:800;'>{_s(b['nome'])}</span>"
        f"<span style='color:#94a3b8;'>{b['hp']} acertos para vencer</span></div>"
        for b in BOSSES
    )
    st.markdown(_card(html_bosses), unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Iniciar Boss Rush", width="stretch", type="primary"):
            _iniciar_boss(0)
            st.rerun()
    with col2:
        if st.button("Reiniciar progresso", width="stretch"):
            _resetar()
            st.rerun()


def _render_status():
    boss = _boss_atual()
    total_bosses = len(BOSSES)
    area = st.session_state.boss_questao.get("area_bncc", boss["area"]) if st.session_state.boss_questao else boss["area"]
    area_label = "Todas as áreas" if area == "Misto" else LABEL_AREA.get(area, area)
    st.markdown(
        _card(
            "<div style='display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;'>"
            "<div>"
            f"<div style='color:#67e8f9;font-weight:900;font-size:0.78rem;letter-spacing:0.1em;text-transform:uppercase;'>Boss {st.session_state.boss_idx + 1}/{total_bosses}</div>"
            f"<div style='color:#f8fafc;font-weight:900;font-size:1.45rem;'>{_s(boss['nome'])}</div>"
            f"<div style='color:#94a3b8;margin-top:0.2rem;'>{_s(area_label)} | {_s(exibir_dificuldade(boss['dificuldade']))}</div>"
            "</div>"
            "<div style='min-width:260px;flex:1;'>"
            + _barra("Vida do boss", st.session_state.boss_hp, boss["hp"], "linear-gradient(90deg,#fb7185,#f4c76a)")
            + _barra("Suas vidas", st.session_state.boss_vidas, boss["vidas"], "linear-gradient(90deg,#22c55e,#67e8f9)")
            + "</div></div>"
        ),
        unsafe_allow_html=True,
    )


def _render_quiz(aluno: dict, escola: dict, db):
    _carregar_questao()
    boss = _boss_atual()
    q = st.session_state.boss_questao
    correta = q.get("correta", "")
    alternativas = q.get("alternativas", [])

    _render_status()
    renderizar_origem_questao(q)
    st.markdown(
        _card(
            f"<div style='display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.75rem;'>"
            f"{_badge('Questão do boss', COR_CYAN)}"
            f"{_badge(LABEL_AREA.get(q.get('area_bncc', ''), q.get('area_bncc', '')), COR_GOLD)}"
            f"{_badge(q.get('matriz_enem', ''), '#818cf8') if q.get('matriz_enem') else ''}"
            "</div>"
            f"<div style='color:#f8fafc;font-size:1.04rem;line-height:1.65;font-weight:600;'>{_s(q.get('pergunta', ''))}</div>"
        ),
        unsafe_allow_html=True,
    )

    if not st.session_state.boss_respondida:
        for i, alt in enumerate(alternativas):
            letra = LETRAS[i] if i < len(LETRAS) else str(i + 1)
            label = f"**{letra})** {_escapar_moeda_markdown(alt)}"
            if st.button(label, key=f"boss_alt_{st.session_state.boss_idx}_{len(st.session_state.boss_historico)}_{i}", width="stretch"):
                acertou = alt == correta
                tempo = round(tempo_decorrido(st.session_state.boss_tempo_inicio), 2)
                st.session_state.boss_respondida = True
                st.session_state.boss_resposta_aluno = alt
                st.session_state.boss_acertou = acertou
                if acertou:
                    st.session_state.boss_hp = max(0, st.session_state.boss_hp - 1)
                else:
                    st.session_state.boss_vidas = max(0, st.session_state.boss_vidas - 1)

                _registrar_log(aluno, escola, q, alt, acertou, tempo, db)
                st.session_state.boss_historico.append({
                    "boss": boss["nome"],
                    "area": q.get("area_bncc", ""),
                    "area_label": LABEL_AREA.get(q.get("area_bncc", ""), q.get("area_bncc", "")),
                    "matriz_enem": q.get("matriz_enem", ""),
                    "dificuldade": q.get("dificuldade", ""),
                    "pergunta": q.get("pergunta", ""),
                    "resposta_aluno": alt,
                    "correta": correta,
                    "acertou": acertou,
                    "tempo": tempo,
                    "explicacao": q.get("explicacao", []),
                })
                st.rerun()
        return

    resposta = st.session_state.boss_resposta_aluno
    acertou = bool(st.session_state.boss_acertou)
    for i, alt in enumerate(alternativas):
        letra = LETRAS[i] if i < len(LETRAS) else str(i + 1)
        is_correta = alt == correta
        is_escolhida = alt == resposta
        cor = COR_ACERTO if is_correta else COR_ERRO if is_escolhida else "#64748b"
        marcador = "OK" if is_correta else "X" if is_escolhida else "-"
        st.markdown(
            f"<div style='border:1px solid {cor}66;border-radius:12px;padding:0.7rem 1rem;"
            f"margin-bottom:0.45rem;background:rgba(10,19,34,0.62);color:{cor};'>"
            f"<b>{marcador} {letra})</b> {_s(alt)}</div>",
            unsafe_allow_html=True,
        )

    renderizar_feedback_resposta(
        acertou,
        correta,
        "Acertou! O boss perdeu 1 coração.",
        "Errou. Você perdeu 1 vida. Resposta correta:",
    )
    if q.get("explicacao"):
        with st.expander("Ver explicação", expanded=True):
            renderizar_resolucao_detalhada({"explicacao": q.get("explicacao", [])})

    acabou_boss = st.session_state.boss_hp <= 0 or st.session_state.boss_vidas <= 0
    if acabou_boss:
        if st.button("Ver resultado do boss", width="stretch", type="primary"):
            st.session_state.boss_fase = "boss_result"
            st.rerun()
    else:
        if st.button("Próxima questão do boss", width="stretch", type="primary"):
            st.session_state.boss_questao = None
            st.session_state.boss_respondida = False
            st.rerun()

    if st.button("Abandonar Boss Rush", width="stretch"):
        _resetar()
        st.rerun()


def _render_boss_result():
    boss = _boss_atual()
    venceu = st.session_state.boss_hp <= 0
    if venceu:
        titulo = f"{boss['nome']} derrotado"
        texto = "Boa. Você venceu este chefe e liberou o próximo desafio."
        cor = COR_ACERTO
    else:
        titulo = "Boss Rush encerrado"
        texto = "Suas vidas acabaram. Revise as explicações e tente novamente."
        cor = COR_ERRO

    st.markdown(
        _card(
            f"<div style='color:{cor};font-weight:900;font-size:1.6rem;'>{_s(titulo)}</div>"
            f"<div style='color:#cbd5e1;margin-top:0.35rem;'>{_s(texto)}</div>"
        ),
        unsafe_allow_html=True,
    )

    if venceu and st.session_state.boss_idx + 1 < len(BOSSES):
        if st.button("Enfrentar próximo boss", width="stretch", type="primary"):
            _iniciar_boss(st.session_state.boss_idx + 1)
            st.rerun()
    elif venceu:
        st.session_state.boss_fase = "resultado"
        st.rerun()
    else:
        if st.button("Tentar novamente", width="stretch", type="primary"):
            _resetar()
            st.rerun()


def _render_resultado_final(aluno: dict, escola: dict):
    historico = st.session_state.boss_historico
    total = len(historico)
    acertos = sum(1 for item in historico if item.get("acertou"))
    pct = int(acertos / total * 100) if total else 0
    st.markdown(
        _card(
            "<div style='color:#f4c76a;font-size:0.78rem;letter-spacing:0.12em;"
            "text-transform:uppercase;font-weight:900;'>Boss final vencido</div>"
            "<div style='color:#f8fafc;font-size:2rem;font-weight:900;'>Campeao do Boss Rush ENEM</div>"
            f"<div style='color:#cbd5e1;margin-top:0.35rem;'>Acertos: {acertos}/{total} ({pct}%).</div>"
        ),
        unsafe_allow_html=True,
    )

    por_boss: dict[str, list[dict]] = {}
    for item in historico:
        por_boss.setdefault(item["boss"], []).append(item)
    for boss_nome, itens in por_boss.items():
        acertos_boss = sum(1 for item in itens if item.get("acertou"))
        st.markdown(
            _card(
                f"<div style='color:#f8fafc;font-weight:900;'>{_s(boss_nome)}</div>"
                f"<div style='color:#94a3b8;'>{acertos_boss}/{len(itens)} acertos</div>"
            ),
            unsafe_allow_html=True,
        )

    try:
        pdf_bytes = report.gerar_pdf_boss_rush(
            nome_aluno=aluno.get("nome", "Aluno"),
            historico=historico,
            dados_escola=escola,
        )
        st.download_button(
            "Baixar relatório do Boss Rush (PDF)",
            data=pdf_bytes,
            file_name=f"Boss_Rush_{aluno.get('nome', 'Aluno').replace(' ', '_')}.pdf",
            mime="application/pdf",
            width="stretch",
        )
    except Exception as e:
        st.warning(f"PDF indisponivel: {e}")

    if st.button("Jogar Boss Rush novamente", width="stretch", type="primary"):
        _resetar()
        st.rerun()


def renderizar_tela_boss_rush_enem(aluno: dict, escola: dict, db):
    _init_estado()
    fase = st.session_state.boss_fase
    if fase == "config":
        _render_config()
    elif fase == "quiz":
        _render_quiz(aluno, escola, db)
    elif fase == "boss_result":
        _render_boss_result()
    else:
        _render_resultado_final(aluno, escola)
