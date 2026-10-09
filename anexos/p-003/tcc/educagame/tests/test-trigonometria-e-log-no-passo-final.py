"""seno, cosseno, tangente e log no passo final também passam a ser conferidos.

MELHORIA: mesma cegueira do passo final com raiz (ver
`test_raiz_no_passo_final.py`), aplicada ao resto da lista de funções
transcendentes. `sin`, `cos`, `tan` e `log` também fazem o passo inteiro ser
**pulado** na comparação numérica — e é nele que a resposta nasce em
trigonometria e em logaritmo.

A armadilha aqui é **grau × radiano**, e ela é severa: `sin(30)` vale 0,5 em
graus e −0,988 em radianos. O Ensino Médio brasileiro trabalha em graus, mas
a IA às vezes escreve o ângulo em radianos (`π/6`). A mesma ambiguidade
existe em `log` sem base: `log(100)` pode ser 2 (decimal, o padrão da
escola), 4,605 (natural) ou 6,64 (base 2).

Por isso a regra recusa **somente quando nenhuma leitura plausível fecha**.
Se a conta bate em graus OU em radianos, ou em qualquer base de log
razoável, ela passa. Recusar só o indefensável é de propósito: uma validação
que erra joga fora questão boa e empurra a aula para o banco offline sem
necessidade.

Medido: das 50.900 questões offline, 64 têm o padrão nos passos e **nenhuma**
seria recusada.
"""

from __future__ import annotations

import pytest

from services.ia.validacao import (
    _expressao_com_funcao_diverge,
    _funcao_aproximada_incorreta,
    _leituras_da_expressao,
    validar_questao_gerada,
)

BARRA = chr(92)


def com_passo(conteudo: str) -> dict:
    return {"passos_resolucao": [{"titulo": "Resultado Final", "conteudo": conteudo, "final": True}]}


def questao_ph(expoente: int, resultado: str) -> dict:
    """A forma real do banco de Química: pH = -log([H+])."""
    return {
        "pergunta": f"Em um controle de qualidade, se [H+] = 10^{{-{expoente}}} mol/L, qual o pH da solução?",
        "opcoes": [resultado, "1", "14", "0"],
        "correta": 0,
        "formula": f"pH = -{BARRA}log([H^+])",
        "passos_resolucao": [
            {"titulo": "1º Passo", "conteudo": f"[H^+] = 10^{{-{expoente}}}"},
            {"titulo": "Resultado Final", "conteudo": f"pH = -{BARRA}log(10^{{-{expoente}}}) = {resultado}", "final": True},
        ],
        "explicacao": [{"tipo": "texto", "conteudo": "Aplicando a definição de pH."}],
    }


# ====================== TRIGONOMETRIA — GRAUS ======================


@pytest.mark.parametrize(
    "texto",
    [
        "sen(30°) = 0,5",
        "sin(30°) = 0,5",
        f"{BARRA}sin(30^{{o}}) = 0,5",
        "cos(60 graus) = 0,5",
        "tg(45°) = 1",
    ],
)
def test_o_seno_e_cosseno_em_graus_certos_passam(texto):
    assert not _funcao_aproximada_incorreta(com_passo(texto))


@pytest.mark.parametrize(
    "texto",
    [
        "sen(30°) = 0,87",
        "cos(60°) = 0,87",
        "tg(45°) = 2",
        "cos(0°) = 0",
        "sen(90°) = 0",
    ],
)
def test_o_seno_e_cosseno_em_graus_errados_sao_recusados(texto):
    assert _funcao_aproximada_incorreta(com_passo(texto))


def test_arredondamento_para_tres_casas_e_aceito():
    """sen(60°) = 0,866025... — a escola escreve 0,87 ou 0,866. Uma
    tolerância fixa recusaria o arredondamento honesto.
    """
    assert not _funcao_aproximada_incorreta(com_passo("sen(60°) ≈ 0,87"))
    assert not _funcao_aproximada_incorreta(com_passo("cos(30°) ≈ 0,866"))
    assert not _funcao_aproximada_incorreta(com_passo("tan(60°) ≈ 1,73"))


# ====================== A AMBIGUIDADE GRAU × RADIANO ======================


def test_sem_marca_de_grau_a_leitura_em_radianos_tambem_vale():
    """A IA às vezes escreve o ângulo sem `°`. Sem saber se é grau ou
    radiano, as duas leituras são aceitas — recusar aqui seria inventar um
    erro que não se sabe que existe.
    """
    assert not _funcao_aproximada_incorreta(com_passo("sen(30) = 0,5"))     # leitura em graus
    assert not _funcao_aproximada_incorreta(com_passo("sin(1) ≈ 0,84"))     # leitura em radianos


def test_com_pi_a_leitura_e_so_em_radianos():
    assert not _funcao_aproximada_incorreta(com_passo(f"sen({BARRA}frac{{{BARRA}pi}}{{6}}) = 0,5"))
    assert not _funcao_aproximada_incorreta(com_passo("cos(π/3) = 0,5"))


def test_angulo_indefinido_nao_e_julgado():
    """tan(90°) estoura. Sem valor de referência, não há erro para provar."""
    assert not _funcao_aproximada_incorreta(com_passo("tan(90°) = 0"))


def test_argumento_com_incognita_nao_e_julgado():
    assert not _funcao_aproximada_incorreta(com_passo("sen(x) = 0,5"))


# ====================== LOGARITMO ======================


@pytest.mark.parametrize(
    "texto",
    [
        f"{BARRA}log_{{2}}(8) = 3",
        "log_2(8) = 3",
        "log(100) = 2",
        "ln(100) ≈ 4,61",
        "log(8) ≈ 0,9",
        "log(1000) = 3",
    ],
)
def test_log_certo_em_qualquer_base_plausivel_passa(texto):
    assert not _funcao_aproximada_incorreta(com_passo(texto))


@pytest.mark.parametrize(
    "texto",
    [
        "log(100) = 3",
        f"{BARRA}log_{{2}}(8) = 4",
        "log_2(8) = 4",
        "ln(100) ≈ 2",
    ],
)
def test_log_errado_em_toda_base_e_recusado(texto):
    assert _funcao_aproximada_incorreta(com_passo(texto))


def test_log_de_numero_nao_positivo_nao_e_julgado():
    """log(0) e log de negativo não existem — sem um valor de referência para
    comparar, a resposta certa é "não julgar", não recusar."""
    assert not _funcao_aproximada_incorreta(com_passo("log(0) = 0"))
    assert not _funcao_aproximada_incorreta(com_passo("log(-5) = 1"))


def test_a_base_com_indice_e_lida_mesmo_sem_barra_de_palavra():
    """"_" é caractere de palavra: um `\\b` entre "log" e "_{2}" não existe.
    Sem o lookahead certo, a forma com base escrita nunca casava, e
    `\\log_{2}(8) = 4` passava incontestado.
    """
    assert _funcao_aproximada_incorreta(com_passo(f"{BARRA}log_{{2}}(8) = 4"))
    assert not _funcao_aproximada_incorreta(com_passo(f"{BARRA}log_{{2}}(8) = 3"))


# ====================== O SINAL ANTES DA FUNÇÃO ======================


def test_o_sinal_de_menos_antes_do_log_muda_o_resultado_esperado():
    """`pH = -log(10^-3) = 3` é a fórmula real de 8 questões do banco de
    Química offline. Sem capturar o sinal antes da função, log10(0,001) =
    −3 era comparado direto com o "3" escrito, e as 8 seriam recusadas —
    todas verdadeiras, só o sinal ficava de fora da conta.
    """
    assert not _funcao_aproximada_incorreta(com_passo(f"pH = -{BARRA}log(10^{{-3}}) = 3"))
    assert not _funcao_aproximada_incorreta(com_passo("pH = -log(10^-9) = 9"))
    assert _funcao_aproximada_incorreta(com_passo("pH = -log(10^-3) = 4"))


@pytest.mark.parametrize("expoente", [3, 4, 5, 6, 7, 8, 9, 10])
def test_todas_as_questoes_reais_de_ph_do_banco_passam(expoente):
    assert not _funcao_aproximada_incorreta(questao_ph(expoente, str(expoente)))


def test_expoente_em_sobrescrito_unicode_e_resolvido():
    """O banco de Química escreve "10⁻³", não "10^{-3}". Sem resolver, "⁻³"
    não é letra (passa pelo filtro de incógnita) nem dígito ASCII — o
    normalizador que avalia a expressão apagava os dois caracteres em
    silêncio e "10⁻³" virava só "10": achado ao vivo, recusava 20 das 8
    questões reais de pH do banco offline (todas verdadeiras).
    """
    assert not _funcao_aproximada_incorreta(com_passo("pH = -log(10⁻³) = 3."))
    assert not _funcao_aproximada_incorreta(com_passo("pH = -log(10⁻⁹) = 9."))
    assert _funcao_aproximada_incorreta(com_passo("pH = -log(10⁻³) = 4."))


def test_a_soma_de_logaritmos_sem_parenteses_nao_e_mutilada():
    """O template real do banco: "log 6 = log 2 + log 3 ≈ 0,30 + 0,48 =
    0,78" não usa parênteses. O argumento capturado do primeiro "log" (regex
    gulosa até o próximo "=" ou "≈") engolia "log 3" inteiro, e
    `_avaliar_expressao_numerica` apagava a letra em silêncio: "2 + log 3"
    virava "2 + 3" = 5, mutilação que não tem relação com o log de nada.
    """
    assert not _funcao_aproximada_incorreta(
        com_passo("log 6 = log 2 + log 3 ≈ 0,30 + 0,48 = 0,78.")
    )


# ====================== A FUNÇÃO COM COEFICIENTE NA FRENTE ======================


@pytest.mark.parametrize(
    "texto",
    [
        f"h = 50 {BARRA}cdot tan(60) = 86,6",
        f"h = 50 {BARRA}cdot tan(60°) = 86,6",
        "d = 2 * sen(30°) = 1",
        "x = 3 * cos(60°) = 1,5",
        "A = 2 * log(100) = 4",
    ],
)
def test_a_funcao_multiplicada_com_resultado_certo_passa(texto):
    """"h = 50 · tan(60°) = 86,6" é fórmula real (trigonometria aplicada).
    tan(60°) sozinho vale 1,73, não 86,6 — o resultado inclui a multiplicação
    por 50, e a checagem precisa resolver a função **dentro** da expressão
    para julgar o todo.
    """
    assert not _funcao_aproximada_incorreta(com_passo(texto))


@pytest.mark.parametrize(
    "texto",
    [
        f"h = 50 {BARRA}cdot tan(60) = 999,9",
        "d = 2 * sen(30°) = 7",
        "h = 50 * tan(60 graus) = 43,3",
        "A = 2 * log(100) = 30",
    ],
)
def test_a_funcao_multiplicada_com_resultado_errado_e_recusada(texto):
    """O buraco que ficou aberto quando a checagem nasceu: com coeficiente na
    frente ela se desligava inteira, e `50 · tan(60°) = 999,9` passava.
    """
    assert _funcao_aproximada_incorreta(com_passo(texto))


def test_a_ambiguidade_vale_tambem_dentro_da_expressao():
    """`2 · log(100)` dá 4 em log decimal e 9,21 em natural. Escrever "9" é
    defensável (meia unidade na casa mostrada), e por isso passa — a regra de
    "só recusa quando nenhuma leitura fecha" não pode se perder ao avaliar a
    expressão inteira.
    """
    assert not _funcao_aproximada_incorreta(com_passo("A = 2 * log(100) = 9"))


def test_funcao_com_incognita_dentro_de_expressao_nao_e_julgada():
    assert not _funcao_aproximada_incorreta(com_passo("y = 2 * sen(x) = 4"))


def test_a_expressao_e_recortada_no_ultimo_igual():
    """Com dois "=" do lado esquerdo, avaliar tudo cola os números vizinhos:
    o normalizador apaga o "=" e `5 + 2 = 7 · tan(30)` vira `5+27·tan(30)`
    — 20,59 em vez de 4,04. O recorte no último "=" é o que evita esse
    número fantasma.
    """
    assert not _funcao_aproximada_incorreta(
        com_passo(f"x = 5 + 2 = 7 {BARRA}cdot tan(30) = 4,04")
    )
    assert _funcao_aproximada_incorreta(
        com_passo(f"x = 5 + 2 = 7 {BARRA}cdot tan(30) = 20,59")
    )


def test_linha_sem_resultado_declarado_nao_e_julgada():
    """Sem `=` nem `≈` a linha não afirma resultado nenhum.

    Chama `_expressao_com_funcao_diverge` **direto**, e não pela cascata: por
    ela o regex nem casa uma linha sem resultado, então a guarda ficaria
    inalcançável e o teste provaria nada — foi o que um mutante mostrou.
    Sem a guarda, a função estoura no `separadores[-1]`.
    """
    linha = f"50 {BARRA}cdot tan(60)"

    assert not _expressao_com_funcao_diverge(linha, len(linha))
    assert not _funcao_aproximada_incorreta(com_passo(linha))


def test_a_expressao_e_partida_no_aproximado_tambem_e_nao_so_no_igual():
    """A IA escreve "50 · tan(60) ≈ 86,6" sem `=` nenhum. Partindo só no `=`,
    a linha inteira virava o "resultado" e o caso escapava — um mutante
    mostrou que `50 · tan(60) ≈ 999,9` passava incontestado.
    """
    assert _funcao_aproximada_incorreta(com_passo(f"50 {BARRA}cdot tan(60) ≈ 999,9"))
    assert not _funcao_aproximada_incorreta(com_passo(f"50 {BARRA}cdot tan(60) ≈ 86,6"))


def test_a_tolerancia_segue_a_casa_mostrada_tambem_na_expressao():
    """50 · tan(60°) = 86,60. Com uma casa decimal a tolerância é 0,05:
    "86,6" passa e "87,2" não. Uma tolerância fixa e larga deixaria as duas
    passarem.
    """
    assert not _funcao_aproximada_incorreta(com_passo(f"h = 50 {BARRA}cdot tan(60) = 86,6"))
    assert _funcao_aproximada_incorreta(com_passo(f"h = 50 {BARRA}cdot tan(60) = 87,2"))


def test_expressao_com_funcoes_demais_nao_e_julgada():
    """Cada função ambígua dobra o número de leituras (grau e radiano). Com
    cinco, seriam 32 combinações — e uma delas quase sempre bate por acaso,
    o que tornaria a checagem inútil em vez de segura. O teto corta em 16.
    """
    quatro = " + ".join(f"tan({10 * i})" for i in range(1, 5))
    cinco = " + ".join(f"tan({10 * i})" for i in range(1, 6))

    assert len(_leituras_da_expressao(quatro)) == 16
    assert _leituras_da_expressao(cinco) == []


def test_a_funcao_sozinha_continua_sendo_julgada():
    """O coeficiente só desativa a checagem quando ele existe de verdade —
    "tan(60°) = 999" continua indefensável."""
    assert _funcao_aproximada_incorreta(com_passo("tan(60°) = 999"))


# ====================== PALAVRAS QUE NÃO SÃO A FUNÇÃO ======================


@pytest.mark.parametrize(
    "texto",
    [
        "logaritmo de 100 e 2",
        "sinal trocado no resultado",
        "consequencia disso",
    ],
)
def test_palavras_que_comecam_como_a_funcao_nao_sao_capturadas(texto):
    """"logaritmo" não pode virar "log" + "aritmo", e "sinal" não pode casar
    dentro de "sin". O `\\b` original barrava isso; o lookahead que veio no
    lugar dele (para resolver `log_{2}`) precisa continuar barrando.
    """
    assert not _funcao_aproximada_incorreta(com_passo(texto))


# ====================== A CASCATA E OS BANCOS OFFLINE ======================


def test_a_questao_de_ph_errada_e_recusada_pela_cascata():
    ruim = questao_ph(3, "4")

    _, aceita, motivo = validar_questao_gerada(ruim, "Quimica", "laboratorio")

    assert not aceita
    assert motivo == "funcao-aproximada-incorreta"


def test_a_mesma_questao_certa_passa_pela_cascata():
    boa = questao_ph(3, "3")

    _, aceita, motivo = validar_questao_gerada(boa, "Quimica", "laboratorio")

    assert aceita, motivo


@pytest.mark.parametrize("contexto", ["oraculo", "laboratorio"])
def test_a_regra_vale_em_todos_os_modos(contexto):
    """Como a checagem de raiz: não leva guarda de contexto."""
    ruim = questao_ph(5, "6")

    _, aceita, motivo = validar_questao_gerada(ruim, "Quimica", contexto)

    assert not aceita
    assert motivo == "funcao-aproximada-incorreta"


def test_nenhuma_questao_offline_e_recusada_pela_regra_nova():
    """A medição que autorizou a mudança: 64 das 50.900 questões offline têm
    o padrão sin/cos/tan/log, e nenhuma é recusada.
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

    recusadas = [q for q in todas() if _funcao_aproximada_incorreta(q)]

    assert not recusadas, f"{len(recusadas)} questões offline boas seriam recusadas"


def test_questao_sem_passos_nao_quebra():
    assert not _funcao_aproximada_incorreta({})
    assert not _funcao_aproximada_incorreta({"passos_resolucao": None})
    assert not _funcao_aproximada_incorreta({"passos_resolucao": [None, "texto solto"]})
