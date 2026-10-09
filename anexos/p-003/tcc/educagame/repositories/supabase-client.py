from __future__ import annotations

import base64
import hashlib
import os
import json
import sys
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from core.runtime_context import get_runtime, ler_segredo as _get_secret

runtime = get_runtime()

# MELHORIA: um 504 do gateway do Supabase virava falha na hora. Visto em
# 13/09/2026, confirmado no painel do Supabase: cinco "Gateway Timeout" num
# dia, em requisicoes minimas (GET escolas, POST estados_sessao) -- a tela de
# login ficou sem escolas por um instante, e a gravacao do historico do
# Laboratorio se perdeu. Se fosse a do desafio, /laboratorio/responder
# voltaria sem resultado e a resposta do aluno sumiria sem aviso.
#
# 502/503/504 sao do gateway, e passam em segundos: vale UMA segunda
# tentativa. Timeout do nosso lado (15 s) nao repete -- dobraria a espera do
# aluno sem motivo para dar certo.
_STATUS_TRANSITORIOS = {502, 503, 504}
_ESPERA_ANTES_DE_REPETIR = 0.8


def _pode_repetir(query: "_SupabaseQuery") -> bool:
    """So o que da o mesmo resultado se chegar DUAS vezes ao banco.

    O 504 nao diz se o banco gravou: o gateway pode ter desistido depois. GET,
    PATCH (grava valores, nao incrementa), DELETE e upsert terminam iguais.
    INSERT nao: repetir um log_pedagogico duplicaria a linha -- e o gatilho
    trg_atualizar_pontos somaria os pontos da resposta duas vezes.
    """
    if query._metodo in {"GET", "PATCH", "DELETE"}:
        return True
    return query._metodo == "POST" and "resolution=merge-duplicates" in query._prefer

try:
    from dotenv import load_dotenv

    # MELHORIA: com override=True, o .env da maquina passava POR CIMA do
    # endereco de mentira que tests/conftest.py define -- e a suite inteira
    # rodava contra o Supabase de PRODUCAO. Visto em 13/09/2026: seis linhas
    # em estados_sessao com exatamente os dados de um teste do Laboratorio,
    # gravadas nos horarios em que a suite rodou. So 5 dos 119 arquivos de
    # teste usam o banco falso (sem_rede_supabase); os outros liam e gravavam
    # no banco dos alunos.
    #
    # Sob o pytest o .env nao e lido: vale o que o conftest pos no ambiente.
    # Fora dele (Render, scripts, Streamlit) nada muda.
    if "pytest" not in sys.modules:
        load_dotenv(override=True)
except Exception:
    pass


# _get_secret mora em core/runtime_context.py (ler_segredo): a mesma leitura
# existia aqui e em services/ia/providers.py, identica. O nome local e
# mantido porque tests/test_env_example.py e scripts/gerar_env_para_secret_file.py
# varrem o codigo procurando _get_secret(...) para saber quais variaveis
# o projeto le.


class SupabaseNaoConfigurado(RuntimeError):
    """Sem SUPABASE_URL ou sem chave: nenhuma consulta chega a sair."""


class ErroDoSupabase(RuntimeError):
    """Resposta de erro do PostgREST, com o que ela diz separado em campos.

    MELHORIA: o erro era um RuntimeError so com texto, e quem precisava saber
    POR QUE a gravacao falhou tinha de procurar palavras na mensagem
    (st/ui/admin_st.py procura "unique"). O texto continua o mesmo -- ha
    teste que confere o comeco dele --, e agora o status HTTP e o codigo do
    Postgres tambem ficam em atributos.
    """

    def __init__(self, status: int, detalhe: str):
        super().__init__(f"Supabase REST erro {status}: {detalhe}")
        self.status = status
        try:
            corpo = json.loads(detalhe)
        except ValueError:
            corpo = None
        if not isinstance(corpo, dict):
            corpo = {}
        self.codigo = str(corpo.get("code") or "")
        self.mensagem = str(corpo.get("message") or "")

    def violou_unicidade(self, restricao: str) -> bool:
        """Valor repetido na restricao UNIQUE com esse nome.

        O PostgREST responde 409 com o codigo 23505 do Postgres e o nome da
        restricao entre aspas na mensagem:
        duplicate key value violates unique constraint "unique_ra_por_escola"
        """
        return self.codigo == "23505" and f'"{restricao}"' in self.mensagem


def falha_de_conexao(erro: BaseException) -> bool:
    """O banco nao chegou a avaliar o pedido -- ou nao se sabe se avaliou.

    OSError cobre o que o urlopen levanta sem resposta nenhuma: nome que nao
    resolve, conexao recusada, os 15 s de prazo estourados (URLError e
    TimeoutError descendem dele). 502/503/504 vem do gateway, e nao do banco
    (ver _STATUS_TRANSITORIOS). Supabase sem configuracao entra junto: para
    quem esta na tela e o mesmo "o banco nao respondeu".
    """
    if isinstance(erro, (SupabaseNaoConfigurado, OSError)):
        return True
    return isinstance(erro, ErroDoSupabase) and erro.status in _STATUS_TRANSITORIOS


class _SupabaseIndisponivel:
    def table(self, *_args, **_kwargs):
        raise SupabaseNaoConfigurado("Supabase indisponivel ou nao configurado.")


class _SupabaseQuery:
    def __init__(self, client: "_SupabaseRestClient", tabela: str):
        self._client = client
        self._tabela = tabela
        self._metodo = "GET"
        self._params: list[tuple[str, str]] = []
        self._payload = None
        self._prefer = "return=representation"

    def select(self, colunas: str = "*"):
        self._metodo = "GET"
        self._params.append(("select", colunas))
        return self

    def insert(self, payload):
        self._metodo = "POST"
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict: str | None = None):
        self._metodo = "POST"
        self._payload = payload
        self._prefer = "resolution=merge-duplicates,return=representation"
        if on_conflict:
            self._params.append(("on_conflict", on_conflict))
        return self

    def update(self, payload):
        self._metodo = "PATCH"
        self._payload = payload
        return self

    def delete(self):
        self._metodo = "DELETE"
        return self

    def eq(self, campo: str, valor):
        self._params.append((campo, f"eq.{valor}"))
        return self

    def lt(self, campo: str, valor):
        self._params.append((campo, f"lt.{valor}"))
        return self

    def gte(self, campo: str, valor):
        self._params.append((campo, f"gte.{valor}"))
        return self

    def like(self, campo: str, padrao: str):
        self._params.append((campo, f"like.{padrao}"))
        return self

    def order(self, campo: str, desc: bool = False):
        direcao = "desc" if desc else "asc"
        self._params.append(("order", f"{campo}.{direcao}"))
        return self

    def limit(self, total: int):
        self._params.append(("limit", str(total)))
        return self

    def execute(self):
        return self._client.execute(self)


class _SupabaseRestClient:
    def __init__(self, url: str, key: str):
        self._url = url.rstrip("/")
        self._key = key

    def table(self, tabela: str):
        return _SupabaseQuery(self, tabela)

    def execute(self, query: _SupabaseQuery):
        endpoint = f"{self._url}/rest/v1/{quote(query._tabela)}"
        if query._params:
            endpoint = f"{endpoint}?{urlencode(query._params)}"
        body = None
        if query._payload is not None:
            body = json.dumps(query._payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": query._prefer,
        }
        request = Request(endpoint, data=body, headers=headers, method=query._metodo)
        for tentativa in (1, 2):
            try:
                with urlopen(request, timeout=15) as response:
                    raw = response.read().decode("utf-8")
                break
            except HTTPError as exc:
                detalhe = exc.read().decode("utf-8", errors="ignore")
                if tentativa == 1 and exc.code in _STATUS_TRANSITORIOS and _pode_repetir(query):
                    # So o que identifica a chamada: nem chave nem corpo no log.
                    print(f"[Supabase] {exc.code} em {query._metodo} {query._tabela}; tentando de novo")
                    time.sleep(_ESPERA_ANTES_DE_REPETIR)
                    continue
                raise ErroDoSupabase(exc.code, detalhe) from exc
        data = json.loads(raw) if raw else []
        return SimpleNamespace(data=data)


SUPABASE_URL = _get_secret("SUPABASE_URL")
SUPABASE_KEY = (
    _get_secret("SUPABASE_SERVICE_ROLE_KEY")
    or _get_secret("SUPABASE_SERVICE_KEY")
    or _get_secret("SUPABASE_KEY")
)

if SUPABASE_URL and SUPABASE_KEY:
    supabase = _SupabaseRestClient(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = _SupabaseIndisponivel()


def diagnostico_supabase_seguro() -> dict[str, Any]:
    # MELHORIA: portado da branch StreamLit — home_st.py mostra isso na tela
    # de selecao de escola quando listar_escolas() falha, pra dar alguma
    # visibilidade de configuracao sem expor a chave. Adaptado pro cliente
    # REST proprio desta branch (SUPABASE_URL/SUPABASE_KEY simples, sem o
    # rastreio de "fonte" env vs st.secrets que a versao antiga tinha).
    projeto = ""
    if SUPABASE_URL:
        projeto = SUPABASE_URL.replace("https://", "").split(".")[0]
    key = SUPABASE_KEY or ""
    formato = "ausente"
    jwt_role = ""
    jwt_iss = ""
    jwt_ref = ""
    if key.startswith("eyJ") and key.count(".") == 2:
        formato = "jwt"
        try:
            payload_b64 = key.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8"))
            jwt_role = str(payload.get("role") or "")
            jwt_iss = str(payload.get("iss") or "")
            jwt_ref = str(payload.get("ref") or "")
        except Exception:
            jwt_role = "nao foi possivel ler payload"
    elif key.startswith("sb_secret_"):
        formato = "sb_secret"
    elif key.startswith("sb_publishable_"):
        formato = "sb_publishable"
    elif key:
        formato = "desconhecido"
    return {
        "supabase_url_configurada": bool(SUPABASE_URL),
        "projeto_ref": projeto or "ausente",
        "supabase_key_configurada": bool(SUPABASE_KEY),
        "supabase_key_tamanho": len(key),
        "supabase_key_sha256_8": hashlib.sha256(key.encode("utf-8")).hexdigest()[:8] if key else "",
        "supabase_key_formato": formato,
        "jwt_role": jwt_role,
        "jwt_iss": jwt_iss,
        "jwt_ref": jwt_ref,
    }
