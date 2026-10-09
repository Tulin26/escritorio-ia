from __future__ import annotations

from flask import Blueprint, render_template, session

from core.ajuda import secoes_da_ajuda
from core.sessao import MINUTOS_INATIVIDADE_PADRAO
from web.routes.flask_helpers_fla import contexto_aluno_template

ajuda_bp = Blueprint("ajuda", __name__)


@ajuda_bp.route("/")
def tela_ajuda():
    """A ajuda dentro do app — a décima heurística de Nielsen.

    Até aqui a única documentação era um PDF FORA do sistema, entregue à mão.
    Isso falha por dois lados: o aluno que trava no meio de uma questão não
    tem onde olhar, e quem tem o PDF pode estar lendo uma versão velha.

    O conteúdo vem de core/ajuda.py, o mesmo que alimenta o PDF -- escrever
    um texto novo aqui criaria duas descrições dos mesmos oito modos, e a
    segunda vez que alguém mexesse numa delas as duas discordariam.

    Aberta a quem não fez login de propósito: metade das dúvidas ("o que é o
    código da escola?", "por que a primeira tela demora?") acontece ANTES de
    entrar, que é justamente quando a pessoa não alcançaria uma página presa
    atrás do login.
    """
    return render_template(
        "ajuda.html",
        secoes=secoes_da_ajuda(
            # Perguntado ao código, nunca escrito: foi um número escrito à mão
            # que fez o guia antigo mentir.
            minutos_sessao=int(MINUTOS_INATIVIDADE_PADRAO),
            eh_professor=session.get("usuario_role") in ("professor", "desenvolvedor"),
        ),
        **contexto_aluno_template(),
    )
