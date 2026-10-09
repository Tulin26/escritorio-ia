"""Alternativa só com número ganha a unidade que a própria questão dá.

A regra de unidade do Laboratório cobra que a alternativa de Física ou
Química carregue unidade. Ela recusava questões CERTAS em que a unidade
estava na própria questão, e não na alternativa:

  - 15/09/2026 (Render, teste real): "qual a resistência, em ohms?" com
    "2 / 3 / 4 / 6"; "potência, em watts" com "200 / 40 / 20 / 100";
    "em g/L", "(em mol)"... Foram 6 de 6 recusas reais do dia.
  - 30/09/2026 (geração das telas do TCC): o Groq mandou "20 / 25 / 30 / 35"
    com o resultado "s = 25 m". Três de três recusas por unidade.

A unidade sai do resultado -- o bloco "resultado" da explicação ou o passo
final, logo depois do número da resposta certa -- e, sem ela, do "em ..." da
pergunta. Sem unidade em lugar nenhum, nada muda e a recusa continua.

Medido antes de ligar (02/10/2026), contra o validador do HEAD: as 9 questões
acima passam; as 3 erradas conhecidas e as recusas certas do mesmo dia
continuam recusadas; das 2.640 do banco e das 108 de alunos, nenhuma mudou
por causa da unidade.
"""

from __future__ import annotations

import contextlib
import copy
import io

import pytest

import services.calculo_service as calc
from services.ia.normalizacao import normalizar_payload_questao
from services.ia.validacao import _completar_unidade_nas_alternativas, validar_questao_gerada


def questao(pergunta, opcoes, correta, formula, passos, resultado):
    return {
        "enigma": "Enigma",
        "pergunta": pergunta,
        "opcoes": list(opcoes),
        "correta": correta,
        "formula": formula,
        "subformulas": [],
        "legenda_variaveis": "",
        "explicacao": [
            {"tipo": "texto", "conteudo": "Aplicam-se os dados do enunciado na fórmula e faz-se a conta passo a passo."},
            {"tipo": "resultado", "conteudo": resultado},
        ],
        "passos_resolucao": [
            {"titulo": f"{i}º Passo", "conteudo": conteudo, "final": i == len(passos)}
            for i, conteudo in enumerate(passos, 1)
        ],
    }


def no_app(dados, materia):
    """O que o aluno veria: validação e a checagem extra do calculo_service."""
    with contextlib.redirect_stdout(io.StringIO()):
        payload, aceita, motivo = validar_questao_gerada(copy.deepcopy(dados), materia, "laboratorio")
        if not aceita:
            return motivo, None
        questao_final = normalizar_payload_questao(payload)
        if not calc._desafio_parece_calculo_laboratorio(copy.deepcopy(questao_final), materia):
            return "checagem-extra", None
    return "aceita", questao_final["opcoes"]


# O JSON da recusa de 30/09/2026, como o Groq mandou.
MUV_30_09 = questao(
    "Um carro parte do repouso (v₀ = 0 m/s) e acelera uniformemente com a = 2,0 m/s² durante t = 5,0 s. "
    "Qual o deslocamento percorrido?",
    ["20", "25", "30", "35"], 1, r"s = v_{0} t + \frac{1}{2} a t^{2}",
    ["v_{0}=0, a=2.0, t=5.0", r"\frac{1}{2} a t^{2}=\frac{1}{2}\cdot2.0\cdot5.0^{2}=25",
     r"s=0\cdot5.0+25=25", r"s=25\;\text{m}"],
    "s = 25 m",
)


def test_o_caso_de_30_09_chega_ao_aluno_com_metros():
    assert no_app(MUV_30_09, "Fisica") == ("aceita", ["20 m", "25 m", "30 m", "35 m"])


@pytest.mark.parametrize(
    ("materia", "dados", "esperadas"),
    [
        pytest.param("Fisica", questao(
            "Um resistor ligado a 12 V é percorrido por 3 A. Qual a resistência, em ohms?",
            ["2", "3", "4", "6"], 2, r"R = \frac{V}{I}", ["V = 12, I = 3", r"R = \frac{12}{3} = 4", "R = 4"], "R = 4",
        ), ["2 Ω", "3 Ω", "4 Ω", "6 Ω"], id="em-ohms-por-extenso"),
        pytest.param("Fisica", questao(
            "Um resistor de 10 ohms é ligado a 20 volts. Qual a potência, em watts?",
            ["200", "40", "20", "100"], 1, r"P = \frac{V^2}{R}",
            ["V = 20, R = 10", r"P = \frac{20^2}{10} = \frac{400}{10} = 40", "P = 40"], "P = 40",
        ), ["200 W", "40 W", "20 W", "100 W"], id="em-watts"),
        pytest.param("Quimica", questao(
            "Dissolvem-se 5,85 g de NaCl em água até 250 mL de solução. Qual a concentração, em g/L?",
            ["23,4", "5,85", "11,7", "46,8"], 0, r"C = \frac{m}{V}",
            ["m = 5,85, V = 0,250", r"C = \frac{5,85}{0,250} = 23,4", "C = 23,4"], "C = 23,4",
        ), ["23,4 g/L", "5,85 g/L", "11,7 g/L", "46,8 g/L"], id="em-g-por-L"),
        pytest.param("Quimica", questao(
            "Quantos mols de NaOH há em 80 g da substância (em mol)? Massa molar 40 g/mol.",
            ["2", "1", "4", "0,5"], 0, r"n = \frac{m}{M}", ["m = 80, M = 40", r"n = \frac{80}{40} = 2", "n = 2"], "n = 2",
        ), ["2 mol", "1 mol", "4 mol", "0,5 mol"], id="entre-parenteses"),
        pytest.param("Fisica", questao(
            "Um resistor de 30 Ω é ligado a 120 V. Qual a potência dissipada?",
            ["480", "360", "240", "600"], 0, r"P = \frac{V^2}{R}",
            ["V = 120, R = 30", r"P = \frac{120^2}{30} = \frac{14400}{30} = 480", "P = 480 W"], "P = 480 W",
        ), ["480 W", "360 W", "240 W", "600 W"], id="so-no-resultado"),
    ],
)
def test_as_recusas_reais_de_15_09_passam_com_a_unidade_escrita(materia, dados, esperadas):
    assert no_app(dados, materia) == ("aceita", esperadas)


def test_sem_unidade_em_lugar_nenhum_a_recusa_continua():
    dados = questao(
        "Um carro parte do repouso com a = 2,0 m/s² durante 5,0 s. Qual o deslocamento percorrido?",
        ["20", "25", "30", "35"], 1, r"s = \frac{1}{2} a t^{2}",
        ["a = 2.0, t = 5.0", r"s = \frac{1}{2}\cdot2.0\cdot5.0^{2} = 25", "s = 25"], "s = 25",
    )

    assert no_app(dados, "Fisica") == ("laboratorio-sem-calculo", None)


def test_a_unidade_e_a_do_numero_da_resposta_e_nao_a_primeira_do_texto():
    # "40 mL" vem antes no resultado; a resposta e 0,01 -- e o que vem depois
    # DELA e "mol".
    dados = questao(
        "Quantos mols de soluto há em 40 mL de solução a 0,250 mol/L?",
        ["0,01", "0,1", "0,025", "1"], 0, r"n = C \cdot V",
        ["C = 0,250, V = 0,040", r"n = 0,250 \cdot 0,040 = 0,01"], "Em 40 mL de solução, n = 0,01 mol",
    )

    assert _completar_unidade_nas_alternativas(dados, "Quimica")["opcoes"] == ["0,01 mol", "0,1 mol", "0,025 mol", "1 mol"]


def test_a_unidade_tambem_vem_do_passo_final():
    # A explicacao fechou sem unidade; o passo marcado como final tem.
    dados = questao(
        "Um carro parte do repouso com a = 2,0 m/s² durante 5,0 s. Qual o deslocamento percorrido?",
        ["20", "25", "30", "35"], 1, r"s = \frac{1}{2} a t^{2}",
        ["a = 2.0, t = 5.0", r"s = \frac{1}{2}\cdot2.0\cdot5.0^{2} = 25", r"s = 25\;\text{m}"], "s = 25",
    )

    assert _completar_unidade_nas_alternativas(dados, "Fisica")["opcoes"] == ["20 m", "25 m", "30 m", "35 m"]


def test_porcentagem_cola_no_numero():
    dados = questao(
        "Uma reação teórica rende 40 g e a real rende 36 g. Qual o rendimento?",
        ["90", "80", "75", "95"], 0, r"R = \frac{m_{real}}{m_{teorica}} \cdot 100",
        ["m_real = 36, m_teorica = 40", r"R = \frac{36}{40} \cdot 100 = 90"], "R = 90 %",
    )

    assert _completar_unidade_nas_alternativas(dados, "Quimica")["opcoes"] == ["90%", "80%", "75%", "95%"]


@pytest.mark.parametrize(
    ("materia", "opcoes"),
    [
        ("Fisica", ["20 m", "25", "30", "35"]),        # ja tem unidade em uma: nao mexe
        ("Fisica", ["v = 10 m/s", "v = 8", "v = 12", "v = 14"]),  # nao e numero puro
        ("Matematica", ["20", "25", "30", "35"]),       # Matematica nao cobra unidade
    ],
)
def test_so_mexe_quando_todas_sao_numero_puro_de_fisica_ou_quimica(materia, opcoes):
    dados = {**MUV_30_09, "opcoes": opcoes}

    assert _completar_unidade_nas_alternativas(dados, materia)["opcoes"] == opcoes


def test_em_que_nao_e_unidade_nao_conta():
    dados = questao(
        "Em um circuito, em série, há um resistor de 6 Ω ligado a 12 V. Qual a corrente?",
        ["2", "3", "4", "6"], 0, r"I = \frac{V}{R}", ["V = 12, R = 6", r"I = \frac{12}{6} = 2", "I = 2"], "I = 2",
    )

    assert _completar_unidade_nas_alternativas(dados, "Fisica")["opcoes"] == ["2", "3", "4", "6"]
