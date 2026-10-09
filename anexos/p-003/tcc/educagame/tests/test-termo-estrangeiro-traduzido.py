"""O Oraculo deixava termo estrangeiro sem traducao numa materia em portugues.

Captura de tela real (05/10/2026): a explicacao de Historia trouxe 'No periodo
conhecido como "New Imperialism" (final do seculo XIX)...' -- em ingles, entre
aspas, dentro de um texto todo em portugues. A unica regra de idioma que o
prompt do Oraculo tinha era a contraria, e so para a materia de Ingles ("nao
misture portugues no conteudo principal em ingles"); nada pedia o inverso para
as outras materias.

_prompts_oraculo e compartilhado por Treino, Oraculo, Escape Room e RPG; o
Laboratorio (so Exatas, so calculo) nao entra e nao ganhou a regra.

Fica de fora, por decisao do usuario: regra de VALIDADOR que recusasse termo em
ingles. Nome proprio legitimo em ingles aparece direto em texto em portugues
("Wall Street", "Big Bang", "New Deal", citacao de autor), e uma recusa
automatica gerava falso positivo com frequencia. A regra entrou so no prompt,
como pedido -- nao tem como garantir 100%.
"""

from __future__ import annotations

from services.ia.enigma import _prompts_oraculo


def test_materia_em_portugues_recebe_a_regra_de_traduzir_termo_estrangeiro():
    for materia in ["Historia", "Geografia", "Filosofia", "Sociologia", "Fisica"]:
        _, user_prompt = _prompts_oraculo(materia, "2º Ano EM", "Medio", "tema qualquer")
        texto = user_prompt.lower()

        assert "regra geral de idioma" in texto, materia
        assert "new imperialism" in texto, materia
        assert "novo imperialismo" in texto, materia


def test_a_regra_cita_o_que_fica_no_original_por_convencao():
    # Sem essa ressalva, "New Deal" ou "Big Bang" tambem seriam traduzidos --
    # e "Grande Explosao"/"Novo Acordo" nao sao como o portugues usa esses termos.
    _, user_prompt = _prompts_oraculo("Historia", "3º Ano EM", "Medio", "tema qualquer")
    texto = user_prompt.lower()

    assert "new deal" in texto
    assert "big bang" in texto
    assert "laissez-faire" in texto


def test_ingles_nao_recebe_a_regra_pois_tem_a_contraria():
    # A materia de Ingles PRECISA manter o conteudo principal em ingles; a
    # regra geral de idioma, se entrasse aqui tambem, contradiria isso.
    _, user_prompt = _prompts_oraculo("Ingles", "2º Ano EM", "Medio", "tema qualquer")
    texto = user_prompt.lower()

    assert "regra geral de idioma" not in texto
    assert "nao misture portugues no conteudo principal em ingles" in texto
