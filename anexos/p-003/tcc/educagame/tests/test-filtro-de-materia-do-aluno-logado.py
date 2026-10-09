"""O aluno que entra com a própria conta só vê as matérias da sua etapa.

Visto em produção em 11/09/2026: um aluno do 3º Ano EM via "Ciências" no
seletor do Laboratório. Escolhida, a matéria era trocada por Matemática no
servidor, sem aviso nenhum.

O filtro de matérias existia, mas preso à LISTA de alunos
(`select[name="aluno_id"]`), que só professor e desenvolvedor têm. Na conta de
aluno o aluno vai num campo escondido, então o filtro nunca rodava -- nas
quatro telas que incluem o seletor: Laboratório, Treino, Oráculo e Escape
Room.

Estes testes conferem a MARCAÇÃO que o filtro precisa. O comportamento no
navegador (a opção some de verdade) foi conferido abrindo a página.
"""

from __future__ import annotations

import pytest


def _renderizar(**contexto) -> str:
    from flask_app import app

    with app.test_request_context("/"):
        return app.jinja_env.get_template("partials/student_selector.html").render(**contexto)


def test_o_aluno_logado_leva_o_ano_para_o_filtro():
    html = _renderizar(aluno_travado=True, aluno_nome="Lucas", ano_escolar="3º Ano EM", aluno_id="a1", alunos=[])

    assert 'name="aluno_id"' in html
    assert 'data-ano="3º Ano EM"' in html, "o campo escondido não diz o ano, e o filtro não tem de onde ler"


def test_o_script_procura_o_campo_escondido_do_aluno_logado():
    """O defeito era exatamente este seletor faltar: o script só olhava a lista."""
    html = _renderizar(aluno_travado=True, aluno_nome="Lucas", ano_escolar="3º Ano EM", aluno_id="a1", alunos=[])

    assert 'input[name="aluno_id"][data-ano]' in html
    # Achar o campo não basta: um mutante que apagou a CHAMADA do filtro, e
    # deixou o seletor no lugar, passava pela linha acima.
    assert 'filtrarMaterias(campo.closest("form"), campo.dataset.ano' in html


def test_o_professor_continua_filtrando_pela_lista():
    """O par: consertar o aluno logado não pode desligar o caminho que já
    funcionava para quem escolhe o aluno numa lista."""
    alunos = [{"id": "a1", "nome": "Ana", "ano_escolar": "7º Ano"}, {"id": "a2", "nome": "Bia", "ano_escolar": "2º Ano EM"}]

    html = _renderizar(aluno_travado=False, alunos=alunos, aluno_id="a2", ano_escolar="2º Ano EM")

    assert '<select id="aluno_id" name="aluno_id"' in html
    assert 'data-ano="7º Ano"' in html and 'data-ano="2º Ano EM"' in html
    assert 'select[name="aluno_id"]' in html


@pytest.mark.parametrize("tela", ["laboratorio.html", "treino.html", "oraculo.html", "escape_room.html"])
def test_nas_quatro_telas_o_seletor_de_aluno_esta_no_mesmo_formulario_da_materia(tela):
    """O filtro acha as matérias subindo até o <form>. Se um dia o seletor de
    aluno sair do formulário da matéria, o filtro volta a não achar nada."""
    from pathlib import Path

    fonte = (Path(__file__).resolve().parent.parent / "web" / "templates" / tela).read_text(encoding="utf-8")
    inicio = fonte.index('name="materia"')
    abre = fonte.rfind("<form", 0, inicio)
    fecha = fonte.find("</form>", inicio)

    assert abre != -1 and fecha != -1
    assert 'include "partials/student_selector.html"' in fonte[abre:fecha], (
        f"em {tela}, o seletor de aluno saiu do formulário da matéria"
    )
