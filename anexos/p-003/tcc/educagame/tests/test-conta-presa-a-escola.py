"""A conta de professor abria todas as escolas.

MELHORIA: `usuarios` nascia sem escola. Só `aluno` carregava unidade (na
tabela `alunos`), então na prática **professor era uma conta global**: bastava
escolher outra escola na lista de entrada para abrir o painel de gestão dela —
alunos, logs, ranking, relatórios.

Visto ao vivo, e com gente de fora envolvida: a conta entregue ao diretor de
uma escola alcançava a outra.

A checagem até existia, mas em um lugar só e para um papel só — dentro da tela
do Streamlit (`st/ui/home_st.py`), com `role == "aluno"` escrito na condição.
O Flask não checava nada: copiava a escola da conta para a sessão e seguia.

Agora é **uma regra só** (`services/auth_service.py::conta_pode_entrar`),
chamada pelos dois frontends, e em dois pontos no Flask — no login e na home.
Os dois pontos existem porque dá para logar antes de escolher escola (basta
abrir `/login` direto), e aí só a home tem as duas pontas na mão.

`desenvolvedor` continua global de propósito: é a conta de manutenção, e o
painel ADM existe justamente para agir sobre todas as escolas.
"""

from __future__ import annotations

import pytest

import web.routes.auth_fla as auth_fla
from services.auth_service import (
    MOTIVO_OUTRA_ESCOLA,
    MOTIVO_SEM_VINCULO,
    conta_pode_entrar,
)
from web.routes import home_fla

from tests.apoio_flask import carimbar_sessao

ETEC = {"id": "esc-etec", "nome": "ETEC", "slug": "etecata"}
DELTA = {"id": "esc-delta", "nome": "Educacional Delta", "slug": "deltaata"}


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch):
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [ETEC, DELTA])
    monkeypatch.setattr(
        home_fla,
        "buscar_escola_por_slug",
        lambda slug: next((e for e in (ETEC, DELTA) if e["slug"] == slug), None),
    )


def _conta(papel: str, escola_id=None) -> dict:
    return {"id": "u1", "username": f"{papel}x", "role": papel, "escola_id": escola_id}


# ====================== A REGRA ======================


def test_professor_entra_na_propria_escola():
    pode, motivo = conta_pode_entrar(_conta("professor", ETEC["id"]), ETEC["id"])

    assert pode
    assert motivo == ""


def test_professor_nao_entra_na_escola_de_outro():
    # O caso real: a conta do diretor da Delta não pode abrir a ETEC.
    pode, motivo = conta_pode_entrar(_conta("professor", DELTA["id"]), ETEC["id"])

    assert not pode
    assert motivo == MOTIVO_OUTRA_ESCOLA


def test_professor_sem_vinculo_e_recusado():
    # Fica registrado porque a tentação é grande de fazer o contrário: "sem
    # escola" era exatamente o estado que abria todas, então tratar como
    # "pode tudo" seria manter o furo com outro nome.
    pode, motivo = conta_pode_entrar(_conta("professor", None), ETEC["id"])

    assert not pode
    assert motivo == MOTIVO_SEM_VINCULO


def test_aluno_segue_a_mesma_regra():
    assert conta_pode_entrar(_conta("aluno", ETEC["id"]), ETEC["id"])[0]
    assert not conta_pode_entrar(_conta("aluno", DELTA["id"]), ETEC["id"])[0]


@pytest.mark.parametrize("vinculo", [None, "esc-etec", "esc-delta"])
def test_desenvolvedor_e_global_de_proposito(vinculo):
    pode, motivo = conta_pode_entrar(_conta("desenvolvedor", vinculo), ETEC["id"])

    assert pode, "o ADM existe justamente para agir sobre todas as escolas"
    assert motivo == ""


def test_sem_escola_escolhida_nao_ha_o_que_comparar():
    # /login aberto direto, antes de escolher escola. Quem barra é a home,
    # que resolve a escola e chama a regra de novo.
    assert conta_pode_entrar(_conta("professor", None), "")[0]
    assert conta_pode_entrar(_conta("professor", DELTA["id"]), None)[0]


def test_compara_como_texto():
    # id vem como uuid do banco e como str da sessão; comparar objetos
    # diferentes daria "escola errada" para a escola certa.
    assert conta_pode_entrar({"role": "professor", "escola_id": 7}, "7")[0]


def test_conta_vazia_nao_passa():
    assert not conta_pode_entrar(None, ETEC["id"])[0]
    assert not conta_pode_entrar({}, ETEC["id"])[0]


# ====================== NO FLASK: O LOGIN ======================


def _com_escola(client, escola: dict) -> None:
    with client.session_transaction() as sess:
        sess["escola_id"] = escola["id"]
        sess["escola_slug"] = escola["slug"]
        sess["escola_nome"] = escola["nome"]
        carimbar_sessao(sess)


def test_login_recusa_professor_de_outra_escola(client, monkeypatch):
    monkeypatch.setattr(auth_fla, "autenticar", lambda u, s: _conta("professor", DELTA["id"]))
    _com_escola(client, ETEC)

    resposta = client.post("/login", data={"username": "p", "senha": "x"})

    assert resposta.status_code == 200, "não pode redirecionar: o login falhou"
    assert "outra escola" in resposta.data.decode("utf-8")
    with client.session_transaction() as sess:
        assert "usuario_role" not in sess, "entrou mesmo assim"


def test_login_recusa_professor_sem_vinculo(client, monkeypatch):
    monkeypatch.setattr(auth_fla, "autenticar", lambda u, s: _conta("professor", None))
    _com_escola(client, ETEC)

    resposta = client.post("/login", data={"username": "p", "senha": "x"})

    assert "não está vinculada" in resposta.data.decode("utf-8")
    with client.session_transaction() as sess:
        assert "usuario_role" not in sess


def test_login_aceita_professor_da_escola_certa(client, monkeypatch):
    monkeypatch.setattr(auth_fla, "autenticar", lambda u, s: _conta("professor", ETEC["id"]))
    _com_escola(client, ETEC)

    resposta = client.post("/login", data={"username": "p", "senha": "x"}, follow_redirects=False)

    assert resposta.status_code == 302
    with client.session_transaction() as sess:
        assert sess["usuario_role"] == "professor"
        assert sess["usuario_escola_id"] == ETEC["id"]


def test_login_aceita_desenvolvedor_em_qualquer_escola(client, monkeypatch):
    monkeypatch.setattr(auth_fla, "autenticar", lambda u, s: _conta("desenvolvedor", None))
    _com_escola(client, DELTA)

    resposta = client.post("/login", data={"username": "d", "senha": "x"}, follow_redirects=False)

    assert resposta.status_code == 302
    with client.session_transaction() as sess:
        assert sess["usuario_role"] == "desenvolvedor"


# ====================== NO FLASK: A SEGUNDA TRANCA ======================


def test_quem_logou_antes_de_escolher_escola_e_barrado_na_home(client):
    # Dá para abrir /login direto, sem escola nenhuma: ali não há o que
    # comparar. A home é o ponto onde as duas pontas existem ao mesmo tempo.
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["usuario_escola_id"] = DELTA["id"]
        sess["escola_slug"] = ETEC["slug"]
        carimbar_sessao(sess)

    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "outra escola" in resposta.data.decode("utf-8")
    assert "Escolha sua escola" in resposta.data.decode("utf-8")


def test_a_home_solta_a_escola_recusada_em_vez_de_repetir_o_erro(client):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["usuario_escola_id"] = DELTA["id"]
        sess["escola_slug"] = ETEC["slug"]
        carimbar_sessao(sess)

    client.get("/")

    with client.session_transaction() as sess:
        assert "escola_slug" not in sess, "manteve a escola recusada na sessao"
        assert sess["usuario_role"] == "professor", "deslogou sem precisar"


def test_a_home_deixa_passar_a_escola_certa(client):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["usuario_escola_id"] = ETEC["id"]
        sess["escola_slug"] = ETEC["slug"]
        carimbar_sessao(sess)

    resposta = client.get("/", follow_redirects=False)

    assert resposta.status_code == 302
    assert "/professor" in resposta.headers["Location"]


def test_o_vinculo_da_conta_nao_se_confunde_com_a_escola_aberta(client):
    # "escola_id" na sessão é reescrito a cada visita à home (é a escola
    # aberta agora). Se o vínculo da conta morasse lá, a checagem compararia
    # a escola consigo mesma e nunca reprovaria nada.
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["usuario_escola_id"] = DELTA["id"]
        sess["escola_slug"] = ETEC["slug"]
        sess["escola_id"] = ETEC["id"]
        carimbar_sessao(sess)

    corpo = client.get("/").data.decode("utf-8")

    assert "outra escola" in corpo


def test_sair_leva_o_vinculo_junto(client):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["usuario_escola_id"] = ETEC["id"]
        carimbar_sessao(sess)

    client.post("/logout", follow_redirects=False)

    with client.session_transaction() as sess:
        assert "usuario_escola_id" not in sess, "o vinculo sobreviveu ao logout"


# ====================== SEM CÓPIA DIVERGENTE ======================


def test_a_tela_do_streamlit_usa_a_regra_compartilhada():
    # A versão anterior desta checagem morava aqui, escrita à mão e só para
    # aluno. Uma cópia por frontend diverge na primeira vez que alguém mexe
    # numa só -- e foi assim que professor ficou de fora da regra.
    from pathlib import Path

    fonte = (Path(__file__).resolve().parent.parent / "st/ui/home_st.py").read_text(
        encoding="utf-8-sig"
    )

    assert "conta_pode_entrar" in fonte
    assert 'usuario.get("role") == "aluno"' not in fonte, "a regra própria voltou"


def test_o_login_guarda_o_vinculo_da_conta_e_nao_a_escola_aberta(client, monkeypatch):
    # O mutante que sobreviveu na primeira rodada: guardar a escola ABERTA
    # como se fosse o vinculo da conta. A checagem passaria a comparar a
    # escola consigo mesma e nunca reprovaria ninguem -- verde por fora,
    # regra desligada por dentro.
    #
    # Usa desenvolvedor porque ele e o unico que consegue logar numa escola
    # diferente da propria; e justamente por isso as duas pontas ficam
    # visiveis na mesma sessao.
    monkeypatch.setattr(auth_fla, "autenticar", lambda u, s: _conta("desenvolvedor", DELTA["id"]))
    _com_escola(client, ETEC)

    client.post("/login", data={"username": "d", "senha": "x"}, follow_redirects=False)

    with client.session_transaction() as sess:
        assert sess["usuario_escola_id"] == DELTA["id"], "guardou a escola aberta, nao a da conta"
        assert sess["escola_id"] == ETEC["id"], "as duas nao podem virar a mesma coisa"


# ====================== O QUE A EXCLUSÃO LEVA JUNTO ======================


def test_os_dois_frontends_avisam_que_a_conta_vai_junto():
    # usuarios.escola_id tem ON DELETE CASCADE: apagada a escola, a conta de
    # professor dela some. É a escolha certa -- SET NULL faria a conta virar
    # GLOBAL em silêncio, que é o problema que a migração existe para tirar --
    # mas muda o que "excluir escola" significa.
    #
    # O aviso do Streamlit listava alunos, logs e RPGs e não citava a conta; o
    # Flask não avisava nada. Aviso que não acompanha o que a ação faz é pior
    # que aviso nenhum: dá confiança errada na hora de clicar.
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    telas = {
        "streamlit": raiz / "st/ui/admin_st.py",
        "flask": raiz / "web/templates/partials/admin_panel.html",
    }

    for onde, caminho in telas.items():
        texto = caminho.read_text(encoding="utf-8-sig")
        assert "conta de professor" in texto, f"{onde}: a exclusão não avisa sobre a conta"
        assert "desfazer" in texto, f"{onde}: não diz que é definitivo"


def test_a_migracao_usa_cascade_e_nao_set_null():
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parent.parent
        / "supabase/migrations/20260831120000_usuarios_escola.sql"
    ).read_text(encoding="utf-8-sig")

    assert "on delete cascade" in sql.lower()
    assert "on delete set null" not in sql.lower(), "SET NULL devolveria a conta ao estado global"
