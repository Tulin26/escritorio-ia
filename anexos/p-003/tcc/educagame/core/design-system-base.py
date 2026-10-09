"""O pouco que as duas folhas de estilo compartilham.

MELHORIA: `_ler_css` e `_PASTA_ESTILOS` existiam byte a byte iguais em
`design_system_global.py` e `design_system_rpg.py`, e `_bloco_html` existia em
QUATRO lugares (os dois acima mais `st/ui/home_st.py` e
`st/ui/rpg_helpers_st.py`).

São funções pequenas, e é justamente por isso que ninguém as junta: cada cópia
parece barata demais para incomodar. O preço não é o tamanho — é que uma
correção feita numa não chega às outras, e aqui a de `_ler_css` carrega uma
decisão que custou caro para descobrir (o caminho sair de `__file__`, e não do
diretório de trabalho). Corrigir isso em uma cópia e esquecer a outra deixaria
metade do app sem estilo, que é uma falha muda: a tela abre, só fica feia.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from textwrap import dedent

PASTA_ESTILOS = Path(__file__).resolve().parent / "estilos"


@lru_cache(maxsize=8)
def ler_css(nome: str) -> str:
    """Le a folha de estilo do disco, uma vez por processo.

    O caminho sai de __file__, nao do diretorio de trabalho: o Render roda
    via gunicorn e o Streamlit Cloud via "streamlit run", de lugares
    diferentes -- caminho relativo quebraria num dos dois.
    """
    return (PASTA_ESTILOS / nome).read_text(encoding="utf-8")


def bloco_html(html: str) -> str:
    """Tira a indentacao que o HTML herdou de estar dentro do Python.

    Sem isso o Markdown do Streamlit le quatro espacos como bloco de codigo e
    mostra a tag crua na tela.
    """
    return dedent(html).strip()
