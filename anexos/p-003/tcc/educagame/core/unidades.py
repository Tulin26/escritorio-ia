"""As unidades de medida que o Laboratorio reconhece, num lugar so.

MELHORIA: estas listas moravam dentro de `services/ia/validacao.py`, onde
servem para uma coisa: cobrar que a alternativa de Fisica ou Quimica carregue
unidade de verdade.

Passaram a servir para outra, em `core/formula_formatting.py`: decidir se uma
palavra depois de um numero e unidade ou e prosa. Sem isso, "mol" e "cal" eram
contados como palavras e passos legitimos de Quimica viravam texto --

    n = \\frac{18 g}{44 g/mol} = 0,41 mol

-- enquanto o contrario tambem acontecia: qualquer palavra depois de um
numero era tratada como unidade, e "5 com" (de "... + 5 com f(x) = ...")
sumia da contagem de prosa, devolvendo uma frase inteira ao MathJax.

Ficam em `core/` e nao em `services/` por causa da direcao da dependencia:
`core` nao pode importar de `services`, e as duas precisam da mesma lista.
Duas copias divergiriam na primeira unidade nova que alguem acrescentasse de
um lado so.
"""

from __future__ import annotations

import re

UNIDADES_FISICA = frozenset({
    # comprimento
    "m", "cm", "mm", "dm", "km",
    # tempo
    "s", "ms", "min", "h",
    # velocidade e aceleracao
    "m/s", "km/h", "cm/s", "km/s", "m/min", "m/s2", "cm/s2",
    # massa
    "kg", "g", "mg", "t",
    # forca e pressao
    "n", "kn", "pa", "kpa", "atm", "bar", "mmhg", "n/m", "n.m",
    # trabalho, energia e potencia
    "j", "kj", "cal", "kcal", "wh", "kwh", "w", "kw", "cv", "hp",
    # eletricidade
    "v", "mv", "kv", "a", "ma", "ohm", "ω", "c", "f", "hz",
    # temperatura
    "°c", "°f", "k",
    # area, volume e densidade
    "m2", "cm2", "km2", "m3", "cm3", "l", "ml", "g/cm3", "kg/m3", "g/ml",
})

UNIDADES_QUIMICA = frozenset({
    "mol", "mols", "mol/l", "mol/kg", "g/mol", "mol/dm3",
    "g", "kg", "mg", "g/l", "g/ml", "g/cm3",
    "l", "ml", "dm3", "cm3", "m3",
    "j", "kj", "cal", "kcal", "kj/mol",
    "atm", "mmhg", "pa", "kpa",
    "k", "°c",
    "%", "u", "ppm",
})

UNIDADES = UNIDADES_FISICA | UNIDADES_QUIMICA

# A unidade vem colada ou logo depois do numero: "80 km/h", "20m/s",
# "58,5 g/mol", "12 °C". O token comeca por letra ou simbolo e pode
# seguir com barra, ponto e digito ("g/cm3", "m/s2", "n.m").
UNIDADE_APOS_NUMERO = re.compile(
    r"\d[\d.,]*\s*([a-zà-ÿ°ωΩ%][a-zà-ÿ0-9¹²³°ωΩ/.·-]*)",
    re.IGNORECASE,
)


def normalizar_unidade(texto: str) -> str:
    unidade = str(texto or "").strip().lower().rstrip(".,;:")
    # a IA escreve os dois jeitos: "m/s2" e "m/s²", "g/cm3" e "g/cm³"
    unidade = unidade.replace("¹", "1").replace("²", "2").replace("³", "3")
    unidade = unidade.replace("·", ".")
    unidade = unidade.replace("Ω", "ω")  # omega maiusculo -> minusculo
    return unidade


def eh_unidade(texto: str) -> bool:
    """O token e uma unidade conhecida (de Fisica ou de Quimica)?"""
    return normalizar_unidade(texto) in UNIDADES


# MELHORIA: a IA escreve unidade em LaTeX e com expoente negativo, e nas duas
# formas a unidade sumia da leitura. Visto nas recusas reais do Laboratorio
# (Render, 11/09/2026): "I = 3 \text{A}", "a = 4 \;\text{m/s}^2", "n = 0,43
# \text{ mol}", e na pergunta "58,5 g·mol⁻¹". O token de UNIDADE_APOS_NUMERO
# comeca por letra, entao "3 \text{A}" nao tinha unidade nenhuma -- e uma
# questao certa de Fisica caia em "laboratorio-sem-calculo". Em "mol·L⁻¹" o
# token parava em "mol·L", que nao e unidade.
#
# Aqui a notacao vira a forma que a lista ja conhece: "\text{A}" -> "A",
# "mol·L⁻¹" -> "mol/L", "m \cdot s^{-2}" -> "m/s2". Nenhum numero muda.
_COMANDO_DE_TEXTO = re.compile(r"\\(?:text|mathrm|mbox|rm)\s*\{([^{}]*)\}")
_ESPACO_LATEX = re.compile(r"\\[,;:! ]|~")
_SOBRESCRITO_PARA_DIGITO = str.maketrans("¹²³", "123")
# O separador exige LETRA antes: "mol·L⁻¹" e unidade, "10^{-3}" e conta.
_POR_EXPOENTE_NEGATIVO = re.compile(
    r"(?<=[a-zA-Z])\s*(?:·|\\cdot|\.|\s)\s*([a-zA-Z]+)"
    r"\s*(?:\^\s*\{\s*-\s*([123])\s*\}|\^\s*-\s*([123])|⁻([¹²³]))"
)


def _por_barra(achado: re.Match) -> str:
    expoente = next(grupo for grupo in achado.groups()[1:] if grupo).translate(_SOBRESCRITO_PARA_DIGITO)
    return f"/{achado.group(1)}{'' if expoente == '1' else expoente}"


def simplificar_unidade_latex(texto: str) -> str:
    """"3 \\text{A}" -> "3  A"; "mol·L⁻¹" -> "mol/L". So a notacao muda."""
    saida = _COMANDO_DE_TEXTO.sub(lambda achado: f" {achado.group(1)}", str(texto or ""))
    saida = _ESPACO_LATEX.sub(" ", saida)
    return _POR_EXPOENTE_NEGATIVO.sub(_por_barra, saida)
