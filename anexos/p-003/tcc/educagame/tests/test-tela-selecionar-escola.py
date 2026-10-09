"""A tela de escolha de escola nao pode ficar invisivel.

MELHORIA: regressao de um bug visto em producao -- o mesmo endereco abria
normal no computador de um amigo e completamente preto no do Lucas.

A secao de conteudo recebia "school-entry-oculta" (opacity: 0 permanente,
sem animacao que a traga de volta) sempre que havia UMA escola cadastrada.
So que o redirecionamento automatico que justificaria esconder depende de
mostrar_intro TAMBEM, e mostrar_intro e falso quando ha erro. Com uma escola
e um erro: nada de splash, nada de script, e o conteudo escondido assim
mesmo. A propria mensagem de erro vive dentro da secao, entao nem o motivo
aparecia.
"""

from __future__ import annotations

import pytest
from flask import render_template

UMA_ESCOLA = [{"id": "1", "nome": "ETEC", "slug": "etec"}]
DUAS_ESCOLAS = UMA_ESCOLA + [{"id": "2", "nome": "Outra", "slug": "outra"}]


def _render(client, **contexto):
    with client.application.test_request_context("/"):
        return render_template("selecionar_escola.html", **contexto)


def test_com_erro_o_conteudo_fica_visivel(client):
    html = _render(client, escolas=UMA_ESCOLA, erro="Escola nao encontrada.", next="")

    assert "school-entry-oculta" not in html, "escondeu a tela sem ter redirecionamento"
    assert "Escola nao encontrada." in html
    # MELHORIA: o teste procurava "setTimeout", que era proxy para "ha
    # redirecionamento automatico". O proxy quebrou quando o base.html ganhou
    # o aviso de carregamento, que tambem usa setTimeout -- e a falha nao
    # tinha relacao nenhuma com esta tela. `window.location.href` e o que de
    # fato leva o aluno embora, e e o que este teste sempre quis proteger.
    assert "window.location.href" not in html, "sem redirect automatico quando ha erro"


def test_sem_erro_e_uma_escola_esconde_porque_vai_redirecionar(client):
    html = _render(client, escolas=UMA_ESCOLA, erro="", next="")

    # aqui esconder e correto: a splash toca e o script leva embora sozinho
    assert "school-entry-oculta" in html
    assert "window.location.href" in html
    assert "school-splash" in html


def test_com_varias_escolas_nunca_esconde(client):
    html = _render(client, escolas=DUAS_ESCOLAS, erro="", next="")

    assert "school-entry-oculta" not in html
    assert "ETEC" in html
    assert "Outra" in html


@pytest.mark.parametrize("erro", ["", "Escola nao encontrada."])
def test_o_esconder_nunca_sobrevive_sem_o_redirect(client, erro):
    # A regra que o bug violava: so pode esconder quem vai ser levado embora.
    html = _render(client, escolas=UMA_ESCOLA, erro=erro, next="")

    if "school-entry-oculta" in html:
        assert "window.location.href" in html, "conteudo escondido sem nada para revela-lo"
