"""A troca de acentos não cola uma palavra na outra.

Visto em produção em 11/09/2026: "Qual e a corrente?" chegava à tela como
"Qualé a corrente?". Não era a IA: a mesma colagem aparecia em pergunta do
banco próprio.

O dicionário está certo -- `" e a corrente": " é a corrente"`, com o espaço
dos dois lados. O espaço sumia em `_manter_capitalizacao`, que para frase de
várias palavras reconstrói o texto com `split()` e `" ".join()`: o espaço da
frente não é palavra, e não volta.

Medido antes de consertar: 628 perguntas do banco próprio saíam com "Qualé",
fora outras coladas do mesmo jeito; e 10 das 17 questões reais do dia.
"""

from __future__ import annotations

import pytest

from core.text_cleanup import _manter_capitalizacao, aplicar_acentos_pt


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("Qual e a corrente?", "Qual é a corrente?"),
        ("Qual e a velocidade final?", "Qual é a velocidade final?"),
        ("Qual e a potencia dissipada?", "Qual é a potência dissipada?"),
    ],
)
def test_qual_e_a_nao_vira_uma_palavra_so(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado


def test_o_caso_exato_da_tela():
    bruto = "Na revisão de grandezas físicas, um circuito tem tensão de 60 V e resistência de 11 ohm. Qual e a corrente?"

    saida = aplicar_acentos_pt(bruto)

    assert "Qualé" not in saida, saida
    assert saida.endswith("Qual é a corrente?"), saida


def test_o_espaco_da_frente_e_de_tras_da_frase_sobrevive():
    assert _manter_capitalizacao(" é a corrente", " e a corrente") == " é a corrente"
    assert _manter_capitalizacao("é a corrente ", "e a corrente ") == "é a corrente "


def test_a_maiuscula_palavra_a_palavra_continua_valendo():
    """O motivo de existir o caminho de várias palavras: "Idade Media" tem de
    virar "Idade Média", e não "Idade média"."""
    assert aplicar_acentos_pt("Idade Media") == "Idade Média"
    assert _manter_capitalizacao(" é a Corrente", " e a Corrente") == " é a Corrente"


def test_nenhuma_pergunta_do_banco_sai_com_qual_colado():
    """A varredura que decide: as 50.900 perguntas, pelo mesmo caminho da tela."""
    import services.banks.em as em
    import services.banks.fundamental as ef
    import services.banks.laboratorio as lab
    import services.banks.rpg as rp

    perguntas = []
    for materia in em.MATERIAS:
        perguntas += [q.get("pergunta") for q in em.listar_questoes_em(materia)]
    for materia in ef.MATERIAS:
        perguntas += [q.get("pergunta") for q in ef.listar_questoes_ef(materia)]
    for materia in rp.MATERIAS:
        perguntas += [q.get("pergunta") for q in rp.listar_questoes_rpg(materia)]
    for materia in lab.MATERIAS_LAB_OFFLINE:
        perguntas += [q.get("pergunta") for q in lab.listar_questoes_laboratorio(materia, "EM")]
    for materia in lab.MATERIAS_LAB_EF_OFFLINE:
        perguntas += [q.get("pergunta") for q in lab.listar_questoes_laboratorio(materia, "EF")]

    # As 50.900 perguntas são só ~8.600 textos diferentes, e a troca de
    # acentos depende do texto, não de qual questão o traz: cada texto passa
    # por ela uma vez só. Mesmo veredito, e o teste deixa de ser 37% da suíte
    # (248 s em 08/10/2026).
    distintas = sorted({str(p or "") for p in perguntas})
    assert distintas, "a varredura não leu nenhuma pergunta"

    coladas = [p for p in distintas if "qualé" in aplicar_acentos_pt(p).lower()]

    assert not coladas, f"{len(coladas)} perguntas distintas com 'Qualé'; ex.: {coladas[0][:90]!r}"
