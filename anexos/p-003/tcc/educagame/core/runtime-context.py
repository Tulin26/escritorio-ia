from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable
from functools import wraps
from typing import Any


class _Secrets:
    def get(self, nome: str, default: Any = None) -> Any:
        return os.getenv(nome, default)


_TTL_PADRAO_SEGUNDOS = 60.0


def _montar_chave_cache(nome: str, f_args: tuple, f_kwargs: dict) -> str:
    partes = [repr(valor) for valor in f_args]
    partes += [f"{chave}={valor!r}" for chave, valor in sorted(f_kwargs.items())]
    return f"{nome}:" + "|".join(partes)


# MELHORIA: o cache do nivel 2 mora em public.cache_dados, no Supabase --
# escolhido para ser compartilhado entre workers. So que assim ATE O ACERTO
# custa uma ida a rede: acerto = 1 consulta, erro = 3 (le o cache, le a
# fonte, grava o cache). O painel do professor faz 6 leituras dessas em
# sequencia e levava ~6 s em producao.
#
# Este nivel 1 fica em memoria do processo e corta a rede do caminho comum.
# O TTL e curto de proposito: com mais de um worker, cada um tem o seu, e
# uma escrita num deles nao limpa o do outro -- entao a defasagem possivel
# fica limitada a estes segundos, em vez dos 60 do nivel 2. Com um worker
# so (o caso hoje) nao ha defasagem nenhuma, porque .clear() alcanca o unico
# nivel 1 que existe.
_L1_TTL_SEGUNDOS = 5.0
_l1_lock = threading.Lock()
_l1: dict[str, tuple[float, Any]] = {}


def _l1_buscar(chave: str) -> tuple[Any, bool]:
    agora = time.monotonic()
    with _l1_lock:
        entrada = _l1.get(chave)
        if entrada is None:
            return None, False
        expira_em, valor = entrada
        if expira_em <= agora:
            _l1.pop(chave, None)
            return None, False
        return valor, True


def _l1_salvar(chave: str, valor: Any, ttl: float) -> None:
    agora = time.monotonic()
    with _l1_lock:
        # Varre o vencido junto: sem isso as chaves so acumulam, e cada valor
        # e uma lista inteira (alunos, logs) num processo de 512 MB.
        if len(_l1) > 64:
            for chave_velha in [k for k, (exp, _) in _l1.items() if exp <= agora]:
                _l1.pop(chave_velha, None)
        _l1[chave] = (agora + min(ttl, _L1_TTL_SEGUNDOS), valor)


def _copia_defensiva(valor: Any) -> Any:
    """Devolve uma copia, para o chamador nao poder corromper o cache.

    MELHORIA: o cache entregava o PROPRIO objeto que o nivel 1 guarda. Um
    `.sort()` ou `.append()` na lista devolvida corrompia o valor guardado
    para todos os leitores seguintes, pelo resto do TTL -- e sem erro
    nenhum, porque nada quebra: os dados so ficam errados.

    Havia teste para isso desde o comeco, e ele nao pegava. Ele fazia
    `runtime = get_runtime()` no import do arquivo; na suite completa outro
    teste ja tinha importado streamlit, entao `runtime` virava o MODULO do
    streamlit e o teste media o cache do Streamlit, nao o deste projeto.
    Verde no lugar onde se costuma olhar, vermelho quando rodava sozinho.

    A copia vai um nivel para dentro dos registros: protege a lista (sort,
    append) e cada dicionario dentro dela (aluno["nome"] = ...). Estrutura
    aninhada DENTRO de um registro continua compartilhada -- e a troca
    consciente aqui:

        5000 registros    deepcopy 27,6 ms    este copiador 1,17 ms

    O nivel 1 existe para custar quase nada; 27 ms por leitura comeria boa
    parte do que ele economiza.
    """
    if isinstance(valor, list):
        return [dict(item) if isinstance(item, dict) else item for item in valor]
    if isinstance(valor, dict):
        return {
            chave: list(item) if isinstance(item, list) else dict(item) if isinstance(item, dict) else item
            for chave, item in valor.items()
        }
    # texto, numero, None: imutaveis, nao ha o que copiar
    return valor


def _l1_limpar_prefixo(prefixo: str) -> None:
    with _l1_lock:
        for chave in [k for k in _l1 if k.startswith(prefixo)]:
            _l1.pop(chave, None)


class RuntimeContext:
    secrets = _Secrets()
    session_state: dict[str, Any] = {}

    def cache_data(self, *args, ttl: float = _TTL_PADRAO_SEGUNDOS, **kwargs):
        # MELHORIA: antes este decorator so existia pra manter a mesma API
        # de um app Streamlit antigo (dai o nome), mas nao cacheava nada de
        # verdade — toda leitura (alunos, logs, ranking...) batia no
        # Supabase de novo a cada request, mesmo com .clear() sendo chamado
        # religiosamente apos cada escrita pra "invalidar" um cache que nunca
        # existiu. Depois virou um cache em memoria por processo, mas isso
        # nao sobrevive a mais de um worker do Gunicorn: cada worker cacheia
        # (e invalida) por conta propria, entao uma escrita num worker deixa
        # os outros servindo dado obsoleto pelo TTL inteiro. Agora o
        # armazenamento e a tabela public.cache_dados (Supabase), visivel
        # por todos os workers/instancias.
        def decorate(func: Callable):
            nome_cache = f"{func.__module__}.{func.__qualname__}"

            @wraps(func)
            def wrapper(*f_args, **f_kwargs):
                from repositories import cache_repo

                chave = _montar_chave_cache(nome_cache, f_args, f_kwargs)

                # Os tres caminhos devolvem COPIA: o que sai daqui vai para
                # as maos de quem chamou, e o que fica guardado tem de
                # continuar intacto para o proximo leitor.
                valor, encontrado = _l1_buscar(chave)
                if encontrado:
                    return _copia_defensiva(valor)

                valor, encontrado = cache_repo.buscar(chave)
                if encontrado:
                    _l1_salvar(chave, valor, ttl)
                    return _copia_defensiva(valor)

                resultado = func(*f_args, **f_kwargs)
                cache_repo.salvar(chave, resultado, ttl)
                _l1_salvar(chave, resultado, ttl)
                return _copia_defensiva(resultado)

            def limpar() -> None:
                from repositories import cache_repo

                # O nivel 1 primeiro: se a limpeza do nivel 2 falhar por rede,
                # ao menos este processo para de servir o valor antigo.
                _l1_limpar_prefixo(f"{nome_cache}:")
                cache_repo.limpar_prefixo(f"{nome_cache}:")

            wrapper.clear = limpar  # type: ignore[attr-defined]
            return wrapper

        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return decorate(args[0])
        return decorate

    def error(self, mensagem: str) -> None:
        print(mensagem)

    def warning(self, mensagem: str) -> None:
        print(mensagem)

    def stop(self) -> None:
        raise RuntimeError("Aplicacao interrompida por configuracao ausente.")


_runtime = RuntimeContext()


def ler_segredo(nome: str) -> str | None:
    """Le uma configuracao: variavel de ambiente primeiro, secrets depois.

    MELHORIA: esta funcao existia DUAS vezes, identica, como `_get_secret`
    em repositories/supabase_client.py e em services/ia/providers.py -- uma
    lendo a chave do Supabase, a outra as chaves de IA. Havia ainda uma
    terceira leitura, com contrato proprio, em core/diagnostico_config.py.
    Tres caminhos para a mesma pergunta.

    Ninguem estava errado, mas leitura de segredo divergindo em silencio e a
    pior versao do problema: se uma passasse a olhar secrets antes do
    ambiente e a outra nao, metade do sistema ficaria sem a chave e o log
    nao diria nada -- que e a falha que este projeto ja teve duas vezes.

    MELHORIA (a de verdade, alem de juntar): as duas copias resolviam o
    runtime no IMPORT (`runtime = get_runtime()` no topo do modulo). Sob o
    Streamlit isso e uma corrida: se o modulo for importado antes de
    "streamlit" entrar em sys.modules, a copia guarda o contexto neutro para
    sempre e NUNCA enxerga st.secrets -- que e justamente como o Streamlit
    Cloud entrega SUPABASE_URL e SUPABASE_KEY. E o mesmo tropeco que o
    comentario de get_runtime() abaixo descreve. Aqui o runtime e resolvido
    na CHAMADA, entao a ordem de import deixa de importar.
    """
    valor = os.getenv(nome)
    if valor:
        return valor
    try:
        return get_runtime().secrets.get(nome)
    except Exception:  # noqa: BLE001 - sem secrets configurado
        return None


def get_runtime():
    # MELHORIA: rodando dentro de "streamlit run app.py", o modulo
    # "streamlit" ja esta em sys.modules quando repositories/ e services/ sao
    # importados (app.py faz "import streamlit as st" antes das paginas).
    # Devolver o modulo real aqui faz cache_data/secrets/session_state/error/
    # warning/stop usarem a implementacao de verdade -- em especial
    # st.secrets, que e como o Streamlit Cloud entrega SUPABASE_URL e
    # SUPABASE_KEY. O RuntimeContext abaixo tem o mesmo shape (os mesmos 6
    # atributos) justamente para o swap ser direto.
    #
    # Sem isto o app sobe, mas sem banco: _get_secret (repositories/
    # supabase_client.py) tenta os.getenv, nao acha, e cai em
    # runtime.secrets, que no contexto neutro esta vazio. Localmente o
    # problema nao aparece porque o .env preenche os.getenv.
    st = sys.modules.get("streamlit")
    if st is not None:
        return st
    return _runtime
