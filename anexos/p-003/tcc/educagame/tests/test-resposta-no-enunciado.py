"""O enunciado não pode dizer qual é a resposta.

Achado 5.5 do relatório de QA de 23/09/2026 ("itens mal formulados, ambíguos
ou auto-respondidos"). Dois casos da tabela são o mesmo defeito:

  * Escape Room · Geografia (08:45:20): 'o comando termina com "indicando
    seu crescimento natural" e a alternativa correta é "Taxa de crescimento
    natural"';
  * Geografia Q17 e Q20 (Oráculo): 'a correta repete literalmente o
    enunciado'.

Medida a recusa ANTES de ligar a regra, nos dois corpora (28/09/2026):

  * bancos offline, 50.900 questões: 20 (0,04%), todas o MESMO enunciado (o
    do IPHAN, em que a alternativa correta abre a sigla com as palavras do
    próprio enunciado) -- e questão de banco nem passa pelo validador;
  * questões reais da IA, 554 registros: 4 (0,72%), as quatro defeituosas de
    fato. Uma delas é o caso do relatório, palavra por palavra: "Qual
    indicador demográfico representa a diferença entre nascimentos e óbitos
    em uma população, indicando seu crescimento natural?" -> "Taxa de
    crescimento natural".

Três armadilhas apareceram na medição e viraram guarda:

  1. Questão de interpretação TEM a resposta no enunciado de propósito
     ("Leia: '...é o melhor da série.' Qual parte do trecho é uma opinião?").
     Sem a guarda de leitura, 36 questões corretas dos bancos seriam
     recusadas.
  2. "5 g/L" tem três "palavras" para quem separa por não-letra, e a resposta
     numérica costuma aparecer no enunciado. Sem contar só palavra de letra,
     20 questões de diluição -- corretas -- cairiam na regra.
  3. A resposta repete o ASSUNTO da pergunta sem se entregar: "O MST,
     fundado no Brasil na década de 1980, luta principalmente por:" ->
     "a reforma agrária e o acesso à terra para trabalhadores rurais sem
     propriedade". "Trabalhadores rurais" está no nome do movimento, não na
     resposta. Por isso o trecho repetido precisa cobrir METADE da
     alternativa correta: sem essa terceira guarda seriam 108 recusas no
     banco, e três dos catorze enunciados distintos eram bons.

O que NÃO virou regra: o viés de tamanho ('a correta é muito mais longa que
os 3 distratores', caso do Escape Room · Sociologia 09:01:46). Medido no
mesmo corpus, o limiar mais frouxo (correta 2x maior que o maior distrator e
com 60+ caracteres) pega 4 das 554 -- e a primeira delas é legítima: "Qual
foi a principal ação de Martim Lutero..." -> "Publicação das 95 teses nas
portas da Igreja do Castelo de Wittenberg". Tamanho não separa "resposta
precisa de mais palavras" de "resposta se entrega pelo tamanho", então isso
ficou como regra de prompt, que não recusa nada.
"""

from __future__ import annotations

import pytest

from services.ia.enigma import _prompts_oraculo
from services.ia.resposta_no_enunciado import pergunta_entrega_a_resposta
from services.ia.validacao import validar_questao_gerada


# --------------------------------------------------------------------------
# A regra, isolada


def test_caso_do_relatorio_escape_room_geografia():
    assert pergunta_entrega_a_resposta(
        "Observe a diferença entre nascimentos e óbitos de um país, indicando seu crescimento natural.",
        ["Taxa de migração", "Taxa de crescimento natural", "Densidade demográfica", "Taxa de urbanização"],
        1,
    )


def test_caso_real_da_ia_epistemologia():
    # Registro real de 2026, modo Oráculo.
    assert pergunta_entrega_a_resposta(
        "Qual formulação tradicional da epistemologia clássica define conhecimento como crença verdadeira justificada?",
        ["Crença verdadeira justificada", "Intuição sensível", "Dúvida metódica", "Indução completa"],
        0,
    )


def test_caso_real_da_ia_poesia_barroca():
    # Registro real, Escape Room: o enunciado LISTA a resposta.
    assert pergunta_entrega_a_resposta(
        "Qual característica distintiva da poesia barroca se manifesta na presença de contrastes "
        "entre o mundano e o espiritual, uso de paradoxos e antíteses?",
        [
            "Uso de contrastes, paradoxos e antíteses",
            "Exaltação da razão e da ciência",
            "Linguagem coloquial e oral",
            "Simplicidade e clareza",
        ],
        0,
    )


def test_caso_real_da_ia_em_ingles():
    # O modo de Inglês não é exceção: o aluno acerta comparando as frases.
    assert pergunta_entrega_a_resposta(
        "Which sentence correctly uses the passive voice to indicate that the report was written by the manager?",
        [
            "The manager wrote the report.",
            "The report was written by the manager.",
            "The report writes the manager.",
            "The manager is writing the report.",
        ],
        1,
    )


def test_a_correta_pode_vir_como_texto_em_vez_de_indice():
    # O ENEM e a Batalha mandam o texto exato da correta, não o índice.
    assert pergunta_entrega_a_resposta(
        "Qual formulação define conhecimento como crença verdadeira justificada?",
        ["Crença verdadeira justificada", "Intuição sensível", "Dúvida metódica"],
        "Crença verdadeira justificada",
    )


# --------------------------------------------------------------------------
# O que a regra NÃO pode recusar


def test_questao_de_interpretacao_continua_valida():
    # Caso real dos bancos: a resposta é um pedaço do texto citado, e tem de
    # estar no enunciado.
    assert not pergunta_entrega_a_resposta(
        "Leia: 'O filme dura 120 minutos e estreou em março. Na minha opinião, é o melhor da série.' "
        "Qual parte do trecho é uma opinião?",
        ["'é o melhor da série'", "'dura 120 minutos'", "'estreou em março'", "'o filme'"],
        0,
    )


def test_analise_de_frase_citada_continua_valida():
    # Outro caso real dos bancos, e o que a guarda de leitura protege sozinha:
    # a alternativa cita o trecho analisado porque a questão é sobre ele.
    assert not pergunta_entrega_a_resposta(
        "Em 'Machado de Assis, autor de Dom Casmurro, é um dos maiores nomes da literatura brasileira', "
        "as vírgulas foram empregadas para:",
        [
            "isolar o aposto explicativo 'autor de Dom Casmurro'",
            "separar orações coordenadas assindéticas",
            "marcar a elipse do verbo principal",
        ],
        0,
    )


def test_pergunta_que_cita_os_dois_termos_e_manda_escolher():
    # "Entre A e B, qual...": o enunciado traz as duas alternativas inteiras,
    # e escolher continua exigindo saber a diferença. É a folga sobre o melhor
    # distrator que enxerga isso.
    assert not pergunta_entrega_a_resposta(
        "Entre crescimento natural e saldo migratório, qual indicador mede a diferença entre "
        "nascimentos e óbitos?",
        ["crescimento natural", "saldo migratório"],
        0,
    )


def test_resposta_numerica_com_unidade_continua_valida():
    # "5 g/L" aparece no enunciado de 20 questões de diluição dos bancos --
    # todas corretas. Sem contar só palavra de letra, a regra as recusaria.
    assert not pergunta_entrega_a_resposta(
        "Uma solução de 200 mL com concentração 15 g/L recebe água até completar 600 mL. "
        "Qual passa a ser a concentração da solução diluída, em g/L? Use 5 g/L como referência de leitura.",
        ["5 g/L", "10 g/L", "15 g/L", "45 g/L"],
        0,
    )


@pytest.mark.parametrize(
    ("pergunta", "opcoes"),
    [
        # O assunto do enunciado aparece na correta E nos distratores: aqui
        # "gás carbônico" não aponta para alternativa nenhuma, e é isso que a
        # folga sobre o melhor distrator existe para enxergar.
        ("Durante a fotossíntese a planta usa gás carbônico e libera oxigênio. "
         "Qual é o papel do gás carbônico nesse processo?",
         ["o gás carbônico é a fonte de carbono do açúcar produzido",
          "o gás carbônico é liberado como resíduo da reação",
          "o gás carbônico transporta a água até as folhas"]),
        # Palavras soltas da resposta no enunciado, mas não a frase inteira.
        ("Qual processo explica o aumento da população urbana no Brasil?",
         ["o êxodo rural somado à industrialização", "a reforma agrária", "o crescimento vegetativo"]),
    ],
)
def test_coincidencia_de_palavras_nao_e_resposta_entregue(pergunta, opcoes):
    assert not pergunta_entrega_a_resposta(pergunta, opcoes, 0)


@pytest.mark.parametrize(
    ("pergunta", "opcoes"),
    [
        # Casos reais dos bancos que a regra pegava antes da guarda de
        # cobertura. Nos dois, o trecho repetido vem do ASSUNTO da pergunta.
        ("O Movimento dos Trabalhadores Rurais Sem Terra (MST), fundado no Brasil na década de 1980, "
         "luta principalmente por:",
         ["a reforma agrária e o acesso à terra para trabalhadores rurais sem propriedade",
          "a criação de novas universidades públicas no campo",
          "a redução da jornada de trabalho na indústria"]),
        ("Qual é uma diferença entre uma lei e uma regra moral?",
         ["a lei é escrita e tem punição prevista pelo Estado; a regra moral é cobrada pela consciência e pelo grupo",
          "as duas são escritas e julgadas pelo mesmo tribunal",
          "nenhuma das duas orienta o comportamento das pessoas"]),
        ("A performance, como linguagem artística, tem como principal característica:",
         ["usar o corpo do artista como principal meio de expressão, numa ação ao vivo diante do público",
          "registrar paisagens em tinta a óleo sobre tela",
          "esculpir figuras em mármore para praças públicas"]),
    ],
)
def test_resposta_que_so_repete_o_assunto_continua_valida(pergunta, opcoes):
    assert not pergunta_entrega_a_resposta(pergunta, opcoes, 0)


def test_sem_gabarito_legivel_nao_recusa():
    assert not pergunta_entrega_a_resposta("Qual é a resposta?", ["uma coisa", "outra coisa"], 9)
    assert not pergunta_entrega_a_resposta("Qual é a resposta?", [], 0)
    assert not pergunta_entrega_a_resposta("", ["uma coisa qualquer", "outra"], 0)


# --------------------------------------------------------------------------
# No validador compartilhado (Oráculo, Escape Room, RPG, Treino, Laboratório)


def _questao(pergunta: str, opcoes: list[str], correta: int) -> dict:
    return {
        "pergunta": pergunta,
        "opcoes": opcoes,
        "correta": correta,
        "explicacao": [{"tipo": "resultado", "conteudo": "A taxa de crescimento natural é nascimentos menos óbitos."}],
    }


def test_validacao_recusa_com_motivo_proprio():
    _dados, valida, motivo = validar_questao_gerada(
        _questao(
            "Observe a diferença entre nascimentos e óbitos de um país, indicando seu crescimento natural.",
            ["Taxa de migração", "Taxa de crescimento natural", "Densidade demográfica", "Taxa de urbanização"],
            1,
        ),
        "Geografia",
        contexto="oraculo",
    )

    assert valida is False
    assert motivo == "resposta-no-enunciado"


def test_validacao_aceita_o_mesmo_enunciado_sem_a_entrega():
    _dados, valida, motivo = validar_questao_gerada(
        _questao(
            "Que indicador se obtém pela diferença entre nascimentos e óbitos de um país?",
            ["Taxa de migração", "Taxa de crescimento natural", "Densidade demográfica", "Taxa de urbanização"],
            1,
        ),
        "Geografia",
        contexto="oraculo",
    )

    assert valida is True, motivo


# --------------------------------------------------------------------------
# O que só o prompt pode pedir


@pytest.mark.parametrize(
    "trecho",
    [
        "as quatro alternativas tem de ter tamanho parecido",
        "o enunciado NAO pode conter a resposta escrita",
    ],
)
def test_o_prompt_pede_o_que_a_regra_nao_recusa(trecho):
    _, user_prompt = _prompts_oraculo("Geografia", "3º Ano EM", "Medio", "demografia")

    assert trecho in user_prompt
