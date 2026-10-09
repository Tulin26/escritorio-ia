r"""Markdown, `\text{}` e matriz em colchetes não chegam ao aluno.

Achado 4.4 do relatório de QA de 23/09/2026 ("fórmulas e símbolos quebrados
na renderização"), parte mecânica. Varrido o corpus real em 28/09/2026 --
50.900 questões dos bancos offline e as 554 questões de IA gravadas -- para
separar o que é defeito de verdade do que só parece:

  * `[[6, 2], [3, 9]]`: 20 questões do banco do Laboratório (uma família de
    determinante) e 1 da IA. Corrigido na fonte do banco; na IA, a limpeza
    reescreve.
  * `Delta T: variacao`: 132 questões do Laboratório traziam a letra grega
    POR EXTENSO na legenda -- o dicionário de core/simbolos.py só troca o
    comando com barra (`\Delta`), e de propósito: "delta" é palavra
    portuguesa ("o delta do rio"). Corrigido na fonte.
  * `*should*` (2 textos) e `a = 5 \text{ cm}` (3 textos): só da IA.
  * Decimal misturado (ponto na resolução, vírgula nas alternativas): ZERO
    ocorrências hoje, nos dois corpora. O caso do relatório não se repete, e
    por isso não há regra nenhuma para ele -- converter ponto em vírgula no
    escuro estragaria "R$ 1.800,00".

E o defeito de maior volume não estava no dado, e sim na tela: as listas de
revisão (ENEM, Batalha, Treino, Escape Room e Progresso) imprimiam o
enunciado sem filtro nenhum, enquanto a MESMA questão aparecia formatada na
tela de responder. 260 questões dos bancos e 34 das 554 da IA mostravam
"357 cm^2" ou "x^2 - 6x + 8" ali.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.marcacao_crua import limpar_marcacao_crua
from services.ia.normalizacao import normalizar_payload_questao

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATES = RAIZ / "web" / "templates"
B = chr(92)


# --------------------------------------------------------------------------
# O que sai


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        # O caso real do relatório, na explicação de Inglês.
        ("The modal verb *should* is used to advise.", "The modal verb should is used to advise."),
        ("O ponto **mais importante** é a unidade.", "O ponto mais importante é a unidade."),
        # Negrito de número também sai: o asterisco não tem o que fazer na tela.
        ("O resultado é **42** unidades.", "O resultado é 42 unidades."),
        (f"a = 5 {B}text{{ cm}}", "a = 5 cm"),
        (f"a = 4 {B};{B}text{{m/s}}^2", "a = 4 m/s^2"),
        (f"A variação {B}Delta T foi de 5 C.", "A variação Δ T foi de 5 C."),
        (
            "Qual é o determinante da matriz [[6, 2], [3, 9]]?",
            "Qual é o determinante da matriz de linhas (6, 2) e (3, 9)?",
        ),
        (
            "Determinante da matriz [[1, 2, 3], [4, 5, 6], [7, 8, 9]]:",
            "Determinante da matriz de linhas (1, 2, 3), (4, 5, 6) e (7, 8, 9):",
        ),
    ],
)
def test_marcacao_crua_sai_do_texto(bruto, esperado):
    assert limpar_marcacao_crua(bruto) == esperado


# --------------------------------------------------------------------------
# O que NÃO sai -- cada um destes é um jeito de estragar questão boa


@pytest.mark.parametrize(
    "texto",
    [
        # Multiplicação, não ênfase: 44 passos do banco escrevem assim.
        "V = 3 * 4 * 5 = 60",
        "Calcule 2*x*3 para x = 5",
        # O cifrão do dinheiro. converter_simbolos_latex apaga "$", e por isso
        # não serve para prosa: 40 textos dos bancos falam em reais.
        "Uma locadora cobra R$ 50 fixos mais R$ 2 por quilômetro.",
        # Estrutura de fórmula não tem caractere único: "frac{a}{b}" e "√{x}"
        # seriam piores que o comando cru.
        f"x = {B}frac{{-b}}{{2a}}",
        f"A raiz {B}sqrt{{16}} vale 4.",
        # Lista de listas fora de matriz: aqui o colchete pode ser a notação
        # certa, e trocar por "linhas" seria inventar erro.
        "Os pares ordenados são [[1, 2], [3, 4]] no plano cartesiano.",
        # Uma linha só não é matriz.
        "O vetor é a matriz [[1, 2]] de uma linha.",
    ],
)
def test_texto_legitimo_fica_como_esta(texto):
    assert limpar_marcacao_crua(texto) == texto


def test_asterisco_sozinho_nao_vira_nada():
    assert limpar_marcacao_crua("A nota * indica o rodapé.") == "A nota * indica o rodapé."


# --------------------------------------------------------------------------
# No caminho da questão


def test_pergunta_opcoes_e_explicacao_passam_pela_limpeza():
    questao = normalizar_payload_questao(
        {
            "pergunta": "Qual é o determinante da matriz [[6, 2], [3, 9]]?",
            "opcoes": [f"a = 5 {B}text{{ cm}}", "12"],
            "correta": 0,
            "explicacao": "O **primeiro** passo é multiplicar as diagonais.",
        }
    )

    assert questao["pergunta"] == "Qual é o determinante da matriz de linhas (6, 2) e (3, 9)?"
    assert questao["opcoes"][0] == "a = 5 cm"
    assert questao["explicacao"][0]["conteudo"] == "O primeiro passo é multiplicar as diagonais."


def test_modo_ingles_tambem_perde_o_markdown():
    # O `*should*` do relatório é de uma questão de Inglês, e o modo de Inglês
    # pula o dicionário de acentos inteiro -- se a limpeza morasse junto com
    # ele, o único caso real ficaria de fora.
    questao = normalizar_payload_questao(
        {
            "pergunta": "Which sentence uses *should* correctly?",
            "opcoes": ["You **should** study.", "You shoulds study."],
            "correta": 0,
            "explicacao": "The modal verb *should* is used to advise.",
        },
        modo_ingles=True,
    )

    assert questao["pergunta"] == "Which sentence uses should correctly?"
    assert questao["opcoes"][0] == "You should study."
    assert questao["explicacao"][0]["conteudo"] == "The modal verb should is used to advise."


def test_passos_nao_passam_pela_limpeza():
    # O passo é LaTeX de verdade e vai para o MathJax entre `$$`: "√{16}" ali
    # quebraria o desenho. 1.932 passos dos bancos usam `\frac` e `\cdot`.
    questao = normalizar_payload_questao(
        {
            "pergunta": "Resolva.",
            "opcoes": ["4", "5"],
            "correta": 0,
            "passos_resolucao": [{"titulo": "1o Passo", "conteudo": f"x = {B}sqrt{{16}} = 4"}],
        }
    )

    assert questao["passos_resolucao"][0]["conteudo"] == f"x = {B}sqrt{{16}} = 4"


# --------------------------------------------------------------------------
# As telas


@pytest.mark.parametrize(
    ("template", "trecho"),
    [
        # Listas de revisão: era o buraco de maior volume.
        ("boss_rush.html", "{{ item.pergunta|unidades|formula_html }}"),
        ("enem.html", "{{ item.pergunta|unidades|formula_html }}"),
        ("treino.html", "{{ item.pergunta|unidades|formula_html }}"),
        ("escape_room.html", "{{ item.pergunta|unidades|formula_html }}"),
        ("progresso.html", "{{ log.pergunta_texto|unidades|formula_html }}"),
        # Enunciado do Escape Room: tinha só "unidades", sem o expoente.
        ("escape_room.html", 'questao.get("pergunta", "")|unidades|formula_html'),
        # Resultado do RPG: o cartão dos outros modos (partials/result_card.html)
        # já usava a cadeia inteira; o RPG desenha o dele à parte.
        ("rpg.html", "estado.resultado.resposta_aluno|unidades|formula_html"),
        ("rpg.html", "estado.resultado.resposta_correta|unidades|formula_html"),
        ("rpg.html", "estado.resultado.explicacao_texto|unidades|formula_html"),
        ("rpg.html", "estado.resultado.feedback.confundiu|unidades|formula_html"),
        ("rpg.html", "estado.resultado.feedback.evitar|unidades|formula_html"),
        ("rpg.html", "estado.resultado.feedback.treino|unidades|formula_html"),
    ],
)
def test_tela_usa_a_cadeia_inteira(template, trecho):
    assert trecho in (TEMPLATES / template).read_text(encoding="utf-8")


def test_a_cadeia_resolve_o_que_o_relatorio_mostrou(client):
    from flask import render_template_string

    with client.application.app_context():
        # "357 cm^2" e "x^2 - 6x + 8 = 0" são os dois exemplos reais da lista
        # de revisão; "x_1" é da explicação de uma questão da IA.
        saida = render_template_string(
            "{{ v|unidades|formula_html }}", v="357 cm^2, x^2 - 6x + 8 = 0 e x_1"
        )

    assert saida == "357 cm², x<sup>2</sup> - 6x + 8 = 0 e x<sub>1</sub>"


# --------------------------------------------------------------------------
# O banco, na fonte


def _textos_do_laboratorio() -> list[str]:
    import services.banks.laboratorio as lab

    questoes = []
    for materia in lab.MATERIAS_LAB_OFFLINE:
        questoes += lab.listar_questoes_laboratorio(materia, "EM")
    for materia in lab.MATERIAS_LAB_EF_OFFLINE:
        questoes += lab.listar_questoes_laboratorio(materia, "EF")

    textos = []
    for questao in questoes:
        textos.append(str(questao.get("pergunta", "")))
        textos.append(str(questao.get("legenda_variaveis", "")))
    return [texto for texto in textos if texto]


def test_nenhuma_legenda_do_laboratorio_escreve_delta_por_extenso():
    textos = _textos_do_laboratorio()
    assert textos, "sem questão nenhuma o teste não estaria conferindo nada"

    por_extenso = re.compile(r"(?<!\\)\bDelta\s*[A-Za-z]\b")
    sobraram = [texto for texto in textos if por_extenso.search(texto)]

    assert sobraram == [], f"{len(sobraram)} texto(s) com a letra grega por extenso, ex.: {sobraram[:1]}"


def test_nenhuma_questao_do_laboratorio_mostra_matriz_em_colchetes():
    crua = re.compile(r"\[\s*\[")
    sobraram = [texto for texto in _textos_do_laboratorio() if crua.search(texto)]

    assert sobraram == [], f"{len(sobraram)} texto(s) com matriz crua, ex.: {sobraram[:1]}"


def test_a_questao_de_determinante_continua_dizendo_os_numeros():
    import services.banks.laboratorio as lab

    perguntas = [
        str(questao.get("pergunta", ""))
        for questao in lab.listar_questoes_laboratorio("Matematica", "EM")
        if "determinante" in str(questao.get("pergunta", "")).lower()
    ]

    assert perguntas, "a família de determinante sumiu do banco"
    for pergunta in perguntas:
        # Trocar a notação não pode apagar o dado: duas linhas, dois números
        # em cada, senão a questão fica sem resposta possível.
        assert re.search(r"linhas \(-?\d+, -?\d+\) e \(-?\d+, -?\d+\)", pergunta), pergunta
