"""As palavras que o QA achou sem acento chegam acentuadas à tela.

Relatório de QA de 23/09/2026, item 5.1: cerca de 30 ocorrências de acento,
cedilha e grafia, "a maioria no banco autoral offline -- correção manual
pontual, barata e definitiva". Varrido o projeto em 28/09/2026, eram bem
mais: só "explicacao" aparecia em 26.004 textos, e nenhuma das palavras deste
arquivo estava no dicionário de acentos.

O conserto é no dicionário, e não no banco, porque o mesmo texto sai por sete
modos e dois frontends; o banco só foi corrigido onde a palavra estava errada
de verdade ("O toyotista" por "O toyotismo").
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.text_cleanup import _PALAVRAS_PT, _PALAVRAS_QUE_TAMBEM_SAO_VERBO, aplicar_acentos_pt

RAIZ = Path(__file__).resolve().parents[1]

# (como o banco escreve, como tem de chegar ao aluno) -- frases reais do banco.
DO_RELATORIO = [
    ("Uma populacao inicial de 120 bacterias dobra a cada hora. Quantas bacterias havera apos 3 horas?",
     "haverá"),
    ("Em uma situacao de engenharia simples, uma maquina realiza 160 J em 5 s.", "máquina"),
    ("2x = 44, entao x = 22.", "então"),
    ("Um indice passou de 120 para 145. Qual foi a taxa percentual de variacao?", "índice"),
    ("Favoraveis = 22, possiveis = 48.", "Favoráveis"),
    ("diluicao", "diluição"),
    ("Em um portao movido por energia, marcas no chao indicam deslocamento e tempo.", "chão"),
    ("Uma rampa de acesso tem 14 m de comprimento e forma 30 graus com o chao.", "alcança"),
    ("Reconhecer a diversidade de crencas e praticas ao interpretar diversidade religiosa.", "crenças"),
    ("o grupo precisa registrar o criterio que impedira a equipe de errar", "impedirá"),
    ("O guardiao de um painel aceita apenas uma explicacao ligada ao que foi observado.", "explicação"),
    ("Relacionar astronomia a observacao, hipotese, evidencia e explicacao cientifica.", "científica"),
    ("Transferencia de massa atomica por numero atomico.", "atômico"),
]


@pytest.mark.parametrize(("bruto", "esperado"), [(t, e) for t, e in DO_RELATORIO if e != "alcança"])
def test_palavra_do_relatorio_chega_acentuada(bruto, esperado):
    assert esperado in aplicar_acentos_pt(bruto)


def test_cedilha_de_alcanca():
    assert aplicar_acentos_pt("a rampa alcanca 7 m de altura") == "a rampa alcança 7 m de altura"


def test_crase_do_tema_do_rpg():
    # "respeito a diversidade religiosa" é tema do RPG e aparece em 852
    # textos, sempre pedindo crase.
    assert aplicar_acentos_pt("RPG - respeito a diversidade religiosa") == "RPG - respeito à diversidade religiosa"
    # E o "a" que não é crase continua como está.
    assert aplicar_acentos_pt("a diversidade religiosa e grande") == "a diversidade religiosa e grande"


@pytest.mark.parametrize("palavra", ["maquina", "indice", "cientifica"])
def test_palavra_ambigua_entra_nas_duas_listas(palavra):
    # Sem estar em _PALAVRAS_PT ela não seria acentuada em lugar nenhum; sem
    # estar na lista das que também são verbo, o app acentuaria o verbo que a
    # IA escreveu certo (regra de ace1e0c).
    assert palavra in _PALAVRAS_PT
    assert palavra in _PALAVRAS_QUE_TAMBEM_SAO_VERBO


@pytest.mark.parametrize("frase", [
    "A fábrica maquina uma saída para o problema da produção.",
    "O delegado indicie o suspeito antes do prazo, diz a notícia.",
    "A norma cientifica o interessado sobre o prazo, segundo o próprio artigo.",
])
def test_o_verbo_escrito_pela_ia_continua_verbo(frase):
    assert aplicar_acentos_pt(frase) == frase


def test_toyotismo_corrigido_no_banco():
    bruto = (RAIZ / "data" / "banco_especifico_em.json").read_text(encoding="utf-8")
    assert "O toyotista, desenvolvido" not in bruto, "toyotista é quem trabalha; o sistema é o toyotismo"
    assert "O toyotismo, desenvolvido" in bruto


def _textos_do_banco_com(palavras: set[str]) -> list[str]:
    """Só os textos dos bancos de conteúdo que trazem alguma das palavras."""
    rx = re.compile(r"\b(?:" + "|".join(sorted(palavras)) + r")\b")
    textos = []
    for arquivo in sorted((RAIZ / "data").glob("banco_especifico_*.json")):
        pilha = [json.loads(arquivo.read_text(encoding="utf-8"))]
        while pilha:
            valor = pilha.pop()
            if isinstance(valor, str):
                if rx.search(valor):
                    textos.append(valor)
            elif isinstance(valor, dict):
                pilha.extend(valor.keys())
                pilha.extend(valor.values())
            elif isinstance(valor, list):
                pilha.extend(valor)
    return textos


PALAVRAS_SEM_VERBO = {"explicacao", "explicacoes", "impedira", "atomico", "chao", "crencas",
                      "diluicao", "havera", "alcanca", "favoraveis", "entao"}


def test_nenhum_texto_do_banco_mostra_essas_palavras_sem_acento():
    # As ambíguas (maquina, indice, cientifica) ficam de fora: em texto que já
    # tem acento elas são o verbo, e aí continuam sem acento de propósito.
    textos = _textos_do_banco_com(PALAVRAS_SEM_VERBO)
    assert textos, "a varredura não achou nenhum texto: caminho errado esconderia o defeito"

    rx = re.compile(r"\b(?:" + "|".join(sorted(PALAVRAS_SEM_VERBO)) + r")\b")
    sobraram = [t for t in textos if rx.search(aplicar_acentos_pt(t))]

    assert sobraram == [], f"{len(sobraram)} texto(s) do banco ainda chegam sem acento, ex.: {sobraram[:1]}"
