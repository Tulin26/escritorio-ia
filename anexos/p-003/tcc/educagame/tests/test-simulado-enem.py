"""O simulado ENEM: histórico, cronômetro e gabarito, sem desenhar nada.

MELHORIA: `_tela_quiz` tinha 189 linhas, e **montava o mesmo dicionário de
histórico duas vezes** -- uma no caminho do tempo esgotado, outra no da
alternativa clicada. Doze chaves cada, que precisam continuar iguais para o
boletim do simulado sair certo: se uma ganhasse campo e a outra não, o
relatório quebraria só para quem estourou o tempo. O mesmo valia para as três
cores do gabarito, escritas inteiras em dois lugares.

Nada disso desenha; tudo isso decide. Extraído, testa-se direto.
"""

from __future__ import annotations

import pytest

from st.ui.tela_enem_st import (
    COR_ACERTO,
    COR_ERRO,
    TEMPO_LIMITE_QUESTAO,
    estado_do_cronometro,
    estilo_da_alternativa,
    item_do_historico,
)

QUESTAO = {
    "pergunta": "Qual a capital do Brasil?",
    "alternativas": ["São Paulo", "Brasília", "Rio de Janeiro", "Salvador", "Recife"],
    "correta": "Brasília",
    "area_bncc": "Ciencias Humanas e Sociais Aplicadas",
    "dificuldade": "Medio",
    "matriz_enem": "H12",
    "explicacao": [{"conteudo": "Brasília é a capital desde 1960."}],
}

CHAVES = {
    "numero", "area", "area_label", "dificuldade", "pergunta", "alternativas",
    "correta", "resposta_aluno", "acertou", "explicacao", "matriz_enem", "tempo",
}


# ====================== O HISTÓRICO ======================


def test_o_item_tem_as_doze_chaves_que_o_pdf_le():
    item = item_do_historico(1, QUESTAO, "Ciências Humanas", "Brasília", True, 12.5)

    assert set(item) == CHAVES


def test_os_dois_caminhos_produzem_a_mesma_forma():
    """A razão de a função existir: eram duas cópias que podiam divergir.

    Uma linha vinda do tempo esgotado e outra vinda de um clique precisam ter
    exatamente os mesmos campos -- o PDF do ENEM lê as duas do mesmo jeito.
    """
    por_clique = item_do_historico(1, QUESTAO, "Ciências Humanas", "Brasília", True, 12.5)
    por_tempo = item_do_historico(2, QUESTAO, "Ciências Humanas", "Tempo esgotado", False, 180.0)

    assert set(por_clique) == set(por_tempo)


def test_o_item_copia_o_que_a_questao_traz():
    item = item_do_historico(3, QUESTAO, "Ciências Humanas", "Rio de Janeiro", False, 40.0)

    assert item["numero"] == 3
    assert item["area"] == "Ciencias Humanas e Sociais Aplicadas"
    assert item["area_label"] == "Ciências Humanas"
    assert item["pergunta"] == "Qual a capital do Brasil?"
    assert item["correta"] == "Brasília"
    assert item["alternativas"] == QUESTAO["alternativas"]
    assert item["matriz_enem"] == "H12"
    assert item["explicacao"] == QUESTAO["explicacao"]


def test_a_resposta_do_aluno_e_o_acerto_vem_de_fora():
    # São os únicos campos que a questão não sabe: dependem do que aconteceu.
    errado = item_do_historico(1, QUESTAO, "CH", "Salvador", False, 30.0)

    assert errado["resposta_aluno"] == "Salvador"
    assert errado["acertou"] is False
    assert errado["correta"] == "Brasília", "o gabarito não pode mudar com o erro"


def test_questao_incompleta_nao_derruba_o_historico():
    """A IA às vezes devolve questão sem matriz ou sem explicação.

    Um KeyError aqui perderia a resposta que o aluno acabou de dar.
    """
    item = item_do_historico(1, {"pergunta": "P"}, "CH", "A", False, 1.0)

    assert set(item) == CHAVES
    assert item["alternativas"] == []
    assert item["correta"] == ""
    assert item["explicacao"] == []


# ====================== O CRONÔMETRO ======================


def test_o_cronometro_conta_do_inicio_da_questao():
    decorrido, restante, expirado = estado_do_cronometro(1000.0, 1030.0)

    assert decorrido == 30.0
    assert restante == TEMPO_LIMITE_QUESTAO - 30
    assert expirado is False


def test_o_limite_exato_ja_conta_como_expirado():
    # Fronteira: em `>` no lugar de `>=`, a questão ficaria pendurada no
    # segundo 180 até o próximo tique.
    _, restante, expirado = estado_do_cronometro(1000.0, 1000.0 + TEMPO_LIMITE_QUESTAO)

    assert expirado is True
    assert restante == 0


def test_o_restante_nunca_fica_negativo():
    # Ele vai para a tela como texto; um "-42s" apareceria para o aluno.
    _, restante, expirado = estado_do_cronometro(1000.0, 5000.0)

    assert restante == 0
    assert expirado is True


def test_sem_inicio_gravado_o_relogio_comeca_agora():
    """Acontece quando a sessão é retomada e o carimbo se perdeu.

    Sem isto, `agora - None` derrubaria a tela; com zero, o aluno começaria
    a questão já com o tempo estourado.
    """
    decorrido, restante, expirado = estado_do_cronometro(None, 1000.0)

    assert decorrido == 0
    assert restante == TEMPO_LIMITE_QUESTAO
    assert expirado is False


def test_o_restante_e_inteiro_para_ir_a_tela():
    _, restante, _ = estado_do_cronometro(1000.0, 1000.5)

    assert isinstance(restante, int)


# ====================== O GABARITO ======================


def test_a_correta_aparece_marcada_mesmo_quando_o_aluno_errou():
    """É o que transforma a tela de resultado em correção.

    Sem isso o aluno vê que errou, mas não vê qual era a certa.
    """
    borda, icone, texto = estilo_da_alternativa("Brasília", "Brasília", "Salvador")

    assert borda == COR_ACERTO
    assert icone == "✅"
    assert texto == COR_ACERTO


def test_a_escolhida_errada_aparece_marcada_como_erro():
    borda, icone, texto = estilo_da_alternativa("Salvador", "Brasília", "Salvador")

    assert borda == COR_ERRO
    assert icone == "❌"
    assert texto == COR_ERRO


def test_a_alternativa_nao_escolhida_fica_neutra():
    borda, icone, texto = estilo_da_alternativa("Recife", "Brasília", "Salvador")

    assert borda not in (COR_ACERTO, COR_ERRO)
    assert icone == "○"


def test_quando_o_aluno_acerta_a_certa_aparece_uma_vez_so_e_como_acerto():
    # A escolhida É a correta: não pode sair pintada de erro nem duas vezes.
    borda, icone, _ = estilo_da_alternativa("Brasília", "Brasília", "Brasília")

    assert borda == COR_ACERTO
    assert icone == "✅"


@pytest.mark.parametrize("resposta", [None, "", "Tempo esgotado"])
def test_sem_resposta_do_aluno_so_a_correta_e_marcada(resposta):
    # É o caso do tempo esgotado: nenhuma alternativa foi escolhida.
    marcadas = [
        alt for alt in QUESTAO["alternativas"]
        if estilo_da_alternativa(alt, "Brasília", resposta)[1] != "○"
    ]

    assert marcadas == ["Brasília"]
