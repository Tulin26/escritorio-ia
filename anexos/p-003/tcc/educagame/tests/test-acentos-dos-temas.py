"""O tema sorteado chega ao aluno com acento.

Visto em 13/09/2026, em explicações reais do Oráculo: "Entendendo
Redemocratizacao". O tema sai de core/config.py em ASCII e só ganha acento
em aplicar_acentos_pt; 80 dos 286 temas mostravam palavra sem acento
("genetica mendeliana", "Grandes Navegacoes", "placas tectonicas").
"""

from __future__ import annotations

import re

import pytest

from core.config import MATERIAS, get_temas_rpg
from core.text_cleanup import aplicar_acentos_pt

ANOS = ("1º EM", "2º EM", "3º EM", "6º Ano", "7º Ano", "8º Ano", "9º Ano")

CORRIGIDAS = frozenset(
    """agroquimicos algebricas analitica artistica artisticas atomistica bacterias basicas cinematica circulatorio
    climaticas coesao combinatoria combustiveis concordancia contemporanea distribuicao economicos educacao
    eletromagnetico eletronica eletronicos eletroquimica eletrostatica energeticas escravidao estatistica estetica
    evolucao fisicos genetica geometrica geopolitica globalizacao grecia hidrostatica horarios independencia inorganicas
    instituicoes lancamento lesoes ligacoes logaritmica mesopotamia migratorios mudancas navegacoes nutricao optica
    organica periodica politica prevencao producao projeteis radiacoes redemocratizacao regencia revolucao sintatica
    sistematica socioeconomicos tectonicas termodinamica termoquimica vegetacao virus vocabulario""".split()
)


def _temas() -> list[str]:
    temas: set[str] = set()
    for materia in MATERIAS:
        for ano in ANOS:
            try:
                temas.update(get_temas_rpg(materia, ano) or [])
            except Exception:
                continue
    return sorted(temas)


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("Entendendo Redemocratizacao", "Entendendo Redemocratização"),
        ("Grandes Navegacoes", "Grandes Navegações"),
        ("genetica mendeliana", "genética mendeliana"),
        ("placas tectonicas", "placas tectônicas"),
        ("Termodinamica", "Termodinâmica"),
    ],
)
def test_tema_ganha_acento(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado


def test_nenhum_tema_mostra_palavra_corrigida_sem_acento():
    temas = _temas()
    assert len(temas) > 200, "a lista de temas mudou de lugar: o teste não estaria olhando nada"

    sobrou = sorted(
        {palavra for tema in temas for palavra in re.findall(r"[a-z]+", aplicar_acentos_pt(tema).lower()) if palavra in CORRIGIDAS}
    )

    assert sobrou == []


@pytest.mark.parametrize(
    "frase",
    [
        "Analise o gráfico a seguir e responda.",
        "O autor critica a sociedade da época.",
        "Eu dialogo com a turma todos os dias.",
    ],
)
def test_verbo_nao_ganha_acento(frase):
    # "analise", "critica" e "dialogo" ficaram de fora do dicionário de
    # palavra solta de propósito: são também verbo.
    assert aplicar_acentos_pt(frase) == frase


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("analise combinatoria", "análise combinatória"),
        ("analise sintatica", "análise sintática"),
        ("comercio internacional", "comércio internacional"),
        ("dialogo inter-religioso", "diálogo inter-religioso"),
        ("taxas e indices socioeconomicos", "taxas e índices socioeconômicos"),
        ("Na analise de dados", "Na análise de dados"),
    ],
)
def test_palavra_ambigua_ganha_acento_presa_a_frase(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado


def test_nenhum_tema_mostra_palavra_ambigua_sem_acento():
    ambiguas = {"analise", "critica", "comercio", "dialogo", "indices"}

    sobrou = sorted(
        {tema for tema in _temas() for palavra in re.findall(r"[a-z]+", aplicar_acentos_pt(tema).lower()) if palavra in ambiguas}
    )

    assert sobrou == []
