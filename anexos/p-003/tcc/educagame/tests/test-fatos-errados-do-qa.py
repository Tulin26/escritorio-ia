"""Os erros factuais do achado 4.3 viram âncora no prompt, tema por tema.

Relatório de QA de 23/09/2026, achado 4.3 ("erros factuais e conceituais nas
questões e explicações"). O relatório o classificou como "fora do escopo de
correção automática -- exigiria fixar respostas canônicas no banco, decisão
de produto".

Fixar a QUESTÃO no banco é mesmo decisão de produto: congela o enunciado e
tira a chance de regenerar. Fixar o FATO no prompt não é -- a IA continua
escrevendo a pergunta, as alternativas e a explicação, só não pode mais
inventar um fato diferente do estabelecido. O mecanismo já existia desde
44e40ff (achado 4.2, prioridade #8); aqui ele recebe a lista do 4.3.

Cada caso deste arquivo é uma linha da tabela do relatório, com a fonte do
erro entre parênteses. Medido em 28/09/2026: dos 297 temas sorteáveis do
app, 27 passam a carregar âncora.

Metade da lista não é erro de conceito, e sim nome próprio inventado (uma
usina atribuída à empresa errada, um acordo comercial que não existe, duas
práticas religiosas que nunca existiram). Para esses, além da âncora do tema,
os prompts do Oráculo e do ENEM ganharam uma regra geral de veracidade -- no
ENEM ela precisa ser geral, porque ali não há tema sorteado em que ancorar.
"""

from __future__ import annotations

import pytest

from services.enem_service import _prompt_enem
from services.ia.enigma import _prompts_oraculo
from services.ia.fatos_canonicos import fato_canonico_para_tema


# (tema como o app sorteia, trecho que a âncora precisa trazer, o erro do relatório)
DA_TABELA_DO_RELATORIO = [
    ("fusos horarios", "UTC-5: Acre", 'distrator "UTC-4 (Acre)" — o Acre é UTC-5'),
    ("blocos economicos", "USMCA", "NAFTA citado como bloco vigente"),
    ("comercio internacional", "nao invente", '"Acordo de Livre Comércio da União Europeia" não existe'),
    ("demografia", "taxa de natalidade", "TCN normalizada duas vezes"),
    ("industria", "ArcelorMittal", "usina de João Monlevade atribuída à Usiminas"),
    ("ligacoes quimicas", "reticulo cristalino", '"a atração eletrostática mantém a molécula unida"'),
    ("geometria espacial", "CINCO faces", '"o prisma triangular tem três lados triangulares"'),
    ("radioatividade", "AUMENTA", "decaimento beta-menos descrito como se diminuísse Z"),
    ("estrutura e propriedades dos materiais", "PROPRIEDADES FISICAS", "ponto de ebulição tratado como errado"),
    ("Brasil indigena", "PARA", "povo Xikrin localizado na Bahia"),
    ("tradicoes religiosas", "NAO-TEISTA", 'meditação budista como "presença divina"'),
    ("diversidade religiosa", "Dia de Muertos", "Finados católico com oferendas de alimentos"),
    ("equipamentos eletricos e eletronicos", "PROXIMA DA INCANDESCENTE", 'halógena como eficiência "intermediária"'),
]


@pytest.mark.parametrize(("tema", "trecho", "erro"), DA_TABELA_DO_RELATORIO)
def test_tema_da_tabela_traz_o_fato_certo(tema, trecho, erro):
    fato = fato_canonico_para_tema(tema)

    assert fato, f"tema sem âncora nenhuma: {tema} ({erro})"
    assert trecho in fato, f"a âncora de {tema!r} não corrige {erro}: {fato}"


@pytest.mark.parametrize(
    ("tema", "proibido"),
    [
        # O texto da âncora não pode repetir o erro que veio consertar.
        ("blocos economicos", "NAFTA e um bloco"),
        ("ligacoes quimicas", "molecula de NaCl e mantida"),
        # "diminui" sozinho não serve: o decaimento ALFA diminui mesmo o
        # número atômico, e a âncora diz isso na frase seguinte.
        ("radioatividade", "beta-menos diminui"),
    ],
)
def test_a_ancora_nao_repete_o_erro(tema, proibido):
    assert proibido.lower() not in fato_canonico_para_tema(tema).lower()


@pytest.mark.parametrize(
    "tema",
    [
        # Temas vizinhos que NÃO podem puxar o fato do vizinho: o prisma não
        # tem nada a dizer sobre área de círculo, e estatística não é demografia.
        "geometria plana",
        "estatistica",
        "funcoes do 2o grau e parabola",
        "Revolução Francesa",
    ],
)
def test_tema_vizinho_continua_sem_ancora(tema):
    assert fato_canonico_para_tema(tema) == ""


def test_o_fato_chega_ao_prompt_do_oraculo():
    # Escape Room, RPG e Treino Rápido passam pelo MESMO _prompts_oraculo, então
    # os três recebem a âncora junto -- e é de lá que vêm metade dos casos da
    # tabela (Usiminas, retículo cristalino, prisma, budismo).
    _, user_prompt = _prompts_oraculo("Geografia", "3º Ano EM", "Medio", "fusos horarios")

    assert "UTC-5: Acre" in user_prompt


# --------------------------------------------------------------------------
# A regra geral -- para o que não é conceito, e sim nome próprio inventado


@pytest.mark.parametrize("tema", ["fusos horarios", "Funções da linguagem"])
def test_oraculo_sempre_proibe_nome_proprio_inventado(tema):
    # Vale com âncora e sem âncora: "Cantos de Oração" e "Pregação dos
    # Corações" saíram num tema (Ensino Religioso) que hoje TEM fato fixado,
    # mas o Xikrin saiu de um que não tem.
    _, user_prompt = _prompts_oraculo("Geografia", "3º Ano EM", "Medio", tema)

    assert "nao invente nome proprio" in user_prompt.lower()
    assert "povo indigena" in user_prompt.lower()


def test_enem_proibe_nome_proprio_inventado():
    # No ENEM a regra precisa ser geral: o prompt é montado por ÁREA, sem tema
    # sorteado, e não há onde pendurar uma âncora por assunto. O Xikrin na
    # Bahia saiu justamente daqui.
    _, user = _prompt_enem("Ciencias Humanas e suas Tecnologias", "Medio")

    assert "não invente nome próprio" in user.lower()
    assert "povo indígena" in user.lower()


def test_o_prompt_sem_tema_conhecido_nao_ganha_fato_nenhum():
    # A regra geral entra sempre; o FATO, só quando o tema bate. Sem isso o
    # prompt cresceria em toda questão, e o orçamento de tokens do Groq
    # (8.000 por minuto) é o mesmo para todos os modos.
    _, user_prompt = _prompts_oraculo("Matematica", "3º Ano EM", "Medio", "estatistica")

    assert "fato correto e obrigatorio" not in user_prompt.lower()
