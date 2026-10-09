import streamlit as st


from services.gamification_service import BADGES, calcular_badges, streak_acertos

def renderizar_perfil_aluno(aluno, logs_aluno):
    total = len(logs_aluno)
    acertos = sum(1 for r in logs_aluno if r.get("resultado") == "Acertou")
    erros = total - acertos
    pct = int(acertos / total * 100) if total > 0 else 0
    streak = streak_acertos(logs_aluno)
    badges = calcular_badges(logs_aluno, aluno)

    st.markdown(f"### 🧑‍🎓 {aluno.get('nome', '')} — {aluno.get('ano_escolar', '')}")
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 Respondidas", total)
    c2.metric("✅ Acertos", acertos)
    c3.metric("❌ Erros", erros)
    c4.metric("🎯 Aproveitamento", f"{pct}%")

    st.markdown(f"⚡ **Maior sequência de acertos:** {streak} questões")
    st.markdown("---")
    st.markdown("### 🏅 Conquistas")
    st.caption(f"{len(badges)} de {len(BADGES)} conquistas desbloqueadas")

    ids_desbloqueados = {b["id"] for b in badges}
    cols_por_linha = 5
    for row_start in range(0, len(BADGES), cols_por_linha):
        row_badges = BADGES[row_start : row_start + cols_por_linha]
        cols = st.columns(cols_por_linha)
        for col, badge in zip(cols, row_badges):
            desbloqueado = badge["id"] in ids_desbloqueados
            with col:
                if desbloqueado:
                    st.markdown(
                        f"""<div style="text-align:center;padding:10px;border-radius:10px;
                        background:#1a3a1a;border:2px solid #2ecc71;">
                        <div style="font-size:2rem">{badge["emoji"]}</div>
                        <div style="font-size:0.75rem;color:#2ecc71;font-weight:bold">{badge["nome"]}</div>
                        <div style="font-size:0.65rem;color:#aaa">{badge["desc"]}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""<div style="text-align:center;padding:10px;border-radius:10px;
                        background:#1a1a1a;border:2px solid #333;opacity:0.5;">
                        <div style="font-size:2rem">🔒</div>
                        <div style="font-size:0.75rem;color:#666;font-weight:bold">{badge["nome"]}</div>
                        <div style="font-size:0.65rem;color:#555">{badge["desc"]}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
        st.markdown("")
