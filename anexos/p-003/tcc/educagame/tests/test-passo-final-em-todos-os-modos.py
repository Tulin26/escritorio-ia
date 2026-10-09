"""O passo final que não bate com o anterior passa a ser pego nos cinco modos.

MELHORIA: `passo-final-diverge-do-calculo-anterior` valia **só no
Laboratório**. Com a guarda `contexto != "oraculo"`, uma questão com

    d = 12 * 5
    d = 50

era **aceita** no Treino, no Oráculo, no Escape Room e no RPG, e recusada só
no Laboratório. É o mesmo erro que ela existe para pegar, e os quatro modos
estavam descobertos.

A guarda tinha motivo: medida contra os bancos offline, a checagem recusava
**228 das 14.310** questões de exatas (1,6%). Mas as 228 eram falso positivo
do **verificador**, não defeito das questões — ele lia o número errado do
passo final em quatro formatos:

| passo final | lia | devia ler |
|---|---|---|
| `A = 48 m^2` | 2 — o expoente da **unidade** | 48 |
| `V = 125 cm^3` | 3 | 125 |
| `P = 3/10` | 10 — o **denominador** | 0,3 |
| `Vertice = (3, 4)` | 4 | nada: par ordenado não é um número |

e mais `log_2(4) = 2`, que era tratado como aritmética comum porque `"log("`
não casa com `"log_2("` — a mesma armadilha do `_` já corrigida em
`_FUNCAO_APROXIMADA`.

Corrigidos os quatro, a medição foi a **zero** e a guarda deixou de ter
motivo. Todas as 228 vinham do Laboratório, onde a checagem já estava ligada.

A outra checagem desligada, `exatas-sem-estrutura`, **continua desligada de
propósito** — ver `test_estrutura_de_exatas_continua_so_no_laboratorio`.
"""

from __future__ import annotations

import copy

import pytest

from services.ia.validacao import (
    _passo_final_diverge_do_calculo_anterior,
    _resposta_exatas_sem_estrutura,
    _valor_do_passo_final,
    validar_questao_gerada,
)

BARRA = chr(92)
CONTEXTOS = ["oraculo", "laboratorio"]


def passos(*conteudos: str) -> dict:
    lista = [{"conteudo": c} for c in conteudos]
    lista[-1]["final"] = True
    return {"passos_resolucao": lista}


def questao(final: str, alternativa: str, anterior: str = "d = 12 * 5") -> dict:
    return {
        "pergunta": "Um carro percorre 12 km em cada uma das 5 horas. Qual a distância total, em km?",
        "opcoes": [alternativa, "70", "80", "90"],
        "correta": 0,
        "formula": f"d = v {BARRA}cdot t",
        "passos_resolucao": [
            {"titulo": "1º Passo", "conteudo": anterior},
            {"titulo": "Resultado Final", "conteudo": final, "final": True},
        ],
        "explicacao": [{"tipo": "texto", "conteudo": "Multiplique a velocidade pelo tempo."}],
    }


# ====================== A CHECAGEM VALE EM TODOS OS MODOS ======================


@pytest.mark.parametrize("contexto", CONTEXTOS)
def test_o_passo_final_errado_e_recusado_em_todos_os_modos(contexto):
    """Os cinco modos passam por um de dois contextos: o Laboratório usa
    "laboratorio"; Treino, Oráculo, Escape Room e RPG usam "oraculo".
    """
    _, aceita, motivo = validar_questao_gerada(questao("d = 50", "50"), "Matematica", contexto)

    assert not aceita
    assert motivo == "passo-final-diverge-do-calculo-anterior"


@pytest.mark.parametrize("contexto", CONTEXTOS)
def test_a_conta_certa_passa_em_todos_os_modos(contexto):
    """O par obrigatório: uma regra que recusa tudo não serve de nada."""
    _, aceita, motivo = validar_questao_gerada(questao("d = 60", "60"), "Matematica", contexto)

    assert aceita, motivo


# ====================== O NÚMERO QUE O PASSO FINAL AFIRMA ======================


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("A = 48 m^2", 48.0),
        ("A = 48 m²", 48.0),
        ("V = 125 cm^3", 125.0),
        ("64 cm^3", 64.0),
        ("A = 22,5 cm^2", 22.5),
        ("F = 20 N", 20.0),
        ("d = 12 km", 12.0),
        ("v = 3,5 m/s", 3.5),
        ("h = 86,6 metros", 86.6),
    ],
)
def test_o_expoente_da_unidade_nao_e_confundido_com_o_resultado(texto, esperado):
    """O defeito mais grosseiro dos quatro: em "A = 48 m^2" o último número
    do texto é o **2** do metro quadrado.
    """
    assert _valor_do_passo_final(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("texto,esperado", [("P = 3/10", 0.3), ("6/22", 6 / 22)])
def test_a_fracao_e_avaliada_e_nao_lida_pelo_denominador(texto, esperado):
    assert _valor_do_passo_final(texto) == pytest.approx(esperado)


def test_o_par_ordenado_nao_e_julgado():
    """`Vertice = (3, 4)` é um ponto, não um valor — não há o que comparar
    com o passo anterior."""
    assert _valor_do_passo_final("Vertice = (3, 4).") is None


def test_o_expoente_matematico_continua_valendo():
    """A correção só ignora o expoente quando ele vem depois de uma unidade.
    Em "2^3 = 8" o expoente é da conta, e o resultado é 8."""
    assert _valor_do_passo_final("2^3 = 8") == pytest.approx(8.0)


@pytest.mark.parametrize("texto,esperado", [("5^2", 25.0), ("2^3", 8.0), ("4^3", 64.0)])
def test_potencia_sozinha_no_passo_final_e_calculada(texto, esperado):
    """O caso que exige a letra no regex do expoente de unidade. Com "5^2"
    sozinho (sem "=" para isolar o lado direito), um regex que aceitasse
    expoente sem unidade antes leria **5** em vez de 25 — um mutante mostrou
    que sem este teste a exigência de letra podia ser afrouxada sem que nada
    reclamasse.
    """
    assert _valor_do_passo_final(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("texto,esperado", [("F = 20 N", 20.0), ("v = 3,5 m/s", 3.5)])
def test_a_unidade_sem_expoente_nao_precisa_de_tratamento(texto, esperado):
    """A barra de "m/s" não vira divisão nem a letra vira número: o avaliador
    já descarta letra sozinho. Só o expoente da unidade atrapalhava."""
    assert _valor_do_passo_final(texto) == pytest.approx(esperado)


# ====================== OS QUATRO FORMATOS QUE ERAM FALSO POSITIVO ======================


@pytest.mark.parametrize(
    "anterior,final,rotulo",
    [
        ("A = 6 * 8 = 48", "A = 48 m^2", "área com unidade ao quadrado"),
        ("V = 5^3 = 125", "125 cm^3", "volume com unidade ao cubo"),
        (f"P = {BARRA}frac{{3}}{{10}}", "P = 3/10", "probabilidade como fração"),
        ("Compare f(x) = (x - 3)^2 + 4 com f(x)=a(x-h)^2+k.", "Vertice = (3, 4).", "par ordenado"),
        ("2^2 = 4.", "log_2(4) = 2", "logaritmo com base escrita"),
    ],
)
def test_os_formatos_legitimos_do_banco_deixam_de_ser_recusados(anterior, final, rotulo):
    assert not _passo_final_diverge_do_calculo_anterior(passos(anterior, final)), rotulo


@pytest.mark.parametrize(
    "anterior,final,rotulo",
    [
        ("20 N - 15 N - 98 N", "5 N", "o caso original: 20-15-98 = -93, não 5"),
        ("d = 12 * 5", "d = 50", "12x5 = 60, não 50"),
        ("A = 6 * 8 = 48", "A = 50 m^2", "48 != 50, mesmo com unidade"),
        (f"P = {BARRA}frac{{3}}{{10}}", "P = 4/10", "0,3 != 0,4, mesmo em fração"),
        ("V = 5^3 = 125", "V = 130 cm^3", "125 != 130, mesmo com expoente de unidade"),
    ],
)
def test_o_erro_de_verdade_continua_sendo_pego(anterior, final, rotulo):
    """A correção não pode ter desligado a checagem por acidente — cada
    formato consertado tem aqui o seu par errado."""
    assert _passo_final_diverge_do_calculo_anterior(passos(anterior, final)), rotulo


# ====================== A MEDIÇÃO QUE AUTORIZOU LIGAR ======================


def test_nenhuma_questao_offline_de_exatas_e_recusada():
    """Era 228 de 14.310 (1,6%). Uma validação que erra joga fora questão boa
    e empurra a aula para o banco offline sem necessidade — por isso a
    checagem só pôde ser ligada nos outros modos depois de zerar isto.
    """
    import services.banks.em as em
    import services.banks.fundamental as ef
    import services.banks.laboratorio as lab
    import services.banks.rpg as rp

    exatas = {"Matematica", "Fisica", "Quimica"}

    def todas():
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
            if materia in exatas:
                yield from lab.listar_questoes_laboratorio(materia, "EM")
        for materia in lab.MATERIAS_LAB_EF_OFFLINE:
            if materia in exatas:
                yield from lab.listar_questoes_laboratorio(materia, "EF")

    recusadas = [q for q in todas() if _passo_final_diverge_do_calculo_anterior(q)]

    assert not recusadas, f"{len(recusadas)} questões offline boas seriam recusadas"


# ====================== A OUTRA GUARDA CONTINUA, E POR QUÊ ======================


def test_estrutura_de_exatas_continua_so_no_laboratorio():
    """`exatas-sem-estrutura` exige fórmula, subfórmula **ou** passos. Medido
    por banco, a divisão é limpa:

        EM / EF / RPG (conceituais)  100% sem estrutura
        Laboratório                    0% sem estrutura

    Não é defeito do verificador como as 228 acima — é design. O Oráculo
    **apaga** fórmula e passos logo depois de validar
    (`_normalizar_questao_oraculo`: "No Oraculo, exatas e conceitual; conta
    com formula e passo a passo e o Laboratorio"). Exigi-los fora do
    Laboratório seria cobrar exatamente o que o código descarta em seguida.
    """
    conceitual = {
        "pergunta": "O que a Segunda Lei de Newton relaciona?",
        "opcoes": ["Força, massa e aceleração", "Só massa", "Só força", "Nada"],
        "correta": 0,
        "explicacao": [{"tipo": "texto", "conteudo": "Ela liga força, massa e aceleração."}],
    }

    assert _resposta_exatas_sem_estrutura(conceitual)

    _, aceita_no_oraculo, _ = validar_questao_gerada(
        copy.deepcopy(conceitual), "Fisica", "oraculo"
    )
    _, aceita_no_lab, motivo_lab = validar_questao_gerada(
        copy.deepcopy(conceitual), "Fisica", "laboratorio"
    )

    assert aceita_no_oraculo, "questão conceitual de exatas é o normal no Oráculo"
    assert not aceita_no_lab
    assert motivo_lab == "exatas-sem-estrutura"
