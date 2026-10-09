"""O enigma que o aluno le: quando trocar, e por qual frase.

Duas coisas moram aqui e conversam entre si:

  _enigma_precisa_de_ajuste  decide se o enigma da IA vale ou vai fora
  _enigma_oracular           escreve a frase generica que entra no lugar

O defeito que estes testes prendem: a primeira casava os sinais como
PEDACO DE TEXTO, entao "ela " batia dentro de "revela " -- e "revela" e das
palavras mais provaveis num texto escrito em tom de profecia. O resultado
era o enigma da IA ser descartado quase sempre, e a segunda sempre devolver
a MESMA frase, porque so usava a primeira de cada par.
"""

from __future__ import annotations

import ast
import io
import re
from pathlib import Path

import pytest

from services.ia.enigma import _enigma_oracular, _enigma_precisa_de_ajuste

PERGUNTA = "Qual e a raiz da funcao?"

MATERIAS = [
    "Portugues", "Historia", "Geografia", "Ciencias",
    "Biologia", "Matematica", "Fisica", "Quimica",
    "Arte",  # fora do dicionario: cai no par generico
]


def _frases_escritas() -> list[str]:
    """Le as frases direto do fonte, inclusive as que o sorteio nao tirou."""
    fonte = Path(__file__).resolve().parent.parent / "services" / "ia" / "enigma.py"
    arvore = ast.parse(io.open(fonte, encoding="utf-8").read())
    fn = next(
        no for no in arvore.body
        if isinstance(no, ast.FunctionDef) and no.name == "_enigma_oracular"
    )
    frases = []
    for no in ast.walk(fn):
        if isinstance(no, ast.JoinedStr):
            partes = [
                v.value if isinstance(v, ast.Constant) else "funcoes de 2o grau"
                for v in no.values
            ]
            frases.append("".join(partes))
    return frases


# --------------------------------------------------------------------------
# a frase de reposicao nao pode ser reprovada pelo proprio criterio
# --------------------------------------------------------------------------


def test_toda_frase_escrita_passa_no_proprio_criterio():
    # Se a frase que entra no lugar do enigma ruim fosse ela mesma reprovada,
    # a troca nao seria uma melhora -- so uma troca.
    reprovadas = [f for f in _frases_escritas() if _enigma_precisa_de_ajuste(f, PERGUNTA)]

    assert not reprovadas, f"frases que a funcao produz e reprovaria: {reprovadas}"


def test_nenhuma_frase_escrita_ficou_orfa():
    # Guarda contra voltar ao "return opcoes[0]", que deixava 9 das 18
    # frases sem nunca chegar na tela.
    escritas = {re.sub(r"\s+", " ", f).strip() for f in _frases_escritas()}
    vistas = {
        re.sub(r"\s+", " ", _enigma_oracular(materia, "funcoes de 2o grau")).strip()
        for materia in MATERIAS
        for _ in range(60)
    }

    assert escritas <= vistas, f"frases inalcancaveis: {sorted(escritas - vistas)}"


@pytest.mark.parametrize("materia", MATERIAS)
def test_cada_materia_tem_mais_de_uma_frase(materia):
    saidas = {_enigma_oracular(materia, "funcoes de 2o grau") for _ in range(60)}

    assert len(saidas) >= 2, f"{materia} sempre devolve o mesmo enigma"


@pytest.mark.parametrize("materia", MATERIAS)
def test_a_frase_sempre_cita_o_tema(materia):
    # O enigma generico existe para substituir o da IA sem perder o assunto.
    for _ in range(20):
        assert "logaritmos" in _enigma_oracular(materia, "logaritmos")


# --------------------------------------------------------------------------
# o filtro: palavra inteira, nao pedaco de palavra
# --------------------------------------------------------------------------


ENIGMAS_BONS = [
    "O tempo revela o que a pressa esconde.",
    "Entre o visivel e o oculto, a medida desvela seu segredo.",
    "O que os alunos do passado buscaram ainda aguarda resposta.",
    "A estrela guia quem entende a proporcao.",
    "O museu do saber guarda a peca que falta.",
    "Seu caminho comeca onde o numero se cala.",
    "Nas sombras do templo, um sinal aguarda quem souber ler.",
    "Um antigo pergaminho sussurra a ordem das grandezas.",
    "Aquilo que se repete guarda a chave do enigma.",
]


@pytest.mark.parametrize("enigma", ENIGMAS_BONS)
def test_enigma_bem_escrito_nao_e_descartado(enigma):
    # revela / desvela / alunos / estrela / museu / seu: todas continham um
    # dos sinais como pedaco de palavra. Numa amostra de 10, 7 eram jogadas
    # fora por isso.
    assert not _enigma_precisa_de_ajuste(enigma, PERGUNTA), enigma


ENIGMAS_LITERAIS = [
    "Qual e a raiz da funcao?",
    "Qual é o valor de x",
    "Assinale a alternativa correta.",
    "Marque a opcao que representa o valor de x.",
    "Escolha entre as quatro alternativas.",
    "Complete a frase com o termo correto.",
    "Identifique o conceito correto.",
    "Voce consegue achar a raiz?",
    "Voces devem calcular a media.",
    "Eu preciso que voce calcule a raiz.",
    "Ela e a medida que voce procura.",
    "Nos vamos calcular juntos o valor.",
    "Nós vamos calcular juntos o valor.",
    "",
    "   ",
]


@pytest.mark.parametrize("enigma", ENIGMAS_LITERAIS)
def test_enigma_literal_continua_sendo_pego(enigma):
    # A metade que importa: afrouxar o filtro nao pode deixar passar
    # instrucao de prova disfarcada de profecia.
    assert _enigma_precisa_de_ajuste(enigma, PERGUNTA), enigma


def test_enigma_igual_a_pergunta_e_descartado():
    assert _enigma_precisa_de_ajuste("O tempo revela tudo.", "O tempo revela tudo.")


def test_enigma_que_termina_em_interrogacao_e_descartado():
    assert _enigma_precisa_de_ajuste("O que o tempo esconde?", PERGUNTA)
