from __future__ import annotations

from werkzeug.security import generate_password_hash

import services.auth_service as auth_service


def _usuario(username="aluno", senha="aluno", role="aluno", ativo=True):
    return {
        "id": "1",
        "username": username,
        "senha_hash": generate_password_hash(senha),
        "role": role,
        "ativo": ativo,
    }


def test_autentica_com_senha_correta(monkeypatch):
    monkeypatch.setattr(auth_service, "buscar_usuario_por_username", lambda username: _usuario())

    usuario = auth_service.autenticar("aluno", "aluno")

    # escola_id entrou no retorno: e o que prende a conta a uma unidade
    # (ver conta_pode_entrar em services/auth_service.py).
    assert usuario == {"id": "1", "username": "aluno", "role": "aluno", "escola_id": None}


def test_rejeita_senha_errada(monkeypatch):
    monkeypatch.setattr(auth_service, "buscar_usuario_por_username", lambda username: _usuario())

    assert auth_service.autenticar("aluno", "senha-errada") is None


def test_rejeita_usuario_inexistente(monkeypatch):
    monkeypatch.setattr(auth_service, "buscar_usuario_por_username", lambda username: None)

    assert auth_service.autenticar("ninguem", "qualquer") is None


def test_rejeita_usuario_inativo(monkeypatch):
    monkeypatch.setattr(auth_service, "buscar_usuario_por_username", lambda username: _usuario(ativo=False))

    assert auth_service.autenticar("aluno", "aluno") is None
