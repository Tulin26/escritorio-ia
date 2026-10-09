"""O que muda no progresso do aluno quando ele clica — XP, HP e histórico.

MELHORIA: estas seis funções moravam dentro das duas maiores funções do
projeto, `renderizar_tela_rpg` (339 linhas) e `_renderizar_desafio_rpg`
(277). Nenhuma delas desenha nada, e nenhuma tinha teste.

`tests/test_tela_rpg.py` prende o **roteiro** de cada tela: o que o aluno vê
em cada estado. O que ele não alcançava era o clique — nele o XP sobe, o HP
cai e a crônica ganha uma linha, e era justamente o pedaço sem rede. É o que
este arquivo cobre.

Os dois lugares onde o progresso muda são gêmeos e fáceis de confundir:

  * `aplicar_escolha_ao_estado` — na hora de **escolher a ação**, antes de
    qualquer pergunta: o dado é rolado e a escolha já cobra o preço dela;
  * `aplicar_resposta_ao_estado` — na hora de **responder o desafio**.

Os dois somam XP e tiram HP, os dois têm piso em zero, e cada um tem o seu
motivo para isso.
"""

from __future__ import annotations

import pytest

import services.rpg_service as rpg_engine
from st.ui.tela_rpg_st import (
    aplicar_escolha_ao_estado,
    aplicar_resposta_ao_estado,
    contexto_do_desafio,
    guardar_desafio_no_estado,
    log_da_resposta_rpg,
    passo_da_cronica,
)

DESAFIO = {
    "pergunta": "Qual o valor de x em 2x = 10?",
    "opcoes": ["5", "10", "2", "20"],
    "correta": 0,
    "explicacao": "Divida os dois lados por 2.",
    "tema_usado": "Equações do 1º grau",
}
CONFIG = {"id": "av-1", "titulo": "A Torre", "materia": "Matemática"}
OPCAO = {
    "id": "op-1", "texto": "Entrar na torre", "rota": "torre", "risco": "medio",
    "impacto_destino": "conhecimento", "chance_sucesso": 70, "recurso": "Tocha",
}


def estado(**mudancas):
    base = {
        "xp": 30, "hp": 100, "fase": 3,
        "historico": [], "historico_desafios": [], "temas_usados": [],
        "ultima_escolha": OPCAO, "ultima_checagem_escolha": {"bonus_risco_ativo": True},
    }
    base.update(mudancas)
    return base


def responder(indice, **mudancas):
    est = estado(**mudancas)
    acertou, resultado = aplicar_resposta_ao_estado(est, DESAFIO, CONFIG, indice, rpg_engine)
    return est, acertou, resultado


CERTA = DESAFIO["correta"]
ERRADA = (DESAFIO["correta"] + 1) % len(DESAFIO["opcoes"])


# ====================== RESPONDER O DESAFIO ======================


def test_acertar_soma_xp_e_nao_tira_hp():
    est, acertou, resultado = responder(CERTA)

    assert acertou
    assert est["xp"] == 30 + resultado["xp_ganho"]
    assert resultado["xp_ganho"] > 0, "acertar tem de valer alguma coisa"
    assert est["hp"] == 100


def test_errar_tira_hp_e_nao_soma_xp():
    est, acertou, resultado = responder(ERRADA)

    assert not acertou
    assert est["xp"] == 30
    assert est["hp"] == 100 - resultado["hp_perda"]
    assert resultado["hp_perda"] > 0, "errar tem de custar alguma coisa"


def test_o_hp_para_em_zero_e_nao_fica_negativo():
    """A barra de vida desenha `hp`. Negativo desenharia uma barra quebrada,
    e o "herói caiu" é decidido por `hp <= 0` — que já vale no zero."""
    est, _, resultado = responder(ERRADA, hp=1)

    assert resultado["hp_perda"] > 1, "o teste só prova o piso se o dano passar do HP"
    assert est["hp"] == 0


def test_acertar_gera_recompensa_e_errar_nao():
    acertou_est, _, _ = responder(CERTA)
    errou_est, _, _ = responder(ERRADA)

    assert acertou_est["recompensa_pendente"]
    assert errou_est["recompensa_pendente"] is None


def test_a_recompensa_anterior_e_limpa_antes_da_nova():
    """Sem isto o item da fase passada reaparece na tela da fase seguinte."""
    est, _, _ = responder(ERRADA, ultima_recompensa_item={"item": "Amuleto velho"})

    assert est["ultima_recompensa_item"] is None


def test_a_resposta_entra_no_historico_com_o_que_o_professor_precisa():
    est, _, resultado = responder(ERRADA)

    assert len(est["historico_desafios"]) == 1
    linha = est["historico_desafios"][0]
    assert linha["acertou"] is False
    assert linha["resposta_aluno"] == DESAFIO["opcoes"][ERRADA]
    assert linha["resposta_correta"] == DESAFIO["opcoes"][CERTA]
    assert linha["pergunta"] == DESAFIO["pergunta"]
    assert linha["fase"] == 3
    assert linha["materia"] == "Matemática"
    assert linha["tema"] == DESAFIO["tema_usado"]
    assert linha["xp_ganho"] == resultado["xp_ganho"]
    assert linha["hp_perda"] == resultado["hp_perda"]


def test_o_historico_acumula_em_vez_de_substituir():
    """É o relatório em PDF da aventura inteira: perder as fases anteriores
    esvaziaria o relatório do aluno."""
    est = estado()
    aplicar_resposta_ao_estado(est, DESAFIO, CONFIG, CERTA, rpg_engine)
    aplicar_resposta_ao_estado(est, DESAFIO, CONFIG, ERRADA, rpg_engine)

    assert [linha["acertou"] for linha in est["historico_desafios"]] == [True, False]


def test_o_historico_nasce_sozinho_se_faltar():
    """Progresso salvo antes desta versão pode voltar sem a chave."""
    est = estado()
    del est["historico_desafios"]

    aplicar_resposta_ao_estado(est, DESAFIO, CONFIG, CERTA, rpg_engine)

    assert len(est["historico_desafios"]) == 1


def test_a_tela_fica_sabendo_que_ja_foi_respondido():
    """`desafio_respondido` é o que faz a tela trocar as alternativas pelo
    resultado — sem ele o aluno responderia a mesma pergunta de novo."""
    est, _, _ = responder(CERTA)

    assert est["desafio_respondido"] is True
    assert est["desafio_acertou"] is True
    assert est["ultimo_resultado_risco"]


# ====================== ESCOLHER A AÇÃO ======================


def test_a_escolha_registra_a_checagem_e_a_propria_escolha():
    """A tela seguinte desenha a rota, o recurso e o resultado da rolagem a
    partir destas duas chaves."""
    est = estado(ultima_escolha=None, ultima_checagem_escolha=None)

    resultado = aplicar_escolha_ao_estado(est, OPCAO, 3, rpg_engine)

    assert est["ultima_escolha"] == OPCAO
    assert est["ultima_checagem_escolha"] == resultado
    assert "rolagem" in resultado


def test_a_escolha_tambem_tem_piso_em_zero_no_hp(monkeypatch):
    """O gêmeo de `test_o_hp_para_em_zero_e_nao_fica_negativo`: o dano da
    escolha vem antes da pergunta, e o piso tem de valer nos dois.

    O dano é forçado porque o do motor real nunca passou de 1 HP nesta cena —
    e um dano menor que o HP não encosta no piso: o teste passava com o `max`
    arrancado.
    """
    monkeypatch.setattr(
        rpg_engine, "resolver_tentativa_acao",
        lambda *_a, **_k: {"xp_imediato": 0, "hp_perda_imediata": 99},
    )
    est = estado(hp=5)

    aplicar_escolha_ao_estado(est, OPCAO, 3, rpg_engine)

    assert est["hp"] == 0


def test_a_escolha_so_mexe_no_xp_quando_ha_xp_imediato(monkeypatch):
    monkeypatch.setattr(
        rpg_engine, "resolver_tentativa_acao",
        lambda *_a, **_k: {"xp_imediato": 0, "hp_perda_imediata": 0},
    )
    est = estado()

    aplicar_escolha_ao_estado(est, OPCAO, 3, rpg_engine)

    assert est["xp"] == 30
    assert est["hp"] == 100


def test_o_xp_e_o_dano_imediatos_sao_aplicados(monkeypatch):
    monkeypatch.setattr(
        rpg_engine, "resolver_tentativa_acao",
        lambda *_a, **_k: {"xp_imediato": 7, "hp_perda_imediata": 11},
    )
    est = estado()

    aplicar_escolha_ao_estado(est, OPCAO, 3, rpg_engine)

    assert est["xp"] == 37
    assert est["hp"] == 89


def test_a_escolha_avanca_a_jornada():
    """A jornada é o que decide o final da aventura — cada escolha pesa nela."""
    est = estado(jornada=None)

    aplicar_escolha_ao_estado(est, OPCAO, 3, rpg_engine)

    assert est["jornada"]


# ====================== ARMAR O DESAFIO ======================


def test_armar_o_desafio_liga_a_espera_e_zera_a_resposta():
    est = estado(desafio_respondido=True, recompensa_pendente=[{"item": "velho"}])

    guardar_desafio_no_estado(est, DESAFIO, OPCAO)

    assert est["aguardando_desafio"] is True
    assert est["desafio_atual"] == DESAFIO
    assert est["desafio_respondido"] is False
    assert est["recompensa_pendente"] is None
    assert est["ultima_recompensa_item"] is None
    assert est["acao_pendente"] == OPCAO["texto"]


def test_o_tema_e_anotado_uma_vez_so():
    """A lista alimenta o gerador para ele não repetir tema. Repetir aqui
    faria o aluno ver a mesma matéria fase após fase."""
    est = estado(temas_usados=["Frações"])

    guardar_desafio_no_estado(est, DESAFIO, OPCAO)
    guardar_desafio_no_estado(est, DESAFIO, OPCAO)

    assert est["temas_usados"] == ["Frações", DESAFIO["tema_usado"]]


def test_desafio_sem_tema_nao_suja_a_lista():
    est = estado(temas_usados=["Frações"])

    guardar_desafio_no_estado(est, dict(DESAFIO, tema_usado=""), OPCAO)

    assert est["temas_usados"] == ["Frações"]


# ====================== A CRÔNICA E O LOG ======================


def test_a_cronica_guarda_a_acao_e_o_que_veio_depois():
    cena = {"local_atual": "Portal", "narracao": "A equipe atravessa."}
    nova_cena = {"narracao": "A torre se abre."}
    checagem = {"texto_resultado": "Sucesso", "chance_sucesso": 70, "rolagem": 42}

    passo = passo_da_cronica(cena, OPCAO, checagem, 3, nova_cena)

    assert passo["local"] == "Portal"
    assert passo["acao"] == OPCAO["texto"]
    assert passo["fase"] == 3
    assert passo["rolagem"] == 42
    assert passo["narracao_resultante"] == "A torre se abre."
    assert passo["resultado"] == "sem_desafio", "esta crônica é a do caminho sem pergunta"


def test_a_fase_da_cronica_e_a_de_agora_e_nao_a_seguinte():
    """A fase é incrementada logo depois, na tela. Se a crônica lesse o estado
    em vez do parâmetro, cada linha sairia com a fase errada."""
    assert passo_da_cronica({}, OPCAO, {}, 7, {})["fase"] == 7


def test_o_log_diz_acertou_ou_errou_e_de_qual_materia():
    log = log_da_resposta_rpg(DESAFIO, CONFIG, {"id": "aluno-1"}, "escola-1", "5", True)

    assert log["resultado"] == "Acertou"
    assert log["modo"] == "rpg"
    assert log["materia"] == "RPG-Matemática", "o painel separa RPG do quiz por este prefixo"
    assert log["aluno_id"] == "aluno-1"
    assert log["escola_id"] == "escola-1"
    assert log["resposta_aluno"] == "5"
    assert log["resposta_correta"] == DESAFIO["opcoes"][CERTA]


def test_o_log_de_erro_nao_vira_acerto():
    log = log_da_resposta_rpg(DESAFIO, CONFIG, {"id": "aluno-1"}, "escola-1", "10", False)

    assert log["resultado"] == "Errou"


@pytest.mark.parametrize("explicacao", [None, "", [{"tipo": "texto", "conteudo": "x"}]])
def test_a_explicacao_do_log_e_sempre_texto(explicacao):
    """A coluna do banco é texto; a explicação da IA às vezes vem como lista."""
    log = log_da_resposta_rpg(
        dict(DESAFIO, explicacao=explicacao), CONFIG, {"id": "a"}, "e", "5", True
    )

    assert isinstance(log["explicacao_ia"], str)


# ====================== AS ETIQUETAS ACIMA DA PERGUNTA ======================
#
# `contexto_do_desafio` devolve uma lista, então dá para conferir direto. Os
# testes de roteiro em `test_tela_rpg.py` não alcançam estes chips: eles saem
# dentro de um bloco de HTML grande, que o roteiro corta antes de chegar lá —
# medido, os cinco mutantes destes `if` sobreviviam com a suíte verde.


ESCOLHA_CHEIA = {
    "rota": "Torre Norte",
    "destino_titulo": "Salão dos Ecos",
    "icone_destino": "🏰",
    "recurso": "Tocha",
    "foco_aprendizado": "Equações",
}


def chips(config=None, desafio=None, escolha=None):
    return contexto_do_desafio(
        CONFIG if config is None else config,
        DESAFIO if desafio is None else desafio,
        {} if escolha is None else escolha,
    )


def test_cada_informacao_presente_vira_uma_etiqueta():
    texto = " ".join(chips(escolha=ESCOLHA_CHEIA))

    assert "Matemática" in texto
    assert DESAFIO["tema_usado"] in texto
    assert "Torre Norte" in texto
    assert "Salão dos Ecos" in texto
    assert "Tocha" in texto
    assert "Equações" in texto


def test_o_que_falta_nao_vira_etiqueta_vazia():
    """Sem os `if`, a tela desenharia chips com só o ícone dentro."""
    assert chips(config={}, desafio={}, escolha={}) == []


@pytest.mark.parametrize(
    "chave,valor",
    [
        ("rota", "Torre Norte"),
        ("destino_titulo", "Salão dos Ecos"),
        ("recurso", "Tocha"),
        ("foco_aprendizado", "Equações"),
    ],
)
def test_cada_campo_da_escolha_responde_sozinho(chave, valor):
    """Um a um: com todos juntos, apagar um `if` passava despercebido."""
    lista = chips(config={}, desafio={}, escolha={chave: valor})

    assert len(lista) == 1
    assert valor in lista[0]


def test_a_materia_e_o_tema_respondem_sozinhos():
    assert chips(desafio={}, escolha={}) == chips(desafio={}, escolha={})
    assert len(chips(desafio={}, escolha={})) == 1, "só a matéria"
    assert len(chips(config={}, escolha={})) == 1, "só o tema"


def test_o_icone_do_destino_tem_um_padrao():
    """Aventura antiga pode não ter ícone gravado; a bússola cobre o buraco."""
    sem_icone = chips(config={}, desafio={}, escolha={"destino_titulo": "Salão"})

    assert "🧭" in sem_icone[0]
