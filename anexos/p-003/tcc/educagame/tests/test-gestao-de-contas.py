"""`usuarios` era a única tabela sem tela.

MELHORIA: dava para viver assim enquanto a conta não tinha escola — criar
professor era rodar `scripts/seed_usuarios.py` uma vez e pronto. Isso mudou
quando o vínculo passou a decidir em que unidade a conta entra
(`services/auth_service.py::conta_pode_entrar`): a partir dali, vincular um
professor virou `UPDATE` na mão no Supabase, e **a conta nasce sem vínculo**,
ou seja, nasce sem conseguir entrar em lugar nenhum.

As regras moram no serviço, e não nas telas, porque são duas telas.
"""

from __future__ import annotations

import pytest

import services.usuario_service as contas

ETEC = {"id": "esc-etec", "nome": "ETEC"}
DELTA = {"id": "esc-delta", "nome": "Educacional Delta"}


class _Resposta:
    def __init__(self, data):
        self.data = data


@pytest.fixture
def banco(monkeypatch):
    """Um banco de mentira com as contas em memória."""
    estado = {
        "usuarios": [
            {"id": "u-dev", "username": "desenvolvedor", "role": "desenvolvedor", "ativo": True, "escola_id": None},
            {"id": "u-prof", "username": "professores", "role": "professor", "ativo": True, "escola_id": None},
            {"id": "u-prof2", "username": "professordelta", "role": "professor", "ativo": True, "escola_id": "esc-delta"},
        ],
        "atualizacoes": [],
        "criadas": [],
    }

    def _atualizar(usuario_id, dados):
        estado["atualizacoes"].append((usuario_id, dados))
        for usuario in estado["usuarios"]:
            if str(usuario["id"]) == str(usuario_id):
                usuario.update(dados)
                return _Resposta([usuario])
        return _Resposta([])

    def _criar(username, senha, role, ativo=True, escola_id=None):
        estado["criadas"].append({"username": username, "role": role, "escola_id": escola_id, "senha": senha})
        return _Resposta([{"id": "novo", "username": username}])

    monkeypatch.setattr(contas, "listar_escolas", lambda: [ETEC, DELTA])
    monkeypatch.setattr(contas, "listar_usuarios", lambda: [dict(u) for u in estado["usuarios"]])
    monkeypatch.setattr(contas, "atualizar_usuario", _atualizar)
    monkeypatch.setattr(contas, "criar_usuario", _criar)
    monkeypatch.setattr(
        contas,
        "buscar_usuario_por_username",
        lambda nome: next((u for u in estado["usuarios"] if u["username"] == nome), None),
    )
    return estado


# ====================== A LISTA ======================


def test_a_lista_resolve_o_nome_da_escola(banco):
    por_id = {c["id"]: c for c in contas.listar_contas()}

    assert por_id["u-prof2"]["escola_nome"] == "Educacional Delta"
    assert por_id["u-dev"]["escola_nome"] == ""


def test_a_lista_marca_professor_sem_vinculo(banco):
    # O que a tela precisa destacar não é "tem escola?", é "esta conta
    # consegue entrar?". Professor sem vínculo passa despercebido numa lista
    # -- e simplesmente não entra em unidade nenhuma.
    por_id = {c["id"]: c for c in contas.listar_contas()}

    assert por_id["u-prof"]["sem_vinculo"] is True
    assert por_id["u-prof2"]["sem_vinculo"] is False


def test_desenvolvedor_sem_escola_nao_e_marcado(banco):
    # Ele é global de propósito; marcar como pendência seria pedir para
    # "consertar" o que está certo.
    por_id = {c["id"]: c for c in contas.listar_contas()}

    assert por_id["u-dev"]["sem_vinculo"] is False


# ====================== VINCULAR ======================


def test_vincular_escola(banco):
    ok, erro = contas.vincular_escola("u-prof", "esc-etec")

    assert ok and erro == ""
    assert banco["atualizacoes"][-1] == ("u-prof", {"escola_id": "esc-etec"})


def test_desvincular_grava_nulo_e_nao_string_vazia(banco):
    # Coluna uuid não aceita "" -- e "sem escola" tem que ser NULL para a
    # regra de entrada enxergar como "sem vínculo".
    ok, _ = contas.vincular_escola("u-prof2", "")

    assert ok
    assert banco["atualizacoes"][-1] == ("u-prof2", {"escola_id": None})


def test_vincular_escola_inexistente_e_recusado(banco):
    ok, erro = contas.vincular_escola("u-prof", "esc-que-nao-existe")

    assert not ok
    assert "não existe" in erro
    assert banco["atualizacoes"] == []


def test_vincular_sem_escolher_conta(banco):
    ok, erro = contas.vincular_escola("", "esc-etec")

    assert not ok and "Selecione" in erro


# ====================== ATIVAR E DESATIVAR ======================


def test_desativar_conta(banco):
    ok, erro = contas.definir_ativo("u-prof", False)

    assert ok and erro == ""
    assert banco["atualizacoes"][-1] == ("u-prof", {"ativo": False})


def test_nao_da_para_desativar_o_ultimo_desenvolvedor(banco):
    # Um clique trancaria todo mundo do lado de fora do ADM, e a porta
    # reserva (a Chave Mestra da tela inicial) depende de uma SENHA_MESTRA
    # que pode nem estar configurada. Não haveria tela para desfazer -- só SQL.
    ok, erro = contas.definir_ativo("u-dev", False)

    assert not ok
    assert "última conta de desenvolvedor" in erro
    assert banco["atualizacoes"] == []


def test_com_dois_desenvolvedores_da_para_desativar_um(banco):
    banco["usuarios"].append(
        {"id": "u-dev2", "username": "dev2", "role": "desenvolvedor", "ativo": True, "escola_id": None}
    )

    ok, erro = contas.definir_ativo("u-dev", False)

    assert ok, erro


def test_reativar_o_ultimo_desenvolvedor_sempre_pode(banco):
    # A trava é só para desativar; ligar de volta nunca tranca ninguém.
    banco["usuarios"][0]["ativo"] = False

    ok, erro = contas.definir_ativo("u-dev", True)

    assert ok, erro


# ====================== CRIAR ======================


def test_criar_professor_exige_escola(banco):
    # Conta de professor sem escola nasce muda. Melhor recusar aqui, com o
    # motivo na tela, do que criar e a pessoa descobrir no login.
    ok, erro, senha = contas.criar_conta("prof_novo", "professor", "")

    assert not ok
    assert "escola" in erro.lower()
    assert senha == ""
    assert banco["criadas"] == []


def test_criar_professor_com_escola(banco):
    ok, erro, senha = contas.criar_conta("prof_novo", "professor", "esc-etec")

    assert ok, erro
    assert len(senha) >= 6, "a senha volta em texto: é a única vez que ela existe legível"
    assert banco["criadas"][-1]["escola_id"] == "esc-etec"
    assert banco["criadas"][-1]["role"] == "professor"


def test_criar_desenvolvedor_nao_exige_escola(banco):
    ok, erro, _ = contas.criar_conta("dev_novo", "desenvolvedor", "")

    assert ok, erro


def test_username_duplicado_e_recusado(banco):
    ok, erro, _ = contas.criar_conta("professores", "professor", "esc-etec")

    assert not ok
    assert "Já existe" in erro


def test_username_normalizado_para_minusculas(banco):
    contas.criar_conta("  ProfNovo  ", "professor", "esc-etec")

    assert banco["criadas"][-1]["username"] == "profnovo"


@pytest.mark.parametrize(
    "username, papel, escola",
    [
        ("", "professor", "esc-etec"),
        ("com espaco", "professor", "esc-etec"),
        ("valido", "chefe", "esc-etec"),
        ("valido", "professor", "esc-que-nao-existe"),
    ],
)
def test_entradas_invalidas_nao_criam_nada(banco, username, papel, escola):
    ok, erro, _ = contas.criar_conta(username, papel, escola)

    assert not ok
    assert erro
    assert banco["criadas"] == []


def test_senha_curta_e_recusada(banco):
    ok, erro, _ = contas.criar_conta("prof_novo", "professor", "esc-etec", senha="123")

    assert not ok
    assert "6 caracteres" in erro


# ====================== REDEFINIR SENHA ======================


def test_redefinir_senha_gera_e_devolve_em_texto(banco):
    # O par de redefinir_senha_do_aluno, que já existia. Sem isto, professor
    # que esquece a senha só tem saída pelo SQL.
    ok, erro, senha = contas.redefinir_senha_de_conta("u-prof")

    assert ok, erro
    assert len(senha) >= 6


def test_o_banco_guarda_o_hash_e_nao_a_senha(banco):
    ok, _, senha = contas.redefinir_senha_de_conta("u-prof")

    assert ok
    _, dados = banco["atualizacoes"][-1]
    assert "senha_hash" in dados
    assert senha not in dados["senha_hash"]
    assert dados["senha_hash"].startswith("scrypt:")


def test_redefinir_sem_escolher_conta(banco):
    ok, erro, senha = contas.redefinir_senha_de_conta("")

    assert not ok and "Selecione" in erro and senha == ""


# ====================== A TELA DO FLASK ======================


CONTAS_FALSAS = [
    {"id": "u-dev", "username": "desenvolvedor", "role": "desenvolvedor", "ativo": True,
     "escola_id": "", "escola_nome": "", "sem_vinculo": False},
    {"id": "u-prof", "username": "professores", "role": "professor", "ativo": True,
     "escola_id": "", "escola_nome": "", "sem_vinculo": True},
]


@pytest.fixture
def painel(client, monkeypatch):
    """Painel do professor renderizável, com a rede toda de mentira."""
    import web.routes.professor_fla as professor_fla

    from tests.apoio_flask import carimbar_sessao

    monkeypatch.setattr(professor_fla, "buscar_alunos", lambda *_a, **_k: [])
    monkeypatch.setattr(professor_fla, "buscar_logs", lambda *_a, **_k: [])
    monkeypatch.setattr(professor_fla, "buscar_resumo_turma", lambda *_a, **_k: [])
    monkeypatch.setattr(professor_fla, "listar_escolas", lambda: [ETEC, DELTA])
    monkeypatch.setattr(professor_fla, "listar_rpg_configs", lambda *_a, **_k: [])
    monkeypatch.setattr(professor_fla, "listar_contas", lambda: [dict(c) for c in CONTAS_FALSAS])

    with client.session_transaction() as sess:
        sess["usuario_role"] = "desenvolvedor"
        sess["escola_id"] = ETEC["id"]
        carimbar_sessao(sess)
    return professor_fla


def test_o_painel_mostra_as_contas(client, painel):
    corpo = client.get("/professor/?aba=adm").data.decode("utf-8")

    assert "Contas de login" in corpo
    assert "professores" in corpo
    assert "não entra: sem escola" in corpo, "professor sem vínculo tem que saltar aos olhos"


def test_o_painel_oferece_criar_conta(client, painel):
    corpo = client.get("/professor/?aba=adm").data.decode("utf-8")

    assert "Criar conta" in corpo
    assert 'name="papel"' in corpo


@pytest.mark.parametrize(
    "rota, campos",
    [
        ("/professor/adm/conta/criar", {"username": "x", "papel": "professor", "escola_id": "esc-etec"}),
        ("/professor/adm/conta/escola", {"usuario_id": "u-prof", "escola_id": "esc-etec"}),
        ("/professor/adm/conta/ativo", {"usuario_id": "u-prof", "ativo": "0"}),
        ("/professor/adm/conta/senha", {"usuario_id": "u-prof"}),
    ],
)
def test_professor_nao_alcanca_as_rotas_de_conta(client, monkeypatch, rota, campos):
    # Gestão de contas é do desenvolvedor. Um professor que descubra a URL não
    # pode criar conta nem redefinir senha de ninguém.
    import web.routes.professor_fla as professor_fla

    from tests.apoio_flask import carimbar_sessao

    chamou = []
    for nome in ("criar_conta", "vincular_escola", "definir_ativo", "redefinir_senha_de_conta"):
        monkeypatch.setattr(professor_fla, nome, lambda *_a, **_k: chamou.append(nome))

    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        carimbar_sessao(sess)

    resposta = client.post(rota, data=campos, follow_redirects=False)

    assert resposta.status_code == 302
    assert not chamou, f"{rota} deixou o professor passar"


def test_criar_conta_pela_tela_mostra_a_senha_uma_vez(client, painel, monkeypatch):
    monkeypatch.setattr(painel, "criar_conta", lambda **_k: (True, "", "ab12cd"))

    resposta = client.post(
        "/professor/adm/conta/criar",
        data={"username": "novo", "papel": "professor", "escola_id": ETEC["id"]},
        follow_redirects=False,
    )

    assert "ab12cd" in resposta.headers["Location"], "a senha precisa chegar à tela"


def test_erro_do_servico_vira_mensagem_e_nao_500(client, painel, monkeypatch):
    monkeypatch.setattr(painel, "criar_conta", lambda **_k: (False, "Escolha a escola desta conta.", ""))

    resposta = client.post(
        "/professor/adm/conta/criar",
        data={"username": "novo", "papel": "professor", "escola_id": ""},
        follow_redirects=False,
    )

    assert resposta.status_code == 302
    assert "Escolha" in resposta.headers["Location"]


# ====================== A TELA DO STREAMLIT ======================


def test_a_secao_de_contas_aparece_no_adm_do_streamlit(monkeypatch):
    import importlib
    import sys

    import st.ui.admin_st  # noqa: F401  -- prende a cadeia ao runtime real
    from tests.apoio_streamlit import StreamlitFalso

    with StreamlitFalso(sessao={"usuario": {"id": "1", "role": "desenvolvedor"}}) as fake:
        sys.modules.pop("st.ui.admin_st", None)
        tela = importlib.import_module("st.ui.admin_st")
        monkeypatch.setattr(tela, "listar_escolas", lambda: [ETEC, DELTA])
        monkeypatch.setattr(tela, "listar_contas", lambda: [dict(c) for c in CONTAS_FALSAS])
        monkeypatch.setattr(tela, "buscar_alunos", lambda *_a, **_k: [])
        try:
            tela.tela_administrador()
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:150]}")
        roteiro = fake.roteiro()

    assert not any(linha.startswith("!!") for linha in roteiro), roteiro
    assert any("Contas de login" in linha for linha in roteiro), roteiro
    assert any("Criar conta" in linha for linha in roteiro), roteiro


def test_as_duas_telas_usam_o_mesmo_servico():
    # A garantia contra o que este projeto mais paga: a mesma regra escrita
    # duas vezes, uma por frontend.
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    for onde in ("web/routes/professor_fla.py", "st/ui/admin_st.py"):
        fonte = (raiz / onde).read_text(encoding="utf-8-sig")
        assert "from services.usuario_service import" in fonte, onde
        for funcao in ("criar_conta", "vincular_escola", "definir_ativo", "listar_contas"):
            assert funcao in fonte, f"{onde} não usa {funcao}"


def test_cada_linha_ja_vem_com_a_escola_atual_selecionada(client, monkeypatch, painel):
    # O select troca o vínculo ao mudar (onchange submete). Se a linha viesse
    # sempre em "— sem escola —", um clique distraído desvincularia a conta --
    # e conta de professor sem vínculo não entra em lugar nenhum.
    import re

    monkeypatch.setattr(
        painel,
        "listar_contas",
        lambda: [
            {"id": "u-pd", "username": "professordelta", "role": "professor", "ativo": True,
             "escola_id": DELTA["id"], "escola_nome": DELTA["nome"], "sem_vinculo": False},
        ],
    )

    corpo = client.get("/professor/?aba=adm").data.decode("utf-8")
    bloco = corpo[corpo.index("Contas de login"): corpo.index("Criar conta")]
    selecionadas = re.findall(r'<option value="([^"]*)"\s+selected>', bloco)

    assert selecionadas == [DELTA["id"]], f"selecao errada na linha: {selecionadas}"


def test_a_tela_nao_aninha_formulario(client, painel):
    # Cada linha tem formulários próprios (vínculo, ativar, senha) dentro de
    # uma tabela. <form> dentro de <form> é HTML inválido: o navegador
    # descarta o de dentro em silêncio, e o botão para de fazer efeito.
    import re

    corpo = client.get("/professor/?aba=adm").data.decode("utf-8")

    profundidade = maxima = 0
    for tag in re.findall(r"<form\b|</form>", corpo):
        profundidade += 1 if tag == "<form" else -1
        maxima = max(maxima, profundidade)

    assert maxima == 1, "formulário aninhado: o de dentro seria descartado"
    assert profundidade == 0, "sobrou <form> sem fechar"
