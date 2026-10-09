"""Importa TODO modulo de interface, dos dois frontends.

MELHORIA: `core/` e `services/` sao compartilhados entre o frontend Flask e
o Streamlit, mas a suite so exercitava um lado por vez. Duas vezes a main
apagou codigo achando que ninguem mais usava, e a tela do Streamlit quebrou
no boot -- as cicatrizes estao no proprio repositorio:

  - core/config.py: "a main removeu-o ao refatorar este arquivo, sem saber
    que st/ui/tela_oraculo_st.py ainda chama get_habilidades_area(...)"
  - core/utils.py: bloco "COMPAT STREAMLIT" com formatar_latex,
    limpar_formula_no_texto e tem_matriz

Nenhum teste pegava isso porque nada importava aqueles modulos. Este pega:
as duas falhas explodem no import, entao um `pytest` acusa o nome da funcao
que sumiu em vez de o aluno achar a tela em branco.

Os modulos sao descobertos pelo que existe em disco, nao por lista fixa --
assim o mesmo arquivo vale na branch do Flask, na do Streamlit e numa
eventual branch unificada, e cobre modulo novo sem ninguem lembrar de
registrar aqui.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# (pasta em disco, prefixo do modulo). Pasta ausente = frontend nao existe
# nesta branch, e simplesmente nao gera casos.
PACOTES_DE_INTERFACE = [
    ("st/ui", "st.ui"),
    ("web/routes", "web.routes"),
]


def _descobrir_modulos() -> list[str]:
    encontrados: list[str] = []
    for pasta, prefixo in PACOTES_DE_INTERFACE:
        raiz_pacote = RAIZ / pasta
        if not raiz_pacote.is_dir():
            continue
        for arquivo in sorted(raiz_pacote.glob("*.py")):
            if arquivo.stem == "__init__":
                continue
            encontrados.append(f"{prefixo}.{arquivo.stem}")
    return encontrados


MODULOS = _descobrir_modulos()


def test_encontrou_modulos_para_cobrir():
    # Sem isto, um erro de caminho faria a varredura achar zero modulos e a
    # suite passaria verde cobrindo nada -- exatamente o problema que este
    # arquivo existe para resolver.
    assert MODULOS, f"nenhum modulo de interface encontrado em {RAIZ}"


@pytest.mark.parametrize("nome_modulo", MODULOS)
def test_modulo_de_interface_importa(nome_modulo):
    try:
        importlib.import_module(nome_modulo)
    except Exception as erro:  # noqa: BLE001
        # Exception, nao so ImportError: os modulos de st/ui/ vinculam na propria
        # importacao ("formatar_latex = core_utils.formatar_latex"), entao
        # funcao removida chega como AttributeError. Qualquer excecao no
        # import significa tela quebrada no boot.
        pytest.fail(
            f"{nome_modulo} nao importa: {type(erro).__name__}: {erro}\n"
            "Se o nome que falta e de core/ ou services/, provavelmente foi "
            "removido por estar sem uso no OUTRO frontend -- confira antes "
            "de apagar."
        )
