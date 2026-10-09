"""O enunciado nao pode trazer as proprias alternativas com letra fixa.

Por que este arquivo existe
----------------------------
Relatorio de QA de 23/09/2026, achado 3.1, caso Batalha contra Chefes ·
Batalha 7 · Chefe 3: o proprio enunciado trazia as opcoes com letras fixas
("A) adubos inorganicos; B) plantar leguminosas; C) fosforo...") enquanto a
lista exibida mostrava outra ordem, pos-embaralhamento. O aluno que le "B"
no enunciado e marca B erra sem cometer erro de conteudo -- a correcao da
letra citada na EXPLICACAO (services/ia/citacao_alternativas.py) nao
alcanca esse caso, porque o texto problematico esta na PERGUNTA.
"""

from __future__ import annotations

import pytest

from services.enem_service import _validar_questao
from services.ia.opcoes_no_enunciado import pergunta_embute_opcoes_com_letra
from services.ia.validacao import validar_questao_gerada


def _questao_base(pergunta: str) -> dict:
    return {
        "pergunta": pergunta,
        "opcoes": ["Fazenda A", "Fazenda B", "Fazenda C", "Fazenda D"],
        "correta": 0,
        "explicacao": [{"tipo": "resultado", "conteudo": "Porque a Fazenda A produziu mais toneladas que as demais."}],
    }


# ====================== A REGRA, ISOLADA ======================


def test_caso_real_batalha_contra_chefes():
    pergunta = (
        "Qual pratica agricola reduz mais a erosao do solo? "
        "A) adubos inorganicos; B) plantar leguminosas; C) fosforo; D) irrigacao intensiva"
    )
    assert pergunta_embute_opcoes_com_letra(pergunta)


def test_duas_letras_bastam():
    assert pergunta_embute_opcoes_com_letra("Escolha entre A) fazer isso e B) fazer aquilo.")


def test_uma_letra_sozinha_nao_e_lista():
    # Um "A)" isolado nao caracteriza uma lista de opcoes -- pode ser
    # qualquer outra coisa (item unico, sigla, etc.).
    assert not pergunta_embute_opcoes_com_letra("No item A) do enunciado, considere o grafico.")


def test_letras_fora_de_ordem_nao_e_lista():
    # Uma lista de opcoes real sempre aparece em ordem alfabetica -- letras
    # soltas fora de ordem sao outra coisa, nao a mesma causa-raiz.
    assert not pergunta_embute_opcoes_com_letra("Compare o ponto C) com o ponto A) do grafico.")


def test_sem_pergunta_nao_quebra():
    assert not pergunta_embute_opcoes_com_letra(None)
    assert not pergunta_embute_opcoes_com_letra("")


def test_pergunta_comum_nao_e_falso_positivo():
    casos = [
        "Qual é a capital do Brasil?",
        "Um corpo de massa 4 kg acelera a 3 m/s². Qual a força resultante?",
        "A tabela abaixo mostra a produção de três fazendas. Qual produziu mais?",
        "Leia o texto a seguir e responda: qual figura de linguagem aparece no verso 'Ó mar salgado'?",
    ]
    for pergunta in casos:
        assert not pergunta_embute_opcoes_com_letra(pergunta), pergunta


# ====================== A VALIDACAO COMPARTILHADA (ORACULO/ESCAPE ROOM/RPG/TREINO/LABORATORIO) ======================


def test_validar_questao_gerada_recusa_opcoes_embutidas():
    dados, valida, motivo = validar_questao_gerada(
        _questao_base(
            "Qual pratica reduz a erosao? A) adubos inorganicos; B) plantar leguminosas; C) fosforo"
        ),
        "Geografia",
        contexto="oraculo",
    )

    assert valida is False
    assert motivo == "opcoes-embutidas-no-enunciado"


def test_validar_questao_gerada_aceita_enunciado_comum():
    dados, valida, motivo = validar_questao_gerada(
        _questao_base("Qual fazenda produziu mais toneladas?"),
        "Geografia",
        contexto="oraculo",
    )

    assert valida is True, motivo


# ====================== O VALIDADOR PROPRIO DO ENEM/BATALHA ======================


def test_enem_validar_questao_recusa_opcoes_embutidas():
    q = {
        "pergunta": (
            "Qual pratica agricola reduz mais a erosao do solo? "
            "A) adubos inorganicos; B) plantar leguminosas; C) fosforo; D) irrigacao intensiva"
        ),
        "alternativas": ["Remover cobertura", "Pesticidas", "Plantar leguminosas", "Irrigacao intensiva"],
        "correta": "Plantar leguminosas",
        "explicacao": [{"tipo": "resultado", "conteudo": "Leguminosas fixam nitrogenio e protegem o solo da erosao."}],
    }

    assert _validar_questao(q) is False


def test_enem_validar_questao_aceita_enunciado_comum():
    q = {
        "pergunta": "Qual é a capital do Brasil?",
        "alternativas": ["Brasília", "São Paulo", "Rio de Janeiro", "Salvador"],
        "correta": "Brasília",
        "explicacao": [{"tipo": "resultado", "conteudo": "Brasília é a capital federal do Brasil desde 1960."}],
    }

    assert _validar_questao(q) is True


# ====================== O PROMPT PEDE PARA NUNCA FAZER ISSO ======================


def test_o_prompt_do_oraculo_proibe_opcoes_no_enunciado():
    from services.ia.enigma import _prompts_oraculo

    system_prompt, _ = _prompts_oraculo("Geografia", "3º Ano EM", "Medio", "Erosão do solo")

    texto = system_prompt.lower()
    assert "nunca" in texto and "pergunta" in texto and "opcoes" in texto


def test_o_prompt_do_enem_proibe_opcoes_no_enunciado():
    from services.enem_service import _prompt_enem

    system_prompt, _ = _prompt_enem("Matematica e suas Tecnologias", "Medio")

    texto = system_prompt.lower()
    assert "nunca" in texto and "pergunta" in texto and "alternativas" in texto
