"""O simulado do ENEM não repete a questão que o aluno acabou de ver.

Visto em 13/09/2026: as questões 1 e 2 de um simulado de Matemática eram a
mesma ("A função f(x) = (x - 14)^2 + 15 tem vértice em qual ponto?"). O
histórico guardava a pergunta normalizada, com acento; o filtro comparava com
a pergunta crua do banco, sem acento. Nunca casava.
"""

from __future__ import annotations

import json

import pytest

import services.enem_service as enem
from services import historico_perguntas as hp

CRUA = "A funcao f(x) = (x - 14)^2 + 15 tem vertice em qual ponto?"


def _questao(pergunta: str, correta: str) -> dict:
    return {
        "pergunta": pergunta,
        "alternativas": [correta, "outra 1", "outra 2", "outra 3", "outra 4"],
        "correta": correta,
        "explicacao": [],
        "area_bncc": "Matematica e suas Tecnologias",
    }


BANCO_DE_DUAS = [
    _questao(CRUA, "(14, 15)"),
    _questao("Qual e a distancia entre A(15,30) e B(18,34)?", "5"),
]


@pytest.fixture
def banco_de_duas(monkeypatch):
    monkeypatch.setattr(enem, "_FALLBACK_POR_AREA", {"Matematica e suas Tecnologias": []})
    monkeypatch.setattr(enem, "_fallback_autoral_por_area", lambda area: [dict(q) for q in BANCO_DE_DUAS])
    monkeypatch.setattr(enem, "_fallback_matematica_variantes", lambda: [])


def test_crua_e_normalizada_dao_a_mesma_chave():
    normalizada = enem._normalizar_textos_questao(_questao(CRUA, "(14, 15)"))["pergunta"]

    assert normalizada != CRUA, "o caso só existe se a normalização mexe no texto"
    assert enem._chave_repeticao(normalizada) == enem._chave_repeticao(CRUA)


def test_perguntas_diferentes_nao_colidem():
    assert enem._chave_repeticao(BANCO_DE_DUAS[0]["pergunta"]) != enem._chave_repeticao(BANCO_DE_DUAS[1]["pergunta"])


def test_a_chave_ignora_o_espaco_que_a_normalizacao_poe_na_pontuacao():
    """Uma chave que só tirasse o acento deixaria escapar 53 perguntas do banco
    de reserva, como as citações de Linguagens: a normalização separava a aspa
    do ponto ("picanha.'" virava "picanha. '").

    Desde 15/09/2026 a normalização não separa mais (tests/test_defeitos_visiveis.py),
    mas o histórico de um simulado em andamento ainda guarda a pergunta com o
    espaço. Por isso as duas versões ficam escritas aqui, sem depender dela."""
    from core.text_cleanup import chave_busca

    crua = (
        "Leia: 'Pedro é vegetariano convicto há dez anos. Por isso, no jantar de ontem, "
        "repetiu três vezes a picanha.' O trecho é incoerente porque:"
    )
    gravada_antes = crua.replace("picanha.' O", "picanha. ' O")

    def so_sem_acento(texto: str) -> str:
        return " ".join(chave_busca(texto).split())

    assert so_sem_acento(gravada_antes) != so_sem_acento(crua), "o caso só existe se o espaço muda o texto"
    assert enem._chave_repeticao(gravada_antes) == enem._chave_repeticao(crua)


def test_a_questao_ja_vista_nao_volta(banco_de_duas):
    vista = enem._normalizar_textos_questao(dict(BANCO_DE_DUAS[0]))["pergunta"]

    sorteadas = {enem._fallback("Matematica e suas Tecnologias", "Medio", [vista])["pergunta"] for _ in range(30)}

    assert len(sorteadas) == 1
    assert enem._chave_repeticao(sorteadas.pop()) == enem._chave_repeticao(BANCO_DE_DUAS[1]["pergunta"])


def test_duas_questoes_seguidas_no_mesmo_simulado_sao_diferentes(banco_de_duas, monkeypatch):
    """Pelo caminho de verdade: IA fora do ar, banco de reserva, histórico da sessão."""
    from flask_app import app

    linhas: dict = {}
    monkeypatch.setattr(hp, "carregar_estado_temporario", lambda chave: json.loads(json.dumps(linhas.get(chave))) if chave in linhas else None)
    monkeypatch.setattr(hp, "salvar_estado_temporario", lambda chave, estado: linhas.__setitem__(chave, json.loads(json.dumps(estado))) or True)
    monkeypatch.setattr(enem, "_gerar_via_ia", lambda *a, **k: None)
    monkeypatch.setattr(enem, "obter_ultimo_provedor_ia", lambda: "")

    for _ in range(10):
        linhas.clear()
        perguntas = []
        for _ in range(2):
            with app.test_request_context("/"):
                from flask import session

                session["_estado_sid"] = "sid-simulado"
                perguntas.append(enem.gerar_questao_enem("Matematica e suas Tecnologias", "Medio")["pergunta"])

        assert enem._chave_repeticao(perguntas[0]) != enem._chave_repeticao(perguntas[1]), perguntas


def test_a_ia_nao_emplaca_a_questao_que_o_aluno_acabou_de_ver(monkeypatch):
    """O mesmo filtro no caminho da IA: ela pode devolver a pergunta já vista
    com outra acentuação, e aí o provedor é trocado."""
    from flask import session

    from flask_app import app

    linhas: dict = {}
    monkeypatch.setattr(hp, "carregar_estado_temporario", lambda chave: json.loads(json.dumps(linhas.get(chave))) if chave in linhas else None)
    monkeypatch.setattr(hp, "salvar_estado_temporario", lambda chave, estado: linhas.__setitem__(chave, json.loads(json.dumps(estado))) or True)
    monkeypatch.setattr(enem, "_orcamento_ia_enem_segundos", lambda: 30.0)
    monkeypatch.setattr(enem, "obter_ultimo_provedor_ia", lambda: "")

    nova = _questao("Qual e o valor de x em 2x + 6 = 10?", "2")
    respostas = iter([dict(BANCO_DE_DUAS[0], _provedor_ia="groq"), dict(nova, _provedor_ia="mistral")])
    monkeypatch.setattr(enem, "_gerar_via_ia", lambda *a, **k: next(respostas, None))

    with app.test_request_context("/"):
        session["_estado_sid"] = "sid-simulado"
        vista = enem._normalizar_textos_questao(dict(BANCO_DE_DUAS[0]))["pergunta"]
        enem._set_historico_sessao(("Matematica e suas Tecnologias", "Medio"), [vista])

        pergunta = enem.gerar_questao_enem("Matematica e suas Tecnologias", "Medio")["pergunta"]

    assert pergunta == nova["pergunta"], "a IA repetiu a questão e ela foi aceita"
