"""O aluno passa a saber que está carregando, e o tempo volta a ser medido.

Dois defeitos achados varrendo os **logs reais de uso**, não o código:

**1. Nenhuma das 20 telas do Flask avisava que estava carregando** — e gerar
uma questão pela IA leva até 22 segundos (`_orcamento_ia_oraculo_segundos`).
O aluno clicava e olhava uma tela parada, sem saber se tinha funcionado. Sem
nada travando o botão, clicava de novo, e cada clique dispara outra cascata
de IA. É a heurística 1 de Nielsen (visibilidade do status) somada à
prevenção de erro.

**2. Laboratório e Oráculo não registravam tempo de resposta** — medido, **68
dos 107 logs reais (63%)**, e o Laboratório é o modo mais usado. O painel do
professor mostra tempo médio e, para esses dois, o dado não existia. A causa
era uma linha: o Treino chama `registrar_log_com_tempo`, esses dois chamavam
`registrar_log` sem nada.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATES = RAIZ / "web" / "templates"
CSS = RAIZ / "web" / "static" / "css" / "flask.css"

# As telas com formulário de POST: são elas que podem prender o aluno.
TELAS_COM_FORMULARIO = [
    "laboratorio.html", "oraculo.html", "treino.html", "rpg.html",
    "escape_room.html", "enem.html", "boss_rush.html", "professor.html",
    "login.html", "cadastro.html", "codigo_escola.html", "perfil.html",
]


def texto(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


# ====================== O AVISO EXISTE E VALE PARA TODAS ======================


def test_o_aviso_mora_no_base_e_nao_em_cada_tela():
    """Vinte telas, um lugar só. Espalhado por tela, envelheceria em silêncio
    — a tela nova nasceria sem aviso e ninguém notaria.
    """
    base = texto(TEMPLATES / "base.html")

    assert 'document.addEventListener("submit"' in base
    # MELHORIA: procurar "data-aguardando" solto era fraco -- a palavra
    # aparece em varios pontos, e arrancar a atribuicao passava batido.
    assert 'botao.dataset.aguardando = "1"' in base


@pytest.mark.parametrize("tela", TELAS_COM_FORMULARIO)
def test_toda_tela_com_formulario_herda_o_aviso(tela):
    """Herdar do `base.html` é o que garante isso — o teste existe para o dia
    em que alguém criar uma tela que não estenda a base."""
    conteudo = texto(TEMPLATES / tela)

    assert "{% extends" in conteudo, f"{tela} não estende o base"


def test_o_estilo_do_estado_de_espera_existe():
    css = texto(CSS)

    # A regra que aplica o estado, e nao so a palavra solta: trocar o seletor
    # por outro deixava o botao sem estilo nenhum e o teste passava.
    assert "button[data-aguardando]," in css
    assert ".button[data-aguardando] {" in css
    assert "@keyframes educagame-girando" in css


def test_o_ponto_usa_a_cor_do_proprio_botao():
    """`currentColor` resolve o contraste por construção: o ponto herda a cor
    do texto do botão, que já tem contraste garantido com o fundo dele. Uma
    cor fixa quebraria no tema claro ou no escuro.
    """
    css = texto(CSS)
    # MELHORIA: pegar a ULTIMA ocorrencia pegava o bloco do media query, e
    # uma cor fixa no bloco principal passava despercebida (visto por
    # mutacao). O bloco certo e o que desenha a borda.
    blocos = [t.split("}")[0] for t in css.split("button[data-aguardando]::after")[1:]]
    principal = next(b for b in blocos if "border: " in b)

    assert "currentColor" in principal
    assert "#" not in principal, "cor fixa quebraria num dos dois temas"


def test_quem_pede_menos_movimento_nao_ganha_animacao():
    """O projeto já respeita `prefers-reduced-motion` no resto do CSS; o
    indicador não podia ser a exceção. Sem giro, mas o aviso em texto
    continua dizendo o que está acontecendo.
    """
    css = texto(CSS)
    reduzido = css.split("prefers-reduced-motion")[-1]

    assert "data-aguardando" in reduzido
    assert "animation: none" in reduzido


# ====================== O AVISO NÃO PODE ATRAPALHAR ======================


def test_o_botao_nao_e_travado_antes_do_envio_comecar():
    """`setTimeout(..., 0)` deixa o navegador montar o envio primeiro. Travar
    antes descartaria o `name`/`value` do botão — nenhum tem hoje, e o
    adiamento é o que mantém isso verdade se um dia tiver.
    """
    base = texto(TEMPLATES / "base.html")

    assert "setTimeout(function () {" in base


def test_formulario_invalido_nao_trava_a_tela():
    """Campo obrigatório vazio não chega a enviar. Travar aí deixaria o aluno
    preso olhando um botão morto, sem nada ter acontecido.
    """
    base = texto(TEMPLATES / "base.html")

    assert "checkValidity" in base


def test_voltar_pelo_historico_destrava_o_botao():
    """O cache do navegador devolve a página com o botão como estava — e ele
    ficaria travado para sempre. É o mesmo caminho de "voltar" que já tinha
    dado problema antes (o 405).
    """
    base = texto(TEMPLATES / "base.html")

    assert "pageshow" in base
    assert "persisted" in base


def test_o_aviso_e_anunciado_para_leitor_de_tela():
    base = texto(TEMPLATES / "base.html")

    assert 'aviso.setAttribute("role", "status")' in base
    assert 'botao.setAttribute("aria-busy", "true")' in base
    assert "form.appendChild(aviso)" in base, "o aviso nao chega a tela"


# ====================== TEXTO PRÓPRIO ONDE A ESPERA É LONGA ======================


@pytest.mark.parametrize(
    "tela,acao",
    [
        ("laboratorio.html", "laboratorio.tela_laboratorio"),
        ("oraculo.html", "oraculo.tela_oraculo"),
        ("treino.html", "treino.iniciar_treino"),
        ("rpg.html", "rpg.continuar_rpg"),
        ("escape_room.html", "escape_room.iniciar_escape_room"),
        ("enem.html", "enem.iniciar_enem"),
        ("boss_rush.html", "boss_rush.iniciar_boss_rush"),
    ],
)
def test_os_formularios_que_chamam_a_ia_dizem_o_que_esperam(tela, acao):
    """O genérico já travaria o botão. Mas nesses a espera chega a 22 s, e aí
    vale dizer o que está acontecendo no vocabulário de cada modo — é o mesmo
    que o app já usa ("O Mestre narra o próximo capítulo").
    """
    conteudo = texto(TEMPLATES / tela)
    trecho = conteudo.split(acao, 1)[1][:200]

    assert "data-aviso-texto" in trecho, f"{acao} sem texto próprio"


# ====================== O TEMPO DE RESPOSTA ======================


@pytest.mark.parametrize("rota", ["laboratorio_fla.py", "oraculo_fla.py", "treino_fla.py"])
def test_os_modos_registram_o_tempo_de_resposta(rota):
    """Medido: 68 dos 107 logs reais estavam sem tempo, todos do Laboratório
    e do Oráculo. O Treino já fazia certo e serve de referência.
    """
    conteudo = texto(RAIZ / "web" / "routes" / rota)

    assert "registrar_log_com_tempo" in conteudo
    assert "registrar_log(" not in conteudo, "ainda registra sem tempo"


# MELHORIA: os testes acima leem TEXTO do arquivo, e a mutação mostrou que
# isso é fraco — trocar a linha por outra que ainda contenha a palavra
# procurada passava despercebido. Os de baixo exercitam a rota de verdade e
# olham o que chegou ao log.


@pytest.mark.parametrize(
    "modo,rota_gerar,rota_responder,campo_estado",
    [
        ("laboratorio", "/laboratorio/", "/laboratorio/responder", "desafio_laboratorio"),
        ("oraculo", "/oraculo/", "/oraculo/responder", "enigma_atual"),
    ],
)
def test_o_tempo_chega_ao_log_de_verdade(
    monkeypatch, client, modo, rota_gerar, rota_responder, campo_estado
):
    """O que importa não é a linha existir, é o número chegar ao banco."""
    import web.routes.laboratorio_fla as lab
    import web.routes.oraculo_fla as ora

    registrado = {}

    def espiao(dados, tempo_resposta=None):
        registrado["dados"] = dados
        registrado["tempo"] = tempo_resposta
        return None

    monkeypatch.setattr(lab, "registrar_log_com_tempo", espiao)
    monkeypatch.setattr(ora, "registrar_log_com_tempo", espiao)

    modulo = lab if modo == "laboratorio" else ora
    guardado = {}
    monkeypatch.setattr(modulo, "salvar_estado_flask",
                        lambda chave, valor: guardado.__setitem__(chave, valor))
    monkeypatch.setattr(modulo, "obter_estado_flask",
                        lambda chave, padrao=None: guardado.get(chave, padrao))
    monkeypatch.setattr(modulo, "limpar_estado_flask", lambda chave: guardado.pop(chave, None))

    questao = {
        "pergunta": "Quanto é 2 + 2?",
        "opcoes": ["4", "3", "5", "6"],
        "correta": 0,
        "materia": "Matematica",
        "nivel": "Médio",
        "ano_escolar": "1º EM",
        "serie_tipo": "EM",
    }
    if modo == "laboratorio":
        monkeypatch.setattr(lab, "gerar_desafio_exatas", lambda *a, **k: dict(questao))
    else:
        monkeypatch.setattr(ora, "invocar_enigma", lambda *a, **k: dict(questao))
    monkeypatch.setattr(modulo, "registrar_pontuacao_acerto", lambda *a, **k: 0)
    monkeypatch.setattr(modulo, "sincronizar_aluno_da_requisicao", lambda *a, **k: None)

    from tests.apoio_flask import carimbar_sessao

    with client.session_transaction() as sessao:
        sessao["aluno_id"] = "aluno-1"
        sessao["escola_id"] = "escola-1"
        sessao["ano_escolar"] = "1º EM"
        # O gate central de `flask_app.exigir_login` recusa quem não tem papel.
        sessao["usuario_role"] = "aluno"
        carimbar_sessao(sessao)

    client.post(rota_gerar, data={"materia": "Matematica", "nivel": "Médio", "tema": ""})
    assert campo_estado in guardado, "a questão não foi guardada"
    assert "_tempo_inicio" in guardado[campo_estado], "o instante não foi anotado"

    client.post(rota_responder, data={"resposta": "0"})

    assert "tempo" in registrado, "o log não foi registrado"
    assert isinstance(registrado["tempo"], float), f"tempo não veio: {registrado.get('tempo')!r}"
    assert registrado["tempo"] >= 0


@pytest.mark.parametrize("rota", ["laboratorio_fla.py", "oraculo_fla.py"])
def test_questao_antiga_sem_marcador_nao_quebra(rota):
    """Uma questão salva antes desta mudança volta do estado sem
    `_tempo_inicio`. O log tem de continuar sendo gravado, só que sem tempo.
    """
    modulo = __import__(
        f"web.routes.{rota[:-3]}", fromlist=["_tempo_desde"]
    )

    assert modulo._tempo_desde(None) is None
    assert modulo._tempo_desde("texto") is None
    assert modulo._tempo_desde(0) is not None


def test_o_tempo_e_positivo_e_plausivel():
    import time

    from web.routes.laboratorio_fla import _tempo_desde

    agora = time.time()
    assert _tempo_desde(agora) == pytest.approx(0.0, abs=1.0)
    assert _tempo_desde(agora - 30) == pytest.approx(30.0, abs=1.0)


def test_relogio_para_tras_nao_gera_tempo_negativo():
    """O piso em zero: `tempo_resposta` tem `check (>= 0)` no banco, e um
    valor negativo derrubaria o insert — perdendo o log inteiro do aluno.
    """
    import time

    from web.routes.laboratorio_fla import _tempo_desde

    assert _tempo_desde(time.time() + 60) == 0.0
