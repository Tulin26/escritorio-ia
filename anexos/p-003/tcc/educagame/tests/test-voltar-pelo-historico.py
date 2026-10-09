"""Voltar ou atualizar no meio da atividade não mostra "Method Not Allowed".

MELHORIA: visto no Laboratório, em produção — o aluno respondeu, apertou voltar
e recebeu a página branca do Werkzeug:

    Method Not Allowed
    The method is not allowed for the requested URL.

As rotas de responder já fazem POST-Redirect-GET certo; o problema não é o
envio, é o **histórico**. Depois do POST para `/laboratorio/responder`, esse
endereço fica no histórico do navegador, e voltar ou atualizar faz o navegador
pedi-lo de novo — como GET. São 41 rotas do app em que isso dá 405.

Tratar no handler do 405, e não acrescentar "GET" em cada rota, é o que evita
esquecer a quadragésima segunda: o handler não precisa saber quais rotas
existem, ele parte do próprio mapa de URLs.
"""

from __future__ import annotations

import pytest

from flask_app import app as flask_app


def _rotas_so_post() -> list[str]:
    return sorted(
        str(regra)
        for regra in flask_app.url_map.iter_rules()
        if (regra.methods - {"HEAD", "OPTIONS"}) == {"POST"} and not regra.arguments
    )


# ====================== O DEFEITO RELATADO ======================


def test_voltar_para_a_rota_de_responder_devolve_a_tela_do_laboratorio(client):
    resposta = client.get("/laboratorio/responder")

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/laboratorio/"


@pytest.mark.parametrize(
    "rota, tela",
    [
        ("/laboratorio/responder", "/laboratorio/"),
        ("/laboratorio/nova", "/laboratorio/"),
        ("/oraculo/responder", "/oraculo/"),
        ("/treino/reiniciar", "/treino/"),
        ("/enem/proxima", "/enem/"),
        ("/boss-rush/responder", "/boss-rush/"),
        ("/escape-room/proxima", "/escape-room/"),
        ("/rpg/escolher", "/rpg/"),
        ("/professor/matricula", "/professor/"),
    ],
)
def test_cada_modo_volta_para_a_propria_tela(client, rota, tela):
    """Voltar para a tela do modo, e não para a home.

    O aluno estava no meio de uma atividade; devolvê-lo à página inicial faria
    ele perder o lugar. A tela do modo retoma de onde parou, porque o estado
    vive na sessão.
    """
    resposta = client.get(rota)

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == tela


def test_rota_sem_modo_proprio_volta_para_a_home(client):
    # `/logout` e `/esqueci-senha` não pertencem a nenhum modo.
    for rota in ("/logout", "/esqueci-senha"):
        assert client.get(rota).headers["Location"] == "/"


def test_toda_rota_so_post_tem_para_onde_voltar(client):
    """A propriedade inteira, e não nove casos.

    É o que faz a rota número 42 já nascer coberta: se alguém acrescentar um
    POST novo, ele entra nesta lista sozinho.
    """
    rotas = _rotas_so_post()

    assert len(rotas) > 30, "a varredura parou de achar as rotas"
    for rota in rotas:
        resposta = client.get(rota)

        assert resposta.status_code == 302, f"{rota} devolveu {resposta.status_code}"
        assert resposta.headers["Location"].endswith("/"), rota


# ====================== O QUE NÃO PODE MUDAR ======================


def test_post_em_rota_que_so_aceita_get_continua_405(client):
    """O 405 existe por um motivo, e continua valendo para quem erra o método.

    Quem manda POST onde só cabe GET é cliente errado, não navegador voltando
    — e precisa receber o erro, não um redirecionamento silencioso.
    """
    assert client.post("/healthz").status_code == 405


def test_rota_inexistente_continua_404(client):
    assert client.get("/nao-existe-mesmo").status_code == 404


def test_o_redirecionamento_e_para_dentro_do_app(client):
    """Nunca para um endereço vindo de fora.

    O destino sai do url_map do próprio app, não do Referer nem de nada que o
    navegador mande — senão isto viraria um redirecionador aberto.
    """
    for rota in _rotas_so_post():
        destino = client.get(
            rota, headers={"Referer": "https://exemplo-malicioso.invalid/"}
        ).headers["Location"]

        assert destino.startswith("/"), destino
        assert not destino.startswith("//"), destino


def test_o_destino_precisa_aceitar_get():
    """Senão o retorno cairia noutra rota só-POST, e o 405 voltaria.

    Hoje nenhuma rota só-POST do app é prefixo de outra, então o filtro é
    defensivo e não dá para exercitá-lo com as rotas reais — foi o único
    defeito plantado que sobreviveu à mutação. Um app de mentira com esse
    formato prende a intenção antes de ela ser necessária.
    """
    import flask

    from flask_app import _tela_de_volta

    app = flask.Flask(__name__)
    app.add_url_rule("/modo/", "tela", lambda: "", methods=["GET"])
    app.add_url_rule("/modo/acao", "acao", lambda: "", methods=["POST"])
    # a armadilha: rota só-POST que é PREFIXO da outra
    app.add_url_rule("/modo/acao/confirmar", "confirmar", lambda: "", methods=["POST"])

    assert _tela_de_volta(app, "/modo/acao/confirmar") == "/modo/"
