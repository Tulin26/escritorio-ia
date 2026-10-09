"""Todos os modos decidem Ensino Medio x Fundamental do mesmo jeito.

Esta decisao muda o que o aluno ve: quais materias aparecem no Laboratorio,
de qual banco offline sai a questao, e quais regras curriculares vao no
prompt da IA (o Fundamental tem uma lista propria que PROIBE Bhaskara, PA e
trigonometria).

Ela vivia escrita em CINCO lugares, um por modo, com listas diferentes:

    services/banks/em.py       EM, MEDIO, MÉDIO, 1O ANO, 2O ANO, 3O ANO, 1º, 2º, 3º
    services/calculo_service   EM, MEDIO, MÉDIO, 1º, 2º, 3º
    web/routes/laboratorio_fla EM, MEDIO, MÉDIO
    services/rpg_service       em, medio, 1o ano, 2o ano, 3o ano
    st/ui/tela_laboratorio_st  EM, MÉDIO, 1º, 2º, 3º      <- faltava "MEDIO"

Nos valores de SERIES as cinco concordavam, entao com dado vindo do
formulario nada aparecia. Bastava um ano_escolar digitado direto no banco
para as telas discordarem entre si, em silencio.
"""

from __future__ import annotations

import pytest

from core.config import SERIES, eh_ensino_medio

EM = ["1o Ano EM", "2o Ano EM", "3o Ano EM"]
EF = ["6o Ano", "7o Ano", "8o Ano", "9o Ano"]


def _decisoes(ano_escolar: str) -> dict[str, bool]:
    """A mesma pergunta, feita a cada modo pelo caminho que ele usa."""
    from services.calculo_service import _etapa_laboratorio
    from services.rpg_service import _serie_em
    from web.routes.laboratorio_fla import _serie_tipo_laboratorio

    return {
        "core.config": eh_ensino_medio(ano_escolar),
        "laboratorio (servico)": _etapa_laboratorio(ano_escolar) == "EM",
        "laboratorio (Flask)": _serie_tipo_laboratorio(ano_escolar) == "EM",
        "rpg": _serie_em(ano_escolar),
    }


# --------------------------------------------------------------------------
# os valores canonicos
# --------------------------------------------------------------------------


@pytest.mark.parametrize("serie", EM)
def test_series_de_ensino_medio(serie):
    assert eh_ensino_medio(serie), serie


@pytest.mark.parametrize("serie", EF)
def test_series_de_fundamental(serie):
    assert not eh_ensino_medio(serie), serie


def test_a_lista_de_series_esta_coberta():
    # Se alguem acrescentar uma serie em SERIES, ela tem que cair de um lado
    # ou do outro de proposito, e nao por acaso.
    assert set(SERIES) == set(EM) | set(EF), (
        "SERIES mudou: revise este teste e a classificacao de cada serie nova"
    )


# --------------------------------------------------------------------------
# a parte que importa: os modos nao podem discordar
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ano_escolar",
    [
        *SERIES,
        # grafias que nao vem do formulario, mas chegam de dado herdado ou
        # digitado direto no banco
        "Ensino Medio",
        "Ensino Médio",
        "ENSINO MEDIO",
        "ensino medio",
        "Medio",
        "MÉDIO",
        "1o Ano",
        "2o Ano",
        "3o Ano",
        "1º Ano EM",
        "6º Ano",
        "9º Ano",
        "Ensino Fundamental",
        "6o Ano EF",
        "9o Ano EF",
        "",
        "   ",
    ],
)
def test_todos_os_modos_concordam(ano_escolar):
    decisoes = _decisoes(ano_escolar)

    assert len(set(decisoes.values())) == 1, (
        f"os modos discordam sobre {ano_escolar!r}: {decisoes}"
    )


def test_medio_sem_acento_e_ensino_medio():
    # O caso concreto que estava quebrado: o Laboratorio do Streamlit
    # respondia Fundamental aqui, e o aluno via so Matematica -- sem Fisica
    # nem Quimica.
    assert eh_ensino_medio("Ensino Medio")
    assert eh_ensino_medio("ensino medio")
    assert eh_ensino_medio("MEDIO")


def test_acento_nao_muda_a_resposta():
    # A lista antiga trazia "MEDIO" e "MÉDIO" como entradas separadas, e foi
    # esquecer uma delas que criou a versao divergente. Agora o acento sai
    # antes da comparacao.
    for com, sem in [("Médio", "Medio"), ("Ensino Médio", "Ensino Medio")]:
        assert eh_ensino_medio(com) == eh_ensino_medio(sem)


@pytest.mark.parametrize("valor", [None, 0, [], {}])
def test_valor_estranho_nao_quebra(valor):
    assert eh_ensino_medio(valor) is False


def test_existe_uma_definicao_so():
    import ast
    import io
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    ignorar = {"__pycache__", ".venv", "tests", "node_modules", ".claude"}  # .claude: worktrees
    definicoes = []
    for arquivo in sorted(raiz.rglob("*.py")):
        if set(arquivo.parts) & ignorar:
            continue
        try:
            arvore = ast.parse(io.open(arquivo, encoding="utf-8-sig", errors="ignore").read())
        except SyntaxError:
            continue
        for no in arvore.body:
            if isinstance(no, ast.FunctionDef) and no.name == "eh_ensino_medio":
                definicoes.append(arquivo.relative_to(raiz).as_posix())

    assert definicoes == ["core/config.py"], definicoes
