"""O resultado final que contradiz a conta, escondido atrás de um passo que só repete o valor.

A captura 08c das telas do TG (10/09/2026) mostrava "Acertou" com a resposta
errada. A questão do Hugging Face tinha:

    2º Passo         v = 0 + 3 · 6 = 18
    3º Passo         v = 18 m/s
    Resultado Final  15 m/s          e 15 m/s marcado como certo

`passo-final-diverge-do-calculo-anterior` comparava o final só com o passo
IMEDIATAMENTE anterior, e só quando ele era uma conta: o 3º passo, que apenas
repete o 18, desligava a checagem. Agora a regra volta por cima dos passos que
só repetem o valor até achar a conta.

Medido antes de mexer (16/09/2026): 14.750 questões offline de exatas, 36
respondidas por alunos, 6 inteiras do Render e 19 da IA vistas na sessão --
nenhuma mudou de veredito, só os casos da 08c passaram a ser recusados.
"""
from __future__ import annotations

import copy

import pytest

from services.ia.validacao import (
    _deve_pular_comparacao_numerica,
    _passo_final_diverge_do_calculo_anterior,
    _remover_variaveis_com_indice,
    _valor_do_passo_final,
    _valor_e_operador_do_passo,
    _valor_so_repetido,
    validar_questao_gerada,
)

BARRA = chr(92)
CONTEXTOS = ["oraculo", "laboratorio"]


def passo(titulo: str, conteudo: str, final: bool = False) -> dict:
    return {"titulo": titulo, "conteudo": conteudo, "final": final}


def questao_da_08c(resultado_final: str = "15 m/s", marcada: int = 2) -> dict:
    """A questão da captura, como o Hugging Face a mandou."""
    return {
        "pergunta": (
            "Um carro parte do repouso com aceleração constante de 3 m/s². "
            "Após 6 segundos, qual a velocidade final atingida?"
        ),
        "opcoes": ["18 m/s", "10 m/s", "15 m/s", "12 m/s"],
        "correta": marcada,
        "formula": f"v = v_0 + a {BARRA}cdot t",
        "subformulas": [],
        "legenda_variaveis": (
            "v = velocidade final (m/s), v_0 = velocidade inicial (m/s), "
            "a = aceleração (m/s²), t = tempo (s)"
        ),
        "passos_resolucao": [
            passo("1º Passo", "v_0 = 0, a = 3, t = 6"),
            passo("2º Passo", f"v = 0 + 3 {BARRA}cdot 6 = 18"),
            passo("3º Passo", "v = 18 m/s"),
            passo("Resultado Final", resultado_final, final=True),
        ],
        "explicacao": [{
            "tipo": "resultado",
            "conteudo": "A velocidade final e a soma da velocidade inicial com o produto da aceleracao pelo tempo decorrido.",
        }],
    }


def passos(*conteudos: str) -> dict:
    lista = [{"conteudo": c} for c in conteudos]
    lista[-1]["final"] = True
    return {"passos_resolucao": lista}


# ====================== A QUESTÃO DA CAPTURA ======================


@pytest.mark.parametrize("contexto", CONTEXTOS)
def test_a_questao_da_captura_e_recusada(contexto):
    _, aceita, motivo = validar_questao_gerada(questao_da_08c(), "Fisica", contexto)

    assert not aceita
    assert motivo == "passo-final-diverge-do-calculo-anterior"


@pytest.mark.parametrize("contexto", CONTEXTOS)
def test_a_mesma_questao_com_a_conta_certa_passa(contexto):
    """O par: com 18 no final e 18 marcado, a questão continua aceita."""
    certa = questao_da_08c("18 m/s", marcada=0)

    _, aceita, motivo = validar_questao_gerada(certa, "Fisica", contexto)

    assert aceita, motivo


# ====================== O CAMINHO NOVO ======================


@pytest.mark.parametrize(
    "conteudos, rotulo",
    [
        (("v = 0 + 3 * 6 = 18", "v = 18 m/s", "15 m/s"), "um passo repetindo o 18"),
        (("v = 0 + 3 * 6 = 18", "v = 18 m/s", "v = 18,0 m/s", "15 m/s"), "dois passos repetindo"),
        (("a = 30 / 10 = 3", "a = 3 m/s²", "3,5 m/s²"), "unidade ao quadrado no passo repetido"),
        (("d = 12 * 5", "d = 60 km", "d = 50 km"), "conta sem '=' antes da repetição"),
    ],
)
def test_o_final_errado_atras_da_repeticao_e_pego(conteudos, rotulo):
    assert _passo_final_diverge_do_calculo_anterior(passos(*conteudos)), rotulo


@pytest.mark.parametrize(
    "conteudos, rotulo",
    [
        (("v = 0 + 3 * 6 = 18", "v = 18 m/s", "18 m/s"), "um passo repetindo o 18"),
        (("v = 0 + 3 * 6 = 18", "v = 18 m/s", "v = 18,0 m/s", "v = 18 m/s"), "dois passos repetindo"),
        (("a = 30 / 10 = 3", "a = 3 m/s²", "3 m/s²"), "unidade ao quadrado no passo repetido"),
        (("d = 12 * 5", "d = 60 km", "d = 60 km"), "conta sem '=' antes da repetição"),
    ],
)
def test_o_final_certo_atras_da_repeticao_passa(conteudos, rotulo):
    """Cada caso pego acima tem aqui o seu par certo."""
    assert not _passo_final_diverge_do_calculo_anterior(passos(*conteudos)), rotulo


@pytest.mark.parametrize(
    "conteudos, rotulo",
    [
        (("v = 0 + 3 * 6 = 18", "t = 6 s", "15 m/s"), "passo com OUTRO número pode ser outra grandeza"),
        (("t = 2 * 3 = 6", "a = 3, t = 6", "v = 20"), "dois valores no passo não são repetição"),
        (("v = 0 + 3 * 6 = 18", "v = 18 m/s (64,8 km/h)", "64,8 km/h"), "conversão no passo do meio"),
        (("v = 0 + 3 * 6 = 18", "Agora converta para km/h", "64,8 km/h"), "passo sem número"),
        (("v = 0 + 3 * 6 = 18", "v = 0 + 3 * 6 m/s", "15 m/s"), "conta que o verificador não avalia"),
    ],
)
def test_na_duvida_a_regra_nao_recusa(conteudos, rotulo):
    """Recusar questão certa empurra a aula para o banco offline. Quando o
    passo do meio não é, com certeza, a repetição do resultado da conta, a
    regra desiste -- como fazia antes."""
    assert not _passo_final_diverge_do_calculo_anterior(passos(*conteudos)), rotulo


# ====================== O VALOR QUE O PASSO SÓ REPETE ======================


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("v = 18 m/s", 18.0),
        ("18 m/s", 18.0),
        ("a = 3 m/s²", 3.0),
        ("A = 48 m^2", 48.0),
        ("v = -2,5 m/s", -2.5),
    ],
)
def test_o_valor_repetido_e_lido(texto, esperado):
    assert _valor_so_repetido(texto) == pytest.approx(esperado)


@pytest.mark.parametrize(
    "texto",
    ["a = 3, t = 6", "x = 2 + 3 = 5", "v = 18 m/s (64,8 km/h)", "Vertice = (3, 4)", "Resposta final"],
)
def test_o_que_nao_e_so_repeticao_nao_tem_valor(texto):
    assert _valor_so_repetido(texto) is None


# ====================== OS BANCOS COM UM PASSO REPETIDO INSERIDO ======================


def _questoes_de_exatas():
    import services.banks.em as em
    import services.banks.fundamental as ef
    import services.banks.laboratorio as lab
    import services.banks.rpg as rp

    exatas = {"Matematica", "Fisica", "Quimica"}
    for materia in em.MATERIAS:
        if materia in exatas:
            yield from em.listar_questoes_em(materia)
    for materia in ef.MATERIAS:
        if materia in exatas:
            yield from ef.listar_questoes_ef(materia)
    for materia in rp.MATERIAS:
        if materia in exatas:
            yield from rp.listar_questoes_rpg(materia)
    for materia in lab.MATERIAS_LAB_OFFLINE:
        yield from lab.listar_questoes_laboratorio(materia, "EM")
    for materia in lab.MATERIAS_LAB_EF_OFFLINE:
        yield from lab.listar_questoes_laboratorio(materia, "EF")


def _com_passo_repetido(questao: dict, final: str | None = None) -> dict | None:
    """A questão com "x = <resultado da conta>" entre a conta e o final.

    None quando a regra não compara o final com o passo anterior: ele não é
    uma conta que ela lê, ou a comparação é pulada (raiz, log, "±").
    """
    lista = [
        copy.deepcopy(p)
        for p in (questao.get("passos_resolucao") or [])
        if isinstance(p, dict) and str(p.get("conteudo", "")).strip()
    ]
    if len(lista) < 2 or not lista[-1].get("final"):
        return None
    anterior = _remover_variaveis_com_indice(lista[-2]["conteudo"])
    ultimo = _remover_variaveis_com_indice(lista[-1]["conteudo"])
    valor, eh_conta = _valor_e_operador_do_passo(anterior)
    if (
        not eh_conta
        or valor is None
        or _deve_pular_comparacao_numerica(anterior, ultimo)
        or _valor_do_passo_final(ultimo) is None
        or _passo_final_diverge_do_calculo_anterior({"passos_resolucao": lista})
    ):
        return None
    repetido = f"{valor:.6f}".rstrip("0").rstrip(".").replace(".", ",")
    lista.insert(-1, {"conteudo": f"x = {repetido}"})
    if final is not None:
        lista[-1]["conteudo"] = final
    return {"passos_resolucao": lista}


def test_um_passo_repetido_nao_muda_o_veredito_das_questoes_do_banco():
    """Os bancos quase não têm passo que só repete o valor, então a medição
    dele sozinha não diz nada sobre o caminho novo. Inserindo um, cada questão
    certa tem de continuar aceita -- e, com o final trocado, ser recusada."""
    comparadas = 0
    for questao in _questoes_de_exatas():
        certa = _com_passo_repetido(questao)
        if certa is None:
            continue
        comparadas += 1
        assert not _passo_final_diverge_do_calculo_anterior(certa), certa
        errada = _com_passo_repetido(questao, final="999999")
        assert _passo_final_diverge_do_calculo_anterior(errada), errada

    assert comparadas > 1000
