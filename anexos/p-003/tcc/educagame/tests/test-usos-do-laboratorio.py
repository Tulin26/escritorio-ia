"""O cartão "onde usamos isso no dia a dia" do Laboratório.

MELHORIA: `_usos_dia_a_dia_laboratorio` tinha 152 linhas e era a quinta maior
função do projeto -- mas 133 delas eram **dados**. A lógica sempre teve quatro
linhas: casar marcador, devolver o cartão. A tabela morava dentro do corpo, e
por isso ninguém conseguia lê-la, contá-la nem testá-la como dado.

Como constante de módulo, dá para cobrar o que importa numa tabela de
marcadores: que ela esteja bem formada, que **toda regra escrita seja
alcançável** (regra inalcançável é texto que nunca chega ao aluno) e que os
marcadores estejam na forma que o texto de busca realmente tem -- minúsculas
e sem acento, porque `_texto_busca_laboratorio` normaliza para ASCII.
"""

from __future__ import annotations

import pytest

from st.ui.mode_common_st import (
    USOS_DIA_A_DIA_LABORATORIO,
    USOS_PADRAO_LABORATORIO,
    _usos_dia_a_dia_laboratorio,
)


def titulo_de(pergunta: str, materia: str = "") -> str:
    return _usos_dia_a_dia_laboratorio({"pergunta": pergunta}, materia)[0]


# ====================== A TABELA ESTÁ BEM FORMADA ======================


def test_toda_regra_tem_marcadores_titulo_e_exemplos():
    assert len(USOS_DIA_A_DIA_LABORATORIO) == 12

    for marcadores, titulo, usos in USOS_DIA_A_DIA_LABORATORIO:
        assert marcadores, titulo
        assert titulo.startswith("Onde usamos"), titulo
        assert len(usos) == 5, f"{titulo}: {len(usos)} exemplos"
        for onde, texto in usos:
            assert onde and texto, titulo
            assert texto.endswith("."), f"{titulo} / {onde}"


def test_os_marcadores_estao_na_forma_do_texto_de_busca():
    """Minúsculas e sem acento -- é assim que o texto chega.

    `_texto_busca_laboratorio` faz `.lower()` e depois normaliza para ASCII.
    Um marcador com acento ou maiúscula nunca casaria com nada, e a regra
    inteira ficaria morta em silêncio.
    """
    for marcadores, titulo, _ in USOS_DIA_A_DIA_LABORATORIO:
        for marcador in marcadores:
            assert marcador == marcador.lower(), f"{titulo}: {marcador!r}"
            assert marcador.isascii(), f"{titulo}: {marcador!r} tem acento"


def test_nenhum_titulo_se_repete():
    titulos = [titulo for _, titulo, _ in USOS_DIA_A_DIA_LABORATORIO]

    assert len(titulos) == len(set(titulos))


# ====================== TODA REGRA É ALCANÇÁVEL ======================


def test_toda_regra_e_alcancavel_pelo_seu_primeiro_marcador():
    """Regra que nunca casa é texto escrito que nenhum aluno vai ler.

    Testa pelo primeiro marcador de cada uma: se outra regra anterior o
    roubar, esta falha e aponta qual.
    """
    for marcadores, titulo, _ in USOS_DIA_A_DIA_LABORATORIO:
        alcancado = titulo_de(marcadores[0])

        assert alcancado == titulo, (
            f"{titulo!r} é inalcançável pelo próprio marcador {marcadores[0]!r}: "
            f"quem atendeu foi {alcancado!r}"
        )


@pytest.mark.parametrize(
    "pergunta, esperado",
    [
        ("Calcule a area do triangulo de base 10 e altura 4", "área e medidas"),
        ("Um produto de 200 reais teve desconto de 15%", "porcentagem"),
        ("Numa progressao aritmetica a razao vale 5", "progressão aritmética"),
        ("Quantos mol de reagente sobram na reacao", "mol e proporções"),
        ("Calcule a massa molar na estequiometria da reacao", "mol e proporções"),
        ("Resolva a equacao do 2o grau por bhaskara", "equação do 2º grau"),
        ("Qual a tangente do angulo formado pela sombra do poste", "trigonometria"),
        ("Qual a velocidade media em m/s do deslocamento", "velocidade"),
        ("Uma massa sofre aceleracao; calcule a forca em newton", "força"),
        ("Pela lei de ohm, qual a corrente no circuito", "eletricidade"),
        ("Qual a concentracao em g/l dessa solucao", "concentração"),
        ("Qual o calor necessario para a variacao de temperatura", "calor e temperatura"),
    ],
)
def test_a_pergunta_tipica_cai_no_cartao_certo(pergunta, esperado):
    assert esperado in titulo_de(pergunta)


def test_assunto_de_fora_cai_no_cartao_generico():
    assert titulo_de("Quem foi o imperador do Brasil em 1822") == USOS_PADRAO_LABORATORIO[0]


def test_o_cartao_generico_tem_a_mesma_forma_dos_outros():
    # Ele é o mais visto de todos -- toda questão que não casa com regra
    # nenhuma cai aqui --, e mesmo assim ficava de fora da conferência de
    # forma, que só varria a tabela.
    titulo, usos = USOS_PADRAO_LABORATORIO

    assert titulo.startswith("Onde usamos")
    assert len(usos) == 5
    for onde, texto in usos:
        assert onde and texto
        assert texto.endswith("."), onde


def test_a_materia_tambem_entra_na_busca():
    # O texto de busca junta matéria + pergunta + fórmula + passos.
    assert "velocidade" in titulo_de("Complete o valor pedido", "velocidade")


# ====================== QUANDO DUAS REGRAS CASAM ======================
#
# Parar no primeiro que casa dava o cartão errado sempre que um marcador
# genérico de uma regra aparecia numa questão de outra. Medido contra 1070
# questões do banco offline: 117 das 1070 (11%) iam para o cartão errado.
#
# A regra passou a ser "quem casar MAIS marcadores", com a ordem servindo só
# de desempate. Os casos abaixo são os que a medição encontrou.


@pytest.mark.parametrize(
    "materia, pergunta, esperado, ladrao",
    [
        # "base" é marcador da regra de ÁREA (base do triângulo) e da de pH
        # (base como álcali). A de área vem antes.
        (
            "Quimica", "Uma base forte tem pH acima de 7. Calcule o pOH.",
            "pH", "área",
        ),
        # "massa" (força) está contido em "massa molar" (mol).
        (
            "Quimica", "Calcule a massa molar na estequiometria da reacao.",
            "mol", "força",
        ),
        # Um template do banco escreve "M = 44 g/mol" em vez de "massa molar",
        # e aí o mol empatava com força em 1 a 1. Foi o que "g/mol" resolveu.
        (
            "Quimica", "Qual massa corresponde a 23 mol de substancia com M = 44 g/mol?",
            "mol", "força",
        ),
        # "m/s" (velocidade) está contido em "m/s^2", que é unidade de
        # ACELERAÇÃO. 36 questões de força recebiam o cartão de velocidade.
        (
            "Fisica",
            "Um corpo de 4 kg com massa conhecida acelera a 3 m/s^2. Qual a forca em newton?",
            "força", "velocidade",
        ),
    ],
)
def test_a_regra_com_mais_marcadores_vence_a_que_vem_antes(materia, pergunta, esperado, ladrao):
    titulo = titulo_de(pergunta, materia)

    assert esperado in titulo, f"esperava {esperado!r}, veio {titulo!r}"
    assert ladrao not in titulo


def test_o_empate_continua_decidido_pela_ordem():
    """É o que preserva o comportamento de hoje onde não há sinal melhor.

    "mola" contém "mol", então a regra de mol casa 1; a de força casa 1 por
    "forca". Empatadas, vence a que vem antes -- força, como já vencia.
    """
    assert "força" in titulo_de("Uma mola comprime sob forca de 10 N.", "Fisica")


def test_uma_regra_so_vence_com_mais_marcadores_e_nao_com_marcador_maior():
    """A alternativa que foi medida e descartada.

    Escolher pelo marcador mais LONGO parecia razoável e é pior: "concentracao"
    tem 12 letras e "ph" tem 2, então toda questão de pH viraria concentração
    e o cartão de pH ficaria inalcançável.
    """
    assert "pH" in titulo_de("Calcule o pH de uma solucao com [H+] = 10^-3.", "Quimica")


def test_as_sobreposicoes_de_marcador_estao_mapeadas():
    """Marcador de uma regra contido no de outra.

    Não é mais um defeito -- a contagem resolve --, mas continua sendo o sinal
    de que duas regras disputam o mesmo texto. Este teste falha quando aparecer
    uma sobreposição nova, para ela ser medida antes de entrar.
    """
    sobrepostos = set()
    for i, (marcadores_i, _, _) in enumerate(USOS_DIA_A_DIA_LABORATORIO):
        for j, (marcadores_j, _, _) in enumerate(USOS_DIA_A_DIA_LABORATORIO):
            if i >= j:
                continue
            for a in marcadores_i:
                for b in marcadores_j:
                    if a in b or b in a:
                        sobrepostos.add(min(a, b, key=len))

    assert sobrepostos == {"base", "massa"}, f"sobreposições inesperadas: {sobrepostos}"
