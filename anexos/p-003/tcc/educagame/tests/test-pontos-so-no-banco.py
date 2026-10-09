"""Os pontos são somados só no banco, pela mesma tabela que a tela mostra.

Medido em 13/09/2026: cada resposta no Flask somava DUAS vezes -- o gatilho
trg_atualizar_pontos (+10 / -5) e o somar_pontos_aluno do app (por
dificuldade). A conta de teste tinha 510 pontos: 355 do app + 155 do gatilho.

O banco não roda aqui, então o que se prende é o CONTRATO entre as duas pontas:
os valores escritos no SQL e os do Python, que a tela usa para dizer "+30".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from web.routes.flask_helpers_fla import perda_pontuacao_por_dificuldade, pontuacao_por_dificuldade

RAIZ = Path(__file__).resolve().parents[1]
MIGRACAO = RAIZ / "supabase" / "migrations" / "20260913120000_pontos_por_dificuldade_no_banco.sql"


def _sql() -> str:
    return MIGRACAO.read_text(encoding="utf-8")


def _faixas_do_sql() -> list[tuple[int, int]]:
    """(ganho, perda) na ordem do if/elsif/else: difícil, fácil, médio."""
    return [(int(g), int(p)) for g, p in re.findall(r"ganho := (\d+); perda := (\d+);", _sql())]


def test_o_sql_tem_as_tres_faixas():
    assert len(_faixas_do_sql()) == 3


@pytest.mark.parametrize("posicao, dificuldade", [(0, "Dificil"), (1, "Facil"), (2, "Medio")])
def test_o_banco_soma_o_mesmo_que_a_tela_mostra(posicao, dificuldade):
    """Se alguém mudar um lado, a tela diria "+30" e o banco somaria outra coisa."""
    ganho, perda = _faixas_do_sql()[posicao]

    assert ganho == pontuacao_por_dificuldade(dificuldade)
    assert perda == perda_pontuacao_por_dificuldade(dificuldade)


def test_sem_dificuldade_vale_como_medio_nos_dois_lados():
    """Rota que não manda dificuldade grava NULL no log: o else do SQL."""
    ganho, perda = _faixas_do_sql()[2]

    assert (ganho, perda) == (pontuacao_por_dificuldade(""), perda_pontuacao_por_dificuldade(""))


def test_o_erro_desconta_e_o_total_nao_fica_negativo():
    sql = _sql()

    assert "greatest(0, coalesce(pontos_totais, 0) - perda)" in sql
    assert "coalesce(pontos_totais, 0) + ganho" in sql


def test_a_migracao_limpa_os_avisos_do_advisor():
    sql = _sql()

    assert "set search_path = public, pg_temp" in sql
    assert "drop function if exists public.atualizar_pontos();" in sql
    assert "drop function if exists public.atualizar_tempo_medio_aluno();" in sql
    # Sem os comentarios: o cabecalho EXPLICA que nao ha cascade, e a palavra
    # ali nao executa nada.
    so_comandos = re.sub(r"--[^\n]*", "", sql).lower()
    assert "cascade" not in so_comandos, "com cascade, apagaria gatilho em uso sem avisar"


def test_fica_um_gatilho_so():
    sql = _sql()

    assert "drop trigger if exists trg_pontos on public.logs_pedagogicos;" in sql
    assert sql.count("create trigger") == 1


def test_nenhum_codigo_volta_a_somar_pontos_no_app():
    """Somar no app de novo é recriar a contagem em dobro."""
    culpados = []
    for pasta in ("repositories", "services", "web", "st", "core"):
        for arquivo in (RAIZ / pasta).rglob("*.py"):
            texto = arquivo.read_text(encoding="utf-8", errors="replace")
            if re.search(r"\.update\(\s*\{\s*[\"']pontos_totais[\"']", texto):
                culpados.append(str(arquivo.relative_to(RAIZ)))

    assert culpados == []
