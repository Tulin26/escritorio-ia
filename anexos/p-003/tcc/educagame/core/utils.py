"""
Módulo de utilitários compartilhados entre os módulos do EduGame.
Contém funções de formatação LaTeX, validação de fórmulas, chamada de IA etc.
"""

import re


def formatar_unidades_texto(texto: str) -> str:
    """Deixa unidades comuns legiveis em textos fora do MathJax."""
    txt = str(texto or "")
    substituicoes = {
        "cm^2": "cm²",
        "cm2": "cm²",
        "m^2": "m²",
        "m2": "m²",
        "cm^3": "cm³",
        "cm3": "cm³",
        "m^3": "m³",
        "m3": "m³",
        "m/s^2": "m/s²",
    }
    for bruto, bonito in substituicoes.items():
        txt = re.sub(r"\b" + re.escape(bruto) + r"\b", bonito, txt, flags=re.IGNORECASE)
    return txt


# ====================== FORMATAÇÃO LATEX ======================


def _formatar_moeda_latex(texto: str) -> str:
    return re.sub(r"\bR\s*(-?\d+(?:[.,]\d+)?)", r"\\mathrm{R\\$}\,\1", texto)


def _converter_parenteses_fracao_latex(texto: str) -> str:
    texto = re.sub(
        r"\(\s*(-?\d+(?:[.,]\d+)?)\s*/\s*(-?\d+(?:[.,]\d+)?)\s*\)",
        r"\\frac{\1}{\2}",
        texto,
    )
    return re.sub(
        r"\(\s*([A-Za-z0-9_\\\.\,\s\*]+?)\s*/\s*(-?\d+(?:[.,]\d+)?)\s*\)",
        lambda match: r"\frac{"
        + re.sub(r"\s*\*\s*", r" \\cdot ", match.group(1).strip())
        + "}{"
        + match.group(2)
        + "}",
        texto,
    )


def _converter_produto_sobre_denominador_latex(texto: str) -> str:
    fator = r"(?:\\mathrm\{[^}]+\}|[A-Za-z0-9_\\]+)"
    return re.sub(
        rf"(?<![,\.\d])({fator}(?:\s*\\cdot\s*{fator})+)\s*/\s*(-?\d+(?:[.,]\d+)?)",
        r"\\frac{\1}{\2}",
        texto,
    )


# Os caracteres da faixa Latin-1 que significam algo em matematica, com o
# comando LaTeX equivalente. Espaco em volta de proposito: sem ele "5±3" vira
# "5\pm3" e o "\pm3" e lido como um comando chamado "pm3", que nao existe.
#
# O que NAO esta aqui e deliberado: "²" e "³" ja sao tratados acima, e "×",
# "⋅", "·" viram "*" na linha anterior. Repetir aqui seria uma segunda regra
# para o mesmo caractere -- e a segunda nunca roda.
_SIMBOLOS_LATIN1_EM_LATEX = {
    "±": r" \pm ",
    "°": r"^\circ ",
    "µ": r" \mu ",   # U+00B5, o "sinal de micro"; o "μ" grego (U+03BC) passa
                     # pelo filtro sozinho, porque a faixa grega e aceita.
    "¹": "^1",
    "½": r" \frac{1}{2} ",
    "¼": r" \frac{1}{4} ",
    "¾": r" \frac{3}{4} ",
}


def _normalizar_entrada_formula(f: str) -> str:
    """Unicode, moeda, sinais de multiplicacao, apelidos e subscritos."""
    f = f.replace("x²", "x^2").replace("x³", "x^3")
    f = f.replace("²", "^2").replace("³", "^3")
    f = f.replace("$", "")
    f = _formatar_moeda_latex(f)
    # MELHORIA: "·" (ponto medio, U+00B7) e um caractere diferente de "×" e
    # "⋅" mas visualmente parecido, e a IA usa ele com frequencia como sinal
    # de multiplicacao. Sem tratar ele aqui, ele nao caia em nenhum dos
    # intervalos aceitos pelo filtro de caracteres mais abaixo e era apagado
    # em silencio, colando os dois numeros vizinhos (ex: "12·0,577" virava
    # "120,577", visto em producao no Laboratorio de trigonometria).
    f = f.replace("×", "*").replace("⋅", "*").replace("·", "*")

    # MELHORIA: o "·" acima nao era um caso isolado -- era um sintoma. O filtro
    # de caracteres (_remover_caracteres_nao_latex) aceita ASCII, depois pula
    # direto para À; TODA a faixa -¿ cai fora e e apagada em
    # silencio. Medido, o que a IA de fato escreve nessa faixa:
    #
    #   "x = (-b ± √Δ)/(2a)"  ->  "x = (-b √Δ)/(2a)"   Bhaskara sem o ±
    #   "x = (-7 ± 5)/4"      ->  "x = (-7 5)/4"       dois numeros colados
    #   "sen(30°) = 0,5"      ->  "sen(30) = 0,5"      grau vira radiano
    #   "T = 25 °C"           ->  "T = 25 C"           temperatura sem unidade
    #   "d = 5 µm"            ->  "d = 5 m"            micrometro vira METRO
    #
    # O ultimo e o pior: muda o valor por um fator de 10^6 sem avisar. E o "±"
    # e o da tela que abriu esta investigacao -- a formula mostrada ao aluno
    # nao produzia as duas raizes que o proprio passo seguinte apresentava.
    #
    # Traduzir para o comando LaTeX (e nao so preservar o caractere) e o que o
    # "·" ja fazia: o resto da funcao sabe lidar com \pm e ^\circ, e nao com a
    # faixa Latin-1. Os "²"/"³" logo acima seguem a mesma receita.
    for simbolo, comando in _SIMBOLOS_LATIN1_EM_LATEX.items():
        f = f.replace(simbolo, comando)

    # MELHORIA: so "sqrt{144}", ja com CHAVE, chegava certo ao MathJax. As
    # quatro grafias que a IA de fato escreve saiam quebradas:
    #
    #   sqrt(144)  ->  \sqrt(144)   radical sobre o VAZIO, e "(144)" ao lado
    #   raiz(144)  ->  raiz(144)    tipografado como as variaveis r·a·i·z
    #   √(144)     ->  √(144)       idem, radical sobre o vazio
    #   √144       ->  √144         o traco nao cobre o numero
    #
    # A conversao existia -- em formatar_latex(), que so o Streamlit usa. O
    # caminho do Flask (preparar_formula_latex) nunca teve. Antes de
    # _prefixar_comandos_latex de proposito: e ele quem poe a barra, e barra
    # em "sqrt(" so troca um erro por outro.
    f = re.sub(r"\\?(?:sqrt|raiz)\s*\(([^()]*)\)", r"\\sqrt{\1}", f, flags=re.IGNORECASE)
    f = re.sub(r"√\s*\(([^()]*)\)", r"\\sqrt{\1}", f)
    f = re.sub(r"√\s*(\d+(?:[.,]\d+)?|[A-Za-zΑ-Ωα-ω])", r"\\sqrt{\1}", f)

    aliases_formula = {
        "delta_s": r"\Delta s",
        "delta_t": r"\Delta t",
        "delta_v": r"\Delta v",
        "variacao_temperatura": r"\Delta T",
        "velocidade_media": "v",
        "velocidade_final": "v",
        "velocidade_inicial": "v_0",
        "deslocamento": r"\Delta s",
        "distancia": "d",
        "tempo": "t",
        "massa": "m",
        "forca": "F",
        "aceleracao": "a",
        "trabalho": "W",
        "potencia": "P",
        "energia_cinetica": "E_c",
        "energia_potencial": "E_p",
    }
    for longo, curto in aliases_formula.items():
        f = re.sub(
            r"\b" + re.escape(longo) + r"\b",
            lambda _m, valor=curto: valor,
            f,
            flags=re.IGNORECASE,
        )

    f = re.sub(r"\b([A-Za-z]+)_([A-Za-z0-9]{1,4})\b", r"\1_{\2}", f)
    f = _converter_parenteses_fracao_latex(f)
    return f


def _restaurar_latex_corrompido(f: str) -> str:
    """Desfaz escape perdido: '' virou form feed, '	' virou tab."""
    f = re.sub(r"\x0crac\s*\{", r"\\frac{", f)
    f = re.sub(r"\x0chi\b", r"\\phi", f)
    f = re.sub(r"\x09imes\b", r"\\times", f)
    f = re.sub(r"\x09au\b", r"\\tau", f)
    f = re.sub(r"\x09heta\b", r"\\theta", f)
    f = re.sub(r"\x08eta\b", r"\\beta", f)
    f = re.sub(r"\x08egin\b", r"\\begin", f)
    f = re.sub(r"(?<![A-Za-z\\])rac\s*\{", r"\\frac{", f)
    f = re.sub(r"(?<![A-Za-z\\])imes\b", r"\\times", f)

    f = f.strip()
    return f


# MELHORIA: visto na tela do Laboratorio em 15/09/2026, numa Bhaskara da IA: a
# formula chegou como "x = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}", com a barra
# escapada DUAS vezes, e o aluno leu "-bpmsqrtDelta" -- o MathJax toma "\\"
# por quebra de linha e desenha "pm", "sqrt" e "Delta" como letras. So o
# \frac saia certo, porque _normalizar_frac ja desfazia "\\frac"; os outros
# comandos nao tinham quem os consertasse.
#
# Desfaz so DUAS barras exatas antes de um comando conhecido. "\\x" no meio de
# \begin{cases} e quebra de linha de verdade (o banco usa em sistemas
# lineares) e fica; tres barras ("\\\end") tambem ficam: sao quebra + comando.
_COMANDOS_COM_BARRA_DOBRADA = (
    "frac", "dfrac", "tfrac", "cfrac", "sqrt", "pm", "mp", "cdot", "times", "div",
    "approx", "leq", "geq", "neq", "infty", "Delta", "delta", "alpha", "beta", "gamma",
    "lambda", "mu", "sigma", "pi", "theta", "omega", "Omega", "rho", "phi", "tau",
    "log", "ln", "sin", "cos", "tan", "circ", "left", "right", "text", "mathrm",
    "begin", "end", "quad",
)
_BARRA_DOBRADA_EM_COMANDO = re.compile(
    r"(?<!\\)\\\\(?!\\)(?=(?:"
    + "|".join(sorted(_COMANDOS_COM_BARRA_DOBRADA, key=len, reverse=True))
    + r")(?![A-Za-z]))"
)


def _desfazer_barra_dobrada(f: str) -> str:
    return _BARRA_DOBRADA_EM_COMANDO.sub(lambda _achado: "\\", f)


def _remover_caracteres_nao_latex(f: str) -> str:
    """Filtro de caracteres aceitos."""
    f = re.sub(
        r"[^\x20-\x7F\u00C0-\u024F\u0391-\u03C9\u2200-\u22FF"
        r"\{\}\[\]\(\)\\_\^\+\-\*\/\=\.\,\;\:\!\?]",
        "",
        f,
    )
    return f


def _desfazer_text_latex(f: str) -> str:
    """Tira 	ext{...} e restos de 'ext'."""
    f = re.sub(r"\[ext([^\]]*)\]", r"\1", f)
    f = re.sub(r"\\text\{([^}]*)\}", r"\1", f)
    f = re.sub(r"\bext([A-Z][a-zA-Z0-9+\-]*)", r"\1", f)
    return f


def _inserir_operadores(f: str) -> str:
    """Multiplicacao implicita e operadores colados."""
    f = re.sub(r"(?<![A-Za-z])tg(?=\s*\()", "tan", f, flags=re.IGNORECASE)
    f = re.sub(r"\s*\*\s*", r" \\cdot ", f)
    f = re.sub(r"([a-zA-Z0-9])cdot([a-zA-Z0-9])", r"\1 \\cdot \2", f)
    f = re.sub(r"([a-zA-Z0-9])times([a-zA-Z0-9])", r"\1 \\times \2", f)
    f = re.sub(r"(\\frac\{[^{}]+\}\{[^{}]+\})([A-Za-z0-9])", r"\1 \\cdot \2", f)
    f = re.sub(r"(\d)\(", r"\1 \\cdot (", f)
    f = re.sub(r"\)(\d)", r") \\cdot \1", f)
    f = re.sub(r"\)\(", r") \\cdot (", f)
    f = re.sub(r"(\d)\\sqrt", r"\1 \\cdot \\sqrt", f)
    f = re.sub(r"(\d)([A-Za-z])(?=[\s\+\-\=\)])", r"\1 \2", f)
    f = re.sub(r"(?<!\\)\b([A-Za-z])([A-Za-z])\b", r"\1 \\cdot \2", f)
    f = re.sub(r"\bp\s*\\cdot\s*H\b", "pH", f)
    f = _converter_produto_sobre_denominador_latex(f)
    return f


def _prefixar_comandos_latex(f: str) -> str:
    """Poe a barra invertida em cdot, pm, sqrt, sin..."""
    for op in [
        "cdot",
        "times",
        "div",
        "pm",
        "approx",
        "leq",
        "geq",
        "neq",
        "infty",
        "Delta",
        "mu",
        "lambda",
        "sigma",
        "pi",
        "theta",
        "log",
        "ln",
        "sin",
        "cos",
        "tan",
        "sqrt",
    ]:
        f = re.sub(r"(?<!\\)\b" + op + r"\b", r"\\" + op, f)
    return f


def _normalizar_frac(f: str) -> str:
    """Conserta rac escrito de varios jeitos."""
    f = re.sub(r"f{1,3}\s*frac\s*\{", r"\\frac{", f)
    # MELHORIA: aqui era so (?<!\\)frac -- "frac que nao vem depois de barra".
    # Em \dfrac, \tfrac e \cfrac o que vem antes de "frac" e a LETRA, nao a
    # barra, e a regra enfiava outra barra no meio: \dfrac virava \d\frac, e o
    # \d aparecia em vermelho na tela como comando desconhecido. Visto em
    # producao em 11/09/2026: "P = \dfrac{W}{t}", que a IA mandou certo.
    #
    # A trava e so para essas tres variantes, e nao para "qualquer letra
    # antes": "xfrac{1}{2}" hoje vira x\frac{1}{2}, que desenha x vezes a
    # fracao, e isso continua funcionando.
    f = re.sub(r"(?<!\\)(?<!\\[dtc])frac\s*\{", r"\\frac{", f)
    f = re.sub(r"\\{2,}frac", r"\\frac", f)
    return f


def _formatar_unidades_restantes(f: str) -> str:
    r"""Numero + unidade vira \,\mathrm{...}."""
    unidades_regex = [
        r"m/s\^2",
        r"m/s",
        r"cm\^2",
        r"cm2",
        r"m\^2",
        r"m2",
        r"kg",
        r"mol",
        r"g/L",
        r"g/ml",
        r"mL",
        r"ml",
        r"L",
        r"l",
        r"ohm",
        r"N",
        r"J",
        r"V",
        r"A",
        r"W",
        r"cal",
        r"m",
        r"s",
        r"g",
    ]

    def _formatar_unidade_latex(match):
        numero = match.group(1)
        unidade = match.group(2)
        unidade_fmt = unidade.replace("cm2", "cm^2").replace("m2", "m^2")
        return rf"{numero}\,\mathrm{{{unidade_fmt}}}"

    f = re.sub(
        r"(-?\d+(?:[.,]\d+)?)\s*(" + "|".join(unidades_regex) + r")\b",
        _formatar_unidade_latex,
        f,
    )
    return f


def _remover_rotulo_antes_da_formula(f: str) -> str:
    """Corta "Passo 2: x = 1" no dois-pontos, se o que vem antes nao e formula."""
    if ":" in f:
        partes = f.split(":", 1)
        antes, depois = partes[0].strip(), partes[1].strip()
        if (
            "=" not in antes
            and "\\" not in antes
            and "^" not in antes
            and "{" not in antes
        ):
            f = depois
    return f


def _proteger_unidades_e_simbolos(f: str) -> tuple[str, dict[str, str]]:
    """Troca unidade e simbolo quimico por marcador, para as regras de
    multiplicacao implicita nao os quebrarem. Devolve (texto, marcadores)."""
    unidades_protegidas = {}

    def _proteger_unidade_latex(match):
        numero = match.group(1)
        unidade = match.group(2)
        unidade_fmt = (
            unidade.replace("cm2", "cm^2")
            .replace("m2", "m^2")
            .replace("cm3", "cm^3")
            .replace("m3", "m^3")
        )
        marcador = f"§{len(unidades_protegidas)}§"
        unidades_protegidas[marcador] = rf"{numero}\,\mathrm{{{unidade_fmt}}}"
        return marcador

    unidades_protegidas_regex = [
        r"m/s\^2", r"m/s", r"cm\^3", r"cm3", r"cm\^2", r"cm2",
        r"m\^3", r"m3", r"m\^2", r"m2", r"kg", r"mol/L", r"mol",
        r"g/L", r"g/ml", r"mL", r"ml", r"L", r"l", r"ohm",
        r"cal", r"m", r"s", r"g",
    ]
    # MELHORIA: a busca ignora maiuscula e minuscula, e N, J, V, A e W estavam
    # nesta lista: o "2a" de Bhaskara virava 2\,\mathrm{a} (ampere) e a tela
    # mostrava "2 a" separado e em letra reta (visto em 15/09/2026, e ja listado
    # em 13/09 como "denominador 2 a"). Pelo mesmo caminho "2n - 1" virava
    # newton e "2v t", volt.
    #
    # As cinco sairam daqui sem fazer falta: _formatar_unidades_restantes, logo
    # depois, ja as formata -- e diferencia maiuscula. Medido em 25 formulas
    # com essas unidades (com e sem espaco, colada, em fracao, em produto): o
    # desenho e o mesmo com ou sem elas nesta lista.
    f = re.sub(
        r"(-?\d+(?:[.,]\d+)?)\s*(" + "|".join(unidades_protegidas_regex) + r")\b",
        _proteger_unidade_latex,
        f,
        flags=re.IGNORECASE,
    )

    # MELHORIA: simbolos quimicos de 2 letras (Na, Cl, Mg, Fe, Cu, Ca...) caiam
    # na mesma regra que insere "\cdot" entre letras adjacentes (pensada pra
    # multiplicacao implicita, tipo "ab"), virando "N·a + C·l" — muito comum
    # em equacoes quimicas antes dos elementos se combinarem num composto.
    # Protegidos aqui com o mesmo mecanismo de marcador usado pras unidades,
    # ja que o padrao de capitalizacao (maiuscula + minuscula) e exclusivo
    # de simbolos quimicos e nao aparece em multiplicacao algebrica normal.
    _simbolos_quimicos_2_letras = (
        "He Li Be Ne Na Mg Al Si Cl Ar Ca Sc Ti Cr Mn Fe Co Ni Cu Zn Ga Ge "
        "As Se Br Kr Rb Sr Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te Xe Cs Ba "
        "La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta Re Os Ir Pt Au "
        "Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa Np Pu Am Cm Bk Cf Es Fm Md No Lr "
        "OH"
    ).split()

    def _proteger_simbolo_quimico(match):
        marcador = f"§{len(unidades_protegidas)}§"
        unidades_protegidas[marcador] = match.group(0)
        return marcador

    f = re.sub(
        r"(?<![A-Za-z])(" + "|".join(_simbolos_quimicos_2_letras) + r")(?![A-Za-z])",
        _proteger_simbolo_quimico,
        f,
    )

    # MELHORIA: nao sao so simbolos quimicos que sofrem com essa regex -
    # qualquer palavra comum de 2 letras do portugues tambem (visto em
    # producao: uma frase de justificativa da IA, tipo "ajustado para duas
    # casas decimais, ou exatos e inteiro", virou "decimaiso · uexatos ·
    # einteiro" ilegivel). Isso acontece quando texto livre (nao-formula)
    # acaba passando por este formatador junto com a parte matematica.
    _palavras_portugues_2_letras = (
        "de da do na no em um eu ou as os me te se ao tu so ja la ca ai ha oi ta"
    ).split()

    f = re.sub(
        r"(?<![A-Za-z])(" + "|".join(_palavras_portugues_2_letras) + r")(?![A-Za-z])",
        _proteger_simbolo_quimico,
        f,
        flags=re.IGNORECASE,
    )
    return f, unidades_protegidas


def _restaurar_protegidos(f: str, unidades_protegidas: dict[str, str]) -> str:
    """Devolve as unidades e simbolos guardados, e junta a divisao entre
    duas grandezas numa fracao."""
    for marcador, unidade_latex in unidades_protegidas.items():
        f = f.replace(marcador, unidade_latex)
    f = re.sub(
        r"(-?\d+(?:[.,]\d+)?\\,\\mathrm\{[^}]+\})\s*/\s*(-?\d+(?:[.,]\d+)?\\,\\mathrm\{[^}]+\})",
        r"\\frac{\1}{\2}",
        f,
    )
    return f


def preparar_formula_latex(formula_raw: str) -> str:
    """Sanitiza qualquer string de formula para uso em LaTeX.

    MELHORIA: eram 258 linhas seguidas de "f = re.sub(...)". A ORDEM entre
    elas importa e ja causou bug -- proteger unidade DEPOIS de inserir
    multiplicacao implicita quebraria "12 m", e converter "tg" para "tan"
    DEPOIS da regra de duas letras renderizava "t·g(30)". Com as etapas
    nomeadas, essa ordem fica visivel aqui em vez de escondida no meio de
    duzentas linhas.
    """
    if not formula_raw:
        return ""

    f = str(formula_raw)
    f = _normalizar_entrada_formula(f)
    f = _restaurar_latex_corrompido(f)
    f = _desfazer_barra_dobrada(f)
    f = f.strip()
    f = _remover_caracteres_nao_latex(f)
    f = _desfazer_text_latex(f)

    # Daqui ate _restaurar_protegidos, unidades e simbolos viram marcadores:
    # sem isso, "Na" vira "N \cdot a" e "12 m" perde a unidade.
    f, protegidos = _proteger_unidades_e_simbolos(f)
    f = _inserir_operadores(f)
    f = _prefixar_comandos_latex(f)
    f = _normalizar_frac(f)
    f = _formatar_unidades_restantes(f)
    f = _restaurar_protegidos(f, protegidos)

    f = _remover_rotulo_antes_da_formula(f)
    return re.sub(r"\s{2,}", " ", f).strip()


# ====================== COMPAT STREAMLIT ======================
# MELHORIA: formatar_latex, limpar_formula_no_texto (usada por ela) e
# tem_matriz nao tem mais uso na parte Flask deste repositorio (que passou a
# formatar LaTeX de outro jeito, ver core/formula_formatting.py), mas
# continuam sendo importadas direto por st/ui/home_st.py, mode_common_st.py,
# rpg_helpers_st.py e tela_rpg_st.py (vinculadas na propria importacao do
# modulo: "formatar_latex = core_utils.formatar_latex" e
# "tem_matriz = core_utils.tem_matriz") — removê-las quebraria o app
# Streamlit no boot. Mantidas como estavam antes da sincronizacao com a main.


def limpar_formula_no_texto(texto: str, formula_principal: str = "") -> str:
    """Converte LaTeX cru em texto legível quando a fórmula vem dentro de um parágrafo."""
    if not texto:
        return ""

    txt = str(texto)
    txt = txt.replace("R$", "CURRENCYBRLTOKEN")
    formulas = [formula_principal] if formula_principal else []
    formulas.extend(
        re.findall(
            r"[A-Za-z][A-Za-z0-9_]*\s*=\s*(?:\\?frac\{[^}]+\}\{[^}]+\}|[^,.!?;]+)", txt
        )
    )

    for formula in formulas:
        formula = str(formula).strip().strip("$.")
        if len(formula) < 3:
            continue

        formula_legivel = formula
        formula_legivel = re.sub(
            r"\\?frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", formula_legivel
        )
        formula_legivel = re.sub(r"\\?sqrt\{([^{}]+)\}", r"√(\1)", formula_legivel)
        formula_legivel = re.sub(r"(\d)\s*√", r"\1·√", formula_legivel)
        formula_legivel = re.sub(r"(\))\s*√", r"\1·√", formula_legivel)
        for bruto, legivel in [
            ("\\cdot", "·"),
            ("\\times", "×"),
            ("\\Delta", "Δ"),
            ("\\pm", "±"),
            ("\\theta", "θ"),
            ("\\lambda", "λ"),
            ("\\pi", "π"),
        ]:
            formula_legivel = formula_legivel.replace(bruto, legivel)
        for bruto, legivel in [
            ("cdot", "·"),
            ("times", "×"),
            ("Delta", "Δ"),
            ("pm", "±"),
            ("theta", "θ"),
            ("lambda", "λ"),
            ("pi", "π"),
        ]:
            formula_legivel = re.sub(r"\b" + bruto + r"\b", legivel, formula_legivel)
        formula_legivel = re.sub(r"\s+", " ", formula_legivel).strip()
        txt = txt.replace(formula, formula_legivel)

    txt = re.sub(r"\\?frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", txt)
    txt = re.sub(r"\\?sqrt\{([^{}]+)\}", r"√(\1)", txt)
    txt = re.sub(r"(\d)\s*√", r"\1·√", txt)
    txt = re.sub(r"(\))\s*√", r"\1·√", txt)
    for bruto, legivel in [
        ("\\cdot", "·"),
        ("\\times", "×"),
        ("\\Delta", "Δ"),
        ("\\pm", "±"),
        ("\\theta", "θ"),
        ("\\lambda", "λ"),
        ("\\pi", "π"),
    ]:
        txt = txt.replace(bruto, legivel)
    for bruto, legivel in [
        ("cdot", "·"),
        ("times", "×"),
        ("Delta", "Δ"),
        ("pm", "±"),
        ("theta", "θ"),
        ("lambda", "λ"),
        ("pi", "π"),
    ]:
        txt = re.sub(r"\b" + bruto + r"\b", legivel, txt)
    txt = txt.replace("$", "")
    txt = txt.replace("CURRENCYBRLTOKEN", "R$")
    return re.sub(r"\s+", " ", txt).strip()


def formatar_latex(texto):
    """Formata texto com LaTeX para renderização no Streamlit."""
    if not texto:
        return ""
    txt = limpar_formula_no_texto(str(texto))

    # Corrige escapes JSON corrompidos
    txt = re.sub(r"\x0crac\s*\{", r"\\\\frac{", txt)
    txt = re.sub(r"\x0chi\b", r"\\\\phi", txt)
    txt = re.sub(r"\x09imes\b", r"\\\\times", txt)
    txt = re.sub(r"\x09heta\b", r"\\\\theta", txt)
    txt = re.sub(r"\x09au\b", r"\\\\tau", txt)
    txt = re.sub(r"\x08eta\b", r"\\\\beta", txt)
    txt = re.sub(r"\x0dho\b", r"\\\\rho", txt)
    txt = re.sub(r"\x08egin\b", r"\\\\begin", txt)
    txt = re.sub(r"\x08end\b", r"\\\\end", txt)
    txt = re.sub(r"(?<![a-zA-Z])rac\s*V\s*([A-Za-z])", r"\\\\frac{V}{", txt)
    txt = txt.replace("racV ", "\\frac{V}{")
    txt = txt.replace("sin(heta", "\\sin(\\theta")
    txt = txt.replace("heta_", "\\theta_")
    txt = txt.replace("R$", "CURRENCYBRLTOKEN")

    # Remove caracteres de outros idiomas
    txt = re.sub(
        r"[^\x00-\x7F\u00B0-\u024F\u0370-\u03FF\u2200-\u22FF$\\{}^_\+\-\*\/\=\(\)\[\]\s\.\,\;\:\!\?\'\"\n]",
        "",
        txt,
    )

    # Organização visual
    txt = txt.replace("Passo 1:", "\n\n**Passo 1:**")
    txt = txt.replace("Passo 2:", "\n\n**Passo 2:**")
    txt = txt.replace("Passo 3:", "\n\n**Passo 3:**")
    txt = txt.replace("Resultado:", "\n\n✨ **Resultado:**")

    # Remove rótulos indevidos
    termos_sujos = [
        r"Fórmula correta[:\s]*",
        r"Fórmula errada[:\s]*",
        r"Opção correta[:\s]*",
        r"Opção errada[:\s]*",
        r"Resposta correta[:\s]*",
        r"Resposta errada[:\s]*",
        r"Correta[:\s]*",
        r"Errada \d+[:\s]*",
        r"Errada[:\s]*",
    ]
    for padrao in termos_sujos:
        txt = re.sub(padrao, "", txt, flags=re.IGNORECASE)

    # Converte sqrt(...) para LaTeX
    txt = re.sub(
        r"(?<!\$)(?<!\\)\bsqrt\s*\(([^)]+)\)",
        lambda m: "$\\sqrt{" + m.group(1) + "}$",
        txt,
    )
    txt = re.sub(
        r"(?<!\$)\\sqrt\s*\(([^)]+)\)", lambda m: "$\\sqrt{" + m.group(1) + "}$", txt
    )
    txt = re.sub(r"√\(([^)]+)\)", lambda m: "$\\sqrt{" + m.group(1) + "}$", txt)
    txt = re.sub(r"√(\d+)", lambda m: "$\\sqrt{" + m.group(1) + "}$", txt)

    # Operadores LaTeX soltos
    operadores_inline = [
        r"\\times",
        r"\\cdot",
        r"\\approx",
        r"\\pm",
        r"\\leq",
        r"\\geq",
        r"\\neq",
        r"\\infty",
        r"\\sqrt\{[^}]+\}",
    ]
    for op in operadores_inline:
        txt = re.sub(r"(?<!\$)(" + op + r")(?!\$)", r"$\1$", txt)

    # Fórmulas completas
    txt = re.sub(r"(?<!\$)(\\frac\{[^}]+\}\{[^}]+\})(?!\$)", r"$\1$", txt)
    txt = re.sub(r"(?<!\$)(\\sqrt\{[^}]+\})(?!\$)", r"$\1$", txt)

    # Normaliza frac
    txt = re.sub(r"f{1,2}frac", "frac", txt)
    txt = re.sub(r"f\s*frac(\{)", r"frac\1", txt)
    txt = re.sub(r"(?<!\\)frac(\{)", r"\\frac\1", txt)
    txt = re.sub(r"\\{2,}frac", r"\\frac", txt)

    # Crases → LaTeX inline
    txt = re.sub(r"`(.*?)`", lambda m: "$" + m.group(1) + "$", txt)

    # Protege padrão número+letra+número
    txt = re.sub(r"(\d)([a-zA-Z])(\d)", r"\1\2·\3", txt)
    txt = re.sub(r"(\d)([a-zA-Z])(?=\s*[\+\-\=])", r"\1·\2 ", txt)

    # Subscritos
    txt = re.sub(r"_([A-Za-z0-9]+)(?!\})", r"_{\1}", txt)

    # Renderização automática
    txt = re.sub(r"(?<!\$)([A-Za-z]+_\{[^}]+\})(?!\$)", r"$\1$", txt)
    txt = re.sub(r"(?<!\$)(Δ[A-Za-z])(?!\$)", r"$\1$", txt)
    txt = re.sub(r"(?<!\$)(\\frac\{[^}]+\}\{[^}]+\})(?!\$)", r"$\1$", txt)
    txt = re.sub(r"(?<!\$)(\\sqrt\{[^}]+\})(?!\$)", r"$\1$", txt)

    # Matrizes
    txt = re.sub(
        r"\$?(\\begin\{(?:pmatrix|bmatrix|vmatrix|cases)\}.*?\\end\{(?:pmatrix|bmatrix|vmatrix|cases)\})\$?",
        r"\n\n$$\1$$\n\n",
        txt,
        flags=re.DOTALL,
    )

    txt = re.sub(r"(?<!\$)(\b[\w]+)\^(\d+)(?!\$)", r"$\1^{\2}$", txt)

    # Limpeza final
    txt = txt.replace(":math:", "").replace("f?:math:", "")
    txt = txt.replace("CURRENCYBRLTOKEN", r"R\$")
    return txt.strip().lstrip(":").strip()


def tem_matriz(texto):
    """Verifica se o texto contém ambiente LaTeX de matriz."""
    return bool(re.search(r"\\begin\{(?:pmatrix|bmatrix|vmatrix|cases)\}", str(texto)))
