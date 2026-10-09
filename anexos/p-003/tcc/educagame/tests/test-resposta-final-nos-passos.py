"""A resposta da alternativa correta tem de aparecer em algum passo.

Visto no Laboratório em 11/09/2026 -- desconto de 15% e imposto de 8% sobre
R$ 250,00, alternativa correta 229,5:

    1º Passo:  P_0 = 250, d = 0,15, t = 0,08
    2º Passo:  P_d = 250 \\times 0,85 = 212,5
               <- e acabou: o imposto nunca foi aplicado

A regra nasceu como OBSERVAÇÃO (93431e9, 13/09/2026): registrava no log e não
recusava. Medida em 2 de 13 resoluções reais da IA, com 0 falso positivo --
pouco para recusar questão. Recusa desde 02/10/2026, com o "sim" do usuário:
os casos reais registrados eram todos resolução incompleta (o desconto, e um
MUV de 30/09 cujo único passo listava os dados), e das 2.640 questões do
banco e das 108 de alunos nenhuma outra foi marcada.
"""

from __future__ import annotations

import pytest

from services.ia.validacao import (
    _numeros_com_casas,
    _resposta_final_fora_dos_passos,
    observar_questao_gerada,
    validar_questao_gerada,
)

# A questão inteira do log de 11/09/2026, como chegou ao aluno.
DESCONTO = {
    "enigma": "O preço troca de roupa duas vezes antes de chegar ao caixa.",
    "pergunta": (
        "Um produto custa R$ 250,00. Recebe 15% de desconto e, sobre o preço com "
        "desconto, incide um imposto de 8%. Qual o preço final?"
    ),
    "opcoes": ["237,0", "240,0", "225,0", "229,5"],
    "correta": 3,
    "formula": "P_f = P_0 (1 - d)(1 + t)",
    "subformulas": [],
    "legenda_variaveis": "P_0 = preço original; d = desconto (decimal); t = imposto (decimal); P_f = preço final",
    "explicacao": [
        {"tipo": "bold", "conteudo": "Cálculo do preço final"},
        {"tipo": "texto", "conteudo": "Aplica-se primeiro o desconto e depois o imposto sobre o preço já descontado."},
        {"tipo": "resultado", "conteudo": "Preço final = R$ 229,5"},
    ],
    "passos_resolucao": [
        {"titulo": "1º Passo", "conteudo": "P_0 = 250, d = 0,15, t = 0,08"},
        {"titulo": "2º Passo", "conteudo": "P_d = 250 \\times 0,85 = 212,5"},
    ],
}


def _questao(resposta: str, *conteudos: str, titulos: list[str] | None = None) -> dict:
    titulos = titulos or [f"{i}º Passo" for i in range(1, len(conteudos) + 1)]
    return {
        "opcoes": [resposta, "outra 1", "outra 2", "outra 3"],
        "correta": 0,
        "passos_resolucao": [{"titulo": t, "conteudo": c} for t, c in zip(titulos, conteudos)],
    }


# ====================== OS CASOS REAIS ======================


def test_pega_a_resolucao_do_desconto_que_para_no_meio():
    """Copiado do log de 11/09/2026."""
    desconto = _questao("229,5", "P_0 = 250, d = 0,15, t = 0,08", "P_d = 250 \\times 0,85 = 212,5")

    assert _resposta_final_fora_dos_passos(desconto)


@pytest.mark.parametrize(
    "resposta, passos",
    [
        # As outras três questões da IA daqueles mesmos logs, todas certas.
        ("25 m", ["a = 15, b = 20", "c = \\sqrt{15^2 + 20^2} = \\sqrt{225 + 400} = \\sqrt{625}", "c = 25"]),
        ("21,0", ["d = 30,0, \\theta = 35^{\\circ}", "\\tan(35^{\\circ}) = 0,7002", "h = 30,0 \\cdot 0,7002", "h = 21,0"]),
        ("W = 160 J, P = 40 W", ["O trabalho é o produto da força pela distância.", "W = 160 J, P = 40 W"]),
    ],
)
def test_nao_marca_as_resolucoes_reais_que_estavam_certas(resposta, passos):
    assert not _resposta_final_fora_dos_passos(_questao(resposta, *passos))


# ====================== AS FORMAS DE ESCREVER O MESMO NÚMERO ======================


@pytest.mark.parametrize(
    "resposta, ultimo_passo",
    [
        ("21,0 m", "h = 21,006"),            # arredondado na alternativa
        ("21 m", "h = 20,6"),                # inteiro aceita meia unidade
        ("229,50", "P = 229,5"),             # zero a mais
        ("229.5", "P = 229,5"),              # ponto ou vírgula
        ("R$ 1.200,50", "V = 1200,5"),       # milhar
        ("15%", "d = 0,15"),                 # porcentagem como fração
        ("-93 N", "F = −93 N"),              # sinal de outro jeito
    ],
)
def test_o_mesmo_numero_escrito_de_outro_jeito_conta(resposta, ultimo_passo):
    assert not _resposta_final_fora_dos_passos(_questao(resposta, "dados", ultimo_passo))


def test_porcentagem_nao_afrouxa_a_tolerancia_da_fracao():
    """"15%" casa com 0,15 -- não com qualquer número entre 0 e 0,65."""
    assert _resposta_final_fora_dos_passos(_questao("15%", "d = 0,4"))


def test_arredondamento_tem_limite():
    assert _resposta_final_fora_dos_passos(_questao("21,0 m", "h = 21,2"))


def test_o_titulo_do_passo_nao_conta():
    """"3º Passo" tem um 3, mas não é resolução."""
    questao = _questao("3", "x = 2 + 2", "x = 4", titulos=["1º Passo", "3º Passo"])

    assert _resposta_final_fora_dos_passos(questao)


# ====================== QUANDO A REGRA NÃO TEM O QUE DIZER ======================


@pytest.mark.parametrize(
    "questao",
    [
        _questao("25 m"),                                            # sem passos
        _questao("25 m", "Some os catetos ao quadrado."),            # passos sem número
        _questao("Nenhuma das anteriores", "x = 4"),                 # resposta sem número
        {**_questao("25 m", "c = 7"), "correta": 9},                 # índice fora da lista
        {**_questao("25 m", "c = 7"), "correta": "a primeira"},      # índice que não é número
    ],
)
def test_sem_como_comparar_nao_marca(questao):
    assert not _resposta_final_fora_dos_passos(questao)


def test_le_o_numero_e_as_casas():
    assert _numeros_com_casas("x = 1.200,50 e y = 0,15; z = 7") == [(1200.5, 2), (0.15, 2), (7.0, 0)]


# ====================== RECUSA, E SÓ NO LABORATÓRIO ======================


def test_recusa_no_laboratorio():
    _, aceita, motivo = validar_questao_gerada(dict(DESCONTO), "Matematica", "laboratorio")

    assert (aceita, motivo) == (False, "resposta-final-fora-dos-passos")


@pytest.mark.parametrize("contexto", ["oraculo", "rpg", "treino", ""])
def test_fora_do_laboratorio_nao_recusa_por_isso(contexto):
    # Os passos só sobrevivem no Laboratório; nos outros modos não há o que cruzar.
    _, _, motivo = validar_questao_gerada(dict(DESCONTO), "Matematica", contexto)

    assert motivo != "resposta-final-fora-dos-passos"


def test_a_observacao_ficou_sem_regra():
    # Não pode recusar E observar: o log diria que a questão foi aceita.
    assert observar_questao_gerada(dict(DESCONTO), "laboratorio") == []
