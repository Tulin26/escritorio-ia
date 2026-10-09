"""A rota que monta o painel do professor.

`tela_professor` tinha 149 linhas e decidia, tudo no mesmo lugar: qual aba
abrir, quem pode ver o ADM, qual aluno e qual matéria filtrar, e o que buscar
na rede. Quase nada disso dava para conferir sem subir o Flask inteiro, e o
que não dá para conferir barato não é conferido.

Depois de separar as decisões do desenho, a mutação apontou seis linhas que
nenhum teste sustentava. Estes são os testes dessas seis -- a maioria é
defeito silencioso, do tipo que a página continua abrindo e mostrando número
errado.

O ADM ficou de fora daqui de propósito: a tranca de "só desenvolvedor entra"
já morre em `test_duas_areas_do_desenvolvedor.py`, que é onde ela mora.
"""

from __future__ import annotations

import pytest

from services.professor_service import ABAS
from web.routes import professor_fla
from web.routes.professor_fla import aba_escolhida

from tests.apoio_flask import carimbar_sessao

ESCOLA = {"id": "esc-1", "nome": "ETEC", "slug": "etec"}

ALUNOS = [
    {"id": "a1", "nome": "Ronnie Rillo", "ano_escolar": "1º EM", "periodo": "Manhã"},
    {"id": "a2", "nome": "Ana Lima", "ano_escolar": "2º EM", "periodo": "Tarde"},
]


def _log(aluno_id: str, materia: str, resultado: str, i: int = 0) -> dict:
    return {
        "id": f"log-{aluno_id}-{i}", "aluno_id": aluno_id, "escola_id": ESCOLA["id"],
        "materia": materia, "modo": "oraculo-flask", "resultado": resultado,
        "pergunta_texto": f"Pergunta {i}", "resposta_correta": "A", "resposta_aluno": "A",
        "tempo_resposta": 30, "data_hora": "2026-09-01T10:00:00+00:00",
    }


@pytest.fixture
def sem_rede(monkeypatch):
    """Nenhuma consulta sai para o Supabase; e conta quem foi chamado."""
    chamadas: dict[str, int] = {}

    def _contar(nome, valor):
        def _falso(*_a, **_k):
            chamadas[nome] = chamadas.get(nome, 0) + 1
            return valor() if callable(valor) else valor
        return _falso

    monkeypatch.setattr(professor_fla, "buscar_alunos", _contar("buscar_alunos", lambda: [dict(a) for a in ALUNOS]))
    monkeypatch.setattr(professor_fla, "buscar_logs", _contar("buscar_logs", lambda: []))
    monkeypatch.setattr(professor_fla, "buscar_resumo_turma", _contar("buscar_resumo_turma", lambda: []))
    monkeypatch.setattr(professor_fla, "listar_rpg_configs", _contar("listar_rpg_configs", lambda: []))
    monkeypatch.setattr(professor_fla, "listar_escolas", _contar("listar_escolas", lambda: [dict(ESCOLA)]))
    monkeypatch.setattr(professor_fla, "listar_contas", _contar("listar_contas", lambda: []))
    monkeypatch.setattr(professor_fla, "_diagnostico_do_sistema", _contar("diagnostico", lambda: {}))
    return chamadas


def _entrar(client, papel: str = "professor", escola_id: str | None = ESCOLA["id"]):
    with client.session_transaction() as sess:
        sess["usuario_role"] = papel
        sess["escola_id"] = escola_id
        sess["escola_nome"] = ESCOLA["nome"]
        carimbar_sessao(sess)


@pytest.fixture
def entregue(monkeypatch):
    """O que a rota entrega ao template, sem passar pelo HTML.

    Vale mais que raspar a página: o defeito de trocar acertos por erros
    aparece aqui como dois números trocados, e no HTML apareceria como dois
    números plausíveis em lugares parecidos.
    """
    capturado: dict = {}

    def _falso(_nome, **kwargs):
        capturado.clear()
        capturado.update(kwargs)
        return "<html></html>"

    monkeypatch.setattr(professor_fla, "render_template", _falso)
    return capturado


# ====================== QUAL ABA A URL CONSEGUE PEDIR ======================


@pytest.mark.parametrize("pedida", [None, "", "xpto", "ADM", "analises "])
def test_aba_que_nao_existe_cai_em_analises(pedida):
    """Sem isto a página abre com a tira de abas e NENHUM conteúdo, e não diz
    por quê. Um link antigo ou um erro de digitação bastam."""
    assert aba_escolhida(pedida, eh_desenvolvedor=True) == "analises"


@pytest.mark.parametrize("valor", [item["valor"] for item in ABAS])
def test_toda_aba_de_verdade_sobrevive(valor):
    """O par que protege: apertar a regra não pode fechar aba legítima.

    Roda sobre a lista real de abas, então uma aba nova nasce coberta."""
    assert aba_escolhida(valor, eh_desenvolvedor=True) == valor


def test_o_professor_nao_alcanca_o_adm_pela_barra_de_enderecos():
    """O `before_request` do blueprint deixa professor entrar; "adm" é só de
    desenvolvedor. Esta é a segunda tranca."""
    assert aba_escolhida("adm", eh_desenvolvedor=False) == "analises"
    assert aba_escolhida("adm", eh_desenvolvedor=True) == "adm"


# ====================== O FILTRO DE MATÉRIA ======================


def test_materia_que_o_aluno_nao_tem_volta_para_todas(client, sem_rede, entregue, monkeypatch):
    """Acontece ao trocar de aluno com o filtro montado: o link continua
    pedindo Física e o novo aluno nunca fez Física. Mostrar tudo é melhor que
    mostrar uma tela vazia sem explicação."""
    monkeypatch.setattr(
        professor_fla, "buscar_logs",
        lambda _e: [_log("a1", "Matematica", "Acertou", i) for i in range(3)],
    )
    _entrar(client)

    client.get("/professor/?aba=analises&aluno_id=a1&materia=Fisica")

    assert entregue["materia"] == "todas"
    assert entregue["materia_label"] == "Todas as matérias"


def test_materia_que_o_aluno_tem_e_respeitada(client, sem_rede, entregue, monkeypatch):
    """O par: a queda para "todas" não pode virar um filtro que nunca filtra."""
    monkeypatch.setattr(
        professor_fla, "buscar_logs",
        lambda _e: [_log("a1", "Matematica", "Acertou", 0), _log("a1", "Fisica", "Errou", 1)],
    )
    _entrar(client)

    client.get("/professor/?aba=analises&aluno_id=a1&materia=Fisica")

    assert entregue["materia"] == "Fisica"
    # A chave filtra; o titulo da tela mostra o rotulo (ver
    # tests/test_textos_das_telas_escuras.py).
    assert entregue["materia_label"] == "Física"


# ====================== OS NÚMEROS DO TOPO ======================


def test_acertos_e_erros_nao_saem_trocados(client, sem_rede, entregue, monkeypatch):
    """Trocar os dois passava por toda a bateria, e é o defeito mais caro que
    esta tela pode ter: o professor lê "8 acertos" numa turma que errou 8."""
    logs = [_log("a1", "Matematica", "Acertou", i) for i in range(7)]
    logs += [_log("a1", "Matematica", "Errou", 100 + i) for i in range(2)]
    monkeypatch.setattr(professor_fla, "buscar_logs", lambda _e: logs)
    _entrar(client)

    client.get("/professor/?aba=analises&aluno_id=a1")

    assert entregue["acertos"] == 7, "os acertos não são os acertos"
    assert entregue["erros"] == 2, "os erros não são os erros"


def test_a_lista_de_questoes_e_cortada(client, sem_rede, entregue, monkeypatch):
    """A tela mostra as últimas questões, não o histórico inteiro. Sem o
    corte, um aluno com dois mil registros vira uma página de dois mil <tr>
    -- no plano gratuito do Render, com 60s de timeout."""
    monkeypatch.setattr(
        professor_fla, "buscar_logs",
        lambda _e: [_log("a1", "Matematica", "Acertou", i) for i in range(200)],
    )
    _entrar(client)

    client.get("/professor/?aba=analises&aluno_id=a1")

    assert len(entregue["logs_recorte"]) == 20, "a lista foi para a tela inteira"
    assert entregue["metricas"]["total"] == 200, "as métricas passaram a contar só as 20 da tela"


# ====================== O QUE SÓ SE BUSCA QUANDO APARECE ======================


@pytest.mark.parametrize("aba", ["analises", "ranking", "resumo", "matricula", "rpg"])
def test_o_painel_do_adm_nao_e_buscado_nas_outras_abas(client, sem_rede, aba):
    """Cada leitura é uma ida à rede -- até o cache mora no Supabase. Buscar
    contas e diagnóstico em toda carga da página eram duas idas jogadas fora,
    e nenhum teste segurava isso: some a guarda e a página continua igual.
    """
    _entrar(client, papel="desenvolvedor")

    client.get(f"/professor/?aba={aba}")

    assert sem_rede.get("listar_contas", 0) == 0, f"buscou as contas do ADM na aba {aba}"
    assert sem_rede.get("diagnostico", 0) == 0, f"rodou o diagnóstico na aba {aba}"
    # a lista de escolas é lida uma vez, para saber em que escola o professor
    # está. A segunda leitura é do painel do ADM, e só cabe quando ele abre.
    assert sem_rede.get("listar_escolas", 0) == 1, (
        f"aba {aba}: leu a lista de escolas {sem_rede.get('listar_escolas', 0)}x"
    )


def test_o_painel_do_adm_e_buscado_quando_ele_aparece(client, sem_rede, entregue):
    """O par: economizar não pode virar tela vazia."""
    _entrar(client, papel="desenvolvedor")

    client.get("/professor/?aba=adm")

    assert sem_rede.get("listar_contas", 0) == 1
    assert sem_rede.get("diagnostico", 0) == 1
    assert sem_rede.get("listar_escolas", 0) == 2, "o ADM ficou sem a lista de escolas"
    assert entregue["aba"] == "adm"
