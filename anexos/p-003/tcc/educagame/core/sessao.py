"""Quando a sessao do Flask deixa de valer.

MELHORIA: o app nao tinha prazo de sessao NENHUM. O cookie saia assim --

    session=...; HttpOnly; Path=/

-- sem Expires e sem Max-Age. Isso o torna um cookie de sessao do navegador:
o servidor nunca o recusa, e quem decide a hora de morrer e o navegador, ao
fechar. So que o Chrome e o Edge restauram cookies de sessao quando estao com
"continuar de onde parei" ligado (e no Android isso e o normal), entao na
pratica o login virava permanente: abrir o site caia direto no perfil do
aluno ou do professor, dias depois, sem pedir escola nem senha.

Em sala isso e o pior caso: o computador e compartilhado. Quem senta depois
herda a conta de quem levantou -- com o painel do professor junto, se o
anterior for professor.

Duas travas, porque respondem a coisas diferentes:

  inatividade  conta desde o ultimo clique. E a que devolve a tela de
               escolher escola + senha para quem volta ao site mais tarde.
  vida maxima  conta desde o login. Fecha o caso do computador que fica
               aberto o dia inteiro, onde o clique de alguem renova a
               sessao para sempre.

As duas sao ajustaveis por variavel de ambiente. Zero desliga a trava --
explicito, porque desligar em silencio por causa de um valor invalido seria
pior do que voltar ao padrao.
"""

from __future__ import annotations

import os
from typing import Any, MutableMapping

# As mesmas chaves que o logout limpa. Ficam aqui, e nao em auth_fla, para
# expirar e sair pela porta serem a mesma lista: se uma esquecer a escola e a
# outra nao, "sair" passa a significar duas coisas diferentes no mesmo app.
CHAVES_DE_ACESSO = (
    "usuario_id",
    "usuario_username",
    "usuario_role",
    "usuario_escola_id",
    "escola_id",
    "escola_slug",
    "escola_nome",
    "aluno_id",
    "aluno_nome",
    "ano_escolar",
)

# O identificador do estado temporario dos jogos (ver
# web/routes/flask_helpers_fla.py::_id_estado_sessao). Nao e credencial, mas
# sai junto: sem isso o proximo aluno no MESMO navegador retomaria o quiz pela
# metade de quem estava antes -- exatamente o computador compartilhado que
# motiva as travas daqui. As linhas orfas no banco ja tem faxina propria
# (repositories/database_repo.py), e o progresso que importa fica salvo por
# aluno, entao nada duravel se perde.
CHAVES_DE_ESTADO = ("_estado_sid",)

CHAVE_INICIO = "sessao_inicio"
CHAVE_VISTO = "sessao_visto_em"

MINUTOS_INATIVIDADE_PADRAO = 30.0
HORAS_MAXIMAS_PADRAO = 12.0

# Carimbar a atividade suja a sessao, e sessao suja significa um Set-Cookie a
# mais na resposta. Uma vez por minuto basta: com a inatividade em minutos, a
# imprecisao que isso introduz e de segundos.
_SEGUNDOS_ENTRE_CARIMBOS = 60.0

# Carimbo no futuro so aparece se o relogio do servidor andar para tras. Sem
# esta folga, um ajuste de milissegundos entre requisicoes derrubaria gente
# sem motivo; com ela, o carimbo adiantado de verdade ainda e recusado -- e
# precisa ser, porque "agora - carimbo" negativo nunca expira.
_FOLGA_DE_RELOGIO_SEGUNDOS = 60.0


def _numero_do_ambiente(nome: str, padrao: float) -> float:
    bruto = (os.getenv(nome) or "").strip().replace(",", ".")
    if not bruto:
        return padrao
    try:
        valor = float(bruto)
    except ValueError:
        # Valor escrito errado volta ao padrao. O caminho para desligar a
        # trava e escrever 0, nao errar a digitacao.
        return padrao
    return max(valor, 0.0)


def segundos_de_inatividade() -> float:
    return _numero_do_ambiente("SESSAO_MINUTOS_INATIVIDADE", MINUTOS_INATIVIDADE_PADRAO) * 60.0


def segundos_de_vida_maxima() -> float:
    return _numero_do_ambiente("SESSAO_HORAS_MAXIMAS", HORAS_MAXIMAS_PADRAO) * 3600.0


def _instante(valor: Any) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def tem_acesso(sessao: MutableMapping[str, Any]) -> bool:
    return any(sessao.get(chave) for chave in CHAVES_DE_ACESSO)


def motivo_de_expiracao(sessao: MutableMapping[str, Any], agora: float) -> str:
    """Por que esta sessao nao vale mais. String vazia = ainda vale."""
    inicio = _instante(sessao.get(CHAVE_INICIO))
    visto = _instante(sessao.get(CHAVE_VISTO))

    # Sessao com acesso e sem carimbo e uma sessao anterior a esta regra --
    # foi emitida quando prazo nenhum existia, entao nao da para saber a
    # idade dela. Recusar de uma vez tambem faz o primeiro deploy encerrar
    # os logins eternos que ja estao nos navegadores. A sessao criada AGORA
    # nao cai aqui: carimbar_se_novo() a carimba no fim da propria
    # requisicao que a criou.
    if inicio <= 0 or visto <= 0:
        return "sem-carimbo"

    if inicio > agora + _FOLGA_DE_RELOGIO_SEGUNDOS or visto > agora + _FOLGA_DE_RELOGIO_SEGUNDOS:
        return "carimbo-no-futuro"

    limite_ocioso = segundos_de_inatividade()
    if limite_ocioso > 0 and agora - visto > limite_ocioso:
        return "inatividade"

    limite_total = segundos_de_vida_maxima()
    if limite_total > 0 and agora - inicio > limite_total:
        return "tempo-maximo"

    return ""


# MELHORIA: os historicos de perguntas ja mostradas iam para o cookie com estes
# prefixos, e nenhuma limpeza os alcancava -- nem o logout, nem a expiracao, que
# usam as listas fixas acima. O cookie inchava dia apos dia ate o navegador
# descarta-lo. Eles foram para o banco (services/historico_perguntas.py); isto
# encolhe, no primeiro acesso, o cookie de quem ja estava inchado.
PREFIXOS_DE_HISTORICO_NO_COOKIE = ("calc_hist_", "oraculo_hist_", "enem_hist_")


def remover_historicos_do_cookie(sessao: MutableMapping[str, Any]) -> int:
    """Tira da sessao os historicos antigos. Devolve quantas chaves sairam."""
    antigas = [
        chave
        for chave in list(sessao.keys())
        if isinstance(chave, str) and chave.startswith(PREFIXOS_DE_HISTORICO_NO_COOKIE)
    ]
    for chave in antigas:
        sessao.pop(chave, None)
    return len(antigas)


def encerrar(sessao: MutableMapping[str, Any]) -> None:
    for chave in (*CHAVES_DE_ACESSO, *CHAVES_DE_ESTADO, CHAVE_INICIO, CHAVE_VISTO):
        sessao.pop(chave, None)


def marcar_login(sessao: MutableMapping[str, Any], agora: float) -> None:
    """Zera os dois relogios. A vida maxima conta a partir do login."""
    sessao[CHAVE_INICIO] = agora
    sessao[CHAVE_VISTO] = agora


def revisar(sessao: MutableMapping[str, Any], agora: float) -> str:
    """Expira a sessao ociosa e carimba a atividade de quem continua dentro.

    Devolve o motivo da expiracao, ou string vazia se a sessao segue valendo.
    """
    if not tem_acesso(sessao):
        # Visitante sem escola nem login nao tem o que expirar. Carimbar aqui
        # so daria cookie a quem ainda nao escolheu nada.
        return ""

    motivo = motivo_de_expiracao(sessao, agora)
    if motivo:
        encerrar(sessao)
        return motivo

    if agora - _instante(sessao.get(CHAVE_VISTO)) >= _SEGUNDOS_ENTRE_CARIMBOS:
        sessao[CHAVE_VISTO] = agora
    return ""


def carimbar_se_novo(sessao: MutableMapping[str, Any], agora: float) -> None:
    """Carimba a sessao que acabou de ganhar acesso, no fim da requisicao.

    A escolha da escola e o login acontecem DENTRO da view, depois que
    revisar() ja passou. Sem este segundo passo, a sessao recem-criada
    chegaria a requisicao seguinte sem carimbo -- e "sem carimbo" e motivo de
    expiracao, entao ninguem conseguiria entrar em lugar nenhum.
    """
    if not tem_acesso(sessao):
        return
    if _instante(sessao.get(CHAVE_INICIO)) > 0 and _instante(sessao.get(CHAVE_VISTO)) > 0:
        return
    marcar_login(sessao, agora)
