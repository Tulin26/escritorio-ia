from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from core.utils import preparar_formula_latex


def formatar_data_local(valor, formato: str = "%d/%m/%Y %H:%M") -> str:
    if not valor:
        return "-"
    if isinstance(valor, datetime):
        data = valor
    else:
        texto = str(valor).strip()
        if not texto:
            return "-"
        try:
            data = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return texto

    if data.tzinfo:
        data = data.astimezone(ZoneInfo("America/Sao_Paulo"))
    return data.strftime(formato)


def _separar_atribuicoes_coladas(texto: str) -> str:
    texto = str(texto or "").strip()
    unidades = r"(?:cm\^2|cm2|m\^2|m2|m/s\^2|m/s|kg|mol|g/L|mL|ml|cm|mm|ohm|N|J|V|A|W|m|s|g|L|l)"
    texto = re.sub(
        rf"(-?\d+(?:[.,]\d+)?)\s*({unidades})(?=\s*(?:\\+Delta\s*[A-Za-z]|[A-Za-zÀ-ÿ_]+)\s*=)",
        r"\1 \2, ",
        texto,
        flags=re.IGNORECASE,
    )
    texto = re.sub(r"([A-Za-zÀ-ÿ_]+)\s*=\s*", r"\1 = ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _parenteses_externos_cobrem_tudo(texto: str) -> bool:
    if not (texto.startswith("(") and texto.endswith(")")):
        return False

    profundidade = 0
    for indice, char in enumerate(texto):
        if char == "(":
            profundidade += 1
        elif char == ")":
            profundidade -= 1
            if profundidade == 0 and indice != len(texto) - 1:
                return False
    return profundidade == 0


def _remover_parenteses_externos(texto: str) -> str:
    texto = str(texto or "").strip()
    while _parenteses_externos_cobrem_tudo(texto):
        texto = texto[1:-1].strip()
    return texto


def _separar_divisao_top_level(expressao: str) -> tuple[str, str] | None:
    profundidade = 0
    for indice, char in enumerate(expressao):
        if char == "(":
            profundidade += 1
        elif char == ")":
            profundidade = max(0, profundidade - 1)
        elif char == "/" and profundidade == 0:
            numerador = expressao[:indice].strip()
            denominador = expressao[indice + 1 :].strip()
            if numerador and denominador:
                return numerador, denominador
    return None


def _normalizar_sqrt_parenteses_latex(expressao: str) -> str:
    texto = str(expressao or "")
    saida: list[str] = []
    indice = 0

    while indice < len(texto):
        match = re.match(r"\\?sqrt\s*\(", texto[indice:])
        if not match:
            saida.append(texto[indice])
            indice += 1
            continue

        inicio_conteudo = indice + match.end()
        profundidade = 1
        cursor = inicio_conteudo
        while cursor < len(texto) and profundidade > 0:
            if texto[cursor] == "(":
                profundidade += 1
            elif texto[cursor] == ")":
                profundidade -= 1
            cursor += 1

        if profundidade != 0:
            saida.append(texto[indice : inicio_conteudo])
            indice = inicio_conteudo
            continue

        conteudo = texto[inicio_conteudo : cursor - 1].strip()
        saida.append(rf"\sqrt{{{conteudo}}}")
        indice = cursor

    return "".join(saida)


def _formatar_fracao_longa_alinhada(formula_txt: str) -> str | None:
    if "=" not in formula_txt:
        return None

    esquerda, direita = formula_txt.split("=", 1)
    esquerda = esquerda.strip()
    direita = direita.strip()
    if len(direita) < 35 or not any(marcador in direita for marcador in ["sqrt", "\\sqrt", ")/("]):
        return None

    partes = _separar_divisao_top_level(direita)
    if not partes:
        return None

    numerador, denominador = partes
    # MELHORIA: guarda de seguranca. Um numerador/denominador de fracao de
    # verdade nunca contem um "=" — se contiver, o "/" que achamos nao
    # separava uma fracao, e sim emendava um trecho de texto corrido (varias
    # contas em sequencia, ou uma frase inteira colada com mais uma formula,
    # tipo "= 5, substituir na formula: a12 = ..."). Visto em producao no
    # Laboratorio de progressao aritmetica: sem essa guarda, o texto inteiro
    # (incluindo a parte em portugues) acabava dentro de um \frac{}{}, e o
    # MathJax renderiza tudo colado sem espaco nenhum ("Substituirnaformula"),
    # porque espacos soltos nao tem significado no modo matematico do LaTeX
    # fora de um \text{}.
    if "=" in numerador or "=" in denominador:
        return None
    numerador = _normalizar_sqrt_parenteses_latex(
        preparar_formula_latex(_remover_parenteses_externos(numerador))
    )
    denominador = _normalizar_sqrt_parenteses_latex(
        preparar_formula_latex(_remover_parenteses_externos(denominador))
    )
    esquerda_latex = preparar_formula_latex(esquerda)

    # MELHORIA: aqui saiam mais duas linhas, "numerador = ..." e
    # "denominador = ...", montadas com as MESMAS variaveis usadas dentro do
    # \frac acima -- ou seja, uma copia literal do que o aluno acabara de
    # ler, sem nenhuma informacao nova. No 3o passo de Bhaskara a tela
    # mostrava a fracao e logo abaixo repetia "numerador = [-(-7) ± √Δ]" e
    # "denominador = 2·2". Fica so a fracao.
    return rf"{esquerda_latex} = \frac{{{numerador}}}{{{denominador}}}"


def _preparar_formula_passo(formula: str) -> str:
    formula_txt = _separar_atribuicoes_coladas(formula)
    fracao_alinhada = _formatar_fracao_longa_alinhada(formula_txt)
    if fracao_alinhada:
        return fracao_alinhada

    # MELHORIA: a virgula separa atribuicoes ("V_i = 240, d = 15" vira duas
    # linhas), mas em portugues ela tambem e o separador DECIMAL -- e a
    # regra nao distinguia as duas. Visto na tela:
    #
    #     "V_f = 240 \cdot 0,85 = 204"   virava    V_f = 240 · 0
    #                                              85 = 204
    #
    # A conta aparecia partida ao meio no meio do numero, num passo a passo
    # que existe justamente para o aluno acompanhar o calculo.
    #
    # Virgula seguida de digito e decimal, sempre. So a que NAO e seguida de
    # digito separa. Isso tambem conserta o caso misto, "V_i = 2,5, d = 15",
    # que antes deixava de quebrar na virgula que era de verdade separadora.
    partes = [
        parte.strip()
        for parte in re.split(r"\s*(?:,(?!\d)|;|\be\b)\s*", formula_txt)
        if parte.strip()
    ]

    if len(partes) >= 2 and all("=" in parte for parte in partes):
        linhas = []
        for parte in partes:
            esquerda, direita = parte.split("=", 1)
            esquerda = esquerda.strip()
            direita = preparar_formula_latex(direita.strip())
            if re.fullmatch(r"[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ_ ]*", esquerda):
                esquerda = rf"\mathrm{{{esquerda}}}"
            else:
                esquerda = preparar_formula_latex(esquerda)
            linhas.append(rf"{esquerda} &= {direita}")
        return r"\begin{aligned}" + r"\\ ".join(linhas) + r"\end{aligned}"

    if "=" in formula_txt:
        esquerda, direita = formula_txt.split("=", 1)
        esquerda = esquerda.strip()
        direita = direita.strip()
        if re.fullmatch(r"[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ_ ]+", esquerda):
            return rf"\mathrm{{{esquerda}}} = {preparar_formula_latex(direita)}"

    return preparar_formula_latex(formula_txt)


# ====================== COMPAT STREAMLIT ======================
# MELHORIA: as 5 funcoes abaixo nao tem mais uso na parte Flask deste
# repositorio (a main removeu-as ao refatorar este arquivo, sem saber que
# st/ui/mode_common_st.py ainda as importa direto pra renderizar os passos
# de resolucao de RPG/Laboratorio/Oraculo/Treino/Escape Room/ENEM) —
# removê-las quebraria a importacao desses modulos no boot do Streamlit.
# Mantidas como estavam antes da sincronizacao com a main.
def _extrair_texto_e_formula(conteudo: str) -> tuple[str, str]:
    texto = str(conteudo or "").strip()
    if not texto or ":" not in texto:
        return "", ""

    prefixo, sufixo = texto.split(":", 1)
    prefixo = prefixo.strip()
    sufixo = sufixo.strip()
    if not prefixo or not sufixo:
        return "", ""

    if any(marcador in sufixo for marcador in ["\\", "^", "_", "{", "}"]):
        return prefixo, sufixo

    if "=" in sufixo and len(re.findall(r"-?\d+(?:[.,]\d+)?", sufixo)) >= 1:
        return prefixo, sufixo

    return "", ""


def _extrair_coeficientes_bhaskara(pergunta: str):
    texto = str(pergunta or "").lower()
    texto = texto.replace("x²", "x^2").replace(" ", "")
    match = re.search(r"([+-]?\d*)x\^2([+-]\d*)x([+-]\d+)=0", texto)
    if not match:
        return None

    a_txt, b_txt, c_txt = match.groups()

    def _coef(valor: str, padrao_um: bool = False) -> int:
        if valor in ("", "+"):
            return 1 if padrao_um else 0
        if valor == "-":
            return -1
        return int(valor)

    a = _coef(a_txt, padrao_um=True)
    b = _coef(b_txt)
    c = _coef(c_txt)
    return a, b, c


def _formatar_numero_bonito(valor: float) -> str:
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.2f}".rstrip("0").rstrip(".")


def _conteudo_passo_parece_formula(conteudo: str) -> bool:
    texto = str(conteudo or "").strip()
    if not texto:
        return False

    texto_sem_decimais = re.sub(r"\d+\.\d+", "NUM", texto)
    tokens = re.findall(r"[A-Za-z]+", texto)
    conectivos = {"e", "ou", "de", "do", "da", "dos", "das", "em", "por", "para", "com"}
    palavras_descritivas = {
        "identificar", "calcular", "resolver", "continuar", "simplificar", "substituir",
        "coeficientes", "equacao", "nesse", "caso", "portanto", "resultado",
        "primeiro", "segundo", "terceiro", "passo", "possibilidades", "valores",
    }
    if any(marcador in texto for marcador in ["\\", "^", "_", "{", "}"]):
        if len(tokens) < 2:
            return True
        if (
            "." not in texto_sem_decimais
            and all(len(token) <= 5 for token in tokens)
            and not any(token.lower() in conectivos or token.lower() in palavras_descritivas for token in tokens)
        ):
            return True
        return False

    unidades = {"m", "s", "kg", "g", "n", "j", "v", "a", "w", "cm", "mm", "l", "ml", "mol", "ohm", "c"}
    if len(tokens) >= 2 and any(token.lower() in palavras_descritivas for token in tokens):
        return False
    if any(token.lower() in conectivos for token in tokens):
        return False

    tem_operador = any(marcador in texto for marcador in ["=", "+", "-", "/", "*"])
    if "=" in texto and tem_operador:
        return True
    if any(token.lower() in unidades for token in tokens):
        return False

    funcoes_formula = {"sqrt", "frac", "sin", "cos", "tan", "log", "ln", "delta"}
    if len(tokens) >= 2:
        if (
            tem_operador
            and all(len(token) <= 5 for token in tokens)
            and any(token.lower() in funcoes_formula or len(token) == 1 for token in tokens)
            and "." not in texto_sem_decimais
        ):
            return True
        return False

    return tem_operador


def _inferir_subformulas_simbolicas(formula: str, pergunta: str) -> list[str]:
    formula_txt = str(formula or "").strip()
    pergunta_txt = str(pergunta or "").strip().lower()

    if any(
        trecho in pergunta_txt
        for trecho in ["bhaskara", "equação quadrática", "equacao quadratica", "2º grau", "2o grau"]
    ) or r"\sqrt{\Delta}" in formula_txt:
        return [r"\Delta = b^2 - 4ac"]

    return []
