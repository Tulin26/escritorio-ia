"""A resolução tem de mostrar a conta, não só a fórmula e o resultado.

O defeito
---------
Na tela do Laboratório:

    1º Passo:  a = 2, b = -7, c = 3       <- a, b, c ganham número
    2º Passo:  Δ = (-7)^2 - 4 · 2 · 3     <- substituiu, certo
    3º Passo:  x = (-b ± √Δ)/(2a)         <- voltou para as LETRAS
    Resultado: x = 3, x = 0,5             <- de onde vieram?

O aluno recebe a fórmula e o resultado, e nada entre os dois -- que é
justamente o pedaço que ensina.

Por que só o ÚLTIMO passo antes do resultado: escrever a fórmula com letras é
legítimo como enunciado de etapa (`Δ = b² - 4ac`) **desde que** um passo
seguinte substitua. No último não há mais essa chance.

A medição, e o que ela ensinou sobre medir
------------------------------------------
Três desenhos anteriores (A: passo final sem dígito; B: passo final com Δ
simbólico; C: resolução inteira sem dígito) foram prototipados em 03/09 e
ficaram esperando dado. Medidos agora, os três disparam **0 vezes** nas 8
resoluções reais guardadas: o defeito que eles miravam nunca foi observado. O
que apareceu foi este, que nenhum deles pega -- o passo final tinha números.

E o aviso que ficou: contra o banco offline (2.114 resoluções distintas) este
desenho deu **0%**, e contra as 8 reais a primeira versão dele deu **25%** de
falso positivo. O banco autoral não mostra as formas que a IA inventa; ele diz
"a regra não recusa o que NÓS escrevemos", que é uma pergunta mais fraca.

Os dois falsos positivos, e as duas armadilhas que eles revelaram, estão
cobertos abaixo.
"""

from __future__ import annotations

import pytest

from services.ia.validacao import (
    _resolucao_nao_substitui_os_valores,
    _variaveis_do_passo,
)


def _resolucao(*conteudos: str) -> dict:
    passos = [{"titulo": f"{i}º Passo", "conteudo": c} for i, c in enumerate(conteudos, 1)]
    if passos:
        passos[-1]["final"] = True
    return {"passos_resolucao": passos}


# ====================== O CASO DA TELA ======================


def test_pega_a_bhaskara_que_nao_substitui():
    """O caso real, copiado do log."""
    ruim = _resolucao(
        "a=2, b=-7, c=3",
        "Δ = (-7)^2 - 4*2*3",
        "x = (-b ± √Δ)/(2a)",
        "x₁ = 3, x₂ = 0.5",
    )

    assert _resolucao_nao_substitui_os_valores(ruim)


@pytest.mark.parametrize(
    "passo_da_substituicao",
    [
        "x = (7 ± 5)/(2 · 2)",
        r"x = \frac{16\pm\sqrt{16}}{2} = \frac{16\pm 4}{2}",
        r"x = \frac{6\pm\sqrt{0}}{2} = \frac{6\pm 0}{2}",
    ],
)
def test_deixa_passar_a_bhaskara_resolvida_certo(passo_da_substituicao):
    """O caso difícil, e o que dá valor à regra: as duas últimas são
    resoluções REAIS que estavam no banco, corretas, e precisam passar."""
    boa = _resolucao(
        "a = 1, b = -16, c = 60.",
        r"\Delta = (-16)^2 - 4\cdot 1\cdot 60 = 16",
        passo_da_substituicao,
        "x' = 6;\\; x'' = 10",
    )

    assert not _resolucao_nao_substitui_os_valores(boa)


def test_enunciar_a_formula_antes_de_substituir_e_legitimo():
    """`Δ = b² - 4ac` com letras é uma etapa válida -- desde que a seguinte
    substitua. É por isso que a regra olha só o último passo antes do
    resultado."""
    boa = _resolucao(
        "a = 2, b = -7, c = 3",
        "Δ = b^2 - 4ac",
        "Δ = (-7)^2 - 4 · 2 · 3 = 25",
        "x = (7 ± 5)/4",
        "x_1 = 3",
    )

    assert not _resolucao_nao_substitui_os_valores(boa)


# ====================== AS DUAS ARMADILHAS ======================
#
# Cada uma destas foi um falso positivo contra dado real, na primeira versão.


def test_prosa_dentro_do_passo_nao_inventa_variaveis():
    """Resolução real que a primeira versão acusou por engano.

    "substituir na fórmula de Bhaskara" tem b, a e c dentro das PALAVRAS. O
    passo substituiu certinho -- o problema dele é outro (prosa no conteúdo,
    que o prompt já não pede mais)."""
    passo = "substituir na fórmula de Bhaskara: (-8 ± sqrt(144)) / (2*(-2))"

    variaveis = _variaveis_do_passo(passo)

    assert "b" not in variaveis, f"letra de palavra virou variavel: {sorted(variaveis)}"
    assert "a" not in variaveis
    assert "c" not in variaveis

    real = _resolucao(
        "identificar os valores a = -2, b = 8, c = 10",
        "calcular o delta: 8^2 - 4*(-2)*10",
        passo,
        "-1, 5",
    )
    assert not _resolucao_nao_substitui_os_valores(real)


def test_subscrito_e_uma_variavel_e_nao_a_letra_de_base():
    """A outra: "P_f" virava {P, f}, e como "P = 150" existia antes, a regra
    concluía que P não fora substituído. P_f é outra variável."""
    variaveis = _variaveis_do_passo("P_f=150*(1-0.20)")

    assert "P_f" in variaveis
    assert "P" not in variaveis, f"o subscrito virou a letra de base: {sorted(variaveis)}"

    real = _resolucao("P=150", "D=0.20*150", "P_f=150*(1-0.20)", "P_f=120")
    assert not _resolucao_nao_substitui_os_valores(real)


def test_nome_de_funcao_nao_e_variavel():
    variaveis = _variaveis_do_passo(r"sen(\theta) = \frac{15}{25}")

    for letra in ("s", "e", "n"):
        assert letra not in variaveis, f"'{letra}' de 'sen' virou variavel"


def test_comando_latex_com_subscrito_nao_inventa_variavel():
    """A terceira armadilha, achada por mutação.

    Sem tirar o comando LaTeX **antes** de procurar subscrito, `\\Delta_1` casa
    o regex pelo "a" de "Delta" e nasce a variável fantasma `a_1`. Se um passo
    anterior tivesse dado número a um `a_1` de verdade, a regra dispararia por
    uma variável que não existe.

    O `Δ_1` em si acaba não sendo reconhecido como variável -- o que erra para
    o lado de deixar passar, que é o lado seguro."""
    variaveis = _variaveis_do_passo(r"\Delta_1 = 25")

    assert "a_1" not in variaveis, f"variavel fantasma: {sorted(variaveis)}"
    assert "a" not in variaveis


# ====================== OS LIMITES DA REGRA ======================


def test_so_vale_a_atribuicao_de_NUMERO():
    """`Δ = b² - 4ac` não dá número ao Δ: define em função de outras letras.
    Sem isso, a regra acusaria toda resolução que enuncia uma subfórmula."""
    resolucao = _resolucao("Δ = b^2 - 4ac", "x = (-b ± √Δ)/(2a)", "x = 3")

    assert not _resolucao_nao_substitui_os_valores(resolucao)


def test_resolucao_curta_demais_nao_e_julgada():
    """Com menos de três passos não há "o passo antes do resultado" separado
    de quem atribuiu os valores."""
    assert not _resolucao_nao_substitui_os_valores(_resolucao("a = 2", "a = 2"))
    assert not _resolucao_nao_substitui_os_valores(_resolucao("x = 3"))
    assert not _resolucao_nao_substitui_os_valores({"passos_resolucao": []})
    assert not _resolucao_nao_substitui_os_valores({})


def test_sem_atribuicao_numerica_nao_ha_o_que_cobrar():
    """Uma resolução que nunca deu número a letra nenhuma não pode ser
    acusada de não substituir."""
    resolucao = _resolucao(
        "A área do círculo depende do raio",
        "A = π R^2",
        "A = 3,14 · 25",
        "A = 78,5",
    )

    assert not _resolucao_nao_substitui_os_valores(resolucao)


# ====================== A ROTA ======================


def test_a_validacao_esta_ligada_no_laboratorio():
    from services.ia.validacao import validar_questao_gerada

    ruim = {
        "pergunta": "Determine as raízes de 2x² - 7x + 3 = 0.",
        "opcoes": ["{3; 0,5}", "{1; 2}", "{-3; 0,5}", "{3; -0,5}"],
        "correta": 0,
        "explicacao": [{"tipo": "resultado", "conteudo": "As raizes vem da formula de Bhaskara aplicada aos coeficientes da equacao."}],
        "formula": "x = (-b ± √Δ)/(2a)",
        "subformulas": ["Δ = b^2 - 4ac"],
        "legenda_variaveis": "a = coeficiente; b = coeficiente; c = termo independente; Δ = discriminante",
        **_resolucao(
            "a=2, b=-7, c=3",
            "Δ = (-7)^2 - 4*2*3",
            "x = (-b ± √Δ)/(2a)",
            "x₁ = 3, x₂ = 0.5",
        ),
    }

    _, ok, motivo = validar_questao_gerada(ruim, "Matematica", contexto="laboratorio")

    assert not ok
    assert motivo == "resolucao-nao-substitui-os-valores", motivo


def _densidade_sem_substituir() -> dict:
    """A MESMA questão, para comparar dois recortes de matéria.

    Precisa ser uma questão de cálculo de verdade -- com números no enunciado
    e explicação com a conta --, senão `laboratorio-sem-calculo` a recusa
    antes e o teste não chega a medir o que diz medir. A primeira versão deste
    teste caiu nessa: passava porque o payload morria três regras antes."""
    return {
        "pergunta": "Um corpo tem massa de 10 g e volume de 5 mL. Calcule a densidade em g/mL.",
        "opcoes": ["2 g/mL", "3 g/mL", "4 g/mL", "5 g/mL"],
        "correta": 0,
        "explicacao": [{"tipo": "resultado", "conteudo": "A densidade e a razao entre a massa do corpo e o volume que ele ocupa."}],
        "formula": "d = m/V",
        "subformulas": [],
        "legenda_variaveis": "d = densidade; m = massa; V = volume",
        **_resolucao("m = 10, V = 5", "d = m/V", "d = 2"),
    }


def test_a_regra_vale_para_exatas():
    from services.ia.validacao import validar_questao_gerada

    _, ok, motivo = validar_questao_gerada(
        _densidade_sem_substituir(), "Quimica", contexto="laboratorio"
    )

    assert not ok
    assert motivo == "resolucao-nao-substitui-os-valores", motivo


def test_ciencias_fica_de_fora_como_nas_regras_vizinhas():
    """O par do teste acima, com o MESMO payload: só muda a matéria.

    `eh_exatas` é Matemática, Física e Química -- Ciências não entra, e a
    regra vizinha (`legenda-com-variavel-sem-formula`) usa o mesmo recorte.
    Ciências aparece no Laboratório (`MATERIAS_LAB`), então sem essa guarda a
    regra passaria a valer lá. Não é bug nem acerto óbvio: é o recorte
    escolhido, e o par existe para que mudá-lo seja decisão, não efeito
    colateral."""
    from services.ia.validacao import validar_questao_gerada

    _, ok, motivo = validar_questao_gerada(
        _densidade_sem_substituir(), "Ciencias", contexto="laboratorio"
    )

    assert ok, f"Ciencias passou a ser julgada: {motivo}"


def test_fora_do_laboratorio_a_regra_nao_vale():
    """Os outros modos passam por `_normalizar_questao_oraculo`, que apaga os
    passos de propósito -- lá não há resolução para julgar."""
    from services.ia.validacao import validar_questao_gerada

    ruim = {
        "pergunta": "Determine as raízes de 2x² - 7x + 3 = 0.",
        "opcoes": ["{3; 0,5}", "{1; 2}", "{-3; 0,5}", "{3; -0,5}"],
        "correta": 0,
        "explicacao": "Bhaskara.",
        **_resolucao(
            "a=2, b=-7, c=3",
            "Δ = (-7)^2 - 4*2*3",
            "x = (-b ± √Δ)/(2a)",
            "x₁ = 3, x₂ = 0.5",
        ),
    }

    _, _, motivo = validar_questao_gerada(dict(ruim), "Matematica", contexto="treino")

    assert motivo != "resolucao-nao-substitui-os-valores"
