"""Cada relatorio sai com a logo DA SUA escola -- ou com nenhuma.

MELHORIA: a busca procurava um arquivo unico, "logo_escola.png", e devolvia
o mesmo para todo mundo. Pior: esse arquivo ERA a logo da ETEC, com um nome
generico que escondia o fato. Com uma escola cadastrada ninguem notava; ao
cadastrar a Educacional Delta, o relatorio dela sairia carimbado com a
marca da ETEC.

E a terceira vez que a marca de uma escola vaza para a de outra neste
arquivo: antes havia um "SALESIANO" fixo como texto de reserva, que
aparecia no relatorio de qualquer outra escola.

A regra que estes testes prendem: **nenhuma logo e melhor que a logo
errada.** Quando nao existe arquivo para a escola, a funcao devolve None e
quem chama escreve o nome da propria escola no lugar.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.relatorios.commons import _localizar_logo

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"


def nome_do_arquivo(caminho: str | None) -> str | None:
    return os.path.basename(caminho) if caminho else None


# --------------------------------------------------------------------------
# cada escola pega a sua
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "escola, esperado",
    [
        ("Educacional Delta", "DeltaEducacional.jpg"),
        ("ETEC - Araçatuba", "EtecAracatuba.png"),
    ],
)
def test_cada_escola_recebe_a_propria_logo(escola, esperado):
    assert nome_do_arquivo(_localizar_logo(escola)) == esperado


def test_a_ordem_das_palavras_no_arquivo_nao_importa():
    # A logo da Educacional Delta chegou nomeada "DeltaEducacional.jpg".
    # Exigir a mesma ordem do cadastro seria exigir que quem salva o arquivo
    # adivinhe como a escola foi digitada no banco.
    assert _localizar_logo("Educacional Delta") == _localizar_logo("Delta Educacional")


def test_acento_e_pontuacao_no_nome_nao_atrapalham():
    assert _localizar_logo("ETEC - Araçatuba") == _localizar_logo("etec aracatuba")


# --------------------------------------------------------------------------
# a metade que importa: nenhuma logo e melhor que a logo errada
# --------------------------------------------------------------------------


@pytest.mark.parametrize("escola", ["Escola Que Nao Existe", "Colegio Novo", "Delta", ""])
def test_escola_sem_logo_nao_herda_a_de_outra(escola):
    assert _localizar_logo(escola) is None, (
        f"{escola!r} recebeu uma logo que nao e dela"
    )


def test_sem_nome_de_escola_nao_devolve_logo_nenhuma():
    # Chamada antiga, sem argumento: antes devolvia a logo da ETEC para
    # qualquer relatorio. Agora nao devolve nada.
    assert _localizar_logo() is None


def test_nao_sobrou_arquivo_de_nome_generico():
    # "logo_escola.png" era a logo da ETEC com nome de arquivo generico.
    # Enquanto esse nome existir, alguem vai supor que serve para todas.
    genericos = [p.name for p in ASSETS.glob("logo_escola.*")]

    assert not genericos, (
        f"{genericos} tem nome generico mas e a marca de UMA escola. "
        "Nomeie pelo nome da escola."
    )


# --------------------------------------------------------------------------
# a ligacao com quem gera o PDF
# --------------------------------------------------------------------------


def test_o_cabecalho_do_relatorio_passa_a_escola():
    import inspect

    from services.relatorios import commons

    fonte = inspect.getsource(commons._cabecalho)

    assert "_localizar_logo(escola_nome)" in fonte, (
        "o cabecalho voltou a pedir a logo sem dizer de qual escola"
    )


def test_o_pdf_de_credenciais_passa_a_escola():
    fonte = (RAIZ / "scripts" / "criar_alunos_teste.py").read_text(encoding="utf-8")

    assert "_localizar_logo(escola_nome)" in fonte


def test_toda_chamada_informa_a_escola():
    # Uma chamada sem argumento nao quebra e nao avisa: so devolve None e o
    # relatorio sai sem marca. Este teste existe para que isso apareca.
    import re

    ignorar = {"__pycache__", ".venv", "tests", "node_modules", ".claude"}  # .claude: worktrees
    sem_escola = []
    for arquivo in sorted(RAIZ.rglob("*.py")):
        if set(arquivo.parts) & ignorar:
            continue
        texto = arquivo.read_text(encoding="utf-8-sig", errors="ignore")
        for linha in re.findall(r"_localizar_logo\(\s*\)", texto):
            if "def _localizar_logo" in texto and arquivo.name == "commons.py":
                continue
            sem_escola.append(f"{arquivo.relative_to(RAIZ).as_posix()}: {linha}")

    assert not sem_escola, sem_escola
