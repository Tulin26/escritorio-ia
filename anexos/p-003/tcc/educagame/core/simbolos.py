"""Comandos LaTeX de símbolo traduzidos para o caractere Unicode.

MELHORIA: a legenda de variáveis chegava à tela com o comando cru --
"\\alpha: ângulo agudo procurado" em vez de "α: ângulo agudo procurado".
A fórmula acima dela renderiza certo porque passa pelo LaTeX; a legenda é
texto solto em três telas (`laboratorio.html`, `treino.html` e o
`st.caption` do Streamlit) e nenhuma delas converte nada.

Medido: das 50.900 questões dos bancos offline, **nenhuma** legenda tem
barra invertida. O problema é só das questões geradas por IA.

A legenda NÃO pode ser renderizada como LaTeX: ela é meia símbolo, meia
prosa em português ("α: ângulo agudo procurado; a: cateto oposto"), e
mandar a frase inteira para o renderizador sairia em itálico matemático,
que é exatamente o que a guarda de prosa de `core/formula_formatting.py`
existe para impedir. Por isso a troca é por caractere.

Só converte comando com barra invertida. `core/utils.py` também troca a
palavra solta (`\\bpi\\b` → π), e ali faz sentido porque o texto já é
sabidamente uma fórmula; em prosa seria armadilha -- "delta" é palavra
portuguesa ("o delta do rio"), e "beta" e "pi" aparecem em texto comum.
"""

from __future__ import annotations

import re

# Alfabeto grego inteiro: quem escreve a legenda é a IA, e não dá para
# adivinhar de qual letra ela vai precisar. A tabela antiga de
# core/utils.py tinha sete entradas e alpha não estava entre elas.
GREGAS_MINUSCULAS = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η",
    "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "omicron": "ο", "pi": "π", "rho": "ρ", "sigma": "σ",
    "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω",
}

GREGAS_MAIUSCULAS = {
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ",
    "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ",
    "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}

OPERADORES = {
    "cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥",
    "neq": "≠", "ne": "≠", "approx": "≈", "equiv": "≡", "propto": "∝",
    "sim": "~", "infty": "∞", "partial": "∂", "nabla": "∇",
    "sum": "Σ", "prod": "Π", "int": "∫", "sqrt": "√",
    "degree": "°", "circ": "°", "angle": "∠",
    "perp": "⊥", "parallel": "∥",
    "rightarrow": "→", "to": "→", "Rightarrow": "⇒",
    "leftarrow": "←", "Leftarrow": "⇐", "leftrightarrow": "↔",
    "in": "∈", "notin": "∉", "subset": "⊂", "supset": "⊃",
    "cup": "∪", "cap": "∩", "forall": "∀", "exists": "∃",
    "ldots": "…", "dots": "…", "cdots": "…",
}

SIMBOLOS_LATEX = {**GREGAS_MINUSCULAS, **GREGAS_MAIUSCULAS, **OPERADORES}

# \alpha, \Delta -- o [A-Za-z]+ pega o comando inteiro, entao \thetazinho
# nao vira "θzinho": o nome capturado e "thetazinho", que nao esta na
# tabela, e o trecho fica como estava.
_COMANDO = re.compile(r"\\([A-Za-z]+)")

# \text{...} e \mathrm{...} embrulham texto comum dentro de formula; na
# legenda so atrapalham.
_EMBRULHO_DE_TEXTO = re.compile(r"\\(?:text|mathrm|mathit|operatorname)\{([^{}]*)\}")

# $x$ e \(x\): delimitadores de modo matematico que a legenda nao usa.
_CIFRAO = re.compile(r"\$+")
_PARENTESE_MATEMATICO = re.compile(r"\\[()\[\]]")


def converter_simbolos_latex(texto) -> str:
    """Troca comandos LaTeX de símbolo pelo caractere correspondente.

    Comando fora da tabela fica como está, de propósito: `\\frac{a}{b}` não
    tem caractere único, e apagar a barra deixaria "frac{a}{b}", que é pior
    que o original. Um comando cru visível é um defeito que se enxerga; um
    texto mutilado em silêncio, não.
    """
    txt = str(texto or "")
    if "\\" not in txt and "$" not in txt:
        return txt

    txt = _EMBRULHO_DE_TEXTO.sub(r"\1", txt)
    txt = _PARENTESE_MATEMATICO.sub("", txt)
    txt = _COMANDO.sub(lambda m: SIMBOLOS_LATEX.get(m.group(1), m.group(0)), txt)
    txt = _CIFRAO.sub("", txt)
    return re.sub(r"[ \t]{2,}", " ", txt).strip()


# Sobrescrito escrito como LaTeX dentro da legenda. Visto em producao
# (11/09/2026), no Laboratorio:
#
#     θ = ângulo de elevação (35^{°})
#
# converter_simbolos_latex nao alcanca: sem barra invertida nem cifrao, o
# atalho de saida dela devolve o texto intacto antes de qualquer troca.
_SOBRESCRITOS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")
_SOBRESCRITO_COM_CHAVES = re.compile(r"\^\{\s*([^{}]*?)\s*\}")
_SOBRESCRITO_NUMERICO = re.compile(r"\^([+-]?\d+)")
# "35^\circ" e o jeito padrao de escrever grau em LaTeX; depois que
# converter_simbolos_latex troca \circ por °, sobra o circunflexo solto.
_GRAU_SOLTO = re.compile(r"\^\s*°")


def converter_sobrescritos(texto) -> str:
    """Troca sobrescrito LaTeX pelo caractere: `35^{°}` -> `35°`, `m^2` -> `m²`.

    So o que tem caractere unico: o grau, e numero inteiro com sinal.
    `r^{n-1}` nao tem, e fica como esta -- a mesma regra de
    converter_simbolos_latex: um sobrescrito cru visivel e um defeito que se
    enxerga; "rn-1" seria um texto mutilado em silencio.

    NAO e chamada de dentro de converter_simbolos_latex, de proposito. Aquela
    funcao tambem le as FORMULAS na validacao (services/ia/validacao.py,
    _nomes_usados_nas_formulas), e trocar `b^2` por `b²` la mudaria o que as
    regras enxergam. Esta mora so no caminho da legenda, que e texto de tela.

    Medido antes de ligar: nenhuma das 2.200 legendas do banco proprio tem
    circunflexo, entao ele nao muda; nas legendas reais da IA, a conversao nao
    alterou nenhuma declaracao lida nem o resultado da regra de legenda.
    """
    txt = str(texto or "")
    if "^" not in txt:
        return txt

    def por_chaves(m):
        conteudo = m.group(1)
        # So "°": quando esta funcao roda, \circ ja virou ° (a normalizacao
        # chama converter_simbolos_latex antes). Aceitar "circ" e "\circ"
        # aqui era codigo morto -- a mutacao arrancou os dois e nada mudou.
        if conteudo == "°":
            return "°"
        if re.fullmatch(r"[+-]?\d+", conteudo):
            return conteudo.translate(_SOBRESCRITOS)
        return m.group(0)

    txt = _SOBRESCRITO_COM_CHAVES.sub(por_chaves, txt)
    txt = _GRAU_SOLTO.sub("°", txt)
    return _SOBRESCRITO_NUMERICO.sub(lambda m: m.group(1).translate(_SOBRESCRITOS), txt)
