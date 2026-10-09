"""Textos errados que as capturas de tela de 30/09/2026 mostraram.

As telas do TCC foram refeitas no tema escuro, e a revisão delas, uma a uma,
achou texto que nenhum teste de acento pegava -- os testes de acento leem o
que está ESCRITO no template, e quase tudo aqui chega por variável:

  - "Voltar para o inicio", no cabeçalho de TODA tela logada (base.html);
  - "Matematica" e "LAB-Matematica" no Perfil e no Meu Progresso. O log grava
    a matéria como CHAVE, com o modo na frente, e as duas telas a imprimiam
    crua -- a regra "a chave fica, a tela ganha rótulo" (MATERIAS_COM_ACENTO)
    não tinha chegado lá;
  - na Batalha de Guildas: "participacao", "bonus", "Lider", "lider:", as
    posições "1o, 2o" e "1 alunos | 1 participaram";
  - "--" no papel de travessão, na política de privacidade e na ajuda da meta
    de jornada. É o travessão dos comentários do código, que vazou para a
    tela;
  - a aba Análises do professor, que mostrava a matéria crua no filtro e no
    título quando se escolhia uma.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import web.routes.guildas_fla as guildas_fla
import web.routes.perfil_fla as perfil_fla
import web.routes.progresso_fla as progresso_fla
from core.metas import METAS
from core.privacidade import secoes_da_privacidade
from web.routes import professor_fla
from tests.apoio_flask import carimbar_sessao

TEMPLATES = Path(__file__).resolve().parents[1] / "web" / "templates"
ESCOLA_ID = "escola-telas"

# A matéria como o log grava: com e sem o modo na frente.
LOGS = [
    {"aluno_id": "aluno-1", "resultado": "Acertou", "materia": "LAB-Matematica", "modo": "laboratorio-flask",
     "pergunta_texto": "Resolva a equação"},
    {"aluno_id": "aluno-1", "resultado": "Errou", "materia": "Matematica", "modo": "oraculo-flask",
     "pergunta_texto": "Qual é o domínio"},
    {"aluno_id": "aluno-1", "resultado": "Acertou", "materia": "Fisica", "modo": "treino-flask",
     "pergunta_texto": "Qual é a unidade"},
]

# Chave crua na tela: a palavra sem acento, ou o prefixo de modo.
CHAVE_CRUA = re.compile(r"\bMatematica\b|\bFisica\b|LAB-")


@pytest.fixture
def aluno_logado(client, sem_rede_supabase):
    sem_rede_supabase.table("escolas").insert(
        {"id": ESCOLA_ID, "nome": "Escola", "slug": "escola", "mostrar_ranking": False, "modo_guilda": True}
    ).execute()
    with client.session_transaction() as sess:
        sess["usuario_role"] = "aluno"
        sess["usuario_escola_id"] = ESCOLA_ID
        sess["escola_id"] = ESCOLA_ID
        sess["escola_slug"] = "escola"
        sess["escola_nome"] = "Escola"
        sess["aluno_id"] = "aluno-1"
        sess["aluno_nome"] = "Ana Ribeiro"
        sess["ano_escolar"] = "3º Ano EM"
        carimbar_sessao(sess)
    return client


# --------------------------------------------------------------------------
# Matéria: a chave fica, a tela ganha rótulo


def test_o_progresso_mostra_a_materia_com_acento_e_sem_o_modo(aluno_logado, monkeypatch):
    monkeypatch.setattr(progresso_fla, "buscar_logs", lambda escola_id, aluno_id=None: [dict(log) for log in LOGS])
    monkeypatch.setattr(progresso_fla, "buscar_alunos", lambda escola_id: [])

    html = aluno_logado.get("/progresso/").get_data(as_text=True)

    # "Por matéria" (seletor e linha) e o histórico
    assert ">Matemática</option>" in html
    assert "<strong>Matemática</strong>" in html
    assert "Acertou · Matemática · Resolva a equação" in html
    assert "Acertou · Física · Qual é a unidade" in html
    assert CHAVE_CRUA.findall(html) == []


def test_o_perfil_mostra_a_materia_com_acento_e_sem_o_modo(aluno_logado, monkeypatch):
    aluno = {"id": "aluno-1", "nome": "Ana Ribeiro", "ano_escolar": "3º Ano EM", "pontos_totais": 30}
    monkeypatch.setattr(perfil_fla, "buscar_aluno_por_id", lambda aluno_id: dict(aluno))
    monkeypatch.setattr(perfil_fla, "buscar_logs", lambda escola_id, aluno_id=None: [dict(log) for log in LOGS])

    html = aluno_logado.get("/perfil/").get_data(as_text=True)

    # "Desempenho por matéria" (seletor e tabela) e o histórico
    assert ">Matemática</option>" in html
    assert "<strong>Matemática</strong>" in html
    assert re.search(r"em Matemática\s*<small>Laboratório", html)
    assert CHAVE_CRUA.findall(html) == []


def test_toda_tela_logada_diz_inicio_com_acento(aluno_logado, monkeypatch):
    monkeypatch.setattr(progresso_fla, "buscar_logs", lambda escola_id, aluno_id=None: [])
    monkeypatch.setattr(progresso_fla, "buscar_alunos", lambda escola_id: [])

    html = aluno_logado.get("/progresso/").get_data(as_text=True)

    assert "Voltar para o início" in html
    assert not [t.name for t in TEMPLATES.rglob("*.html") if "Voltar para o inicio" in t.read_text(encoding="utf-8")]


# --------------------------------------------------------------------------
# Batalha de Guildas


def test_as_guildas_falam_portugues_com_acento_e_concordancia(aluno_logado, monkeypatch):
    alunos = [
        {"id": "aluno-1", "nome": "Ana", "ano_escolar": "3º Ano EM", "periodo": "Manhã", "pontos_totais": 10},
        {"id": "aluno-2", "nome": "Bia", "ano_escolar": "1º Ano EM", "periodo": "Tarde", "pontos_totais": 0},
        {"id": "aluno-3", "nome": "Caio", "ano_escolar": "1º Ano EM", "periodo": "Tarde", "pontos_totais": 0},
    ]
    monkeypatch.setattr(guildas_fla, "buscar_alunos", lambda escola_id: [dict(a) for a in alunos])
    monkeypatch.setattr(guildas_fla, "buscar_logs", lambda escola_id, aluno_id=None: [dict(LOGS[0])])

    html = aluno_logado.get("/guildas/").get_data(as_text=True)

    for certo in (
        "participação semanal",
        "Líder semanal",
        "Pontos do líder",
        "líder: 3º Ano EM - Manhã",
        "+5 pontos de bônus",
        "<strong>1º</strong>",
        "<strong>2º</strong>",
        "1 aluno | 1 participou",
        "2 alunos | 0 participaram",
    ):
        assert certo in html, certo
    for errado in ("participacao", "Lider", "lider:", "bonus", "<strong>1o</strong>", "1 alunos", "1 participaram"):
        assert errado not in html, errado


# --------------------------------------------------------------------------
# Travessão


def _texto_visivel(template: str) -> str:
    """O que chega à tela: sem comentário, script, estilo nem expressão Jinja."""
    for padrao in (r"\{#.*?#\}", r"<!--.*?-->", r"<script\b.*?</script>", r"<style\b.*?</style>",
                   r"\{\{.*?\}\}", r"\{%.*?%\}"):
        template = re.sub(padrao, " ", template, flags=re.S | re.I)
    return template


def test_nenhuma_tela_usa_hifen_duplo_como_travessao():
    achados = {
        t.name: [linha.strip() for linha in _texto_visivel(t.read_text(encoding="utf-8")).splitlines() if " -- " in linha]
        for t in TEMPLATES.rglob("*.html")
    }

    assert {nome: linhas for nome, linhas in achados.items() if linhas} == {}


# Palavras que NUNCA aparecem certas sem acento no texto visivel. O dicionario
# do app (aplicar_acentos_pt) nao conhecia "alteracoes" nem "formulario", e
# os dois estavam na tela; esta lista nao depende dele. Fora dela, de
# proposito, o que e ambiguo: "esta" (demonstrativo), "e", "so", "ja", e
# "analise" (imperativo de analisar)...
SEM_ACENTO_NUNCA = {
    "inicio", "alteracoes", "formulario", "pagina", "paginas", "participacao",
    "bonus", "lider", "configuracoes", "preferencias", "questao", "questoes",
    "opcao", "opcoes", "numero", "conteudo", "historico", "tambem", "codigo",
    "ultimo", "ultima", "proximo", "proxima", "voce", "nao", "matematica",
    "fisica", "quimica", "historia", "ciencias", "portugues", "educacao",
    "nivel", "facil", "dificil", "periodo", "titulo",
}


def _sem_tags(template: str) -> str:
    return re.sub(r"<[^>]+>", " ", _texto_visivel(template))


def test_nenhum_template_escreve_palavra_que_so_existe_com_acento():
    achados = {}
    for t in TEMPLATES.rglob("*.html"):
        palavras = set(re.findall(r"[^\W\d_]+", _sem_tags(t.read_text(encoding="utf-8")).lower()))
        if palavras & SEM_ACENTO_NUNCA:
            achados[t.name] = sorted(palavras & SEM_ACENTO_NUNCA)

    assert achados == {}


def test_a_politica_e_a_meta_usam_travessao():
    paragrafos = [p for secao in secoes_da_privacidade() for p in secao["paragrafos"]]
    textos_da_meta = [texto for meta in METAS for texto in (meta.label, meta.ajuda)]

    assert [p for p in paragrafos if "--" in p] == []
    assert [t for t in textos_da_meta if "--" in t] == []
    assert any(" — " in p for p in paragrafos)


# --------------------------------------------------------------------------
# Aba Análises do professor


def test_o_filtro_de_materia_do_professor_mostra_rotulo_e_envia_chave(client, sem_rede_supabase, monkeypatch):
    aluno = {"id": "a1", "nome": "Ana Ribeiro", "ano_escolar": "1º EM", "periodo": "Manhã"}
    log = {"aluno_id": "a1", "escola_id": ESCOLA_ID, "materia": "Matematica", "modo": "oraculo-flask",
           "resultado": "Acertou", "pergunta_texto": "P", "data_hora": "2026-09-29T10:00:00+00:00"}
    monkeypatch.setattr(professor_fla, "buscar_alunos", lambda *_a, **_k: [dict(aluno)])
    monkeypatch.setattr(professor_fla, "buscar_logs", lambda *_a, **_k: [dict(log)])
    monkeypatch.setattr(professor_fla, "buscar_resumo_turma", lambda *_a, **_k: [])
    monkeypatch.setattr(professor_fla, "listar_rpg_configs", lambda *_a, **_k: [])
    with client.session_transaction() as sess:
        sess["usuario_role"] = "professor"
        sess["escola_id"] = ESCOLA_ID
        sess["escola_nome"] = "Escola"
        carimbar_sessao(sess)

    html = client.get("/professor/?aba=analises&aluno_id=a1&materia=Matematica").get_data(as_text=True)

    # O value volta para a rota e filtra os logs: continua chave.
    assert '<option value="Matematica" selected>Matemática</option>' in html
    assert "Desempenho: Ana Ribeiro - Matemática" in html
