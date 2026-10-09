"""Expoente desenhado com <sup> em texto que vai para a tela sem MathJax.

MELHORIA: no Oráculo, o enunciado chegava ao aluno assim:

    Sobre a função exponencial f(x)=a^x, com base a>1, ...

com o circunflexo cru. Visto em produção em 11/09/2026.

Por que não resolve com caractere, como `expoentes_em_sobrescrito`
(web/routes/flask_helpers_fla.py): aquela troca só expoente NUMÉRICO, e com
letra não há como -- nem toda letra tem versão sobrescrita no Unicode (não
existe "q" sobrescrito). O `<sup>` do HTML serve para qualquer uma.

Por que só em tela sem MathJax: dentro de `$...$` o "^" é do MathJax, e um
`<sup>` no meio quebraria a fórmula. Treino, Laboratório e RPG carregam
MathJax; o Oráculo não. Por isso isto é um filtro próprio, aplicado onde se
sabe que pode, e não uma mudança no filtro `unidades`, que é usado em onze
lugares.
"""

from __future__ import annotations

import re

from markupsafe import Markup, escape

# Base: letra, dígito ou fecha-parêntese -- o mesmo critério de
# expoentes_em_sobrescrito. "a^x", "2^10", "(x+1)^2".
_BASE = r"(?<=[\w\)\]])"

# "e^{-x}", "x^{n+1}": sinal opcional e termos de letra ou dígito ligados por
# + ou -. Com espaço ou qualquer outra coisa dentro das chaves, fica cru.
_COM_CHAVES = re.compile(_BASE + r"\^\{([+\-]?[A-Za-z0-9]+(?:[+\-][A-Za-z0-9]+)*)\}")

# "a^x", "2^10", "e^-x": sinal opcional e um número inteiro ou UMA letra. Uma
# letra só, porque em "x^2y" o expoente é o 2, e o y fica na linha.
_SIMPLES = re.compile(_BASE + r"\^([+\-]?(?:\d+|[A-Za-z]))")


def expoentes_html(texto) -> Markup:
    """Escapa o texto e desenha o expoente: `a^x` -> `a<sup>x</sup>`.

    Escapar ANTES é o que torna isto seguro: o texto vem da IA e vai para a
    tela como HTML, e só as tags `<sup>` que esta função cria saem sem escape.

    Expoente que não cabe nas duas formas fica cru e visível -- a mesma regra
    de `core/simbolos.py`: um defeito que se enxerga é melhor que um texto
    mutilado em silêncio.
    """
    return Markup(_desenhar_expoentes(str(escape(str(texto or "")))))


def _desenhar_expoentes(seguro: str) -> str:
    """Recebe texto JA escapado."""
    if "^" not in seguro:
        return seguro
    seguro = _COM_CHAVES.sub(lambda m: f"<sup>{m.group(1)}</sup>", seguro)
    return _SIMPLES.sub(lambda m: f"<sup>{m.group(1)}</sup>", seguro)


# "35^{°}" e "35^°": o grau ja e sinal elevado -- em <sup> ficaria minusculo.
_GRAU = re.compile(r"\^\{?°\}?")

# Indice: "m_{solução}", "m_soluto", "P_0". A base e UMA letra solta: colada em
# palavra ("nome_completo") e identificador, e fica como esta. Dentro das
# chaves nada de espaco nem & -- este ultimo para nao partir entidade HTML.
_INDICE_COM_CHAVES = re.compile(r"(?<!\w)([A-Za-z])_\{([^{}\s<>&]{1,20})\}")
_INDICE_SIMPLES = re.compile(r"(?<!\w)([A-Za-z])_([A-Za-zÀ-ÿ0-9]{1,12})(?!\w)")


def formula_html(texto) -> Markup:
    """Expoente E indice em texto que vai para a tela sem MathJax.

    MELHORIA: a varredura de 13/09/2026 (cada questao dos bancos passada pela
    mesma preparacao e pelos mesmos filtros de cada tela) achou formula crua
    onde o aluno le texto corrido:

      * ENEM e Batalha, enunciado: "x^2 - 6x + 8 = 0" em 84 questoes e
        "[H+] = 10^{-3} mol/L" em 44 -- as telas so usavam `unidades`;
      * Laboratorio, legenda: "m_soluto: massa do soluto", "P_0 = preco
        original", "(35^{°})" -- 44 do banco e 2 reais da IA;
      * Laboratorio, passo que sobra como texto: "m_{soluto} = 6 g" e
        "2^x = 4" -- 64 do banco.

    `expoentes_html` (o do Oraculo) so desenha expoente; aqui entra o indice.
    Mesma regra de seguranca: escapa ANTES, e so as tags criadas aqui saem sem
    escape. O que nao casa fica cru e visivel.
    """
    seguro = str(escape(str(texto or "")))
    seguro = _GRAU.sub("°", seguro)
    seguro = _desenhar_expoentes(seguro)
    if "_" in seguro:
        seguro = _INDICE_COM_CHAVES.sub(lambda m: f"{m.group(1)}<sub>{m.group(2)}</sub>", seguro)
        seguro = _INDICE_SIMPLES.sub(lambda m: f"{m.group(1)}<sub>{m.group(2)}</sub>", seguro)
    return Markup(seguro)
