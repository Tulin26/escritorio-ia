import re

import streamlit as st

from core.design_system_base import bloco_html as _bloco_html, ler_css as _ler_css

_SO_STYLE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)


def _e_somente_style(html: str) -> bool:
    return not _SO_STYLE.sub("", html).strip()


def _renderizar_html_seguro(html: str) -> None:
    # MELHORIA: quando o bloco e SO <style>, o st.html() do Streamlit >= 1.36
    # desvia para o "event container" (streamlit/elements/html.py, issue
    # #9388) para o CSS nao ocupar espaco no layout. So que de la o <style>
    # nao chega ao DOM da pagina: no dashboard o tema inteiro sumia -- fonte
    # Cinzel, fundo escuro e todas as variaveis --edu-* ficavam indefinidas.
    # st.markdown injeta um <style> de verdade na arvore principal.
    if _e_somente_style(html):
        st.markdown(html, unsafe_allow_html=True)
        return
    render_html = getattr(st, "html", None)
    if callable(render_html):
        render_html(html)
        return
    st.markdown(html, unsafe_allow_html=True)


def aplicar_estilo_global_edugame(cor_escola: str = "#f4c76a"):
    """Aplica uma identidade visual global inspirada na tela RPG.

    MELHORIA: o CSS morava aqui, numa f-string de 1.187 linhas com 327 pares
    de chave duplicada so para escapar o proprio f-string. Ele existia por
    UMA interpolacao -- a cor da escola, que ja era a custom property
    --edu-school. Agora o CSS e um arquivo .css de verdade, com o valor
    padrao dentro dele, e aqui so entra a sobrescrita quando a escola tem
    cor propria.
    """
    _renderizar_html_seguro(f"<style>{_ler_css('design_system_global.css')}</style>")

    cor_escola = (cor_escola or "").strip() or "#f4c76a"
    if cor_escola != "#f4c76a":
        # Regra separada e posterior: mesma especificidade, entao vence.
        _renderizar_html_seguro(
            f"<style>:root {{ --edu-school: {cor_escola}; }}</style>"
        )
