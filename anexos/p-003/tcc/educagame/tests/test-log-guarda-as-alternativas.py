"""As alternativas vão para o log, em todos os modos.

Por que existe
--------------
A validação `_explicacao_aponta_para_outra_alternativa` recusa a questão
quando a IA marca uma alternativa e explica outra. Hoje ela roda só para
humanas e linguagens, porque exatas tem a checagem numérica no lugar dela --
e uma questão CONCEITUAL de exatas ("no MUV, a aceleração é...") não tem
número a conferir. Cai entre as duas e não é conferida por nenhuma.

Medido em 10/09/2026, antes de mexer, sobre 492 questões de exatas dos bancos
próprios: estender a regra como está recusaria **6,50%** de questões boas --
porque a explicação boa cita as alternativas erradas para descartá-las. Não
dá para ligar assim.

A candidata estreita (só recusar quando a explicação AFIRMA qual é a correta)
deu 0 de 492 -- mas **0 porque nenhuma explicação do banco afirma nada**. O
número é vazio, não é prova. É a armadilha de corpus de sempre: o banco
responde "a regra recusa o que NÓS escrevemos?", pergunta mais fraca que a
que importa.

Para medir contra o que a IA escreve, falta a lista de alternativas do lado
real. O log guardava `resposta_correta` (o TEXTO da certa) e nunca a lista --
e sem a lista não dá para saber se a explicação nomeia OUTRA alternativa.

Este arquivo cobra que a lista chegue lá, modo por modo. Um por um porque foi
exatamente assim que o aviso de banco offline ficou faltando em três dos oito
modos: o trabalho estava feito e faltava a última linha.
"""

from __future__ import annotations

import importlib

import pytest

from tests.apoio_flask import carimbar_sessao

# (modo, módulo da rota, url do responder, montador do estado)
QUESTAO = {
    "pergunta": "No Movimento Uniformemente Variado, a aceleração é:",
    "opcoes": ["constante e diferente de zero", "sempre nula", "sempre crescente", "variável"],
    "alternativas": ["constante e diferente de zero", "sempre nula", "sempre crescente", "variável"],
    "correta": 0,
    "explicacao": [{"tipo": "texto", "conteudo": "No MUV a aceleração não muda."}],
    "materia": "Fisica",
}


def _sessao_de_aluno(client):
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["escola_id"] = "escola-1"
        sess["aluno_id"] = "aluno-1"
        sess["ano_escolar"] = "1º EM"
        carimbar_sessao(sess)


MODOS = [
    ("treino", "treino_fla", "/treino/responder", "treino_flask",
     {"questao": dict(QUESTAO), "materia": "Fisica", "acertos": 0, "erros": 0, "indice": 0, "total": 5}),
    ("laboratorio", "laboratorio_fla", "/laboratorio/responder", "desafio_laboratorio",
     dict(QUESTAO)),
    ("oraculo", "oraculo_fla", "/oraculo/responder", "enigma_atual",
     dict(QUESTAO)),
]


@pytest.mark.parametrize("modo, modulo, url, chave, estado", MODOS,
                         ids=[m[0] for m in MODOS])
def test_o_modo_manda_as_alternativas_para_o_log(client, monkeypatch, modo, modulo, url, chave, estado):
    """Comportamento: o que a rota ENTREGA ao gravador do log.

    Um teste que só procurasse `"opcoes"` no texto da rota passaria mesmo com
    a lista chegando vazia -- foi assim que `erro_ia` enganou a bateria do
    aviso de banco offline."""
    rota = importlib.import_module(f"web.routes.{modulo}")

    gravados: list[dict] = []
    monkeypatch.setattr(
        rota, "registrar_log_com_tempo",
        lambda dados, *a, **k: gravados.append(dict(dados)),
    )
    monkeypatch.setattr(rota, "obter_estado_flask", lambda nome, padrao=None: (
        dict(estado) if nome == chave else padrao
    ))
    monkeypatch.setattr(rota, "salvar_estado_flask", lambda *a, **k: None)
    monkeypatch.setattr(rota, "limpar_estado_flask", lambda *a, **k: None)
    _sessao_de_aluno(client)

    client.post(url, data={"resposta": "0"}, follow_redirects=False)

    assert gravados, f"o {modo} não gravou log nenhum"
    opcoes = gravados[0].get("opcoes")
    assert opcoes, f"o {modo} gravou log sem as alternativas"
    assert len(opcoes) == 4, f"o {modo} mandou {len(opcoes)} alternativas"


def test_toda_rota_que_grava_log_manda_as_alternativas():
    """A varredura que pega o modo novo.

    Os três de cima são conferidos pelo comportamento; este cobre os outros
    quatro (ENEM, Escape Room, Boss Rush, RPG), cujo estado é mais custoso de
    montar. É estrutural de propósito, e o seu limite está dito: garante que
    a linha existe, não que o valor chega cheio.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    faltando = []
    for arquivo in sorted((raiz / "web" / "routes").glob("*_fla.py")):
        fonte = arquivo.read_text(encoding="utf-8")
        if "registrar_log_com_tempo(" not in fonte:
            continue
        if '"opcoes":' not in fonte:
            faltando.append(arquivo.name)

    assert not faltando, f"gravam log sem mandar as alternativas: {faltando}"


def test_a_lista_guardada_preserva_a_posicao_do_gabarito():
    """O gabarito é um ÍNDICE desta lista.

    Compactar a lista para tirar uma alternativa vazia moveria as de baixo, e
    a medição passaria a apontar para a alternativa errada -- pior do que não
    medir, porque parece medida."""
    from repositories.log_repo import _opcoes_para_json

    guardadas = _opcoes_para_json(["primeira", "", "terceira"])

    assert guardadas == ["primeira", "", "terceira"]
    assert guardadas[2] == "terceira", "a terceira mudou de lugar"


def test_lista_toda_vazia_nao_vira_linha_no_banco():
    """Gravar [] faria a consulta contar como "tem alternativas" o que não
    tem, e o denominador da medição sairia inflado."""
    from repositories.log_repo import _opcoes_para_json, preparar_payload_log

    assert _opcoes_para_json(["", "  "]) == []
    assert _opcoes_para_json(None) == []
    assert _opcoes_para_json("não é lista") == []

    payload = preparar_payload_log({"materia": "Fisica", "resultado": "Acertou", "opcoes": []})
    assert "opcoes" not in payload


def test_a_lista_e_cortada_para_nao_inchar_o_log():
    from repositories.log_repo import _MAX_OPCOES_LOG, _opcoes_para_json

    guardadas = _opcoes_para_json([f"alternativa {i}" for i in range(20)])

    assert len(guardadas) == _MAX_OPCOES_LOG
    assert _MAX_OPCOES_LOG >= 5, "o ENEM tem cinco alternativas (A-E)"
