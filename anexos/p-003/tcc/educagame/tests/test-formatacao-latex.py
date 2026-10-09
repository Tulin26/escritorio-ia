from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.utils import formatar_unidades_texto
from web.routes.flask_helpers_fla import formatar_texto_simples_pergunta

TEMPLATES = Path(__file__).resolve().parent.parent / "web" / "templates"
TEMPLATES_COM_MATHJAX = ("treino.html", "laboratorio.html", "rpg.html")


def test_filtro_unidades_registrado_no_app(client):
    # MELHORIA: regressao para uma quebra real -- os templates passaram a
    # usar o filtro "unidades", e sem o registro em flask_app.py toda tela
    # de questao respondia 500 ("No filter named 'unidades'"). Nenhum teste
    # da suite pegava isso, porque nenhum renderizava essas telas.
    from flask import render_template_string

    with client.application.app_context():
        assert render_template_string("{{ v|unidades }}", v="48 m^2") == "48 m²"


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("48 m^2", "48 m²"),
        ("30 cm^3", "30 cm³"),
        ("5 m/s^2", "5 m/s²"),
    ],
)
def test_unidades_comuns_viram_expoente_de_verdade(bruto, esperado):
    assert formatar_unidades_texto(bruto) == esperado


def test_enunciado_da_questao_tambem_formata_unidades():
    # MELHORIA: regressao para um bug visto pelo usuario. Só o Laboratório
    # aplicava formatar_unidades_texto, e apenas nas ALTERNATIVAS -- na
    # mesma tela, as opções mostravam "48 m²" e o enunciado "m^2". MathJax
    # não resolve isso: ele só processa o que está entre delimitadores, e o
    # "m^2" do texto corrido fica de fora.
    pergunta = "Uma sala retangular mede 6 m por 8 m. Qual e sua area em m^2?"

    assert "m²" in formatar_texto_simples_pergunta(pergunta)
    assert "m^2" not in formatar_texto_simples_pergunta(pergunta)


@pytest.mark.parametrize("nome_template", TEMPLATES_COM_MATHJAX)
def test_mathjax_nao_usa_cifrao_como_delimitador_inline(nome_template):
    # MELHORIA: regressao para um bug verificado ao vivo no navegador. Com
    # "$" configurado como delimitador de fórmula inline, um enunciado com
    # dinheiro ("Um produto de R$ 200 ... o desconto em R$?") tinha TODO o
    # texto entre os dois cifrões engolido pelo MathJax e renderizado como
    # matemática itálica ilegível. As fórmulas do app usam $$...$$
    # (displayMath), que não depende dessa configuração.
    conteudo = (TEMPLATES / nome_template).read_text(encoding="utf-8")
    match = re.search(r"inlineMath:\s*(\[[^\]]*\]\])", conteudo)

    assert match, f"{nome_template} deveria configurar inlineMath"
    assert '"$"' not in match.group(1)


def test_todas_as_telas_de_questao_renderizam_sem_erro(client):
    # Guarda contra o tipo de quebra acima: renderiza de fato cada tela de
    # questão, com um enunciado que mistura dinheiro e expoente, e confere
    # que o expoente chega formatado ao aluno.
    from flask import render_template

    questao = {
        "pergunta": "Um produto de R$ 200. Qual a area em m^2?",
        "opcoes": ["48 m^2", "30 cm^3", "5 m/s^2", "R$ 30"],
        "alternativas": ["48 m^2", "30 cm^3", "5 m/s^2", "R$ 30"],
        "correta": 0,
    }
    telas = [
        ("oraculo.html", {"enigma": questao, "aluno": {}, "alunos": [], "materias": [], "respondido": False}),
        ("enem.html", {"questao": questao, "simulado": {"fase": "quiz"}, "aluno": {}, "alunos": [], "resultado": None, "respondido": False}),
        (
            "escape_room.html",
            {
                "questao": questao,
                "estado": {"fase": "sala", "atual": 0, "salas": [1, 2]},
                "sala": {"nome": "S", "numero": 1},
                "aluno": {},
                "alunos": [],
                "resultado": None,
            },
        ),
        (
            "boss_rush.html",
            {
                "questao": questao,
                "estado": {"fase": "battle", "idx": 0, "bosses": [1, 2]},
                "boss": {"nome": "B", "area_label": "X"},
                "aluno": {},
                "alunos": [],
                "resultado": None,
            },
        ),
    ]

    with client.application.test_request_context("/"):
        for nome_template, contexto in telas:
            html = render_template(nome_template, **contexto)
            assert "m^2" not in html, f"{nome_template} mostrou expoente cru"
            assert "m²" in html, f"{nome_template} nao formatou o expoente"


RESULTADO_COM_UNIDADE = {
    "acertou": True,
    "pontos": 20,
    "resposta_aluno": "160 cm^2",
    "resposta_correta": "160 cm^2",
    "xp_ganho": 60,
    "hp_perda": 0,
    "explicacao_texto": "Resposta correta: 160 cm^2.",
    "feedback": {
        "confundiu": "A area sai em cm^2.",
        "evitar": "Confira a unidade final em cm^2.",
        "treino": "Refaca dois exercicios de area em cm^2.",
    },
}


def test_card_de_resultado_formata_unidade(client):
    # MELHORIA: o teste acima cobre a tela da PERGUNTA, e por isso o expoente
    # cru sobreviveu na tela do RESULTADO: "Sua resposta: 160 cm^2". O
    # Laboratorio escapava porque a rota dele ja passa formatar_unidades_texto
    # em Python (laboratorio_fla.py), mas Treino, Oraculo, ENEM, Boss Rush e
    # Escape Room compartilham este partial e mostravam o "^" cru.
    from flask import render_template

    with client.application.test_request_context():
        html = render_template(
            "partials/result_card.html",
            resultado=RESULTADO_COM_UNIDADE,
            explicacao_texto=RESULTADO_COM_UNIDADE["explicacao_texto"],
        )

    assert "cm²" in html
    assert "cm^2" not in html


def test_rpg_formata_unidade_no_resultado(client):
    # O RPG nao usa o partial: tem o proprio bloco de resultado em rpg.html.
    from flask import render_template

    with client.application.test_request_context():
        html = render_template(
            "rpg.html",
            estado={
                "resultado": RESULTADO_COM_UNIDADE,
                "jornada": {},
                "cena": None,
                "hp": 100,
                "xp": 60,
                "fase": 1,
                "status": "em_andamento",
            },
            fases_totais=15,
            resumo={"titulo": "Arquiteto do Conhecimento", "descricao": "", "placar": {}},
            desafio=None,
            progresso=10,
            aluno={},
            alunos=[],
            configs=[],
        )

    assert "cm²" in html
    assert "cm^2" not in html
