"""A validação recusa contradição, não ausência de prova.

Em questões não-exatas, a checagem confere se a explicação combina com a
alternativa marcada. Ela pedia que a explicação apontasse para UMA única
alternativa; quando não conseguia decidir, recusava a questão como
"alternativa-correta-nao-comprovada".

Isso cobrava PROVA. O que a checagem existe para pegar é a IA marcar uma
alternativa e explicar outra — CONTRADIÇÃO. Três formas normais de escrever
caíam na exigência antiga:

  1. a explicação cita a marcada junto de outra palavra que também é
     alternativa ("modifica o verbo, então é um advérbio de modo");
  2. as alternativas se distinguem por palavras curtas, e todas casam pelo
     trecho longo em comum ("Vou à escola" / "Vou as escola");
  3. a explicação parafraseia ("Amazônia" explicada como "floresta
     amazônica").

Visto em produção: quatro rejeições seguidas no Oráculo, em Matemática,
História, Biologia e Português. Cada uma custa um provedor queimado e
empurra a questão para o banco offline.
"""

from __future__ import annotations

import pytest

from services.ia.validacao import (
    _explicacao_aponta_para_outra_alternativa,
    validar_questao_gerada,
)


def questao(pergunta, opcoes, correta_txt, resultado, passos=()):
    return {
        "enigma": "Nas brumas do templo, um sinal antigo aguarda.",
        "pergunta": pergunta,
        "opcoes": opcoes,
        "correta": opcoes.index(correta_txt),
        "explicacao": [{"tipo": "resultado", "conteudo": resultado}],
        "passos_resolucao": [
            {"titulo": "Passo", "conteudo": p, "final": i == len(passos) - 1}
            for i, p in enumerate(passos)
        ],
    }


# --------------------------------------------------------------------------
# escrita normal: tem que passar
# --------------------------------------------------------------------------

BEM_ESCRITAS = [
    ("a explicacao cita a marcada E outra palavra que tambem e alternativa",
     "Portugues",
     "Qual a classe da palavra 'rapidamente' na frase?",
     ["Adverbio", "Adjetivo", "Verbo", "Nome"], "Adverbio",
     "A palavra modifica o verbo, entao e um adverbio de modo."),

    ("alternativas que so diferem em palavras curtas",
     "Portugues",
     "Qual alternativa apresenta crase corretamente empregada?",
     ["Vou a escola", "Vou à escola", "Vou às escola", "Vou a as escola"], "Vou à escola",
     "A forma correta e 'Vou à escola', com a crase entre a preposicao e o artigo."),

    ("a explicacao parafraseia em vez de repetir",
     "Geografia",
     "Qual bioma brasileiro tem a maior biodiversidade?",
     ["Amazonia", "Cerrado", "Caatinga", "Pampa"], "Amazonia",
     "A floresta amazonica concentra a maior variedade de especies do pais."),

    ("alternativas com uma palavra em comum",
     "Historia",
     "Qual movimento derrubou a monarquia na Franca em 1789?",
     ["Revolucao Francesa", "Revolucao Industrial", "Revolucao Russa", "Revolucao Gloriosa"],
     "Revolucao Francesa",
     "A Revolucao Francesa poe fim ao Antigo Regime."),

    ("alternativas muito curtas (seculos)",
     "Historia",
     "Em que seculo teve inicio a Revolucao Industrial?",
     ["XVIII", "XVI", "XX", "XIX"], "XVIII",
     "O processo comeca na Inglaterra no seculo XVIII."),

    ("alternativas numericas curtas",
     "Historia",
     "Em que ano o Brasil proclamou a Republica?",
     ["1889", "1822", "1888", "1891"], "1889",
     "A Republica foi proclamada em 1889."),

    ("ingles: alternativas de duas ou tres letras",
     "Ingles",
     "Choose the correct form: She ___ happy.",
     ["is", "are", "am", "be"], "is",
     "The correct answer is is, since the subject she agrees with the verb to be."),

    ("ingles: frases que diferem so no verbo",
     "Ingles",
     "Which sentence is correct?",
     ["She is happy", "She are happy", "She am happy", "She be happy"], "She is happy",
     "The correct sentence is She is happy, since the verb agrees with the subject."),
]


@pytest.mark.parametrize(
    "rotulo, materia, pergunta, opcoes, correta, resultado",
    BEM_ESCRITAS,
    ids=[c[0][:45] for c in BEM_ESCRITAS],
)
def test_questao_bem_escrita_passa(rotulo, materia, pergunta, opcoes, correta, resultado):
    dados = questao(pergunta, opcoes, correta, resultado)

    _, valida, motivo = validar_questao_gerada(dados, materia, contexto="oraculo")

    assert valida, f"{rotulo}: recusada como {motivo!r}"


# --------------------------------------------------------------------------
# a metade que importa: contradicao continua sendo pega
# --------------------------------------------------------------------------

CONTRADIZEM = [
    ("explicacao nomeia outro movimento",
     "Historia",
     "Qual movimento valorizou a razao e criticou o absolutismo?",
     ["Renascimento", "Iluminismo", "Mercantilismo", "Feudalismo"], "Renascimento",
     "O Iluminismo valorizou a razao e criticou o absolutismo."),

    ("explicacao nomeia outra figura de linguagem",
     "Portugues",
     "Qual figura de linguagem compara sem conectivo?",
     ["Metafora", "Comparacao", "Ironia", "Eufemismo"], "Ironia",
     "A metafora compara sem usar conectivo."),

    ("explicacao nomeia outra organela",
     "Biologia",
     "Qual organela faz a fotossintese?",
     ["Cloroplasto", "Mitocondria", "Ribossomo", "Nucleo"], "Ribossomo",
     "O cloroplasto e a organela onde ocorre a fotossintese."),

    ("explicacao nomeia outro bioma",
     "Geografia",
     "Qual bioma ocupa a maior area do Brasil?",
     ["Amazonia", "Cerrado", "Caatinga", "Pampa"], "Pampa",
     "A Amazonia ocupa a maior area do territorio brasileiro."),
]


@pytest.mark.parametrize(
    "rotulo, materia, pergunta, opcoes, correta, resultado",
    CONTRADIZEM,
    ids=[c[0][:45] for c in CONTRADIZEM],
)
def test_explicacao_que_contradiz_a_marcada_e_recusada(
    rotulo, materia, pergunta, opcoes, correta, resultado
):
    dados = questao(pergunta, opcoes, correta, resultado)

    _, valida, _motivo = validar_questao_gerada(dados, materia, contexto="oraculo")

    assert not valida, f"{rotulo}: passou, e a explicacao aponta para outra alternativa"


# --------------------------------------------------------------------------
# a regra, isolada
# --------------------------------------------------------------------------


def test_sem_nenhuma_alternativa_citada_nao_e_contradicao():
    # Ausencia de evidencia nao e evidencia de erro.
    assert not _explicacao_aponta_para_outra_alternativa(
        questao("Qual bioma tem maior biodiversidade?",
                ["Amazonia", "Cerrado", "Caatinga", "Pampa"], "Amazonia",
                "O bioma equatorial umido concentra mais especies.")
    )


def test_marcada_entre_varias_citadas_nao_e_contradicao():
    assert not _explicacao_aponta_para_outra_alternativa(
        questao("Qual a classe de 'rapidamente'?",
                ["Adverbio", "Adjetivo", "Verbo", "Nome"], "Adverbio",
                "A palavra modifica o verbo, entao e um adverbio de modo.")
    )


def test_marcada_fora_das_citadas_e_contradicao():
    assert _explicacao_aponta_para_outra_alternativa(
        questao("Qual movimento valorizou a razao?",
                ["Renascimento", "Iluminismo", "Mercantilismo", "Feudalismo"], "Renascimento",
                "O Iluminismo valorizou a razao e criticou o absolutismo.")
    )


def test_sem_explicacao_nao_ha_o_que_contradizer():
    dados = questao("Qual movimento valorizou a razao?",
                    ["Renascimento", "Iluminismo", "Mercantilismo", "Feudalismo"],
                    "Renascimento", "")
    dados["explicacao"] = []

    assert not _explicacao_aponta_para_outra_alternativa(dados)


@pytest.mark.parametrize("indice", [-1, 4, 99, "x", None])
def test_indice_marcado_estranho_nao_quebra(indice):
    dados = questao("Qual movimento valorizou a razao?",
                    ["Renascimento", "Iluminismo", "Mercantilismo", "Feudalismo"],
                    "Renascimento", "O Iluminismo valorizou a razao.")
    dados["correta"] = indice

    assert _explicacao_aponta_para_outra_alternativa(dados) is False
