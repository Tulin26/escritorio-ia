from __future__ import annotations

import re
import unicodedata

import pandas as pd

from core.config import materia_base as _materia_base_de_texto


# MELHORIA: "adm" era a setima aba desta lista, e a rota a escondia de quem
# nao fosse desenvolvedor. Isso punha uma area de DESENVOLVEDOR dentro da area
# de outro papel: quem entrava como desenvolvedor caia no painel de professor
# e tinha de procurar o ADM entre as abas de dar aula.
#
# Agora sao duas listas. O desenvolvedor escolhe primeiro a AREA (Professor ou
# ADM), e so entao ve as abas dela. Mesma separacao do Streamlit, onde o ADM
# virou pagina propria (st/ui/home_st.py::PAGINAS_SO_DE_DESENVOLVEDOR).
ABAS_GESTAO = [
    {"valor": "analises", "label": "Análises"},
    {"valor": "rpg", "label": "RPG"},
    {"valor": "matricula", "label": "Matrícula"},
    {"valor": "ranking", "label": "Ranking"},
    {"valor": "resumo", "label": "Resumo da Turma"},
    {"valor": "metas", "label": "Metas e foco"},
    {"valor": "professores", "label": "Professores"},
    {"valor": "configuracoes", "label": "Configurações"},
]

ABA_ADM = {"valor": "adm", "label": "ADM"}

# Mantida porque a rota ainda precisa validar "?aba=adm" contra o conjunto de
# abas que existem. Quem monta o menu usa ABAS_GESTAO.
ABAS = [*ABAS_GESTAO, ABA_ADM]

MODOS_PROFESSOR = [
    {"valor": "todos", "label": "Todos os modos"},
    {"valor": "oraculo", "label": "Oráculo"},
    {"valor": "treino", "label": "Jogar/Treinar"},
    {"valor": "enem", "label": "ENEM"},
    {"valor": "boss_rush", "label": "Boss Rush"},
    {"valor": "escape_room", "label": "Escape Room"},
    {"valor": "rpg", "label": "RPG"},
    {"valor": "laboratorio", "label": "Laboratório de Exatas"},
]

SERIES_GERAIS = ["6º Ano", "7º Ano", "8º Ano", "9º Ano", "1º Ano EM", "2º Ano EM", "3º Ano EM"]
MATERIAS_RPG = [
    "Matemática",
    "Física",
    "Química",
    "Biologia",
    "Português",
    "História",
    "Geografia",
    "Inglês",
    "Arte",
    "Educação Física",
    "Filosofia",
    "Sociologia",
    "Ensino Religioso",
    "Ciências",
]


def normalizar_modo_log(log: dict) -> str:
    modo = str(log.get("modo") or "").lower()
    materia = str(log.get("materia") or "").upper()
    if "boss_rush" in modo:
        return "boss_rush"
    if "escape_room" in modo:
        return "escape_room"
    if "rpg" in modo or materia.startswith("RPG-"):
        return "rpg"
    if "laboratorio" in modo or materia.startswith("LAB-"):
        return "laboratorio"
    if "treino" in modo:
        return "treino"
    if "enem" in modo or materia.startswith("ENEM-"):
        return "enem"
    if "oraculo" in modo or not modo:
        return "oraculo"
    return modo


def materia_base(log: dict) -> str:
    return _materia_base_de_texto(log.get("materia") or "Geral")


def gerar_slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def aluno_padrao(alunos: list[dict], aluno_sessao: str = "") -> str:
    aluno_sessao = str(aluno_sessao or "")
    if aluno_sessao and any(str(aluno.get("id")) == aluno_sessao for aluno in alunos):
        return aluno_sessao
    return str(alunos[0].get("id")) if alunos else ""


def filtrar_logs(logs: list[dict], aluno_id: str, modo: str, materia: str) -> list[dict]:
    filtrados = [log for log in logs if str(log.get("aluno_id")) == str(aluno_id)]
    if modo and modo != "todos":
        filtrados = [log for log in filtrados if normalizar_modo_log(log) == modo]
    if materia and materia != "todas":
        filtrados = [log for log in filtrados if materia_base(log) == materia]
    return filtrados


def materias_disponiveis(logs_aluno: list[dict]) -> list[str]:
    return sorted({materia_base(log) for log in logs_aluno if materia_base(log).strip()})


def metricas_logs(logs: list[dict]) -> dict:
    total = len(logs)
    acertos = sum(1 for log in logs if log.get("resultado") == "Acertou")
    erros = total - acertos
    percentual = int(acertos / total * 100) if total else 0
    return {"total": total, "acertos": acertos, "erros": erros, "percentual": percentual}


def ranking_alunos(alunos: list[dict], logs: list[dict], serie: str) -> list[dict]:
    dados = []
    for aluno in alunos:
        if serie != "Todas as séries" and aluno.get("ano_escolar") != serie:
            continue
        logs_aluno = [log for log in logs if str(log.get("aluno_id")) == str(aluno.get("id"))]
        total = len(logs_aluno)
        acertos = sum(1 for log in logs_aluno if log.get("resultado") == "Acertou")
        dados.append(
            {
                "nome": aluno.get("nome", ""),
                "serie": aluno.get("ano_escolar", ""),
                "total": total,
                "acertos": acertos,
                "percentual": int(acertos / total * 100) if total else 0,
                "pontos": int(aluno.get("pontos_totais") or 0),
            }
        )
    dados.sort(key=lambda item: item["pontos"], reverse=True)
    return dados[:10]


def resumo_filtrado(resumo: list[dict], serie: str, periodo: str) -> list[dict]:
    return [
        item
        for item in resumo
        if (serie == "Todas" or item.get("ano_escolar") == serie)
        and (periodo == "Todos" or item.get("periodo") == periodo)
    ]


def metricas_turma(dados: list[dict]) -> dict:
    alunos = len(dados)
    questoes = sum(int(item.get("total_questoes") or 0) for item in dados)
    acertos = sum(int(item.get("acertos") or 0) for item in dados)
    tempos = [float(item.get("tempo_medio_resposta") or 0) for item in dados if float(item.get("tempo_medio_resposta") or 0) > 0]
    return {
        "alunos": alunos,
        "questoes": questoes,
        "media": int(acertos / questoes * 100) if questoes else 0,
        "tempo": round(sum(tempos) / len(tempos), 1) if tempos else 0,
    }


def df_logs_revisao(logs: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(logs)
    for coluna in [
        "resultado",
        "materia",
        "modo",
        "pergunta_texto",
        "resposta_aluno",
        "resposta_correta",
        "explicacao_ia",
        "tempo_resposta",
        "area_bncc",
        "competencia_bncc",
        "habilidade_bncc",
        "dificuldade",
        "matriz_enem",
    ]:
        if coluna not in df.columns:
            df[coluna] = ""
    return df


def nome_arquivo_revisao(nome: str, materia: str, modo: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", nome.strip() or "Aluno").strip("_")
    filtro = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{modo}_{materia}".strip()).strip("_")
    return f"Revisao_{base}_{filtro or 'recorte'}.pdf"
