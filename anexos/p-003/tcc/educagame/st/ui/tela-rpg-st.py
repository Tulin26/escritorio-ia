import time as time_mod
import pandas as pd
import streamlit as st

from core.design_system import aplicar_design_system_rpg
import core.utils as core_utils
import st.ui.rpg_helpers_st as rpg_helpers
from st.ui.mode_common_st import (
    formatar_pergunta as _formatar_pergunta,
    registrar_log_com_tempo_ui as _registrar_log_com_tempo_ui_base,
    renderizar_origem_questao,
    renderizar_feedback_pedagogico,
    tempo_decorrido,
)

formatar_latex = core_utils.formatar_latex
_preparar_formula_latex = core_utils.preparar_formula_latex
_tem_matriz = core_utils.tem_matriz


def _registrar_log_com_tempo_ui(db_repo, dados, tempo_resposta=None):
    return _registrar_log_com_tempo_ui_base(db_repo, dados, tempo_resposta)


def _formatar_texto_markdown(texto) -> str:
    texto_fmt = str(texto or "")
    texto_fmt = texto_fmt.replace("R$", "CURRENCYBRLTOKEN")
    texto_fmt = texto_fmt.replace("$", r"\$")
    return texto_fmt.replace("CURRENCYBRLTOKEN", r"R\$")


# MELHORIA: estas tres pecas moravam dentro de _renderizar_desafio_rpg, que
# tem 277 linhas. Nenhuma delas desenha nada -- sao o contexto em texto, a
# conta do que o aluno ganha ou perde, e o payload do log. Eram as unicas
# partes sem teste da tela, e sao justamente as que mudam o progresso dele.
def contexto_do_desafio(config_rpg: dict, desafio: dict, ultima_escolha: dict) -> list[str]:
    """As etiquetas que aparecem acima da pergunta (materia, tema, rota...)."""
    contexto_desafio = []
    if config_rpg.get("materia"):
        contexto_desafio.append(rpg_helpers._chip_rpg(f"📘 {config_rpg.get('materia')}", "quest"))
    if desafio.get("tema_usado"):
        contexto_desafio.append(rpg_helpers._chip_rpg(f"🧠 Tema: {desafio.get('tema_usado')}", "missao"))
    if ultima_escolha.get("rota"):
        contexto_desafio.append(rpg_helpers._chip_rpg(f"🗺️ {ultima_escolha['rota']}", "quest"))
    if ultima_escolha.get("destino_titulo"):
        contexto_desafio.append(rpg_helpers._chip_rpg(f"{ultima_escolha.get('icone_destino', '🧭')} {ultima_escolha['destino_titulo']}", "missao"))
    if ultima_escolha.get("recurso"):
        contexto_desafio.append(rpg_helpers._chip_rpg(f"🎒 {ultima_escolha['recurso']}", "poder"))
    if ultima_escolha.get("foco_aprendizado"):
        contexto_desafio.append(rpg_helpers._chip_rpg(f"📘 {ultima_escolha['foco_aprendizado']}", "poder"))

    return contexto_desafio


def aplicar_resposta_ao_estado(
    estado: dict, desafio: dict, config_rpg: dict, indice: int, rpg_engine
) -> tuple[bool, dict]:
    """Atualiza XP, HP, recompensa e historico. Devolve (acertou, resultado).

    E aqui que o aluno ganha ou perde de verdade, e era a parte da tela que
    nao tinha rede nenhuma: acertar soma XP e sorteia recompensa; errar tira
    HP, com o piso em zero para a barra nao ficar negativa.
    """
    acertou = indice == desafio["correta"]
    opt_str = str(desafio["opcoes"][indice])
    ultima_escolha = estado.get("ultima_escolha") or {}
    checagem_escolha = estado.get("ultima_checagem_escolha") or {}
    resultado_risco = rpg_engine.calcular_resultado_desafio(
        ultima_escolha,
        acertou,
        checagem_escolha.get("bonus_risco_ativo", True),
    )
    estado["desafio_respondido"] = True
    estado["desafio_acertou"] = acertou
    estado["ultimo_resultado_risco"] = resultado_risco
    estado["ultima_recompensa_item"] = None
    if acertou:
        estado["xp"] += resultado_risco["xp_ganho"]
        estado["recompensa_pendente"] = rpg_engine.gerar_recompensas_vitoria(ultima_escolha, estado.get("fase", 1))
    else:
        estado["hp"] = max(0, estado["hp"] - resultado_risco["hp_perda"])
        estado["recompensa_pendente"] = None
    if "historico_desafios" not in estado:
        estado["historico_desafios"] = []
    estado["historico_desafios"].append(
        {
            "fase": estado.get("fase", "?"),
            "pergunta": desafio.get("pergunta", ""),
            "resposta_aluno": opt_str,
            "resposta_correta": desafio["opcoes"][desafio["correta"]],
            "explicacao": desafio.get("explicacao", ""),
            "acertou": acertou,
            "risco": resultado_risco["risco"],
            "xp_ganho": resultado_risco["xp_ganho"],
            "hp_perda": resultado_risco["hp_perda"],
            "tema": desafio.get("tema_usado", ""),
            "materia": config_rpg.get("materia", ""),
        }
    )
    return acertou, resultado_risco


def log_da_resposta_rpg(
    desafio: dict, config_rpg: dict, al_obj: dict, escola_id, opt_str: str, acertou: bool
) -> dict:
    """O registro que alimenta o painel do professor."""
    return {
        "aluno_id": al_obj["id"],
        "escola_id": escola_id,
        "materia": f"RPG-{config_rpg.get('materia', '')}",
        "modo": "rpg",
        "resultado": "Acertou" if acertou else "Errou",
        "pergunta_texto": desafio.get("pergunta", ""),
        "resposta_aluno": opt_str,
        "resposta_correta": desafio["opcoes"][desafio["correta"]],
        "explicacao_ia": str(desafio.get("explicacao", "")),
        # MELHORIA: a questao do RPG ja trazia estes campos e o log nao os
        # levava -- o painel do professor nao tinha BNCC de nenhum RPG.
        "area_bncc": desafio.get("area_bncc"),
        "competencia_bncc": desafio.get("competencia_bncc"),
        "habilidade_bncc": desafio.get("habilidade_bncc"),
        "codigo_bncc": desafio.get("codigo_bncc"),
    }


# MELHORIA: o gemeo do bloco acima. E o outro lugar onde o XP e o HP do aluno
# mudam -- na hora da escolha, antes mesmo da pergunta -- e tambem nao tinha
# teste. As tres pecas sao estado puro; o desenho fica na tela.
def aplicar_escolha_ao_estado(estado: dict, op: dict, fase_atual: int, rpg_engine) -> dict:
    """Rola o dado da acao escolhida e cobra o preco dela. Devolve a checagem.

    O XP imediato e o dano imediato saem daqui, com o mesmo piso em zero do
    desafio: HP negativo desenharia uma barra quebrada.
    """
    resultado_escolha = rpg_engine.resolver_tentativa_acao(op, estado.get("jornada"), fase_atual)
    estado["ultima_checagem_escolha"] = resultado_escolha
    if resultado_escolha.get("xp_imediato", 0):
        estado["xp"] += resultado_escolha["xp_imediato"]
    if resultado_escolha.get("hp_perda_imediata", 0):
        estado["hp"] = max(0, estado["hp"] - resultado_escolha["hp_perda_imediata"])
    estado["jornada"] = rpg_engine.registrar_escolha_jornada(estado.get("jornada"), op, fase_atual)
    estado["ultima_escolha"] = op
    return resultado_escolha


def guardar_desafio_no_estado(estado: dict, desafio: dict, op: dict) -> None:
    """Arma a pergunta e anota o tema, sem repetir tema ja usado.

    `dict.fromkeys` mantem a ordem e descarta repetido: o gerador evita temas
    que ja cairam, e a lista e a memoria disso.
    """
    temas_usados = estado.get("temas_usados", [])
    if desafio.get("tema_usado"):
        estado["temas_usados"] = list(dict.fromkeys(temas_usados + [desafio["tema_usado"]]))
    estado["desafio_atual"] = desafio
    estado["aguardando_desafio"] = True
    estado["acao_pendente"] = op["texto"]
    estado["desafio_respondido"] = False
    estado["recompensa_pendente"] = None
    estado["ultima_recompensa_item"] = None


def passo_da_cronica(
    cena: dict, op: dict, resultado_escolha: dict, fase: int, nova_cena: dict
) -> dict:
    """Uma linha da cronica: o que o aluno fez e no que deu."""
    return {
        "local": cena.get("local_atual", ""),
        "acao": op["texto"],
        "resultado": "sem_desafio",
        "rota": op.get("rota", ""),
        "impacto": op.get("impacto_destino", ""),
        "recurso": op.get("recurso", ""),
        "resultado_tentativa": resultado_escolha.get("texto_resultado", ""),
        "chance_sucesso": resultado_escolha.get("chance_sucesso", ""),
        "rolagem": resultado_escolha.get("rolagem", ""),
        "fase": fase,
        "narracao_resultante": nova_cena.get("narracao", ""),
    }


def _renderizar_desafio_rpg(
    *,
    estado,
    cena,
    config_rpg,
    al_obj,
    escola_id,
    db_repo,
    rpg_engine,
    fases_totais,
) -> bool:
    """Desenha o desafio em curso. Devolve True quando desenhou.

    MELHORIA: eram 242 linhas dentro de renderizar_tela_rpg, que tinha 570 --
    quase metade da maior funcao do projeto. Ela ficou parada por muito tempo
    porque tela de Streamlit nao devolve valor: nao dava para fotografar
    entrada -> saida como se fez com invocar_enigma, e extrair sem rede seria
    apostar.

    A rede veio de tests/apoio_streamlit.py, que troca o Streamlit por um
    dublê que ANOTA o que a tela mandou desenhar. A saida de uma tela e a
    sequencia dessas chamadas; com ela, valeu a mesma receita das outras
    duas: fotografar antes, extrair, conferir que a fotografia bate.

    O `True`/`False` no retorno substitui o `return` seco que havia aqui: o
    chamador precisa saber se deve parar ou seguir para as opcoes da cena.
    """
    _bloco_html = rpg_helpers._bloco_html
    _chip_rpg = rpg_helpers._chip_rpg
    _html_seguro = rpg_helpers._html_seguro
    _renderizar_alternativa_desafio_rpg = rpg_helpers._renderizar_alternativa_desafio_rpg
    _renderizar_banner_rpg = rpg_helpers._renderizar_banner_rpg
    _renderizar_recompensa_desafio_rpg = rpg_helpers._renderizar_recompensa_desafio_rpg

    if estado.get("aguardando_desafio") and estado.get("desafio_atual"):
        desafio = estado["desafio_atual"]
        aviso_ia_desafio = str(desafio.get("aviso_ia", "") or "")
        ultima_escolha = estado.get("ultima_escolha") or {}
        contexto_desafio = contexto_do_desafio(config_rpg, desafio, ultima_escolha)

        # Ver tela_escape_room_st: o texto técnico não vai mais para o aluno,
        # só o recado escrito para ele.
        renderizar_origem_questao(desafio, aviso_ia_desafio)

        st.markdown(
            _bloco_html(
                f"""
                <div class="rpg-card">
                    <div class="rpg-kicker">Desafio acadêmico da fase</div>
                    <div class="rpg-card-title">🔮 {_html_seguro(desafio.get('ambientacao', 'Um desafio surge...'))}</div>
                    <div class="rpg-card-copy">Responda com atenção: esta etapa decide o rumo da trilha que você acabou de abrir.</div>
                    {f"<div class='rpg-chip-row'>{''.join(contexto_desafio)}</div>" if contexto_desafio else ""}
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        if desafio.get("formula"):
            with st.container(border=True):
                st.markdown("### 📐 Fórmula principal")
                formula_limpa = _preparar_formula_latex(desafio["formula"])
                if formula_limpa:
                    try:
                        st.latex(formula_limpa)
                    except Exception:
                        st.markdown(f"$$\n{formula_limpa}\n$$")

        subformulas = desafio.get("subformulas", [])
        if subformulas and estado.get("desafio_respondido", False):
            with st.container(border=True):
                st.markdown("### 📚 Fórmulas auxiliares")
                for sf in subformulas[:3]:
                    try:
                        st.latex(_preparar_formula_latex(sf))
                    except Exception:
                        st.markdown(f"$$\n{sf}\n$$")

        with st.container(border=True):
            st.markdown("### ❓ Pergunta da fase")
            st.markdown(_formatar_pergunta(desafio.get("pergunta", "")))

        if not estado.get("desafio_respondido", False):
            tempo_inicio_rpg = time_mod.time()
            for i, opt in enumerate(desafio["opcoes"]):
                opt_str = str(opt)
                clicou = _renderizar_alternativa_desafio_rpg(opt_str, i, f"rpg_opt_{i}")
                if clicou:
                    tempo_resposta = round(time_mod.time() - tempo_inicio_rpg, 1)
                    acertou, resultado_risco = aplicar_resposta_ao_estado(
                        estado, desafio, config_rpg, i, rpg_engine
                    )
                    _registrar_log_com_tempo_ui(
                        db_repo,
                        log_da_resposta_rpg(
                            desafio, config_rpg, al_obj, escola_id, opt_str, acertou
                        ),
                        tempo_resposta,
                    )
                    st.rerun()
        else:
            acertou = estado.get("desafio_acertou", False)
            resultado_risco = estado.get("ultimo_resultado_risco", {"xp_ganho": 30, "xp_bonus": 0, "hp_perda": 20, "risco": "baixo"})
            recompensa_pendente = estado.get("recompensa_pendente") or []
            ultima_recompensa_item = estado.get("ultima_recompensa_item")
            if acertou:
                msg_bonus = f" | +{resultado_risco['xp_bonus']} XP extras pelo risco {resultado_risco['risco']}" if resultado_risco.get("xp_bonus", 0) else ""
                _renderizar_banner_rpg("⚔️ Desafio superado", f"+{resultado_risco.get('xp_ganho', 30)} XP{msg_bonus}", "success")
                if resultado_risco.get("risco") == "alto" and not resultado_risco.get("bonus_risco_ativo", True):
                    _renderizar_banner_rpg(
                        "⚠️ Bônus parcial",
                        "Você acertou o desafio, mas a jogada arriscada falhou antes. O bônus extra dessa rota não foi ativado.",
                        "warning",
                    )
                item_escolhido = _renderizar_recompensa_desafio_rpg(estado, f"rpg_reward_{estado.get('fase', 1)}")
                if item_escolhido:
                    item_aplicado = dict(item_escolhido)
                    if item_aplicado.get("tipo") == "xp":
                        valor_efetivo = int(item_aplicado.get("valor", 0) or 0)
                        estado["xp"] += valor_efetivo
                    else:
                        hp_atual = int(estado.get("hp", 100) or 100)
                        valor_base = int(item_aplicado.get("valor", 0) or 0)
                        valor_efetivo = min(valor_base, max(0, 100 - hp_atual))
                        estado["hp"] = min(100, hp_atual + valor_base)
                    item_aplicado["valor_efetivo"] = valor_efetivo
                    estado["ultima_recompensa_item"] = item_aplicado
                    estado["recompensa_pendente"] = None
                    if estado.get("historico_desafios"):
                        estado["historico_desafios"][-1]["item_recompensa"] = item_aplicado.get("nome", "")
                        estado["historico_desafios"][-1]["item_recompensa_tipo"] = item_aplicado.get("tipo", "")
                        estado["historico_desafios"][-1]["item_recompensa_valor"] = valor_efetivo
                    st.rerun()
                if ultima_recompensa_item:
                    _renderizar_banner_rpg(
                        "🎁 Item conquistado",
                        f"{ultima_recompensa_item.get('icone', '🎁')} {ultima_recompensa_item.get('nome', 'Recompensa')}: "
                        f"{'+' + str(int(ultima_recompensa_item.get('valor_efetivo', 0) or 0)) + ' HP' if ultima_recompensa_item.get('tipo') == 'hp' else '+' + str(int(ultima_recompensa_item.get('valor_efetivo', 0) or 0)) + ' XP'}",
                        "success",
                    )
            else:
                correta_rpg = desafio["opcoes"][desafio["correta"]]
                if _tem_matriz(str(correta_rpg)):
                    _renderizar_banner_rpg(
                        "❌ Resposta errada",
                        f"-{resultado_risco.get('hp_perda', 20)} HP. A alternativa correta está logo abaixo.",
                        "danger",
                    )
                    st.markdown(formatar_latex(str(correta_rpg)))
                else:
                    _renderizar_banner_rpg(
                        "❌ Resposta errada",
                        f"-{resultado_risco.get('hp_perda', 20)} HP. Correto: {correta_rpg}",
                        "danger",
                    )
                ultimo_desafio = (estado.get("historico_desafios") or [{}])[-1]
                renderizar_feedback_pedagogico(
                    acertou=False,
                    dados=desafio,
                    materia=config_rpg.get("materia", ""),
                    resposta_aluno=str(ultimo_desafio.get("resposta_aluno", "")),
                    resposta_correta=str(correta_rpg),
                )
            with st.expander("📖 Explicação do Mestre", expanded=True):
                exp_rpg = desafio.get("explicacao", "")
                if isinstance(exp_rpg, list):
                    for bloco in exp_rpg:
                        t = bloco.get("tipo")
                        c = bloco.get("conteudo", "")
                        if t == "bold":
                            st.markdown(f"**{c}**")
                        elif t == "latex":
                            try:
                                st.latex(_preparar_formula_latex(c))
                            except Exception:
                                st.markdown(f"$$\n{c}\n$$")
                        elif t in ["resultado", "final"]:
                            st.info(f"✨ {_formatar_texto_markdown(c)}")
                        else:
                            st.markdown(formatar_latex(c))
                else:
                    st.markdown(formatar_latex(exp_rpg))
            pode_continuar = not (acertou and recompensa_pendente)
            if st.button("⚔️ Continuar a Aventura", width="stretch", disabled=not pode_continuar):
                with st.spinner("O Mestre narra o próximo capítulo..."):
                    resultado = "acertou" if acertou else "errou"
                    acao = estado.get("acao_pendente", "Enfrentou o desafio")
                    ultima_escolha = estado.get("ultima_escolha")
                    nova_cena = rpg_engine.continuar_aventura(
                        config_rpg,
                        estado["historico"],
                        acao,
                        resultado,
                        estado.get("ultima_checagem_escolha"),
                        estado.get("jornada"),
                        ultima_escolha,
                    )
                    ultima_checagem = estado.get("ultima_checagem_escolha") or {}
                    estado["historico"].append(
                        {
                            "local": cena.get("local_atual", ""),
                            "acao": acao,
                            "resultado": resultado,
                            "rota": (ultima_escolha or {}).get("rota", ""),
                            "impacto": (ultima_escolha or {}).get("impacto_destino", ""),
                            "recurso": (ultima_escolha or {}).get("recurso", ""),
                            "resultado_tentativa": ultima_checagem.get("texto_resultado", ""),
                            "chance_sucesso": ultima_checagem.get("chance_sucesso", ""),
                            "rolagem": ultima_checagem.get("rolagem", ""),
                            "fase": estado.get("fase", 1),
                            "narracao_resultante": nova_cena.get("narracao", ""),
                        }
                    )
                    estado["fase"] = min(fases_totais, estado["fase"] + 1)
                    estado["cena_atual"] = nova_cena
                    estado["aguardando_desafio"] = False
                    estado["desafio_atual"] = None
                    estado["desafio_respondido"] = False
                    estado["acao_pendente"] = None
                    estado["ultimo_resultado_risco"] = None
                    estado["recompensa_pendente"] = None
                    estado["ultima_recompensa_item"] = None
                st.rerun()
        return True
    return False


def renderizar_tela_rpg(
    *,
    escola_id,
    dados_escola,
    db_repo,
    report_service,
    rpg_engine,
    listar_rpg_configs_fn,
):
    _bloco_html = rpg_helpers._bloco_html
    _renderizar_cabecalho_aventura_rpg = rpg_helpers._renderizar_cabecalho_aventura_rpg
    _renderizar_status_rpg = rpg_helpers._renderizar_status_rpg
    _renderizar_bloco_save_rpg = rpg_helpers._renderizar_bloco_save_rpg
    _formatar_data_salva_rpg = rpg_helpers._formatar_data_salva_rpg
    _montar_estado_rpg = rpg_helpers._montar_estado_rpg
    _renderizar_banner_rpg = rpg_helpers._renderizar_banner_rpg
    _renderizar_resumo_destino_rpg = rpg_helpers._renderizar_resumo_destino_rpg
    _renderizar_cronica_rpg = rpg_helpers._renderizar_cronica_rpg
    _renderizar_cena_atual_rpg = rpg_helpers._renderizar_cena_atual_rpg
    _renderizar_resultado_escolha_rpg = rpg_helpers._renderizar_resultado_escolha_rpg
    _chip_rpg = rpg_helpers._chip_rpg
    _html_seguro = rpg_helpers._html_seguro
    _renderizar_alternativa_desafio_rpg = rpg_helpers._renderizar_alternativa_desafio_rpg
    _renderizar_recompensa_desafio_rpg = rpg_helpers._renderizar_recompensa_desafio_rpg
    _renderizar_opcao_rpg = rpg_helpers._renderizar_opcao_rpg

    aplicar_design_system_rpg()
    st.markdown(
        _bloco_html(
            """
            <div class="rpg-page-shell">
                <div class="rpg-kicker">Masmorra do conhecimento</div>
                <div class="rpg-page-title">⚔️ Aventura RPG</div>
                <div class="rpg-page-copy">
                    Avance por corredores antigos, salões cobertos de musgo e desafios que misturam narrativa, estratégia e conteúdo escolar.
                    Cada decisão abre uma trilha, cada prova fortalece a aprendizagem e cada fase aproxima o herói do coração da masmorra.
                </div>
                <div class="rpg-chip-row">
                    <span class="rpg-chip rpg-chip--missao">Exploração narrativa</span>
                    <span class="rpg-chip rpg-chip--quest">Rotas da masmorra</span>
                    <span class="rpg-chip rpg-chip--poder">Aprendizagem ativa</span>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    fases_totais = rpg_engine.FASES_TOTAIS

    try:
        todas_aventuras = listar_rpg_configs_fn(escola_id)
    except Exception as e:
        st.error(f"Erro ao buscar aventuras: {e}")
        todas_aventuras = []

    if not todas_aventuras:
        st.warning("⚠️ O professor ainda não configurou nenhuma aventura. Acesse **Painel do Professor → ⚔️ RPG** para criar uma.")
        st.stop()

    opcoes_aventuras = [f"{a.get('titulo', 'Sem título')} - {a.get('materia', '')} ({a.get('serie', '')})" for a in todas_aventuras]

    alunos = db_repo.buscar_alunos(escola_id)
    if not alunos:
        st.info("Nenhum aluno cadastrado.")
        st.stop()

    df_al = pd.DataFrame(alunos)
    topo_cfg, topo_aluno = st.columns([1.35, 1])
    with topo_cfg:
        st.markdown("<div class='rpg-field-label'>Campanha</div>", unsafe_allow_html=True)
        aventura_escolhida = st.selectbox(
            "Escolha sua aventura",
            options=opcoes_aventuras,
            key="escolher_aventura_rpg",
            label_visibility="collapsed",
        )
    idx_escolhida = opcoes_aventuras.index(aventura_escolhida)
    config_rpg = todas_aventuras[idx_escolhida]

    with topo_aluno:
        st.markdown("<div class='rpg-field-label'>Herói em campo</div>", unsafe_allow_html=True)
        nome_s = st.selectbox(
            "Quem embarca na aventura?",
            df_al["nome"].tolist(),
            label_visibility="collapsed",
        )
    al_obj = df_al[df_al["nome"] == nome_s].iloc[0]

    _renderizar_cabecalho_aventura_rpg(config_rpg, fases_totais)

    rpg_key = f"rpg_{al_obj['id']}_{config_rpg['id']}"
    if rpg_key not in st.session_state:
        st.session_state[rpg_key] = None
    flash_key = f"{rpg_key}_flash"

    estado = st.session_state[rpg_key]
    progresso_salvo = db_repo.carregar_progresso_rpg(escola_id, al_obj["id"], config_rpg["id"])
    resumo_salvo = (progresso_salvo or {}).get("estado", {}) if isinstance(progresso_salvo, dict) else {}

    if st.session_state.get(flash_key):
        flash = st.session_state.pop(flash_key)
        if flash.get("tipo") == "success":
            st.success(flash.get("texto", ""))
        elif flash.get("tipo") == "error":
            st.error(flash.get("texto", ""))
        else:
            st.info(flash.get("texto", ""))

    if estado:
        _renderizar_status_rpg(estado, fases_totais)
        c_save, c_save_exit = st.columns(2)
        if c_save.button("💾 Salvar progresso", width="stretch"):
            ok, retorno = db_repo.salvar_progresso_rpg(escola_id, al_obj["id"], config_rpg["id"], estado, origem="manual")
            st.session_state[flash_key] = {
                "tipo": "success" if ok else "error",
                "texto": (
                    f"Progresso salvo com sucesso. Fase {estado.get('fase', 1)}, HP {estado.get('hp', 100)} e XP {estado.get('xp', 0)}."
                    if ok
                    else f"Não foi possível salvar o progresso: {retorno}"
                ),
            }
            st.rerun()
        if c_save_exit.button("🚪 Salvar e sair", width="stretch"):
            ok, retorno = db_repo.salvar_progresso_rpg(escola_id, al_obj["id"], config_rpg["id"], estado, origem="salvar_e_sair")
            st.session_state[rpg_key] = None
            st.session_state[flash_key] = {
                "tipo": "success" if ok else "error",
                "texto": (
                    "Progresso salvo. Você pode voltar depois e continuar do mesmo ponto."
                    if ok
                    else f"Não foi possível salvar antes de sair: {retorno}"
                ),
            }
            st.rerun()

    if not estado:
        if resumo_salvo:
            fase_salva = resumo_salvo.get("fase", 1)
            salvo_em = _formatar_data_salva_rpg((progresso_salvo or {}).get("salvo_em"))
            _renderizar_bloco_save_rpg(resumo_salvo, salvo_em)
            c_resume, c_restart, c_delete = st.columns(3)
            if c_resume.button("▶️ Continuar progresso salvo", width="stretch"):
                st.session_state[rpg_key] = _montar_estado_rpg({}, config_rpg["id"], resumo_salvo)
                st.session_state[flash_key] = {
                    "tipo": "success",
                    "texto": f"Progresso restaurado. Você voltou para a fase {fase_salva}.",
                }
                st.rerun()
            if c_restart.button("🚀 Iniciar nova aventura", width="stretch"):
                db_repo.remover_progresso_rpg(escola_id, al_obj["id"], config_rpg["id"])
                with st.spinner("O Mestre está preparando o cenário..."):
                    cena = rpg_engine.iniciar_aventura(config_rpg)
                    st.session_state[rpg_key] = _montar_estado_rpg(cena, config_rpg["id"])
                st.rerun()
            if c_delete.button("🗑️ Apagar save", width="stretch"):
                ok = db_repo.remover_progresso_rpg(escola_id, al_obj["id"], config_rpg["id"])
                st.session_state[flash_key] = {
                    "tipo": "success" if ok else "error",
                    "texto": "Save apagado com sucesso." if ok else "Não foi possível apagar o save.",
                }
                st.rerun()
        else:
            _renderizar_banner_rpg(
                "✨ Tudo pronto para começar",
                "Escolha o aluno e inicie a campanha. A aventura vai organizar trilhas, risco, progresso e desafios ao longo das fases.",
                "info",
            )
            if st.button("🚀 Iniciar Aventura!", width="stretch"):
                with st.spinner("O Mestre está preparando o cenário..."):
                    cena = rpg_engine.iniciar_aventura(config_rpg)
                    st.session_state[rpg_key] = _montar_estado_rpg(cena, config_rpg["id"])
                st.rerun()
        return

    estado = st.session_state[rpg_key]
    cena = estado["cena_atual"]

    if estado["hp"] <= 0:
        _renderizar_banner_rpg(
            "💀 Seu herói caiu em batalha",
            f"Você chegou até a fase {estado['fase']} com {estado['xp']} XP.",
            "danger",
        )
        _renderizar_resumo_destino_rpg(estado)
        hist_desafios = estado.get("historico_desafios", [])
        if hist_desafios:
            try:
                pdf_bytes = report_service.gerar_pdf_rpg(
                    nome_aluno=nome_s,
                    titulo_aventura=estado.get("titulo", config_rpg.get("titulo", "Aventura")),
                    historico_desafios=hist_desafios,
                    dados_escola=dados_escola,
                    hp_final=0,
                    xp_final=estado.get("xp", 0),
                )
                st.download_button(
                    label="📥 Baixar Relatório da Aventura (PDF)",
                    data=pdf_bytes,
                    file_name=f"RPG_{nome_s.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    width="stretch",
                )
            except Exception as e:
                st.warning(f"PDF indisponível: {e}")
        if st.button("🔄 Recomeçar Aventura"):
            db_repo.remover_progresso_rpg(escola_id, al_obj["id"], config_rpg["id"])
            st.session_state[rpg_key] = None
            st.rerun()
        st.stop()

    _renderizar_resumo_destino_rpg(estado)
    _renderizar_cronica_rpg(estado)
    _renderizar_cena_atual_rpg(cena, estado.get("fase", 1), fases_totais)

    if cena.get("evento") == "chefao":
        _renderizar_banner_rpg("💀 Chefão final", f"Fase {fases_totais}/{fases_totais}. O confronto decisivo chegou.", "danger")
    elif cena.get("evento") == "vitoria":
        _renderizar_banner_rpg("🏆 Vitória", f"Você completou as {fases_totais} fases e derrotou o Chefão.", "success")
        st.balloons()
        hist_desafios = estado.get("historico_desafios", [])
        if hist_desafios:
            try:
                pdf_bytes = report_service.gerar_pdf_rpg(
                    nome_aluno=nome_s,
                    titulo_aventura=estado.get("titulo", config_rpg.get("titulo", "Aventura")),
                    historico_desafios=hist_desafios,
                    dados_escola=dados_escola,
                    hp_final=estado.get("hp", 0),
                    xp_final=estado.get("xp", 0),
                )
                st.download_button(
                    label="📥 Baixar Relatório da Aventura (PDF)",
                    data=pdf_bytes,
                    file_name=f"RPG_{nome_s.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    width="stretch",
                )
            except Exception as e:
                st.warning(f"PDF indisponível: {e}")
        if st.button("🔄 Nova Aventura"):
            db_repo.remover_progresso_rpg(escola_id, al_obj["id"], config_rpg["id"])
            st.session_state[rpg_key] = None
            st.rerun()
        st.stop()

    if cena.get("recompensa"):
        _renderizar_banner_rpg("✨ Recompensa", cena["recompensa"], "success")
    if cena.get("dano_narrativo"):
        _renderizar_banner_rpg("💔 Consequência", cena["dano_narrativo"], "warning")
    _renderizar_resultado_escolha_rpg(estado)

    if _renderizar_desafio_rpg(
        estado=estado,
        cena=cena,
        config_rpg=config_rpg,
        al_obj=al_obj,
        escola_id=escola_id,
        db_repo=db_repo,
        rpg_engine=rpg_engine,
        fases_totais=fases_totais,
    ):
        return

    opcoes = cena.get("opcoes", [])
    if opcoes:
        st.markdown(
            _bloco_html(
                """
                <div class="rpg-card">
                    <div class="rpg-kicker">Próxima decisão</div>
                    <div class="rpg-card-title">O que você faz agora?</div>
                    <div class="rpg-card-copy">Cada escolha altera sua rota, fortalece um tipo de destino e muda o foco educacional da próxima etapa.</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        for op in opcoes:
            fase_atual = estado.get("fase", 1)
            if _renderizar_opcao_rpg(op, f"rpg_acao_{fase_atual}_{op['id']}", estado, fase_atual):
                resultado_escolha = aplicar_escolha_ao_estado(estado, op, fase_atual, rpg_engine)
                if estado["hp"] <= 0:
                    st.rerun()
                gerar_desafio = rpg_engine.deve_gerar_desafio(fase_atual, op)
                if gerar_desafio:
                    with st.spinner("O guardião lança um enigma..."):
                        desafio = rpg_engine.gerar_desafio_academico(
                            config_rpg,
                            cena.get("local_atual", ""),
                            cena.get("narracao", ""),
                            estado.get("temas_usados", []),
                            estado.get("jornada"),
                            op,
                        )
                        guardar_desafio_no_estado(estado, desafio, op)
                else:
                    with st.spinner("O Mestre narra o próximo capítulo..."):
                        nova_cena = rpg_engine.continuar_aventura(
                            config_rpg,
                            estado["historico"],
                            op["texto"],
                            None,
                            resultado_escolha,
                            estado.get("jornada"),
                            op,
                        )
                        estado["historico"].append(
                            passo_da_cronica(cena, op, resultado_escolha, estado.get("fase", 1), nova_cena)
                        )
                        estado["fase"] = min(fases_totais, estado["fase"] + 1)
                        estado["cena_atual"] = nova_cena
                st.rerun()
