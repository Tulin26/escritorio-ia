"""Fatos que a IA nao pode mais contradizer de uma questao pra outra.

Por que este arquivo existe
----------------------------
Relatorio de QA de 23/09/2026, achado 4.2 (7 contradicoes de gabarito na
mesma sessao) e prioridade #8: em vez de reescrever esses temas como banco
autoral fixo (que reintroduziria o mesmo risco, so que sem chance de
regenerar), o prompt do Oraculo passa a receber um fato ancora sempre que
o tema sorteado bate com um dos conceitos que o relatorio flagrou como
inconsistentes entre questoes -- Andes, cidadania e Platao.
"""

from __future__ import annotations

from services.ia.enigma import _prompts_oraculo
from services.ia.fatos_canonicos import fato_canonico_para_tema


def test_andes_ancora_subduccao_oceanica_continental():
    fato = fato_canonico_para_tema("Formação dos Andes")
    assert "subduccao" in fato.lower() or "subducção" in fato.lower()
    assert "nazca" in fato.lower()
    assert "duas placas continentais" in fato.lower()


def test_cidadania_ancora_que_nao_e_so_o_voto():
    fato = fato_canonico_para_tema("Cidadania e participação política")
    assert "voto" in fato.lower()
    assert "nao se resume" in fato.lower() or "não se resume" in fato.lower()


def test_platao_ancora_conhecimento_vem_da_razao():
    fato = fato_canonico_para_tema("Platão e a teoria do conhecimento")
    assert "razao" in fato.lower() or "razão" in fato.lower()
    assert "doxa" in fato.lower()


def test_tema_sem_fato_conhecido_nao_ancora_nada():
    assert fato_canonico_para_tema("Funções da linguagem") == ""
    assert fato_canonico_para_tema("Equações do 2º grau") == ""
    assert fato_canonico_para_tema("") == ""


def test_o_prompt_do_oraculo_inclui_a_ancora_quando_o_tema_bate():
    _, user_prompt = _prompts_oraculo("Geografia", "3º Ano EM", "Medio", "Formação dos Andes")

    assert "subduccao" in user_prompt.lower() or "subducção" in user_prompt.lower()


def test_o_prompt_do_oraculo_fica_igual_quando_o_tema_nao_bate():
    _, user_prompt = _prompts_oraculo("Matematica", "3º Ano EM", "Medio", "Funções de 2º grau")

    assert "fato correto e obrigatorio" not in user_prompt.lower()
