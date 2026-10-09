"""Expoente e índice de fórmula nas telas sem MathJax.

Varredura de 13/09/2026: ENEM/Batalha com "x^2 - 6x + 8 = 0" cru em 84
questões e "10^{-3}" em 44; Laboratório com legenda "m_soluto", "P_0",
"35^{°}" (44 do banco + 2 reais) e passo em texto "m_{soluto} = 6 g",
"2^x = 4" (64). Ver core/expoentes_html.py::formula_html.
"""

from __future__ import annotations

import pytest

from core.expoentes_html import expoentes_html, formula_html


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("Resolva a equação x^2 - 6x + 8 = 0.", "Resolva a equação x<sup>2</sup> - 6x + 8 = 0."),
        ("f(x) = (x - 14)^2 + 15", "f(x) = (x - 14)<sup>2</sup> + 15"),
        ("se [H+] = 10^{-3} mol/L", "se [H+] = 10<sup>-3</sup> mol/L"),
        ("m_soluto: massa do soluto", "m<sub>soluto</sub>: massa do soluto"),
        ("m_{solução} = 120 g", "m<sub>solução</sub> = 120 g"),
        ("P_0 = preço original", "P<sub>0</sub> = preço original"),
        ("ângulo de elevação (35^{°})", "ângulo de elevação (35°)"),
        ("Procure x tal que 2^x = 4.", "Procure x tal que 2<sup>x</sup> = 4."),
    ],
)
def test_desenha_expoente_e_indice(bruto, esperado):
    assert str(formula_html(bruto)) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "O campo nome_completo do aluno",
        "Custa R$ 5,00 à vista.",
        "Qual é a raiz (o zero) da função?",
    ],
)
def test_texto_comum_fica_como_esta(texto):
    assert str(formula_html(texto)) == texto


def test_escapa_antes_de_desenhar():
    saida = str(formula_html("<script>alert(1)</script> v_0"))

    assert "<script>" not in saida
    assert "&lt;script&gt;" in saida
    assert "v<sub>0</sub>" in saida


def test_o_filtro_do_oraculo_nao_mudou():
    # expoentes_html continua só com expoente: o índice é do filtro novo.
    assert str(expoentes_html("m_soluto e a^x")) == "m_soluto e a<sup>x</sup>"
