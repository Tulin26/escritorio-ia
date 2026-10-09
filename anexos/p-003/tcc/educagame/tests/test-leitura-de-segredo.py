"""Só existe um caminho para ler configuração, e ele não depende da ordem de import.

MELHORIA: a mesma leitura existia três vezes — `_get_secret` em
repositories/supabase_client.py, `_get_secret` em services/ia/providers.py e
`_lido` em core/diagnostico_config.py. Uma lia a chave do Supabase, outra as
chaves de IA, a terceira conferia as duas no boot.

Ninguém estava errado. O risco é divergirem: se uma passasse a olhar
`secrets` antes do ambiente e a outra não, metade do sistema ficaria sem a
chave e o log não diria nada — a falha que este projeto já teve duas vezes.

E havia um defeito latente nas duas primeiras: elas resolviam o runtime no
IMPORT (`runtime = get_runtime()` no topo do módulo). Sob o Streamlit isso é
uma corrida — se o módulo for importado antes de "streamlit" entrar em
sys.modules, a cópia guarda o contexto neutro para sempre e nunca enxerga
`st.secrets`, que é como o Streamlit Cloud entrega SUPABASE_URL e
SUPABASE_KEY.
"""

from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

from core.runtime_context import ler_segredo

RAIZ = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# a ordem: ambiente primeiro, secrets depois
# --------------------------------------------------------------------------


def test_variavel_de_ambiente_vence(monkeypatch):
    monkeypatch.setenv("EDUCAGAME_TESTE_SEGREDO", "do-ambiente")

    assert ler_segredo("EDUCAGAME_TESTE_SEGREDO") == "do-ambiente"


def test_cai_para_secrets_quando_nao_ha_ambiente(monkeypatch):
    monkeypatch.delenv("EDUCAGAME_TESTE_SEGREDO", raising=False)

    class _RuntimeFalso:
        class secrets:
            @staticmethod
            def get(nome, default=None):
                return "do-secrets" if nome == "EDUCAGAME_TESTE_SEGREDO" else default

    import core.runtime_context as rc

    monkeypatch.setattr(rc, "get_runtime", lambda: _RuntimeFalso)

    assert ler_segredo("EDUCAGAME_TESTE_SEGREDO") == "do-secrets"


def test_sem_ambiente_e_sem_secrets_devolve_none(monkeypatch):
    monkeypatch.delenv("EDUCAGAME_TESTE_SEGREDO", raising=False)

    assert ler_segredo("EDUCAGAME_TESTE_SEGREDO") is None


def test_secrets_que_explode_nao_derruba_a_leitura(monkeypatch):
    monkeypatch.delenv("EDUCAGAME_TESTE_SEGREDO", raising=False)

    class _RuntimeQuebrado:
        class secrets:
            @staticmethod
            def get(nome, default=None):
                raise RuntimeError("secrets.toml ausente")

    import core.runtime_context as rc

    monkeypatch.setattr(rc, "get_runtime", lambda: _RuntimeQuebrado)

    assert ler_segredo("EDUCAGAME_TESTE_SEGREDO") is None


# --------------------------------------------------------------------------
# a parte que motivou juntar: o runtime é resolvido na CHAMADA
# --------------------------------------------------------------------------


def test_o_runtime_e_resolvido_na_chamada_e_nao_no_import(monkeypatch):
    # Este é o defeito latente das cópias antigas. Se o runtime fosse preso
    # no import, trocar o contexto depois não teria efeito nenhum -- e sob o
    # Streamlit isso significa nunca enxergar st.secrets.
    monkeypatch.delenv("EDUCAGAME_TESTE_SEGREDO", raising=False)

    import core.runtime_context as rc

    assert ler_segredo("EDUCAGAME_TESTE_SEGREDO") is None

    class _RuntimeQueChegouDepois:
        class secrets:
            @staticmethod
            def get(nome, default=None):
                return "chegou-depois"

    monkeypatch.setattr(rc, "get_runtime", lambda: _RuntimeQueChegouDepois)

    assert ler_segredo("EDUCAGAME_TESTE_SEGREDO") == "chegou-depois", (
        "a leitura prendeu o runtime no import: sob o Streamlit isso e nunca "
        "ver st.secrets"
    )


# --------------------------------------------------------------------------
# uma implementação só
# --------------------------------------------------------------------------


def test_os_tres_leitores_usam_a_mesma_funcao():
    import core.diagnostico_config as diag
    import repositories.supabase_client as supa
    import services.ia.providers as prov

    assert supa._get_secret is ler_segredo
    assert prov._get_secret is ler_segredo
    # o diagnostico embrulha para devolver texto, mas le pelo mesmo caminho
    assert "ler_segredo" in io.open(diag.__file__, encoding="utf-8").read()


def test_existe_uma_definicao_so():
    ignorar = {"__pycache__", ".venv", "tests", "node_modules", ".claude"}  # .claude: worktrees
    definicoes = []
    for arquivo in sorted(RAIZ.rglob("*.py")):
        if set(arquivo.parts) & ignorar:
            continue
        try:
            arvore = ast.parse(io.open(arquivo, encoding="utf-8-sig", errors="ignore").read())
        except SyntaxError:
            continue
        for no in arvore.body:
            if isinstance(no, ast.FunctionDef) and no.name in ("_get_secret", "ler_segredo"):
                definicoes.append(f"{arquivo.relative_to(RAIZ).as_posix()}:{no.name}")

    assert definicoes == ["core/runtime_context.py:ler_segredo"], definicoes


# --------------------------------------------------------------------------
# a rede que varre os nomes de variável continua enxergando
# --------------------------------------------------------------------------


# O minimo do providers.py acompanha a cascata: eram 13 leituras com seis
# provedores; com Mistral, Cerebras e Hugging Face fora (08 e 09/10/2026),
# sao 8. A folga e para trocar uma leitura de lugar, nao para renomear.
@pytest.mark.parametrize(
    "arquivo, minimo",
    [("repositories/supabase_client.py", 4), ("services/ia/providers.py", 7)],
)
def test_as_chamadas_continuam_com_o_nome_que_o_scanner_procura(arquivo, minimo):
    # tests/test_env_example.py e scripts/gerar_env_para_secret_file.py varrem
    # o codigo atras de _get_secret(...) para descobrir quais variaveis o
    # projeto le. Renomear as chamadas faria essa rede parar de enxerga-las --
    # em silencio, que e o pior jeito de perder um verificador.
    texto = io.open(RAIZ / arquivo, encoding="utf-8").read()

    assert texto.count('_get_secret("') >= minimo
