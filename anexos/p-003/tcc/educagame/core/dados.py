"""Arquivos de dados do app, em data/.

MELHORIA: os bancos de conteudo especifico do Oraculo (EM) e do Ensino
Fundamental eram dicionarios literais escritos em Python -- 28.957 linhas,
quase metade das linhas de Python do projeto, sem uma linha de logica.
Viraram JSON em data/: o mesmo dicionario, com as mesmas chaves na mesma
ordem. Os modulos de antes continuam exportando os mesmos nomes, e quem os
importa nao muda.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PASTA_DADOS = Path(__file__).resolve().parent.parent / "data"


def ler_json(nome: str) -> Any:
    """O conteudo de data/<nome>, lido como UTF-8."""
    return json.loads((PASTA_DADOS / nome).read_text(encoding="utf-8"))
