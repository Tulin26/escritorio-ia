"""As folhas de estilo saíram do Python e viraram .css de verdade.

MELHORIA: design_system_global.py tinha 1.230 linhas, sendo 1.187 de CSS
numa f-string unica -- com 327 pares de chave duplicada ("{{" e "}}") so
para escapar o f-string, num arquivo cuja linguagem usa chave o tempo todo.
E a f-string existia por UMA interpolacao: a cor da escola, que ja era a
custom property --edu-school.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ESTILOS = RAIZ / "core" / "estilos"

FOLHAS = ["design_system_global.css", "design_system_rpg.css"]


@pytest.mark.parametrize("nome", FOLHAS)
def test_folha_existe_e_tem_conteudo(nome):
    arquivo = ESTILOS / nome

    assert arquivo.is_file(), f"{nome} nao encontrada em core/estilos"
    assert len(arquivo.read_text(encoding="utf-8").splitlines()) > 100


@pytest.mark.parametrize("nome", FOLHAS)
def test_nao_sobrou_escape_de_f_string(nome):
    css = (ESTILOS / nome).read_text(encoding="utf-8")

    assert "{{" not in css, "chave duplicada sobrou da f-string"
    assert "}}" not in css
    # nenhuma interpolacao pendente: seria um "{nome}" cru na tela
    assert not re.search(r"\{[a-z_]+\}", css), "interpolacao Python nao substituida"


def test_ler_css_nao_depende_do_diretorio_de_trabalho(tmp_path, monkeypatch):
    # O Render roda via gunicorn e o Streamlit Cloud via "streamlit run", de
    # lugares diferentes. Caminho relativo funcionaria aqui e quebraria num
    # dos dois -- e o sintoma seria a tela sem estilo nenhum, que ja
    # aconteceu neste projeto por outro motivo.
    from core.design_system_base import ler_css

    monkeypatch.chdir(tmp_path)

    css = ler_css("design_system_global.css")

    assert "--edu-text" in css


def test_cor_da_escola_vira_sobrescrita_so_quando_difere():
    import core.design_system_global as ds

    injetado: list[str] = []
    original = ds._renderizar_html_seguro
    ds._renderizar_html_seguro = injetado.append
    try:
        ds.aplicar_estilo_global_edugame("#003366")
        com_cor = list(injetado)

        injetado.clear()
        ds.aplicar_estilo_global_edugame("#f4c76a")
        com_padrao = list(injetado)
    finally:
        ds._renderizar_html_seguro = original

    assert len(com_cor) == 2, "faltou a regra de sobrescrita da cor"
    assert "--edu-school: #003366" in com_cor[1]
    # a sobrescrita vem DEPOIS: mesma especificidade, entao vence
    assert com_cor[1].index("--edu-school") > 0

    assert len(com_padrao) == 1, "injetou sobrescrita igual ao padrao, a toa"


def test_valor_padrao_da_cor_mora_no_css():
    css = (ESTILOS / "design_system_global.css").read_text(encoding="utf-8")

    assert "--edu-school: #f4c76a" in css


@pytest.mark.parametrize("modulo", ["design_system_global", "design_system_rpg"])
def test_modulo_python_ficou_pequeno(modulo):
    # A regressao a evitar e alguem voltar a colar CSS aqui dentro.
    arquivo = RAIZ / "core" / f"{modulo}.py"
    linhas = arquivo.read_text(encoding="utf-8").splitlines()

    assert len(linhas) < 80, f"{modulo}.py voltou a crescer: {len(linhas)} linhas"


# ====================== UMA COPIA SO DOS AJUDANTES ======================


def test_ninguem_reescreve_ler_css_nem_bloco_html():
    """MELHORIA: `_ler_css` e `_PASTA_ESTILOS` existiam byte a byte iguais nos
    dois modulos de design, e `_bloco_html` existia em QUATRO lugares.

    Sao funcoes pequenas, e e por isso que ninguem as juntava: cada copia
    parece barata demais para incomodar. O preco nao e o tamanho -- e que uma
    correcao feita numa nao chega as outras. A de `ler_css` carrega uma
    decisao que custou caro (o caminho sair de __file__, nao do diretorio de
    trabalho); corrigi-la numa copia e esquecer a outra deixaria metade do app
    sem estilo, que e uma falha muda: a tela abre, so fica feia.
    """
    duplicaveis = ("def _ler_css", "def ler_css", "def _bloco_html", "def bloco_html",
                   "_PASTA_ESTILOS =", "PASTA_ESTILOS =")
    arquivos = sorted(RAIZ.glob("core/*.py")) + sorted(RAIZ.glob("st/ui/*.py"))

    for caminho in arquivos:
        if caminho.name == "design_system_base.py":
            continue
        fonte = caminho.read_text(encoding="utf-8-sig")
        for marca in duplicaveis:
            assert marca not in fonte, f"{caminho.name} voltou a definir {marca!r}"


def test_a_varredura_de_copias_olha_onde_as_copias_estavam():
    # Sem isto, um glob errado faria o teste acima passar sem olhar nada.
    arquivos = sorted(RAIZ.glob("core/*.py")) + sorted(RAIZ.glob("st/ui/*.py"))
    nomes = {c.name for c in arquivos}

    assert len(arquivos) > 20
    for onde in ("design_system_global.py", "design_system_rpg.py", "home_st.py", "rpg_helpers_st.py"):
        assert onde in nomes, onde


def test_bloco_html_tira_a_indentacao_do_python():
    # Sem isso o Markdown do Streamlit le quatro espacos como bloco de codigo
    # e mostra a tag crua na tela.
    from core.design_system_base import bloco_html

    html = bloco_html(
        """
        <div>
            <span>oi</span>
        </div>
        """
    )

    assert html.startswith("<div>")
    assert html.endswith("</div>")
    assert "\n    <span>" in html, "a indentacao relativa de dentro tem que ficar"


def test_ler_css_le_do_disco_uma_vez_por_processo():
    from core.design_system_base import ler_css

    primeira = ler_css("design_system_rpg.css")
    segunda = ler_css("design_system_rpg.css")

    assert primeira is segunda, "o lru_cache saiu; passaria a ler o disco a cada tela"
