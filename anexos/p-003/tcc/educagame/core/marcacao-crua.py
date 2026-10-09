r"""Marcação que vaza para a tela: markdown, `\text{}` e matriz em colchetes.

Achado 4.4 do relatório de QA de 23/09/2026 -- "fórmulas e símbolos quebrados
na renderização". Três dos casos listados lá não são do renderizador: chegam
assim no dado da questão, e nenhuma tela tem como desenhá-los.

  * `*should*` -- a IA responde em markdown quando o prompt pede texto puro.
    Nas telas o asterisco fica visível, porque nada aqui interpreta markdown.
  * `a = 5 \text{ cm}` -- a unidade escrita em LaTeX no meio da PROSA. Dentro
    de `$$ ... $$` o MathJax desenha; solta no texto, o comando aparece cru.
    É o mesmo defeito do "a = 23c · m" do relatório, visto do outro lado: lá
    a unidade virou produto de variáveis porque a prosa foi para o MathJax.
  * `[[6, 2], [3, 9]]` -- notação de lista de listas para uma matriz. Não é
    como se escreve matriz em lugar nenhum: nem em LaTeX, nem em livro.

Medido em 28/09/2026 (50.900 questões dos bancos + 554 reais da IA): 2 textos
com markdown, 3 com `\text{}` e 21 com matriz crua -- 20 deles do banco do
Laboratório, corrigidos na fonte. O volume é pequeno, mas cada um deles torna
UMA questão ilegível para o aluno que a recebeu.

O que esta limpeza NÃO faz, de propósito:

  * não roda nos passos de resolução, que são LaTeX de verdade e vão para o
    MathJax (`passos_para_template`): trocar `\sqrt` por "√" ali quebraria o
    desenho da fórmula;
  * não mexe no cifrão. `converter_simbolos_latex` (core/simbolos.py) apaga
    `$`, e em prosa isso comeria o "R$" de todo enunciado de dinheiro;
  * não inventa desenho para o que não tem caractere único -- a mesma regra
    de core/simbolos.py: comando cru visível é defeito que se enxerga, texto
    mutilado em silêncio não.
"""

from __future__ import annotations

import re

from core.simbolos import SIMBOLOS_LATEX

# `*should*` e `**importante**`. As duas pontas coladas no conteúdo, e fora
# dele nada de letra nem dígito: é isso que separa ênfase de multiplicação.
# "V = 3 * 4 * 5" tem espaço depois do asterisco; "2*x*3" tem dígito colado
# do lado de fora. Nenhum dos dois casa.
_ENFASE_MARKDOWN = re.compile(r"(?<![\w*])(\*{1,2})(?=[^\s*])([^*\n]{1,80}?)(?<=[^\s*])\1(?![\w*])")

# `\text{ cm}`, `\mathrm{mol}`: embrulho de texto comum dentro de fórmula.
_EMBRULHO_DE_TEXTO = re.compile(r"\\(?:text|mathrm|mathit|mbox|rm|operatorname)\s*\{([^{}]*)\}")

# `\,` `\;` `\:` `\!` e `~`: espaçamento de LaTeX, invisível na fórmula e
# visível na prosa.
_ESPACO_LATEX = re.compile(r"\\[,;:!]|(?<!\\)~")

_COMANDO = re.compile(r"\\([A-Za-z]+)")

# Só o que tem caractere único E não é estrutura de fórmula. `\frac` e
# `\sqrt` ficam de fora: viram "frac{a}{b}" e "√{x}", piores que o original.
_ESTRUTURA_DE_FORMULA = frozenset({"sqrt", "sum", "prod", "int"})
_SIMBOLOS_EM_PROSA = {
    nome: simbolo for nome, simbolo in SIMBOLOS_LATEX.items() if nome not in _ESTRUTURA_DE_FORMULA
}

# `[[2, 2], [3, 5]]`: duas ou mais linhas de números entre colchetes.
_LINHA_DE_MATRIZ = r"\[\s*-?\d+(?:[.,]\d+)?(?:\s*,\s*-?\d+(?:[.,]\d+)?)*\s*\]"
_MATRIZ_CRUA = re.compile(rf"\[\s*({_LINHA_DE_MATRIZ}(?:\s*,\s*{_LINHA_DE_MATRIZ})+)\s*\]")
_FALA_DE_MATRIZ = re.compile(r"\bmatriz|\bmatrizes\b|\bdeterminante", re.IGNORECASE)


def _sem_enfase_markdown(texto: str) -> str:
    # Uma segunda guarda, exigindo letra dentro dos asteriscos, foi tentada e
    # arrancada: a mutação mostrou que nenhum caso real precisava dela (a
    # regra de espaço acima já pega toda multiplicação), e ela ainda estragava
    # o negrito de número -- "**42**" ficava com os asteriscos na tela.
    return _ENFASE_MARKDOWN.sub(r"\2", texto)


def _sem_latex_de_prosa(texto: str) -> str:
    saida = _EMBRULHO_DE_TEXTO.sub(lambda achado: f" {achado.group(1).strip()}", texto)
    saida = _ESPACO_LATEX.sub(" ", saida)
    saida = _COMANDO.sub(lambda achado: _SIMBOLOS_EM_PROSA.get(achado.group(1), achado.group(0)), saida)
    return re.sub(r"[ \t]{2,}", " ", saida)


def matriz_em_palavras(texto: str) -> str:
    """`matriz [[6, 2], [3, 9]]` -> `matriz de linhas (6, 2) e (3, 9)`.

    Só quando o texto FALA de matriz. Uma lista de listas em outro assunto
    (coordenadas, pares ordenados, tabela de dados) fica como está: ali o
    colchete pode ser a notação certa, e trocar por "linhas" seria erro.
    """
    if "[[" not in texto.replace(" ", "") or not _FALA_DE_MATRIZ.search(texto):
        return texto

    def trocar(achado: re.Match) -> str:
        linhas = [
            "(" + ", ".join(valor.strip() for valor in linha.strip(" []").split(",")) + ")"
            for linha in re.findall(_LINHA_DE_MATRIZ, achado.group(1))
        ]
        # Duas linhas no mínimo é exigência do próprio `_MATRIZ_CRUA`: uma
        # lista sozinha ("[[1, 2]]") não casa, então não há caso de uma linha
        # para tratar aqui.
        return "de linhas " + ", ".join(linhas[:-1]) + f" e {linhas[-1]}"

    return _MATRIZ_CRUA.sub(trocar, texto)


def limpar_marcacao_crua(texto) -> str:
    """Tira da PROSA o que nenhuma tela desenha. Fórmula e passo não passam aqui."""
    bruto = str(texto or "")
    if not bruto:
        return bruto

    saida = bruto
    if "*" in saida:
        saida = _sem_enfase_markdown(saida)
    if "\\" in saida or "~" in saida:
        saida = _sem_latex_de_prosa(saida)
    if "[" in saida:
        saida = matriz_em_palavras(saida)
    return saida
