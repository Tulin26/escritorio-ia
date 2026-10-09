"""O expoente com letra chega desenhado no enunciado do Oráculo.

Visto em produção em 11/09/2026:

    Sobre a função exponencial f(x)=a^x, com base a>1, ...

O Oráculo mostrava o enunciado como texto puro, e `expoentes_em_sobrescrito`,
que o Treino usa, só troca expoente numérico. Medido: nenhuma das 34.050
perguntas do banco que o Oráculo usa tem "^"; é só texto da IA.
"""

from __future__ import annotations

import pytest
from markupsafe import Markup

from core.expoentes_html import expoentes_html

FRASE = (
    "Sobre a função exponencial f(x)=a^x, com base a>1, qual das alternativas "
    "a seguir descreve corretamente sua característica principal?"
)


def test_o_caso_da_tela():
    saida = str(expoentes_html(FRASE))

    assert "a<sup>x</sup>" in saida, saida
    assert "^" not in saida
    assert "a&gt;1" in saida, "o '>' do texto tem de sair escapado, uma vez só"


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("e^{-x}", "e<sup>-x</sup>"),
        ("x^{n+1}", "x<sup>n+1</sup>"),
        ("2^10", "2<sup>10</sup>"),
        ("(x+1)^2", "(x+1)<sup>2</sup>"),
        ("e^-x", "e<sup>-x</sup>"),
        ("x^2y", "x<sup>2</sup>y"),
    ],
)
def test_as_formas_que_a_ia_escreve(bruto, esperado):
    assert str(expoentes_html(bruto)) == esperado


def test_o_texto_da_ia_continua_escapado():
    """O filtro devolve HTML; só o <sup> que ele cria pode sair sem escape."""
    saida = str(expoentes_html('<script>alert("x")</script> a^x'))

    assert "<script>" not in saida
    assert "&lt;script&gt;" in saida
    assert "a<sup>x</sup>" in saida


def test_expoente_que_nao_cabe_fica_visivel():
    """Com espaço dentro das chaves não há como saber o que é expoente."""
    assert str(expoentes_html("x^{a b}")) == "x^{a b}"


def test_circunflexo_sem_base_fica_como_esta():
    assert str(expoentes_html("^x solto")) == "^x solto"


def test_sem_circunflexo_so_escapa():
    assert str(expoentes_html("Qual é a área?")) == "Qual é a área?"
    assert isinstance(expoentes_html("x"), Markup)


def test_a_tela_do_oraculo_desenha_o_expoente(client, monkeypatch):
    """Pela rota de verdade, e não só a função."""
    from tests.apoio_flask import carimbar_sessao
    from web.routes import oraculo_fla

    enigma = {
        "pergunta": FRASE,
        "opcoes": ["Cresce", "Decresce", "É constante", "É periódica"],
        "correta": 0,
        "materia": "Matematica",
        "materia_label": "Matemática",
        "_origem_geracao": "ia",
    }
    monkeypatch.setattr(
        oraculo_fla, "obter_estado_flask",
        lambda nome, padrao=None: dict(enigma) if nome == "enigma_atual" else padrao,
    )
    monkeypatch.setattr(oraculo_fla, "alunos_para_selecao", lambda: [])
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        sess["aluno_id"] = "aluno-1"
        carimbar_sessao(sess)

    corpo = client.get("/oraculo/").get_data(as_text=True)

    assert "a<sup>x</sup>" in corpo
    assert "a^x" not in corpo
