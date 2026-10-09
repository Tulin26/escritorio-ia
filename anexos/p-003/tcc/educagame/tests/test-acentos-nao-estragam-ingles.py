"""O corretor de acentos é de português e rodava em cima do inglês.

MELHORIA: `aplicar_acentos_pt` conserta o que a IA e o banco offline escrevem
em ASCII. Duas entradas legítimas em português são palavra comum em inglês:

    "ate"  -> "até"     mas *ate* é o passado de *eat*
    "area" -> "área"    mas *area* é a mesma palavra em inglês

`services/ia/normalizacao.py` já tomava esse cuidado — todo `aplicar_acentos_pt`
lá está sob `if not modo_ingles`. Só que a camada de apresentação do Flask
refazia a correção sem saber a matéria: `texto_explicacao`
(`web/routes/flask_helpers_fla.py`) chama a função em cima do que o serviço
tinha acabado de proteger.

Medido de ponta a ponta, numa questão de *simple past*:

    servico:  The simple past of "eat" is "ate". She ate lunch...
    tela:     The simple past of "eat" is "até". She até lunch...

A explicação da resposta certa contradizia a resposta certa — e num modo em
que **a grafia é a lição**.

Passar a matéria pelas seis rotas seria remendar chamada por chamada. O
reconhecimento de idioma mora na própria função, então protege todas de uma
vez, inclusive as que não têm como saber qual é a matéria.
"""

from __future__ import annotations

import pytest

from core.text_cleanup import _PALAVRAS_PT, aplicar_acentos_pt, texto_parece_ingles
from web.routes.flask_helpers_fla import texto_explicacao

# ====================== O CASO QUE MOTIVOU ======================


def test_a_explicacao_de_ingles_chega_intacta_na_tela():
    explicacao = [
        {
            "tipo": "texto",
            "conteudo": 'The simple past of "eat" is "ate". She ate lunch at school in the area near the library.',
        }
    ]

    saida = texto_explicacao(explicacao)

    assert "até" not in saida, 'trocou "ate" (passado de eat) por "até"'
    assert "área" not in saida, 'trocou "area" por "área" num texto em ingles'
    assert 'is "ate"' in saida


def test_as_duas_palavras_do_problema_continuam_no_dicionario():
    # A correção NÃO foi tirar "ate" e "area" da lista -- isso deixaria de
    # acentuar dois termos comuns em Matemática e Física. Quem resolve é o
    # reconhecimento de idioma; se alguém "simplificar" removendo as
    # entradas, este teste avisa que o remédio virou outro.
    assert _PALAVRAS_PT["ate"] == "até"
    assert _PALAVRAS_PT["area"] == "área"


# ====================== RECONHECER O IDIOMA ======================

EM_INGLES = [
    "She ate lunch at school yesterday.",
    "Choose the correct option: he ate / he eated / he eaten",
    "What does the word area mean in this context?",
    "The simple past of the verb is used for finished actions.",
    "Read the text and answer the question below.",
    "Which alternative is correct according to the passage?",
    "In a digital genre like a social media post, a hashtag mainly functions to:",
]

EM_PORTUGUES = [
    "Qual e a area do triangulo retangulo?",
    "Uma familia fara uma viagem de ida e volta de 240 km em cada trecho.",
    "A distancia total e 240 km de ida mais 240 km de volta.",
    "O aluno deve calcular a area e o perimetro da figura plana.",
    "Nao ha dados suficientes para essa conclusao.",
    "as portas so reconhecem evidencias, nao aparencias",
    "Selo da Memoria",
    "Acertou 10 questoes seguidas sem errar",
    "Codigo incorreto. Peca o codigo da escola ao seu professor.",
    "O enunciado exige apenas memorizacao, sem analise.",
    "planejamento e logica",
    "Descer ate uma memoria instavel para recuperar uma pista perdida.",
]


@pytest.mark.parametrize("texto", EM_INGLES)
def test_reconhece_o_ingles(texto):
    assert texto_parece_ingles(texto), texto


@pytest.mark.parametrize("texto", EM_PORTUGUES)
def test_nao_confunde_portugues_com_ingles(texto):
    # O falso positivo aqui é o caro: uma frase em português tratada como
    # inglês para de ser acentuada, e o problema original volta calado.
    assert not texto_parece_ingles(texto), texto


@pytest.mark.parametrize("texto", EM_PORTUGUES)
def test_o_portugues_continua_sendo_acentuado(texto):
    # A metade que não pode se perder: proteger o inglês não vale nada se
    # desligar a correção do português junto.
    assert aplicar_acentos_pt(texto) != texto, texto


@pytest.mark.parametrize("texto", EM_INGLES)
def test_o_ingles_sai_como_entrou(texto):
    assert aplicar_acentos_pt(texto) == texto, texto


# ====================== BORDAS ======================


def test_texto_curto_demais_nao_e_chutado_como_ingles():
    # Alternativa de uma palavra não dá sinal nenhum de idioma. Nesses casos
    # quem protege é o modo_ingles do serviço, que enxerga a questão inteira
    # (services/ia/normalizacao.py).
    assert not texto_parece_ingles("ate")
    assert not texto_parece_ingles("area")
    assert not texto_parece_ingles("")
    assert not texto_parece_ingles(None)


def test_uma_palavra_inglesa_solta_no_meio_do_portugues_nao_desliga_a_correcao():
    # "the" aparece em nome próprio e citação. Um marcador só não pode
    # desligar a acentuação da frase inteira.
    texto = "A banda The Beatles mudou a musica popular e a industria fonografica."

    assert not texto_parece_ingles(texto)
    assert "música" in aplicar_acentos_pt(texto)


def test_mojibake_e_consertado_mesmo_em_ingles():
    # Troca de mojibake é conserto de codificação, não de idioma: se o texto
    # chegou quebrado, chegou quebrado nas duas línguas.
    from core.text_cleanup import _MOJIBAKE

    bruto, correto = next(iter(_MOJIBAKE.items()))
    frase = f"The answer is {bruto} and that is what the text says."

    assert correto in aplicar_acentos_pt(frase)
