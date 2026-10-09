"""O código da BNCC sai do campo errado, e todo modo passa a ter BNCC.

Dois defeitos, achados ao investigar por que `codigo_bncc` estava **0%**
preenchido nos logs reais.

**1. O código estava no campo da habilidade.** `BNCC_REFERENCIAS` guarda
`("Matemática e suas Tecnologias", "Competência específica 1", "EM13MAT101")`
— o terceiro elemento é o **código**, mas era desempacotado numa variável
chamada `habilidade` e gravado em `habilidade_bncc`. A coluna `codigo_bncc`,
que existe exatamente para ele, ficava vazia. O mesmo no banco do Fundamental
(`EF07MA01`).

Isso deixava o log com três formatos misturados no mesmo campo — só o código,
código + descrição (da IA), ou só a descrição. É a mesma mistura já corrigida
na dificuldade.

**2. Metade dos modos não gravava BNCC nenhuma.** Medido nos logs:

| modo | preenchia |
|---|---|
| Boss Rush ENEM | 100% |
| Oráculo | 33% |
| Treino | 18% |
| **Laboratório** (o mais usado) | **0%** |
| RPG, Escape Room, ENEM | 0% |

E havia um caso pior que vazio: o banco do RPG **inventava** a BNCC —
`RPG-QUI-01` não é código de habilidade nenhum, e a competência era `"RPG
educacional: <perfil>"`. Isso parece BNCC no painel do professor e não é.

Depois: **50.900 de 50.900** questões offline com código válido e descrição
legível.
"""

from __future__ import annotations

import re

import pytest

import services.banks.em as em
import services.banks.fundamental as ef
import services.banks.laboratorio as lab
import services.banks.rpg as rp
from services.banks.em import BNCC_REFERENCIAS, HABILIDADES_BNCC
from services.banks.fundamental import HABILIDADES_BNCC_EF

# O formato oficial: EM13MAT101, EF07MA01, EM13LGG403...
CODIGO_BNCC = re.compile(r"^E[FM]\d{2}[A-Z]{2,4}\d{2,3}[A-Z]?$")


def uma_de_cada_banco():
    yield "EM", em.listar_questoes_em("Matematica")[0]
    yield "EF", ef.listar_questoes_ef("Matematica")[0]
    yield "RPG", rp.listar_questoes_rpg("Quimica")[0]
    yield "LAB-EM", lab.listar_questoes_laboratorio("Fisica", "EM")[0]
    yield "LAB-EF", lab.listar_questoes_laboratorio("Matematica", "EF")[0]


def todas_as_questoes():
    for materia in em.MATERIAS:
        yield from em.listar_questoes_em(materia)
    for materia in ef.MATERIAS:
        yield from ef.listar_questoes_ef(materia)
    for materia in rp.MATERIAS:
        yield from rp.listar_questoes_rpg(materia)
    for materia in lab.MATERIAS_LAB_OFFLINE:
        yield from lab.listar_questoes_laboratorio(materia, "EM")
    for materia in lab.MATERIAS_LAB_EF_OFFLINE:
        yield from lab.listar_questoes_laboratorio(materia, "EF")


# ====================== O CÓDIGO VAI PARA O CAMPO DO CÓDIGO ======================


@pytest.mark.parametrize("banco,questao", list(uma_de_cada_banco()))
def test_o_codigo_esta_no_campo_do_codigo(banco, questao):
    assert CODIGO_BNCC.match(str(questao.get("codigo_bncc") or "")), banco


@pytest.mark.parametrize("banco,questao", list(uma_de_cada_banco()))
def test_a_habilidade_e_uma_frase_e_nao_um_codigo(banco, questao):
    """Era o defeito: "EM13MAT101" ocupava o campo da descrição. Um código
    não diz nada a quem lê o relatório; a frase diz.
    """
    habilidade = str(questao.get("habilidade_bncc") or "")

    assert habilidade, f"{banco} sem habilidade"
    assert not CODIGO_BNCC.match(habilidade), f"{banco} ainda guarda o código aqui"
    assert len(habilidade) > 30, f"{banco}: descrição curta demais para ser uma"


def test_os_50900_tem_codigo_valido_e_descricao():
    """Era 0%. A medição que fecha os dois passos."""
    sem_codigo, sem_descricao = [], []
    total = 0
    for questao in todas_as_questoes():
        total += 1
        if not CODIGO_BNCC.match(str(questao.get("codigo_bncc") or "")):
            sem_codigo.append(questao.get("id_offline"))
        habilidade = str(questao.get("habilidade_bncc") or "")
        if not habilidade or CODIGO_BNCC.match(habilidade):
            sem_descricao.append(questao.get("id_offline"))

    assert total > 50000, f"só {total} questões varridas"
    assert not sem_codigo, f"{len(sem_codigo)} sem código válido"
    assert not sem_descricao, f"{len(sem_descricao)} sem descrição"


# ====================== O RPG PARA DE INVENTAR ======================


def test_o_rpg_nao_inventa_mais_codigo_de_habilidade():
    """`RPG-QUI-01` não existe na BNCC. Guardar isso é pior que deixar vazio:
    aparece no painel do professor com cara de referência oficial.
    """
    inventados = [
        q.get("id_offline")
        for materia in rp.MATERIAS
        for q in rp.listar_questoes_rpg(materia)
        if str(q.get("habilidade_bncc") or "").startswith("RPG-")
        or str(q.get("competencia_bncc") or "").startswith("RPG educacional")
    ]

    assert not inventados, f"{len(inventados)} questões com BNCC inventada"


# ====================== TODO MODO GRAVA BNCC ======================


@pytest.mark.parametrize(
    "arquivo",
    [
        "web/routes/laboratorio_fla.py",
        "web/routes/rpg_fla.py",
        "web/routes/oraculo_fla.py",
        "web/routes/treino_fla.py",
        "web/routes/enem_fla.py",
        "web/routes/boss_rush_fla.py",
        "web/routes/escape_room_fla.py",
        "st/ui/tela_laboratorio_st.py",
        "st/ui/tela_rpg_st.py",
    ],
)
def test_a_rota_leva_a_bncc_ao_log(arquivo):
    """O Laboratório e o RPG tinham o dado na mão e não o gravavam — 70 dos
    107 logs reais saíam em branco."""
    from pathlib import Path

    fonte = (Path(__file__).resolve().parent.parent / arquivo).read_text(encoding="utf-8")

    for campo in ("area_bncc", "competencia_bncc", "habilidade_bncc", "codigo_bncc"):
        assert campo in fonte, f"{arquivo} não leva {campo}"


def test_a_bncc_chega_ao_log_do_laboratorio_de_verdade(monkeypatch, client):
    """O teste acima lê TEXTO do arquivo, e a mutação mostrou que isso é
    fraco: trocar `desafio.get("codigo_bncc")` por `None` mantém a palavra
    ali e passa. Este exercita a rota e olha o que chegou ao log.
    """
    import web.routes.laboratorio_fla as rota
    from tests.apoio_flask import carimbar_sessao

    registrado = {}
    monkeypatch.setattr(rota, "registrar_log_com_tempo",
                        lambda dados, tempo_resposta=None: registrado.update(dados))

    guardado = {}
    monkeypatch.setattr(rota, "salvar_estado_flask",
                        lambda chave, valor: guardado.__setitem__(chave, valor))
    monkeypatch.setattr(rota, "obter_estado_flask",
                        lambda chave, padrao=None: guardado.get(chave, padrao))
    monkeypatch.setattr(rota, "limpar_estado_flask", lambda chave: guardado.pop(chave, None))
    monkeypatch.setattr(rota, "registrar_pontuacao_acerto", lambda *a, **k: 0)
    monkeypatch.setattr(rota, "sincronizar_aluno_da_requisicao", lambda *a, **k: None)
    monkeypatch.setattr(
        rota, "gerar_desafio_exatas",
        lambda *a, **k: dict(lab.listar_questoes_laboratorio("Fisica", "EM")[0]),
    )

    with client.session_transaction() as sessao:
        sessao["aluno_id"] = "aluno-1"
        sessao["escola_id"] = "escola-1"
        sessao["ano_escolar"] = "1º EM"
        sessao["usuario_role"] = "aluno"
        carimbar_sessao(sessao)

    client.post("/laboratorio/", data={"materia": "Fisica", "nivel": "Médio", "tema": ""})
    client.post("/laboratorio/responder", data={"resposta": "0"})

    assert CODIGO_BNCC.match(str(registrado.get("codigo_bncc") or "")), (
        f"o código não chegou ao log: {registrado.get('codigo_bncc')!r}"
    )
    assert registrado.get("area_bncc")
    assert len(str(registrado.get("habilidade_bncc") or "")) > 30


def test_a_bncc_chega_ao_log_do_rpg_de_verdade():
    """O gêmeo do teste acima, pelo caminho do Streamlit. O RPG era o caso
    pior: tinha o dado na mão, não o gravava, e ainda inventava um código
    que não existe na BNCC.
    """
    from st.ui.tela_rpg_st import log_da_resposta_rpg

    desafio = rp.listar_questoes_rpg("Quimica")[0]
    log = log_da_resposta_rpg(
        desafio, {"materia": "Quimica"}, {"id": "aluno-1"}, "escola-1", "resposta", True
    )

    assert CODIGO_BNCC.match(str(log.get("codigo_bncc") or "")), log.get("codigo_bncc")
    assert log.get("area_bncc")
    assert len(str(log.get("habilidade_bncc") or "")) > 30
    assert not str(log.get("habilidade_bncc") or "").startswith("RPG-")


def test_a_bncc_chega_ao_log_da_rota_do_rpg(monkeypatch, client):
    """O terceiro caminho: a rota Flask do RPG. Os três (Laboratório Flask,
    RPG Streamlit e RPG Flask) precisam de teste próprio — ler o texto do
    arquivo deixava passar trocar o valor por `None`.
    """
    import web.routes.rpg_fla as rota
    from tests.apoio_flask import carimbar_sessao

    registrado = {}
    monkeypatch.setattr(rota, "registrar_log_com_tempo",
                        lambda dados, tempo_resposta=None: registrado.update(dados))
    monkeypatch.setattr(rota, "registrar_pontuacao_acerto", lambda *a, **k: 0)

    desafio = dict(rp.listar_questoes_rpg("Quimica")[0])
    estado = {
        "desafio_atual": desafio,
        "config_rpg": {"materia": "Quimica", "nivel": "Medio"},
        "xp": 0, "hp": 100, "tempo_inicio": 0,
        "ultima_escolha": {}, "ultima_checagem_escolha": {},
        "historico_desafios": [], "historico": [], "fase": 1,
        "temas_usados": [], "cena_atual": {},
    }
    monkeypatch.setattr(rota, "_estado_atual", lambda: estado)

    with client.session_transaction() as sessao:
        sessao["aluno_id"] = "aluno-1"
        sessao["escola_id"] = "escola-1"
        sessao["ano_escolar"] = "1º EM"
        sessao["usuario_role"] = "aluno"
        carimbar_sessao(sessao)

    client.post("/rpg/responder", data={"resposta": str(desafio["correta"])})

    assert CODIGO_BNCC.match(str(registrado.get("codigo_bncc") or "")), (
        f"o código não chegou ao log do RPG: {registrado.get('codigo_bncc')!r}"
    )
    assert registrado.get("area_bncc")


def test_a_coluna_do_codigo_e_conhecida_pelo_log():
    """Fora de `LOG_COLUMNS`, o campo é descartado em silêncio antes do
    insert — foi assim que ele ficou 0% mesmo existindo no banco."""
    from repositories.log_repo import LOG_COLUMNS

    assert "codigo_bncc" in LOG_COLUMNS


def test_o_log_guarda_codigo_e_descricao_separados():
    from repositories.log_repo import preparar_payload_log

    questao = lab.listar_questoes_laboratorio("Fisica", "EM")[0]
    dados = preparar_payload_log({
        "aluno_id": "a", "escola_id": "e", "materia": "LAB-Fisica", "resultado": "Acertou",
        "area_bncc": questao["area_bncc"],
        "competencia_bncc": questao["competencia_bncc"],
        "habilidade_bncc": questao["habilidade_bncc"],
        "codigo_bncc": questao["codigo_bncc"],
    })

    assert CODIGO_BNCC.match(dados["codigo_bncc"])
    assert not CODIGO_BNCC.match(dados["habilidade_bncc"])


# ====================== AS TABELAS ======================


def test_toda_materia_do_medio_tem_descricao():
    """Uma matéria sem entrada gravaria descrição vazia, e o campo voltaria a
    não servir para nada — só que em silêncio."""
    assert set(HABILIDADES_BNCC) == set(BNCC_REFERENCIAS)


def test_toda_materia_do_fundamental_tem_descricao():
    assert set(HABILIDADES_BNCC_EF) == set(ef.MATERIAS)


@pytest.mark.parametrize("tabela", [HABILIDADES_BNCC, HABILIDADES_BNCC_EF])
def test_nenhuma_descricao_e_um_codigo_disfarçado(tabela):
    """A troca que originou tudo: se alguém colar um código aqui, o defeito
    volta sem ninguém perceber."""
    codigos = [m for m, texto in tabela.items() if CODIGO_BNCC.match(str(texto))]

    assert not codigos, codigos


@pytest.mark.parametrize("materia,dados", list(BNCC_REFERENCIAS.items()))
def test_a_tabela_de_referencia_guarda_codigo_no_terceiro_lugar(materia, dados):
    """O contrato que o desempacotamento assume — e que foi lido errado
    durante todo esse tempo."""
    _area, _competencia, codigo = dados

    assert CODIGO_BNCC.match(codigo), f"{materia}: {codigo!r} não é código BNCC"
