import math
import re
import time
import unicodedata
from html import escape

import pandas as pd
import streamlit as st

from core.origem_questao import aviso_de_origem
import core.utils as core_utils
from core.formatters import (
    _conteudo_passo_parece_formula,
    _extrair_coeficientes_bhaskara,
    _extrair_texto_e_formula,
    _formatar_numero_bonito,
    _inferir_subformulas_simbolicas,
    _preparar_formula_passo,
)
from services.pedagogical_feedback import gerar_feedback_pedagogico

formatar_latex = core_utils.formatar_latex
preparar_formula_latex = core_utils.preparar_formula_latex
tem_matriz = core_utils.tem_matriz


def _formula_tem_moeda(texto: str) -> bool:
    return "R$" in str(texto or "") or "r$" in str(texto or "").lower()


def _escapar_moeda_markdown(texto: str) -> str:
    return str(texto or "").replace("$", r"\$")


def registrar_log_com_tempo_ui(db_repo, dados: dict, tempo_resposta: float | None = None):
    resposta = db_repo.registrar_log_com_tempo(dados, tempo_resposta)
    return resposta


def registrar_resposta_modo(
    db_repo,
    *,
    aluno_id,
    escola_id,
    materia: str,
    modo: str,
    acertou: bool,
    pergunta_texto: str,
    resposta_aluno: str,
    resposta_correta: str,
    explicacao_ia,
    tempo_resposta: float | None = None,
    extras: dict | None = None,
):
    dados = {
        "aluno_id": aluno_id,
        "escola_id": escola_id,
        "materia": materia,
        "modo": modo,
        "resultado": "Acertou" if acertou else "Errou",
        "pergunta_texto": pergunta_texto,
        "resposta_aluno": resposta_aluno,
        "resposta_correta": resposta_correta,
        "explicacao_ia": str(explicacao_ia or ""),
    }
    if extras:
        dados.update(extras)

    # O trigger trg_atualizar_pontos no banco já cuida de somar/descontar pontos
    # automaticamente a cada INSERT em logs_pedagogicos. Não é necessário fazer
    # nenhuma atualização manual aqui — isso causaria double-count.
    return registrar_log_com_tempo_ui(db_repo, dados, tempo_resposta)


def selecionar_aluno(alunos, label: str, key: str):
    # MELHORIA: este seletor deixava QUALQUER pessoa escolher por qual aluno
    # jogar -- e pontuar. Fazia sentido quando nao havia login (entrava-se
    # com o slug da escola, um codigo compartilhado pela turma), mas agora
    # ha autenticacao: o aluno logado joga como ele mesmo, sem escolha.
    # Professor e desenvolvedor continuam com o seletor, porque precisam
    # abrir a tela de um aluno especifico para acompanhar a turma.
    if not alunos:
        return None

    usuario = st.session_state.get("usuario") or {}
    if usuario.get("role") == "aluno":
        aluno_id = str(usuario.get("aluno_id") or "")
        proprio = next((a for a in alunos if str(a.get("id")) == aluno_id), None)
        if proprio:
            st.caption(f"{label} **{proprio.get('nome', '')}**")
            return dict(proprio)
        # A conta e de aluno mas nao esta na lista desta escola: nao cai no
        # seletor (isso deixaria jogar no nome de outro), avisa e para.
        st.warning("Sua conta de aluno não foi encontrada nesta escola. Fale com seu professor.")
        return None

    df_al = pd.DataFrame(alunos)
    nome_sel = st.selectbox(label, df_al["nome"].tolist(), key=key)
    return df_al[df_al["nome"] == nome_sel].iloc[0].to_dict()


def renderizar_cabecalho_modo(titulo: str, subtitulo: str = ""):
    st.title(titulo)
    if subtitulo:
        st.caption(subtitulo)


def _html_seguro(valor) -> str:
    return escape(str(valor or ""))


def card_modo_html(icone: str, titulo: str, texto: str, tags: list[str] | None = None, variante: str = "") -> str:
    tags_html = "".join(f"<span class='edu-mode-pill'>{_html_seguro(tag)}</span>" for tag in (tags or []))
    classe_variante = f" edu-mode-card--{_html_seguro(variante)}" if variante else ""
    return (
        f"<div class='edu-mode-card{classe_variante}'>"
        f"<div class='edu-dashboard-icon'>{_html_seguro(icone)}</div>"
        f"<div class='edu-mode-title'>{_html_seguro(titulo)}</div>"
        f"<div class='edu-mode-copy'>{_html_seguro(texto)}</div>"
        f"<div class='edu-mode-meta'>{tags_html}</div>"
        "</div>"
    )


def renderizar_cards_modo(cards: list[dict]):
    html = "".join(
        card_modo_html(
            str(card.get("icone", "")),
            str(card.get("titulo", "")),
            str(card.get("texto", "")),
            list(card.get("tags", []) or []),
            str(card.get("variante", "")),
        )
        for card in cards
    )
    st.markdown(f"<div class='edu-mode-grid'>{html}</div>", unsafe_allow_html=True)


def _formatar_equacoes_no_enunciado(pergunta: str) -> str:
    texto = str(pergunta or "")
    expoente_2 = r"(?:\^2|²)"
    padrao_equacao = re.compile(
        rf"([+-]?\s*\d*\s*x\s*{expoente_2}\s*(?:[+-]\s*\d*\s*x\s*)?(?:[+-]\s*\d+\s*)=\s*-?\d+)(\?)?",
        flags=re.IGNORECASE,
    )

    def _normalizar_equacao(match: re.Match) -> str:
        equacao = match.group(1)
        pontuacao_final = match.group(2) or ""
        equacao = equacao.replace("²", "^2")
        equacao = re.sub(r"\s+", " ", equacao).strip()
        equacao = re.sub(
            r"(?<![A-Za-z])([+-]?\s*\d*)\s*x\^2",
            lambda m: f"{m.group(1).replace(' ', '') or ''}x^2",
            equacao,
        )
        equacao = re.sub(r"([+-])\s+", r"\1 ", equacao)
        equacao = re.sub(r"\s*=\s*", " = ", equacao)
        return f"{pontuacao_final}\n\n$${preparar_formula_latex(equacao)}$$\n\n"

    return padrao_equacao.sub(_normalizar_equacao, texto)


def _normalizar_ordinais_texto(texto: str) -> str:
    texto = str(texto or "")
    texto = re.sub(r"\b1\s*[oº]\b", "1º", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b2\s*[oº]\b", "2º", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b3\s*[oº]\b", "3º", texto, flags=re.IGNORECASE)
    return texto


def formatar_pergunta(pergunta: str) -> str:
    if not pergunta:
        return ""
    pergunta_txt = _normalizar_ordinais_texto(str(pergunta))
    pergunta_txt = _formatar_equacoes_no_enunciado(pergunta_txt)
    if "$$" in pergunta_txt:
        return pergunta_txt
    if any(x in pergunta_txt for x in ["$", "\\", "^", "_", "{", "}", "begin", "²", "³", "Δ", "√", "±"]):
        return formatar_latex(
            pergunta_txt
            .replace("x²", "x^2")
            .replace("x³", "x^3")
            .replace("²", "^2")
            .replace("³", "^3")
        )
    if re.search(r"\b\d+[A-Za-z]\b", pergunta_txt) and "=" in pergunta_txt:
        return formatar_latex(pergunta_txt)
    return pergunta_txt


def renderizar_origem_questao(dados: dict | None, aviso_ia: str = ""):
    """De onde veio a questão -- e, quando não veio da IA, por quê.

    MELHORIA: a versão offline era a legenda "Questão gerada em modo
    offline.". Isso ROTULA e não explica: o aluno lê uma palavra técnica e
    continua sem saber por que aquela questão é diferente, nem se ela vale.
    É a mesma meia-solução que o ENEM tinha no Flask, numa pílula.

    A nona heurística pede o problema indicado com precisão e uma saída. O
    texto agora vem de core/origem_questao.py, o mesmo dos dois frontends.
    """
    dados = dados or {}
    aviso_txt = str(aviso_ia or dados.get("aviso_ia", "") or "").strip()

    aviso = aviso_de_origem(dados, aviso_txt)
    if aviso:
        st.info(aviso)
        return

    if str(dados.get("_origem_geracao", "") or "").strip().lower() == "ia":
        st.caption("Questão gerada com IA.")


def _renderizar_resultado_final(conteudo: str, titulo_resultado: str):
    prefixo, formula = _extrair_texto_e_formula(conteudo)
    if prefixo and formula:
        st.markdown(titulo_resultado)
        try:
            if _formula_tem_moeda(formula):
                raise ValueError("formula-com-moeda")
            st.latex(_preparar_formula_passo(formula))
        except Exception:
            st.markdown(formatar_latex(formula))
        return
    if _conteudo_passo_parece_formula(conteudo):
        st.markdown(titulo_resultado)
        try:
            if _formula_tem_moeda(conteudo):
                raise ValueError("formula-com-moeda")
            st.latex(_preparar_formula_passo(conteudo))
        except Exception:
            st.markdown(formatar_latex(conteudo))
        return
    st.markdown(f"{titulo_resultado} {_escapar_moeda_markdown(conteudo)}")



def _renderizar_conteudo_passo(conteudo: str):
    texto = str(conteudo or "").strip()
    if not texto:
        return
    prefixo, formula = _extrair_texto_e_formula(texto)
    if prefixo and formula:
        st.markdown(prefixo.replace("R$", r"R\$").replace("$", r"\$") + ":")
        try:
            if _formula_tem_moeda(formula):
                raise ValueError("formula-com-moeda")
            st.latex(_preparar_formula_passo(formula))
        except Exception:
            st.markdown(formatar_latex(formula))
        return
    if _conteudo_passo_parece_formula(texto):
        try:
            if _formula_tem_moeda(texto):
                raise ValueError("formula-com-moeda")
            st.latex(_preparar_formula_passo(texto))
        except Exception:
            st.markdown(formatar_latex(texto))
        return
    st.markdown(texto.replace("R$", r"R\$").replace("$", r"\$"))



def _explicacao_bhaskara_pedagogica(dados: dict):
    pergunta = str(dados.get("pergunta", "") or "")
    if not any(trecho in pergunta.lower() for trecho in ["bhaskara", "equação quadrática", "equacao quadratica", "2º grau", "2o grau"]):
        return None

    coeficientes = _extrair_coeficientes_bhaskara(pergunta)
    if not coeficientes:
        return None

    a, b, c = coeficientes
    delta = (b ** 2) - (4 * a * c)
    blocos = [
        {"tipo": "bold", "conteudo": "Onde essa ideia aparece na prática"},
        {"tipo": "texto", "conteudo": f"Primeiro identificamos os coeficientes da equação: a = {a}, b = {b} e c = {c}."},
        {"tipo": "latex", "conteudo": rf"\Delta = b^2 - 4ac = ({b})^2 - 4\cdot({a})\cdot({c}) = {delta}"},
    ]

    if delta < 0:
        blocos.append({"tipo": "texto", "conteudo": "Em situações reais, isso indica que o modelo não cruza o eixo x, então não há solução real para o problema descrito."})
        blocos.append({"tipo": "resultado", "conteudo": "Como o discriminante é negativo, a equação não possui raízes reais."})
        return blocos

    raiz_delta = math.sqrt(delta)
    x1 = (-b + raiz_delta) / (2 * a)
    x2 = (-b - raiz_delta) / (2 * a)
    x1_txt = _formatar_numero_bonito(x1)
    x2_txt = _formatar_numero_bonito(x2)

    blocos.append({
        "tipo": "texto",
        "conteudo": "Equações do 2º grau aparecem, por exemplo, em problemas de trajetória, área, lucro máximo e tempo de movimento. As raízes mostram os valores que fazem o modelo atingir exatamente a condição pedida no enunciado.",
    })
    blocos.append({
        "tipo": "resultado",
        "conteudo": f"Aqui, os valores que satisfazem a equação são x' = {x1_txt} e x'' = {x2_txt}.",
    })
    return blocos


def dados_para_exibicao(dados: dict, mostrar_traducao: bool = False) -> dict:
    if not isinstance(dados, dict):
        return {}
    exibicao = dict(dados)
    if not mostrar_traducao:
        return exibicao
    for campo in ["enigma", "pergunta", "explicacao", "passos_resolucao"]:
        traducao = dados.get(f"{campo}_traducao")
        if traducao:
            exibicao[campo] = traducao
    opcoes_traducao = dados.get("opcoes_traducao")
    if isinstance(opcoes_traducao, list) and opcoes_traducao:
        exibicao["opcoes"] = opcoes_traducao
    return exibicao


def titulo_passo_a_passo(modo_ingles: bool = False) -> str:
    return "### 📚 Step by step" if modo_ingles else "### 📚 Passo a passo da resolução"


def _subformula_auxiliar_visivel(subformula: str) -> bool:
    texto = str(subformula or "").strip()
    if not texto or "=" not in texto:
        return False

    esquerda, direita = texto.split("=", 1)
    esquerda = esquerda.strip()
    direita = direita.strip()
    if not esquerda or not direita:
        return False

    tem_operador = any(op in direita for op in ("+", "-", "*", "/", "\\frac", "\\sqrt", "^", "\\cdot", "±", "\\pm"))
    tem_texto_descritivo = bool(re.search(r"[A-Za-zÀ-ÿ]{4,}", direita))
    return tem_operador and not tem_texto_descritivo


def renderizar_passos_resolucao(
    dados: dict,
    revelar_resultado: bool = False,
    titulo: str = "### 📚 Passo a passo",
    mostrar_etapas: bool = True,
):
    passos = dados.get("passos_resolucao", []) or []
    subformulas = dados.get("subformulas", []) or []
    formula = str(dados.get("formula", "") or "").strip()
    legenda_variaveis = str(dados.get("legenda_variaveis", "") or "").strip()
    pergunta_txt = str(dados.get("pergunta", "") or "").lower()

    if not formula and not subformulas:
        eh_bhaskara = any(
            trecho in pergunta_txt
            for trecho in ["bhaskara", "equação quadrática", "equacao quadratica", "2º grau", "2o grau"]
        )
        if eh_bhaskara:
            formula = r"x = \frac{-b \pm \sqrt{\Delta}}{2a}"
            subformulas = [r"\Delta = b^2 - 4ac"]
            if not legenda_variaveis:
                legenda_variaveis = "a: coeficiente de x², b: coeficiente de x, c: termo independente."
    elif formula and not subformulas:
        if any(trecho in pergunta_txt for trecho in ["bhaskara", "equação quadrática", "equacao quadratica", "2º grau", "2o grau"]):
            subformulas = [r"\Delta = b^2 - 4ac"]
            if not legenda_variaveis:
                legenda_variaveis = "a: coeficiente de x², b: coeficiente de x, c: termo independente."

    if not passos and not subformulas and not formula:
        return

    with st.container(border=True):
        st.markdown(titulo)
        exibiu_formulas = False
        if revelar_resultado:
            subformulas_visiveis = subformulas
        else:
            subformulas_visiveis = _inferir_subformulas_simbolicas(formula, pergunta_txt) or [
                sf for sf in subformulas
                if not any(ch.isdigit() for ch in str(sf)) and _subformula_auxiliar_visivel(sf)
            ]
        if formula:
            exibiu_formulas = True
            st.markdown("**Fórmula principal:**")
            try:
                st.latex(preparar_formula_latex(formula))
            except Exception:
                st.markdown(f"$$\n{preparar_formula_latex(formula)}\n$$")
            if legenda_variaveis:
                st.caption(legenda_variaveis)
            if subformulas_visiveis:
                st.markdown("**Subfórmulas auxiliares:**")
                for sf in subformulas_visiveis:
                    try:
                        st.latex(preparar_formula_latex(sf))
                    except Exception:
                        st.markdown(f"$$\n{sf}\n$$")
        elif subformulas_visiveis:
            exibiu_formulas = True
            st.markdown("**Subfórmulas auxiliares:**")
            for sf in subformulas_visiveis:
                try:
                    st.latex(preparar_formula_latex(sf))
                except Exception:
                    st.markdown(f"$$\n{sf}\n$$")

        if mostrar_etapas and revelar_resultado and exibiu_formulas and passos:
            st.markdown("---")
            st.markdown("**Etapas da resolução:**")

        if mostrar_etapas and revelar_resultado and passos:
            for passo in passos:
                if passo.get("final") and not revelar_resultado:
                    continue
                st.markdown(f"**{passo.get('titulo', 'Etapa')}:**")
                conteudo = str(passo.get("conteudo", "")).strip()
                if not conteudo:
                    continue
                _renderizar_conteudo_passo(conteudo)


def renderizar_resolucao_detalhada(dados: dict, em_ingles: bool = False, mostrar_passos: bool = True):
    passos = dados.get("passos_resolucao", []) or []
    explicacao = dados.get("explicacao", [])
    if not em_ingles:
        explicacao_bhaskara = _explicacao_bhaskara_pedagogica(dados)
        if explicacao_bhaskara:
            explicacao = explicacao_bhaskara
    titulo_passos = "**Step by step:**" if em_ingles else "**Passo a passo:**"
    titulo_explicacao = "**Explanation:**" if em_ingles else "**Explicação:**"
    titulo_resultado = "**Final Answer:**" if em_ingles else "**Resultado Final:**"

    if mostrar_passos and passos:
        st.markdown(titulo_passos)
        for passo in passos:
            if isinstance(passo, dict):
                titulo = str(passo.get("titulo", "Etapa")).strip()
                conteudo = str(passo.get("conteudo", "")).strip()
                eh_final = bool(passo.get("final"))
            else:
                titulo = "Etapa"
                conteudo = str(passo or "").strip()
                eh_final = False
            if not conteudo:
                continue
            if eh_final:
                _renderizar_resultado_final(conteudo, titulo_resultado)
                continue
            st.markdown(f"**{titulo}:**")
            _renderizar_conteudo_passo(conteudo)

    if isinstance(explicacao, str):
        try:
            import json
            explicacao = json.loads(explicacao)
        except Exception:
            explicacao = [{"tipo": "texto", "conteudo": explicacao}]

    if isinstance(explicacao, list) and explicacao:
        if mostrar_passos and passos:
            st.markdown("---")
        st.markdown(titulo_explicacao)
        for bloco in explicacao:
            if isinstance(bloco, dict):
                tipo_b = bloco.get("tipo", "texto")
                cont_b = str(bloco.get("conteudo", "")).strip()
            else:
                tipo_b = "texto"
                cont_b = str(bloco or "").strip()
            if not cont_b:
                continue
            if tipo_b == "bold":
                st.markdown(f"**{cont_b}**")
            elif tipo_b == "latex":
                try:
                    st.latex(preparar_formula_latex(cont_b))
                except Exception:
                    st.markdown(f"$$\n{preparar_formula_latex(cont_b)}\n$$")
            elif tipo_b in ["resultado", "final"]:
                _renderizar_resultado_final(cont_b, titulo_resultado)
            else:
                st.markdown(_escapar_moeda_markdown(cont_b))
    elif explicacao:
        st.markdown(_escapar_moeda_markdown(str(explicacao)))


def _texto_busca_laboratorio(dados: dict, materia: str = "") -> str:
    partes = [materia, str(dados.get("pergunta", "") or ""), str(dados.get("formula", "") or "")]
    partes.extend(str(item) for item in (dados.get("subformulas", []) or []))
    for passo in dados.get("passos_resolucao", []) or []:
        if isinstance(passo, dict):
            partes.append(str(passo.get("titulo", "") or ""))
            partes.append(str(passo.get("conteudo", "") or ""))
    for bloco in dados.get("explicacao", []) or []:
        if isinstance(bloco, dict):
            partes.append(str(bloco.get("conteudo", "") or ""))
        else:
            partes.append(str(bloco or ""))
    texto = " ".join(partes).lower()
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


# MELHORIA: esta tabela morava DENTRO da funcao, e era o que fazia dela a
# quinta maior do projeto: 152 linhas, das quais 133 eram dados. A logica
# sempre teve quatro linhas -- casar marcador, devolver o cartao. Como
# constante de modulo, os dados viram dado: da para ler, contar e testar
# sem chamar a funcao.
USOS_DIA_A_DIA_LABORATORIO = [
    (
        ("area", "triangulo", "retangulo", "base", "altura", "superficie"),
        "Onde usamos área e medidas no dia a dia",
        [
            ("Construção civil", "Calcular área de telhados, fachadas, rampas, paredes inclinadas e estruturas que precisam de medida precisa."),
            ("Terrenos e áreas rurais", "Dividir espaços irregulares em partes menores para estimar área total, cerca, plantio ou custo de manutenção."),
            ("Arquitetura e design", "Planejar portas, janelas, placas, móveis, suportes e peças decorativas com tamanho, material e custo adequados."),
            ("Engenharia e segurança", "Analisar estruturas triangulares em pontes, torres e treliças, porque esse formato dá estabilidade."),
            ("Situações indiretas", "Descobrir alturas ou distâncias quando não dá para medir diretamente, usando sombra, base, ângulo ou proporções."),
        ],
    ),
    (
        ("desconto", "preco", "porcentagem", "percentual", "aumento"),
        "Onde usamos porcentagem no dia a dia",
        [
            ("Compras e promoções", "Comparar preço antigo e novo para saber se um desconto realmente compensa."),
            ("Aumento de preço", "Entender reajustes de mensalidade, aluguel, combustível, mercado e serviços."),
            ("Juros e parcelas", "Avaliar financiamento, cartão de crédito, empréstimos e compras parceladas."),
            ("Orçamento pessoal", "Separar parte do dinheiro para contas, lazer, reserva e metas."),
            ("Impostos e taxas", "Perceber quanto uma porcentagem muda o valor final de produtos e serviços."),
        ],
    ),
    (
        ("progressao", " pa ", "a_1", "a1", "razao", "sequencia"),
        "Onde usamos progressão aritmética no dia a dia",
        [
            ("Planejamento de metas", "Prever crescimento regular, como aumentar tempo de estudo, treino ou economia semanal."),
            ("Parcelas e pagamentos", "Analisar valores que mudam sempre pela mesma diferença em carnês, bônus ou reajustes."),
            ("Produção por etapas", "Estimar produção diária quando a quantidade aumenta de forma constante."),
            ("Padrões em tabelas", "Completar sequências de dados em relatórios, planilhas e cronogramas."),
            ("Rotinas de treino", "Organizar séries, repetições ou distância quando o aumento é sempre igual."),
        ],
    ),
    (
        ("bhaskara", "2o grau", "2 grau", "quadratica", "equacao"),
        "Onde usamos equação do 2º grau no dia a dia",
        [
            ("Construção de rampas, arcos e pontes", "Modelar curvas em formato de parábola e encontrar altura, largura ou ponto de contato."),
            ("Lucro em vendas", "Analisar situações em que aumentar muito o preço reduz vendas e existe um melhor ponto de lucro."),
            ("Área de terrenos ou objetos", "Descobrir medidas quando a área total é conhecida e os lados dependem um do outro."),
            ("Movimento e trajetórias", "Estudar lançamentos, quedas e caminhos curvos em esportes, física e engenharia."),
            ("Projetos e otimização", "Encontrar valores que maximizam, minimizam ou fazem uma situação atingir uma condição específica."),
        ],
    ),
    (
        ("trigonom", "tangente", "seno", "cosseno", "sombra", "poste"),
        "Onde usamos trigonometria no dia a dia",
        [
            ("Alturas difíceis de medir", "Descobrir altura de prédios, postes e árvores usando sombra, distância e ângulo."),
            ("Rampas e acessibilidade", "Planejar inclinação segura para rampas, escadas e acessos."),
            ("Mapas e localização", "Calcular distâncias indiretas em topografia, navegação e posicionamento."),
            ("Construção e obras", "Conferir ângulos, inclinações de telhado e alinhamento de estruturas."),
            ("Fotografia e tecnologia", "Relacionar distância, ângulo de visão, lentes e enquadramento."),
        ],
    ),
    (
        ("velocidade", "movimento", "m/s", "deslocamento"),
        "Onde usamos velocidade no dia a dia",
        [
            ("Trânsito e viagens", "Prever tempo de chegada e comparar rotas em carro, ônibus, bicicleta ou caminhada."),
            ("Segurança", "Entender distância de frenagem, limites de velocidade e risco de colisões."),
            ("Esportes", "Comparar desempenho em corrida, natação, ciclismo e jogos."),
            ("Máquinas e produção", "Medir ritmo de esteiras, motores e equipamentos industriais."),
            ("Aplicativos de rota", "Interpretar médias de deslocamento usadas por GPS e mapas."),
        ],
    ),
    (
        ("forca", "newton", "massa", "aceleracao"),
        "Onde usamos força no dia a dia",
        [
            ("Veículos", "Entender aceleração, frenagem, colisões e uso de cinto de segurança."),
            ("Elevadores e máquinas", "Dimensionar motores, cabos e cargas que precisam ser movidas."),
            ("Esportes", "Analisar chutes, arremessos, saltos e impactos."),
            ("Ergonomia", "Avaliar esforço para empurrar, puxar ou levantar objetos com segurança."),
            ("Estruturas", "Prever como cargas afetam pontes, suportes, móveis e equipamentos."),
        ],
    ),
    (
        ("ohm", "corrente", "tensao", "resistencia", "circuito"),
        "Onde usamos eletricidade no dia a dia",
        [
            ("Instalações elétricas", "Evitar sobrecarga em tomadas, fios, disjuntores e extensões."),
            ("Aparelhos eletrônicos", "Entender consumo, tensão correta e risco de queimar componentes."),
            ("Projetos com Arduino ou robótica", "Escolher resistores e proteger LEDs, sensores e placas."),
            ("Manutenção", "Diagnosticar falhas simples em circuitos, fontes e equipamentos."),
            ("Segurança doméstica", "Reconhecer quando corrente e tensão podem causar perigo."),
        ],
    ),
    (
        ("concentracao", "solucao", "g/l", "soluto"),
        "Onde usamos concentração no dia a dia",
        [
            ("Medicamentos", "Preparar ou interpretar doses em xaropes, soluções e diluições."),
            ("Produtos de limpeza", "Diluir corretamente água sanitária, desinfetantes e detergentes."),
            ("Alimentos e bebidas", "Controlar quantidade de sal, açúcar, conservantes ou suplementos em uma mistura."),
            ("Laboratório e escola", "Preparar soluções seguras e comparar resultados de experimentos."),
            ("Tratamento de água", "Ajustar substâncias para manter segurança e qualidade."),
        ],
    ),
    (
        ("ph", "acido", "base", "h+"),
        "Onde usamos pH no dia a dia",
        [
            ("Água potável e piscinas", "Verificar se a água está segura para consumo ou banho."),
            ("Solo e agricultura", "Ajustar acidez do solo para melhorar crescimento das plantas."),
            ("Alimentos", "Controlar sabor, conservação e fermentação em bebidas, queijos e conservas."),
            ("Cosméticos", "Escolher produtos adequados para pele e cabelo."),
            ("Saúde", "Entender acidez no estômago, exames e equilíbrio de soluções corporais."),
        ],
    ),
    (
        # "g/mol" entra porque um dos templates do banco escreve
        # "M = 44 g/mol" em vez das palavras "massa molar" -- ali o mol
        # empatava 1 a 1 com a regra de forca (por causa de "massa") e
        # perdia na ordem. Medido: corrige 39 das 1070 e nao mexe em mais
        # nada.
        ("mol", "massa molar", "g/mol", "estequiometr"),
        "Onde usamos mol e proporções químicas no dia a dia",
        [
            ("Receitas químicas", "Calcular quantidades certas de reagentes em laboratório."),
            ("Indústria", "Evitar desperdício ao produzir tintas, fertilizantes, remédios e alimentos."),
            ("Controle de qualidade", "Conferir se uma mistura tem proporção adequada."),
            ("Meio ambiente", "Estimar poluentes, gases e substâncias em amostras."),
            ("Experimentos escolares", "Relacionar massa medida na balança com quantidade de partículas."),
        ],
    ),
    (
        ("calor", "termoqu", "temperatura", "delta t"),
        "Onde usamos calor e temperatura no dia a dia",
        [
            ("Cozinha", "Entender aquecimento, resfriamento, fervura e conservação de alimentos."),
            ("Climatização", "Calcular energia para aquecer ou resfriar ambientes."),
            ("Motores e máquinas", "Evitar superaquecimento e melhorar eficiência."),
            ("Materiais", "Escolher isolamento térmico para roupas, casas e embalagens."),
            ("Segurança", "Prever risco de queimaduras, choque térmico e armazenamento inadequado."),
        ],
    ),
]


USOS_PADRAO_LABORATORIO = (
    "Onde usamos esse conhecimento no dia a dia",
    [
        ("Decisões práticas", "Transformar dados do enunciado em uma comparação, previsão ou escolha melhor."),
        ("Planejamento", "Estimar custo, tempo, quantidade de material, risco ou desempenho antes de agir."),
        ("Tecnologia e trabalho", "Aplicar raciocínio quantitativo em planilhas, máquinas, laboratório, comércio e projetos."),
        ("Segurança", "Evitar erros em medidas, doses, instalações, deslocamentos e estruturas."),
        ("Leitura do mundo", "Perceber que fórmulas servem para interpretar situações reais, não apenas para fazer contas."),
    ],
)


def _usos_dia_a_dia_laboratorio(dados: dict, materia: str = "") -> tuple[str, list[tuple[str, str]]]:
    """O cartao de quem casar MAIS marcadores -- nao o primeiro que casar.

    MELHORIA: parar no primeiro dava o cartao errado sempre que um marcador
    generico de uma regra aparecia numa questao de outra. Tres pares, medidos
    contra 1070 questoes do banco offline:

        "quantos mol existem em 558 g com massa molar 186 g/mol"
            -> forca, porque "massa" e marcador de forca               (39x)
        "um corpo de 4 kg acelera a 3 m/s^2. Qual a forca resultante?"
            -> velocidade, porque "m/s" esta dentro de "m/s^2"         (36x)
        "uma base forte tem pH acima de 7"
            -> area e medidas, porque "base" e a base do triangulo

    Casar por palavra inteira NAO resolveria nenhum deles: "massa" e palavra
    inteira dentro de "massa molar", e "base" e palavra inteira na frase de
    quimica. O que falta nao e limite de palavra, e corroboracao -- a questao
    de mol casa tres marcadores da regra de mol e so um da de forca.

    Medido: muda 78 das 1070 questoes (7%), e as 78 sao correcoes; a taxa de
    queda no cartao generico nao muda (255 nas duas), entao nao se perde
    cobertura.

    O `>` (e nao `>=`) e o que preserva o comportamento de hoje no empate:
    "uma mola comprime sob forca de 10 N" casa "mol" (dentro de "mola") e
    "forca", 1 a 1, e forca continua vencendo por vir antes.
    """
    texto = _texto_busca_laboratorio(dados, materia)

    melhor, casados = None, 0
    for marcadores, titulo, usos in USOS_DIA_A_DIA_LABORATORIO:
        quantos = sum(1 for marcador in marcadores if marcador in texto)
        if quantos > casados:
            melhor, casados = (titulo, usos), quantos

    return melhor or USOS_PADRAO_LABORATORIO


def renderizar_contexto_pratico_laboratorio(dados: dict, materia: str = ""):
    titulo, usos = _usos_dia_a_dia_laboratorio(dados or {}, materia)
    st.markdown("**Uso no dia a dia**")
    st.markdown(f"**{titulo}**")
    for indice, (subtitulo, descricao) in enumerate(usos, start=1):
        st.markdown(f"**{indice}. {subtitulo}**")
        st.markdown(descricao)


def renderizar_alternativas_multipla_escolha(opcoes, key_prefix: str):
    for i, opt in enumerate(opcoes):
        opt_str = str(opt)
        if tem_matriz(opt_str):
            col_txt, col_btn = st.columns([3, 1])
            with col_txt:
                st.markdown(formatar_latex(opt_str))
            with col_btn:
                clicou = st.button("Selecionar", key=f"{key_prefix}_{i}", width="stretch")
        else:
            label = opt_str if opt_str.startswith("**") else _escapar_moeda_markdown(opt_str)
            clicou = st.button(label, key=f"{key_prefix}_{i}", width="stretch")
        if clicou:
            return i, opt_str
    return None, None


def renderizar_feedback_resposta(acertou: bool, resposta_correta: str, sucesso_msg: str, erro_msg_prefixo: str):
    if acertou:
        st.success(sucesso_msg)
        return
    if tem_matriz(str(resposta_correta)):
        st.error(erro_msg_prefixo)
        st.markdown(formatar_latex(str(resposta_correta)))
    else:
        st.error(f"{erro_msg_prefixo} {_escapar_moeda_markdown(resposta_correta)}")


def renderizar_feedback_pedagogico(
    *,
    acertou: bool,
    dados: dict,
    materia: str,
    resposta_aluno: str,
    resposta_correta: str,
):
    if acertou:
        return

    feedback = gerar_feedback_pedagogico(
        dados=dados,
        materia=materia,
        resposta_aluno=resposta_aluno,
        resposta_correta=resposta_correta,
    )
    st.markdown(
        (
            "<div class='edu-feedback-card'>"
            "<div class='edu-feedback-head'><span>🧭</span><span>Feedback para evoluir</span></div>"
            "<div class='edu-feedback-grid'>"
            "<div class='edu-feedback-item'>"
            "<div class='edu-feedback-label'>O que voce confundiu</div>"
            f"<div class='edu-feedback-text'>{_html_seguro(feedback['confundiu'])}</div>"
            "</div>"
            "<div class='edu-feedback-item'>"
            "<div class='edu-feedback-label'>Como evitar esse erro</div>"
            f"<div class='edu-feedback-text'>{_html_seguro(feedback['evitar'])}</div>"
            "</div>"
            "<div class='edu-feedback-item'>"
            "<div class='edu-feedback-label'>Treinar tema parecido</div>"
            f"<div class='edu-feedback-text'>{_html_seguro(feedback['treino'])}</div>"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def tempo_decorrido(timestamp_inicio):
    return round(time.time() - (timestamp_inicio or time.time()), 1)
