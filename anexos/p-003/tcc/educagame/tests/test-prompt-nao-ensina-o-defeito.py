"""O modelo que mandamos para a IA não pode ser exemplo do defeito.

O que aconteceu
---------------
A tela do Laboratório mostrou um 1º Passo assim:

    identificarosvaloresa = −2

As palavras entraram na fórmula e foram tipografadas como variável, sem
espaço. A investigação natural aponta para o renderizador -- e ele de fato
colou. Mas a causa estava antes, no nosso próprio prompt:

    {"titulo": "1º Passo", "conteudo": "identificar os valores", "final": false}

A prosa "identificar os valores" estava no campo **conteudo**. A IA copiou o
modelo e anexou a conta. E a regra que proíbe isso já existia no system
prompt -- ela só era contradita pelo modelo logo abaixo, e o modelo venceu.

Por que a assimetria: a IA não copia `"pergunta": "problema numerico com
pelo menos dois valores explicitos"`, porque isso não é um valor plausível
para o campo. Já "identificar os valores" **é** um conteúdo de passo
plausível. Descrição que parece valor vira valor.

O que este arquivo cobra
------------------------
Não as frases -- essas mudam. A ESTRUTURA: todo `conteudo` do modelo de
passos precisa ser um buraco `<...>`, que não se confunde com conteúdo. Se
alguém voltar a escrever uma descrição em prosa ali, este teste reprova.

Também cobra as duas regras que saíram da mesma questão de projétil
(`h(t) = -2t² + 8t + 10`), porque as duas faziam o aluno ler algo falso:

- "Resultado Final: -1, 5" lê-se como o número -1,5 em português;
- `t = -1 s` é raiz da equação mas não existe fisicamente, e a IA
  apresentava as duas como se ambas valessem.
"""

from __future__ import annotations

import re

import pytest

from services.ia.enigma import _prompts_laboratorio


def _prompt() -> str:
    system, user = _prompts_laboratorio("Matematica", "1º EM", "Médio", "Bhaskara")
    return system + "\n" + user


def _conteudos_do_modelo(prompt: str) -> list[str]:
    """Os `"conteudo": "..."` que aparecem DENTRO do modelo de passos."""
    bloco = re.search(r'"passos_resolucao":\s*\[(.*?)\]', prompt, re.DOTALL)
    assert bloco, "o modelo de passos_resolucao sumiu do prompt"
    return re.findall(r'"conteudo":\s*"([^"]*)"', bloco.group(1))


def test_o_modelo_de_passos_existe_e_tem_quatro_slots():
    """Guarda: sem isto, os testes abaixo ficariam vazios se o bloco sumisse."""
    conteudos = _conteudos_do_modelo(_prompt())

    assert len(conteudos) == 4, f"esperado 4 passos no modelo, achei {len(conteudos)}: {conteudos}"


def test_nenhum_conteudo_do_modelo_e_texto_copiavel():
    """A regra que pega o defeito: buraco `<...>`, nunca descrição em prosa.

    Foi assim que "identificar os valores" virou conteúdo de verdade na tela
    de um aluno."""
    for conteudo in _conteudos_do_modelo(_prompt()):
        assert conteudo.startswith("<") and conteudo.endswith(">"), (
            f'"{conteudo}" nao e um buraco <...>: e uma descricao em prosa, e a IA copia '
            f"descricao que parece valor plausivel"
        )


@pytest.mark.parametrize(
    "prosa",
    ["identificar os valores", "calcular o valor auxiliar", "substituir os valores"],
)
def test_as_frases_que_a_ia_copiou_nao_voltam_como_conteudo(prosa: str):
    """O par do teste acima, pelo lado do exemplo concreto. `<...>` é a forma;
    estas três são as frases que de fato vazaram para a tela."""
    for conteudo in _conteudos_do_modelo(_prompt()):
        assert prosa not in conteudo.lower(), f"'{prosa}' voltou para o campo conteudo do modelo"


def test_o_prompt_manda_nao_repetir_o_titulo_no_conteudo():
    prompt = _prompt().lower()

    assert "nunca repita no conteudo o que o titulo do passo ja diz" in prompt


# ====================== A QUESTÃO DO PROJÉTIL ======================


def test_o_prompt_proibe_o_resultado_final_ambiguo():
    """"-1, 5" lê-se como -1,5. A regra existia para as alternativas e não
    alcançava o passo final -- que é justamente onde o aluno confere."""
    prompt = _prompt().lower()

    assert "separador decimal" in prompt or "separador\ndecimal" in prompt, (
        "o prompt nao explica mais POR QUE '-1, 5' e proibido; sem o motivo a regra "
        "vira superstição e a IA a ignora no primeiro caso novo"
    )
    assert 'x_1 = -1, x_2 = 5' in prompt or "x' = -1 e x'' = 5" in prompt, (
        "sumiu o exemplo da forma certa de escrever duas raizes"
    )


def test_o_prompt_manda_descartar_raiz_sem_sentido_fisico():
    """`t = -1 s` é raiz da equação e não existe no mundo. Apresentar as duas
    como se ambas valessem ensina errado."""
    prompt = _prompt().lower()

    assert "descarte" in prompt and "negativa" in prompt, "sumiu a regra de descartar a raiz negativa"
    for grandeza in ("tempo", "comprimento", "distancia", "area", "massa"):
        assert grandeza in prompt, f"a regra da raiz negativa nao cita '{grandeza}'"


def test_a_regra_da_raiz_negativa_pede_o_motivo_na_tela():
    """Descartar em silêncio não ensina: o aluno precisa ver por que a raiz
    sai, senão fica achando que a conta deu errado."""
    prompt = _prompt()

    assert "(descartada, t > 0)" in prompt, "sumiu o exemplo de como mostrar o descarte ao aluno"


# ====================== O QUE NÃO PODE SER PERDIDO ======================


def test_as_regras_antigas_continuam_no_prompt():
    """Este arquivo mexe num prompt de ~75 linhas onde cada regra veio de um
    defeito real. Uma edição descuidada apaga vizinho."""
    prompt = _prompt().lower()

    esperadas = [
        # a questão precisa ser de conta, não teórica
        "nao gere perguntas teoricas",
        # valor de referência tem de vir no enunciado
        "massa molar",
        # a subformula indispensável (círculo circunscrito, 09/09)
        "regra que vence as duas acima",
        # um cálculo por passo
        "exatamente uma conta",
    ]
    for trecho in esperadas:
        assert trecho in prompt, f"regra antiga sumiu do prompt: '{trecho}'"
