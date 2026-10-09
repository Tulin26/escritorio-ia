from __future__ import annotations

import pytest

from services.ia.normalizacao import normalizar_payload_questao
from services.ia.validacao import _avaliar_expressao_numerica, validar_questao_gerada


def test_validar_questao_gerada_rejeita_quantidade_errada_de_opcoes():
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Quanto vale 2 + 2?",
            "opcoes": ["4", "5", "6"],
            "correta": 0,
            "formula": "a + b",
            "passos_resolucao": [{"conteudo": "2 + 2 = 4", "final": True}],
        },
        "Matematica",
    )

    assert valida is False
    assert motivo == "quantidade-de-opcoes-invalida"


def test_validar_questao_gerada_aceita_exatas_com_numeros_apenas_nos_passos():
    dados, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Um corpo de massa 4 kg acelera a 3 m/s^2. Qual é a força resultante?",
            "opcoes": ["12 N", "10 N", "16 N", "8 N"],
            "correta": 0,
            "formula": r"F = m \cdot a",
            "subformulas": [],
            "passos_resolucao": [
                {"conteudo": "m = 4 kg e a = 3 m/s^2."},
                {"conteudo": r"F = 4 \cdot 3 = 12 N", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "A forca resultante e o produto da massa pela aceleracao."}],
        },
        "Fisica",
        contexto="laboratorio",
    )

    assert valida is True
    assert motivo == ""
    assert dados["correta"] == 0


def test_normalizar_payload_aceita_formula_principal_e_legenda_em_dict():
    dados = normalizar_payload_questao(
        {
            "pergunta": "Qual é a força?",
            "opcoes": ["12 N", "10 N", "8 N", "6 N"],
            "correta": 0,
            "formula_principal": r"F = m \cdot a",
            "legenda_variaveis": {"F": "força resultante", "m": "massa", "a": "aceleração"},
        }
    )

    assert dados["formula"] == r"F = m \cdot a"
    assert "F: força resultante" in dados["legenda_variaveis"]


def test_validar_questao_gerada_rejeita_formula_de_bhaskara_em_questao_de_pa():
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Em uma progressão aritmética com a1 = 2, r = 3 e n = 5, qual é o termo a5?",
            "opcoes": ["23", "14", "11", "17"],
            "correta": 0,
            "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
            "subformulas": [r"\Delta = b^2 - 4ac"],
            "passos_resolucao": [
                {"conteudo": "a1 = 2, r = 3 e n = 5."},
                {"conteudo": r"a_5 = 2 + (5 - 1)\cdot 3"},
                {"conteudo": r"a_5 = 2 + 12 = 14", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "O 5º termo da progressão é 14."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is False
    assert motivo == "formula-matematica-incoerente"


def test_laboratorio_rejeita_concentracao_molar_incorreta():
    from services.ia.validacao import validar_questao_gerada

    dados = {
        "pergunta": "Dissolvem-se 20 g de NaCl em 500 mL de solucao. M = 58,44 g/mol. Qual e a concentracao molar?",
        "opcoes": ["0,34 mol/L", "0,68 mol/L", "1,16 mol/L", "0,17 mol/L"],
        "correta": 0,
        "formula": r"C = \frac{n}{V}",
        "subformulas": [],
        "passos_resolucao": [
            {"titulo": "1o Passo", "conteudo": r"n = \frac{20 g}{58,44 g/mol} = 0,342 mol"},
            {"titulo": "2o Passo", "conteudo": r"C = \frac{0,342 mol}{0,5 L} = 0,684 mol/L"},
            {"titulo": "Resultado Final", "conteudo": r"C = 0,684 mol/L, porem a resposta correta deve ser 0,34 mol/L", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "A concentracao molar e a razao entre mols de soluto e volume de solucao."}],
    }

    _payload, valido, motivo = validar_questao_gerada(dados, "Quimica", contexto="laboratorio")

    assert valido is False
    assert motivo == "concentracao-molar-invalida"


def test_validar_questao_gerada_rejeita_conta_final_errada():
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Em uma PA, com a1 = 2, razão 3 e n = 5, qual é o 5º termo?",
            "opcoes": ["23", "14", "17", "20"],
            "correta": 0,
            "formula": r"a_n = a_1 + (n-1)\cdot r",
            "subformulas": [],
            "passos_resolucao": [
                {"conteudo": "a1 = 2, r = 3 e n = 5."},
                {"conteudo": r"a_5 = 2 + (5 - 1)\cdot 3"},
                {"conteudo": r"a_5 = 2 + 12 = 23", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "O 5º termo da progressão é 23."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is False
    assert motivo == "resultado-aritmetico-invalido"


def test_validar_questao_gerada_aceita_bhaskara_com_pm_e_raiz():
    # MELHORIA: regressao para um bug visto em producao. O checador de
    # aritmetica apagava "\pm"/"\sqrt{" silenciosamente e comparava os
    # digitos restantes como se fossem um numero de verdade, rejeitando
    # respostas corretas de Bhaskara (ex: Groq gerando "-2 e -3" para
    # x^2 + 5x + 6 = 0, que e a resposta certa, sendo recusado como
    # "resultado-aritmetico-invalido").
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Determine as raízes da equação x^2 + 5x + 6 = 0",
            "opcoes": ["-2 e -3", "2 e 3", "-1 e -6", "1 e 6"],
            "correta": 0,
            "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
            "subformulas": [],
            "passos_resolucao": [
                {"conteudo": "a = 1, b = 5, c = 6."},
                {
                    "conteudo": r"x = \frac{-5 \pm \sqrt{25 - 24}}{2} = \frac{-5 \pm 1}{2}",
                },
                {"conteudo": "x = -2 e -3", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "As raízes são -2 e -3."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is True
    assert motivo == ""


def test_laboratorio_rejeita_pa_sem_alternativa_correta():
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Dada uma progressão aritmética com o primeiro termo a = 2 e a diferença comum d = 3, qual é o 5º termo da sequência?",
            "opcoes": ["11", "13", "15", "17"],
            "correta": 2,
            "formula": r"a_n = a + (n - 1)d",
            "passos_resolucao": [
                {"conteudo": "a = 2, d = 3 e n = 5."},
                {"conteudo": r"a_5 = 2 + (5 - 1)\cdot 3 = 14", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "O 5º termo da progressão é igual a 14."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is False
    assert motivo == "alternativa-correta-calculavel-invalida"


def test_laboratorio_rejeita_pa_com_termos_por_extenso_e_alternativa_errada():
    # MELHORIA: regressao para um bug visto em producao. Quando a questao
    # da dois termos quaisquer da PA em vez do primeiro termo e da razao
    # (ex: "o primeiro termo vale 7 e o quinto termo vale 27"), com a
    # posicao pedida por extenso ("qual e o decimo segundo termo"), o
    # detector de PA nao reconhecia nenhum "razao =" no texto (o aluno tem
    # que deduzir) nem posicoes em numeral, e ficava cego — deixando passar
    # uma alternativa marcada como correta que nao batia com a conta certa
    # (a_12 = 62).
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Em uma progressão aritmética, o primeiro termo vale 7 e o quinto termo vale 27. Qual é o décimo segundo termo da sequência?",
            "opcoes": ["57", "60", "65", "70"],
            "correta": 1,
            "formula": r"a_n = a_1 + (n-1) \cdot r",
            "passos_resolucao": [
                {"conteudo": "a1 = 7, a5 = 27, n = 12."},
                {"conteudo": "a12 = 7 + 11*5 = 60", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "O décimo segundo termo é 60."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is False


def test_laboratorio_aceita_pa_com_termos_por_extenso_e_alternativa_certa():
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Em uma progressão aritmética, o primeiro termo vale 7 e o quinto termo vale 27. Qual é o décimo segundo termo da sequência?",
            "opcoes": ["57", "60", "62", "70"],
            "correta": 2,
            "formula": r"a_n = a_1 + (n-1) \cdot r",
            "passos_resolucao": [
                {"conteudo": "a1 = 7, a5 = 27, n = 12."},
                {"conteudo": "a12 = 7 + 11*5 = 62", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "O décimo segundo termo é 62."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is True
    assert motivo == ""


def test_laboratorio_rejeita_trigonometria_sem_altura_correta():
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Um observador esta a 50 metros da base de um predio. O angulo de elevacao para o topo do predio e 60 graus. Calcule a altura do predio.",
            "opcoes": ["90,6 metros", "100 metros", "106,6 metros", "96,6 metros"],
            "correta": 0,
            "formula": r"h = d \cdot tan(\theta)",
            "passos_resolucao": [
                {"conteudo": "d = 50 m e theta = 60 graus."},
                {"conteudo": r"h = 50 \cdot tan(60) = 90,6 metros", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "A altura e 90,6 metros."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is False
    assert motivo == "alternativa-correta-calculavel-invalida"


def test_laboratorio_aceita_trigonometria_com_altura_correta():
    dados, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Um observador esta a 50 metros da base de um predio. O angulo de elevacao para o topo do predio e 60 graus. Calcule a altura do predio.",
            "opcoes": ["90,6 metros", "86,6 metros", "100 metros", "96,6 metros"],
            "correta": 1,
            "formula": r"h = d \cdot tan(\theta)",
            "passos_resolucao": [
                {"conteudo": "d = 50 m e theta = 60 graus."},
                {"conteudo": r"h = 50 \cdot tan(60) = 86,6 metros", "final": True},
            ],
            "explicacao": [{"tipo": "resultado", "conteudo": "A altura e aproximadamente 86,6 metros."}],
        },
        "Matematica",
        contexto="laboratorio",
    )

    assert valida is True
    assert motivo == ""
    assert dados["correta"] == 1


def test_oraculo_rejeita_resposta_textual_incoerente_com_explicacao():
    _, valida, motivo = validar_questao_gerada(
        {
            "pergunta": "Qual movimento valorizou a razão e criticou o absolutismo?",
            "opcoes": ["Renascimento", "Iluminismo", "Mercantilismo", "Feudalismo"],
            "correta": 0,
            "explicacao": [
                {"tipo": "texto", "conteudo": "O Iluminismo valorizou a razão e criticou o absolutismo."},
                {"tipo": "resultado", "conteudo": "Resposta: Iluminismo."},
            ],
        },
        "Historia",
        contexto="oraculo",
    )

    assert valida is False
    assert motivo == "alternativa-correta-inconsistente"


def test_avaliar_expressao_com_notacao_cientifica_e_times():
    # MELHORIA: regressao para um bug visto ao auditar outras materias.
    # "\times" (usado em notacao cientifica, ex: numero de Avogadro em
    # Quimica/Fisica) nao era convertido para "*", entao era apagado em
    # silencio e colava os numeros vizinhos, virando uma conta absurda
    # (6,02 \times 10^23 virava 6.021 elevado a 23 em vez de 6.02 * 10^23).
    assert _avaliar_expressao_numerica(r"6,02 \times 10^{23}") == 6.02e23
    assert _avaliar_expressao_numerica(r"3 \times 10^-3") == 0.003


def test_equacao_2o_grau_com_alternativa_errada_e_rejeitada():
    # MELHORIA: regressao para um bug visto em producao. A IA calculou certo
    # nos passos (raizes 1 e -5/3 para 3x^2+2x-5=0), mas a alternativa
    # marcada como correta era outro par de numeros que nao correspondia a
    # nenhuma raiz real (nem sequer aproximada). Nada detectava isso porque
    # so havia checador de valor esperado pra progressao aritmetica e
    # trigonometria, nao para equacao do 2o grau.
    dados = {
        "pergunta": "Resolva a equação do 2º grau 3x^2 + 2x - 5 = 0 encontrando os valores de x.",
        "opcoes": ["(0.5, -2)", "(2, -1)", "(-1, 0.6)", "(-0.5, 1.5)"],
        "correta": 2,
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [r"\Delta = b^2 - 4ac"],
        "passos_resolucao": [
            {"conteudo": "a = 3, b = 2, c = -5"},
            {"conteudo": r"\Delta = 2^2 - 4 \cdot 3 \cdot (-5) = 4 + 60 = 64"},
            {"conteudo": r"x = \frac{-2 \pm \sqrt{64}}{2 \cdot 3} = \frac{-2 \pm 8}{6}"},
            {"conteudo": r"x_1 = 1, x_2 = -5/3", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "As raízes são 1 e -5/3."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Matematica", contexto="laboratorio")
    assert valida is False
    assert motivo == "alternativa-correta-calculavel-invalida"


def test_equacao_2o_grau_com_alternativa_certa_e_aceita():
    dados = {
        "pergunta": "Resolva a equação do 2º grau 3x^2 + 2x - 5 = 0 encontrando os valores de x.",
        "opcoes": ["(0.5, -2)", "(2, -1)", "(1, -1.67)", "(-0.5, 1.5)"],
        "correta": 2,
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [r"\Delta = b^2 - 4ac"],
        "passos_resolucao": [
            {"conteudo": "a = 3, b = 2, c = -5"},
            {"conteudo": r"\Delta = 2^2 - 4 \cdot 3 \cdot (-5) = 4 + 60 = 64"},
            {"conteudo": r"x = \frac{-2 \pm \sqrt{64}}{2 \cdot 3} = \frac{-2 \pm 8}{6}"},
            {"conteudo": r"x_1 = 1, x_2 = -1.67", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "As raízes são 1 e -1,67."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Matematica", contexto="laboratorio")
    assert valida is True
    assert motivo == ""


def test_checagem_geral_pega_resposta_errada_em_tipo_sem_detector_especifico():
    # MELHORIA: generaliza o conserto do bug do Bhaskara pra qualquer tipo de
    # questao de exatas, nao so equacao do 2o grau. Este caso e de
    # porcentagem/desconto, um tipo que NAO tem nenhum detector especifico
    # (so PA, trigonometria e equacao do 2o grau tem). Antes desta checagem
    # geral, uma resposta calculada certa nos passos mas com a alternativa
    # marcada errada passaria batido aqui.
    dados = {
        "pergunta": "Um produto de R$ 200 tem desconto de 15%. Qual o valor do desconto?",
        "opcoes": ["R$ 45", "R$ 15", "R$ 185", "R$ 60"],
        "correta": 0,
        "formula": "desconto = valor * percentual / 100",
        "passos_resolucao": [
            {"conteudo": "desconto = 200 * 15 / 100 = 30", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "O desconto é de R$ 30."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Matematica", contexto="laboratorio")
    assert valida is False
    assert motivo == "alternativa-correta-diverge-do-resultado-final"


def test_checagem_geral_aceita_resposta_correta_em_tipo_sem_detector_especifico():
    dados = {
        "pergunta": "Um produto de R$ 200 tem desconto de 15%. Qual o valor do desconto?",
        "opcoes": ["R$ 45", "R$ 15", "R$ 185", "R$ 30"],
        "correta": 3,
        "formula": "desconto = valor * percentual / 100",
        "passos_resolucao": [
            {"conteudo": "desconto = 200 * 15 / 100 = 30", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "O desconto é de R$ 30."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Matematica", contexto="laboratorio")
    assert valida is True


def test_resposta_diverge_do_resultado_final_ignora_bloco_explicacao_sem_numero():
    # MELHORIA: bug visto ao vivo com Groq no Laboratorio de Exatas -- o
    # bloco "explicacao" tipo "resultado" as vezes so descreve o resultado
    # em palavras, sem numero nenhum (ex: "Forca resultante"), vindo DEPOIS
    # do passo final numerico na ordem de coleta. A checagem antiga olhava
    # so o ULTIMO candidato da lista (esse texto sem numero) e concluia que
    # nao havia nada pra comparar, deixando passar uma alternativa marcada
    # que nao batia com a conta.
    dados = {
        "pergunta": "Um objeto de 10 kg esta submetido a duas forcas: uma de 20 N para cima e outra de 15 N para baixo. Qual e a forca resultante?",
        "opcoes": ["25 N", "35 N", "5 N", "-5 N"],
        "correta": 0,
        "formula": "F_r = F_1 + F_2",
        "passos_resolucao": [
            {"conteudo": "20 N - 15 N", "final": False},
            {"conteudo": "5 N", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "A forca resultante sobre o corpo, em modulo"}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Fisica", contexto="laboratorio")
    assert valida is False
    assert motivo == "alternativa-correta-diverge-do-resultado-final"


def test_rejeita_passo_final_que_nao_bate_com_conta_do_passo_anterior():
    # MELHORIA: reproduz ao vivo com Groq -- os passos vem como expressoes
    # soltas, sem "=" ligando uma linha a outra ("20 N - 15 N - 98 N" numa
    # linha, "-98 N + 5 N" na seguinte), entao _resultado_aritmetico_incorreto
    # (que so compara os lados de um "=" na MESMA linha) nunca disparava. A
    # conta real da 20 - 15 - 98 = -93, nao 5 N como o passo final afirmava.
    dados = {
        "pergunta": "Um objeto de 10 kg esta submetido a duas forcas: uma de 20 N para cima e outra de 15 N para baixo, alem do peso. Qual e a forca resultante?",
        "opcoes": ["25 N", "35 N", "5 N", "-5 N"],
        "correta": 2,
        "formula": "F_r = F_1 + F_2 - m*g",
        "passos_resolucao": [
            {"conteudo": "20 N + (-15 N) - 10 kg * 9,8 m/s^2", "final": False},
            {"conteudo": "20 N - 15 N - 98 N", "final": False},
            {"conteudo": "-98 N + 5 N", "final": False},
            {"conteudo": "5 N", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "A forca resultante soma as forcas e subtrai o peso do corpo."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Fisica", contexto="laboratorio")
    assert valida is False
    assert motivo == "passo-final-diverge-do-calculo-anterior"


def test_aceita_passo_final_consistente_com_conta_sem_sinal_de_igual():
    dados = {
        "pergunta": "Um objeto de 5 kg esta sobre uma mesa e sofre duas forcas: uma de 10 N para a esquerda e outra de 8 N para a direita. Qual a forca resultante?",
        "opcoes": ["6 N", "4 N", "-2 N", "2 N"],
        "correta": 2,
        "formula": "F_r = F_1 + F_2",
        "passos_resolucao": [
            {"conteudo": "-10 N + 8 N", "final": False},
            {"conteudo": "-2 N", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "A forca resultante e a soma vetorial das duas forcas opostas."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Fisica", contexto="laboratorio")
    assert valida is True
    assert motivo == ""


def test_questao_conceitual_de_exatas_correta_nao_e_rejeitada_por_falta_de_numero():
    # MELHORIA: bug visto ao vivo em producao (reproduzido 2x seguidas com
    # Mistral) -- _ajustar_indice_correto tratava "a heuristica numerica
    # nao achou nada pra comparar" (indice_inferido None) como se fosse
    # "achou uma inconsistencia", rejeitando questoes CONCEITUAIS de exatas
    # (sem numero, ex: "como o juro simples e calculado") mesmo quando a IA
    # acertou e a explicacao bate exatamente com a opcao marcada. O branch
    # "geral" (materias nao-exatas) nunca teve esse problema -- so falha
    # quando ACHA um indice divergente, nao quando simplesmente nao
    # consegue confirmar nada.
    dados = {
        "pergunta": "Nos juros simples, o cálculo do juro em cada período é feito:",
        "opcoes": [
            "sempre sobre o valor inicial (principal), sem incidir sobre juros já acumulados",
            "de forma aleatória, sem nenhuma fórmula fixa",
            "apenas uma única vez em toda a história do empréstimo",
            "sempre sobre o montante acumulado, incluindo os juros anteriores",
        ],
        "correta": 0,
        "formula": "J = C * i * t",
        "passos_resolucao": [
            {
                "titulo": "Etapa 1",
                "conteudo": "No juro simples, o valor do juro é sempre calculado sobre o capital inicial, o que faz o crescimento ser linear ao longo do tempo.",
                "final": False,
            },
            {
                "titulo": "Resultado Final",
                "conteudo": "Isso é diferente do juro composto, que incide também sobre os juros já acumulados.",
                "final": True,
            },
        ],
        "explicacao": [
            {"tipo": "bold", "conteudo": "Juros simples"},
            {"tipo": "texto", "conteudo": "No juro simples, o valor do juro é sempre calculado sobre o capital inicial."},
            {"tipo": "resultado", "conteudo": "Isso é diferente do juro composto, que incide também sobre os juros já acumulados."},
        ],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Matematica", contexto="rpg")
    assert valida is True
    assert motivo == ""


def test_variavel_com_indice_no_passo_nao_gera_falso_positivo():
    # Garante que "a_5" (variavel com indice) nao vira um digito fantasma
    # que se cola no proximo numero da conta (ver _remover_variaveis_com_indice).
    dados = {
        "pergunta": "Em uma progressão aritmética com a1 = 2, r = 3 e n = 5, qual é o termo a5?",
        "opcoes": ["23", "14", "11", "17"],
        "correta": 1,
        "formula": "a_n = a_1 + (n-1) * r",
        "passos_resolucao": [
            {"conteudo": "a1 = 2, r = 3 e n = 5.", "final": False},
            {"conteudo": r"a_5 = 2 + (5 - 1)\cdot 3", "final": False},
            {"conteudo": r"a_5 = 2 + 12 = 14", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "O termo pedido se obtem somando quatro razoes ao primeiro termo da sequencia."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Matematica", contexto="laboratorio")
    assert valida is True
    assert motivo == ""


def test_passo_com_igual_interno_nao_gera_numero_fantasma():
    # MELHORIA: achado na revisao de codigo (dois agentes independentes) --
    # quando o penultimo passo ja tem "=" dentro dele (formato comum:
    # "conta = resultado"), _avaliar_expressao_numerica tratava a linha
    # inteira como uma unica expressao, colando os digitos dos dois lados
    # do "=" (20-15-98-93 virava -186 em vez de -93), rejeitando uma
    # questao correta como se o passo final divergisse.
    from services.ia.validacao import _valor_e_operador_do_passo

    valor, tem_operador = _valor_e_operador_do_passo("20 N - 15 N - 98 N = -93 N")
    assert tem_operador is True
    assert valor == -93.0

    dados = {
        "pergunta": "Um corpo de 10 kg sofre forcas de 20 N e 15 N, alem do peso de 98 N. Qual a forca resultante final?",
        "opcoes": ["25 N", "35 N", "-93 N", "-5 N"],
        "correta": 2,
        "formula": "F_r = F_1 - F_2 - P",
        "passos_resolucao": [
            {"conteudo": "F_r = 20 N - 15 N - 98 N = -93 N", "final": False},
            {"conteudo": "-93 N", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "A forca resultante subtrai as forcas contrarias e o peso do corpo."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Fisica", contexto="laboratorio")
    assert valida is True
    assert motivo == ""


def test_palavras_com_tan_nao_desligam_checagem_de_passo_final():
    # MELHORIA: achado na revisao -- a checagem antiga de "pular passo com
    # trigonometria" usava substring solta ("tan" in texto), que tambem
    # casava com "distancia", "constante", "instante" (palavras comuns de
    # Fisica sem nenhuma relacao com trigonometria) e desligava a checagem
    # nesses casos, deixando passar um passo final que realmente diverge.
    dados = {
        "pergunta": "Um carro percorre uma distancia numa velocidade constante. Qual a velocidade final calculada?",
        "opcoes": ["10 m/s", "20 m/s", "30 m/s", "40 m/s"],
        "correta": 1,
        "formula": "v = d / t",
        "passos_resolucao": [
            {"conteudo": "a distancia e constante: v = 100 / 10 = 10", "final": False},
            {"conteudo": "20 m/s", "final": True},
        ],
        "explicacao": [{"tipo": "resultado", "conteudo": "A velocidade e a razao entre a distancia percorrida e o tempo gasto."}],
    }
    _, valida, motivo = validar_questao_gerada(dados, "Fisica", contexto="laboratorio")
    assert valida is False
    assert motivo == "passo-final-diverge-do-calculo-anterior"


def test_formula_molecular_de_quimica_nao_e_apagada_como_variavel_indexada():
    # MELHORIA: achado na revisao -- o regex de "variavel com indice"
    # original casava tambem com formulas moleculares tipo O2/H2/N2 (letra
    # + digito sem "_"), apagando notacao quimica valida. Exige "_" de
    # proposito (so casa "a_5", "F_1" etc.) pra nao confundir com formulas.
    from services.ia.validacao import _remover_variaveis_com_indice

    texto = "2 mols de O2 reagem com H2 formando agua"
    assert _remover_variaveis_com_indice(texto) == texto


@pytest.mark.parametrize(
    "opcoes",
    [
        ["A", "B", "C", "D"],
        ["A)", "B)", "C)", "D)"],
        ["a.", "b.", "c.", "d."],
        ["alternativa A", "alternativa B", "alternativa C", "alternativa D"],
    ],
)
def test_rejeita_alternativa_que_e_so_rotulo(opcoes):
    # MELHORIA: visto em producao no RPG -- "Qual solido geometrico possui
    # todas as faces quadradas congruentes...?" chegou ao aluno com as quatro
    # opcoes sendo "A", "B", "C" e "D". A pergunta e a explicacao estavam
    # certas; so as alternativas perderam o texto, e nao havia como
    # responder a nao ser chutando.
    from services.ia.validacao import _validar_estrutura_basica_questao

    ok, motivo = _validar_estrutura_basica_questao(
        {"pergunta": "Qual solido tem seis faces quadradas congruentes?", "opcoes": opcoes, "correta": 0}
    )

    assert ok is False
    assert motivo == "opcoes-sao-apenas-rotulos"


@pytest.mark.parametrize(
    ("opcoes", "assunto"),
    [
        (["C", "O", "N", "H"], "simbolos de elementos quimicos"),
        (["A", "T", "C", "G"], "bases do DNA"),
        (["A", "B", "C", "E"], "sequencia quebrada, nao e rotulo"),
        (["x", "y", "z", "w"], "variaveis"),
    ],
)
def test_letra_solta_legitima_continua_passando(opcoes, assunto):
    # A regra exige a sequencia COMPLETA a partir de "a". Barrar qualquer
    # letra solta reprovaria quimica e biologia, onde a resposta e mesmo
    # uma letra.
    from services.ia.validacao import _opcoes_sao_apenas_rotulos

    assert _opcoes_sao_apenas_rotulos(opcoes) is False, assunto
