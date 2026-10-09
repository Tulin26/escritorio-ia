"""Custo do hash de senha e migracao dos hashes antigos."""

from __future__ import annotations

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from core.senhas import METODO_HASH_SENHA, hash_senha, precisa_regravar_hash

ANTIGO = "scrypt:32768:8:1"  # o padrao do werkzeug, usado ate agora


def test_custo_acima_do_padrao_do_werkzeug():
    # MELHORIA: as senhas eram geradas com o padrao do Werkzeug (N = 2^15).
    # A OWASP recomenda 2^17 para scrypt; ficamos em 2^16 por causa dos
    # 512 MB e do worker unico do Render -- ver a docstring de core/senhas.py.
    n_atual = int(METODO_HASH_SENHA.split(":")[1])
    n_werkzeug = int(ANTIGO.split(":")[1])

    assert METODO_HASH_SENHA.startswith("scrypt:")
    assert n_atual > n_werkzeug
    assert n_atual == 65536


def test_hash_novo_sai_com_o_metodo_configurado():
    assert hash_senha("Rillo01").startswith(METODO_HASH_SENHA + "$")


def test_senha_continua_conferindo():
    assert check_password_hash(hash_senha("Rillo01"), "Rillo01")
    assert not check_password_hash(hash_senha("Rillo01"), "errada")


def test_hash_antigo_continua_valido():
    # O formato guarda os proprios parametros, entao hash gerado com custo
    # menor segue conferindo -- e o que permite migrar sem resetar senha.
    antigo = generate_password_hash("Rillo01", method=ANTIGO)

    assert check_password_hash(antigo, "Rillo01")


@pytest.mark.parametrize(
    ("hash_dado", "esperado"),
    [
        (generate_password_hash("x", method=ANTIGO), True),
        (generate_password_hash("x", method=METODO_HASH_SENHA), False),
        ("", False),
        ("formato-desconhecido", True),
    ],
)
def test_reconhece_quem_precisa_regravar(hash_dado, esperado):
    assert precisa_regravar_hash(hash_dado) is esperado


def test_login_regrava_hash_antigo(monkeypatch):
    # MELHORIA: sem isto, so senha NOVA ganharia o custo maior -- os 40
    # alunos ja cadastrados ficariam no custo antigo para sempre.
    from services import aluno_auth_service as auth

    aluno = {
        "id": "a1",
        "nome": "Ronnie",
        "senha_hash": generate_password_hash("Rillo01", method=ANTIGO),
    }
    gravados = {}
    monkeypatch.setattr(auth, "buscar_aluno_por_username", lambda u: aluno)
    monkeypatch.setattr(
        auth, "atualizar_aluno_por_id", lambda aluno_id, dados: gravados.update({aluno_id: dados})
    )

    assert auth.autenticar_aluno_por_username("ronnie", "Rillo01") is not None
    assert gravados["a1"]["senha_hash"].startswith(METODO_HASH_SENHA + "$")


def test_login_nao_regrava_hash_ja_atual(monkeypatch):
    from services import aluno_auth_service as auth

    aluno = {"id": "a1", "senha_hash": hash_senha("Rillo01")}
    gravados = {}
    monkeypatch.setattr(auth, "buscar_aluno_por_username", lambda u: aluno)
    monkeypatch.setattr(
        auth, "atualizar_aluno_por_id", lambda aluno_id, dados: gravados.update({aluno_id: dados})
    )

    assert auth.autenticar_aluno_por_username("ronnie", "Rillo01") is not None
    assert not gravados, "regravou sem necessidade"


def test_falha_ao_regravar_nao_derruba_o_login(monkeypatch):
    # Melhor esforco: o hash antigo continua valido, entao o aluno entra.
    from services import aluno_auth_service as auth

    aluno = {"id": "a1", "senha_hash": generate_password_hash("Rillo01", method=ANTIGO)}

    def _falha(*a, **k):
        raise RuntimeError("supabase fora do ar")

    monkeypatch.setattr(auth, "buscar_aluno_por_username", lambda u: aluno)
    monkeypatch.setattr(auth, "atualizar_aluno_por_id", _falha)

    assert auth.autenticar_aluno_por_username("ronnie", "Rillo01") is not None
