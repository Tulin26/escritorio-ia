"""A ajuda dentro do app, no Streamlit.

O par de `web/routes/ajuda_fla.py`. O conteúdo vem do mesmo `core/ajuda.py`
que alimenta os dois frontends e o PDF do guia -- escrever um texto próprio
aqui criaria a terceira descrição dos mesmos oito modos, e foi assim que o
guia de acesso envelheceu da primeira vez.
"""

from __future__ import annotations

import unicodedata

import streamlit as st

from core.ajuda import secoes_da_ajuda
from core.sessao import MINUTOS_INATIVIDADE_PADRAO


def _sem_acento(texto: str) -> str:
    """Quem digita "duvida" tem de achar "dúvida" -- no teclado do celular o
    acento nem costuma ser sugerido."""
    forma = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in forma if not unicodedata.combining(c))


def renderizar_tela_ajuda() -> None:
    st.title("❓ Como usar o EducaGame")
    st.caption("Procure pelo que você quer fazer. Se não achar, pergunte ao seu professor.")

    papel = str((st.session_state.get("usuario") or {}).get("role", ""))
    secoes = secoes_da_ajuda(
        # Perguntado ao código, nunca escrito à mão: foi um número escrito
        # assim que fez o guia antigo mentir.
        minutos_sessao=int(MINUTOS_INATIVIDADE_PADRAO),
        eh_professor=papel in ("professor", "desenvolvedor"),
    )

    busca = _sem_acento(st.text_input("Buscar na ajuda", placeholder="ex.: senha, demora, RPG"))

    achou = 0
    for secao in secoes:
        itens = [
            (titulo, texto)
            for titulo, texto in secao["itens"]
            if not busca or busca in _sem_acento(f"{titulo} {texto}")
        ]
        if not itens:
            # Seção sem item visível some junto com o título, senão sobram
            # cabeçalhos soltos sobre o vazio.
            continue
        achou += len(itens)
        st.subheader(secao["titulo"])
        for titulo, texto in itens:
            with st.expander(titulo):
                st.write(texto)

    if not achou:
        st.info("Nada encontrado. Tente outra palavra, ou peça ajuda ao seu professor.")
