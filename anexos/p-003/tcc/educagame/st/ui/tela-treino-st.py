import time

import streamlit as st

import services.dados_service as db
import services.ia_service as ai
from core.config import normalizar_materia
from st.ui.mode_common_st import (
    dados_para_exibicao,
    formatar_pergunta,
    registrar_resposta_modo,
    renderizar_alternativas_multipla_escolha,
    renderizar_cards_modo,
    renderizar_feedback_pedagogico,
    renderizar_feedback_resposta,
    renderizar_origem_questao,
    renderizar_passos_resolucao,
    renderizar_resolucao_detalhada,
    tempo_decorrido,
    titulo_passo_a_passo,
)


# MELHORIA: a aba era uma funcao de 192 linhas com quatro fases de uma
# maquina de estados empilhadas -- configurar, perguntar, corrigir e
# encerrar. Duas pecas nao desenham nada, e por isso nunca tinham sido
# testadas: o estado inicial da sessao e a mensagem de encerramento.
def estado_inicial_do_treino(materia, tema, nivel, quantidade, questao, aviso_ia) -> dict:
    """O que a sessao de treino guarda entre um clique e o proximo."""
    return {
        "materia": materia,
        "tema": tema,
        "nivel": nivel,
        "total": quantidade,
        "atual": 1,
        "acertos": 0,
        "erros": 0,
        "historico": [],
        "questao": questao,
        "aviso_ia": aviso_ia,
        "respondida": False,
        "tempo_inicio": time.time(),
    }


def mensagem_de_encerramento(acertos: int, total: int) -> tuple[str, str]:
    """(faixa, texto) -- a faixa diz a cara da mensagem, o texto ja vem pronto.

    Separado da tela porque e a unica regra desta aba: 100% e perfeito, 60%
    ou mais e bom, abaixo disso e incentivo. Nada disso precisa de Streamlit
    para ser conferido.
    """
    pct_f = int(acertos / total * 100) if total else 0
    if pct_f == 100:
        return "perfeito", f"🌟 **PERFEITO! {acertos}/{total} — {pct_f}%**"
    if pct_f >= 60:
        return "bom", f"✅ **Bom trabalho! {acertos}/{total} — {pct_f}%**"
    return "fraco", f"💪 **Continue praticando! {acertos}/{total} — {pct_f}%**"


def renderizar_aba_treino(aluno: dict, escola_id, materias: list[str]):
    if "treino" not in st.session_state:
        st.session_state.treino = None

    treino = st.session_state.treino

    if treino is None:
        _configurar_treino(aluno, materias)
        return

    q = treino["questao"]
    # MELHORIA: havia um st.info logo abaixo repetindo o mesmo aviso. Passava
    # despercebido enquanto renderizar_origem_questao mostrava só uma legenda
    # curta; agora que ela dá a explicação inteira, os dois juntos mostrariam
    # o mesmo recado duas vezes na mesma tela.
    renderizar_origem_questao(q, treino.get("aviso_ia", ""))
    atual = treino["atual"]
    total = treino["total"]
    eh_ingles = treino.get("materia") == "Ingles"
    mostrar_passos_detalhados = treino.get("materia") in {"Matematica", "Fisica", "Quimica"}
    mostrar_traducao = False
    if eh_ingles:
        mostrar_traducao = st.toggle("Show PT-BR translation", key="toggle_traducao_treino_ingles")
    q_exib = dados_para_exibicao(q, mostrar_traducao)

    st.progress(atual / total, text=f"Questão {atual} de {total} | ✅ {treino['acertos']} acertos | ❌ {treino['erros']} erros")
    st.markdown("---")
    st.warning(f"📜 {q_exib.get('enigma', '🔮 Um mistério foi invocado...')}")
    st.markdown("---")
    renderizar_passos_resolucao(
        q_exib,
        revelar_resultado=treino.get("respondida", False),
        titulo=titulo_passo_a_passo(eh_ingles and not mostrar_traducao),
        mostrar_etapas=False,
    )
    st.markdown("---")

    if not treino["respondida"]:
        st.markdown(formatar_pergunta(q_exib.get("pergunta", "")))
        st.markdown("---")
        opcoes = q_exib.get("opcoes", ["-"] * 4)
        opcoes_base = q.get("opcoes", opcoes)
        idx_correta = q.get("correta", 0)
        clicado_idx, opt_str = renderizar_alternativas_multipla_escolha(opcoes, "treino_opt")
        if clicado_idx is not None:
            _registrar_resposta_do_treino(
                treino, q, q_exib, opcoes, opcoes_base, idx_correta,
                clicado_idx, opt_str, aluno, escola_id,
            )
            st.rerun()
        return

    hist_atual = treino["historico"][-1]
    renderizar_feedback_resposta(
        hist_atual["acertou"],
        hist_atual["resposta_certa"],
        "✅ **ACERTOU!**",
        "❌ **Errou!** Correto:",
    )
    renderizar_feedback_pedagogico(
        acertou=hist_atual["acertou"],
        dados=q,
        materia=treino["materia"],
        resposta_aluno=hist_atual["resposta_aluno"],
        resposta_correta=hist_atual["resposta_certa"],
    )
    titulo = "📝 Oracle's Explanation:" if eh_ingles and not mostrar_traducao else "📝 Explicação:"
    with st.expander(titulo, expanded=False):
        renderizar_resolucao_detalhada(
            q_exib,
            em_ingles=eh_ingles and not mostrar_traducao,
            mostrar_passos=mostrar_passos_detalhados and not (eh_ingles and not mostrar_traducao),
        )
    st.markdown("---")

    if atual >= total:
        st.markdown("## 🏁 Treino Concluído!")
        faixa, texto = mensagem_de_encerramento(treino["acertos"], total)
        if faixa == "perfeito":
            st.balloons()
            st.success(texto)
        elif faixa == "bom":
            st.success(texto)
        else:
            st.warning(texto)
        _resumo_do_treino(treino)
        return

    _carregar_proxima_questao(treino, aluno)


def _configurar_treino(aluno: dict, materias: list[str]) -> None:
    st.markdown("### 🎯 Configure sua sessão de treino")
    renderizar_cards_modo([
        {
            "icone": "⚡",
            "titulo": "Treino rápido",
            "texto": "Escolha matéria, tema e dificuldade para praticar em poucos minutos.",
            "tags": ["3 a 10 questões", "ritmo curto"],
            "variante": "jogar",
        },
        {
            "icone": "📈",
            "titulo": "Progresso claro",
            "texto": "Acompanhe acertos e erros enquanto a sessão avança.",
            "tags": ["acertos", "erros"],
            "variante": "guildas",
        },
        {
            "icone": "🧭",
            "titulo": "Correção guiada",
            "texto": "Ao errar, o sistema explica a confusão e sugere como evitar o erro.",
            "tags": ["feedback", "reforço"],
            "variante": "lab",
        },
    ])
    st.markdown("---")
    c1t, c2t = st.columns(2)
    with c1t:
        mat_treino = st.selectbox("📚 Matéria:", materias, key="mat_treino")
        tema_treino = st.text_input("🎯 Tema (opcional):", key="tema_treino", placeholder="Ex: frações, equações...")
    with c2t:
        nivel_treino = st.select_slider(
            "⚡ Dificuldade:",
            options=["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
            value="🟡 Médio",
            key="nivel_treino",
        )
        qtd_treino = st.select_slider(
            "📝 Nº de questões:",
            options=[3, 5, 7, 10],
            value=5,
            key="qtd_treino",
        )
    st.markdown("")
    if st.button("🚀 Iniciar Treino!", width="stretch", key="btn_iniciar_treino"):
        mat_norm = normalizar_materia(mat_treino)
        with st.spinner("Preparando sua sessão de treino..."):
            primeira = ai.invocar_enigma(mat_norm, aluno["ano_escolar"], nivel_treino, tema_treino)
            aviso_ia = ai.obter_ultimo_erro_ia()
        st.session_state.treino = estado_inicial_do_treino(
            mat_norm, tema_treino, nivel_treino, qtd_treino, primeira, aviso_ia
        )
        st.rerun()


def _registrar_resposta_do_treino(
    treino, q, q_exib, opcoes, opcoes_base, idx_correta,
    clicado_idx, opt_str, aluno, escola_id,
) -> None:
    acertou = clicado_idx == idx_correta
    treino["respondida"] = True
    treino["historico"].append({
        "pergunta": q_exib.get("pergunta", ""),
        "resposta_aluno": opt_str,
        "resposta_certa": str(opcoes[idx_correta]),
        "acertou": acertou,
        "explicacao": q_exib.get("explicacao", ""),
    })
    if acertou:
        treino["acertos"] += 1
    else:
        treino["erros"] += 1
    registrar_resposta_modo(
        db,
        aluno_id=aluno["id"],
        escola_id=escola_id,
        materia=treino["materia"],
        modo="treino",
        acertou=acertou,
        pergunta_texto=q.get("pergunta", ""),
        resposta_aluno=str(opcoes_base[clicado_idx]),
        resposta_correta=str(opcoes_base[idx_correta]),
        explicacao_ia=q.get("explicacao", ""),
        tempo_resposta=tempo_decorrido(treino.get("tempo_inicio")),
        extras={
            "dificuldade": q.get("dificuldade", treino.get("nivel", "")),
        },
    )
    st.rerun()


def _resumo_do_treino(treino: dict) -> None:
    with st.expander("📋 Ver resumo do treino"):
        for j, h in enumerate(treino["historico"], 1):
            icone = "✅" if h["acertou"] else "❌"
            st.markdown(f"**Q{j}** {icone} {h['pergunta'][:80]}...")
            if not h["acertou"]:
                st.caption(f"   Correto: {h['resposta_certa']}")
    if st.button("🔄 Novo Treino", width="stretch", key="btn_novo_treino"):
        st.session_state.treino = None
        st.rerun()


def _carregar_proxima_questao(treino: dict, aluno: dict) -> None:
    if st.button("➡️ Próxima Questão", width="stretch", key="btn_proxima"):
        with st.spinner("Gerando próxima questão..."):
            proxima = ai.invocar_enigma(treino["materia"], aluno["ano_escolar"], treino["nivel"], treino["tema"])
            aviso_ia = ai.obter_ultimo_erro_ia()
        treino["atual"] += 1
        treino["questao"] = proxima
        treino["aviso_ia"] = aviso_ia
        treino["respondida"] = False
        treino["tempo_inicio"] = time.time()
        st.rerun()
