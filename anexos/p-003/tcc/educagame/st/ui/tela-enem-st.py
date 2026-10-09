"""
Tela do Modo ENEM – EduGame Salesiano

Como usar em app.py:
    from st.ui.tela_enem_st import tela_enem
    # no roteador de telas:
    tela_enem(aluno=al_obj, escola=dados_escola, db=db)
"""
from __future__ import annotations

import time
from html import escape

import streamlit as st

from services.enem_service import (
    AREAS_ENEM,
    DIFICULDADES,
    LABEL_AREA,
    gerar_questao_enem,
    exibir_dificuldade,
    inferir_dificuldade_aluno,
    montar_sequencia_questoes,
)
from services.relatorios import gerar_pdf_enem
from st.ui.mode_common_st import (
    _escapar_moeda_markdown,
    registrar_resposta_modo,
    renderizar_feedback_resposta,
    renderizar_origem_questao,
    renderizar_resolucao_detalhada,
    tempo_decorrido,
)

# ── Constantes ────────────────────────────────────────────────────────────────

LETRAS = ["A", "B", "C", "D", "E"]
COR_ACERTO = "#4ade80"
COR_ERRO = "#fb7185"
COR_GOLD = "#f4c76a"
COR_CYAN = "#67e8f9"
TEMPO_LIMITE_QUESTAO = 180


# ── Helpers de HTML ───────────────────────────────────────────────────────────

def _s(texto) -> str:
    return escape(str(texto or ""))


def _card(conteudo: str, classe: str = "") -> str:
    return (
        f"<div style='"
        f"background:rgba(10,19,34,0.88);border:1px solid rgba(148,163,184,0.18);"
        f"border-radius:18px;padding:1.2rem 1.4rem;margin-bottom:0.8rem;{classe}'>"
        f"{conteudo}</div>"
    )


def _badge(texto: str, cor: str = COR_GOLD) -> str:
    return (
        f"<span style='background:rgba(0,0,0,0.3);border:1px solid {cor}44;"
        f"color:{cor};border-radius:999px;padding:0.2rem 0.7rem;"
        f"font-size:0.78rem;font-weight:700;'>{_s(texto)}</span>"
    )


def _progresso_bar(atual: int, total: int) -> str:
    pct = int(atual / total * 100) if total else 0
    return (
        f"<div style='margin:0.5rem 0;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;"
        f"color:#94a3b8;margin-bottom:4px;'>"
        f"<span>Questão {atual} de {total}</span><span>{pct}%</span></div>"
        f"<div style='height:8px;border-radius:999px;background:rgba(18,32,53,0.9);"
        f"border:1px solid rgba(148,163,184,0.14);overflow:hidden;'>"
        f"<div style='height:100%;width:{pct}%;border-radius:999px;"
        f"background:linear-gradient(90deg,{COR_GOLD},{COR_CYAN});'></div>"
        f"</div></div>"
    )


def _formatar_tempo(segundos: int) -> str:
    segundos = max(0, int(segundos))
    return f"{segundos // 60:02d}:{segundos % 60:02d}"


def _timer_card(restante: int, expirado: bool) -> str:
    cor = COR_ERRO if expirado or restante <= 30 else COR_CYAN
    texto = "Tempo esgotado" if expirado else f"Tempo restante: {_formatar_tempo(restante)}"
    return (
        "<div style='display:flex;justify-content:flex-end;margin:-0.2rem 0 0.75rem;'>"
        f"<span style='border:1px solid {cor}66;color:{cor};background:rgba(0,0,0,0.26);"
        "border-radius:999px;padding:0.28rem 0.78rem;font-weight:900;font-size:0.86rem;'>"
        f"{_s(texto)}</span></div>"
    )


# ── Estado de sessão ──────────────────────────────────────────────────────────

def _init_estado():
    defaults = {
        "enem_fase": "config",          # config | quiz | resultado
        "enem_sequencia": [],           # list[tuple[area, dificuldade]]
        "enem_idx": 0,                  # índice da questão atual
        "enem_questao_atual": None,     # dict da questão
        "enem_respondida": False,       # já respondeu esta questão
        "enem_resposta_aluno": None,    # texto escolhido
        "enem_acertou": None,           # bool
        "enem_historico": [],           # list[dict] — todas as questões respondidas
        "enem_tempo_inicio": None,      # float — timestamp do início da questão
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _resetar():
    keys = [k for k in st.session_state if k.startswith("enem_")]
    for k in keys:
        del st.session_state[k]
    _init_estado()


# ── Tela de configuração ──────────────────────────────────────────────────────

def _tela_config(logs_aluno: list | None = None):
    st.markdown(
        f"<div style='text-align:center;margin-bottom:1.5rem;'>"
        f"<div style='font-size:0.78rem;letter-spacing:0.12em;text-transform:uppercase;"
        f"color:{COR_CYAN};font-weight:700;margin-bottom:0.4rem;'>Modo Simulado</div>"
        f"<h2 style='margin:0;font-size:2rem;font-weight:800;color:#f8fafc;'>🎓 Simulado ENEM</h2>"
        f"<p style='color:#94a3b8;margin-top:0.4rem;'>Configure seu simulado e teste seus conhecimentos</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        modo_areas = st.radio(
            "Áreas do conhecimento",
            ["Todas as áreas (aleatório)", "Escolher áreas específicas"],
            key="enem_cfg_modo_areas",
        )

        areas_escolhidas = list(AREAS_ENEM.keys())
        if modo_areas == "Escolher áreas específicas":
            areas_escolhidas = st.multiselect(
                "Selecione as áreas",
                options=list(AREAS_ENEM.keys()),
                format_func=lambda a: LABEL_AREA.get(a, a),
                default=list(AREAS_ENEM.keys()),
                key="enem_cfg_areas",
            )
            if not areas_escolhidas:
                st.warning("Selecione ao menos uma área.")
                return

    with col2:
        total_questoes = st.select_slider(
            "Número de questões",
            options=[5, 10, 15, 20, 30],
            value=10,
            key="enem_cfg_total",
        )
        # MELHORIA: dificuldade sugerida com base no desempenho recente do aluno
        dificuldade_sugerida = inferir_dificuldade_aluno(logs_aluno or [])
        idx_sugerido = DIFICULDADES.index(dificuldade_sugerida) if dificuldade_sugerida in DIFICULDADES else 1
        dificuldade = st.selectbox(
            "Nível de dificuldade",
            DIFICULDADES,
            format_func=exibir_dificuldade,
            index=idx_sugerido,
            key="enem_cfg_dificuldade",
            help=f"Sugerido com base no seu histórico: **{exibir_dificuldade(dificuldade_sugerida)}**",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Prévia da distribuição
    if areas_escolhidas:
        por_area = {a: 0 for a in areas_escolhidas}
        for i in range(total_questoes):
            por_area[areas_escolhidas[i % len(areas_escolhidas)]] += 1

        st.markdown(
            f"<div style='font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem;font-weight:600;'>"
            f"Distribuição de questões:</div>",
            unsafe_allow_html=True,
        )
        partes = " &nbsp;|&nbsp; ".join(
            f"<span style='color:{COR_GOLD};'>{_s(LABEL_AREA.get(a, a))}</span> "
            f"<span style='color:#cbd5e1;'>({n})</span>"
            for a, n in por_area.items()
        )
        st.markdown(
            f"<div style='font-size:0.85rem;color:#94a3b8;margin-bottom:1.2rem;'>{partes}</div>",
            unsafe_allow_html=True,
        )

    if st.button("🚀 Iniciar Simulado", width="stretch", type="primary"):
        sequencia = montar_sequencia_questoes(areas_escolhidas, total_questoes, dificuldade)
        st.session_state.enem_sequencia = sequencia
        st.session_state.enem_fase = "quiz"
        st.session_state.enem_idx = 0
        st.session_state.enem_historico = []
        st.session_state.enem_questao_atual = None
        st.session_state.enem_respondida = False
        st.rerun()


# ── Tela de quiz ──────────────────────────────────────────────────────────────

# MELHORIA: _tela_quiz tinha 189 linhas, e dentro delas o MESMO dicionario
# de historico era montado DUAS vezes -- 12 chaves, uma no caminho do tempo
# esgotado e outra no da resposta clicada. Duas copias que precisam ficar
# iguais para o boletim do simulado sair certo: se uma ganhar campo e a
# outra nao, o relatorio quebra so para quem estourou o tempo.
def item_do_historico(numero, questao, area_label, resposta_aluno, acertou, tempo) -> dict:
    """Uma linha do historico do simulado -- o que o PDF do ENEM le depois."""
    return {
        "numero": numero,
        "area": questao.get("area_bncc", ""),
        "area_label": area_label,
        "dificuldade": questao.get("dificuldade", ""),
        "pergunta": questao.get("pergunta", ""),
        "alternativas": questao.get("alternativas", []),
        "correta": questao.get("correta", ""),
        "resposta_aluno": resposta_aluno,
        "acertou": acertou,
        "explicacao": questao.get("explicacao", []),
        "matriz_enem": questao.get("matriz_enem", ""),
        "tempo": tempo,
    }


def estado_do_cronometro(inicio, agora) -> tuple[float, int, bool]:
    """(decorrido, restante em segundos, estourou?).

    O agora entra por parametro porque a tela chamava time.time() DUAS vezes
    em duas linhas seguidas: o decorrido e o restante podiam sair de
    instantes diferentes. Diferenca minuscula, mas sem motivo -- e assim o
    cronometro fica conferivel sem esperar o relogio andar.
    """
    inicio = inicio or agora
    decorrido = agora - inicio
    restante = max(0, int(TEMPO_LIMITE_QUESTAO - decorrido))
    return decorrido, restante, decorrido >= TEMPO_LIMITE_QUESTAO


def estilo_da_alternativa(alternativa, correta, resposta_aluno) -> tuple[str, str, str]:
    """(cor da borda, icone, cor do texto) no gabarito.

    A correta sempre aparece marcada, tenha o aluno escolhido ela ou nao --
    e o que transforma a tela de resultado em correcao.
    """
    is_correta = alternativa == correta
    is_escolhida = alternativa == resposta_aluno
    if is_correta:
        cor_borda = COR_ACERTO
        icone = "✅"
        cor_texto = COR_ACERTO
    elif is_escolhida and not is_correta:
        cor_borda = COR_ERRO
        icone = "❌"
        cor_texto = COR_ERRO
    else:
        cor_borda = "rgba(148,163,184,0.14)"
        icone = "○"
        cor_texto = "#64748b"

    return cor_borda, icone, cor_texto


def _tela_quiz(aluno: dict, escola: dict, db):
    sequencia = st.session_state.enem_sequencia
    idx = st.session_state.enem_idx
    total = len(sequencia)

    # Carrega questão se necessário
    _carregar_questao_se_preciso(sequencia, idx)

    q = st.session_state.enem_questao_atual
    area_label = LABEL_AREA.get(q.get("area_bncc", ""), q.get("area_bncc", ""))
    tempo_decorrido_atual, tempo_restante, tempo_expirado = estado_do_cronometro(
        st.session_state.enem_tempo_inicio, time.time()
    )

    st.markdown(_progresso_bar(idx + 1, total), unsafe_allow_html=True)
    st.markdown(_timer_card(tempo_restante, tempo_expirado), unsafe_allow_html=True)

    renderizar_origem_questao(q)

    # Header da questão
    st.markdown(
        f"<div style='display:flex;gap:0.6rem;align-items:center;margin-bottom:0.8rem;flex-wrap:wrap;'>"
        f"{_badge(f'Questão {idx + 1}', COR_CYAN)}"
        f"{_badge(area_label, COR_GOLD)}"
        f"{_badge(q.get('dificuldade', ''), '#94a3b8')}"
        f"{_badge(q.get('matriz_enem', ''), '#818cf8') if q.get('matriz_enem') else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Enunciado
    st.markdown(
        _card(
            f"<div style='color:#f8fafc;font-size:1.05rem;line-height:1.7;font-weight:500;'>"
            f"{_s(q.get('pergunta', ''))}</div>"
        ),
        unsafe_allow_html=True,
    )

    # Alternativas
    alternativas = q.get("alternativas", [])
    correta = q.get("correta", "")
    respondida = st.session_state.enem_respondida

    if tempo_expirado and not respondida:
        tempo = round(tempo_decorrido_atual, 2)
        st.session_state.enem_respondida = True
        st.session_state.enem_resposta_aluno = "Tempo esgotado"
        st.session_state.enem_acertou = False
        _registrar_log_enem(
            aluno=aluno,
            escola=escola,
            questao=q,
            resposta_aluno="Tempo esgotado",
            acertou=False,
            tempo=tempo,
            db=db,
        )
        st.session_state.enem_historico.append(
            item_do_historico(idx + 1, q, area_label, "Tempo esgotado", False, tempo)
        )
        st.rerun()

    if not respondida:
        for i, alt in enumerate(alternativas):
            letra = LETRAS[i] if i < len(LETRAS) else str(i + 1)
            if st.button(
                f"**{letra})** {_escapar_moeda_markdown(alt)}",
                key=f"enem_alt_{idx}_{i}",
                width="stretch",
            ):
                tempo = round(tempo_decorrido(st.session_state.enem_tempo_inicio), 2)
                acertou = alt == correta
                st.session_state.enem_respondida = True
                st.session_state.enem_resposta_aluno = alt
                st.session_state.enem_acertou = acertou

                # Registra log
                _registrar_log_enem(
                    aluno=aluno,
                    escola=escola,
                    questao=q,
                    resposta_aluno=alt,
                    acertou=acertou,
                    tempo=tempo,
                    db=db,
                )

                st.session_state.enem_historico.append(
                    item_do_historico(idx + 1, q, area_label, alt, acertou, tempo)
                )

                st.rerun()
        if not tempo_expirado:
            time.sleep(1)
            st.rerun()
    else:
        _gabarito_da_questao(q, alternativas, correta, idx, total)

    # Botão abandonar (discreto)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↩ Abandonar simulado", key="enem_abandonar"):
        _resetar()
        st.rerun()


# ── Tela de resultado ─────────────────────────────────────────────────────────

def _tela_resultado(aluno: dict, escola: dict, db):
    historico = st.session_state.enem_historico
    total = len(historico)
    acertos = sum(1 for q in historico if q["acertou"])
    pct = int(acertos / total * 100) if total else 0

    # Cor do resultado
    cor_pct = COR_ACERTO if pct >= 60 else COR_GOLD if pct >= 40 else COR_ERRO

    st.markdown(
        f"<div style='text-align:center;margin-bottom:1.5rem;'>"
        f"<h2 style='font-size:2rem;font-weight:800;color:#f8fafc;margin:0;'>🎓 Resultado do Simulado</h2>"
        f"<p style='color:#94a3b8;margin:0.4rem 0 0;'>Veja como você se saiu em cada área</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Card de nota geral
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            _card(
                f"<div style='color:#94a3b8;font-size:0.74rem;text-transform:uppercase;"
                f"letter-spacing:0.08em;font-weight:700;margin-bottom:0.3rem;'>Acertos</div>"
                f"<div style='color:#f8fafc;font-size:1.8rem;font-weight:800;'>{acertos}/{total}</div>"
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _card(
                f"<div style='color:#94a3b8;font-size:0.74rem;text-transform:uppercase;"
                f"letter-spacing:0.08em;font-weight:700;margin-bottom:0.3rem;'>Aproveitamento</div>"
                f"<div style='color:{cor_pct};font-size:1.8rem;font-weight:800;'>{pct}%</div>"
            ),
            unsafe_allow_html=True,
        )
    with col3:
        tempo_total = round(sum(q.get("tempo", 0) for q in historico), 1)
        tempo_medio = round(tempo_total / total, 1) if total else 0
        st.markdown(
            _card(
                f"<div style='color:#94a3b8;font-size:0.74rem;text-transform:uppercase;"
                f"letter-spacing:0.08em;font-weight:700;margin-bottom:0.3rem;'>Tempo médio</div>"
                f"<div style='color:#f8fafc;font-size:1.8rem;font-weight:800;'>{tempo_medio}s</div>"
            ),
            unsafe_allow_html=True,
        )

    # Desempenho por área
    st.markdown(
        f"<h3 style='color:#f8fafc;font-size:1.1rem;font-weight:800;margin:1.2rem 0 0.6rem;'>"
        f"📊 Desempenho por Área</h3>",
        unsafe_allow_html=True,
    )

    areas_stats: dict[str, dict] = {}
    for q in historico:
        a = q["area_label"]
        if a not in areas_stats:
            areas_stats[a] = {"total": 0, "acertos": 0}
        areas_stats[a]["total"] += 1
        if q["acertou"]:
            areas_stats[a]["acertos"] += 1

    for area, stats in areas_stats.items():
        t = stats["total"]
        ac = stats["acertos"]
        p = int(ac / t * 100) if t else 0
        cor = COR_ACERTO if p >= 60 else COR_GOLD if p >= 40 else COR_ERRO
        st.markdown(
            f"<div style='margin-bottom:0.5rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.85rem;"
            f"color:#cbd5e1;margin-bottom:3px;'>"
            f"<span>{_s(area)}</span><span style='color:{cor};font-weight:700;'>{ac}/{t} ({p}%)</span></div>"
            f"<div style='height:7px;border-radius:999px;background:rgba(18,32,53,0.9);overflow:hidden;'>"
            f"<div style='height:100%;width:{p}%;border-radius:999px;background:{cor};'></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # Questões erradas
    erradas = [q for q in historico if not q["acertou"]]
    if erradas:
        st.markdown(
            f"<h3 style='color:#f8fafc;font-size:1.1rem;font-weight:800;margin:1.4rem 0 0.6rem;'>"
            f"❌ Questões para Revisar ({len(erradas)})</h3>",
            unsafe_allow_html=True,
        )
        for q in erradas:
            with st.expander(
                f"Q{q['numero']} · {q['area_label']} · {q['pergunta'][:70]}...",
                expanded=False,
            ):
                st.markdown(f"**Pergunta:** {_escapar_moeda_markdown(q['pergunta'])}")
                st.markdown(f"**Sua resposta:** :red[{_escapar_moeda_markdown(q['resposta_aluno'])}]")
                st.markdown(f"**Resposta correta:** :green[{_escapar_moeda_markdown(q['correta'])}]")
                if q.get("explicacao"):
                    st.markdown("**Explicação:**")
                    for bloco in q["explicacao"]:
                        tipo = bloco.get("tipo", "texto")
                        conteudo = bloco.get("conteudo", "")
                        if tipo == "bold":
                            st.markdown(f"**{_escapar_moeda_markdown(conteudo)}**")
                        elif tipo == "resultado":
                            st.info(_escapar_moeda_markdown(conteudo))
                        else:
                            st.markdown(_escapar_moeda_markdown(conteudo))

    # Botão PDF
    st.markdown("<br>", unsafe_allow_html=True)
    col_pdf, col_novo = st.columns(2)
    with col_pdf:
        try:
            pdf_bytes = gerar_pdf_enem(
                nome_aluno=aluno.get("nome", "Aluno"),
                historico=historico,
                dados_escola=escola,
                acertos=acertos,
                total=total,
            )
            st.download_button(
                "📄 Baixar relatório PDF",
                data=pdf_bytes,
                file_name=f"enem_{aluno.get('nome','aluno').replace(' ','_')}.pdf",
                mime="application/pdf",
                width="stretch",
            )
        except Exception as e:
            st.warning(f"PDF não disponível: {e}")

    with col_novo:
        if st.button("🔄 Novo Simulado", width="stretch"):
            _resetar()
            st.rerun()


# ── Log ───────────────────────────────────────────────────────────────────────

def _registrar_log_enem(
    aluno: dict,
    escola: dict,
    questao: dict,
    resposta_aluno: str,
    acertou: bool,
    tempo: float,
    db,
):
    try:
        registrar_resposta_modo(
            db,
            aluno_id=aluno.get("id"),
            escola_id=escola.get("id"),
            materia=f"ENEM-{questao.get('area_bncc', '')}",
            modo="enem",
            acertou=acertou,
            pergunta_texto=questao.get("pergunta", ""),
            resposta_aluno=resposta_aluno,
            resposta_correta=questao.get("correta", ""),
            explicacao_ia=questao.get("explicacao", ""),
            tempo_resposta=tempo,
            extras={
                "area_bncc": questao.get("area_bncc", ""),
                "competencia_bncc": questao.get("competencia_bncc", ""),
                "habilidade_bncc": questao.get("habilidade_bncc", ""),
                "matriz_enem": questao.get("matriz_enem", ""),
                "dificuldade": questao.get("dificuldade", ""),
            },
        )
    except Exception as e:
        print(f"[tela_enem] Erro ao registrar log: {e}")


# ── Entrada principal ─────────────────────────────────────────────────────────

def tela_enem(aluno: dict, escola: dict, db):
    """
    Ponto de entrada da tela ENEM.

    Parâmetros:
        aluno  – dict do aluno logado (id, nome, ano_escolar …)
        escola – dict da escola (id, nome, cor_tema …)
        db     – módulo ou objeto com registrar_log_com_tempo()
    """
    _init_estado()
    fase = st.session_state.enem_fase

    if fase == "config":
        # MELHORIA: passa logs do aluno para sugerir dificuldade adaptativa
        try:
            from repositories.log_repo import buscar_logs
            logs_aluno = buscar_logs(escola.get("id"), aluno.get("id"))
        except Exception:
            logs_aluno = []
        _tela_config(logs_aluno=logs_aluno)
    elif fase == "quiz":
        _tela_quiz(aluno=aluno, escola=escola, db=db)
    elif fase == "resultado":
        _tela_resultado(aluno=aluno, escola=escola, db=db)



def _carregar_questao_se_preciso(sequencia, idx) -> None:
    if st.session_state.enem_questao_atual is None:
        area, dificuldade = sequencia[idx]
        with st.spinner(f"Gerando questão de {LABEL_AREA.get(area, area)}..."):
            q = gerar_questao_enem(area, dificuldade)
        st.session_state.enem_questao_atual = q
        st.session_state.enem_respondida = False
        st.session_state.enem_resposta_aluno = None
        st.session_state.enem_acertou = None
        st.session_state.enem_tempo_inicio = time.time()


def _gabarito_da_questao(q, alternativas, correta, idx, total) -> None:
    # Mostra alternativas com gabarito
    resposta_aluno = st.session_state.enem_resposta_aluno
    acertou = st.session_state.enem_acertou

    for i, alt in enumerate(alternativas):
        letra = LETRAS[i] if i < len(LETRAS) else str(i + 1)
        cor_borda, icone, cor_texto = estilo_da_alternativa(alt, correta, resposta_aluno)

        st.markdown(
            f"<div style='border:1px solid {cor_borda};border-radius:12px;"
            f"padding:0.7rem 1rem;margin-bottom:0.4rem;"
            f"background:rgba(10,19,34,0.6);color:{cor_texto};font-size:0.97rem;'>"
            f"{icone} <b>{letra})</b> {_s(alt)}</div>",
            unsafe_allow_html=True,
        )

    # Feedback
    renderizar_feedback_resposta(
        acertou,
        correta,
        "✅ Resposta correta!",
        "❌ Resposta errada. A correta era:",
    )

    # Explicação
    explicacao = q.get("explicacao", [])
    if explicacao:
        with st.expander("📖 Ver explicação", expanded=True):
            renderizar_resolucao_detalhada({"explicacao": explicacao})

    st.markdown("<br>", unsafe_allow_html=True)

    # Botão avançar
    proximo_label = "Próxima questão →" if idx + 1 < total else "🏁 Ver resultado"
    if st.button(proximo_label, width="stretch", type="primary"):
        if idx + 1 >= total:
            st.session_state.enem_fase = "resultado"
        else:
            st.session_state.enem_idx += 1
            st.session_state.enem_questao_atual = None
        st.rerun()
