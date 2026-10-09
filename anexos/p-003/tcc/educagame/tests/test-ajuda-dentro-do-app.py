"""A décima heurística: ajuda dentro do app, e uma fonte só de texto.

O que faltava
-------------
A única documentação do EducaGame era um PDF **fora** do sistema, entregue à
mão. Isso falha por dois lados: o aluno que trava no meio de uma questão não
tem onde olhar, e quem tem o PDF pode estar lendo uma versão velha.

Por que o texto não foi escrito de novo
---------------------------------------
Escrever um texto de ajuda novo repetiria o erro noutra forma: seriam duas (e
com o Streamlit, três) descrições dos mesmos oito modos, e a segunda vez que
alguém mexesse numa delas as outras passariam a discordar. Foi exatamente
assim que o guia de acesso envelheceu -- e o conserto de lá (um gerador com
teste) é a razão de o texto existir como dado.

Então `core/ajuda.py` é a fonte, sem marcação, e cada lugar aplica a sua: o
PDF embrulha em `<b>` para o ReportLab, as duas telas renderizam como HTML.
Este arquivo cobra que continuem sendo a mesma fonte.
"""

from __future__ import annotations

import pytest

import core.ajuda as ajuda
from core.sessao import MINUTOS_INATIVIDADE_PADRAO


# ====================== UMA FONTE SÓ ======================


@pytest.mark.parametrize(
    "nome", ["MODOS", "PAINEL_PROFESSOR", "TEXTO_ESPERA", "TEXTO_SESSAO", "TEXTO_QUESTOES"]
)
def test_o_guia_em_pdf_usa_o_MESMO_texto_da_ajuda(nome):
    """Não "um texto parecido": o mesmo objeto. Cópia diverge."""
    from scripts import gerar_guia_acesso

    assert getattr(gerar_guia_acesso, nome) is getattr(ajuda, nome), (
        f"{nome} voltou a ser uma cópia no gerador do PDF"
    )


def test_os_passos_do_pdf_saem_dos_passos_da_ajuda():
    """O PDF marca a URL e o código em negrito, mas as frases são as mesmas.

    Comparado sem a marcação: o que não pode divergir é o que se diz, não como
    se destaca."""
    import re

    from scripts.gerar_guia_acesso import passos_de_entrada as passos_pdf

    do_pdf = [re.sub(r"<[^>]+>", "", texto) for _, texto in passos_pdf("etecata")]
    da_ajuda = ajuda.passos_de_entrada(nome_escola="{nome}", codigo="o código da escola: etecata")

    assert do_pdf == da_ajuda


def test_a_ajuda_nao_traz_marcacao_de_pdf():
    """`<b>` no meio da frase é o que impede o mesmo texto de servir aos dois.
    Se voltar, o HTML mostra a tag crua ou (pior) a interpreta."""
    tudo = [ajuda.TEXTO_ESPERA, ajuda.TEXTO_SESSAO, ajuda.TEXTO_QUESTOES, ajuda.TEXTO_SENHA]
    tudo += [t for _, itens in ajuda.MODOS for _, t in itens]
    tudo += [t for _, t in ajuda.PAINEL_PROFESSOR]
    tudo += ajuda.passos_de_entrada()

    for texto in tudo:
        assert "<" not in texto, f"marcação vazou para o texto compartilhado: {texto[:70]!r}"


# ====================== O CONTEÚDO ======================


def test_o_prazo_da_sessao_e_perguntado_ao_codigo():
    """Foi um número escrito à mão que fez o guia antigo mentir: alguém
    escreveu, o código mudou embaixo e nada reclamou."""
    assert "{minutos}" in ajuda.TEXTO_SESSAO, "o texto virou um número fixo"

    secoes = ajuda.secoes_da_ajuda(minutos_sessao=int(MINUTOS_INATIVIDADE_PADRAO))
    textos = " ".join(t for s in secoes for _, t in s["itens"])

    assert f"{int(MINUTOS_INATIVIDADE_PADRAO)} minutos" in textos
    assert "{minutos}" not in textos, "o molde chegou à tela sem ser preenchido"


def test_a_ajuda_cobre_os_oito_modos():
    nomes = " ".join(nome for _, itens in ajuda.MODOS for nome, _ in itens).lower()

    for modo in ("treino", "enem", "laboratório", "oráculo", "rpg", "escape room", "chefes"):
        assert modo in nomes, f"o modo '{modo}' não está na ajuda"


def test_o_painel_do_professor_so_aparece_para_professor():
    """Pôr na ajuda do aluno uma seção que ele não consegue abrir é ruído, e
    ruído é o que faz ninguém ler a ajuda da próxima vez."""
    do_aluno = ajuda.secoes_da_ajuda(minutos_sessao=30, eh_professor=False)
    do_professor = ajuda.secoes_da_ajuda(minutos_sessao=30, eh_professor=True)

    assert not any(s["id"] == "professor" for s in do_aluno)
    assert any(s["id"] == "professor" for s in do_professor)


def test_a_ajuda_explica_o_codigo_da_escola():
    """A dúvida nº 1 de quem chega, e a que trava logo na primeira tela."""
    passos = " ".join(ajuda.passos_de_entrada()).lower()

    assert "não é uma senha" in passos, "a ajuda não desfaz a confusão código × senha"


# ====================== A TELA DO FLASK ======================


def test_a_ajuda_abre_sem_login(client):
    """Metade das dúvidas ("o que é o código da escola?", "por que demora?")
    acontece ANTES de entrar -- exatamente quando uma página presa atrás do
    login não seria alcançável."""
    resposta = client.get("/ajuda/")

    assert resposta.status_code == 200
    assert "Como usar o EducaGame" in resposta.get_data(as_text=True)


def test_o_aluno_nao_ve_a_secao_do_professor(client):
    corpo = client.get("/ajuda/").get_data(as_text=True)

    assert "Painel do professor" not in corpo
    assert "Contas de Login" not in corpo


def test_o_professor_ve_a_secao_do_professor(client):
    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        carimbar_sessao(sess)

    corpo = client.get("/ajuda/").get_data(as_text=True)

    assert "Painel do professor" in corpo
    assert "Contas de Login" in corpo


def test_a_ajuda_tem_campo_de_busca(client):
    """A décima heurística pede ajuda PESQUISÁVEL. Vinte itens sem filtro
    viram parede de texto, e parede de texto ninguém lê duas vezes.

    MELHORIA: este teste procurava "data-ajuda-busca" em qualquer lugar do
    corpo -- e o atributo também aparece no seletor do JavaScript. Apagá-lo do
    input deixava o campo morto e o teste verde. A mutação mostrou. Agora ele
    exige o atributo DENTRO da tag input, com os itens que o script filtra."""
    import re

    corpo = client.get("/ajuda/").get_data(as_text=True)

    campo = re.search(r"<input[^>]*\bdata-ajuda-busca\b[^>]*>", corpo)
    assert campo, "o campo de busca perdeu o gancho que o script usa"
    assert 'type="search"' in campo.group(0), campo.group(0)

    assert corpo.count("data-ajuda-item") > 5, "sem itens marcados, não há o que filtrar"
    assert "data-ajuda-secao" in corpo


def test_toda_tela_alcanca_a_ajuda(client):
    """No rodapé de base.html, e não só na barra de cima: login, escolher
    escola e digitar o código ZERAM o bloco `topnav` -- e são justamente as
    telas onde se pergunta o que é o código da escola."""
    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sess:
        carimbar_sessao(sess)

    for caminho in ("/", "/login"):
        corpo = client.get(caminho).get_data(as_text=True)
        assert "/ajuda/" in corpo, f"{caminho} não tem como chegar na ajuda"


# ====================== A TELA DO STREAMLIT ======================


def test_o_streamlit_tem_a_pagina_e_o_slug():
    from st.ui.home_st import PAGINAS, PAGINAS_POR_SLUG

    assert "❓ Ajuda" in PAGINAS
    assert PAGINAS_POR_SLUG["ajuda"] == "❓ Ajuda"


def test_a_ajuda_do_streamlit_nao_e_barrada_por_papel():
    """Ela não está em PAGINAS_SO_DE_GESTAO nem em
    PAGINAS_SO_DE_DESENVOLVEDOR: ajuda barrada por papel é ajuda que falta a
    quem mais precisa."""
    from st.ui.home_st import PAGINAS_SO_DE_DESENVOLVEDOR, PAGINAS_SO_DE_GESTAO

    assert "❓ Ajuda" not in PAGINAS_SO_DE_GESTAO
    assert "❓ Ajuda" not in PAGINAS_SO_DE_DESENVOLVEDOR


def test_a_busca_do_streamlit_ignora_acento():
    """No teclado do celular o acento nem costuma ser sugerido: quem digita
    "duvida" tem de achar "dúvida"."""
    from st.ui.ajuda_st import _sem_acento

    assert _sem_acento("Matemática") == "matematica"
    assert _sem_acento("SESSÃO") == "sessao"
