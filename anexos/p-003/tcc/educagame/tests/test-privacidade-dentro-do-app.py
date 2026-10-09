"""A política de privacidade, alcançável sem login e coerente com o código.

Por que este arquivo existe
----------------------------
Mesmo raciocínio de tests/test_ajuda_dentro_do_app.py: o texto vive em
core/privacidade.py, não escrito duas vezes; e a tela precisa abrir ANTES
do login, porque é o link que a caixa de aceite do cadastro abre e um
responsável que nunca teve conta também precisa achar.

Cada teste de conteúdo aqui verifica um FATO conferido contra o código
(quem recebe dado, o que a IA recebe, etc.) -- não frase solta de modelo de
política de privacidade.
"""

from __future__ import annotations

import core.privacidade as privacidade


def _todo_o_texto() -> str:
    secoes = privacidade.secoes_da_privacidade()
    return " ".join(p for s in secoes for p in s["paragrafos"]).lower()


# ====================== O CONTEÚDO ======================


def test_diz_que_a_ia_nao_recebe_dado_que_identifique_o_aluno():
    """services/ia/enigma.py (_prompts_oraculo/_prompts_laboratorio) só
    manda materia/serie/nivel/tema -- nunca nome, e-mail ou RA. É o fato
    que mais tranquiliza quem lê, e o mais fácil de ficar mentiroso se o
    prompt um dia passar a incluir dado do aluno."""
    texto = _todo_o_texto()

    assert "nunca nome, e-mail" in texto


def test_cita_os_provedores_que_realmente_recebem_dado():
    texto = _todo_o_texto()

    for provedor in ("supabase", "render"):
        assert provedor in texto, f"'{provedor}' sumiu da política, mas hospeda dado real"


def test_nao_promete_exclusao_automatica_que_o_sistema_nao_tem():
    """Desde 28/09/2026 o pedido tem mecanismo (scripts/dados_do_aluno.py e
    scripts/excluir_aluno.py, ver tests/test_dados_pessoais.py), mas quem roda
    é uma pessoa -- não há tela de autoexclusão nem prazo automático. A
    política não pode prometer o que o sistema não faz."""
    texto = _todo_o_texto()

    assert "não tem exclusão automática" in texto
    assert "peça ao professor" in texto or "escreva para" in texto


def test_explica_os_direitos_do_titular():
    texto = _todo_o_texto()

    for termo in ("acessar", "corrigir", "exclusão", "revogar"):
        assert termo in texto, f"direito '{termo}' (LGPD, Art. 18) não está na política"


def test_fala_sobre_dado_de_crianca_e_adolescente():
    texto = _todo_o_texto()

    assert "menor" in texto or "adolesc" in texto


def test_contato_sem_variavel_de_ambiente_orienta_pela_escola(monkeypatch):
    """Sem PRIVACIDADE_CONTATO_EMAIL configurado, a página tem de orientar
    a pedir pela escola -- nunca inventar um endereço de contato."""
    monkeypatch.delenv("PRIVACIDADE_CONTATO_EMAIL", raising=False)

    texto = _todo_o_texto()

    assert "@" not in texto
    assert "professor" in texto and "escola" in texto


def test_contato_usa_a_variavel_de_ambiente_quando_configurada(monkeypatch):
    monkeypatch.setenv("PRIVACIDADE_CONTATO_EMAIL", "privacidade@escola-teste.com")

    texto = _todo_o_texto()

    assert "privacidade@escola-teste.com" in texto


# ====================== A TELA DO FLASK ======================


def test_a_privacidade_abre_sem_login(client):
    resposta = client.get("/privacidade/")

    assert resposta.status_code == 200
    assert "Política de privacidade" in resposta.get_data(as_text=True)


def test_toda_tela_alcanca_a_privacidade(client):
    """Mesmo raciocínio do rodapé da ajuda: login, escolher escola e
    digitar o código zeram o bloco `topnav`, então o link tem de estar no
    rodapé de base.html, que nenhuma tela nasce sem."""
    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sess:
        carimbar_sessao(sess)

    for caminho in ("/", "/login"):
        corpo = client.get(caminho).get_data(as_text=True)
        assert "/privacidade/" in corpo, f"{caminho} não tem como chegar na privacidade"


def test_o_cadastro_linka_a_privacidade_e_exige_o_aceite(client):
    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sess:
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    corpo = client.get("/cadastro").get_data(as_text=True)

    assert "/privacidade/" in corpo
    assert 'name="consentimento"' in corpo
    assert 'type="checkbox"' in corpo
