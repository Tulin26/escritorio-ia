"""O nível escolhido muda a questão, e a matéria da sala manda no conteúdo.

Achado 5.6 do relatório de QA de 23/09/2026 ("matéria e nível incompatíveis
com o item"), três queixas:

  1. 'Laboratório · Química "Difícil" recebeu o mesmo modelo básico de
     estequiometria do nível Fácil; "Difícil" em outro caso era Q = m·c·ΔT
     direto.'
  2. 'Nível "Médio" com itens de reconhecimento direto -- nomes de 4 biomas;
     média de 7/9/11; datas da 1ª Guerra; distratores como "uma pedra / um
     rio / um animal selvagem".'
  3. 'Sala rotulada Física entregou questão de matriz energética/atualidades,
     sem nenhum conceito físico.'

A primeira tinha causa no código, e é a que este arquivo trava. A dificuldade
do banco do Laboratório saía de `("Facil", "Medio", "Dificil")[indice % 3]`,
e o número de modelos (22 em Matemática, 10 nas outras) não é múltiplo de 3:
TODO modelo aparecia nos três níveis. Somando os cinco bancos, os 63 modelos
apareciam em 189 combinações de nível -- o campo não dizia nada sobre a
questão. Pior: `gerar_desafio_laboratorio_offline` ainda CARIMBAVA o nível
pedido por cima do que tinha sorteado, então a tela mostrava "Difícil" numa
substituição direta, e a pontuação pagava por isso.

Agora cada modelo declara o nível que pede (`_NIVEL_DO_MODELO`), o nível
pedido ESCOLHE a questão, e o rótulo é o verdadeiro.

As outras duas queixas são de questão gerada por IA, e não há como conferir
mecanicamente se um item "exige relacionar dois conceitos". O que dá para
travar é o prompt dizer o que cada nível significa e cobrar conceito da
matéria -- é o que os testes do fim deste arquivo fazem.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

import services.banks.laboratorio as lab
from services.ia.enigma import _prompts_oraculo

BANCOS = [("Matematica", "EM"), ("Fisica", "EM"), ("Quimica", "EM"), ("Matematica", "EF"), ("Ciencias", "EF")]
NIVEIS = ("Facil", "Medio", "Dificil")


def _modelos(materia: str, serie: str) -> dict[str, set[str]]:
    """{tema do modelo: níveis em que ele aparece no banco inteiro}."""
    por_tema: dict[str, set[str]] = defaultdict(set)
    for questao in lab.listar_questoes_laboratorio(materia, serie):
        por_tema[str(questao.get("tema_usado", ""))].add(str(questao.get("dificuldade", "")))
    return por_tema


@pytest.mark.parametrize(("materia", "serie"), BANCOS)
def test_cada_modelo_tem_um_nivel_so(materia, serie):
    # Era exatamente isto que estava quebrado: o mesmo modelo saía como Fácil,
    # Médio e Difícil, dependendo só da posição no banco.
    espalhados = {tema: sorted(niveis) for tema, niveis in _modelos(materia, serie).items() if len(niveis) > 1}

    assert espalhados == {}, f"modelo em mais de um nivel: {espalhados}"


@pytest.mark.parametrize(("materia", "serie"), BANCOS)
def test_os_tres_niveis_existem_no_banco(materia, serie):
    # Sem isto o filtro por nível não teria o que escolher e cairia de volta
    # no banco inteiro, em silêncio.
    niveis = {nivel for niveis in _modelos(materia, serie).values() for nivel in niveis}

    assert set(NIVEIS) <= niveis, f"{materia}/{serie} não tem os três níveis: {sorted(niveis)}"


@pytest.mark.parametrize(("materia", "serie"), BANCOS)
def test_todo_modelo_esta_na_tabela_de_nivel(materia, serie):
    # Quem acrescentar um modelo novo ao banco precisa dizer o nível dele. Sem
    # este teste, o modelo novo voltaria ao rodízio por posição sem ninguém ver.
    fora = [
        tema for tema in _modelos(materia, serie)
        if (materia, tema) not in lab._NIVEL_DO_MODELO
    ]

    assert fora == [], f"modelo sem nivel declarado em _NIVEL_DO_MODELO: {fora}"


@pytest.mark.parametrize(("materia", "serie"), BANCOS)
@pytest.mark.parametrize("nivel", NIVEIS)
def test_o_nivel_pedido_escolhe_a_questao(materia, serie, nivel):
    servidas = [
        lab.gerar_desafio_laboratorio_offline(materia, nivel=nivel, serie_tipo=serie)
        for _ in range(12)
    ]

    assert servidas, "sem questão nenhuma o teste não conferiria nada"
    for desafio in servidas:
        assert desafio.get("dificuldade") == nivel, (
            f'{materia}/{serie} pediu {nivel} e veio "{desafio.get("dificuldade")}" '
            f'no tema "{desafio.get("tema_usado")}"'
        )


def test_o_caso_do_relatorio_quimica_dificil():
    # "Química Difícil recebeu o mesmo modelo básico de estequiometria do
    # nível Fácil": estequiometria é de nível Médio, e não pode mais sair
    # quando o aluno pede Difícil sem escolher esse tema.
    temas = {
        lab.gerar_desafio_laboratorio_offline("Quimica", nivel="Dificil").get("tema_usado")
        for _ in range(20)
    }

    assert "estequiometria" not in temas
    assert temas <= {"pH", "termoquimica", "gases ideais"}, temas


def test_o_tema_escolhido_vence_o_nivel_e_o_rotulo_diz_a_verdade():
    # Quem escolheu "estequiometria" quer estequiometria, mesmo pedindo
    # Difícil. O que não pode voltar a acontecer é a tela dizer "Difícil"
    # numa questão que é de nível Médio -- era o carimbo que existia antes.
    desafio = lab.gerar_desafio_laboratorio_offline("Quimica", tema="estequiometria", nivel="Dificil")

    assert desafio.get("tema_usado") == "estequiometria"
    assert desafio.get("dificuldade") == "Medio"


@pytest.mark.parametrize("nivel", ["Médio", "MEDIO", "medio"])
def test_nivel_com_acento_ou_caixa_diferente_conta_igual(nivel):
    # Doze sorteios seguidos: se a comparação não normalizasse, o filtro não
    # acharia nada, o banco inteiro voltaria a ser candidato e mais cedo ou
    # mais tarde sairia uma questão de outro nível -- que foi o que aconteceu
    # quando a mutação tirou a normalização e um sorteio só ainda passava.
    niveis = {
        lab.gerar_desafio_laboratorio_offline("Fisica", nivel=nivel).get("dificuldade")
        for _ in range(12)
    }

    assert niveis == {"Medio"}, niveis


# --------------------------------------------------------------------------
# O que só o prompt pode cobrar


@pytest.mark.parametrize(
    "trecho",
    [
        # O que cada nível significa (queixa 2 do relatório).
        "nivel Facil: reconhecer ou aplicar UM conceito",
        "nivel Medio: exige relacionar dois conceitos",
        "nivel Dificil: exige comparar, justificar",
        # Conceito da matéria (queixa 3).
        "Tema de atualidades so vale se a pergunta cobrar o conceito da materia",
        # Distrator do mesmo tipo -- vale para 5.6 e para o "os outros 3
        # distratores nem são leis" do 5.5.
        "distratores precisam ser do MESMO tipo da resposta certa",
    ],
)
def test_o_prompt_diz_o_que_o_nivel_e_a_materia_exigem(trecho):
    _, user_prompt = _prompts_oraculo("Fisica", "3º Ano EM", "Medio", "matrizes energeticas e sustentabilidade")

    assert trecho in user_prompt


def test_a_regra_cita_a_materia_da_vez():
    _, user_prompt = _prompts_oraculo("Historia", "3º Ano EM", "Facil", "Era Vargas")

    assert "cobrar um conceito de Historia" in user_prompt
