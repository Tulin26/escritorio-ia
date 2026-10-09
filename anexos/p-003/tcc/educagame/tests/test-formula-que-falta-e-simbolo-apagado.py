"""Dois defeitos que apareceram na mesma tela do Laboratório.

1. O filtro de caracteres apagava o "±"
---------------------------------------
A tela mostrava a fórmula de Bhaskara assim:

    x = (-b √Δ)/(2 a)

Sem o "±" ela não produz as duas raízes que o passo seguinte apresentava
(x = 3 e x = 0,5). A IA tinha escrito o sinal; quem apagou fomos nós.

`_remover_caracteres_nao_latex` aceita ASCII e depois pula direto para "À"
(U+00C0). Toda a faixa U+0080–U+00BF cai fora e some **em silêncio**. Medido,
o que a IA de fato escreve nessa faixa:

    "x = (-b ± √Δ)/(2a)"  ->  "x = (-b √Δ)/(2a)"   Bhaskara sem o ±
    "x = (-7 ± 5)/4"      ->  "x = (-7 5)/4"       números colados
    "sen(30°) = 0,5"      ->  "sen(30) = 0,5"      grau vira radiano
    "T = 25 °C"           ->  "T = 25 C"           temperatura sem unidade
    "d = 5 µm"            ->  "d = 5 m"            micrômetro vira METRO

O último muda o valor por 10⁶ sem avisar.

Este bug **já tinha sido encontrado uma vez**, para o "·" (U+00B7), e o
comentário em `_normalizar_entrada_formula` descreve a causa com precisão --
mas a correção tratou só aquele caractere. Era uma classe, não um caso.

2. A legenda declarava variável que nenhuma fórmula usava
---------------------------------------------------------
Outra tela, mesma sessão: "Um triângulo equilátero tem lado 12 cm; calcule a
área do círculo circunscrito", com

    formula:  A = \\pi R^2
    legenda:  a = lado do triângulo (cm); R = raio do círculo circunscrito;
              π = 3.14; A = área do círculo

Nada liga "a" a "R". O aluno tem o lado, precisa do raio, e não recebeu como
sair de um para o outro. Faltava a subfórmula R = a√3/3.

O prompt era a causa: ele dizia *"O campo subformulas deve vir vazio na
maioria dos casos"* e *"deixe subformulas vazio quando houver apenas uma
formula principal"* -- pressão contra exatamente o que essa questão exigia.

Por que uma validação, e não só o prompt
----------------------------------------
Porque o prompt **já pedia** a substituição dos valores ("Os passos devem ser
curtos, objetivos e mostrar a substituicao dos valores") e a IA escreveu a
fórmula com letras assim mesmo. Pedir de novo não garante; a regra garante.

Medido: 0 de 7.200 questões do banco offline do Laboratório com legenda e
fórmula seriam recusadas. Mesmo perfil das validações já ligadas.

A armadilha que a primeira versão da regra caiu
-----------------------------------------------
Comparar com fronteira de palavra (`(?<![A-Za-z0-9_])`) **recusava Bhaskara
correta**: em "(2a)" e em "4ac" as variáveis vêm coladas. E procurar a letra
crua também não serve -- "\\Delta" contém um "a", "\\sqrt" contém um "r".

Por isso os comandos LaTeX viram símbolo antes de comparar, e os nomes de
função saem da conta. Sem tirar "sen", um "sen(x)" provaria que existem
variáveis chamadas s, e e n -- e a regra pararia de pegar qualquer coisa.
"""

from __future__ import annotations

import re

import pytest

from core.utils import preparar_formula_latex
from services.ia.validacao import (
    _nomes_usados_nas_formulas,
    _variaveis_orfas_da_legenda,
    validar_questao_gerada,
)


# ====================== 1. OS CARACTERES APAGADOS ======================


@pytest.mark.parametrize(
    "entrada, precisa_conter",
    [
        ("x = (-b ± √Δ)/(2a)", r"\pm"),
        ("x = (-7 ± 5)/4", r"\pm"),
        ("5±3", r"\pm"),
        ("sen(30°) = 0,5", r"\circ"),
        ("T = 25 °C", r"\circ"),
        ("θ = 45°", r"\circ"),
        ("d = 5 µm", r"\mu"),
        ("x = ½", r"\frac{1}{2}"),
        ("x = ¼", r"\frac{1}{4}"),
        ("x = ¾", r"\frac{3}{4}"),
        ("10¹", "^1"),
    ],
)
def test_o_simbolo_sobrevive_a_formatacao(entrada, precisa_conter):
    saida = preparar_formula_latex(entrada)

    assert precisa_conter in saida, f"{entrada!r} virou {saida!r}"


def test_o_mais_ou_menos_nao_cola_os_dois_numeros():
    """"(-7 ± 5)" virando "(-7 5)" é pior que perder o sinal: some o operador
    e sobram dois números encostados, que o aluno lê como um só."""
    saida = preparar_formula_latex("x = (-7 ± 5)/4")

    assert "7 5" not in saida
    assert "75" not in saida


def test_o_micrometro_nao_vira_metro():
    """O pior da faixa: muda o valor por um fator de 10^6, em silêncio."""
    saida = preparar_formula_latex("d = 5 µm")

    assert r"\mu" in saida, f"o micro sumiu: {saida!r}"


@pytest.mark.parametrize("entrada", ["5±3", "x=2±1", "a±b"])
def test_o_comando_nao_cola_no_que_vem_depois(entrada):
    """Traduzir "±" para "\\pm" sem espaço em volta troca um defeito por
    outro: "5±3" vira "5\\pm3", e o LaTeX lê "\\pm3" como um comando chamado
    "pm3", que não existe -- a linha inteira deixa de renderizar."""
    saida = preparar_formula_latex(entrada)

    assert not re.search(r"\\pm[0-9A-Za-z]", saida), f"comando colado: {saida!r}"


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("a ² b", "^2"),
        ("a ³ b", "^3"),
        ("a · b", r"\cdot"),
        ("a × b", r"\cdot"),
    ],
)
def test_os_que_ja_eram_tratados_continuam_iguais(entrada, esperado):
    """`²`, `³`, `·` e `×` já tinham tradução própria antes desta correção.
    Repetir a regra para eles criaria uma segunda que nunca roda."""
    assert esperado in preparar_formula_latex(entrada)


def test_nenhum_caractere_da_faixa_latin1_some_calado():
    """A guarda da CLASSE, não dos casos: se alguém acrescentar um símbolo
    matemático dessa faixa sem tradução, ele volta a ser apagado em silêncio.

    Só entram aqui os que significam algo em conta. Letras acentuadas não:
    elas estão acima de U+00C0 e o filtro já as aceita."""
    from core.utils import _SIMBOLOS_LATIN1_EM_LATEX

    for simbolo in _SIMBOLOS_LATIN1_EM_LATEX:
        assert 0x80 <= ord(simbolo) <= 0xBF, (
            f"{simbolo!r} não está na faixa que o filtro apaga -- ou o filtro mudou, "
            "ou este símbolo não precisava estar na tabela"
        )
        saida = preparar_formula_latex(f"a {simbolo} b")
        assert saida.strip() not in ("a b", "ab"), f"{simbolo!r} continua sumindo"


# ====================== 2. A VARIÁVEL SEM FÓRMULA ======================


TELA_DO_ALUNO = {
    "formula": r"A = \pi R^2",
    "subformulas": [],
    "legenda_variaveis": (
        "a = lado do triângulo (cm); R = raio do círculo circunscrito (cm); "
        "π = 3.14; A = área do círculo (cm^{2})"
    ),
}


def test_pega_a_questao_que_o_aluno_nao_tinha_como_resolver():
    assert _variaveis_orfas_da_legenda(TELA_DO_ALUNO) == ["a"]


def test_com_a_subformula_que_faltava_a_questao_passa():
    """O par do teste acima: a regra aponta o que consertar, e o conserto
    silencia a regra."""
    consertada = dict(TELA_DO_ALUNO, subformulas=[r"R = a\sqrt{3}/3"])

    assert _variaveis_orfas_da_legenda(consertada) == []


def test_a_comparacao_e_sensivel_a_maiuscula():
    """A legenda da tela declara "a" (lado) E "A" (área), e só "A" está na
    fórmula. Ignorando a caixa, o "a" órfão seria dado como presente e o
    defeito passaria batido."""
    nomes = _nomes_usados_nas_formulas(r"A = \pi R^2")

    assert "A" in nomes
    assert "a" not in nomes


@pytest.mark.parametrize(
    "caso, dados",
    [
        (
            "bhaskara com variaveis coladas em 2a e 4ac",
            {
                "formula": r"x = (-b \pm \sqrt{\Delta})/(2a)",
                "subformulas": [r"\Delta = b^2 - 4ac"],
                "legenda_variaveis": r"a = coeficiente; b = coeficiente; c = termo independente; \Delta = discriminante",
            },
        ),
        (
            "delta unicode na legenda, comando na formula",
            {
                "formula": r"x = (-b \pm \sqrt{\Delta})/(2a)",
                "subformulas": [r"\Delta = b^2 - 4ac"],
                "legenda_variaveis": "a = coeficiente; b = coeficiente; c = termo independente; Δ = discriminante",
            },
        ),
        (
            "trigonometria: sen/tan nao viram variaveis",
            {
                "formula": r"h = d \cdot \tan(\theta)",
                "subformulas": [],
                "legenda_variaveis": "h = altura (m); d = distância (m); θ = ângulo",
            },
        ),
        (
            "fracao: \\frac nao inventa f, r, a, c",
            {
                "formula": r"n = \frac{m}{M}",
                "subformulas": [],
                "legenda_variaveis": "n = mols; m = massa (g); M = massa molar (g/mol)",
            },
        ),
        (
            "subscrito: v_0 dos dois lados",
            {
                "formula": "v = v_0 + a t",
                "subformulas": [],
                "legenda_variaveis": "v = velocidade final; v_0 = velocidade inicial; a = aceleração; t = tempo",
            },
        ),
    ],
)
def test_questao_legitima_nao_e_recusada(caso, dados):
    """Cada um destes reprovava numa versão anterior da regra. O de Bhaskara é
    o mais importante: recusar a fórmula mais usada do Ensino Médio seria pior
    que o defeito que a regra conserta."""
    assert _variaveis_orfas_da_legenda(dados) == [], caso


def test_nome_de_funcao_nao_conta_como_variavel():
    """Sem tirar "sen" antes de quebrar em letras, um "sen(x)" na fórmula
    prova que existem variáveis chamadas s, e e n -- e a regra para de pegar
    qualquer coisa. Aqui a legenda declara "n", e "n" só existe dentro do
    "sen": a variável está órfã de verdade."""
    dados = {
        # Sem barra invertida de propósito: é como a IA costuma escrever, e é
        # o caso que `_FUNCOES_NA_FORMULA` existe para tratar. Com barra
        # ("\\sin") quem resolve é o removedor genérico de comandos, e o teste
        # não exercitaria a lista de funções.
        "formula": "y = sen(x)",
        "subformulas": [],
        "legenda_variaveis": "y = altura; x = ângulo; n = número de voltas",
    }

    assert _variaveis_orfas_da_legenda(dados) == ["n"]


def test_a_legenda_pode_escrever_o_comando_e_a_formula_o_simbolo():
    """O par do teste do Δ unicode: aqui é ao contrário -- a legenda usa
    "\\Delta" e a fórmula usa "Δ". Sem converter os dois lados para a mesma
    grafia, um dos dois sentidos fica de fora."""
    dados = {
        "formula": "x = -b/(2a) ± √(Δ)/(2a)",
        "subformulas": [],
        "legenda_variaveis": r"a = coeficiente; b = coeficiente; \Delta = discriminante",
    }

    assert _variaveis_orfas_da_legenda(dados) == []


def test_a_regra_so_vale_para_exatas():
    """A guarda `eh_exatas` no despacho. O Laboratório é de exatas hoje, mas a
    regra cruza legenda com fórmula -- coisas que só existem em exatas. Sem a
    guarda, uma questão de outra matéria que tivesse legenda seria julgada por
    um critério que não é dela."""
    _, _ok, motivo = validar_questao_gerada(
        _questao_completa(**TELA_DO_ALUNO), "Historia", contexto="laboratorio"
    )

    assert motivo != "legenda-com-variavel-sem-formula"


@pytest.mark.parametrize(
    "dados",
    [
        {"formula": "A = b*h", "subformulas": [], "legenda_variaveis": ""},
        {"formula": "", "subformulas": [], "legenda_variaveis": "x = algo"},
        {},
    ],
    ids=["sem-legenda", "sem-formula", "vazio"],
)
def test_sem_os_dois_lados_a_regra_nao_julga(dados):
    """Questão sem fórmula é assunto de `_resposta_exatas_sem_estrutura`.
    Julgar aqui seria uma segunda regra recusando pelo mesmo motivo."""
    assert _variaveis_orfas_da_legenda(dados) == []


# ====================== A REGRA LIGADA, PELA PORTA DE VERDADE ======================


def _questao_completa(**extra):
    """Uma questão REAL do banco offline, com a legenda/fórmula trocadas.

    Inventar a questão inteira não funciona: ela esbarra numa validação
    anterior (`passo-final-diverge`, `laboratorio-sem-calculo`) e o teste
    ficaria verde pelo motivo errado -- provando que a questão é ruim, não que
    ESTA regra a pegou. Partindo de uma que já passa por todas, o único
    motivo possível de recusa é o que se está testando."""
    from services.banks.laboratorio import gerar_desafio_laboratorio_offline

    base = None
    for _ in range(200):
        candidata = gerar_desafio_laboratorio_offline("Matematica", "", "Médio", serie_tipo="EM")
        _, ok, _motivo = validar_questao_gerada(dict(candidata), "Matematica", contexto="laboratorio")
        if ok:
            base = dict(candidata)
            break
    assert base is not None, "nenhuma questão do banco passa nas validações -- a bancada quebrou"

    base.update(extra)
    return base


def test_o_laboratorio_recusa_a_questao_sem_a_formula_complementar():
    _, ok, motivo = validar_questao_gerada(
        _questao_completa(**TELA_DO_ALUNO), "Matematica", contexto="laboratorio"
    )

    assert not ok
    assert motivo == "legenda-com-variavel-sem-formula"


def test_a_mesma_questao_com_a_subformula_passa():
    dados = dict(TELA_DO_ALUNO, subformulas=[r"R = a\sqrt{3}/3"])

    _, ok, motivo = validar_questao_gerada(
        _questao_completa(**dados), "Matematica", contexto="laboratorio"
    )

    assert ok, motivo


@pytest.mark.parametrize("contexto", ["oraculo", "treino", "enem", "rpg", "escape"])
def test_fora_do_laboratorio_a_regra_nao_vale(contexto):
    """`_normalizar_questao_oraculo` apaga fórmula e legenda de propósito nos
    outros modos. Lá a regra não teria o que cruzar e recusaria tudo."""
    _, ok, motivo = validar_questao_gerada(
        _questao_completa(**TELA_DO_ALUNO), "Matematica", contexto=contexto
    )

    assert motivo != "legenda-com-variavel-sem-formula", contexto


# ====================== O PROMPT ======================


def test_o_prompt_manda_a_formula_auxiliar_ser_obrigatoria():
    """A causa da questão sem saída: o prompt dizia "subformulas deve vir
    vazio na maioria dos casos" e a IA obedecia até quando a fórmula auxiliar
    era indispensável."""
    import inspect

    from services.ia import enigma

    fonte = inspect.getsource(enigma)

    assert "REGRA QUE VENCE AS DUAS ACIMA" in fonte
    assert "circulo circunscrito" in fonte, "o exemplo concreto saiu do prompt"


def test_o_prompt_pede_numeros_e_nao_letras_no_passo_da_substituicao():
    """O prompt já pedia "mostrar a substituicao dos valores" e a IA escreveu
    a fórmula com letras. O que faltava era mostrar a forma esperada.

    MELHORIA: este teste casava a frase exata "JA COM OS NUMEROS no lugar das
    letras". Ela mudou de lugar em 09/09 (o modelo de passos virou "<...>",
    porque a prosa dentro de "conteudo" era o que a IA copiava) e o teste
    reprovou uma mudança que só o melhorava. Agora ele cobra a PROPRIEDADE:
    o 3º slot fala em números, e o prompt diz explicitamente que a versão com
    letras não serve ali. A forma de escrever isso pode mudar de novo.

    A estrutura do modelo de passos é cobrada em
    tests/test_prompt_nao_ensina_o_defeito.py."""
    from services.ia.enigma import _prompts_laboratorio

    system, user = _prompts_laboratorio("Matematica", "1º EM", "Médio", "Bhaskara")
    prompt = f"{system}\n{user}"

    terceiro = re.search(r'"3º Passo",\s*"conteudo":\s*"([^"]*)"', prompt)
    assert terceiro, "o 3º passo sumiu do modelo"
    assert "NUMEROS" in terceiro.group(1).upper(), (
        f"o 3º slot nao pede mais numeros: {terceiro.group(1)!r}"
    )

    assert "NUMEROS, nao letras" in prompt, "sumiu a marcacao no exemplo preenchido"
    # No fonte é "{{\\Delta}}" (escape de f-string); no prompt construído, que
    # é o que a IA lê, chega com chave simples.
    assert r"x = (-b \pm \sqrt{\Delta})/(2a)" in prompt, (
        "sumiu o contraexemplo: sem ele o prompt diz o que fazer, mas nao o que NAO fazer"
    )
