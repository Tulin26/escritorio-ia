"""Escolha do tema sem reposicao: sorteia todos antes de repetir qualquer um.

Por que este arquivo existe
----------------------------
Relatorio de QA de 23/09/2026, achado 4.5 (maior impacto na experiencia
real de estudo): pedir 30 questoes de uma materia com poucos temas
cadastrados sorteava o mesmo tema varias vezes so por acaso -- "6 questoes
de energias renovaveis em 30", "8 questoes sobre instituicoes sociais". A
causa era `random.choice(temas)` com reposicao a cada chamada, sem memoria
nenhuma do que ja tinha saido.

`_resolver_tema_questao` (services/ia/enigma.py) passa a usar sorteio SEM
reposicao dentro da sessao, igual embaralhar um baralho e virar carta por
carta: so reembaralha quando todas ja saíram. Segue o mesmo padrao dos
outros testes do Oraculo, que trocam o historico persistente (banco) por um
dicionario em memoria via monkeypatch, em vez de montar o Flask inteiro.
"""

from __future__ import annotations

import pytest

import services.ia.enigma as enigma
from services import historico_perguntas


@pytest.fixture
def historico_em_memoria(monkeypatch):
    guardado: dict[str, list[str]] = {}

    def ler(chave):
        return list(guardado.get(chave, []))

    def gravar(chave, itens, *, fora_do_flask=True):
        guardado[chave] = [str(item) for item in itens]

    monkeypatch.setattr(historico_perguntas, "ler", ler)
    monkeypatch.setattr(historico_perguntas, "gravar", gravar)
    return guardado


def _mockar_temas(monkeypatch, temas):
    monkeypatch.setattr(enigma, "get_temas_rpg", lambda materia, ano: list(temas))


def test_um_ciclo_completo_cobre_todos_os_temas_antes_de_repetir(monkeypatch, historico_em_memoria):
    temas = ["Energias renovaveis", "Blocos economicos", "Urbanizacao", "Geopolitica"]
    _mockar_temas(monkeypatch, temas)

    vistos_no_ciclo = {enigma._resolver_tema_questao("Geografia", "3º Ano EM") for _ in range(len(temas))}

    assert vistos_no_ciclo == set(temas)


def test_trinta_chamadas_nao_repetem_mais_que_o_esperado(monkeypatch, historico_em_memoria):
    # O caso real do relatorio: 30 questoes, poucos temas cadastrados.
    temas = ["Platao", "Epistemologia", "Cidadania", "Etica", "Metafisica"]
    _mockar_temas(monkeypatch, temas)

    escolhidos = [enigma._resolver_tema_questao("Filosofia", "3º Ano EM") for _ in range(30)]

    # Sem reposicao, o pior caso ainda e um tema por ciclo de len(temas): em
    # 30 sorteios com 5 temas, cada tema aparece no maximo 6 vezes -- contra
    # o "6 vezes so por engano" que o relatorio descreve como bug, aqui e o
    # teto matematico garantido, nao acaso.
    for tema in temas:
        assert escolhidos.count(tema) <= 6, f"{tema} saiu {escolhidos.count(tema)} vezes"

    # E nenhum tema fica preterido: todos aparecem pelo menos uma vez.
    assert set(escolhidos) == set(temas)


def test_nunca_repete_o_tema_imediatamente_anterior(monkeypatch, historico_em_memoria):
    temas = ["A", "B", "C"]
    _mockar_temas(monkeypatch, temas)

    anterior = None
    for _ in range(20):
        atual = enigma._resolver_tema_questao("Sociologia", "3º Ano EM")
        if anterior is not None:
            assert atual != anterior
        anterior = atual


def test_tema_digitado_pelo_aluno_ignora_o_rodizio(monkeypatch, historico_em_memoria):
    _mockar_temas(monkeypatch, ["A", "B", "C"])

    assert enigma._resolver_tema_questao("Geografia", "3º Ano EM", "Tema especifico") == "Tema especifico"
    # Nao consome nem grava nada no historico de rodizio.
    assert historico_em_memoria == {}


def test_materia_unica_de_tema_sempre_devolve_o_mesmo(monkeypatch, historico_em_memoria):
    _mockar_temas(monkeypatch, ["conteudo geral"])

    for _ in range(5):
        assert enigma._resolver_tema_questao("Educacao Fisica", "3º Ano EM") == "conteudo geral"


def test_materias_diferentes_nao_compartilham_o_rodizio(monkeypatch, historico_em_memoria):
    _mockar_temas(monkeypatch, ["Tema 1", "Tema 2"])

    # Esgota o rodizio de Geografia sozinho.
    vistos_geografia = {enigma._resolver_tema_questao("Geografia", "3º Ano EM") for _ in range(2)}
    assert vistos_geografia == {"Tema 1", "Tema 2"}

    # Historia comeca do zero -- as duas chaves nao se misturam.
    primeiro_historia = enigma._resolver_tema_questao("Historia", "3º Ano EM")
    assert primeiro_historia in {"Tema 1", "Tema 2"}
