"""Defeitos de LEITURA do validador do Laboratório.

Achados na investigação de 14/09/2026, reproduzindo as recusas reais do Render
e as 208 recusas do próprio banco (todas questões certas). Em nenhum destes
casos a regra julgava errado o que ela existe para julgar: ela lia errado o
texto -- o expoente da unidade como número, a unidade em LaTeX como ausente,
uma PG como PA, "retangular" como tangente.

Por isso cada teste vem em par: a questão certa passa, e a mesma questão com a
resposta errada continua recusada. Afrouxar a leitura não pode abrir a porta
para questão errada.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import math

import pytest

import services.banks.laboratorio as lab
import services.calculo_service as calc
import services.exatas_bank as exatas_bank
import services.ia_service as ia_service
from services.ia import validacao
from services.ia.validacao import validar_questao_gerada


def questao(pergunta, opcoes, formula, passos, resultado, correta=0, sub=None, legenda=""):
    return {
        "enigma": "x",
        "pergunta": pergunta,
        "opcoes": list(opcoes),
        "correta": correta,
        "formula": formula,
        "subformulas": sub or [],
        "legenda_variaveis": legenda,
        "explicacao": [
            {"tipo": "texto", "conteudo": "Substitua os valores na formula."},
            {"tipo": "resultado", "conteudo": resultado},
        ],
        "passos_resolucao": [
            {"titulo": f"{i + 1}º Passo", "conteudo": conteudo, "final": i == len(passos) - 1}
            for i, conteudo in enumerate(passos)
        ],
    }


def veredito(dados, materia):
    with contextlib.redirect_stdout(io.StringIO()):
        _, aceita, motivo = validar_questao_gerada(copy.deepcopy(dados), materia, "laboratorio")
    return "aceita" if aceita else motivo


def veredito_do_laboratorio(dados, materia):
    """A validação e, depois dela, a checagem extra do calculo_service."""
    motivo = veredito(dados, materia)
    if motivo != "aceita":
        return motivo
    with contextlib.redirect_stdout(io.StringIO()):
        parece = calc._desafio_parece_calculo_laboratorio(copy.deepcopy(dados), materia)
    return "aceita" if parece else "checagem-extra"


def do_banco(trecho, materia="Matematica"):
    return next(q for q in lab.listar_questoes_laboratorio(materia, "EM") if trecho in q["pergunta"])


def marcando_outra(dados, errada_idx):
    outra = copy.deepcopy(dados)
    outra["correta"] = errada_idx
    return outra


# --------------------------------------------------------------------------
# expoente da unidade
# --------------------------------------------------------------------------

def bloco(final, opcoes):
    return questao(
        "Um bloco de massa 5 kg está sujeito a uma força horizontal constante de 20 N. Qual a aceleração do bloco?",
        opcoes, r"F = m \cdot a",
        ["F = 20, m = 5", r"a = \frac{20}{5} = 4", final], final,
        legenda="F: forca; m: massa; a: aceleracao",
    )


UNIDADES_DE_ACELERACAO = ["m/s^2", r"\text{ m/s}^2", r"\;\text{m/s}^2", "m/s²"]


@pytest.mark.parametrize("unidade", UNIDADES_DE_ACELERACAO)
def test_o_expoente_da_unidade_nao_e_o_resultado(unidade):
    """Render, 11 e 13/09/2026: a = 4 m/s² recusado duas vezes."""
    certa = bloco(f"a = 4 {unidade}", ["4 m/s²", "2 m/s²", "100 m/s²", "0,25 m/s²"])

    assert veredito(certa, "Fisica") == "aceita"


@pytest.mark.parametrize("unidade", UNIDADES_DE_ACELERACAO)
def test_o_resultado_errado_com_unidade_continua_recusado(unidade):
    errada = bloco(f"a = 5 {unidade}", ["5 m/s²", "2 m/s²", "100 m/s²", "0,25 m/s²"])

    assert veredito(errada, "Fisica") != "aceita"


def test_a_mesma_area_com_expoente_escrito_de_dois_jeitos_nao_conflita():
    dados = {
        "passos_resolucao": [{"conteudo": "A = 60 cm²", "final": True}],
        "explicacao": [{"tipo": "resultado", "conteudo": "A = 60 cm^2"}],
    }

    assert not validacao._resultado_exatas_conflitante(dados)


def test_areas_diferentes_continuam_conflitando():
    dados = {
        "passos_resolucao": [{"conteudo": "A = 60 cm²", "final": True}],
        "explicacao": [{"tipo": "resultado", "conteudo": "A = 120 cm^2"}],
    }

    assert validacao._resultado_exatas_conflitante(dados)


def test_o_mesmo_numero_com_casa_decimal_diferente_nao_conflita():
    """Render, 30/09/2026: carrinho em MUV, questao certa recusada.

    O passo final escreveu "10,0" e o bloco resultado escreveu "10" -- o
    mesmo valor, duas notacoes. Comparado como texto, "10" != "10.0" e a
    questao caia em resultado-exatas-conflitante.
    """
    dados = {
        "passos_resolucao": [{"conteudo": r"v = 10,0\,\text{m/s}", "final": True}],
        "explicacao": [{"tipo": "resultado", "conteudo": r"v = 10\,\text{m/s}"}],
    }

    assert not validacao._resultado_exatas_conflitante(dados)


def test_numeros_realmente_diferentes_continuam_conflitando_com_decimal():
    dados = {
        "passos_resolucao": [{"conteudo": "v = 10,0 m/s", "final": True}],
        "explicacao": [{"tipo": "resultado", "conteudo": "v = 10,5 m/s"}],
    }

    assert validacao._resultado_exatas_conflitante(dados)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("4 m^2", "4 m"),
        ("4 m/s^2", "4 m/s"),
        ("20 kg/m^3", "20 kg/m"),
        ("4 m^{2}", "4 m"),
        # a chave depois do 2 é do \frac, não do expoente
        (r"\frac{70 N}{4 m^2}", r"\frac{70 N}{4 m}"),
        # variável, não unidade: o expoente é da conta
        ("2x^2", "2x^2"),
        ("2a^2", "2a^2"),
        ("5 x^2", "5 x^2"),
        ("3 ab^2", "3 ab^2"),
        ("2^3", "2^3"),
        ("10^{-3}", "10^{-3}"),
    ],
)
def test_so_sai_o_expoente_de_unidade_conhecida(texto, esperado):
    assert validacao._sem_expoente_de_unidade(texto) == esperado


def test_expoente_negativo_depois_de_numero_nao_vira_barra():
    """"0,5 s⁻¹" é frequência: virar "0,5/s" apagaria a unidade da alternativa."""
    assert validacao.simplificar_unidade_latex("0,5 s⁻¹") == "0,5 s⁻¹"
    assert validacao._alternativas_carregam_unidade(["0,5 s⁻¹"], "", validacao.UNIDADES_FISICA)


def test_a_conta_com_unidade_no_meio_e_avaliada_sem_o_expoente():
    """As 44 questões de pressão do banco: 70/4 = 17,5, não 70/4² = 4,375."""
    assert validacao._avaliar_expressao_numerica(r"\frac{70 N}{4 m^2}") == pytest.approx(17.5)
    assert validacao._avaliar_expressao_numerica("2^3") == pytest.approx(8)


PRESSAO = "força de 70 N atua em uma area de 4 m^2"


def test_a_pressao_do_banco_passa():
    certa = do_banco(PRESSAO, "Fisica")

    assert veredito(certa, "Fisica") == "aceita"


def test_a_pressao_com_a_conta_errada_continua_recusada():
    errada = copy.deepcopy(do_banco(PRESSAO, "Fisica"))
    for bloco_ou_passo in errada["passos_resolucao"] + errada["explicacao"]:
        bloco_ou_passo["conteudo"] = bloco_ou_passo["conteudo"].replace("17,5", "16,5")
    errada["correta"] = next(i for i, o in enumerate(errada["opcoes"]) if o.startswith("16,5"))

    assert veredito(errada, "Fisica") == "resultado-aritmetico-invalido"


# --------------------------------------------------------------------------
# unidade escrita em LaTeX nas alternativas
# --------------------------------------------------------------------------

def corrente(opcoes):
    return questao(
        "Em um circuito de bancada, uma fonte fornece tensão de 12 V a um resistor de 4 Ω. Calcule a corrente que percorre o resistor.",
        opcoes, r"I = \frac{V}{R}",
        ["V = 12, R = 4", r"I = \frac{12}{4} = 3", "I = 3 A"], "I = 3 A",
        legenda="I: corrente; V: tensao; R: resistencia",
    )


@pytest.mark.parametrize("unidade", [r"\text{A}", r"\,\text{A}", r"\mathrm{A}"])
def test_unidade_em_latex_conta_como_unidade(unidade):
    """Render, 11/09/2026: "I = 3 \\text{A}" caiu em laboratorio-sem-calculo."""
    certa = corrente([f"3 {unidade}", f"48 {unidade}", f"0,33 {unidade}", f"16 {unidade}"])

    assert veredito_do_laboratorio(certa, "Fisica") == "aceita"


def test_alternativa_sem_unidade_ganha_a_unidade_do_resultado():
    """Ate 02/10/2026 este caso era recusado. O resultado diz "I = 3 A", entao
    a alternativa "3" vira "3 A" (ver test_unidade_completada_nas_alternativas.py)."""
    sem_unidade = corrente(["3", "48", "0,33", "16"])

    with contextlib.redirect_stdout(io.StringIO()):
        payload, aceita, motivo = validar_questao_gerada(copy.deepcopy(sem_unidade), "Fisica", "laboratorio")

    assert aceita, motivo
    assert payload["opcoes"] == ["3 A", "48 A", "0,33 A", "16 A"]


def test_sem_unidade_em_lugar_nenhum_continua_recusada():
    sem_unidade = questao(
        "Em um circuito de bancada, uma fonte fornece tensão de 12 V a um resistor de 4 Ω. Calcule a corrente que percorre o resistor.",
        ["3", "48", "0,33", "16"], r"I = rac{V}{R}",
        ["V = 12, R = 4", r"I = rac{12}{4} = 3", "I = 3"], "I = 3",
        legenda="I: corrente; V: tensao; R: resistencia",
    )

    assert veredito(sem_unidade, "Fisica") == "laboratorio-sem-calculo"


@pytest.mark.parametrize("opcao", ["1,0 mol·L⁻¹", r"1,0 mol \cdot L^{-1}", r"1,0 \text{ mol/L}", "58,5 g·mol⁻¹"])
def test_unidade_com_expoente_negativo_e_reconhecida(opcao):
    assert validacao._alternativas_carregam_unidade([opcao], "", validacao.UNIDADES_QUIMICA)


def test_palavra_depois_do_numero_continua_nao_sendo_unidade():
    assert not validacao._alternativas_carregam_unidade(["12 bananas"], "", validacao.UNIDADES_QUIMICA)


# --------------------------------------------------------------------------
# PA: o detector não julga PG nem soma
# --------------------------------------------------------------------------

def test_a_pg_do_banco_passa():
    certa = do_banco("Em uma PG")

    assert veredito(certa, "Matematica") == "aceita"


def test_a_pg_marcando_alternativa_errada_continua_recusada():
    certa = do_banco("Em uma PG")
    errada_idx = next(i for i, o in enumerate(certa["opcoes"]) if i != int(certa["correta"]))

    assert veredito(marcando_outra(certa, errada_idx), "Matematica") != "aceita"


def soma_da_pa(correta=0):
    return questao(
        "Em uma progressão aritmética o primeiro termo é a₁=5, a razão é d=3 e são considerados n=8 termos. Qual é a soma dos oito termos?",
        ["124", "26", "248", "31"], r"S_n = \frac{n(a_1 + a_n)}{2}",
        ["a_1 = 5, d = 3, n = 8", r"a_8 = 5 + 7 \cdot 3 = 26", r"S_8 = \frac{8 \cdot 31}{2} = 124", "S_n = 124"],
        "S_n = 124", correta=correta,
        legenda="a_1: primeiro termo; d: razao; n: numero de termos; a_n: ultimo termo",
    )


def test_a_soma_da_pa_nao_e_julgada_como_termo():
    """Render, 11/09/2026: soma 124, certa, recusada esperando o 8º termo."""
    assert veredito(soma_da_pa(), "Matematica") == "aceita"


def test_a_soma_marcando_alternativa_errada_continua_recusada():
    assert veredito(soma_da_pa(correta=2), "Matematica") != "aceita"


def test_o_termo_da_pa_continua_sendo_calculado():
    dados = {"pergunta": "Em uma PA, a1 = 19, razão = 20 e n = 23. Qual é o termo an?", "passos_resolucao": [], "explicacao": []}

    assert validacao._valor_esperado_progressao_aritmetica(dados) == pytest.approx(459)


# --------------------------------------------------------------------------
# tangente e ângulo só como palavra
# --------------------------------------------------------------------------

def test_a_area_do_retangulo_nao_e_tangente():
    certa = do_banco("retangular")

    assert validacao._valor_esperado_trigonometria_altura(certa) is None
    assert veredito(certa, "Matematica") == "aceita"


def test_a_area_do_retangulo_errada_continua_recusada():
    certa = do_banco("retangular")
    errada_idx = next(i for i, o in enumerate(certa["opcoes"]) if i != int(certa["correta"]))

    assert veredito(marcando_outra(certa, errada_idx), "Matematica") != "aceita"


@pytest.mark.parametrize("escrita", [r"h = 30 \cdot \tan(45^{\circ})", "h = 30 * tan(45)", "h = 30 vezes a tangente de 45"])
def test_a_tangente_de_verdade_continua_detectada(escrita):
    dados = {
        "pergunta": "Um prédio projeta uma sombra de 30 m quando o ângulo de elevação do sol é de 45°. Qual é a altura do prédio?",
        "passos_resolucao": [{"conteudo": escrita}],
        "explicacao": [],
    }

    assert validacao._valor_esperado_trigonometria_altura(dados) == pytest.approx(30)


def test_o_angulo_e_o_que_vem_depois_da_palavra_angulo_e_nao_de_retangulo():
    """Sem a fronteira de palavra, "retângulo tem base 8" dava ângulo 8."""
    dados = {
        "pergunta": "Um retângulo tem base 8 m e a diagonal forma um ângulo de 30° com a base. Use a tangente: qual é a altura?",
        "passos_resolucao": [],
        "explicacao": [],
    }

    assert validacao._valor_esperado_trigonometria_altura(dados) == pytest.approx(8 * math.tan(math.radians(30)))


# --------------------------------------------------------------------------
# checagem extra do calculo_service
# --------------------------------------------------------------------------

def potencia(opcoes):
    return questao(
        "Um resistor de resistência R = 8 Ω é ligado a uma fonte de tensão constante V = 24 V. Qual é a potência dissipada no resistor?",
        opcoes, r"P = \frac{V^2}{R}",
        ["V = 24, R = 8", r"P = \frac{24^2}{8} = 72", "P = 72 W"], "P = 72 W",
        legenda="P: potencia; V: tensao; R: resistencia",
    )


def test_potencia_em_watt_passa_na_checagem_extra():
    """Render, 11/09/2026: a lista antiga não tinha W."""
    assert veredito_do_laboratorio(potencia(["72 W", "3 W", "192 W", "32 W"]), "Fisica") == "aceita"


def test_fisica_sem_unidade_continua_barrada():
    assert veredito_do_laboratorio(potencia(["72", "3", "192", "32"]), "Fisica") != "aceita"


def test_ph_sem_unidade_passa_na_checagem_extra():
    """Uma questão respondida por aluno em 11/09/2026: pH é adimensional."""
    ph = questao(
        "Em um controle de qualidade, se [H+] = 10^{-10} mol/L, qual é o pH?",
        ["10", "11", "12", "9,5"], r"pH=-\log[H^+]",
        ["[H^+] = 10^{-10} mol/L", r"pH = -\log(10^{-10}) = 10", "pH = 10"], "pH = 10",
    )

    assert veredito_do_laboratorio(ph, "Quimica") == "aceita"


def bhaskara(sub):
    return questao(
        "Resolva a equação 2x^2 + 5x - 3 = 0 usando a fórmula de Bhaskara e encontre as raízes reais.",
        ["x' = 0,5 e x'' = -3", "x' = -0,5 e x'' = 3", "x' = 1 e x'' = -1,5", "x' = 3 e x'' = -2"],
        r"x = \frac{-b \pm \sqrt{\Delta}}{2a}",
        ["a = 2, b = 5, c = -3", r"\Delta = 5^2 - 4 \cdot 2 \cdot (-3) = 49", r"x = \frac{-5 \pm 7}{4}", "x_1 = 0,5, x_2 = -3"],
        "x_1 = 0,5, x_2 = -3", sub=sub, legenda="a, b, c: coeficientes",
    )


def test_bhaskara_com_delta_na_subformula_passa():
    """Render, 08/09/2026: o b² estava na subfórmula, como o prompt pede."""
    assert veredito_do_laboratorio(bhaskara([r"\Delta = b^2 - 4ac"]), "Matematica") == "aceita"


def test_bhaskara_sem_b2_em_lugar_nenhum_continua_barrada():
    assert calc._bhaskara_inadequada_laboratorio(bhaskara([]))


def test_a_checagem_extra_registra_a_questao_inteira(monkeypatch, capsys):
    monkeypatch.setattr(calc.runtime, "session_state", {})
    teorica = {
        "pergunta": "Qual conceito explica melhor a lei de Newton?",
        "opcoes": ["Inercia", "Velocidade", "Calor", "Volume"],
        "correta": 0,
        "formula": "",
        "subformulas": [],
        "passos_resolucao": [],
    }
    monkeypatch.setattr(ia_service, "invocar_enigma_laboratorio", lambda *args, **kwargs: dict(teorica))
    monkeypatch.setattr(ia_service, "obter_ultimo_erro_ia", lambda: "")
    monkeypatch.setattr(ia_service, "obter_ultimo_provedor_ia", lambda: "groq")
    monkeypatch.setattr(exatas_bank, "gerar_desafio_exatas", lambda *args, **kwargs: bloco("a = 4 m/s²", ["4 m/s²", "2 m/s²", "1 m/s²", "8 m/s²"]))

    calc.gerar_desafio_exatas("Fisica", "leis de Newton", "1º Ano EM", "Médio")

    linha = next(l for l in capsys.readouterr().out.splitlines() if "(checagem extra)" in l)
    registrada = json.loads(linha.split("questao=", 1)[1])
    assert registrada["opcoes"] == teorica["opcoes"]
    assert registrada["correta"] == 0


# --------------------------------------------------------------------------
# as recusas reais que estavam CERTAS continuam
# --------------------------------------------------------------------------

def test_as_recusas_reais_corretas_continuam_recusadas():
    evaporacao = questao(
        "Um laboratório tem 480 ml de uma solução. Após uma reação, 30% da solução é evaporada. Qual o volume restante em ml?",
        ["144", "336", "480", "150"], r"V_r = V \cdot (1 - p)",
        ["V = 480, p = 0,30", r"V_r = 480 \cdot 0,70 = 336", "144"], "144",
    )
    quarto_termo = questao(
        "Numa progressão aritmética, o primeiro termo é 12 e o quinto termo é 32. Qual é o valor do quarto termo?",
        ["24", "27", "22", "29"], r"a_n = a_1 + (n - 1) r",
        ["a_1 = 12, a_5 = 32", r"r = \frac{32 - 12}{4} = 5", r"a_4 = 12 + 3 \cdot 5 = 27", "24"], "24",
    )
    delta_errado = questao(
        "Resolva a equação 2x² - 5x + 3 = 0 usando a fórmula de Bhaskara, com a = 2, b = -5 e c = 3.",
        ["x' ≈ 2,15 e x'' ≈ 0,35", "x' = 1,5 e x'' = 1", "x' = -1,5 e x'' = -1", "x' = 3 e x'' = 0,5"],
        r"x = \frac{-b \pm \sqrt{\Delta}}{2a}",
        ["a = 2, b = -5, c = 3", r"\Delta = (-5)^2 - 4 \cdot 2 \cdot 3 = 13", r"x = \frac{5 \pm \sqrt{13}}{4}", "x_1 ≈ 2,15, x_2 ≈ 0,35"],
        "x_1 ≈ 2,15, x_2 ≈ 0,35", sub=[r"\Delta = b^2 - 4ac"],
    )

    assert veredito_do_laboratorio(evaporacao, "Matematica") != "aceita"
    assert veredito_do_laboratorio(quarto_termo, "Matematica") != "aceita"
    assert veredito_do_laboratorio(delta_errado, "Matematica") != "aceita"
