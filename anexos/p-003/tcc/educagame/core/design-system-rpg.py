import streamlit as st

from core.design_system_base import bloco_html as _bloco_html, ler_css as _ler_css


def aplicar_design_system_rpg():
    """MELHORIA: eram 488 linhas de CSS numa string dentro desta funcao."""
    st.markdown(
        f"<style>{_ler_css('design_system_rpg.css')}</style>",
        unsafe_allow_html=True,
    )
