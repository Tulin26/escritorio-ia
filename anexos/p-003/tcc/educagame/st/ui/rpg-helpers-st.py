from html import escape

import pandas as pd
import streamlit as st

import core.utils as core_utils
import services.rpg_service as rpg_engine
from core.config import normalizar_materia
from core.design_system_base import bloco_html as _bloco_html
from services.ia.normalizacao import normalizar_payload_questao

formatar_latex = core_utils.formatar_latex
preparar_formula_latex = core_utils.preparar_formula_latex
tem_matriz = core_utils.tem_matriz


def _html_seguro(texto) -> str:
    return escape(str(texto or ""))


def _html_multilinha(texto) -> str:
    return _html_seguro(texto).replace("\n", "<br>")


def _classe_risco_rpg(risco: str) -> str:
    return {"baixo": "baixo", "medio": "medio", "alto": "alto"}.get(str(risco or "").lower(), "medio")


def _chip_rpg(texto: str, variante: str = "neutro") -> str:
    if not texto:
        return ""
    return f"<span class='rpg-chip rpg-chip--{variante}'>{_html_seguro(texto)}</span>"


def _cartao_metrica_rpg(rotulo: str, valor: str, detalhe: str = "", variante: str = "neutro") -> str:
    return (
        f"<div class='rpg-stat-card rpg-stat-card--{variante}'>"
        f"<div class='rpg-stat-label'>{_html_seguro(rotulo)}</div>"
        f"<div class='rpg-stat-value'>{_html_seguro(valor)}</div>"
        f"<div class='rpg-stat-detail'>{_html_seguro(detalhe)}</div>"
        "</div>"
    )


def _mini_metrica_rpg(rotulo: str, valor: str) -> str:
    return (
        "<div class='rpg-mini-stat'>"
        f"<span>{_html_seguro(rotulo)}</span>"
        f"<strong>{_html_seguro(valor)}</strong>"
        "</div>"
    )


def _renderizar_banner_rpg(titulo: str, texto: str = "", variante: str = "info"):
    detalhe = f"<div class='rpg-banner-text'>{_html_multilinha(texto)}</div>" if texto else ""
    st.markdown(
        _bloco_html(
            f"""
            <div class="rpg-banner rpg-banner--{variante}">
                <div class="rpg-banner-title">{_html_seguro(titulo)}</div>
                {detalhe}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _renderizar_cabecalho_aventura_rpg(config_rpg, fases_totais: int):
    chips = [
        _chip_rpg(f"Herói: {config_rpg.get('heroi_nome', 'Herói')}", "quest"),
        _chip_rpg(f"Matéria: {config_rpg.get('materia', '-')}", "quest"),
        _chip_rpg(f"Série: {config_rpg.get('serie', '-')}", "quest"),
        _chip_rpg(f"{fases_totais} fases", "missao"),
    ]
    poderes = [p.strip() for p in str(config_rpg.get("poderes", "")).split(",") if p.strip()]
    poderes_html = "".join(_chip_rpg(poder, "poder") for poder in poderes[:4])
    missao = config_rpg.get("objetivo_final", "Superar a missão da aventura.")
    descricao = config_rpg.get("descricao", "") or "Uma campanha narrativa com escolhas, risco e desafios acadêmicos."

    st.markdown(
        _bloco_html(
            f"""
            <div class="rpg-hero">
                <div class="rpg-kicker">Campanha selecionada</div>
                <div class="rpg-hero-title">⚔️ {_html_seguro(config_rpg.get('titulo', 'Grande Aventura'))}</div>
                <div class="rpg-hero-copy">{_html_multilinha(descricao)}</div>
                <div class="rpg-chip-row">{''.join(chips)}</div>
                <div class="rpg-inline-list"><strong>Missão:</strong> {_html_seguro(missao)}</div>
                {f"<div class='rpg-chip-row'>{poderes_html}</div>" if poderes_html else ""}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _renderizar_status_rpg(estado_rpg, fases_totais: int):
    hp = int(estado_rpg.get("hp", 100))
    xp = int(estado_rpg.get("xp", 0))
    fase = int(estado_rpg.get("fase", 1))
    progresso = max(0, min(fase / fases_totais, 1))
    hp_texto = "Estável" if hp > 60 else "Em alerta" if hp > 25 else "Crítico"
    proximo_marco = "Chefão final" if fase >= fases_totais - 1 else f"Fase {min(fase + 1, fases_totais)}"

    st.markdown(
        _bloco_html(
            f"""
            <div class="rpg-card">
                <div class="rpg-kicker">Estado do herói</div>
                <div class="rpg-card-title">Painel da jornada</div>
                <div class="rpg-card-copy">Acompanhe sua resistência, evolução e o quanto falta para alcançar o confronto final.</div>
                <div class="rpg-grid">
                    {_cartao_metrica_rpg("HP", f"{hp}/100", hp_texto, "hp")}
                    {_cartao_metrica_rpg("XP", str(xp), "Experiência acumulada", "xp")}
                    {_cartao_metrica_rpg("Fase", f"{fase}/{fases_totais}", f"Próximo marco: {proximo_marco}", "fase")}
                    {_cartao_metrica_rpg("Campanha", f"{int(progresso * 100)}%", "Jornada concluída", "destino")}
                </div>
                <div class="rpg-progress-label">
                    <span>Progresso da campanha</span>
                    <span>{int(progresso * 100)}%</span>
                </div>
                <div class="rpg-progress-track">
                    <div class="rpg-progress-fill" style="width: {progresso * 100:.0f}%;"></div>
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _renderizar_cena_atual_rpg(cena, fase_atual: int, fases_totais: int):
    evento = cena.get("evento", "normal")
    etiquetas = {"normal": "Cena em andamento", "chefao": "Confronto final", "vitoria": "Missão concluída"}
    st.markdown(
        _bloco_html(
            f"""
            <div class="rpg-card">
                <div class="rpg-kicker">{_html_seguro(etiquetas.get(evento, "Cena"))}</div>
                <div class="rpg-card-title">📍 {_html_seguro(cena.get('local_atual', 'Local desconhecido'))}</div>
                <div class="rpg-card-subtitle">Fase {fase_atual} de {fases_totais}</div>
                <div class="rpg-card-copy">{_html_multilinha(cena.get('narracao', ''))}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _renderizar_bloco_save_rpg(resumo_salvo, salvo_em: str = ""):
    st.markdown(
        _bloco_html(
            f"""
            <div class="rpg-card">
                <div class="rpg-kicker">Progresso salvo</div>
                <div class="rpg-card-title">Sua campanha está pronta para continuar</div>
                <div class="rpg-card-copy">
                    Retome exatamente do ponto em que parou ou reinicie a aventura com outra estratégia.
                </div>
                <div class="rpg-grid">
                    {_cartao_metrica_rpg("Fase", str(resumo_salvo.get('fase', 1)), "Etapa atual", "fase")}
                    {_cartao_metrica_rpg("HP", f"{resumo_salvo.get('hp', 100)}/100", "Vitalidade do herói", "hp")}
                    {_cartao_metrica_rpg("XP", str(resumo_salvo.get('xp', 0)), "Experiência acumulada", "xp")}
                    {_cartao_metrica_rpg("Salvo em", salvo_em or "--", "Último registro", "destino")}
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def _rotulo_risco_rpg(risco: str) -> str:
    mapa = {"baixo": "🟢 Baixo", "medio": "🟡 Médio", "alto": "🔴 Alto"}
    return mapa.get(str(risco or "").lower(), "🟡 Médio")


def _renderizar_resumo_destino_rpg(estado_rpg):
    resumo = rpg_engine.resumir_jornada(estado_rpg.get("jornada"))
    placar = resumo.get("placar", {})
    extras = []
    if resumo.get("trilhas"):
        extras.append(f"<div class='rpg-inline-list'><strong>Trilhas ativas:</strong> {_html_seguro(' | '.join(resumo['trilhas'][-3:]))}</div>")
    if resumo.get("recursos"):
        extras.append(f"<div class='rpg-inline-list'><strong>Recursos recentes:</strong> {_html_seguro(' | '.join(resumo['recursos'][-3:]))}</div>")
    if resumo.get("focos"):
        extras.append(f"<div class='rpg-inline-list'><strong>Focos de aprendizagem:</strong> {_html_seguro(' | '.join(resumo['focos'][-3:]))}</div>")

    st.markdown(
        _bloco_html(
            f"""
            <div class="rpg-card">
                <div class="rpg-kicker">Destino do herói</div>
                <div class="rpg-card-title">{_html_seguro(resumo.get('icone', '🧭'))} {_html_seguro(resumo.get('titulo', 'Destino em formação'))}</div>
                <div class="rpg-card-copy">{_html_multilinha(resumo.get('descricao', ''))}</div>
                <div class="rpg-grid">
                    {_cartao_metrica_rpg("Conhecimento", str(placar.get("Conhecimento", 0)), "Leituras e domínio de conteúdo", "destino")}
                    {_cartao_metrica_rpg("Estratégia", str(placar.get("Estrategia", 0)), "Planejamento e método", "destino")}
                    {_cartao_metrica_rpg("Coragem", str(placar.get("Coragem", 0)), "Risco e decisão sob pressão", "destino")}
                    {_cartao_metrica_rpg("Cooperação", str(placar.get("Cooperacao", 0)), "Alianças e apoio", "destino")}
                </div>
                {''.join(extras)}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    return resumo


def _renderizar_cronica_rpg(estado_rpg):
    historico = estado_rpg.get("historico", [])
    if not historico:
        return
    with st.expander("📜 Crônica da jornada", expanded=False):
        for passo in historico[-4:]:
            rota = passo.get("rota", "")
            impacto = passo.get("impacto", "")
            resultado = passo.get("resultado", "sem_desafio")
            status = {"acertou": "Desafio vencido", "errou": "Desafio falhou", "sem_desafio": "Avanço narrativo"}.get(resultado, "Jornada em andamento")
            resultado_tentativa = passo.get("resultado_tentativa", "")
            chance = passo.get("chance_sucesso", "")
            rolagem = passo.get("rolagem", "")
            chips = []
            if rota:
                chips.append(_chip_rpg(f"Rota: {rota}", "quest"))
            if impacto:
                chips.append(_chip_rpg(f"Destino: {impacto}", "missao"))
            if resultado_tentativa:
                tentativa = "Tentativa inicial deu certo" if resultado_tentativa == "deu_certo" else "Tentativa inicial falhou"
                chips.append(_chip_rpg(tentativa, "poder"))
            if chance != "":
                chips.append(_chip_rpg(f"Chance {chance}%", "quest"))
            if rolagem != "":
                chips.append(_chip_rpg(f"Rolagem {rolagem}", "quest"))
            narracao = passo.get("narracao_resultante", "")
            st.markdown(
                _bloco_html(
                    f"""
                    <div class="rpg-log-card">
                        <div class="rpg-log-meta">Fase {_html_seguro(passo.get('fase', '?'))} • {_html_seguro(status)}</div>
                        <div class="rpg-log-title">{_html_seguro(passo.get('acao', 'Ação sem descrição'))}</div>
                        {f"<div class='rpg-chip-row'>{''.join(chips)}</div>" if chips else ""}
                        {f"<div class='rpg-card-copy' style='margin-top:0.85rem'>{_html_multilinha(narracao)}</div>" if narracao else ""}
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )


def _renderizar_resultado_escolha_rpg(estado_rpg):
    resultado = estado_rpg.get("ultima_checagem_escolha")
    if not resultado:
        return
    rota = resultado.get("rota", "rota escolhida")
    if resultado.get("sucesso"):
        _renderizar_banner_rpg(
            f"✅ A tentativa em {rota} deu certo!",
            f"Chance: {resultado.get('chance_sucesso', '?')}% | Rolagem: {resultado.get('rolagem', '?')} | +{resultado.get('xp_imediato', 0)} XP imediato",
            "success",
        )
        if resultado.get("xp_bonus_desafio", 0):
            _renderizar_banner_rpg(
                "🎯 Bônus de risco ativo",
                f"Se você acertar o desafio desta rota, ganha +{resultado['xp_bonus_desafio']} XP extras.",
                "info",
            )
    else:
        _renderizar_banner_rpg(
            f"❌ A tentativa em {rota} falhou!",
            f"Chance: {resultado.get('chance_sucesso', '?')}% | Rolagem: {resultado.get('rolagem', '?')} | -{resultado.get('hp_perda_imediata', 0)} HP imediato",
            "danger",
        )
        _renderizar_banner_rpg(
            "⚠️ A rota ficou mais perigosa",
            "A história continua, mas o bônus extra dessa escolha foi perdido.",
            "warning",
        )


def _renderizar_opcao_rpg(opcao, key, estado_rpg, fase_atual):
    efeitos = rpg_engine.obter_efeitos_escolha(opcao, estado_rpg.get("jornada"), fase_atual)
    efeitos_risco = rpg_engine.obter_efeitos_risco(opcao)
    risco_css = _classe_risco_rpg(opcao.get("risco"))
    detalhes = [
        _chip_rpg(f"{opcao.get('icone_destino', '🧭')} {opcao.get('destino_titulo', 'Destino em formação')}", "quest") if opcao.get("destino_titulo") else "",
        _chip_rpg(f"🗺️ {opcao.get('rota', '')}", "quest") if opcao.get("rota") else "",
        _chip_rpg(f"📘 {opcao.get('foco_aprendizado', '')}", "poder") if opcao.get("foco_aprendizado") else "",
        _chip_rpg(f"🎒 {opcao.get('recurso', '')}", "missao") if opcao.get("recurso") else "",
    ]
    metrica_html = "".join(
        [
            _mini_metrica_rpg("Risco", _rotulo_risco_rpg(opcao.get("risco"))),
            _mini_metrica_rpg("Chance", f"{efeitos['chance_sucesso']}%"),
            _mini_metrica_rpg("Se der certo", f"+{efeitos['xp_imediato_sucesso']} XP"),
            _mini_metrica_rpg("Se falhar", f"-{efeitos['hp_perda_falha']} HP"),
        ]
    )
    recompensa_desafio = f"+{efeitos_risco['xp_base'] + efeitos['xp_bonus_desafio']} XP"
    risco_desafio = f"-{efeitos_risco['hp_perda']} HP"
    st.markdown(
        _bloco_html(
            f"""
            <div class="rpg-choice-card rpg-choice-card--{risco_css}">
                <div class="rpg-choice-top">
                    <div>
                        <div class="rpg-choice-id">Escolha {_html_seguro(opcao.get('id', '?'))}</div>
                        <div class="rpg-choice-title">{_html_seguro(opcao.get('texto', 'Escolha sem descrição'))}</div>
                    </div>
                    {_chip_rpg(_rotulo_risco_rpg(opcao.get('risco')), f"risco-{risco_css}")}
                </div>
                {f"<div class='rpg-choice-copy'>{_html_multilinha(opcao.get('consequencia_imediata', ''))}</div>" if opcao.get('consequencia_imediata') else ""}
                {f"<div class='rpg-chip-row'>{''.join([chip for chip in detalhes if chip])}</div>" if any(detalhes) else ""}
                <div class="rpg-choice-grid">
                    {metrica_html}
                </div>
                <div class="rpg-inline-list"><strong>Se vencer o desafio acadêmico:</strong> {_html_seguro(recompensa_desafio)} • <strong>Se errar:</strong> {_html_seguro(risco_desafio)}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    return st.button(f"Seguir com a escolha {opcao.get('id', '?')}", key=key, width="stretch")


def _renderizar_alternativa_desafio_rpg(opt_texto, indice: int, key: str):
    rotulo = chr(65 + indice)
    opt_str = str(opt_texto)
    with st.container(border=True):
        st.markdown(f"<div class='rpg-field-label'>Alternativa {rotulo}</div>", unsafe_allow_html=True)
        st.markdown(formatar_latex(opt_str))
        return st.button(f"Escolher alternativa {rotulo}", key=key, width="stretch")


def _rotulo_item_recompensa_rpg(item) -> str:
    valor = int((item or {}).get("valor", 0) or 0)
    if (item or {}).get("tipo") == "hp":
        return f"+{valor} HP"
    return f"+{valor} XP"


def _renderizar_recompensa_desafio_rpg(estado_rpg, key_base: str):
    recompensas = estado_rpg.get("recompensa_pendente") or []
    if not recompensas:
        return None
    _renderizar_banner_rpg(
        "🎁 Escolha seu item",
        "Você acertou o desafio. Antes de seguir para a próxima sala, selecione uma recompensa.",
        "info",
    )
    colunas = st.columns(len(recompensas))
    for posicao, (coluna, item) in enumerate(zip(colunas, recompensas)):
        item = item or {}
        tipo = item.get("tipo")
        hp_atual = int(estado_rpg.get("hp", 100) or 100)
        desabilitado = tipo == "hp" and hp_atual >= 100
        with coluna:
            with st.container(border=True):
                st.markdown("<div class='rpg-field-label'>Item conquistado</div>", unsafe_allow_html=True)
                st.markdown(f"### {item.get('icone', '🎁')} {item.get('nome', 'Recompensa')}")
                st.caption(item.get("descricao", ""))
                st.markdown(f"**Bônus:** {_rotulo_item_recompensa_rpg(item)}")
                if desabilitado:
                    st.caption("Seu HP já está cheio, então este item não traria recuperação agora.")
                item_id = item.get("id", "item")
                chave_item = f"{key_base}_{posicao}_{item_id}_{tipo}_{item.get('valor', 0)}"
                if st.button(f"Pegar {item.get('nome', 'item')}", key=chave_item, width="stretch", disabled=desabilitado):
                    return item
    return None


def _montar_estado_rpg(cena, aventura_id, estado_salvo=None):
    estado_salvo = estado_salvo if isinstance(estado_salvo, dict) else {}
    cena_base = cena if isinstance(cena, dict) else {}
    desafio_salvo = estado_salvo.get("desafio_atual")
    materia_rpg = normalizar_materia((estado_salvo.get("config_rpg") or {}).get("materia", ""))
    return {
        "hp": estado_salvo.get("hp", 100),
        "xp": estado_salvo.get("xp", 0),
        "fase": estado_salvo.get("fase", 1),
        "titulo": estado_salvo.get("titulo", cena_base.get("titulo", "Aventura RPG")),
        "cena_atual": estado_salvo.get("cena_atual", cena_base),
        "historico": estado_salvo.get("historico", []),
        "temas_usados": estado_salvo.get("temas_usados", []),
        "historico_desafios": estado_salvo.get("historico_desafios", []),
        "aguardando_desafio": estado_salvo.get("aguardando_desafio", False),
        "desafio_atual": normalizar_payload_questao(
            desafio_salvo,
            modo_ingles=(materia_rpg == "Ingles"),
        )
        if isinstance(desafio_salvo, dict)
        else desafio_salvo,
        "acao_pendente": estado_salvo.get("acao_pendente"),
        "desafio_respondido": estado_salvo.get("desafio_respondido", False),
        "aventura_id": estado_salvo.get("aventura_id", aventura_id),
        "jornada": estado_salvo.get("jornada", rpg_engine.criar_jornada_inicial()),
        "ultima_escolha": estado_salvo.get("ultima_escolha"),
        "ultima_checagem_escolha": estado_salvo.get("ultima_checagem_escolha"),
        "desafio_acertou": estado_salvo.get("desafio_acertou", False),
        "ultimo_resultado_risco": estado_salvo.get("ultimo_resultado_risco"),
        "recompensa_pendente": estado_salvo.get("recompensa_pendente"),
        "ultima_recompensa_item": estado_salvo.get("ultima_recompensa_item"),
    }


def _formatar_data_salva_rpg(valor):
    if not valor:
        return ""
    try:
        data = pd.to_datetime(valor)
        return data.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)
