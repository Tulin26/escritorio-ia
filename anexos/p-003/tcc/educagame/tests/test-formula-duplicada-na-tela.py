"""A fórmula não pode aparecer duas vezes na tela.

Visto em produção em 29/09/2026, no Laboratório, no Treino Rápido e no RPG --
com questão do banco e com questão da IA: cada fórmula saía duplicada, a de
cima num tipo e a de baixo em outro.

O MathJax desenha a fórmula em SVG e, ao lado dela, uma cópia em MathML que
existe só para leitor de tela (`<mjx-assistive-mml>`). Quem esconde essa cópia
é um `<style>` que o MathJax injeta em tempo de execução -- e a CSP de
`style-src`, fechada sem `'unsafe-inline'` em 587a290, **recusa esse style**.
Confirmado no console do navegador, na tela do Laboratório: duas mensagens
"Applying inline style violates the following Content Security Policy
directive: style-src 'self' ...". Sem esse estilo, nada escondia a cópia, e o
Chrome desenha MathML nativamente.

A correção mora no CSS do próprio app, que vem de `/static/` e por isso passa
no `'self'` da CSP. Por que assim, e não acertando os hashes: hash de estilo
muda a cada atualização do MathJax, e transcrever um errado foi exatamente o
que já aconteceu aqui (437a358 corrigiu um "I" maiúsculo no lugar de "l"
minúsculo). A cópia em MathML continua no HTML para quem usa leitor de tela --
só volta a ficar invisível, como deveria estar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "web" / "static" / "css" / "flask.css"
TEMPLATES = RAIZ / "web" / "templates"

# As telas que rodam MathJax -- e só elas podem duplicar.
TELAS_COM_MATHJAX = ("laboratorio.html", "rpg.html", "treino.html")


def _regra_do_assistive_mml() -> str:
    texto = CSS.read_text(encoding="utf-8")
    achado = re.search(r"mjx-assistive-mml\s*\{([^}]*)\}", texto)
    return achado.group(1) if achado else ""


def test_o_css_do_app_esconde_a_copia_de_acessibilidade():
    regra = _regra_do_assistive_mml()

    assert regra, "sem esta regra a fórmula volta a aparecer duas vezes"
    # O par que de fato esconde: tirar do fluxo e recortar para 1px. Só
    # `position: absolute` deixaria a cópia visível por cima do SVG.
    assert "position: absolute" in regra
    assert "clip:" in regra


def test_a_copia_continua_no_html_para_leitor_de_tela():
    # `display: none` esconderia dos olhos E do leitor de tela, que é o
    # contrário do motivo de a cópia existir.
    regra = _regra_do_assistive_mml()

    assert "display: none" not in regra.replace(" ", " ")
    assert "display: block" in regra


@pytest.mark.parametrize("template", TELAS_COM_MATHJAX)
def test_as_telas_que_duplicavam_usam_o_css_do_app(template):
    # A regra só alcança essas telas porque todas estendem base.html, que
    # carrega flask.css. Se alguma parar de estender, a duplicação volta lá.
    texto = (TEMPLATES / template).read_text(encoding="utf-8")

    assert 'extends "base.html"' in texto
    assert "tex-svg.js" in texto, "esta tela deixou de carregar MathJax: revisar este teste"


def test_base_carrega_o_css_do_app():
    assert "css/flask.css" in (TEMPLATES / "base.html").read_text(encoding="utf-8")


def test_so_essas_tres_telas_carregam_mathjax():
    # Fixa o alcance do problema: quem não carrega MathJax não duplica. Se uma
    # tela nova passar a carregar, ela entra na lista acima junto.
    com_mathjax = {
        caminho.name
        for caminho in TEMPLATES.glob("*.html")
        if "tex-svg.js" in caminho.read_text(encoding="utf-8")
    }

    assert com_mathjax == set(TELAS_COM_MATHJAX)


def test_a_csp_continua_sem_unsafe_inline_em_style_src():
    # A correção existe para NÃO precisar afrouxar isto. Se alguém abrir o
    # style-src, a regra do CSS vira remendo sobre remendo.
    flask_app = (RAIZ / "flask_app.py").read_text(encoding="utf-8")
    style_src = re.search(r'"style-src ([^"]*)"', flask_app)

    assert style_src, "style-src sumiu da CSP"
    assert "unsafe-inline" not in style_src.group(1)
