from services.enem_service import _normalizar_alternativas_rotuladas
from services.ia.normalizacao import limpar_rotulos_alternativas, normalizar_payload_questao


def test_limpar_rotulos_alternativas_quando_lista_tem_letras():
    opcoes = [
        "D a restauracao do poder da Igreja Catolica",
        "B a propagacao dos ideais de liberdade",
        "A instituicao de uma monarquia absoluta",
        "C a expansao do feudalismo",
    ]

    assert limpar_rotulos_alternativas(opcoes) == [
        "a restauracao do poder da Igreja Catolica",
        "a propagacao dos ideais de liberdade",
        "instituicao de uma monarquia absoluta",
        "a expansao do feudalismo",
    ]


def test_nao_remove_artigo_a_quando_lista_nao_parece_rotulada():
    opcoes = [
        "A instituicao de uma monarquia absoluta",
        "O crescimento urbano",
        "Uma reforma economica",
        "Processos migratorios",
    ]

    assert limpar_rotulos_alternativas(opcoes)[0] == "A instituicao de uma monarquia absoluta"


def test_normalizar_payload_questao_limpa_opcoes_rotuladas():
    dados = normalizar_payload_questao({
        "pergunta": "P?",
        "opcoes": ["A) Primeira", "B) Segunda", "C) Terceira", "D) Quarta"],
        "correta": 0,
    })

    assert dados["opcoes"] == ["Primeira", "Segunda", "Terceira", "Quarta"]


def test_normalizar_payload_questao_formata_opcoes_monetarias():
    dados = normalizar_payload_questao({
        "pergunta": "Um produto que custava R$ 120,00 teve 15% de desconto. Qual é o valor final?",
        "opcoes": ["108,00", "102,00", "112,00", "116,00"],
        "correta": 1,
    })

    assert dados["opcoes"] == ["R$ 108,00", "R$ 102,00", "R$ 112,00", "R$ 116,00"]


def test_normalizar_payload_remove_raizes_equivalentes():
    dados = normalizar_payload_questao({
        "pergunta": "Encontre as raizes.",
        "opcoes": ["(0.5, -3)", "(-1, 1.5)", "(-3, 0.5)", "(1, -1.5)"],
        "correta": 0,
    })

    assert dados["opcoes"] == ["(0.5, -3)", "(-1, 1.5)", "(1, -1.5)"]
    assert dados["correta"] == 0


def test_normalizar_payload_remove_subformulas_que_sao_apenas_variaveis():
    dados = normalizar_payload_questao({
        "pergunta": "P?",
        "opcoes": ["1", "2", "3", "4"],
        "correta": 0,
        "subformulas": ["d = desconto", "V = valor original", r"\Delta = b^2 - 4ac"],
    })

    assert dados["subformulas"] == [r"\Delta = b^2 - 4ac"]


def test_normalizar_alternativas_enem_atualiza_correta():
    dados = _normalizar_alternativas_rotuladas({
        "pergunta": "P?",
        "alternativas": ["A) Primeira", "B) Segunda", "C) Terceira", "D) Quarta", "E) Quinta"],
        "correta": "C) Terceira",
    })

    assert dados["alternativas"] == ["Primeira", "Segunda", "Terceira", "Quarta", "Quinta"]
    assert dados["correta"] == "Terceira"
