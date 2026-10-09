from __future__ import annotations

from flask import request


def _cliente_com_rota_de_ip():
    """App proprio, com uma rota que devolve o IP que ele enxerga.

    MELHORIA: antes registrava a rota no app COMPARTILHADO da fixture
    "client". O Flask recusa add_url_rule depois que o app atendeu a
    primeira requisicao, entao o teste so passava enquanto nenhum outro
    tivesse feito request antes -- uma dependencia de ordem invisivel, que
    quebrou quando um arquivo de teste novo entrou no meio do alfabeto.
    Cada teste daqui monta o seu.
    """
    from flask_app import criar_app

    app = criar_app()
    app.add_url_rule("/__ip_teste", "_ip_visto", lambda: {"visto": request.remote_addr})
    return app.test_client()


def test_alunos_atras_do_proxy_recebem_ips_distintos():
    # MELHORIA: regressao para um problema real de producao. No Render o app
    # roda atras de um proxy, entao request.remote_addr trazia o IP DO PROXY
    # -- igual para todo mundo. Como o Flask-Limiter usa esse endereco como
    # chave (core/rate_limit.py), a turma inteira dividia um unico balde: com
    # "20 per hour" no login, o 21o aluno levaria 429 no primeiro acesso dele.
    c = _cliente_com_rota_de_ip()

    primeiro = c.get(
        "/__ip_teste", environ_base={"REMOTE_ADDR": "10.0.0.1"}, headers={"X-Forwarded-For": "201.10.20.30"}
    )
    segundo = c.get(
        "/__ip_teste", environ_base={"REMOTE_ADDR": "10.0.0.1"}, headers={"X-Forwarded-For": "187.55.44.33"}
    )

    assert primeiro.json["visto"] == "201.10.20.30"
    assert segundo.json["visto"] == "187.55.44.33"
    assert primeiro.json["visto"] != segundo.json["visto"]


def test_cliente_nao_consegue_forjar_o_proprio_ip():
    # O proxy acrescenta o IP real DEPOIS do que o cliente mandou, e x_for=1
    # le apenas a ultima entrada -- entao o valor injetado e ignorado. Se
    # alguem aumentar esse numero sem necessidade, este teste quebra.
    c = _cliente_com_rota_de_ip()

    resposta = c.get(
        "/__ip_teste",
        environ_base={"REMOTE_ADDR": "10.0.0.1"},
        headers={"X-Forwarded-For": "9.9.9.9, 201.10.20.30"},
    )

    assert resposta.json["visto"] == "201.10.20.30"
    assert resposta.json["visto"] != "9.9.9.9"


def test_sem_proxy_continua_usando_o_ip_direto():
    # Desenvolvimento local nao passa por proxy nenhum: sem X-Forwarded-For,
    # o comportamento tem que seguir igual ao de antes.
    c = _cliente_com_rota_de_ip()

    resposta = c.get("/__ip_teste", environ_base={"REMOTE_ADDR": "127.0.0.1"})

    assert resposta.json["visto"] == "127.0.0.1"
