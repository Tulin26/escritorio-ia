import time

import streamlit as st

import services.calculo_service as lab
import services.dados_service as db
import services.ia_service as ai
from core.config import eh_ensino_medio, normalizar_materia
from st.ui.mode_common_st import (
    formatar_pergunta,
    registrar_resposta_modo,
    renderizar_alternativas_multipla_escolha,
    renderizar_cabecalho_modo,
    renderizar_cards_modo,
    renderizar_contexto_pratico_laboratorio,
    renderizar_feedback_pedagogico,
    renderizar_feedback_resposta,
    renderizar_origem_questao,
    renderizar_passos_resolucao,
    selecionar_aluno,
    tempo_decorrido,
)


def renderizar_tela_laboratorio(escola_id, alunos_data):
    renderizar_cabecalho_modo("🧪 Laboratório de Exatas")
    renderizar_cards_modo([
        {
            "icone": "🔬",
            "titulo": "Experimento guiado",
            "texto": "Desafios de matemática, física e química com fórmula e etapas de resolução.",
            "tags": ["exatas", "LaTeX"],
            "variante": "lab",
        },
        {
            "icone": "🧮",
            "titulo": "Raciocínio visível",
            "texto": "O aluno vê os dados, resolve a questão e compara com o passo a passo.",
            "tags": ["fórmula", "cálculo"],
            "variante": "jogar",
        },
        {
            "icone": "♻️",
            "titulo": "Reforço imediato",
            "texto": "Quando erra, recebe orientação e pode treinar um experimento parecido.",
            "tags": ["feedback", "prática"],
            "variante": "guildas",
        },
    ])
    al_obj = selecionar_aluno(alunos_data, "Cientista Responsável:", "lab_aluno")
    if not al_obj:
        st.info("Nenhum aluno cadastrado ainda.")
        return

    if eh_ensino_medio(al_obj["ano_escolar"]):
        areas_lab = ["Matemática", "Física", "Química"]
        area_bncc_lab = "Ciências da Natureza e suas Tecnologias"
    else:
        areas_lab = ["Matemática"]
        area_bncc_lab = "Matemática"

    c1, c2 = st.columns([1, 2])
    with c1:
        mat_lab = st.selectbox("Área de Estudo:", areas_lab)
        st.caption(f"Área integrada BNCC: {area_bncc_lab}")
        tema_lab = st.text_input("🎯 Objetivo do Experimento:", placeholder="Ex: estequiometria, densidade...")
        nivel_l = st.select_slider(
            "⚡ Dificuldade:",
            options=["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
            value="🟡 Médio",
            key="dif_lab",
        )
        if st.button("🧪 Iniciar Reação", width="stretch"):
            mat_lab_norm = normalizar_materia(mat_lab)
            with st.spinner("Preparando desafio..."):
                tema_final = str(tema_lab or "").strip()
                st.session_state.dados_lab = lab.gerar_desafio_exatas(mat_lab_norm, tema_final, al_obj["ano_escolar"], nivel_l)
                st.session_state.aviso_lab_ia = ai.obter_ultimo_erro_ia()
                st.session_state.respondido_lab = False
                st.session_state.tempo_inicio_lab = time.time()
            st.rerun()

    with c2:
        if "dados_lab" not in st.session_state or not st.session_state.dados_lab:
            return

        dl = st.session_state.dados_lab
        aviso_lab_ia = st.session_state.get("aviso_lab_ia", "")
        # Ver tela_escape_room_st: o texto técnico não vai mais para o aluno,
        # só o recado escrito para ele. O técnico continua no painel do ADM.
        renderizar_origem_questao(dl, aviso_lab_ia)

        renderizar_passos_resolucao(
            dl,
            revelar_resultado=st.session_state.get("respondido_lab", False),
            titulo="### 📐 **Passo a passo da resolução**",
            mostrar_etapas=st.session_state.get("respondido_lab", False),
        )
        st.markdown("")
        st.markdown(formatar_pergunta(dl.get("pergunta", "")))
        st.markdown("---")

        opcoes_l = dl.get("opcoes", [])
        idx_l = int(dl.get("correta", 0))
        if not st.session_state.get("respondido_lab", False):
            clicado_idx, opt_str = renderizar_alternativas_multipla_escolha(opcoes_l, "lab")
            if clicado_idx is not None:
                acertou = clicado_idx == idx_l
                st.session_state.acertou_lab = acertou
                st.session_state.resposta_lab_aluno = str(opt_str)
                st.session_state.resposta_lab_correta = str(opcoes_l[idx_l])
                st.session_state.respondido_lab = True
                materia_lab_log = normalizar_materia(mat_lab)
                registrar_resposta_modo(
                    db,
                    aluno_id=al_obj["id"],
                    escola_id=escola_id,
                    materia=f"LAB-{materia_lab_log}",
                    modo="laboratorio",
                    acertou=acertou,
                    pergunta_texto=dl.get("pergunta", ""),
                    resposta_aluno=opt_str,
                    resposta_correta=str(opcoes_l[idx_l]),
                    explicacao_ia=dl.get("explicacao", ""),
                    tempo_resposta=tempo_decorrido(st.session_state.get("tempo_inicio_lab")),
                    extras={
                        "dificuldade": dl.get("dificuldade", nivel_l),
                        # Guardado para poder MEDIR validações da IA contra
                        # dado real — ver a migração 20260903120000.
                        "passos_json": dl.get("passos_resolucao"),
                        # Pelo mesmo motivo, e para a validação vizinha: a
                        # `legenda-com-variavel-sem-formula` cruza os três
                        # (migração 20260909120000).
                        "formula": dl.get("formula"),
                        "subformulas": dl.get("subformulas"),
                        "legenda_variaveis": dl.get("legenda_variaveis"),
                        # O Laboratorio era o unico modo de exatas sem BNCC.
                        "area_bncc": dl.get("area_bncc"),
                        "competencia_bncc": dl.get("competencia_bncc"),
                        "habilidade_bncc": dl.get("habilidade_bncc"),
                        "codigo_bncc": dl.get("codigo_bncc"),
                    },
                )
                st.rerun()
            return

        renderizar_feedback_resposta(
            st.session_state.acertou_lab,
            str(opcoes_l[idx_l]),
            "🌟 **REAÇÃO BEM SUCEDIDA!**",
            "❌ **O correto era:**",
        )
        renderizar_feedback_pedagogico(
            acertou=st.session_state.acertou_lab,
            dados=dl,
            materia=normalizar_materia(mat_lab),
            resposta_aluno=st.session_state.get("resposta_lab_aluno", ""),
            resposta_correta=st.session_state.get("resposta_lab_correta", str(opcoes_l[idx_l])),
        )
        with st.expander("🌍 Onde isso aparece no dia a dia", expanded=False):
            renderizar_contexto_pratico_laboratorio(dl, normalizar_materia(mat_lab))
        if not st.session_state.acertou_lab and st.button("Treinar experimento parecido"):
            mat_lab_norm = normalizar_materia(mat_lab)
            with st.spinner("Preparando um reforco parecido..."):
                tema_final = str(dl.get("tema_usado") or tema_lab or "").strip()
                st.session_state.dados_lab = lab.gerar_desafio_exatas(mat_lab_norm, tema_final, al_obj["ano_escolar"], nivel_l)
                st.session_state.aviso_lab_ia = ai.obter_ultimo_erro_ia()
                st.session_state.respondido_lab = False
                st.session_state.tempo_inicio_lab = time.time()
            st.rerun()
        if st.button("🔄 Nova Reação"):
            st.session_state.dados_lab = None
            st.session_state.aviso_lab_ia = ""
            st.session_state.respondido_lab = False
            st.rerun()
