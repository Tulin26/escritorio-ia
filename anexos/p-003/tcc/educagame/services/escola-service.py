from __future__ import annotations

from repositories.escola_repo import (
    FALHA_SLUG_REPETIDO,
    atualizar_escola,
    buscar_escola_por_id,
    buscar_escola_por_slug,
    criar_escola,
    excluir_escola,
    listar_escolas,
)
from repositories.gravacao import FALHA_NAO_ENCONTRADA, FALHA_RECUSADA, FALHA_SEM_CONEXAO
from services.avisos_de_gravacao import CONFIRMACAO_INVALIDA, FALTA_ESCOLA, FALTAM_DADOS

# MELHORIA: cadastrar, editar e excluir escola (ADM) e salvar as
# preferencias da escola (painel do professor) diziam sucesso sem olhar o
# retorno -- ou, no Flask, "Verifique a conexao" ate para slug repetido.
# Nenhum texto repete o erro do banco; ele fica no log.
MENSAGENS_DA_ESCOLA = {
    FALTAM_DADOS: "Informe o nome e o slug da escola.",
    CONFIRMACAO_INVALIDA: "Confirmação inválida. A escola não foi excluída.",
    FALHA_SLUG_REPETIDO: "Já existe uma escola cadastrada com esse slug. Escolha outro código de acesso.",
    # "nao confirmada": num prazo estourado o pedido pode ter chegado ao banco
    FALHA_SEM_CONEXAO: (
        "O banco de dados não respondeu, e a alteração na escola não foi confirmada. "
        "Tente de novo em instantes."
    ),
    FALHA_RECUSADA: (
        "O banco de dados não aceitou a alteração na escola. "
        "Se isso se repetir, avise o desenvolvedor."
    ),
    FALHA_NAO_ENCONTRADA: "Essa escola não foi encontrada; ela pode ter sido excluída em outra tela.",
}

MENSAGENS_DAS_PREFERENCIAS = {
    FALTA_ESCOLA: "Escolha a escola antes de salvar as preferências.",
    FALHA_SEM_CONEXAO: (
        "O banco de dados não respondeu, e as preferências não foram confirmadas. "
        "Tente de novo em instantes."
    ),
    FALHA_RECUSADA: (
        "O banco de dados não aceitou as preferências. "
        "Se isso se repetir, avise o desenvolvedor."
    ),
    FALHA_NAO_ENCONTRADA: (
        "As preferências não foram salvas: a escola desta sessão não foi encontrada. "
        "Saia e entre de novo."
    ),
}


def salvar_preferencias(escola_id: str | None, *, mostrar_ranking: bool, modo_guilda: bool) -> tuple[bool, str]:
    """Devolve (True, "") ou (False, motivo de MENSAGENS_DAS_PREFERENCIAS)."""
    if not str(escola_id or "").strip():
        return False, FALTA_ESCOLA
    resultado, motivo = atualizar_escola(
        escola_id, {"mostrar_ranking": bool(mostrar_ranking), "modo_guilda": bool(modo_guilda)}
    )
    return resultado is not None, motivo

# MELHORIA: o codigo da escola voltou a ser exigido, e a comparacao ficou
# dentro da rota do Flask. O Streamlit nao acompanhou: clicar no cartao da
# escola levava direto ao login, sem codigo nenhum -- dois frontends
# discordando sobre a mesma porta.
#
# E exatamente a forma de `conta_pode_entrar`: uma checagem que morava numa
# tela so, e por isso valia para metade do produto. A regra vem para ca e as
# duas telas chamam.
#
# O que este codigo NAO e: um segredo. A lista de escolas e publica, a
# comparacao nao e em tempo constante e nada limita tentativas -- de
# proposito, porque um limite por IP derrubaria uma sala inteira atras de um
# NAT so. Quem controla acesso de verdade e a senha, no login. O codigo
# existe para que um clique nao leve ninguem a porta da escola errada.
MOTIVO_CODIGO_INCORRETO = "Código incorreto. Peça o código da escola ao seu professor."


def normalizar_codigo_escola(valor) -> str:
    """Aparado e em minusculas: e digitado a mao, muitas vezes no celular."""
    return str(valor or "").strip().lower()


def codigo_confere(escola, codigo_digitado) -> bool:
    """O codigo da escola e o slug dela.

    Codigo vazio nunca confere, e escola sem slug tambem nao -- senao a
    unidade mal cadastrada viraria a que qualquer um abre sem digitar nada.
    """
    digitado = normalizar_codigo_escola(codigo_digitado)
    esperado = normalizar_codigo_escola((escola or {}).get("slug"))
    return bool(digitado) and bool(esperado) and digitado == esperado


# MELHORIA: mostrar_ranking e modo_guilda eram gravados pelos dois paineis
# (configuracoes do professor e ADM), mas nenhuma tela os lia: o "Ranking da
# escola" e a Batalha de Guildas apareciam do mesmo jeito com a opcao
# desligada. O TCC (RF14) diz o contrario -- o ranking individual so aparece
# com mostrar_ranking ligado, a disputa entre turmas so com modo_guilda
# ligado, e com a opcao desligada o aluno mantem a pontuacao mas nao ve a
# classificacao.
#
# A regra mora aqui pelo mesmo motivo de `codigo_confere`: Flask e Streamlit
# fazem a mesma pergunta, e uma regra escrita em cada tela vale para metade
# do produto na primeira vez que alguem mexe numa so.
AVISO_GUILDAS_DESLIGADAS = (
    "A Batalha de Guildas está desligada nesta escola. "
    "Seus pontos continuam valendo normalmente."
)


def _opcao_ligada(escola, campo: str) -> bool:
    """Se a escola deixou esta opcao ligada.

    Sem escola nenhuma (None, dict vazio), a resposta e NAO: a regra e "so
    aparece se estiver habilitado", e o que nao se conseguiu ler nao esta
    habilitado. Esconder o placar por um instante de falha no banco custa
    menos que mostrar a classificacao que a escola decidiu esconder.

    Escola sem a coluna segue o DEFAULT true do schema -- e o mesmo
    `.get(campo, True)` com que os paineis ja desenham o interruptor.
    """
    if not isinstance(escola, dict) or not escola:
        return False
    return bool(escola.get(campo, True))


def mostra_ranking(escola) -> bool:
    """RF14: o ranking individual so aparece com mostrar_ranking ligado."""
    return _opcao_ligada(escola, "mostrar_ranking")


def mostra_guildas(escola) -> bool:
    """RF14: a disputa entre turmas so aparece com modo_guilda ligado."""
    return _opcao_ligada(escola, "modo_guilda")


def escola_atualizada(escola_id, reserva: dict | None = None) -> dict | None:
    """A escola como esta no banco AGORA; a `reserva` se a leitura falhar.

    O Flask so guarda id/slug/nome na sessao, e o Streamlit guarda a linha
    inteira -- mas do momento do login. Nos dois casos as opcoes da sessao
    envelhecem: o professor desliga o ranking e o aluno ja logado seguiria
    vendo. Por isso as telas perguntam ao banco.
    """
    atual = buscar_escola_por_id(str(escola_id)) if escola_id else None
    return atual or reserva
