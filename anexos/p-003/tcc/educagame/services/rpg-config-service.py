from __future__ import annotations

from repositories.gravacao import FALHA_NAO_ENCONTRADA, FALHA_RECUSADA, FALHA_SEM_CONEXAO
from repositories.rpg_config_repo import (
    atualizar_rpg_config,
    criar_rpg_config,
    excluir_rpg_config,
    listar_rpg_configs,
)
from services.avisos_de_gravacao import FALTA_ESCOLA, FALTAM_DADOS

# MELHORIA: Flask e Streamlit diziam "Aventura salva."/"excluida" sem olhar
# o retorno. Os textos servem para criar, editar e excluir -- por isso
# "alteracao", e nao "gravacao". Nenhum repete o erro do banco.
MENSAGENS_DA_AVENTURA = {
    FALTA_ESCOLA: "Escolha a escola antes de salvar ou excluir uma aventura.",
    FALTAM_DADOS: "Preencha pelo menos o Título e o Cenário.",
    # "nao confirmada": num prazo estourado o pedido pode ter chegado ao banco
    FALHA_SEM_CONEXAO: (
        "O banco de dados não respondeu, e a alteração na aventura não foi confirmada. "
        "Tente de novo em instantes."
    ),
    FALHA_RECUSADA: (
        "O banco de dados não aceitou a alteração na aventura. "
        "Se isso se repetir, avise o desenvolvedor."
    ),
    FALHA_NAO_ENCONTRADA: "Essa aventura não foi encontrada; ela pode ter sido excluída em outra tela.",
}


def salvar_aventura(escola_id: str | None, config_id: str | None, dados: dict) -> tuple[bool, str]:
    """Cria (sem config_id) ou atualiza. Devolve (True, "") ou (False, motivo).

    O motivo e uma chave de MENSAGENS_DA_AVENTURA. Titulo e cenario sao os
    dois campos que as duas telas ja marcavam como obrigatorios -- o Flask so
    no navegador (`required`), que nao vale para quem posta direto.
    """
    if not str(escola_id or "").strip():
        return False, FALTA_ESCOLA
    if not str(dados.get("titulo") or "").strip() or not str(dados.get("cenario") or "").strip():
        return False, FALTAM_DADOS

    if config_id:
        resultado, motivo = atualizar_rpg_config(escola_id, config_id, dados)
    else:
        resultado, motivo = criar_rpg_config({**dados, "escola_id": escola_id})
    return resultado is not None, motivo


def excluir_aventura(escola_id: str | None, config_id: str | None) -> tuple[bool, str]:
    """Exclui so se a aventura for da escola. Devolve (True, "") ou (False, motivo).

    Sem escola, o filtro compararia com nada; sem id, nao ha o que excluir.
    Os dois param aqui, antes de ir ao banco.
    """
    if not str(escola_id or "").strip():
        return False, FALTA_ESCOLA
    if not str(config_id or "").strip():
        return False, FALHA_NAO_ENCONTRADA
    resultado, motivo = excluir_rpg_config(escola_id, config_id)
    return resultado is not None, motivo
