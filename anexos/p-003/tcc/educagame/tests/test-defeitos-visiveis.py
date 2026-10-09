"""Defeitos que o aluno via na tela, medidos em 15/09/2026.

Cada um foi reproduzido pela função real antes de corrigir: a pontuação que o
ENEM quebrava, os títulos com o nome interno do banco, o "Banco autoral
offline" no cabeçalho, os percentuais "20.0%", o plural "1 acertos", palavras
sem acento e o item repetido na narrativa do RPG, e "forca" sem acento no
Laboratório. Onde a correção mexe numa regra que também acertava, o teste vem
em par: o defeito some e o que funcionava continua.
"""
from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

import pytest
from jinja2 import Environment

import services.banks.fundamental as fundamental
import services.banks.laboratorio as lab
import services.enem_service as enem
import services.rpg_service as rpg_service
from core.text_cleanup import aplicar_acentos_pt
from services.banks.em import listar_questoes_em

TEMPLATES = Path(__file__).resolve().parent.parent / "web" / "templates"


def calado(funcao, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return funcao(*args, **kwargs)


def linha_do_template(arquivo, marcador):
    texto = (TEMPLATES / arquivo).read_text(encoding="utf-8")
    return next(linha.strip() for linha in texto.splitlines() if marcador in linha)


def sem_tags(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


# --------------------------------------------------------------------------
# ENEM: a limpeza de texto
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "texto",
    [
        "Leia o trecho: 'A língua é viva.' Depois responda.",
        "O cliente pediu picanha.' O garçom anotou.",
        "Gotas por dia: 86.400 gotas.",
        "As aulas começavam às 8:30 a.m. em ponto.",
        "Os descendentes saem em proporção 1:1.",
        "Consulte www.gov.br antes.",
        "Ele disse (ver nota.) e saiu.",
        "Ela respondeu “sim,” e saiu.",
        "Ele gritou: 'Pare!' e correu.",
    ],
)
def test_a_limpeza_do_enem_nao_quebra_aspa_numero_nem_endereco(texto):
    assert enem._corrigir_texto_enem(texto) == texto


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Fim da frase.Depois veio outra.", "Fim da frase. Depois veio outra."),
        ("Primeiro,segundo e terceiro.", "Primeiro, segundo e terceiro."),
        ("Leia o trecho:a seguir.", "Leia o trecho: a seguir."),
        ("Sim!Agora responda.", "Sim! Agora responda."),
        ("Uma lista , com espaço antes.", "Uma lista, com espaço antes."),
    ],
)
def test_a_limpeza_do_enem_continua_separando_a_palavra_seguinte(texto, esperado):
    """O par: a limpeza existe para isto, e continua fazendo."""
    assert enem._corrigir_texto_enem(texto) == esperado


def test_o_cabecalho_do_enem_nao_mostra_o_nome_do_banco():
    for area in enem.AREAS_ENEM:
        for questao in calado(enem._fallback_autoral_por_area, area)[:5]:
            assert "offline" not in questao["matriz_enem"].lower()
            assert questao["matriz_enem"].startswith("Questão autoral")


# --------------------------------------------------------------------------
# títulos das questões do banco
# --------------------------------------------------------------------------

ROTULO = re.compile(r"^(?:Or[aá]culo|Banco|Desafio de )", re.IGNORECASE)


@pytest.mark.parametrize("materia", ["Biologia", "Fisica", "Arte", "Sociologia"])
def test_o_titulo_do_banco_do_ensino_medio_e_o_tema_no_cenario(materia):
    questoes = calado(listar_questoes_em, materia)
    rotulados = [q["enigma"] for q in questoes if ROTULO.match(aplicar_acentos_pt(q["enigma"]))]

    assert rotulados == []
    primeira = questoes[0]
    assert primeira["enigma"].startswith(primeira["objeto_conhecimento"][:1].upper())
    assert " em " in primeira["enigma"]


def test_os_ramos_sem_conteudo_especifico_tambem_tem_titulo_sem_rotulo(monkeypatch):
    """Hoje as 24.000 questões do EM vêm do conteúdo específico, e os ramos
    "teórico" e "realista" não aparecem -- mas voltam no dia em que um tema
    novo entrar sem conteúdo. Sem conteúdo específico, os dois são forçados."""
    import services.banks.em as em

    monkeypatch.setattr(em, "BANCO_ESPECIFICO_EM", {})
    materia_teorica = sorted(em.EXATAS_TEORICAS)[0]
    materia_realista = "Sociologia"
    assert materia_realista not in em.EXATAS_TEORICAS

    for materia in (materia_teorica, materia_realista):
        titulos = {q["enigma"] for q in em._gerar_banco_materia(materia)}
        assert [t for t in titulos if ROTULO.match(aplicar_acentos_pt(t))] == [], materia


def test_o_titulo_do_fundamental_nao_e_o_mesmo_desafio_generico():
    questao = calado(fundamental.gerar_questao_offline_ef, "Matematica", "", "Medio")

    assert not questao["enigma"].startswith("Desafio de ")
    assert " em " in questao["enigma"]


def test_o_titulo_do_laboratorio_nao_diz_banco_de_formulas():
    questoes = lab.listar_questoes_laboratorio("Matematica", "EM")

    assert [q["enigma"] for q in questoes if q["enigma"].lower().startswith("banco")] == []
    assert questoes[0]["enigma"][:1].isupper()


# --------------------------------------------------------------------------
# percentuais e plural nas telas
# --------------------------------------------------------------------------

CONTEXTO = {
    "simulado": {"idx": 0, "total": 5},
    "estado": {"idx": 0, "bosses": [1, 2, 3, 4, 5], "atual": 0, "salas": [1, 2, 3], "fase": 1},
    "fases_totais": 15,
    "treino": {"atual": 1, "acertos": 1, "total": 3},
}


def test_os_percentuais_de_progresso_saem_inteiros():
    """|round devolve float no Jinja: a tela mostrava "20.0% do simulado"."""
    ambiente = Environment()
    expressoes = {}
    for arquivo in sorted(TEMPLATES.glob("*.html")):
        for achado in re.finditer(r"\{%\s*set\s+(progresso|pct)\s*=\s*(.+?)\s*%\}", arquivo.read_text(encoding="utf-8")):
            expressoes[f"{arquivo.name}:{achado.group(1)}"] = achado.group(2)

    assert len(expressoes) >= 6
    for nome, expressao in expressoes.items():
        valor = ambiente.from_string("{{ " + expressao + " }}").render(**CONTEXTO)
        assert re.fullmatch(r"\d+", valor), f"{nome} mostra {valor}"


@pytest.mark.parametrize("acertos, erros, esperado", [(1, 1, "1 acerto · 1 erro"), (2, 0, "2 acertos · 0 erros")])
def test_o_placar_do_treino_concorda_em_numero(acertos, erros, esperado):
    linha = linha_do_template("treino.html", 'treino.get("erros", 0)')

    assert sem_tags(Environment().from_string(linha).render(treino={"acertos": acertos, "erros": erros})) == esperado


@pytest.mark.parametrize(
    "acertos, total, esperado",
    [(1, 1, "1 sala aberta em 1 tentativa"), (2, 3, "2 salas abertas em 3 tentativas")],
)
def test_o_resumo_do_escape_concorda_em_numero(acertos, total, esperado):
    linha = linha_do_template("escape_room.html", "resumo.total }}")
    texto = sem_tags(Environment().from_string(linha).render(resumo={"acertos": acertos, "total": total, "percentual": 50}))

    assert texto.startswith(esperado)


def test_o_perfil_concorda_em_numero():
    linha = linha_do_template("perfil.html", "materia.acertos }}")

    assert sem_tags(Environment().from_string(linha).render(materia={"acertos": 1})) == "1 acerto"
    assert sem_tags(Environment().from_string(linha).render(materia={"acertos": 4})) == "4 acertos"


# --------------------------------------------------------------------------
# RPG
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bruto, esperado",
    [("a acao 'x'", "a ação 'x'"), ("de forma visivel", "de forma visível"), ("um duelo academico", "um duelo acadêmico")],
)
def test_palavras_da_narrativa_do_rpg_ganham_acento(bruto, esperado):
    assert aplicar_acentos_pt(bruto) == esperado


def test_o_portal_aceita_titulo_que_comeca_com_artigo():
    cena = calado(rpg_service.iniciar_aventura, {"materia": "Matematica", "titulo": "O Enigma da Cripta"})

    assert "portal de O " not in cena["narracao"]
    assert "“O Enigma da Cripta”" in cena["narracao"]


MEMORIA = {
    "recurso": "Caderno de campo", "ultima_rota": "Arquivo das Runas", "foco": "observacao",
    "reliquia": "", "antagonista": "", "ameaca": "", "cicatriz": "", "segredo": "a pista se fecha",
}


@pytest.mark.parametrize("impacto", ["Conhecimento", "Estrategia", "Coragem", "Cooperacao"])
def test_o_recurso_da_rota_nao_se_repete_na_mesma_frase(impacto):
    modelo = {"rota": "Torre do Debate", "recurso": "Caderno de campo", "impacto": impacto, "texto": "x"}

    texto, consequencia = rpg_service._texto_opcao_narrativa(modelo, 3, "Matematica", MEMORIA)

    assert not re.search(r"Caderno de campo.{0,12}Caderno de campo", f"{texto} {consequencia}")


def test_recursos_diferentes_continuam_os_dois_na_frase():
    modelo = {"rota": "Torre do Debate", "recurso": "Escudo runico", "impacto": "Estrategia", "texto": "x"}

    texto, _ = rpg_service._texto_opcao_narrativa(modelo, 3, "Matematica", MEMORIA)

    assert "Escudo runico" in texto and "Caderno de campo" in texto


def test_rotulos_do_rpg_com_acento():
    assert "Desafio academico" not in (TEMPLATES / "rpg.html").read_text(encoding="utf-8")
    linha = linha_do_template("rpg.html", "| risco")
    assert "risco médio" in Environment().from_string(linha).render(opcao={"rota": "Torre", "risco": "medio"})
    assert "risco alto" in Environment().from_string(linha).render(opcao={"rota": "Torre", "risco": "alto"})

    modelo = {"rota": "Torre do Debate", "recurso": "Caderno de campo", "impacto": "Cooperacao", "risco": "medio"}
    detalhes = rpg_service._detalhes_opcao_narrativa(modelo, 2, "Matematica", MEMORIA, "Texto.", "c")
    assert "força coletiva" in detalhes["recompensa_narrativa"]


# --------------------------------------------------------------------------
# Laboratório: "forca"
# --------------------------------------------------------------------------

def test_o_laboratorio_escreve_forca_com_cedilha():
    """"forca" não entra no dicionário (é também a da execução); a correção é na fonte."""
    for serie, materias in (("EM", lab.MATERIAS_LAB_OFFLINE), ("EF", lab.MATERIAS_LAB_EF_OFFLINE)):
        for materia in materias:
            for questao in lab.listar_questoes_laboratorio(materia, serie):
                for campo in ("legenda_variaveis", "pergunta"):
                    texto = aplicar_acentos_pt(questao[campo])
                    assert not re.search(r"\bforca\b", texto, re.IGNORECASE), texto
