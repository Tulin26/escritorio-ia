"""Os textos do RPG sao escritos em ASCII e acentuados na hora de exibir.

Como aplicar_acentos_pt trabalha por dicionario, palavra que nao esta la
chega crua ao aluno. Na mesma tela conviviam "Bussola de retorno" ja
acentuada e "Lente de verificacao" sem acento.
"""

from __future__ import annotations

import unicodedata

import pytest

import services.rpg_service as rpg
from core.text_cleanup import aplicar_acentos_pt


def _sem_acento(texto: str) -> bool:
    return texto == unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("Lente de verificacao", "Lente de verificação"),
        ("Jardim dos Simbolos", "Jardim dos Símbolos"),
        ("Insignia do grupo", "Insígnia do grupo"),
        ("Selo de coerencia", "Selo de coerência"),
        ("Memoria decifrada", "Memória decifrada"),
        ("Astrolabio escolar", "Astrolábio escolar"),
        ("Guardiao Audaz", "Guardião Audaz"),
        ("Lider de Aliancas", "Líder de Alianças"),
        ("Tatico da Masmorra", "Tático da Masmorra"),
        ("cooperacao estrategica", "cooperação estratégica"),
        ("planejamento e logica", "planejamento e lógica"),
        ("Nucleo de Movimento", "Núcleo de Movimento"),
        ("Ampola de Equilibrio", "Ampola de Equilíbrio"),
    ],
)
def test_palavras_do_rpg_recebem_acento(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado


def test_heroico_continua_sem_acento():
    # "heroico" perdeu o acento no Acordo Ortografico de 2009: acentuar
    # aqui seria introduzir um erro, nao corrigir um.
    assert aplicar_acentos_pt("Impulso heroico") == "Impulso heroico"


@pytest.mark.parametrize(
    "ambigua",
    ["so", "da", "e", "de", "a"],
)
def test_palavras_curtas_ambiguas_ficam_fora_do_dicionario(ambigua):
    # "so" casaria com o "so" do ingles e "da" e contracao comum demais.
    # Essas sao corrigidas reescrevendo a frase na origem.
    from core.text_cleanup import _PALAVRAS_PT

    assert ambigua not in _PALAVRAS_PT


def test_nenhum_texto_do_rpg_fica_cru_por_falta_de_dicionario():
    # Varre os dados do RPG e cobra que toda frase longa saia acentuada.
    # As excecoes abaixo sao portugues que realmente nao leva acento.
    sem_acento_legitimo = {
        "ajustar o mecanismo central para abrir uma nova passagem.",
        "arquiteto do conhecimento",
        "diretor vesper, colecionador de respostas sem prova",
        "dividir tarefas entre aliados para juntar pistas que fazem sentido apenas em conjunto.",
        "interpretar sinais de culturas diferentes sem apagar seus significados.",
        "mapa parcial da masmorra",
        "reordenar caminhos que mudam conforme as escolhas feitas pela equipe.",
        "restaurar o arquivo original antes que as fontes sejam reescritas",
        "cada sala preserva uma fonte que contradiz a anterior",
        "seu caminho fica mais forte ao unir recursos, apoio e empatia em cada fase.",
    }

    crus = []
    for nome in dir(rpg):
        valor = getattr(rpg, nome)
        if not (nome.isupper() and isinstance(valor, (list, dict))):
            continue
        itens = valor if isinstance(valor, list) else list(valor.values())
        for item in itens:
            textos = item.values() if isinstance(item, dict) else [item]
            for texto in textos:
                if not isinstance(texto, str) or len(texto.split()) < 5:
                    continue
                exibido = aplicar_acentos_pt(texto)
                if _sem_acento(exibido) and exibido.lower() not in sem_acento_legitimo:
                    crus.append(exibido)

    assert not crus, f"frases sem acento e fora da lista conhecida: {crus}"


@pytest.mark.parametrize(
    ("nome", "preposicao", "esperado"),
    [
        ("Camara Rubra", "em", "na Camara Rubra"),
        ("Jardim dos Simbolos", "em", "no Jardim dos Simbolos"),
        ("Torre do Debate", "em", "na Torre do Debate"),
        ("Arquivo das Runas", "em", "no Arquivo das Runas"),
        ("Sala dos Mapas Vivos", "ate", "ate a Sala dos Mapas Vivos"),
        ("Selo de coerencia", "de", "do Selo de coerencia"),
        ("Lente de verificacao", "de", "da Lente de verificacao"),
        ("Portal da Masmorra", "por", "pelo Portal da Masmorra"),
        ("Escudo runico", "", "o Escudo runico"),
        ("Bussola de retorno", "", "a Bussola de retorno"),
        ("mapa inicial", "", "o mapa inicial"),
    ],
)
def test_artigo_certo_para_cada_nome(nome, preposicao, esperado):
    # MELHORIA: o molde injetava o nome cru -- "Forcar entrada em Camara
    # Rubra usando Escudo runico e protegendo mapa inicial". O genero vem de
    # uma lista fechada, nao de heuristica por terminacao, que erraria em
    # "Ponte", "Torre" e "Mapa".
    assert rpg._com_artigo(nome, preposicao) == esperado


def test_nome_desconhecido_nao_ganha_artigo_errado():
    # Se a IA inventar um local fora da lista, sai sem artigo em vez de
    # sair com o genero errado.
    assert rpg._com_artigo("Cripta Inventada pela IA", "em") == "em Cripta Inventada pela IA"


def test_todo_nome_das_rotas_tem_genero_declarado():
    faltando = []
    for rota in rpg.ROTAS:
        for campo in ("rota", "recurso"):
            nome = str(rota.get(campo) or "")
            if nome not in rpg._GENERO_NOMES:
                faltando.append(nome)

    assert not faltando, f"sem genero declarado: {faltando}"


def test_opcoes_saem_com_artigo():
    textos = " ".join(o["texto"] for o in rpg._criar_opcoes(1, "Matematica"))

    assert "entrada em " not in textos.lower(), textos
    assert "protegendo mapa" not in textos.lower(), textos


def test_resumo_da_jornada_tambem_sai_acentuado():
    # MELHORIA: as opcoes passavam por aplicar_acentos_pt mas resumir_jornada
    # nao, entao no mesmo painel liam-se "Câmara Rubra" e, logo abaixo,
    # "Tatico da Masmorra", "Voce avanca", "Estrategia" e "Cooperacao".
    jornada = rpg.criar_jornada_inicial("Matematica")
    jornada["placar"] = {"Conhecimento": 0, "Estrategia": 3, "Coragem": 0, "Cooperacao": 0}
    resumo = rpg.resumir_jornada(jornada)

    assert resumo["titulo"] == "Tático da Masmorra"
    # com Estrategia dominante, a descricao exibida e a dela
    assert "cenário" in resumo["descricao"]
    assert "decisões" in resumo["descricao"]
    assert resumo["rotulos_placar"]["Estrategia"] == "Estratégia"
    assert resumo["rotulos_placar"]["Cooperacao"] == "Cooperação"
    # a CHAVE continua sem acento: e ela que indexa DESTINOS e o placar salvo
    assert set(resumo["placar"]) == set(rpg.DESTINOS)


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("avanca", "avança"),
        ("mudanca", "mudança"),
        ("intencao", "intenção"),
        ("validacao", "validação"),
        ("divisao", "divisão"),
        ("caldeirao", "caldeirão"),
    ],
)
def test_cedilha_e_til_das_palavras_do_rpg(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado
