"""O campo "suporte": texto ou tabela que o enunciado referencia.

Por que este arquivo existe
----------------------------
Relatorio de QA de 23/09/2026, achado critico 3.2: a IA as vezes escreve
"a tabela abaixo" ou "in the passage" sem nenhum suporte de verdade --
Escape Room de Ingles e de Matematica tinham exatamente esse problema, e a
questao ficava logicamente impossivel de responder.

A correcao tem duas partes: o prompt (services/ia/enigma.py) passa a pedir
o campo suporte quando a pergunta citar algo assim, e a validacao
(services/ia/validacao.py) recusa a questao quando a pergunta cita suporte
e o campo continua vazio -- rede de seguranca para quando o prompt sozinho
nao bastar.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.ia.normalizacao import normalizar_payload_questao
from services.ia.validacao import _pergunta_cita_suporte_ausente, validar_questao_gerada

TEMPLATES = Path(__file__).resolve().parent.parent / "web" / "templates"


def _questao_base(pergunta: str, suporte=None) -> dict:
    questao = {
        "pergunta": pergunta,
        "opcoes": ["Fazenda A", "Fazenda B", "Fazenda C", "Fazenda D"],
        "correta": 0,
        "explicacao": [{"tipo": "resultado", "conteudo": "Porque a Fazenda A produziu mais toneladas que as demais."}],
    }
    if suporte is not None:
        questao["suporte"] = suporte
    return questao


# ====================== NORMALIZACAO ======================


def test_sem_suporte_normaliza_para_tipo_nenhum():
    payload = normalizar_payload_questao(_questao_base("Quanto é 2 + 2?"))

    assert payload["suporte"] == {
        "tipo": "nenhum",
        "titulo": "",
        "texto": "",
        "tabela": {"colunas": [], "linhas": []},
    }


def test_suporte_texto_bem_formado_e_preservado():
    payload = normalizar_payload_questao(
        _questao_base(
            "Leia o texto abaixo e responda.",
            {"tipo": "texto", "titulo": "Um trecho", "texto": "Era uma vez..."},
        )
    )

    assert payload["suporte"]["tipo"] == "texto"
    assert payload["suporte"]["titulo"] == "Um trecho"
    assert payload["suporte"]["texto"] == "Era uma vez..."


def test_suporte_tipo_texto_sem_conteudo_vira_nenhum():
    """A IA as vezes declara o tipo e esquece do conteudo -- tratar como se
    nao tivesse vindo suporte nenhum, nao como um suporte vazio."""
    payload = normalizar_payload_questao(
        _questao_base("Pergunta qualquer.", {"tipo": "texto", "texto": "   "})
    )

    assert payload["suporte"]["tipo"] == "nenhum"


def test_suporte_tabela_bem_formada_e_preservada():
    payload = normalizar_payload_questao(
        _questao_base(
            "A tabela abaixo mostra a produção de três fazendas.",
            {
                "tipo": "tabela",
                "titulo": "Produção",
                "tabela": {"colunas": ["Fazenda", "Toneladas"], "linhas": [["A", "10"], ["B", "20"]]},
            },
        )
    )

    assert payload["suporte"]["tipo"] == "tabela"
    assert payload["suporte"]["tabela"]["colunas"] == ["Fazenda", "Toneladas"]
    assert payload["suporte"]["tabela"]["linhas"] == [["A", "10"], ["B", "20"]]


def test_suporte_tabela_sem_linhas_vira_nenhum():
    payload = normalizar_payload_questao(
        _questao_base("Pergunta qualquer.", {"tipo": "tabela", "tabela": {"colunas": ["X"], "linhas": []}})
    )

    assert payload["suporte"]["tipo"] == "nenhum"


def test_suporte_com_tipo_desconhecido_vira_nenhum():
    payload = normalizar_payload_questao(_questao_base("Pergunta qualquer.", {"tipo": "grafico"}))

    assert payload["suporte"]["tipo"] == "nenhum"


def test_suporte_que_nao_e_dicionario_vira_nenhum():
    payload = normalizar_payload_questao(_questao_base("Pergunta qualquer.", "não é um dict"))

    assert payload["suporte"]["tipo"] == "nenhum"


def test_suporte_em_ingles_nao_ganha_acento_pt():
    payload = normalizar_payload_questao(
        _questao_base(
            "In the passage, what is the tone?",
            {"tipo": "texto", "texto": "Nao tem acento nenhum aqui de proposito"},
        ),
        modo_ingles=True,
    )

    assert payload["suporte"]["texto"] == "Nao tem acento nenhum aqui de proposito"


# ====================== A REGEX NAO PODE TER FALSO POSITIVO ======================


def test_referencia_a_conhecimento_comum_nao_e_suporte_ausente():
    """"Com base na tabela periódica" e "segundo a tabela de conversão" não
    citam nenhum suporte desta questão -- é conhecimento universal, e uma
    primeira versão da regex (gatilho em "com base"/"segundo") rejeitava os
    dois por engano."""
    casos = [
        "Com base na tabela periódica, qual elemento tem número atômico 8?",
        "Segundo a tabela de conversão de unidades do SI, quantos metros há em um km?",
        "Qual figura de linguagem está presente no verso a seguir: 'Ó mar salgado'?",
        "Qual gráfico representa melhor uma função do 2º grau?",
    ]
    for pergunta in casos:
        assert not _pergunta_cita_suporte_ausente({"pergunta": pergunta}), pergunta


def test_referencia_a_suporte_visivel_nao_e_suporte_ausente():
    """A palavra + "abaixo"/"a seguir" citando suporte QUE EXISTE não deve
    ser recusada."""
    dados = {
        "pergunta": "A tabela abaixo mostra a produção de três fazendas. Qual produziu mais?",
        "suporte": {"tipo": "tabela", "tabela": {"colunas": ["Fazenda"], "linhas": [["A"]]}},
    }
    assert not _pergunta_cita_suporte_ausente(dados)


# ====================== OS DOIS CASOS REAIS DO RELATORIO ======================


def test_caso_real_ingles_escape_room():
    """Escape Room · Inglês (08:46:39): "In the passage, what is the main
    purpose..." sem nenhum passage exibido."""
    dados = {
        "pergunta": "In the passage, what is the main purpose of the author's description of the bustling marketplace?",
    }
    assert _pergunta_cita_suporte_ausente(dados)


def test_caso_real_matematica_escape_room():
    """Escape Room · Matemática (08:53:32): "...com base na tabela abaixo?"
    sem nenhuma tabela exibida."""
    dados = {
        "pergunta": "Com base na tabela abaixo, qual foi a tendência de crescimento?",
    }
    assert _pergunta_cita_suporte_ausente(dados)


# ====================== A VALIDACAO PONTA A PONTA ======================


def test_validar_questao_gerada_recusa_suporte_ausente():
    dados, valida, motivo = validar_questao_gerada(
        _questao_base("A tabela abaixo mostra os dados. Qual é maior?"),
        "Geografia",
        contexto="oraculo",
    )

    assert valida is False
    assert motivo == "suporte-ausente"


def test_validar_questao_gerada_aceita_quando_o_suporte_esta_preenchido():
    dados, valida, motivo = validar_questao_gerada(
        _questao_base(
            "A tabela abaixo mostra os dados. Qual é maior?",
            {"tipo": "tabela", "tabela": {"colunas": ["Item"], "linhas": [["A"]]}},
        ),
        "Geografia",
        contexto="oraculo",
    )

    assert valida is True, motivo


# ====================== O PROMPT PEDE O CAMPO ======================


def test_o_prompt_do_oraculo_pede_o_campo_suporte():
    from services.ia.enigma import _prompts_oraculo

    system_prompt, user_prompt = _prompts_oraculo("Geografia", "3º Ano EM", "Medio", "Globalização")

    assert '"suporte"' in user_prompt
    assert "tabela" in user_prompt.lower()
    assert "grafico" in system_prompt.lower() or "gráfico" in system_prompt.lower()


def test_o_prompt_do_oraculo_probe_questao_dependente_de_grafico():
    """O sistema so sabe renderizar texto e tabela -- o prompt tem de
    desviar a IA de propor questao que dependa de um grafico de verdade,
    em vez de tentar gerar dado de grafico (mais arriscado e sem
    renderizador nenhum pra ele)."""
    from services.ia.enigma import _prompts_oraculo

    system_prompt, _ = _prompts_oraculo("Matematica", "3º Ano EM", "Medio", "Funções")

    texto = system_prompt.lower()
    assert "nunca" in texto and ("grafico" in texto or "gráfico" in texto)


# ====================== AS TELAS INCLUEM O PARTIAL ======================


@pytest.mark.parametrize(
    "template",
    ["oraculo.html", "escape_room.html", "treino.html", "rpg.html"],
)
def test_tela_inclui_o_partial_de_suporte(template):
    """As quatro telas movidas por invocar_enigma (Oraculo, Escape Room,
    Treino Rapido, RPG) tem de desenhar o suporte -- e' o mesmo gerador
    para as quatro (services/ia/enigma.py), entao o mesmo bug (achado 3.2)
    podia aparecer em qualquer uma."""
    texto = (TEMPLATES / template).read_text(encoding="utf-8")

    assert 'include "partials/suporte_questao.html"' in texto


def test_partial_de_suporte_desenha_texto(client):
    from flask import render_template

    with client.application.test_request_context():
        html = render_template(
            "partials/suporte_questao.html",
            suporte={"tipo": "texto", "titulo": "Um trecho", "texto": "Era uma vez um reino distante."},
        )

    assert "Um trecho" in html
    assert "Era uma vez um reino distante." in html
    assert "<table" not in html


def test_partial_de_suporte_desenha_tabela(client):
    from flask import render_template

    with client.application.test_request_context():
        html = render_template(
            "partials/suporte_questao.html",
            suporte={
                "tipo": "tabela",
                "titulo": "",
                "tabela": {"colunas": ["Fazenda", "Toneladas"], "linhas": [["A", "10"], ["B", "20"]]},
            },
        )

    assert "<table" in html
    assert "Fazenda" in html and "Toneladas" in html
    assert "<td>A</td>" in html or "A</td>" in html


def test_partial_de_suporte_nao_desenha_nada_quando_tipo_nenhum(client):
    from flask import render_template

    with client.application.test_request_context():
        html = render_template(
            "partials/suporte_questao.html",
            suporte={"tipo": "nenhum", "titulo": "", "texto": "", "tabela": {"colunas": [], "linhas": []}},
        )

    assert html.strip() == ""
