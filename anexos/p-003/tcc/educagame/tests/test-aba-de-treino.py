"""A aba de treino: o estado da sessão e a mensagem de encerramento.

MELHORIA: `renderizar_aba_treino` tinha 192 linhas com quatro fases de uma
máquina de estados empilhadas -- configurar, perguntar, corrigir e encerrar.
Duas peças dela não desenham nada, e por isso nunca tinham sido testadas: o
dicionário que a sessão carrega entre um clique e o próximo, e a regra que
escolhe a mensagem do fim.

A do estado importa porque **ele atravessa `st.rerun()`**: uma chave que
nasce faltando só aparece como `KeyError` várias telas adiante, no meio de um
treino que o aluno já começou.
"""

from __future__ import annotations

import pytest

from st.ui.tela_treino_st import estado_inicial_do_treino, mensagem_de_encerramento

QUESTAO = {"pergunta": "Quanto é 2+2?", "opcoes": ["3", "4"], "correta": 1}


def _estado(**troca):
    base = dict(
        materia="Matematica", tema="frações", nivel="🟡 Médio",
        quantidade=5, questao=QUESTAO, aviso_ia="",
    )
    base.update(troca)
    return estado_inicial_do_treino(**base)


# ====================== O ESTADO QUE ATRAVESSA O RERUN ======================


def test_o_estado_nasce_com_todas_as_chaves_que_a_tela_le():
    """Chave faltando vira KeyError várias telas adiante, no meio do treino."""
    estado = _estado()

    assert set(estado) == {
        "materia", "tema", "nivel", "total", "atual", "acertos", "erros",
        "historico", "questao", "aviso_ia", "respondida", "tempo_inicio",
    }


def test_o_treino_comeca_na_primeira_questao_e_zerado():
    estado = _estado(quantidade=7)

    assert estado["atual"] == 1, "começar em 0 mostraria 'Questão 0 de 7'"
    assert estado["total"] == 7
    assert estado["acertos"] == 0 and estado["erros"] == 0
    assert estado["historico"] == []
    assert estado["respondida"] is False, "nasceria já mostrando a correção"


def test_o_historico_de_cada_treino_e_proprio():
    # Lista mutável compartilhada entre sessões faria o resumo de um treino
    # aparecer no seguinte.
    a, b = _estado(), _estado()
    a["historico"].append({"acertou": True})

    assert b["historico"] == []


def test_o_estado_carrega_a_primeira_questao_e_o_aviso():
    estado = _estado(aviso_ia="a IA falhou, usando banco offline")

    assert estado["questao"] is QUESTAO
    assert "offline" in estado["aviso_ia"]


def test_o_relogio_comeca_a_correr_no_inicio():
    # tempo_inicio alimenta tempo_decorrido, que vai para o log de resposta.
    import time

    antes = time.time()
    estado = _estado()

    assert antes <= estado["tempo_inicio"] <= time.time()


# ====================== A MENSAGEM DO FIM ======================


@pytest.mark.parametrize(
    "acertos, total, faixa",
    [
        (5, 5, "perfeito"),
        (3, 5, "bom"),          # 60% exato: o limite pertence a "bom"
        (2, 5, "fraco"),        # 40%
        (0, 5, "fraco"),
        (7, 10, "bom"),
        (6, 10, "bom"),
        (5, 10, "fraco"),       # 50%
        (1, 1, "perfeito"),
        # Quase tudo certo ainda é "bom": só 100% ganha balão. Sem estes, o
        # limiar do perfeito podia cair para 90 sem ninguém notar.
        (9, 10, "bom"),
        (99, 100, "bom"),
    ],
)
def test_a_faixa_da_mensagem_segue_o_aproveitamento(acertos, total, faixa):
    assert mensagem_de_encerramento(acertos, total)[0] == faixa


def test_o_limite_de_60_por_cento_pertence_a_faixa_boa():
    # O caso de fronteira que um `>` no lugar do `>=` inverteria em silêncio.
    assert mensagem_de_encerramento(3, 5)[0] == "bom"
    assert mensagem_de_encerramento(59, 100)[0] == "fraco"
    assert mensagem_de_encerramento(60, 100)[0] == "bom"


def test_a_mensagem_mostra_o_placar_e_a_porcentagem():
    _, texto = mensagem_de_encerramento(3, 4)

    assert "3/4" in texto
    assert "75%" in texto


def test_treino_sem_questao_nenhuma_nao_divide_por_zero():
    """Não deveria acontecer, mas o custo de não tratar é a tela morrer.

    O aluno terminaria com um traceback em vez do resumo.
    """
    faixa, texto = mensagem_de_encerramento(0, 0)

    assert faixa == "fraco"
    assert "0%" in texto


def test_cada_faixa_tem_um_texto_proprio():
    textos = {mensagem_de_encerramento(a, 5)[1] for a in (5, 3, 1)}

    assert len(textos) == 3
