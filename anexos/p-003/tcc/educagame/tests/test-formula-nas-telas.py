"""As telas que mostram fórmula como texto usam `formula_html`, e o ENEM mostra os passos.

Varredura de 13/09/2026 (ver core/expoentes_html.py::formula_html): ENEM e
Batalha com "x^2" e "10^{-3}" crus no enunciado; Laboratório com "m_soluto",
"P_0" e "35^{°}" na legenda e "m_{soluto} = 6 g" no passo em texto. E o
resultado do ENEM/Batalha mostrava "Identifique as grandezas, substitua os
valores na fórmula..." em vez dos passos que a questão já trazia.

Os passos são escritos em LaTeX ("P = \\frac{8}{100}\\cdot 160"): mostrados
como texto, 1.220 das 2.235 questões do ENEM teriam o comando cru na tela.
Por isso vão com o preparo do Laboratório -- prosa por `formula_html`, fórmula
entre $$ -- e as páginas do ENEM e da Batalha carregam o MathJax.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parents[1] / "web" / "templates"


@pytest.mark.parametrize(
    ("template", "trecho"),
    [
        ("enem.html", 'questao.get("pergunta", "")|unidades|formula_html'),
        ("enem.html", "alternativa|unidades|formula_html"),
        ("enem.html", 'set passos_texto = questao.get("passos_texto")'),
        ("boss_rush.html", 'questao.get("pergunta", "")|unidades|formula_html'),
        ("boss_rush.html", "alternativa|unidades|formula_html"),
        ("boss_rush.html", 'set passos_texto = questao.get("passos_texto")'),
        ("laboratorio.html", 'desafio.get("legenda_variaveis")|formula_html'),
        ("laboratorio.html", "passo.conteudo_texto|formula_html"),
        ("treino.html", 'questao.get("legenda_variaveis")|formula_html'),
        ("rpg.html", "passo.conteudo_texto|formula_html"),
        ("partials/result_card.html", "resultado.resposta_correta|unidades|formula_html"),
        ("partials/result_card.html", "passo.conteudo_texto|formula_html"),
        ("partials/result_card.html", "$$ {{ passo.conteudo_latex }} $$"),
    ],
)
def test_tela_usa_o_filtro(template, trecho):
    assert trecho in (TEMPLATES / template).read_text(encoding="utf-8")


@pytest.mark.parametrize("template", ["enem.html", "boss_rush.html"])
def test_tela_nao_carrega_mathjax(template):
    # MELHORIA: ENEM e Batalha nunca mostram formula nem passo a passo (ver
    # services/enem_service.py::_converter_questao_para_enem), entao nao ha
    # "$$ ... $$" pra desenhar -- o MathJax so ficava carregado sem uso.
    texto = (TEMPLATES / template).read_text(encoding="utf-8")

    assert "mathjax@3/es5/tex-svg.js" not in texto
    assert 'inlineMath: [["\\\\(", "\\\\)"]]' not in texto


def test_filtro_registrado_no_app(client):
    from flask import render_template_string

    with client.application.app_context():
        assert render_template_string("{{ v|formula_html }}", v="m_soluto e x^2") == "m<sub>soluto</sub> e x<sup>2</sup>"


@pytest.mark.parametrize("rota", ["enem_fla._questao_para_template", "boss_rush_fla._questao_template"])
def test_questao_do_enem_vinda_do_laboratorio_nao_mostra_formula(rota):
    # MELHORIA: Matemática e Ciências da Natureza reaproveitam o banco do
    # Laboratório (que TEM fórmula, subfórmulas e passos_resolucao em
    # LaTeX), mas _converter_questao_para_enem agora poda os quatro campos
    # -- o ENEM e a Batalha nunca mostram fórmula nem passo a passo, imitam
    # a prova de verdade. Ver services/enem_service.py::_converter_questao_para_enem.
    import importlib

    import services.enem_service as enem

    modulo, funcao = rota.split(".")
    preparar = getattr(importlib.import_module(f"web.routes.{modulo}"), funcao)
    questao = next(q for q in enem._fallback_autoral_por_area("Matematica e suas Tecnologias") if q.get("pergunta"))
    pronta = preparar(enem._normalizar_textos_questao(dict(questao)))

    assert pronta["passos_texto"] == [], f"{rota}: a questão do ENEM não deveria trazer passos"
    assert pronta["explicacao_texto"], f"{rota}: a explicação não pode ficar vazia"


def test_nenhum_passo_do_enem_deixa_comando_latex_na_prosa():
    """A medição que barrou a primeira versão, agora como regra: em todas as
    questões de Matemática do ENEM, comando LaTeX só dentro da fórmula."""
    import services.enem_service as enem
    from web.routes.enem_fla import _questao_para_template

    com_comando = []
    for questao in enem._fallback_autoral_por_area("Matematica e suas Tecnologias"):
        for passo in _questao_para_template(questao)["passos_texto"]:
            if re.search(r"\\[A-Za-z]{2,}", passo["conteudo_texto"]):
                com_comando.append(passo["conteudo_texto"][:60])

    assert com_comando == [], f"{len(com_comando)} passos com comando cru, ex.: {com_comando[:3]}"


def test_sem_passos_a_explicacao_fica_inteira():
    from web.routes.boss_rush_fla import _questao_template

    frase = "Identifique as grandezas, substitua os valores na formula e confira a unidade final."
    pronta = _questao_template({"pergunta": "?", "explicacao": [{"tipo": "texto", "conteudo": frase}], "passos_resolucao": []})

    assert pronta["passos_texto"] == []
    assert "Identifique as grandezas" in pronta["explicacao_texto"]


def test_cartao_de_resultado_desenha_os_passos(client):
    from flask import render_template

    with client.application.test_request_context():
        html = render_template(
            "partials/result_card.html",
            resultado={"acertou": False, "pontos": 0, "resposta_aluno": "4%", "resposta_correta": "5%", "feedback": None},
            explicacao_texto="",
            passos_texto=[
                {"titulo": "1º Passo", "conteudo_texto": "Com m_{soluto} = 6 g:", "conteudo_latex": r"C = \frac{6}{120}\cdot 100"},
            ],
        )

    assert "Resolução" in html
    # Fora da caixa da explicação, que preserva quebra de linha (pre-line):
    # dentro dela a indentação do template virava buraco em branco na tela.
    assert 'class="steps"' in html and 'class="result-explanation"' not in html
    assert "m<sub>soluto</sub>" in html and "m_{soluto}" not in html
    assert r"$$ C = \frac{6}{120}\cdot 100 $$" in html
