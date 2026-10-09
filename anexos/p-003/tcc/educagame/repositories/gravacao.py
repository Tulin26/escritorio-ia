"""Uma gravacao que diz se gravou -- e, se nao gravou, por que.

MELHORIA: cada repositorio capturava a excecao e devolvia so None, e as telas
diziam "salvo" sem olhar o retorno: aventura, preferencias, escola e
matricula davam sucesso com o Supabase fora do ar ou recusando o pedido.
Devolver o motivo junto permite a tela dizer o que houve sem repetir o erro
do banco -- que fica no log.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from repositories.supabase_client import ErroDoSupabase, falha_de_conexao

FALHA_SEM_CONEXAO = "sem_conexao"
FALHA_RECUSADA = "recusada"
FALHA_NAO_ENCONTRADA = "nao_encontrada"


def gravar(
    consulta: Callable[[], Any],
    *,
    descricao: str,
    sem_linha: str,
    repetidos: dict[str, str] | None = None,
) -> tuple[Any | None, str]:
    """Roda a consulta. Devolve (resultado, "") ou (None, motivo).

    `consulta` e uma funcao, e nao a consulta pronta: sem Supabase
    configurado, o erro sai ja em supabase.table(...), antes do execute.

    `sem_linha`: o motivo quando o banco responde sem linha nenhuma. As
    consultas pedem return=representation, entao a linha gravada volta
    sempre. Num insert, lista vazia e resposta que nao confirma nada
    (FALHA_RECUSADA); num update ou delete, e o filtro que nao achou o
    registro (FALHA_NAO_ENCONTRADA).

    `repetidos`: restricao UNIQUE -> motivo, para o valor repetido que a
    pessoa consegue corrigir na tela (RA, slug).
    """
    try:
        resultado = consulta()
    except Exception as e:
        motivo = _motivo_da_falha(e, repetidos or {})
        print(f"Erro ao {descricao} ({motivo}): {e}")
        return None, motivo
    if not getattr(resultado, "data", None):
        return None, sem_linha
    return resultado, ""


def _motivo_da_falha(erro: Exception, repetidos: dict[str, str]) -> str:
    if falha_de_conexao(erro):
        return FALHA_SEM_CONEXAO
    if isinstance(erro, ErroDoSupabase):
        for restricao, motivo in repetidos.items():
            if erro.violou_unicidade(restricao):
                return motivo
    return FALHA_RECUSADA
