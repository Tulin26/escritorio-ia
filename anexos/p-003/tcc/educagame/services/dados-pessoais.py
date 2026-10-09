"""Pedido de LGPD: o que o EducaGame guarda de um aluno, e como apagar.

Por que este módulo existe
--------------------------
A página `/privacidade` promete os direitos do Art. 18 da LGPD --
confirmação de que existe tratamento, acesso, portabilidade e exclusão -- e
diz, com honestidade, que hoje o pedido é feito pelo professor ou pela
coordenação. Só que do outro lado não havia nada: `excluir_aluno`
(repositories/aluno_repo.py) existia e era chamado apenas por
`scripts/criar_alunos_teste.py`, e para "acesso" não existia função nenhuma.
Atender um pedido significava alguém abrir o painel do Supabase e montar a
consulta na hora.

Este módulo é a parte de dentro; `scripts/dados_do_aluno.py` (leitura) e
`scripts/excluir_aluno.py` (apagar) são a parte de fora.

Por que continua sem tela
-------------------------
É a decisão que já estava escrita em `excluir_aluno`: "Não há tela para isto
de propósito. Quem usa é script, onde a escolha do que apagar fica escrita e
revisável." Um botão de apagar aluno no painel do professor seria uma ação
irreversível, em produção, a um clique de quem estiver logado -- e o pedido
de exclusão é raro, chega por fora do sistema e precisa ser conferido por uma
pessoa antes de ser executado. O que é seguro colocar numa tela um dia é o
LADO DE LEITURA, e por isso `reunir_dados_do_aluno` devolve estrutura pronta
para isso, sem depender de terminal.

Onde moram os dados de uma pessoa
---------------------------------
Três tabelas, e só:

  * `alunos` -- cadastro (nome, RA, e-mail, série, período, pontos, a data do
    consentimento e o hash da senha);
  * `logs_pedagogicos` -- uma linha por questão respondida, com o enunciado,
    a resposta dada, se acertou e quanto tempo levou;
  * `rpg_progressos` -- o estado salvo de cada aventura;
  * `conclusoes_modo` -- uma linha por partida concluida (meta semanal);
  * `foco_do_aluno` -- o tema que o professor anotou para essa pessoa.

Fora dessas: `estados_sessao` guarda a questão em andamento, mas a chave dele
é o id da SESSÃO, não o do aluno (web/routes/flask_helpers_fla.py::
_chave_estado) -- não há como alcançá-lo por aluno, e ele expira sozinho em 6
horas. `cache_dados` guarda agregados por escola, não por pessoa. O IP nunca
é gravado: fica só em memória, no Flask-Limiter.

O que a exclusão faz de verdade
-------------------------------
Apaga a linha de `alunos`, e o CASCADE das migrações 20260803120200 e
20260803120300 leva junto os logs e o progresso de RPG. `apagar_dados_do_aluno`
CONFERE isso depois: se o CASCADE não existir no banco em que o script rodou,
sobram linhas apontando para um aluno que não existe mais, e é melhor
descobrir na hora do que meses depois.

Duas consequências que valem ser ditas em voz alta antes de apagar: o
histórico da turma encolhe (as respostas dessa pessoa saem das estatísticas do
professor, o que é o efeito pretendido de uma exclusão) e o ranking muda. A
alternativa seria anonimizar em vez de apagar -- manter as respostas sem dono
--, e ela NÃO foi escolhida: a resposta a uma questão, junto com o horário,
ainda é dado de uma pessoa identificável dentro de uma turma pequena, e a
página promete exclusão, não anonimização.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from repositories.aluno_repo import (
    buscar_aluno_por_email,
    buscar_aluno_por_id,
    buscar_aluno_por_username,
    excluir_aluno,
)
from repositories.database_repo import listar_progressos_rpg_do_aluno
from repositories.log_repo import buscar_logs
from repositories.meta_repo import listar_conclusoes_do_aluno, listar_focos_do_aluno

# A senha nunca sai daqui, nem para o titular: o hash é credencial, não é
# dado pessoal que o Art. 18 mande entregar. O resto do cadastro vai inteiro.
CAMPOS_QUE_NUNCA_SAEM = frozenset({"senha_hash"})


def encontrar_aluno(identificador: str) -> dict | None:
    """O aluno, procurado por id, e-mail ou usuário -- nessa ordem.

    O RA não entra: ele é único dentro de uma escola, não no banco inteiro, e
    um pedido de exclusão atendido na pessoa errada não tem volta.
    """
    chave = str(identificador or "").strip()
    if not chave:
        return None
    for buscar in (buscar_aluno_por_id, buscar_aluno_por_email, buscar_aluno_por_username):
        try:
            aluno = buscar(chave)
        except Exception:  # noqa: BLE001 -- repo já loga; aqui só tenta o próximo
            aluno = None
        if aluno:
            return aluno
    return None


def _cadastro_sem_credencial(aluno: dict) -> dict:
    return {chave: valor for chave, valor in aluno.items() if chave not in CAMPOS_QUE_NUNCA_SAEM}


def reunir_dados_do_aluno(aluno: dict) -> dict:
    """Tudo que o app guarda dessa pessoa, pronto para virar JSON."""
    aluno_id = str(aluno.get("id") or "")
    escola_id = str(aluno.get("escola_id") or "")

    respostas = buscar_logs(escola_id, aluno_id) if escola_id and aluno_id else []
    progresso = listar_progressos_rpg_do_aluno(aluno_id) if aluno_id else []
    conclusoes = listar_conclusoes_do_aluno(aluno_id) if aluno_id else []
    focos = listar_focos_do_aluno(aluno_id) if aluno_id else []

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aluno": _cadastro_sem_credencial(aluno),
        "respostas": respostas,
        "progresso_rpg": progresso,
        "partidas_concluidas": conclusoes,
        "foco_de_estudo": focos,
        "resumo": resumo_do_que_existe(aluno, respostas, progresso, conclusoes, focos),
    }


def resumo_do_que_existe(
    aluno: dict,
    respostas: list,
    progresso: list,
    conclusoes: list | None = None,
    focos: list | None = None,
) -> dict:
    """A confirmação de existência do Art. 18, I -- em números."""
    acertos = sum(1 for linha in respostas if str(linha.get("resultado", "")).strip().lower().startswith("acert"))
    datas = sorted(str(linha.get("data_hora") or "") for linha in respostas if linha.get("data_hora"))
    return {
        "cadastro": 1 if aluno else 0,
        "respostas": len(respostas),
        "acertos": acertos,
        "aventuras_de_rpg_salvas": len(progresso),
        "partidas_concluidas": len(conclusoes or []),
        "focos_de_estudo": len(focos or []),
        "primeira_resposta": datas[0] if datas else None,
        "ultima_resposta": datas[-1] if datas else None,
        "consentimento_em": aluno.get("consentimento_dados_em"),
    }


def apagar_dados_do_aluno(aluno: dict) -> dict:
    """Apaga o aluno e CONFERE se o CASCADE levou o resto junto.

    Devolve o que sobrou. Sobrar linha não é detalhe: seria dado pessoal
    continuando no banco depois de um pedido de exclusão atendido.
    """
    aluno_id = str(aluno.get("id") or "")
    escola_id = str(aluno.get("escola_id") or "")
    if not aluno_id:
        return {"apagado": False, "motivo": "aluno sem id", "sobraram": {}}

    resultado = excluir_aluno(aluno_id)
    if resultado is None:
        return {"apagado": False, "motivo": "o banco recusou a exclusao", "sobraram": {}}

    sobrou_cadastro = buscar_aluno_por_id(aluno_id)
    sobraram_respostas = buscar_logs(escola_id, aluno_id) if escola_id else []
    sobrou_progresso = listar_progressos_rpg_do_aluno(aluno_id)

    sobraram = {
        "cadastro": 1 if sobrou_cadastro else 0,
        "respostas": len(sobraram_respostas),
        "progresso_rpg": len(sobrou_progresso),
        "partidas_concluidas": len(listar_conclusoes_do_aluno(aluno_id)),
        "foco_de_estudo": len(listar_focos_do_aluno(aluno_id)),
    }
    return {
        "apagado": not any(sobraram.values()),
        "motivo": "" if not any(sobraram.values()) else "o CASCADE nao levou tudo",
        "sobraram": sobraram,
    }


def linhas_do_resumo(resumo: dict[str, Any]) -> list[str]:
    """O resumo em frases, para o terminal e para um dia uma tela."""
    return [
        f"Cadastro: {'existe' if resumo.get('cadastro') else 'nao existe'}",
        f"Respostas gravadas: {resumo.get('respostas', 0)} ({resumo.get('acertos', 0)} certas)",
        f"Aventuras de RPG salvas: {resumo.get('aventuras_de_rpg_salvas', 0)}",
        f"Primeira resposta: {resumo.get('primeira_resposta') or '-'}",
        f"Ultima resposta: {resumo.get('ultima_resposta') or '-'}",
        f"Consentimento aceito em: {resumo.get('consentimento_em') or '-'}",
    ]
