from __future__ import annotations

import importlib.machinery
import os
import sys
import uuid

import pytest


class _SecretsDoStreamlitSemArquivo:
    """Nenhum teste lê o .streamlit/secrets.toml da máquina.

    Visto em 13/09/2026, depois de travar o .env: a suíte inteira ainda
    terminava com SUPABASE_URL, a service_role e as chaves de IA de VERDADE no
    ambiente. Quando um teste importa o streamlit (tests/test_login_streamlit.py
    importa), core/runtime_context.py::ler_segredo passa a consultar st.secrets
    para toda variável que o ambiente não tem -- e o Streamlit, ao ler o
    secrets.toml, copia CADA chave dele para os.environ, por cima dos valores
    de mentira daqui de baixo (Secrets._maybe_set_environment_variable).

    Não dá para desligar por configuração (a opção secrets.files não aceita
    variável de ambiente) nem importar o streamlit aqui (get_runtime() passaria
    a devolvê-lo para a suíte toda). Então este gancho age só no import de
    streamlit.runtime.secrets, venha ele de onde vier: o leitor de arquivo
    passa a não achar nada, e st.secrets fica vazio como num Streamlit sem
    secrets configurado. Os testes de st.secrets usam um streamlit falso e não
    passam por aqui. Quem cobra: tests/test_testes_isolados_da_producao.py.
    """

    NOME = "streamlit.runtime.secrets"

    @staticmethod
    def travar(modulo) -> None:
        modulo.Secrets._parse_file_path = lambda self, caminho: ({}, False)

    def find_spec(self, nome, caminho=None, alvo=None):
        if nome != self.NOME:
            return None
        spec = importlib.machinery.PathFinder.find_spec(nome, caminho)
        if spec is None or spec.loader is None:
            return spec
        executar_original = spec.loader.exec_module

        def executar(modulo):
            executar_original(modulo)
            self.travar(modulo)

        spec.loader.exec_module = executar
        return spec


if _SecretsDoStreamlitSemArquivo.NOME in sys.modules:
    _SecretsDoStreamlitSemArquivo.travar(sys.modules[_SecretsDoStreamlitSemArquivo.NOME])
sys.meta_path.insert(0, _SecretsDoStreamlitSemArquivo())


os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key-for-unit-tests-only")
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests-only")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key-for-unit-tests-only")
os.environ.setdefault("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key-for-unit-tests-only")


@pytest.fixture
def client():
    # MELHORIA: fixture compartilhada pros testes de integracao (E2E-lite)
    # que dirigem o Flask de verdade via app.test_client() em vez de so
    # chamar funcoes Python direto ou ler templates como texto.
    from flask_app import app as flask_application

    flask_application.config["TESTING"] = True
    # MELHORIA: CSRFProtect exige um token valido em todo POST agora (ver
    # flask_app.py) -- os testes chamam client.post(url, data={...}) direto,
    # sem ter renderizado nenhum template pra extrair o token, entao
    # precisam desabilitar a checagem explicitamente (recomendacao oficial
    # do Flask-WTF para testes).
    flask_application.config["WTF_CSRF_ENABLED"] = False
    with flask_application.test_client() as test_client:
        yield test_client


class _TabelaFalsa:
    def __init__(self):
        self.linhas: list[dict] = []


class _SupabaseQueryFalsa:
    """Imita o suficiente de repositories/supabase_client.py::_SupabaseQuery
    pra rodar select/insert/upsert/update/delete em memoria, sem rede — o
    bastante pra um fluxo completo (salvar estado, ler de volta, apagar)
    funcionar de ponta a ponta num teste de integracao."""

    def __init__(self, tabela: _TabelaFalsa):
        self._tabela = tabela
        self._operacao = "select"
        self._payload = None
        self._on_conflict = None
        self._filtros: list[tuple] = []
        self._limite: int | None = None

    def select(self, *args, **kwargs):
        self._operacao = "select"
        return self

    def insert(self, payload):
        self._operacao = "insert"
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict: str | None = None):
        self._operacao = "upsert"
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def update(self, payload):
        self._operacao = "update"
        self._payload = payload
        return self

    def delete(self):
        self._operacao = "delete"
        return self

    def eq(self, campo, valor):
        self._filtros.append((campo, "eq", valor))
        return self

    def lt(self, campo, valor):
        self._filtros.append((campo, "lt", valor))
        return self

    def gte(self, campo, valor):
        self._filtros.append((campo, "gte", valor))
        return self

    def like(self, campo, padrao):
        self._filtros.append((campo, "like", padrao))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, total):
        self._limite = total
        return self

    def _combina(self, linha: dict) -> bool:
        for campo, operador, valor in self._filtros:
            atual = linha.get(campo)
            if operador == "eq" and str(atual) != str(valor):
                return False
            if operador == "lt" and not (atual is not None and atual < valor):
                return False
            if operador == "gte" and not (atual is not None and str(atual) >= str(valor)):
                return False
            if operador == "like":
                import re

                regex = "^" + re.escape(valor).replace(r"\*", ".*") + "$"
                if not re.match(regex, str(atual)):
                    return False
        return True

    def execute(self):
        from types import SimpleNamespace

        linhas = self._tabela.linhas

        if self._operacao == "select":
            resultado = [dict(linha) for linha in linhas if self._combina(linha)]
            if self._limite is not None:
                resultado = resultado[: self._limite]
            return SimpleNamespace(data=resultado)

        if self._operacao in ("insert", "upsert"):
            itens = self._payload if isinstance(self._payload, list) else [self._payload]
            colunas_conflito = [c.strip() for c in (self._on_conflict or "").split(",") if c.strip()]
            devolvidos = []
            for item in itens:
                existente = None
                if self._operacao == "upsert" and colunas_conflito:
                    existente = next(
                        (
                            linha
                            for linha in linhas
                            if all(linha.get(coluna) == item.get(coluna) for coluna in colunas_conflito)
                        ),
                        None,
                    )
                if existente is not None:
                    existente.update(item)
                    devolvidos.append(dict(existente))
                else:
                    nova = dict(item)
                    nova.setdefault("id", str(uuid.uuid4()))
                    linhas.append(nova)
                    devolvidos.append(dict(nova))
            return SimpleNamespace(data=devolvidos)

        if self._operacao == "update":
            afetadas = [linha for linha in linhas if self._combina(linha)]
            for linha in afetadas:
                linha.update(self._payload)
            return SimpleNamespace(data=[dict(linha) for linha in afetadas])

        if self._operacao == "delete":
            removidas = [linha for linha in linhas if self._combina(linha)]
            linhas[:] = [linha for linha in linhas if not self._combina(linha)]
            return SimpleNamespace(data=removidas)

        return SimpleNamespace(data=[])


class _SupabaseFalso:
    def __init__(self):
        self._tabelas: dict[str, _TabelaFalsa] = {}

    def table(self, nome, *args, **kwargs):
        return _SupabaseQueryFalsa(self._tabelas.setdefault(nome, _TabelaFalsa()))


@pytest.fixture
def sem_rede_supabase(monkeypatch):
    # MELHORIA: repositories/*.py fazem "from repositories.supabase_client
    # import supabase" (import por valor) — trocar o atributo em
    # supabase_client depois que os repos ja importaram nao afeta o nome
    # que cada repo guardou na propria namespace. Por isso o patch precisa
    # ser feito em cada modulo de repositorio individualmente. Usado pelos
    # testes de integracao (E2E-lite) pra nunca bater de verdade no
    # Supabase — o "banco" vira so um dict em memoria, valido apenas
    # durante o teste, mas suporta select/insert/upsert/update/delete de
    # verdade (o suficiente pra testar um fluxo de "salvar estado, reler na
    # proxima request" de ponta a ponta).
    falso = _SupabaseFalso()
    for modulo in (
        "repositories.aluno_repo",
        "repositories.cache_repo",
        "repositories.database_repo",
        "repositories.escola_repo",
        "repositories.log_repo",
        "repositories.meta_repo",
        "repositories.rpg_config_repo",
        "repositories.usuario_repo",
    ):
        monkeypatch.setattr(f"{modulo}.supabase", falso)
    return falso
