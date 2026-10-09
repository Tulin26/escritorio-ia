"""O dicionário de acentos não troca o verbo pelo substantivo.

Visto numa captura do TG em 17/09/2026: a IA escreveu "O uso da antítese
evidencia o contraste" -- verbo, certo -- e o aluno leu "antítese evidência o
contraste". No banco offline acentuado, "Cada tradição formula esse princípio"
virava "tradição fórmula".

As palavras de _PALAVRAS_QUE_TAMBEM_SAO_VERBO só ganham acento em texto sem
letra acentuada nenhuma, que é o texto em ASCII dos bancos, em que elas são
substantivo. E nunca com pronome pendurado ("evidencia-se").
"""

from __future__ import annotations

import pytest

from core.text_cleanup import _PALAVRAS_PT, _PALAVRAS_QUE_TAMBEM_SAO_VERBO, aplicar_acentos_pt


@pytest.mark.parametrize(
    "frase",
    [
        "O uso da antítese evidencia o contraste entre saúde e prevenção.",
        "Cada tradição formula esse princípio com suas próprias palavras.",
        "A canção referencia um poema de Drummond.",
        "A tecnologia potencia o alcance da mensagem, diz o crítico.",
        "O discurso distancia o leitor do fato narrado, segundo a crônica.",
        "O narrador experiencia a cidade como estrangeiro, sem saída.",
        "O laboratório sequencia o DNA em poucas horas.",
        "Eu calculo a área antes de comprar o piso.",
        "Eu numero as páginas do relatório à mão.",
        "Eu pratico vôlei três vezes por semana.",
        # Um acento so ja basta, e o cedilha e o maiusculo contam.
        "A força do argumento evidencia a tese.",
        "É o dado que evidencia a crise.",
    ],
)
def test_verbo_em_texto_acentuado_fica_como_a_ia_escreveu(frase):
    assert aplicar_acentos_pt(frase) == frase


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        # Banco offline, escrito sem acento: aí elas são substantivo, e muitas
        # vezes sem artigo antes.
        ("qual evidencia sustenta melhor o proximo passo", "qual evidência sustenta melhor o próximo passo"),
        ("hipotese, evidencia e conclusao", "hipótese, evidência e conclusão"),
        ("Substitua os valores na formula e confira a unidade final.", "Substitua os valores na fórmula e confira a unidade final."),
        ("Numero de alunos", "Número de alunos"),
        ("Diferenciar experiencia individual e memoria coletiva", "Diferenciar experiência individual e memória coletiva"),
        ("A sequencia depende apenas da razao.", "A sequência depende apenas da razão."),
        ("RPG - potencia eletrica", "RPG - potência elétrica"),
        ("qual e a distancia entre A e B?", "qual é a distância entre A e B?"),
        ("O calculo da area usa o ponto de referencia.", "O cálculo da área usa o ponto de referência."),
        ("Um exemplo pratico", "Um exemplo prático"),
    ],
)
def test_substantivo_em_texto_ascii_continua_ganhando_acento(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("Evidencia-se que o calculo esta certo.", "Evidencia-se que o cálculo esta certo."),
        ("Formula-la exige cuidado.", "Formula-la exige cuidado."),
        ("Distancia-o do problema.", "Distancia-o do problema."),
    ],
)
def test_pronome_pendurado_marca_o_verbo_mesmo_em_ascii(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado


def test_substantivo_composto_com_hifen_continua_ganhando_acento():
    # So pronome depois do hifen marca o verbo; "-chave" e substantivo, e
    # "-mestra" so comeca como o pronome "-me".
    assert aplicar_acentos_pt("a evidencia-chave do caso") == "a evidência-chave do caso"
    assert aplicar_acentos_pt("a formula-mestra da quimica") == "a fórmula-mestra da química"


def test_o_acento_que_conta_e_o_de_quem_escreveu():
    # O "proximo" que o proprio dicionario acentua nao torna o texto
    # "acentuado": a decisao olha o texto como chegou.
    assert aplicar_acentos_pt("o proximo calculo") == "o próximo cálculo"
    # Nem o "é" que as frases prontas poem.
    assert aplicar_acentos_pt("qual e o calculo da area?") == "qual é o cálculo da área?"


def test_maiuscula_no_comeco_segue_a_regra():
    assert aplicar_acentos_pt("Evidencia do experimento") == "Evidência do experimento"
    assert aplicar_acentos_pt("Evidencia o contraste, segundo a análise.") == "Evidencia o contraste, segundo a análise."


def test_o_plural_continua_no_dicionario():
    # "tu evidencias", "tu formulas": segunda pessoa, que nao aparece nos
    # textos do app. O plural segue acentuado em qualquer texto.
    assert aplicar_acentos_pt("As evidencias são claras.") == "As evidências são claras."
    assert aplicar_acentos_pt("As formulas estão no quadro.") == "As fórmulas estão no quadro."


def test_as_palavras_da_regra_estao_no_dicionario():
    # Uma palavra da regra que nao esta no dicionario nao seria acentuada em
    # lugar nenhum: a regra ficaria so parecendo proteger.
    assert _PALAVRAS_QUE_TAMBEM_SAO_VERBO <= set(_PALAVRAS_PT)


def test_as_palavras_da_regra_sao_as_conhecidas():
    assert _PALAVRAS_QUE_TAMBEM_SAO_VERBO == {
        "evidencia",
        "formula",
        "referencia",
        "potencia",
        "distancia",
        "experiencia",
        "sequencia",
        "calculo",
        "numero",
        "pratico",
        # Entraram em 28/09/2026 com o item 5.1 do QA de 23/09.
        "maquina",
        "indice",
        "cientifica",
    }
