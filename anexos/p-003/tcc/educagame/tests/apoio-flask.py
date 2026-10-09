"""Apoio para os testes que dirigem o Flask via app.test_client().

MELHORIA: a sessao do Flask passou a ter prazo (ver core/sessao.py), e o
carimbo de idade e o que diz se ela ainda vale. Uma sessao COM acesso e SEM
carimbo so pode ser anterior a essa regra, entao o app a encerra de
proposito -- e um teste que escreve usuario_role/escola_id direto no cookie,
sem passar pelo login, monta exatamente essa sessao. Sem o carimbo o teste
nao falharia por causa do que veio testar: cairia na tela de escolher
escola, com um 302 inexplicavel.
"""

from __future__ import annotations

import time

from core.sessao import marcar_login


def carimbar_sessao(sess) -> None:
    """Da idade a uma sessao montada na mao, como o login faria."""
    marcar_login(sess, time.time())
