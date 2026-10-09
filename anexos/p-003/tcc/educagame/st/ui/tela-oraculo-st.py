import time

import streamlit as st

import services.dados_service as db
import services.ia_service as ai
from core.config import (
    get_area_da_materia,
    get_competencias_area,
    get_habilidades_area,
    normalizar_materia,
)
from st.ui.mode_common_st import (
    dados_para_exibicao,
    formatar_pergunta,
    registrar_resposta_modo,
    renderizar_alternativas_multipla_escolha,
    renderizar_feedback_pedagogico,
    renderizar_feedback_resposta,
    renderizar_origem_questao,
    renderizar_passos_resolucao,
    renderizar_resolucao_detalhada,
    tempo_decorrido,
    titulo_passo_a_passo,
)


def renderizar_aba_oraculo(aluno: dict, escola_id, curriculo: dict):
    areas_curriculares = curriculo.get("areas", {})
    with st.container():
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info(f"🎓 Guilda: **{aluno['ano_escolar']}**")
            if curriculo.get("modelo") == "integrado_area":
                area_sel = st.selectbox("Área BNCC:", list(areas_curriculares.keys()), key="area_oraculo")
                disciplinas_area = areas_curriculares.get(area_sel, [])
                mat_sel = st.selectbox("Componente de apoio:", disciplinas_area, key="mat_oraculo")
                st.caption("No Ensino Médio, a experiência prioriza competências e habilidades integradas por área.")
            else:
                mats = [materia for materias in areas_curriculares.values() for materia in materias]
                mat_sel = st.selectbox("Disciplina:", mats, key="mat_oraculo")
                area_sel = get_area_da_materia(mat_sel, aluno["ano_escolar"])
                st.caption("No Ensino Fundamental, a disciplina continua visível, mas organizada por área da BNCC.")

            mat_sel_norm = normalizar_materia(mat_sel)
            competencias_area = get_competencias_area(area_sel, aluno["ano_escolar"])
            habilidades_area = get_habilidades_area(area_sel, aluno["ano_escolar"])
            with st.expander("📚 Competências e habilidades da área", expanded=False):
                st.markdown(f"**Área:** {area_sel}")
                st.markdown(f"**Componente selecionado:** {mat_sel}")
                if competencias_area:
                    st.markdown("**Competências integradas:**")
                    for item in competencias_area[:3]:
                        st.write(f"• {item}")
                if habilidades_area:
                    st.markdown("**Habilidades em foco:**")
                    for item in habilidades_area[:3]:
                        st.write(f"• {item}")
            tema_p = st.text_input("🎯 Tema Específico (opcional):", key="tema_oraculo")
            nivel_s = st.select_slider(
                "⚡ Dificuldade:",
                options=["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
                value="🟡 Médio",
                key="nivel_oraculo",
            )
            if st.button("🔥 Invocar Enigma", width="stretch", key="btn_invocar"):
                with st.spinner("O Oráculo está consultando as brumas..."):
                    st.session_state.dados = ai.invocar_enigma(mat_sel_norm, aluno["ano_escolar"], nivel_s, tema_p)
                    st.session_state.aviso_oraculo_ia = ai.obter_ultimo_erro_ia()
                    st.session_state.respondido = False
                    st.session_state.tempo_inicio = time.time()
                st.rerun()

        with c2:
            if "dados" not in st.session_state or not st.session_state.dados:
                return

            d = st.session_state.dados
            aviso_oraculo_ia = st.session_state.get("aviso_oraculo_ia", "")
            # Ver tela_escape_room_st: o texto técnico não vai mais para o
            # aluno, só o recado escrito para ele.
            renderizar_origem_questao(d, aviso_oraculo_ia)
            eh_ingles = mat_sel_norm == "Ingles"
            mostrar_passos_detalhados = mat_sel_norm in {"Matematica", "Fisica", "Quimica"}
            mostrar_traducao = False
            if eh_ingles:
                mostrar_traducao = st.toggle("Show PT-BR translation", key="toggle_traducao_oraculo_ingles")
            d_exib = dados_para_exibicao(d, mostrar_traducao)

            st.warning(f"📜 {d_exib.get('enigma', '🔮 Um mistério foi invocado...')}")
            st.markdown("---")
            renderizar_passos_resolucao(
                d_exib,
                revelar_resultado=st.session_state.get("respondido", False),
                titulo=titulo_passo_a_passo(eh_ingles and not mostrar_traducao),
                mostrar_etapas=False,
            )
            st.markdown("---")
            st.markdown(formatar_pergunta(d_exib.get("pergunta", "")))
            st.markdown("---")

            opcoes = d_exib.get("opcoes", ["-"] * 4)
            opcoes_base = d.get("opcoes", opcoes)
            idx_correta = d.get("correta", 0)

            if not st.session_state.get("respondido", False):
                clicado_idx, opt_str = renderizar_alternativas_multipla_escolha(opcoes, "btn_oraculo")
                if clicado_idx is not None:
                    acertou = clicado_idx == idx_correta
                    st.session_state.acertou = acertou
                    st.session_state.resposta_oraculo_aluno = str(opcoes_base[clicado_idx])
                    st.session_state.resposta_oraculo_correta = str(opcoes_base[idx_correta])
                    st.session_state.respondido = True
                    registrar_resposta_modo(
                        db,
                        aluno_id=aluno["id"],
                        escola_id=escola_id,
                        materia=mat_sel_norm,
                        modo="oraculo",
                        acertou=acertou,
                        pergunta_texto=d.get("pergunta", ""),
                        resposta_aluno=str(opcoes_base[clicado_idx]),
                        resposta_correta=str(opcoes_base[idx_correta]),
                        explicacao_ia=d.get("explicacao", ""),
                        tempo_resposta=tempo_decorrido(st.session_state.get("tempo_inicio")),
                        extras={
                            "dificuldade": d.get("dificuldade", nivel_s),
                        },
                    )
                    st.rerun()
            else:
                renderizar_feedback_resposta(
                    st.session_state.acertou,
                    str(opcoes[idx_correta]),
                    "✅ **VOCÊ ACERTOU!**",
                    "❌ **O correto era:**",
                )
                renderizar_feedback_pedagogico(
                    acertou=st.session_state.acertou,
                    dados=d,
                    materia=mat_sel_norm,
                    resposta_aluno=st.session_state.get("resposta_oraculo_aluno", ""),
                    resposta_correta=st.session_state.get("resposta_oraculo_correta", str(opcoes_base[idx_correta])),
                )
                titulo = "📝 Oracle's Explanation:" if eh_ingles and not mostrar_traducao else "📝 Resolução do Oráculo:"
                with st.expander(titulo, expanded=True):
                    renderizar_resolucao_detalhada(
                        d_exib,
                        em_ingles=eh_ingles and not mostrar_traducao,
                        mostrar_passos=mostrar_passos_detalhados and not (eh_ingles and not mostrar_traducao),
                    )
                if not st.session_state.acertou and st.button("Treinar tema parecido", key="btn_treinar_parecido_oraculo"):
                    with st.spinner("Gerando uma questão parecida..."):
                        tema_reforco = d.get("tema_usado") or tema_p
                        st.session_state.dados = ai.invocar_enigma(mat_sel_norm, aluno["ano_escolar"], nivel_s, tema_reforco)
                        st.session_state.aviso_oraculo_ia = ai.obter_ultimo_erro_ia()
                        st.session_state.respondido = False
                        st.session_state.tempo_inicio = time.time()
                    st.rerun()
                if st.button("🔄 Novo Desafio", key="btn_novo_oraculo"):
                    st.session_state.dados = None
                    st.session_state.aviso_oraculo_ia = ""
                    st.session_state.respondido = False
                    st.rerun()
