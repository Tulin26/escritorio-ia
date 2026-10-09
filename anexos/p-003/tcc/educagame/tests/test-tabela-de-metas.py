"""A tabela de metas do professor tem grade própria.

Visto em 02/10/2026: o nome do aluno quebrava em quatro linhas ("Lucas /
Nishigima / 3º Ano EM - / Manhã"). A tabela herdava a grade do `.table-row`,
que é a das Guildas -- lá a PRIMEIRA coluna é a estreita ("Pos."); aqui ela é
o aluno. E no celular a regra geral esconde a 4ª e a 5ª coluna, que na tabela
de metas são "Uma jornada completa" e o foco: metade da meta sumia.

Conferido no navegador, em 1366 e em 375 px, sem rolagem lateral nas duas.
Aqui fica o que o texto do CSS consegue prender.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CSS = (RAIZ / "web" / "static" / "css" / "flask.css").read_text(encoding="utf-8")
PROFESSOR = (RAIZ / "web" / "templates" / "professor.html").read_text(encoding="utf-8")

CELULAR = "@media (max-width: 760px) {"


def _bloco_do_celular() -> str:
    inicio = CSS.index(CELULAR)
    # as regras de dentro sao indentadas: o primeiro "}" na coluna 0 fecha o bloco
    return CSS[inicio:CSS.index("\n}\n", inicio)]


def _regra(texto: str, seletor: str) -> str:
    achado = re.search(re.escape(seletor) + r"\s*\{([^}]*)\}", texto)
    assert achado, f"regra {seletor!r} não encontrada"
    return achado.group(1)


def test_a_tabela_de_metas_usa_a_grade_dela():
    assert '<div class="table-list metas-table">' in PROFESSOR


def test_a_primeira_coluna_e_a_do_aluno_e_e_larga():
    fora_do_celular = CSS[: CSS.index(CELULAR)]
    grade = _regra(fora_do_celular, ".metas-table .table-row")

    primeira = re.search(r"grid-template-columns:\s*minmax\((\d+)px", grade)

    assert primeira and int(primeira.group(1)) >= 160, grade


def test_no_celular_a_grade_nao_tem_largura_minima_que_estoure_a_tela():
    grade = _regra(_bloco_do_celular(), ".metas-table .table-row")

    assert "repeat(3, minmax(0, 1fr))" in grade


def test_no_celular_a_jornada_e_o_foco_nao_somem():
    celular = _bloco_do_celular()

    assert ".metas-table .table-row > :nth-child(4)," in celular
    assert "display: block" in _regra(celular, ".metas-table .table-row > :nth-child(5)")


def test_o_foco_comprido_fica_numa_caixa_so():
    assert "display: inline-block" in _regra(CSS, ".metas-table .pill")
