"""O passo final com raiz passa a ser conferido.

MELHORIA: visto em produção em 03/09/2026, numa questão de lei dos cossenos
gerada por IA. Os três primeiros passos estavam certos:

    BC² = 10² + 15² − 2·10·15·(−0,5)
    BC² = 100 + 225 + 150
    BC² = 475

e o passo final dizia **BC = √475 ≈ 19,4**. A raiz de 475 é 21,79; 19,4 é a
raiz de 375. O aluno respondeu 21,8 — que está certo —, levou "Errou" e
perdeu 15 pontos.

Por que ninguém pegou:

  * `"sqrt"` está em `_TERMOS_FUNCAO_TRANSCENDENTE`, e essa lista faz o passo
    inteiro ser **pulado** na comparação numérica. Isso existe por um bom
    motivo — o normalizador apaga o `sqrt` e leria `sqrt(25)` como 25 —, mas
    o efeito colateral é que o passo onde a resposta nasce em Pitágoras, lei
    dos cossenos e Bhaskara não era conferido por ninguém.
  * `_resposta_marcada_diverge_do_resultado_final` não ajuda aqui: ela
    pergunta se a alternativa bate com o resultado final **escrito**, e batia
    — o passo dizia 19,4 e a alternativa era 19,4. Ninguém perguntava se a
    raiz confere com o radicando.

Medido: das 50.900 questões dos bancos offline, 20 têm o padrão e **nenhuma**
seria recusada pela regra nova.
"""

from __future__ import annotations

import pytest

from services.ia.validacao import (
    _casas_decimais,
    _raiz_aproximada_incorreta,
    _tolerancia_de_arredondamento,
    validar_questao_gerada,
)

BARRA = chr(92)


def com_passo(conteudo: str) -> dict:
    return {"passos_resolucao": [{"titulo": "Resultado Final", "conteudo": conteudo, "final": True}]}


def questao_lei_dos_cossenos(resultado: str, alternativa: str) -> dict:
    """A questão exata que apareceu na tela, com o final parametrizável."""
    return {
        "pergunta": (
            "Em um triângulo ABC, o ângulo A mede 120°, o lado AB = 10 cm e o lado "
            "AC = 15 cm. Qual é o comprimento aproximado do lado BC em centímetros? "
            "(Use cos 120° = -0,5)"
        ),
        "opcoes": [alternativa, "17,5", "25,0", "13,2"],
        "correta": 0,
        "formula": f"BC^2 = AB^2 + AC^2 - 2 {BARRA}cdot AB {BARRA}cdot AC {BARRA}cdot {BARRA}cos(A)",
        "passos_resolucao": [
            {"titulo": "1º Passo", "conteudo": f"BC^2 = 10^2 + 15^2 - 2 {BARRA}cdot 10 {BARRA}cdot 15 {BARRA}cdot (-0,5)"},
            {"titulo": "2º Passo", "conteudo": "BC^2 = 100 + 225 + 150"},
            {"titulo": "3º Passo", "conteudo": "BC^2 = 475"},
            {"titulo": "Resultado Final", "conteudo": resultado, "final": True},
        ],
        "explicacao": [{"tipo": "texto", "conteudo": "Aplicando a lei dos cossenos."}],
    }


# ====================== O CASO QUE TIROU PONTO DO ALUNO ======================


def test_a_questao_que_apareceu_na_tela_e_recusada():
    ruim = questao_lei_dos_cossenos(f"BC = {BARRA}sqrt{{475}} {BARRA}approx 19,4", "19,4")

    _, aceita, motivo = validar_questao_gerada(ruim, "Matematica", "laboratorio")

    assert not aceita
    assert motivo == "raiz-aproximada-incorreta"


def test_a_mesma_questao_com_a_raiz_certa_passa():
    """O par obrigatório: uma regra que recusa tudo não serve de nada."""
    boa = questao_lei_dos_cossenos(f"BC = {BARRA}sqrt{{475}} {BARRA}approx 21,8", "21,8")

    _, aceita, motivo = validar_questao_gerada(boa, "Matematica", "laboratorio")

    assert aceita, motivo


# ====================== ARREDONDAR É LEGÍTIMO ======================


@pytest.mark.parametrize(
    "escrito",
    ["21,8", "21,79", "21,7945", "22", "21,794"],
)
def test_o_arredondamento_honesto_de_raiz_de_475_e_aceito(escrito):
    """√475 = 21,7945. A tolerância acompanha a precisão que o texto declarou:
    meia unidade na última casa mostrada. Uma tolerância fixa recusaria o
    arredondamento para inteiro, que é o mais comum em prova.
    """
    assert not _raiz_aproximada_incorreta(com_passo(f"{BARRA}sqrt{{475}} {BARRA}approx {escrito}"))


@pytest.mark.parametrize(
    "escrito,por_que",
    [
        ("19,4", "é a raiz de 375, não de 475"),
        ("21,7", "21,7945 arredonda para 21,8"),
        ("23", "erra até no inteiro"),
        ("4,7", "é a raiz da raiz"),
    ],
)
def test_o_que_nao_e_arredondamento_e_recusado(escrito, por_que):
    assert _raiz_aproximada_incorreta(
        com_passo(f"{BARRA}sqrt{{475}} {BARRA}approx {escrito}")
    ), por_que


def test_a_tolerancia_encolhe_conforme_as_casas():
    assert _tolerancia_de_arredondamento("22") > _tolerancia_de_arredondamento("21,8")
    assert _tolerancia_de_arredondamento("21,8") > _tolerancia_de_arredondamento("21,79")


@pytest.mark.parametrize(
    "escrito,casas",
    [("22", 0), ("21,8", 1), ("21,79", 2), ("21.7945", 4), ("-3", 0)],
)
def test_as_casas_decimais_sao_contadas_com_virgula_ou_ponto(escrito, casas):
    assert _casas_decimais(escrito) == casas


# ====================== AS FORMAS QUE A IA ESCREVE ======================


@pytest.mark.parametrize(
    "texto",
    [
        BARRA + "sqrt{475} " + BARRA + "approx 19,4",
        BARRA + "sqrt{475} = 19,4",
        BARRA + "sqrt(475) " + BARRA + "approx 19,4",
        "sqrt(475) = 19.4",
        "raiz(475) = 19,4",
        "raiz quadrada de 475 = 19,4",
        "√475 ≈ 19,4",
        "√475 = 19,4",
    ],
)
def test_toda_notacao_de_raiz_e_reconhecida(texto):
    """A IA alterna entre LaTeX, ASCII e o símbolo. Cobrir só uma delas
    deixaria o defeito passar pelas outras.
    """
    assert _raiz_aproximada_incorreta(com_passo(texto)), texto


# ====================== O QUE NÃO DÁ PARA CONFERIR ======================


def test_radicando_com_incognita_nao_e_julgado():
    """`√(x² + 9) = 5` pode estar certo — depende de x. Recusar aqui seria
    inventar um erro que não se sabe que existe.
    """
    assert not _raiz_aproximada_incorreta(com_passo(f"{BARRA}sqrt{{x^2 + 9}} = 5"))
    assert not _raiz_aproximada_incorreta(com_passo(f"{BARRA}sqrt{{b^2-4ac}} = 7"))


def test_raiz_sem_resultado_declarado_nao_e_julgada():
    assert not _raiz_aproximada_incorreta(com_passo(f"{BARRA}Delta = {BARRA}sqrt{{b^2-4ac}}"))


def test_a_raiz_errada_num_passo_do_meio_tambem_e_pega():
    """`_coletar_textos_resultado_exatas` devolve só o passo marcado como
    final. A raiz errada pode estar num passo do meio, com o número errado
    sendo carregado adiante — e aí o passo final "confere" consigo mesmo.

    Um mutante mostrou que sem este caso a varredura dos `passos_resolucao`
    podia ser arrancada inteira com a suíte verde: todos os outros testes
    marcam o passo como final.
    """
    dados = {
        "passos_resolucao": [
            {"titulo": "1º Passo", "conteudo": "x^2 = 475"},
            {"titulo": "2º Passo", "conteudo": f"x = {BARRA}sqrt{{475}} {BARRA}approx 19,4"},
            {"titulo": "Resultado Final", "conteudo": "x = 19,4", "final": True},
        ],
    }

    assert _raiz_aproximada_incorreta(dados)


def test_questao_sem_passos_nao_quebra():
    assert not _raiz_aproximada_incorreta({})
    assert not _raiz_aproximada_incorreta({"passos_resolucao": None})
    assert not _raiz_aproximada_incorreta({"passos_resolucao": [None, "texto solto"]})


def test_a_raiz_certa_de_quadrado_perfeito_passa():
    assert not _raiz_aproximada_incorreta(com_passo(f"{BARRA}sqrt{{100}} = 10"))
    assert not _raiz_aproximada_incorreta(com_passo(f"{BARRA}sqrt{{2}} {BARRA}approx 1,41"))


def test_o_radicando_pode_ser_uma_conta():
    """A IA às vezes não fecha a conta antes da raiz."""
    assert not _raiz_aproximada_incorreta(com_passo(f"{BARRA}sqrt{{100 + 225 + 150}} {BARRA}approx 21,8"))
    assert _raiz_aproximada_incorreta(com_passo(f"{BARRA}sqrt{{100 + 225 + 150}} {BARRA}approx 19,4"))


# ====================== OS BANCOS OFFLINE NÃO SÃO ATINGIDOS ======================


@pytest.mark.parametrize("contexto", ["oraculo", "laboratorio"])
def test_a_regra_vale_em_todos_os_modos(contexto):
    """Os cinco modos passam por um de dois pontos de validação: o Laboratório
    usa `contexto="laboratorio"`; Treino, Oráculo, Escape Room **e RPG** usam
    `"oraculo"`.

    Duas checagens aritméticas que já existiam são desligadas quando o
    contexto é "oraculo" — e isso é deliberado, medido contra os bancos
    offline: `exatas-sem-estrutura` recusaria 87,7% das questões boas de
    exatas, e `passo-final-diverge` recusaria 1,6% (amostradas, todas falsos
    positivos, do passo de declaração "b = 6, h = 8" e de resultados não
    escalares como "3/10").

    Esta aqui não leva guarda de contexto: raiz errada é raiz errada em
    qualquer modo, e a medição deu zero falso positivo.
    """
    ruim = questao_lei_dos_cossenos(f"BC = {BARRA}sqrt{{475}} {BARRA}approx 19,4", "19,4")

    _, aceita, motivo = validar_questao_gerada(ruim, "Matematica", contexto)

    assert not aceita
    assert motivo == "raiz-aproximada-incorreta"


def test_nenhuma_questao_offline_e_recusada_pela_regra_nova():
    """A medição que autorizou a mudança: 20 das 50.900 questões offline têm
    o padrão de raiz aproximada, e nenhuma é recusada. Uma regra de validação
    recusa questão — se ela errar, o aluno perde conteúdo bom e a aula cai no
    banco offline sem necessidade.
    """
    import services.banks.em as em
    import services.banks.fundamental as ef
    import services.banks.laboratorio as lab
    import services.banks.rpg as rp

    def todas():
        for materia in em.MATERIAS:
            yield from em.listar_questoes_em(materia)
        for materia in ef.MATERIAS:
            yield from ef.listar_questoes_ef(materia)
        for materia in rp.MATERIAS:
            yield from rp.listar_questoes_rpg(materia)
        for materia in lab.MATERIAS_LAB_OFFLINE:
            yield from lab.listar_questoes_laboratorio(materia, "EM")
        for materia in lab.MATERIAS_LAB_EF_OFFLINE:
            yield from lab.listar_questoes_laboratorio(materia, "EF")

    recusadas = [q for q in todas() if _raiz_aproximada_incorreta(q)]

    assert not recusadas, f"{len(recusadas)} questões offline boas seriam recusadas"
