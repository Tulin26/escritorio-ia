r"""O passo a passo do banco do Laboratório mostra o raciocínio, não só o resultado.

Visto em 14/09/2026 pelo usuário, numa questão do ENEM (que usa este banco):
"A função f(x) = (x - 14)^2 + 15 tem vértice em qual ponto?". A resolução dizia
"Compare com f(x)=a(x-h)^2+k" e já dava "Vertice = (14, 15)" -- "não entendi
como ele chegou no resultado". Revisados todos os modelos: três tinham só dois
passos (vértice, determinante, combinatória) e outros pulavam a conta do meio
(distância sem 9 + 16 = 25, PG sem a potência, pH sem a regra do logaritmo...).

Os passos respeitam o validador (services/ia/validacao.py), que também roda
sobre este formato: cada conta fecha, e não há número na prosa antes de um "="
-- o avaliador colaria os dígitos ("Dobrar 3 vezes: 2^3 = 8" viraria 32^3).
"""

from __future__ import annotations

import re

import pytest

import services.banks.laboratorio as lab
from core.expoentes_html import formula_html
from services.ia.validacao import _passo_final_diverge_do_calculo_anterior, _resultado_aritmetico_incorreto
from web.routes.flask_helpers_fla import passos_para_template

# nome: (gerador, tipo, quantidade de tipos do gerador)
MODELOS = {
    "PA": (lab._matematica, 1, 22),
    "PG": (lab._matematica, 2, 22),
    "juros": (lab._matematica, 5, 22),
    "distancia": (lab._matematica, 9, 22),
    "vertice": (lab._matematica, 11, 22),
    "exponencial": (lab._matematica, 12, 22),
    "determinante": (lab._matematica, 14, 22),
    "combinatoria": (lab._matematica, 15, 22),
    "energia cinetica": (lab._fisica, 7, 10),
    "pH": (lab._quimica, 3, 10),
    "gases": (lab._quimica, 9, 10),
    "equacao EF": (lab._matematica_ef, 4, 10),
}


def _variantes(nome: str) -> list[dict]:
    gerar, tipo, tipos = MODELOS[nome]
    return [gerar(tipo + tipos * j) for j in range(20)]


def _conteudos(questao: dict) -> list[str]:
    return [p["conteudo"] for p in questao["passos_resolucao"]]


@pytest.mark.parametrize("nome", MODELOS)
def test_modelo_tem_pelo_menos_tres_passos(nome):
    for questao in _variantes(nome):
        assert len(questao["passos_resolucao"]) >= 3, (nome, _conteudos(questao))


@pytest.mark.parametrize("nome", MODELOS)
def test_as_contas_dos_passos_passam_no_validador(nome):
    for questao in _variantes(nome):
        assert not _resultado_aritmetico_incorreto(questao), (nome, _conteudos(questao))
        assert not _passo_final_diverge_do_calculo_anterior(questao), (nome, _conteudos(questao))


@pytest.mark.parametrize("nome", MODELOS)
def test_a_prosa_do_passo_nao_mostra_latex_cru(nome):
    gerar, tipo, _ = MODELOS[nome]
    for passo in passos_para_template(gerar(tipo)["passos_resolucao"]):
        texto = re.sub(r"<[^>]+>", "", str(formula_html(passo["conteudo_texto"])))
        assert not re.search(r"\\[A-Za-z]{2,}|[\^_]\{", texto), (nome, texto)


@pytest.mark.parametrize(
    ("gerar", "trecho", "rotulo"),
    [
        (lambda: lab._matematica(1), r"6\cdot 4 = 24", "PA: os saltos de razão"),
        (lambda: lab._matematica(2), "3^{4} = 81", "PG: a potência da razão"),
        (lambda: lab._matematica(5), r"\frac{3}{100} = 0,03", "juros: a taxa em decimal"),
        (lambda: lab._matematica(9), "9 + 16 = 25", "distância: a soma dos quadrados"),
        (lambda: lab._matematica(9), r"\sqrt{25} = 5", "distância: a raiz"),
        (lambda: lab._matematica(12), "2^3 = 8", "exponencial: quantas vezes dobra"),
        (lambda: lab._matematica(14), r"2\cdot 5 = 10", "determinante: diagonal principal"),
        (lambda: lab._matematica(14), r"2\cdot 3 = 6", "determinante: a outra diagonal"),
        (lambda: lab._fisica(7), "5^2 = 25", "energia cinética: a velocidade ao quadrado"),
        (lambda: lab._quimica(3), r"\log(10^{-3}) = -3", "pH: a regra do logaritmo"),
        (lambda: lab._quimica(9), r"0,082\cdot 300 = 24,6", "gases: R vezes T"),
    ],
)
def test_a_conta_do_meio_aparece(gerar, trecho, rotulo):
    assert trecho in " ".join(_conteudos(gerar())), rotulo


def test_o_vertice_explica_de_onde_vem_h_e_k():
    questao = lab._matematica(11 + 22 * 11)  # f(x) = (x - 14)^2 + 15, a da tela
    texto = " ".join(_conteudos(questao))

    assert "(x - 14)^2 + 15" in questao["pergunta"]
    assert "(h, k)" in texto, "falta dizer que o vértice da forma a(x - h)^2 + k é (h, k)"
    assert "h = 14" in texto and "k = 15" in texto
    assert _conteudos(questao)[-1] == "V = (14, 15)"


def test_a_combinatoria_explica_por_que_divide_por_dois():
    texto = " ".join(_conteudos(lab._matematica(15)))  # 6 alunos

    assert "ordem nao importa" in texto
    assert r"6\cdot 5 = 30" in texto and r"\frac{30}{2} = 15" in texto


def test_a_equacao_do_fundamental_explica_a_operacao():
    assert "dos dois lados" in " ".join(_conteudos(lab._matematica_ef(4)))


def test_o_resultado_final_nao_poe_palavra_dentro_da_formula():
    # "P = 960 bacterias" ia para o MathJax, que desenha a palavra em itálico e
    # sem acento.
    final = passos_para_template(lab._matematica(12)["passos_resolucao"])[-1]

    assert not re.search(r"[a-z]{4,}", final["conteudo_latex"]), final["conteudo_latex"]
