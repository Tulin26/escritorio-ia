"""A fórmula e a legenda passam a ser guardadas, para dar como medir.

Por que
-------
A validação `legenda-com-variavel-sem-formula` foi ligada em 09/09/2026 com
**0 falso positivo em 7.200** questões — medidas no banco offline. No mesmo
dia, a regra vizinha mostrou o quanto esse corpus engana: contra o banco
offline dava 0%, e contra 8 resoluções **reais** a primeira versão dela deu
**25%**, por formas que só a IA escreve (prosa dentro do passo, `P_f` lido
como `P`).

O banco autoral responde *"a regra recusa o que NÓS escrevemos?"*. Para fazer
a pergunta que decide é preciso ter, do lado real, os campos que a regra
cruza — e o log guardava a resolução (desde a 20260903120000) mas não a
fórmula nem a legenda.

São TRÊS campos e não dois: sem `subformulas`, a medição sairia errada **para
mais**, acusando de órfã toda variável que só aparece na fórmula auxiliar — o
`R` de `R = a√3/3`, que é justamente o caso que a regra existe para exigir.
"""

from __future__ import annotations

import pytest

from repositories.log_repo import LOG_COLUMNS, preparar_payload_log

QUESTAO = {
    "aluno_id": "aluno-1",
    "escola_id": "escola-1",
    "materia": "LAB-Matematica",
    "modo": "laboratorio-flask",
    "resultado": "Acertou",
    "pergunta_texto": "Resolva 2x² - 7x + 3 = 0.",
    "formula": r"x = (-b \pm \sqrt{\Delta})/(2a)",
    "subformulas": [r"\Delta = b^2 - 4ac"],
    "legenda_variaveis": "a = coeficiente; b = coeficiente; c = termo independente",
}


def test_as_tres_colunas_existem():
    for coluna in ("formula", "subformulas", "legenda_variaveis"):
        assert coluna in LOG_COLUMNS, f"'{coluna}' nao entra no insert"


def test_os_tres_campos_chegam_ao_payload():
    payload = preparar_payload_log(dict(QUESTAO))

    assert payload["formula"] == QUESTAO["formula"]
    assert payload["subformulas"] == QUESTAO["subformulas"]
    assert payload["legenda_variaveis"] == QUESTAO["legenda_variaveis"]


@pytest.mark.parametrize("campo", ["formula", "subformulas", "legenda_variaveis"])
def test_campo_vazio_nao_vira_linha(campo):
    """Gravar "" faria a consulta contar como "tem legenda" o que não tem, e
    o denominador da medição sairia inflado. A maioria dos modos não tem
    esses campos."""
    questao = dict(QUESTAO)
    questao[campo] = "" if campo != "subformulas" else []

    payload = preparar_payload_log(questao)

    assert campo not in payload, f"'{campo}' vazio virou linha"


@pytest.mark.parametrize("valor", ["   ", None, "\n"])
def test_texto_em_branco_tambem_nao_vira_linha(valor):
    questao = dict(QUESTAO)
    questao["legenda_variaveis"] = valor

    assert "legenda_variaveis" not in preparar_payload_log(questao)


def test_subformulas_ignora_item_vazio():
    questao = dict(QUESTAO, subformulas=["", "  ", r"\Delta = b^2 - 4ac", None])

    payload = preparar_payload_log(questao)

    assert payload["subformulas"] == [r"\Delta = b^2 - 4ac"]


def test_subformulas_que_nao_e_lista_e_ignorada():
    questao = dict(QUESTAO, subformulas="não é lista")

    assert "subformulas" not in preparar_payload_log(questao)


# ====================== OS TETOS ======================


def test_formula_muito_longa_e_truncada():
    questao = dict(QUESTAO, formula="x" * 5000)

    payload = preparar_payload_log(questao)

    assert len(payload["formula"]) == 400


def test_legenda_muito_longa_e_truncada():
    questao = dict(QUESTAO, legenda_variaveis="a = coeficiente; " * 500)

    payload = preparar_payload_log(questao)

    assert len(payload["legenda_variaveis"]) == 800


def test_lista_de_subformulas_tem_teto():
    questao = dict(QUESTAO, subformulas=[f"f_{i} = {i}" for i in range(50)])

    payload = preparar_payload_log(questao)

    assert len(payload["subformulas"]) == 6


def test_subformula_longa_e_truncada():
    questao = dict(QUESTAO, subformulas=["y" * 5000])

    payload = preparar_payload_log(questao)

    assert len(payload["subformulas"][0]) == 400


# ====================== O QUE JÁ FUNCIONAVA ======================


def test_a_resolucao_continua_sendo_guardada():
    """A metade que não pode se perder: acrescentar três campos não pode
    mexer no que a migração anterior trouxe."""
    questao = dict(
        QUESTAO,
        passos_resolucao=[{"titulo": "1º Passo", "conteudo": "a = 2, b = -7, c = 3"}],
    )

    payload = preparar_payload_log(questao)

    assert payload["passos_json"] == [{"conteudo": "a = 2, b = -7, c = 3", "titulo": "1º Passo"}]


def test_campo_desconhecido_continua_sendo_descartado():
    payload = preparar_payload_log(dict(QUESTAO, campo_que_nao_existe="x"))

    assert "campo_que_nao_existe" not in payload


# ====================== A ROTA DO LABORATÓRIO ======================


def test_a_rota_flask_manda_os_tres_campos(client, monkeypatch):
    """Teste de comportamento, e não de texto: trocar o valor por None no
    dicionário da rota mantém a palavra no arquivo, e um teste que lê o fonte
    passaria assim mesmo."""
    from tests.apoio_flask import carimbar_sessao
    from web.routes import laboratorio_fla

    registrados: list[dict] = []
    monkeypatch.setattr(
        laboratorio_fla,
        "registrar_log_com_tempo",
        lambda dados, tempo=None: registrados.append(dados),
    )
    monkeypatch.setattr(laboratorio_fla, "registrar_pontuacao_acerto", lambda *a, **k: 0)
    monkeypatch.setattr(laboratorio_fla, "gerar_feedback_pedagogico", lambda **k: None)

    desafio = {
        "pergunta": "Resolva 2x² - 7x + 3 = 0.",
        "opcoes": ["{3; 0,5}", "{1; 2}"],
        "correta": 0,
        "materia": "Matematica",
        "nivel": "Médio",
        "formula": QUESTAO["formula"],
        "subformulas": QUESTAO["subformulas"],
        "legenda_variaveis": QUESTAO["legenda_variaveis"],
    }

    with client.session_transaction() as sess:
        sess["aluno_id"] = "aluno-1"
        sess["escola_id"] = "escola-1"
        sess["usuario_role"] = "aluno"
        sess["desafio_laboratorio"] = desafio
        carimbar_sessao(sess)

    monkeypatch.setattr(laboratorio_fla, "obter_estado_flask", lambda nome, padrao=None: desafio)
    monkeypatch.setattr(laboratorio_fla, "salvar_estado_flask", lambda *a, **k: None)

    client.post("/laboratorio/responder", data={"resposta": "0"})

    assert registrados, "a rota nao registrou log nenhum"
    enviado = registrados[-1]
    assert enviado.get("formula") == QUESTAO["formula"]
    assert enviado.get("subformulas") == QUESTAO["subformulas"]
    assert enviado.get("legenda_variaveis") == QUESTAO["legenda_variaveis"]


def test_a_tela_do_streamlit_manda_os_tres_campos():
    """O par do teste acima, no outro frontend. Os dois já divergiram antes:
    o Laboratório do Flask gravava BNCC e o do Streamlit não.

    LIMITAÇÃO, dita de propósito: este lê o TEXTO da chamada, porque exercitar
    `renderizar_tela_laboratorio` inteira exigiria montar meia dúzia de
    estados da bancada. Teste de texto pega a remoção da linha, mas não prova
    que a tela chega a executá-la — foi assim que a mutação do BNCC começou em
    8/11. O teste seguinte cobre a outra metade: que o valor de fato atravessa
    a tubulação até o payload."""
    import inspect

    from st.ui import tela_laboratorio_st

    fonte = inspect.getsource(tela_laboratorio_st)
    bloco = fonte[fonte.index('"passos_json"') : fonte.index('"codigo_bncc"')]

    for campo in ("formula", "subformulas", "legenda_variaveis"):
        assert f'"{campo}": dl.get("{campo}")' in bloco, f"o Streamlit nao manda '{campo}'"


def test_os_extras_do_streamlit_chegam_ao_payload():
    """A outra metade: `registrar_resposta_modo` é por onde as telas do
    Streamlit registram, e é ele que decide se `extras` sobrevive até o
    payload. Sem este teste, o campo poderia estar na chamada da tela e ser
    descartado no caminho -- e o teste de texto acima continuaria verde."""
    from st.ui.mode_common_st import registrar_resposta_modo

    recebidos: list[dict] = []

    class RepoFalso:
        @staticmethod
        def registrar_log_com_tempo(dados, tempo_resposta=None):
            recebidos.append(preparar_payload_log(dados, tempo_resposta))

    registrar_resposta_modo(
        RepoFalso,
        aluno_id="aluno-1",
        escola_id="escola-1",
        materia="LAB-Matematica",
        modo="laboratorio",
        acertou=True,
        pergunta_texto="Resolva 2x² - 7x + 3 = 0.",
        resposta_aluno="{3; 0,5}",
        resposta_correta="{3; 0,5}",
        explicacao_ia="Bhaskara.",
        extras={
            "formula": QUESTAO["formula"],
            "subformulas": QUESTAO["subformulas"],
            "legenda_variaveis": QUESTAO["legenda_variaveis"],
        },
    )

    assert recebidos, "registrar_resposta_modo nao chamou o repositorio"
    payload = recebidos[-1]
    assert payload.get("formula") == QUESTAO["formula"]
    assert payload.get("subformulas") == QUESTAO["subformulas"]
    assert payload.get("legenda_variaveis") == QUESTAO["legenda_variaveis"]
