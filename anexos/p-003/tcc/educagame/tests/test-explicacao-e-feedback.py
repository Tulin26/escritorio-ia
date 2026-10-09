"""A explicação e o feedback param de ser texto de gaveta.

MELHORIA: visto na tela numa questão de Educação Física sobre fisiologia do
exercício. A IA escreveu um parágrafo bom sobre ATP e fosfocreatina, e o que
chegou ao aluno foi:

    Esta questão trata de fisiologia do exercício em **Educacao Fisica**.
    [o parágrafo bom]
    **Exemplo:** ao praticar ou estudar fisiologia do exercício, observe
    regras, cooperação e o objetivo da prática corporal.
    A alternativa correta é a que melhor explica o conceito histórico,
    social, cultural ou linguístico pedido no enunciado.

    **O que pode ter confundido:** Você escolheu uma alternativa que parece
    plausível, mas não responde exatamente ao foco da pergunta.
    **Próximo treino:** Treine mais uma questão sobre **Médio**.

Quatro defeitos, todos medidos:

1. **48% do texto na tela era molde** (335 de 650 caracteres). O montador
   tinha quatro vagas fixas e enchia as que sobravam; das quatro, só duas
   podiam vir da IA, então o terceiro parágrafo que ela escreveu era jogado
   fora para dar lugar ao molde.
2. **A chave de normalização vazava para a tela** — "Educacao Fisica". 9 das
   14 matérias perdem acento nessa chave, e `exibir_materia` já existia
   exatamente para isso (a regra "chave × rótulo" deste projeto).
3. **A dificuldade era usada como tema** — "Treine mais uma questão sobre
   Médio", "sobre Difícil". `_tema_curto` tinha `"dificuldade"` na cadeia de
   fallback.
4. **`_feedback_conceitual` só era alcançada em exatas.** Ela nomeia o que o
   aluno marcou e o que era a resposta; todas as outras matérias caíam num
   texto que serve para qualquer questão.
"""

from __future__ import annotations

import pytest

from core.config import MATERIAS, exibir_materia, normalizar_materia
from services.ia.enigma import _explicacao_direta_nao_exatas
from services.pedagogical_feedback import _tema_curto, gerar_feedback_pedagogico

PERGUNTA = "O que limita a duração de um esforço explosivo de até 10 segundos?"
TEMA = "fisiologia do exercício"
EF = normalizar_materia("Educação Física")

TRES_PARAGRAFOS = [
    {"tipo": "texto", "conteudo": "Em esforços explosivos (até 10 s), a energia provém dos estoques de ATP e fosfocreatina presentes nas fibras musculares."},
    {"tipo": "texto", "conteudo": "Quando esses estoques se esgotam, a produção de energia cai abruptamente, limitando a duração do esforço."},
    {"tipo": "resultado", "conteudo": "Outros fatores, como lactato ou oxigenação, entram em ação em esforços mais prolongados."},
]


def explicar(blocos, materia=EF, tema=TEMA):
    return _explicacao_direta_nao_exatas(materia, tema, PERGUNTA, blocos, [])


def textos_de(blocos):
    return [b["conteudo"] for b in blocos if b["tipo"] != "bold"]


# ====================== O QUE A IA ESCREVEU CHEGA À TELA ======================


def test_os_tres_paragrafos_da_ia_aparecem():
    """Antes só dois podiam passar: o terceiro era descartado para o molde
    caber."""
    saida = textos_de(explicar(TRES_PARAGRAFOS))

    for bloco in TRES_PARAGRAFOS:
        assert bloco["conteudo"] in saida, f"sumiu: {bloco['conteudo'][:40]}"


def test_com_conteudo_de_verdade_o_molde_nao_entra():
    saida = " ".join(textos_de(explicar(TRES_PARAGRAFOS)))

    assert "Esta questão trata de" not in saida, "a introdução de gaveta voltou"
    assert "Exemplo: ao estudar" not in saida, "o exemplo de gaveta voltou"
    assert "conceito histórico, social, cultural ou linguístico" not in saida


def test_a_maior_parte_do_texto_passa_a_vir_da_ia():
    """Medido: era 48%. O molde não pode ocupar metade da explicação."""
    blocos = explicar(TRES_PARAGRAFOS)
    da_ia = " ".join(b["conteudo"] for b in TRES_PARAGRAFOS)

    total = sum(len(b["conteudo"]) for b in blocos)
    proprio = sum(len(b["conteudo"]) for b in blocos if b["conteudo"] in da_ia)

    assert proprio / total > 0.8, f"só {100 * proprio // total}% do texto é da IA"


# ====================== O MOLDE AINDA SEGURA O VAZIO ======================


def test_sem_nada_da_ia_o_aluno_ainda_ve_alguma_coisa():
    """Preferir o conteúdo da IA não pode virar tela em branco quando ela
    falha — é o caso em que o molde existe para valer. E o que abre é a
    introdução: ela ao menos nomeia a matéria e o tema, o que o texto de
    gaveta anterior ("Para responder, é importante...") não fazia.
    """
    blocos = textos_de(explicar([]))

    assert blocos, "a explicação ficou vazia"
    assert TEMA in blocos[0] and "Educação Física" in blocos[0]


def test_com_um_paragrafo_so_nao_entra_exemplo_de_gaveta():
    """Antes, um parágrafo sozinho era "completado" com o exemplo de gaveta
    ("ao estudar {tema}, relacione..."). Medido em 13/09/2026: esse texto
    estava em 6 das 14 explicações reais do Oráculo, sem exemplificar nada.
    O parágrafo de verdade fica sozinho.
    """
    blocos = textos_de(explicar([{"tipo": "texto", "conteudo": "A energia vem dos estoques de ATP."}]))

    assert blocos == ["A energia vem dos estoques de ATP."]


def test_o_titulo_continua_nomeando_o_tema():
    blocos = explicar(TRES_PARAGRAFOS)

    assert blocos[0]["tipo"] == "bold"
    assert TEMA in blocos[0]["conteudo"]


# ====================== A CHAVE NÃO VAI PARA A TELA ======================


def test_a_materia_aparece_com_acento_e_nao_como_chave():
    """`normalizar_materia("Educação Física")` é "Educacao Fisica" — chave de
    busca, não rótulo. Ela era impressa direto no texto do aluno.
    """
    saida = " ".join(textos_de(explicar([], materia=EF)))

    assert "Educacao" not in saida
    assert "Educação Física" in saida


@pytest.mark.parametrize("materia", MATERIAS)
def test_nenhuma_materia_vaza_a_chave_sem_acento(materia):
    """9 das 14 matérias têm chave diferente do rótulo. Testar só uma delas
    deixaria as outras oito passarem.
    """
    chave = normalizar_materia(materia)
    rotulo = exibir_materia(chave)
    saida = " ".join(textos_de(explicar([], materia=chave)))

    if chave != rotulo:
        assert chave not in saida, f"a chave {chave!r} apareceu na tela"
    assert rotulo in saida


# ====================== DIFICULDADE NÃO É TEMA ======================


def test_a_dificuldade_nao_vira_tema():
    """Saía "Treine mais uma questão sobre Médio" — as duas, Médio e Difícil,
    vistas na tela."""
    dados = {"dificuldade": "Médio", "materia": "Educacao Fisica"}

    assert _tema_curto(dados) != "Médio"
    assert "Médio" not in gerar_feedback_pedagogico(
        dados=dados, materia="Educacao Fisica", resposta_aluno="A", resposta_correta="B"
    )["treino"]


@pytest.mark.parametrize(
    "dados,esperado",
    [
        ({"tema_usado": "fisiologia do exercício"}, "fisiologia do exercício"),
        ({"objeto_conhecimento": "Sistemas do corpo humano"}, "Sistemas do corpo humano"),
        ({"materia": "LAB-Matematica"}, "Matemática"),
        ({"dificuldade": "Difícil"}, "o mesmo assunto"),
        ({}, "o mesmo assunto"),
    ],
)
def test_a_fila_de_campos_do_tema(dados, esperado):
    assert _tema_curto(dados) == esperado


def test_a_materia_do_tema_perde_o_prefixo_de_modo_e_ganha_acento():
    """Os logs guardam "LAB-Matematica" e "RPG-Fisica" — o prefixo é do modo,
    não do assunto."""
    assert _tema_curto({"materia": "RPG-Fisica"}) == "Física"


# ====================== O FEEDBACK NOMEIA AS ALTERNATIVAS ======================


def feedback(materia, aluno, certa, pergunta=PERGUNTA, tema=TEMA):
    return gerar_feedback_pedagogico(
        dados={"pergunta": pergunta, "tema_usado": tema},
        materia=materia, resposta_aluno=aluno, resposta_correta=certa,
    )


def test_educacao_fisica_passa_a_dizer_o_que_o_aluno_marcou():
    r = feedback("Educacao Fisica",
                 "Acúmulo de lactato nos músculos",
                 "Depleção dos estoques imediatos de ATP e fosfocreatina")

    assert "lactato" in r["confundiu"]
    assert "fosfocreatina" in r["confundiu"]
    assert "parece plausível" not in r["confundiu"], "voltou ao texto de gaveta"


@pytest.mark.parametrize(
    "materia", ["Educacao Fisica", "Historia", "Geografia", "Ingles", "Arte", "Biologia"],
)
def test_toda_materia_nomeia_as_alternativas(materia):
    r = feedback(materia, "Uma alternativa errada e distinta", "A alternativa certa e distinta")

    assert "Uma alternativa errada e distinta" in r["confundiu"]
    assert "A alternativa certa e distinta" in r["confundiu"]


def test_humanas_mantem_o_conselho_proprio():
    """"Volte ao texto e procure a frase que comprova" é conselho de verdade,
    específico da matéria — trocá-lo por um genérico seria piorar.
    """
    r = feedback("Historia", "O avanço da imprensa", "A mecanização da produção têxtil",
                 pergunta="Segundo o texto, qual foi a principal causa da Revolução Industrial?")

    assert "Volte ao texto" in r["evitar"]


def test_ingles_mantem_o_conselho_proprio():
    r = feedback("Ingles", "will go", "went", pergunta="Choose the correct verb tense")

    assert "always" in r["evitar"]


def test_alternativa_que_e_so_rotulo_nao_e_citada():
    """"Você marcou 'B', a resposta é 'A'" não ensina nada — aí o texto por
    matéria é melhor que nomear."""
    r = feedback("Educacao Fisica", "B", "A")

    assert "“B”" not in r["confundiu"]


def test_exatas_continua_com_o_diagnostico_numerico():
    """A conta tem diagnóstico melhor que nomear alternativa: ela compara os
    próprios números. A mudança não pode ter atropelado isso.
    """
    r = gerar_feedback_pedagogico(
        dados={"pergunta": "Qual o valor de x?", "tema_usado": "Bhaskara"},
        materia="Matematica", resposta_aluno="21,8", resposta_correta="19,4",
    )

    assert "arredondamento" in r["confundiu"] or "casa decimal" in r["confundiu"]


# ====================== O EXEMPLO DE EDUCAÇÃO FÍSICA ======================


def test_o_exemplo_de_educacao_fisica_serve_para_teoria():
    """Dizia "observe regras, cooperação e o objetivo da prática corporal" —
    serve para esporte e contradiz o assunto quando o tema é fisiologia, que
    foi o caso visto na tela.
    """
    saida = " ".join(textos_de(explicar([], materia=EF, tema="fisiologia do exercício")))

    assert "regras, cooperação" not in saida
    assert "fisiologia do exercício" in saida
