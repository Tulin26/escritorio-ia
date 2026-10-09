from __future__ import annotations

from core.answer_equivalence import conjunto_raizes_quadraticas, tem_opcoes_equivalentes


def test_opcoes_com_raizes_na_ordem_trocada_sao_equivalentes():
    # MELHORIA: bug visto ao vivo em producao -- "-3 e -2" e "-2 e -3" (o
    # mesmo par de raizes, so em ordem diferente) apareciam como duas
    # alternativas DIFERENTES na mesma questao de Bhaskara. O formato real
    # gerado pelo app pra resposta de duas raizes e so "N e M", sem
    # nenhuma palavra-marcadora ("raiz", "solucao", parenteses etc.) que a
    # funcao antiga exigia pra reconhecer o par.
    opcoes = ["-3 e -2", "-1 e -6", "2 e 3", "-2 e -3"]
    assert tem_opcoes_equivalentes(opcoes) is True


def test_conjunto_raizes_reconhece_par_sem_marcador():
    assert conjunto_raizes_quadraticas("-3 e -2") == (-3.0, -2.0)
    assert conjunto_raizes_quadraticas("-2 e -3") == (-3.0, -2.0)
    assert conjunto_raizes_quadraticas("-3, -2") == (-3.0, -2.0)


def test_conjunto_raizes_ignora_par_de_numeros_com_outro_sentido():
    # Dois numeros lado a lado nao bastam -- precisa sobrar SO os numeros
    # e um conector (e/ou/and/virgula) depois de tirar os digitos, senao
    # vira falso positivo em textos que so citam dois numeros por acaso.
    assert conjunto_raizes_quadraticas("Entre 2 e 5 dias") is None
    assert conjunto_raizes_quadraticas("R$ 2 mil e R$ 5 mil") is None
    assert conjunto_raizes_quadraticas("12 N") is None


def test_opcoes_distintas_sem_par_repetido_nao_sao_equivalentes():
    opcoes = ["-3 e -2", "-1 e -6", "2 e 3", "4 e 5"]
    assert tem_opcoes_equivalentes(opcoes) is False
