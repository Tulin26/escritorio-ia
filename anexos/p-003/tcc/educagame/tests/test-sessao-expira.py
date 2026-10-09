"""A sessao do Flask nao tinha prazo nenhum.

MELHORIA: o cookie saia assim --

    session=...; HttpOnly; Path=/

-- sem Expires e sem Max-Age. Isso o torna um cookie de sessao do navegador:
o servidor nunca o recusava, e quem decidia a hora de morrer era o navegador,
ao fechar. So que Chrome e Edge com "continuar de onde parei" restauram cookie
de sessao (no Android isso e o normal), entao na pratica o login virava
permanente: abrir o site caia direto no perfil do aluno ou do professor, dias
depois, sem pedir escola nem senha.

Num laboratorio de escola, onde a maquina e compartilhada, quem senta depois
herda a conta de quem levantou -- com o painel do professor junto, se o
anterior for professor.

Sao duas travas porque respondem a coisas diferentes: inatividade conta desde
o ultimo clique, vida maxima conta desde o login. Sem a segunda, uma maquina
aberta o dia inteiro renova a sessao para sempre com qualquer clique.
"""

from __future__ import annotations

import time

import pytest

from core.sessao import (
    CHAVE_INICIO,
    CHAVE_VISTO,
    encerrar,
    marcar_login,
    motivo_de_expiracao,
    revisar,
)
from web.routes import home_fla

MINUTO = 60.0
HORA = 3600.0
AGORA = 1_000_000.0

ESCOLA = {"id": "1", "nome": "ETEC", "slug": "etecata"}


@pytest.fixture(autouse=True)
def _prazos_padrao(monkeypatch):
    # 30 min parado, 12 h desde o login. Fixados aqui para o .env de quem
    # roda os testes nao mudar o resultado.
    monkeypatch.delenv("SESSAO_MINUTOS_INATIVIDADE", raising=False)
    monkeypatch.delenv("SESSAO_HORAS_MAXIMAS", raising=False)


def _sessao(**extras) -> dict:
    sessao = {"usuario_role": "aluno", "escola_slug": "etecata"}
    sessao.update(extras)
    return sessao


# ====================== AS DUAS TRAVAS ======================


def test_sessao_ativa_continua_valendo():
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - MINUTO})

    assert motivo_de_expiracao(sessao, AGORA) == ""


def test_parada_alem_do_limite_expira():
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - 31 * MINUTO})

    assert motivo_de_expiracao(sessao, AGORA) == "inatividade"


def test_atividade_nao_estica_a_vida_maxima():
    # A trava que a inatividade sozinha nao daria: a maquina que fica aberta
    # o dia todo tem clique o tempo inteiro, entao o relogio de inatividade
    # nunca chega ao fim.
    sessao = _sessao(**{CHAVE_INICIO: AGORA - 13 * HORA, CHAVE_VISTO: AGORA - 10.0})

    assert motivo_de_expiracao(sessao, AGORA) == "tempo-maximo"


def test_sessao_sem_carimbo_e_recusada():
    # Sessao com acesso e sem idade so pode ser anterior a esta regra. E o
    # que encerra, no primeiro deploy, os logins eternos ja guardados nos
    # navegadores.
    assert motivo_de_expiracao(_sessao(), AGORA) == "sem-carimbo"


def test_carimbo_no_futuro_nao_vira_sessao_eterna():
    # Se o relogio do servidor andar para tras, "agora - carimbo" fica
    # negativo e nenhuma comparacao de prazo dispara nunca mais.
    sessao = _sessao(**{CHAVE_INICIO: AGORA + HORA, CHAVE_VISTO: AGORA + HORA})

    assert motivo_de_expiracao(sessao, AGORA) == "carimbo-no-futuro"


def test_folga_pequena_de_relogio_nao_derruba_ninguem():
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA + 2.0})

    assert motivo_de_expiracao(sessao, AGORA) == ""


# ====================== AJUSTE POR AMBIENTE ======================


def test_zero_desliga_a_trava_de_inatividade(monkeypatch):
    monkeypatch.setenv("SESSAO_MINUTOS_INATIVIDADE", "0")
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - 5 * HORA})

    assert motivo_de_expiracao(sessao, AGORA) == ""


def test_zero_desliga_a_trava_de_vida_maxima(monkeypatch):
    monkeypatch.setenv("SESSAO_HORAS_MAXIMAS", "0")
    sessao = _sessao(**{CHAVE_INICIO: AGORA - 200 * HORA, CHAVE_VISTO: AGORA - 10.0})

    assert motivo_de_expiracao(sessao, AGORA) == ""


def test_valor_escrito_errado_volta_ao_padrao(monkeypatch):
    # Desligar a trava em silencio por causa de um erro de digitacao seria
    # pior do que ignorar o valor: ninguem veria.
    monkeypatch.setenv("SESSAO_MINUTOS_INATIVIDADE", "trinta")
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - 31 * MINUTO})

    assert motivo_de_expiracao(sessao, AGORA) == "inatividade"


def test_aceita_virgula_decimal(monkeypatch):
    monkeypatch.setenv("SESSAO_MINUTOS_INATIVIDADE", "0,5")
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - 40.0})

    assert motivo_de_expiracao(sessao, AGORA) == "inatividade"


# ====================== REVISAR: CARIMBO E LIMPEZA ======================


def test_visitante_sem_acesso_nao_ganha_carimbo():
    # Carimbar quem ainda nao escolheu escola nem logou so serviria para
    # mandar cookie a quem nao precisa de um.
    sessao: dict = {}

    assert revisar(sessao, AGORA) == ""
    assert sessao == {}


def test_revisar_nao_reescreve_o_carimbo_a_cada_requisicao():
    # Mexer na sessao suja o cookie, e cookie sujo significa um Set-Cookie a
    # mais em toda resposta. Uma vez por minuto basta.
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - 5.0})

    assert revisar(sessao, AGORA) == ""
    assert sessao[CHAVE_VISTO] == AGORA - 5.0


def test_revisar_renova_o_carimbo_depois_do_intervalo():
    sessao = _sessao(**{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - 90.0})

    assert revisar(sessao, AGORA) == ""
    assert sessao[CHAVE_VISTO] == AGORA


def test_revisar_limpa_a_sessao_que_expirou():
    sessao = _sessao(
        aluno_id="a1",
        escola_id="e1",
        _estado_sid="sid-1",
        **{CHAVE_INICIO: AGORA - HORA, CHAVE_VISTO: AGORA - 2 * HORA},
    )

    assert revisar(sessao, AGORA) == "inatividade"
    assert sessao == {}


def test_encerrar_leva_o_estado_do_jogo_junto():
    # E o computador compartilhado de novo: sem tirar o _estado_sid, o
    # proximo aluno no mesmo navegador retomaria o quiz pela metade de quem
    # estava antes. O progresso que importa fica salvo por aluno, entao nada
    # duravel se perde.
    sessao = {"usuario_role": "aluno", "_estado_sid": "sid-1", "csrf_token": "fica"}

    encerrar(sessao)

    assert sessao == {"csrf_token": "fica"}


def test_marcar_login_zera_os_dois_relogios():
    sessao = _sessao(**{CHAVE_INICIO: AGORA - 20 * HORA, CHAVE_VISTO: AGORA - 20 * HORA})

    marcar_login(sessao, AGORA)

    assert motivo_de_expiracao(sessao, AGORA) == ""


# ====================== NO APP DE VERDADE ======================


@pytest.fixture
def _sem_rede(monkeypatch):
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [ESCOLA])
    monkeypatch.setattr(
        home_fla,
        "buscar_escola_por_slug",
        lambda slug: ESCOLA if slug == ESCOLA["slug"] else None,
    )


def _sessao_no_client(client, idade_segundos: float, **extras) -> None:
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_slug"] = ESCOLA["slug"]
        sess["escola_id"] = ESCOLA["id"]
        sess.update(extras)
        agora = time.time()
        sess[CHAVE_INICIO] = agora - idade_segundos
        sess[CHAVE_VISTO] = agora - idade_segundos


def test_voltar_depois_de_parado_pede_escola_e_senha(client, _sem_rede):
    _sessao_no_client(client, idade_segundos=31 * MINUTO)

    resposta = client.get("/", follow_redirects=False)

    assert resposta.status_code == 302
    assert "aviso=sessao_expirada" in resposta.headers["Location"]
    with client.session_transaction() as sess:
        assert "usuario_role" not in sess, "continuaria logado"
        assert "escola_slug" not in sess, "pularia a escolha da escola"


def test_a_tela_de_escolher_escola_explica_o_motivo(client, _sem_rede):
    corpo = client.get("/?aviso=sessao_expirada").data.decode("utf-8")

    assert "Escolha sua escola" in corpo
    assert "expirou" in corpo
    # com aviso na tela, a splash nao pode rodar: ela leva 2,85 s e, com uma
    # escola so, redireciona sozinha antes de a pessoa ler o motivo
    assert "school-splash" not in corpo


def test_sessao_ativa_nao_e_interrompida(client, _sem_rede):
    _sessao_no_client(client, idade_segundos=5 * MINUTO)

    resposta = client.get("/", follow_redirects=False)

    assert "aviso=sessao_expirada" not in resposta.headers.get("Location", "")
    with client.session_transaction() as sess:
        assert sess["usuario_role"] == "aluno"


def test_sessao_antiga_sem_carimbo_cai_no_primeiro_acesso(client, _sem_rede):
    # O que acontece com quem ja esta logado quando esta versao sobe.
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["escola_slug"] = ESCOLA["slug"]

    resposta = client.get("/", follow_redirects=False)

    assert resposta.status_code == 302
    assert "aviso=sessao_expirada" in resposta.headers["Location"]


def test_o_estado_do_jogo_nao_passa_para_o_proximo_aluno(client, _sem_rede):
    _sessao_no_client(client, idade_segundos=31 * MINUTO, _estado_sid="sid-do-anterior")

    client.get("/", follow_redirects=False)

    with client.session_transaction() as sess:
        assert "_estado_sid" not in sess


def test_escolher_escola_carimba_a_sessao(client, _sem_rede):
    # A volta que fecha o ciclo: a escolha acontece DENTRO da view, depois
    # do gate. Sem o carimbo no fim da requisicao, a proxima chegaria "sem
    # idade" e ninguem conseguiria entrar em lugar nenhum.
    client.post(
        "/entrar-escola/" + ESCOLA["id"],
        data={"slug": ESCOLA["slug"]},
        follow_redirects=False,
    )

    with client.session_transaction() as sess:
        assert sess[CHAVE_INICIO] > 0
        assert sess[CHAVE_VISTO] > 0

    seguinte = client.get("/", follow_redirects=False)

    assert "aviso=sessao_expirada" not in seguinte.headers.get("Location", "")


def test_login_carimba_a_sessao(client, monkeypatch):
    import web.routes.auth_fla as auth_fla

    monkeypatch.setattr(
        auth_fla,
        "autenticar",
        lambda username, senha: {"id": "1", "username": "p", "role": "professor"},
    )

    client.post("/login", data={"username": "p", "senha": "x"}, follow_redirects=False)

    with client.session_transaction() as sess:
        assert sess[CHAVE_INICIO] > 0
        assert sess[CHAVE_VISTO] > 0


def test_logout_e_expiracao_limpam_a_mesma_coisa(client, _sem_rede):
    # As duas listas eram separadas e podiam divergir -- "sair" passaria a
    # significar duas coisas no mesmo app. Hoje sao a mesma funcao; isto
    # avisa se voltarem a se separar.
    _sessao_no_client(client, idade_segundos=1.0, aluno_id="a1", _estado_sid="sid")
    client.post("/logout", follow_redirects=False)
    with client.session_transaction() as sess:
        depois_do_logout = {c for c in sess if c != "csrf_token"}

    _sessao_no_client(client, idade_segundos=31 * MINUTO, aluno_id="a1", _estado_sid="sid")
    client.get("/", follow_redirects=False)
    with client.session_transaction() as sess:
        depois_da_expiracao = {c for c in sess if c != "csrf_token"}

    assert depois_do_logout == depois_da_expiracao == set()


def test_o_cookie_continua_sem_prazo_proprio(client):
    # O achado que motivou tudo isto, virado teste: o prazo e do servidor,
    # nao do cookie. Se alguem passar a mandar Expires/Max-Age, a validade
    # volta a depender do relogio de quem acessa -- que e justamente o que
    # nao se pode confiar aqui.
    cookies = client.get("/login").headers.getlist("Set-Cookie")
    cookie_da_sessao = next(c for c in cookies if c.startswith("session="))

    assert "Max-Age" not in cookie_da_sessao
    assert "Expires" not in cookie_da_sessao
    assert "HttpOnly" in cookie_da_sessao


def test_rota_protegida_avisa_em_vez_de_so_mandar_para_o_login(client, _sem_rede):
    # Prova a ordem dos dois before_request: o gate de prazo roda ANTES do
    # gate de login. Se rodasse depois, a pessoa cairia em /login seco, sem
    # saber que foi o tempo parado que a tirou de la -- e sem passar pela
    # escolha da escola.
    _sessao_no_client(client, idade_segundos=31 * MINUTO)

    resposta = client.get("/perfil/", follow_redirects=False)

    assert resposta.status_code == 302
    assert "aviso=sessao_expirada" in resposta.headers["Location"]
