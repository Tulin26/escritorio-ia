from __future__ import annotations

import time

import streamlit as st

import services.dados_service as db
import services.ia_service as ai
import services.relatorios as report
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


def _resetar_escape_room():
    st.session_state.escape_room = None


def _gerar_questao(sala: dict, aluno: dict, nivel: str):
    materia = normalizar_materia(sala.get("materia", ""))
    tema = str(sala.get("tema", "") or "").strip()
    questao = ai.invocar_enigma(materia, aluno["ano_escolar"], nivel, tema)
    return questao, ai.obter_ultimo_erro_ia()


def _configurar_salas(materias: list[str]) -> list[dict]:
    qtd_salas = st.number_input(
        "Quantidade de salas/matérias",
        min_value=1,
        max_value=8,
        value=4,
        step=1,
        help="Cada sala vira um desafio. Se o tema ficar vazio, a IA usa um tema aleatorio da BNCC.",
    )
    salas = []
    for idx in range(int(qtd_salas)):
        st.markdown(f"**Sala {idx + 1}**")
        col_materia, col_tema = st.columns([1, 1.2])
        with col_materia:
            materia = st.selectbox(
                "Materia",
                materias,
                key=f"escape_materia_{idx}",
            )
        with col_tema:
            tema = st.text_input(
                "Tema opcional",
                key=f"escape_tema_{idx}",
                placeholder="Vazio = tema aleatorio BNCC",
            )
        salas.append({
            "numero": idx + 1,
            "materia": normalizar_materia(materia),
            "tema": tema.strip(),
        })
    return salas


def _render_config(aluno: dict, materias: list[str]):
    if not materias:
        st.info("Nenhuma matéria disponível para montar o Escape Room.")
        return

    renderizar_cards_modo([
        {
            "icone": "🔐",
            "titulo": "Portas por matéria",
            "texto": "Cada sala tem um enigma. Acertos liberam pistas e aproximam o aluno da saída.",
            "tags": ["interdisciplinar", "IA"],
            "variante": "boss",
        },
        {
            "icone": "🧩",
            "titulo": "Tema flexivel",
            "texto": "O professor escolhe temas especificos ou deixa vazio para sortear pela BNCC.",
            "tags": ["BNCC", "personalizavel"],
            "variante": "lab",
        },
        {
            "icone": "📄",
            "titulo": "PDF final",
            "texto": "Ao terminar, o percurso vira relatório com acertos, erros e explicações.",
            "tags": ["relatório", "professor"],
            "variante": "professor",
        },
    ])

    st.markdown("---")
    nivel = st.select_slider(
        "Dificuldade geral",
        options=["🟢 Fácil", "🟡 Médio", "🔴 Difícil"],
        value="🟡 Médio",
        key="escape_nivel",
    )
    salas = _configurar_salas(materias)

    if st.button("Iniciar Escape Room", width="stretch", type="primary"):
        with st.spinner("Preparando a primeira sala..."):
            primeira, aviso = _gerar_questao(salas[0], aluno, nivel)
        st.session_state.escape_room = {
            "nivel": nivel,
            "salas": salas,
            "atual": 0,
            "questao": primeira,
            "aviso_ia": aviso,
            "respondida": False,
            "tempo_inicio": time.time(),
            "historico": [],
            "pistas": [],
        }
        st.rerun()


def _registrar_resposta(aluno: dict, escola_id, estado: dict, sala: dict, questao: dict, clicado_idx: int, opt_str: str):
    opcoes_base = questao.get("opcoes", [])
    idx_correta = int(questao.get("correta", 0) or 0)
    acertou = clicado_idx == idx_correta
    resposta_correta = str(opcoes_base[idx_correta]) if 0 <= idx_correta < len(opcoes_base) else ""
    tempo = tempo_decorrido(estado.get("tempo_inicio"))
    pista = (
        f"Sala {sala['numero']} liberada: {sala['materia']} foi resolvida."
        if acertou
        else f"Sala {sala['numero']}: revise {sala['materia']} antes da próxima tentativa."
    )

    estado["respondida"] = True
    estado["pistas"].append(pista)
    estado["historico"].append({
        "sala": sala["numero"],
        "materia": sala["materia"],
        "tema": sala.get("tema", ""),
        "pergunta": questao.get("pergunta", ""),
        "resposta_aluno": str(opcoes_base[clicado_idx]) if 0 <= clicado_idx < len(opcoes_base) else opt_str,
        "resposta_correta": resposta_correta,
        "acertou": acertou,
        "tempo": tempo,
        "explicacao": questao.get("explicacao", ""),
    })

    registrar_resposta_modo(
        db,
        aluno_id=aluno["id"],
        escola_id=escola_id,
        materia=sala["materia"],
        modo="escape_room",
        acertou=acertou,
        pergunta_texto=questao.get("pergunta", ""),
        resposta_aluno=str(opcoes_base[clicado_idx]) if 0 <= clicado_idx < len(opcoes_base) else opt_str,
        resposta_correta=resposta_correta,
        explicacao_ia=questao.get("explicacao", ""),
        tempo_resposta=tempo,
        extras={"dificuldade": questao.get("dificuldade", estado.get("nivel", ""))},
    )


def _render_resultado(aluno: dict, escola: dict, estado: dict):
    historico = estado.get("historico", [])
    total = len(historico)
    acertos = sum(1 for item in historico if item.get("acertou"))
    pct = int(acertos / total * 100) if total else 0
    st.markdown("## Escape Room concluido")
    if pct >= 70:
        st.success(f"Saída encontrada: {acertos}/{total} acertos ({pct}%).")
    else:
        st.warning(f"Rota incompleta: {acertos}/{total} acertos ({pct}%). O relatório mostra o que revisar.")

    with st.expander("Pistas liberadas", expanded=True):
        for pista in estado.get("pistas", []):
            st.markdown(f"- {pista}")

    try:
        pdf_bytes = report.gerar_pdf_escape_room(
            nome_aluno=aluno.get("nome", "Aluno"),
            historico=historico,
            dados_escola=escola,
        )
        st.download_button(
            "Baixar relatório do Escape Room (PDF)",
            data=pdf_bytes,
            file_name=f"Escape_Room_{aluno.get('nome', 'Aluno').replace(' ', '_')}.pdf",
            mime="application/pdf",
            width="stretch",
        )
    except Exception as e:
        st.warning(f"PDF indisponivel: {e}")

    if st.button("Criar novo Escape Room", width="stretch", type="primary"):
        _resetar_escape_room()
        st.rerun()


def _render_sala(aluno: dict, escola: dict, estado: dict):
    salas = estado.get("salas", [])
    atual = int(estado.get("atual", 0))
    if atual >= len(salas):
        _render_resultado(aluno, escola, estado)
        return

    sala = salas[atual]
    questao = estado.get("questao") or {}
    eh_ingles = sala.get("materia") == "Ingles"
    mostrar_traducao = False
    if eh_ingles:
        mostrar_traducao = st.toggle("Show PT-BR translation", key=f"escape_traducao_{atual}")
    questao_exib = dados_para_exibicao(questao, mostrar_traducao)

    progresso = (atual + 1) / max(1, len(salas))
    st.progress(progresso, text=f"Sala {atual + 1} de {len(salas)} | {sala['materia']}")
    # MELHORIA: aqui vinha um segundo `st.info(estado["aviso_ia"])`, logo
    # abaixo. O aluno lia o recado escrito para ele e, em seguida, o texto
    # técnico da cascata ("IA indisponivel no momento. Usando banco de
    # questoes local.") -- a mesma informação duas vezes, a segunda em jargão
    # nosso. Sobra de antes de `renderizar_origem_questao` existir.
    renderizar_origem_questao(questao, estado.get("aviso_ia", ""))

    st.markdown(f"### 🔐 Sala {sala['numero']} - {sala['materia']}")
    if sala.get("tema"):
        st.caption(f"Tema: {sala['tema']}")
    st.warning(questao_exib.get("enigma", "Resolva o enigma para abrir a porta."))
    renderizar_passos_resolucao(
        questao_exib,
        revelar_resultado=estado.get("respondida", False),
        titulo=titulo_passo_a_passo(eh_ingles and not mostrar_traducao),
        mostrar_etapas=False,
    )
    st.markdown(formatar_pergunta(questao_exib.get("pergunta", "")))
    st.markdown("---")

    opcoes = questao_exib.get("opcoes", ["-"] * 4)
    idx_correta = int(questao.get("correta", 0) or 0)
    if not estado.get("respondida", False):
        clicado_idx, opt_str = renderizar_alternativas_multipla_escolha(opcoes, f"escape_{atual}")
        if clicado_idx is not None:
            _registrar_resposta(aluno, escola["id"], estado, sala, questao, clicado_idx, opt_str)
            st.rerun()
        return

    hist_atual = estado["historico"][-1]
    resposta_certa_exib = str(opcoes[idx_correta]) if 0 <= idx_correta < len(opcoes) else hist_atual["resposta_correta"]
    renderizar_feedback_resposta(
        hist_atual["acertou"],
        resposta_certa_exib,
        "Porta aberta. Pista liberada.",
        "A porta resistiu. Resposta correta:",
    )
    renderizar_feedback_pedagogico(
        acertou=hist_atual["acertou"],
        dados=questao,
        materia=sala["materia"],
        resposta_aluno=hist_atual["resposta_aluno"],
        resposta_correta=hist_atual["resposta_correta"],
    )
    with st.expander("Explicação da sala", expanded=True):
        renderizar_resolucao_detalhada(questao_exib, em_ingles=eh_ingles and not mostrar_traducao)

    if atual + 1 >= len(salas):
        if st.button("Ver resultado final", width="stretch", type="primary"):
            estado["atual"] = len(salas)
            st.rerun()
    elif st.button("Abrir próxima sala", width="stretch", type="primary"):
        proxima_idx = atual + 1
        with st.spinner("Preparando a próxima sala..."):
            proxima, aviso = _gerar_questao(salas[proxima_idx], aluno, estado["nivel"])
        estado["atual"] = proxima_idx
        estado["questao"] = proxima
        estado["aviso_ia"] = aviso
        estado["respondida"] = False
        estado["tempo_inicio"] = time.time()
        st.rerun()

    if st.button("Abandonar Escape Room", width="stretch"):
        _resetar_escape_room()
        st.rerun()


def renderizar_tela_escape_room(aluno: dict, escola: dict, materias: list[str]):
    if "escape_room" not in st.session_state:
        st.session_state.escape_room = None

    estado = st.session_state.escape_room
    if estado is None:
        _render_config(aluno, materias)
        return

    _render_sala(aluno, escola, estado)
