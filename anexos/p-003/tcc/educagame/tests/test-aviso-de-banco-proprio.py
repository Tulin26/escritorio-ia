"""O aluno passa a saber quando a questão não veio da IA — heurística 9.

O que estava errado
-------------------
Quando a geração por IA falha, o EducaGame serve uma questão do banco próprio
para que a atividade não pare. Isso é bom — mas o aluno não era avisado em
metade dos modos, e nos outros o aviso era ruim.

Medido antes de mexer, nos oito modos do Flask:

    Oráculo, Treino, Laboratório, RPG   avisavam
    ENEM                                pílula escrita "offline"
    Boss Rush                           montava o rótulo e não o mostrava
    Escape Room                         guardava o aviso no estado e não o passava
    Guildas                             não gera questão

Três modos faziam o trabalho e jogavam fora na última etapa. E havia **dois**
marcadores para a mesma informação -- `_origem_geracao` e `_origem` --, que é
como o ENEM acabou com uma pílula em vez de uma frase.

A mensagem também mudou
-----------------------
Era: *"A IA não retornou uma questão válida agora. Usei o banco offline para
manter o treino funcionando."* Três problemas para quem lê com 15 anos, no
meio de uma atividade valendo nota: "Usei" (quem é "eu"?), "banco offline"
(jargão nosso) e, principalmente, ela conta o problema e não diz o que fazer.

A nona heurística pede linguagem simples, o problema indicado com precisão e
uma saída construtiva. A questão do banco é revisada e vale pontos igual --
dizer isso é o que transforma um susto em informação.
"""

from __future__ import annotations

import pytest

from core.origem_questao import (
    AVISO_BANCO_PROPRIO,
    aviso_de_origem,
    veio_do_banco_proprio,
)

MODOS_COM_QUESTAO = [
    ("oraculo", "oraculo.html"),
    ("treino", "treino.html"),
    ("laboratorio", "laboratorio.html"),
    ("enem", "enem.html"),
    ("boss_rush", "boss_rush.html"),
    ("escape_room", "escape_room.html"),
    ("rpg", "rpg.html"),
]


# ====================== A DECISÃO ======================


@pytest.mark.parametrize("campo", ["_origem_geracao", "_origem"])
def test_os_dois_marcadores_valem(campo):
    """O projeto usa dois nomes para a mesma informação. Entender só um foi
    como o ENEM ficou de fora do aviso por tanto tempo."""
    assert veio_do_banco_proprio({campo: "offline"})
    assert aviso_de_origem({campo: "offline"}) == AVISO_BANCO_PROPRIO


@pytest.mark.parametrize("valor", ["OFFLINE", " offline ", "Offline"])
def test_a_comparacao_nao_depende_de_caixa_nem_espaco(valor):
    assert veio_do_banco_proprio({"_origem": valor})


def test_questao_da_ia_nao_gera_aviso():
    """A metade que protege: avisar sempre é o mesmo que não avisar nunca."""
    assert not veio_do_banco_proprio({"_origem_geracao": "ia"})
    assert aviso_de_origem({"_origem_geracao": "ia"}) == ""
    assert aviso_de_origem({}) == ""
    assert aviso_de_origem(None) == ""


def test_erro_da_cascata_tambem_avisa():
    """Nem todo caminho de fallback marca a questão; o erro existir já
    significa que a IA não entregou."""
    assert aviso_de_origem({}, "429 Too Many Requests") == AVISO_BANCO_PROPRIO
    assert aviso_de_origem({}, "   ") == ""


# ====================== A MENSAGEM ======================


def test_a_mensagem_diz_ao_aluno_o_que_fazer():
    """Contar o problema sem dizer a saída deixa o aluno sem saber se a
    questão vale, se deve responder, se deu errado."""
    texto = AVISO_BANCO_PROPRIO.lower()

    assert "pode responder" in texto, "a mensagem não diz o que fazer"
    assert "vale pontos" in texto, "a mensagem não diz que a questão conta igual"


def test_a_mensagem_nao_usa_jargao_nosso():
    texto = AVISO_BANCO_PROPRIO.lower()

    for jargao in ("offline", "fallback", "cascata", "api", "timeout", "provedor"):
        assert jargao not in texto, f"'{jargao}' é jargão nosso, não do aluno"


def test_a_mensagem_nao_fala_na_primeira_pessoa():
    """"Usei o banco offline" -- quem é "eu"? O app não é uma pessoa.

    Com fronteira de palavra: procurar "eu " solto casava dentro de
    "respondeu a tempo", e o teste reprovava a mensagem certa."""
    import re

    for pessoal in ("usei", "eu", "peguei", "coloquei", "resolvi"):
        assert not re.search(rf"\b{pessoal}\b", AVISO_BANCO_PROPRIO.lower()), pessoal


# ====================== OS MODOS, NO FLASK ======================


@pytest.mark.parametrize("nome, template", MODOS_COM_QUESTAO)
def test_todo_modo_de_questao_mostra_o_aviso(nome, template):
    """Um por um, porque foi assim que três deles ficaram para trás: o
    trabalho estava feito e faltava a última linha."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    html = (raiz / "web" / "templates" / template).read_text(encoding="utf-8")

    assert "ia_notice" in html, f"a tela do {nome} não tem onde mostrar o aviso"


@pytest.mark.parametrize("nome", [m for m, _ in MODOS_COM_QUESTAO])
def test_toda_rota_de_questao_calcula_o_aviso(nome):
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    rota = (raiz / "web" / "routes" / f"{nome}_fla.py").read_text(encoding="utf-8")

    assert "erro_ia" in rota, f"a rota do {nome} não passa o aviso para a tela"


def test_o_escape_room_passa_o_aviso_que_ja_guardava(client, monkeypatch):
    """Teste de comportamento para o caso mais claro de trabalho jogado fora:
    a rota gravava `estado["aviso_ia"]` e nunca o entregava."""
    from tests.apoio_flask import carimbar_sessao
    from web.routes import escape_room_fla

    estado = {
        "fase": "sala",
        "nivel": "Medio",
        "salas": [{"numero": 1, "materia": "Matematica", "tema": ""}],
        "atual": 0,
        "historico": [],
        "pistas": [],
        "questao": {"pergunta": "2+2?", "opcoes": ["4"], "correta": 0, "_origem_geracao": "offline"},
        "resultado": None,
        "aviso_ia": "",
    }
    monkeypatch.setattr(
        escape_room_fla, "carregar_estado_persistido", lambda *a, **k: dict(estado)
    )
    monkeypatch.setattr(escape_room_fla, "alunos_para_selecao", lambda: [])

    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    corpo = client.get("/escape-room/").get_data(as_text=True)

    assert AVISO_BANCO_PROPRIO in corpo


def test_a_questao_da_ia_nao_mostra_aviso_no_escape_room(client, monkeypatch):
    """O par: a tela não pode passar a avisar sempre."""
    from tests.apoio_flask import carimbar_sessao
    from web.routes import escape_room_fla

    estado = {
        "fase": "sala",
        "nivel": "Medio",
        "salas": [{"numero": 1, "materia": "Matematica", "tema": ""}],
        "atual": 0,
        "historico": [],
        "pistas": [],
        "questao": {"pergunta": "2+2?", "opcoes": ["4"], "correta": 0, "_origem_geracao": "ia"},
        "resultado": None,
        "aviso_ia": "",
    }
    monkeypatch.setattr(
        escape_room_fla, "carregar_estado_persistido", lambda *a, **k: dict(estado)
    )
    monkeypatch.setattr(escape_room_fla, "alunos_para_selecao", lambda: [])

    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    corpo = client.get("/escape-room/").get_data(as_text=True)

    assert AVISO_BANCO_PROPRIO not in corpo


@pytest.mark.parametrize(
    ("questao", "avisa"),
    [
        # o relatorio final: /proxima ja limpou a questao
        (None, False),
        # a tela de resultado de uma sala: a questao continua ali
        ({"pergunta": "2+2?", "opcoes": ["4"], "correta": 0}, True),
    ],
)
def test_o_aviso_da_ultima_sala_nao_fica_em_cima_do_relatorio(client, monkeypatch, questao, avisa):
    """Visto em 30/09/2026, gerando as telas do TCC: com a ultima sala vinda
    do banco proprio, o relatorio final abria com "Esta questao veio do
    banco..." -- e no relatorio nao ha questao nenhuma. O `aviso_ia` da sala
    fica guardado depois que /proxima limpa a questao."""
    from tests.apoio_flask import carimbar_sessao
    from web.routes import escape_room_fla

    estado = {
        "fase": "resultado" if questao is None else "sala",
        "nivel": "Medio",
        "salas": [{"numero": 1, "materia": "Matematica", "tema": ""}],
        "atual": 0,
        "historico": [{"sala": 1, "tentativa": 1, "materia": "Matematica", "pergunta": "2+2?",
                       "resposta_aluno": "4", "resposta_correta": "4", "acertou": True}],
        "pistas": ["Sala 1 aberta em Matemática."],
        "questao": questao,
        "resultado": None,
        "aviso_ia": "IA indisponivel no momento. Usando banco de questoes local.",
    }
    monkeypatch.setattr(
        escape_room_fla, "carregar_estado_persistido", lambda *a, **k: dict(estado)
    )
    monkeypatch.setattr(escape_room_fla, "alunos_para_selecao", lambda: [])

    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        carimbar_sessao(sess)

    corpo = client.get("/escape-room/").get_data(as_text=True)

    if questao is None:
        assert "Escape Room concluído" in corpo
    assert (AVISO_BANCO_PROPRIO in corpo) is avisa


# ====================== OS MODOS, NO STREAMLIT ======================


@pytest.mark.parametrize(
    "tela",
    [
        "tela_oraculo_st",
        "tela_treino_st",
        "tela_laboratorio_st",
        "tela_enem_st",
        "tela_boss_rush_enem_st",
        "tela_escape_room_st",
        "tela_rpg_st",
    ],
)
def test_toda_tela_do_streamlit_mostra_a_origem(tela):
    import importlib
    import inspect

    modulo = importlib.import_module(f"st.ui.{tela}")
    fonte = inspect.getsource(modulo)

    assert "renderizar_origem_questao(" in fonte, f"{tela} não mostra de onde veio a questão"


def test_o_streamlit_usa_a_mesma_frase_do_flask(monkeypatch):
    """Comportamento, e não texto: a função é chamada com uma questão offline
    e tem de entregar a frase compartilhada."""
    from st.ui import mode_common_st

    mostrados: list[str] = []
    monkeypatch.setattr(mode_common_st.st, "info", lambda texto: mostrados.append(texto))
    monkeypatch.setattr(mode_common_st.st, "caption", lambda texto: None)

    mode_common_st.renderizar_origem_questao({"_origem_geracao": "offline"})

    assert mostrados == [AVISO_BANCO_PROPRIO]


def test_o_streamlit_nao_avisa_para_questao_da_ia(monkeypatch):
    from st.ui import mode_common_st

    mostrados: list[str] = []
    legendas: list[str] = []
    monkeypatch.setattr(mode_common_st.st, "info", lambda texto: mostrados.append(texto))
    monkeypatch.setattr(mode_common_st.st, "caption", lambda texto: legendas.append(texto))

    mode_common_st.renderizar_origem_questao({"_origem_geracao": "ia"})

    assert mostrados == []
    assert legendas, "a questão da IA deixou de ser identificada"


# ====================== SEIS FRASES PARA UM RECADO SÓ ======================
#
# Descoberto em 10/09/2026, ao rotular as capturas do TG: para o MESMO estado
# -- "a IA não entregou, esta questão veio do banco" -- o app mostrava seis
# textos diferentes, em quatro arquivos:
#
#   services/ia/providers.py    "IA indisponivel no momento. Usando banco de
#                                questoes local."
#   services/ia/providers.py    "Os provedores de IA atingiram o limite de uso
#                                temporariamente. Usando banco de questoes local."
#   services/ia/providers.py    "Houve um problema de autenticacao com a IA.
#                                Usando banco de questoes local."
#   services/rpg_service.py     "IA indisponivel no momento. Usando banco RPG
#                                offline."
#   laboratorio_fla.py          "Falha temporária ao gerar por IA. Usando banco
#                                de questões local."
#   core/origem_questao.py      AVISO_BANCO_PROPRIO -- o texto escrito para o aluno
#
# As cinco primeiras chegavam CRUAS na tela. `aviso_offline` só convertia uma
# redação antiga específica ("A IA não retornou ... offline"); todas as outras
# caíam num `return texto`.
#
# Elas não são inúteis: distinguem cota, autenticação e indisponibilidade, e
# isso serve ao desenvolvedor no painel do ADM. O que não serve é mandá-las
# para um aluno de 15 anos no meio de uma atividade valendo nota.


def _frases_tecnicas_do_app() -> list[str]:
    """As frases que a cascata realmente produz, tiradas da fonte.

    Vem de `_mensagem_amigavel_erro_ia` em vez de cópias escritas aqui: se
    amanhã nascer uma sétima redação, ela entra neste teste sozinha.
    """
    from services.ia.providers import _mensagem_amigavel_erro_ia

    return [
        _mensagem_amigavel_erro_ia(),
        _mensagem_amigavel_erro_ia(erro_groq="Error 429 rate limit reached"),
        _mensagem_amigavel_erro_ia(erro_groq="invalid api key"),
        _mensagem_amigavel_erro_ia(erro_groq="connection reset by peer"),
        "IA indisponivel no momento. Usando banco RPG offline.",
        "Falha temporária ao gerar por IA. Usando banco de questões local.",
    ]


def test_toda_frase_tecnica_da_cascata_vira_a_frase_do_aluno():
    """O funil é um só: `aviso_offline`. Entrou mensagem técnica, sai a frase
    escrita para o aluno."""
    from web.routes.flask_helpers_fla import aviso_offline

    for tecnica in _frases_tecnicas_do_app():
        assert aviso_offline({}, "questao", tecnica) == AVISO_BANCO_PROPRIO, (
            f"chegou crua na tela do aluno: {tecnica!r}"
        )


def test_nenhuma_frase_tecnica_carrega_jargao_para_a_tela():
    """O par do teste acima, pelo outro lado: o que sai do funil nunca pode
    conter o jargão, venha de onde vier."""
    from web.routes.flask_helpers_fla import aviso_offline

    for tecnica in _frases_tecnicas_do_app():
        saida = aviso_offline({}, "questao", tecnica).lower()
        for jargao in ("banco de questoes local", "banco de questões local",
                       "banco rpg offline", "indisponivel", "autenticacao"):
            assert jargao not in saida, f"'{jargao}' vazou de {tecnica!r}"


def test_a_questao_da_ia_continua_sem_aviso():
    """A garantia do outro lado: converter tudo não pode virar avisar sempre."""
    from web.routes.flask_helpers_fla import aviso_offline

    assert aviso_offline({"_origem_geracao": "ia"}, "questao", "") == ""
    assert aviso_offline({}, "questao", "") == ""


# ====================== O AVISO SOBREVIVE À CORREÇÃO ======================
#
# O aluno via "esta questão veio do banco" na pergunta, respondia, e a origem
# sumia da tela de correção. Conferido na captura `08c-laboratorio-resolucao`:
# a questão era do banco e a tela de resposta não trazia marca nenhuma.
#
# A causa é a mesma nos dois modos: `erro_ia` nasce "" e só é calculado no
# ramo do POST. A correção redireciona para o GET, e no GET ninguém recalcula.
# Os testes estruturais antigos ("a rota contém erro_ia", "o template contém
# ia_notice") passavam felizes -- a rota contém, o template contém, e o valor
# chega vazio.

DESAFIO_DO_BANCO = {
    "pergunta": "Um corpo percorre 120 m em 15 s. Qual a velocidade média?",
    "opcoes": ["8 m/s", "6 m/s", "10 m/s", "12 m/s"],
    "correta": 0,
    "materia": "Fisica",
    "materia_label": "Física",
    "_origem_geracao": "offline",
}

RESULTADO = {"acertou": True, "pontos": 20, "resposta_aluno": "8 m/s", "resposta_correta": "8 m/s"}


def _aluno_logado(client):
    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        sess["aluno_id"] = "aluno-1"
        carimbar_sessao(sess)


def _estado_falso(rota, por_nome: dict):
    def _obter(nome, padrao=None):
        return por_nome.get(nome, padrao)
    return _obter


@pytest.mark.parametrize(
    "modulo, url, chave_entidade, chave_resultado",
    [
        ("laboratorio_fla", "/laboratorio/", "desafio_laboratorio", "resultado_laboratorio"),
        ("oraculo_fla", "/oraculo/", "enigma_atual", "resultado_oraculo"),
    ],
    ids=["laboratorio", "oraculo"],
)
def test_a_tela_de_correcao_ainda_diz_de_onde_veio_a_questao(
    client, monkeypatch, modulo, url, chave_entidade, chave_resultado
):
    """Depois de responder, o aluno continua sabendo que a questão é do banco.

    É o estado em que ele lê a explicação e decide se confia nela -- é
    justamente aí que a origem importa."""
    import importlib

    rota = importlib.import_module(f"web.routes.{modulo}")
    monkeypatch.setattr(
        rota, "obter_estado_flask",
        _estado_falso(rota, {chave_entidade: dict(DESAFIO_DO_BANCO), chave_resultado: dict(RESULTADO)}),
    )
    monkeypatch.setattr(rota, "alunos_para_selecao", lambda: [])
    _aluno_logado(client)

    corpo = client.get(url).get_data(as_text=True)

    assert AVISO_BANCO_PROPRIO in corpo, "a origem sumiu na tela de correção"


@pytest.mark.parametrize(
    "modulo, url, chave_entidade",
    [
        ("laboratorio_fla", "/laboratorio/", "desafio_laboratorio"),
        ("oraculo_fla", "/oraculo/", "enigma_atual"),
    ],
    ids=["laboratorio", "oraculo"],
)
def test_a_correcao_de_questao_da_ia_nao_ganha_aviso(client, monkeypatch, modulo, url, chave_entidade):
    """O par que protege: recalcular no GET não pode passar a avisar sempre."""
    import importlib

    rota = importlib.import_module(f"web.routes.{modulo}")
    da_ia = dict(DESAFIO_DO_BANCO, _origem_geracao="ia")
    monkeypatch.setattr(rota, "obter_estado_flask", _estado_falso(rota, {chave_entidade: da_ia}))
    monkeypatch.setattr(rota, "alunos_para_selecao", lambda: [])
    _aluno_logado(client)

    corpo = client.get(url).get_data(as_text=True)

    assert AVISO_BANCO_PROPRIO not in corpo


# ====================== A FRASE BOA, E LOGO ABAIXO A TÉCNICA ======================
#
# Quatro telas do Streamlit faziam isto:
#
#     renderizar_origem_questao(questao, aviso_ia)   # a frase escrita para o aluno
#     if aviso_ia:
#         st.info(aviso_ia)                          # e o texto técnico, de novo
#
# O aluno lia "esta questão veio do banco... pode responder normalmente" e,
# logo abaixo, "IA indisponivel no momento. Usando banco de questoes local."
# -- o mesmo recado duas vezes, a segunda em jargão nosso e sem acento.
#
# É sobra de antes de `renderizar_origem_questao` existir. O teste estrutural
# antigo ("a tela chama renderizar_origem_questao") passava feliz: ela chama,
# e mostra o cru em seguida.

TELAS_DE_ALUNO = [
    "tela_oraculo_st",
    "tela_treino_st",
    "tela_laboratorio_st",
    "tela_enem_st",
    "tela_boss_rush_enem_st",
    "tela_escape_room_st",
    "tela_rpg_st",
]


def _avisos_crus_mostrados(fonte: str) -> list[str]:
    """Chamadas de `st.info(...)` que entregam um aviso da IA sem passar pelo
    texto do aluno.

    Olha o NOME do que é passado: numa tela de aluno, a única saída legítima
    para um aviso da IA é `renderizar_origem_questao`, que converte.
    """
    import ast

    achados = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call) or not no.args:
            continue
        alvo = no.func
        # info, warning e caption: os três jeitos de escrever texto na tela.
        # (Ficou de fora na primeira versão o `caption`, que é justamente
        # como o painel do ADM mostra o aviso -- e o teste do ADM reprovou.)
        if not (isinstance(alvo, ast.Attribute) and alvo.attr in ("info", "warning", "caption")):
            continue
        if not (isinstance(alvo.value, ast.Name) and alvo.value.id == "st"):
            continue
        texto = ast.unparse(no.args[0])
        if "aviso" in texto.lower():
            achados.append(texto)
    return achados


@pytest.mark.parametrize("tela", TELAS_DE_ALUNO)
def test_nenhuma_tela_de_aluno_mostra_o_aviso_cru(tela):
    """A tela do ADM continua podendo: lá o texto técnico é a informação útil,
    e quem lê é o desenvolvedor."""
    import importlib
    import inspect

    modulo = importlib.import_module(f"st.ui.{tela}")
    crus = _avisos_crus_mostrados(inspect.getsource(modulo))

    assert not crus, (
        f"{tela} entrega o aviso técnico direto ao aluno: {crus}. "
        "A saída para o aluno é renderizar_origem_questao, que converte."
    )


def test_o_painel_do_adm_continua_vendo_o_texto_tecnico():
    """O par: unificar para o aluno não pode cegar o desenvolvedor. É no ADM
    que se distingue cota de autenticação de indisponibilidade."""
    import inspect

    from st.ui import admin_st

    assert _avisos_crus_mostrados(inspect.getsource(admin_st)), (
        "o painel do ADM parou de mostrar o último aviso da IA"
    )


# ====================== O ERRO É DE UM PEDIDO, NÃO DO PROCESSO ======================
#
# `obter_ultimo_erro_ia()` é uma variável global do PROCESSO. No Render, um
# worker do Gunicorn atende vários alunos: o erro que ela guarda pode ser da
# requisição de outra pessoa, de segundos atrás.
#
# No POST isso não incomoda -- a geração acabou de acontecer nesta requisição.
# No GET incomoda: a tela de correção de um aluno com questão da IA passaria a
# avisar "esta veio do banco" porque a IA falhou para OUTRO aluno.
#
# A mutação achou isto: tirar a guarda `if request.method == "POST"` não
# quebrava teste nenhum.


@pytest.mark.parametrize(
    "modulo, url, chave_entidade",
    [
        ("laboratorio_fla", "/laboratorio/", "desafio_laboratorio"),
        ("oraculo_fla", "/oraculo/", "enigma_atual"),
    ],
    ids=["laboratorio", "oraculo"],
)
def test_erro_de_outra_requisicao_nao_avisa_na_tela_de_correcao(
    client, monkeypatch, modulo, url, chave_entidade
):
    """A questão desta tela veio da IA; quem falhou foi outro pedido."""
    import importlib

    rota = importlib.import_module(f"web.routes.{modulo}")
    da_ia = dict(DESAFIO_DO_BANCO, _origem_geracao="ia")
    monkeypatch.setattr(rota, "obter_estado_flask", _estado_falso(rota, {chave_entidade: da_ia}))
    monkeypatch.setattr(rota, "alunos_para_selecao", lambda: [])
    monkeypatch.setattr(
        rota, "obter_ultimo_erro_ia",
        lambda: "IA indisponivel no momento. Usando banco de questoes local.",
    )
    _aluno_logado(client)

    corpo = client.get(url).get_data(as_text=True)

    assert AVISO_BANCO_PROPRIO not in corpo, (
        "avisou por causa do erro de outra requisição"
    )


def test_o_funil_do_streamlit_tambem_converte_o_texto_tecnico(monkeypatch):
    """O par do teste do Flask, no outro frontend.

    O teste que já existia chamava a função SEM aviso técnico, então uma
    versão que devolvesse o texto cru quando ele existe passava batido."""
    from st.ui import mode_common_st

    mostrados: list[str] = []
    monkeypatch.setattr(mode_common_st.st, "info", lambda texto: mostrados.append(texto))
    monkeypatch.setattr(mode_common_st.st, "caption", lambda texto: None)

    mode_common_st.renderizar_origem_questao(
        {"_origem_geracao": "offline"},
        "IA indisponivel no momento. Usando banco de questoes local.",
    )

    assert mostrados == [AVISO_BANCO_PROPRIO], f"chegou cru na tela: {mostrados}"
