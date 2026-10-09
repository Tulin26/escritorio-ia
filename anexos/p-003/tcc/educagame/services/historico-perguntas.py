"""Historico das perguntas ja mostradas, guardado FORA do cookie de sessao.

MELHORIA: Laboratorio (calc_hist_*), Oraculo (oraculo_hist_*) e ENEM
(enem_hist_*) guardavam no cookie de sessao do Flask o TEXTO de cada pergunta
ja mostrada, para nao repetir. Com o tema em branco, o tema e sorteado (ou
alternado) a cada questao, e cada tema abria uma chave NOVA: o teto de 12
perguntas era por chave, e as chaves nao tinham teto. E nada as apagava -- o
logout e a expiracao limpam uma lista fixa de chaves (core/sessao.py), e estas
tem nome dinamico.

Medido em 13/09/2026: 38 avisos "The 'session' cookie is too large" no Render
em uma semana, com o cookie entre 4.068 e 4.218 bytes para um limite de 4.093.
Acima disso o navegador IGNORA o cookie em silencio, e o aluno perde o login
ou a questao em andamento. Refeita a sequencia real de 33 respostas da conta
de teste, os historicos sozinhos levavam a sessao de 469 para ~2.500 bytes; o
resto vinha das questoes geradas e nao respondidas e dos dias anteriores.

Agora o historico mora em estados_sessao (a mesma tabela da questao em
andamento), numa linha por sessao: "<_estado_sid>:historicos". O cookie guarda
so o _estado_sid, que ja existia -- e que o logout apaga, entao quem sai leva o
historico junto. A linha expira com o TTL da tabela.

Fora de uma requisicao Flask (Streamlit, scripts), o historico fica em
runtime.session_state, como antes -- ou em lugar nenhum, para quem pede.
"""

from __future__ import annotations

import secrets
from typing import Iterable

from core.runtime_context import get_runtime
from repositories.database_repo import carregar_estado_temporario, salvar_estado_temporario

# Chaves distintas guardadas por sessao. Com o tema sorteado, cada questao pode
# abrir uma chave nova; sem teto, a linha no banco cresceria como o cookie
# crescia. Sai a chave usada ha mais tempo.
MAX_CHAVES = 24

_SUFIXO = "historicos"
_ATRIBUTO_G = "_historicos_de_perguntas"


def id_estado_sessao() -> str:
    """O identificador do estado desta sessao, criado na primeira vez.

    Um so para a questao em andamento (web/routes/flask_helpers_fla.py) e para
    os historicos: o logout apaga este id, e os dois vao embora juntos.
    """
    from flask import session

    sid = str(session.get("_estado_sid") or "")
    if not sid:
        sid = secrets.token_urlsafe(16)
        session["_estado_sid"] = sid
    return sid


def _em_requisicao() -> bool:
    from flask import has_request_context

    return has_request_context()


def _chave_no_banco() -> str:
    return f"{id_estado_sessao()}:{_SUFIXO}"


def _historicos_da_requisicao() -> dict[str, list[str]]:
    """Todos os historicos desta sessao, lidos do banco UMA vez por requisicao.

    No banco a ordem vai como LISTA de pares: o jsonb do Postgres nao guarda a
    ordem das chaves de um objeto, e e pela ordem que se sabe qual chave foi
    usada ha mais tempo.
    """
    from flask import g

    cache = getattr(g, _ATRIBUTO_G, None)
    if cache is None:
        salvo = carregar_estado_temporario(_chave_no_banco())
        cache = {}
        pares = salvo.get("historicos") if isinstance(salvo, dict) else None
        for par in pares if isinstance(pares, list) else []:
            if isinstance(par, dict) and isinstance(par.get("itens"), list):
                cache[str(par.get("chave"))] = [str(item) for item in par["itens"]]
        setattr(g, _ATRIBUTO_G, cache)
    return cache


def ler(chave: str) -> list[str]:
    """As perguntas (ou ids do banco proprio) ja mostradas nesta chave.

    Fora do Flask le a memoria. Quem grava com fora_do_flask=False (o Oraculo)
    nunca poe nada la, entao le vazio sem precisar de opcao propria -- um
    mutante mostrou que o guarda que havia aqui nao mudava nada.
    """
    if _em_requisicao():
        return list(_historicos_da_requisicao().get(chave, []))
    valor = get_runtime().session_state.get(chave)
    return list(valor) if isinstance(valor, list) else []


def gravar(chave: str, itens: Iterable, *, fora_do_flask: bool = True) -> None:
    """Substitui o historico da chave. Quem chama ja cortou no tamanho que quer."""
    limpos = [str(item) for item in itens if str(item).strip()]
    if not _em_requisicao():
        if fora_do_flask:
            get_runtime().session_state[chave] = limpos
        return

    historicos = _historicos_da_requisicao()
    historicos.pop(chave, None)  # volta para o fim: e a usada agora
    historicos[chave] = limpos
    while len(historicos) > MAX_CHAVES:
        historicos.pop(next(iter(historicos)))
    salvar_estado_temporario(
        _chave_no_banco(),
        {"historicos": [{"chave": nome, "itens": lista} for nome, lista in historicos.items()]},
    )
