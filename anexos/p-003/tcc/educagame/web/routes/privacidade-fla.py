from __future__ import annotations

from flask import Blueprint, render_template

from core.privacidade import ATUALIZADO_EM, secoes_da_privacidade
from web.routes.flask_helpers_fla import contexto_aluno_template

privacidade_bp = Blueprint("privacidade", __name__)


@privacidade_bp.route("/")
def tela_privacidade():
    """Política de privacidade, pública de propósito -- igual a ajuda.

    Quem decide se cadastra precisa poder ler ANTES de estar logado (é
    justamente o link que a caixa de aceite do cadastro abre), e um
    responsável que nunca teve conta também precisa conseguir achar isto
    sem senha nenhuma.
    """
    return render_template(
        "privacidade.html",
        secoes=secoes_da_privacidade(),
        atualizado_em=ATUALIZADO_EM,
        **contexto_aluno_template(),
    )
