import concurrent.futures
import json
import os
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from core.runtime_context import get_runtime, ler_segredo as _get_secret

runtime = get_runtime()

try:
    from dotenv import load_dotenv

    # MELHORIA: com override=True, o .env da maquina trocava as chaves de
    # mentira do tests/conftest.py pelas REAIS -- a suite podia chamar Groq,
    # Mistral e Gemini de verdade. Mesma falha de repositories/supabase_client.py
    # (13/09/2026). Sob o pytest o .env nao e lido; fora dele nada muda.
    if "pytest" not in sys.modules:
        load_dotenv(override=True, encoding="utf-8-sig")
except Exception:
    pass


# ====================== PRAZO RIGIDO POR CHAMADA ======================
# MELHORIA: alguns SDKs/HTTP clients nao garantem que o "timeout" passado a eles
# realmente corta a chamada no tempo combinado (ex: timeout de leitura e por
# pedaco de dado recebido, nao pelo tempo total da resposta; uma conexao com
# keep-alive pode "parecer viva" indefinidamente). Isso ja travou um worker do
# Gunicorn por mais de 60s numa chamada ao OpenRouter, que so foi encerrada a
# forca (SIGKILL) pelo proprio Gunicorn - virando 500 pro usuario.
# Este wrapper impoe um prazo de parede real e independente do SDK: a chamada
# roda numa thread separada e, se nao responder a tempo, devolvemos o controle
# imediatamente (a thread de fundo e abandonada e sera encerrada sozinha quando
# a conexao subjacente cair).
#
# MELHORIA: eram 4 vagas, pensadas para um processo que atendia um aluno por
# vez. Com varios alunos ao mesmo tempo (gunicorn.conf.py) e com a chamada que
# estoura o prazo seguindo viva ate a conexao cair, 4 vagas lotavam -- e a
# espera na FILA contava dentro do prazo, virando "timeout" de um provedor que
# nem tinha sido chamado. O dobro das threads do Gunicorn, com folga.
_executor_ia = concurrent.futures.ThreadPoolExecutor(max_workers=16, thread_name_prefix="ia-provider")


def _com_prazo_rigido(func, timeout: float):
    futuro = _executor_ia.submit(func)
    try:
        return futuro.result(timeout=max(0.5, float(timeout)))
    except concurrent.futures.TimeoutError as exc:
        raise TimeoutError(f"Prazo de {timeout:.1f}s excedido aguardando resposta") from exc


# ====================== CHAMADA DE IA ======================

_ultimo_erro_ia_processo = ""
_ultimo_provedor_ia_processo = ""
_gemini_quota_bloqueado_ate = 0.0
_gemini_motivo_bloqueio = ""


# MELHORIA: o ultimo erro e o ultimo provedor moravam em runtime.session_state
# -- que, no Flask, e UM dicionario para o processo inteiro. Com um aluno por
# vez isso passava; com varios ao mesmo tempo (gunicorn.conf.py), a rota de um
# aluno lia o provedor ou o aviso de "IA indisponivel" gerado para outro, entre
# a chamada e a leitura.
#
# Dentro de uma requisicao Flask o valor fica em flask.g, que e dela. A
# requisicao que NAO chamou a IA -- o painel do desenvolvedor, que mostra
# "ultimo provedor" como diagnostico geral -- le o ultimo do processo, que e o
# que ela sempre leu. Fora do Flask (Streamlit, scripts) nada muda.
#
# Os registros acontecem todos na thread da requisicao: _com_prazo_rigido so
# leva para a thread de fundo a chamada ao SDK, e o resultado e anotado depois
# que ela volta.


def _em_requisicao_flask() -> bool:
    try:
        from flask import has_request_context
    except ImportError:  # o Streamlit Cloud nao instala o Flask
        return False
    return has_request_context()


def _registrar_ultimo_erro_ia(mensagem: str = ""):
    global _ultimo_erro_ia_processo
    _ultimo_erro_ia_processo = mensagem or ""
    if _em_requisicao_flask():
        from flask import g

        g.ultimo_erro_ia = mensagem or ""
        return
    try:
        runtime.session_state["ultimo_erro_ia"] = mensagem or ""
    except Exception:
        pass


def obter_ultimo_erro_ia() -> str:
    if _em_requisicao_flask():
        from flask import g

        return str(getattr(g, "ultimo_erro_ia", _ultimo_erro_ia_processo))
    try:
        return str(runtime.session_state.get("ultimo_erro_ia", ""))
    except Exception:
        return _ultimo_erro_ia_processo


def _registrar_ultimo_provedor_ia(provedor: str = ""):
    global _ultimo_provedor_ia_processo
    _ultimo_provedor_ia_processo = provedor or ""
    if _em_requisicao_flask():
        from flask import g

        g.ultimo_provedor_ia = provedor or ""
        return
    try:
        runtime.session_state["ultimo_provedor_ia"] = provedor or ""
    except Exception:
        pass


def obter_ultimo_provedor_ia() -> str:
    if _em_requisicao_flask():
        from flask import g

        return str(getattr(g, "ultimo_provedor_ia", _ultimo_provedor_ia_processo))
    try:
        return str(runtime.session_state.get("ultimo_provedor_ia", ""))
    except Exception:
        return _ultimo_provedor_ia_processo


def _mensagem_amigavel_erro_ia(
    erro_groq=None,
    erro_gemini=None,
    erro_groq_reserva=None,
    erro_openrouter=None,
) -> str:
    texto = " ".join(
        str(e)
        for e in [erro_groq, erro_gemini, erro_groq_reserva, erro_openrouter]
        if e
    ).lower()
    if not texto:
        return "IA indisponivel no momento. Usando banco de questoes local."
    if "rate limit" in texto or "quota" in texto or "429" in texto or "resource_exhausted" in texto:
        return "Os provedores de IA atingiram o limite de uso temporariamente. Usando banco de questoes local."
    if "api key" in texto or "invalid api key" in texto or "permission" in texto or "unauthorized" in texto:
        return "Houve um problema de autenticacao com a IA. Usando banco de questoes local."
    return "IA indisponivel no momento. Usando banco de questoes local."


def _erro_de_quota_ia(erro) -> bool:
    texto = str(erro or "").lower()
    return any(
        marcador in texto
        for marcador in (
            "rate limit",
            "ratelimit",
            "quota",
            "429",
            "resource_exhausted",
            "tokens per day",
            "requests per day",
            "requests per minute",
        )
    )


# _get_secret mora em core/runtime_context.py (ler_segredo): a mesma leitura
# existia aqui e em repositories/supabase_client.py, identica. O nome local e
# mantido porque tests/test_env_example.py e scripts/gerar_env_para_secret_file.py
# varrem o codigo procurando _get_secret(...) para saber quais variaveis
# o projeto le.


def _get_float_secret(nome: str, padrao: float) -> float:
    valor = _get_secret(nome)
    if valor is None:
        return padrao
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _timeout_ia_segundos() -> float:
    return max(3.0, min(_get_float_secret("IA_PROVIDER_TIMEOUT_SECONDS", 8.0), 25.0))


def _timeout_cadeia_ia_segundos() -> float:
    return max(6.0, min(_get_float_secret("IA_CHAIN_TIMEOUT_SECONDS", 16.0), 26.0))


def _timeout_gemini_segundos() -> float:
    """Prazo proprio do Gemini, menor que o dos outros: ver chamar_ia."""
    return max(1.0, min(_get_float_secret("GEMINI_TIMEOUT_SECONDS", 5.0), 25.0))


def _timeout_restante_requisicao(inicio: float, limite: float) -> float:
    restante = limite - (time.monotonic() - inicio)
    return max(1.0, min(_timeout_ia_segundos(), restante - 0.5))


def _cooldown_quota_gemini_segundos() -> float:
    return max(0.0, min(_get_float_secret("GEMINI_QUOTA_COOLDOWN_SECONDS", 60.0), 3600.0))


def _cooldown_indisponivel_gemini_segundos() -> float:
    # MELHORIA: o cooldown so existia para cota. Medido em 02/09/2026, rodando
    # a cadeia com a configuracao do Render: o Gemini falhou nas quatro
    # tentativas com 503 "high demand", gastando ATE 8 s em cada uma -- e ele e
    # o primeiro da fila, entao comia quase metade do orcamento de 20 s e era
    # tentado de novo na requisicao seguinte.
    #
    # A duracao e menor que a da cota de proposito: 503 e sobrecarga passageira
    # do lado deles, enquanto cota diaria so volta quando a janela vira.
    return max(0.0, min(_get_float_secret("GEMINI_INDISPONIVEL_COOLDOWN_SECONDS", 30.0), 3600.0))


def _erro_de_indisponibilidade_ia(erro) -> bool:
    """O provedor esta de pe, mas sobrecarregado agora."""
    texto = str(erro or "").lower()
    return any(
        marcador in texto
        for marcador in (
            "503",
            "unavailable",
            "overloaded",
            "high demand",
            "try again later",
        )
    )


def _gemini_em_cooldown_quota() -> bool:
    return time.monotonic() < _gemini_quota_bloqueado_ate


def _motivo_do_cooldown_gemini() -> str:
    """Para o log dizer a verdade: "quota" e "sobrecarga" nao sao a mesma coisa."""
    return _gemini_motivo_bloqueio or "quota"


def _registrar_cooldown_gemini(segundos: float, motivo: str) -> None:
    global _gemini_quota_bloqueado_ate, _gemini_motivo_bloqueio
    if segundos <= 0:
        return
    _gemini_quota_bloqueado_ate = max(_gemini_quota_bloqueado_ate, time.monotonic() + segundos)
    _gemini_motivo_bloqueio = motivo


def _registrar_cooldown_quota_gemini() -> None:
    _registrar_cooldown_gemini(_cooldown_quota_gemini_segundos(), "quota")


def _registrar_cooldown_indisponivel_gemini() -> None:
    _registrar_cooldown_gemini(_cooldown_indisponivel_gemini_segundos(), "sobrecarga")


def _json_da_resposta_ia(res, provedor: str) -> dict:
    try:
        escolha = (res.choices or [])[0]
        mensagem = getattr(escolha, "message", None)
        conteudo = getattr(mensagem, "content", None)
    except Exception as exc:
        raise RuntimeError(f"{provedor} retornou resposta em formato inesperado") from exc

    if not isinstance(conteudo, str) or not conteudo.strip():
        motivo = getattr(escolha, "finish_reason", None)
        detalhe = f" finish_reason={motivo}" if motivo else ""
        raise RuntimeError(f"{provedor} retornou resposta vazia ou sem conteudo JSON.{detalhe}")

    return json.loads(conteudo.strip())


def _limpar_json_textual(conteudo: str) -> str:
    texto = str(conteudo or "").strip()
    if texto.startswith("```"):
        linhas = texto.splitlines()
        if linhas and linhas[0].strip().startswith("```"):
            linhas = linhas[1:]
        if linhas and linhas[-1].strip() == "```":
            linhas = linhas[:-1]
        texto = "\n".join(linhas).strip()
    return texto


MODELO_GEMINI_PADRAO = "gemini-flash-lite-latest"


def _chamar_gemini_rest(system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> dict:
    api_key = _get_secret("GEMINI_API_KEY") or _get_secret("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY nao configurada")

    # MELHORIA: "gemini-2.0-flash" parou de existir no catalogo do Google
    # (404 model_not_found em toda chamada). O "gemini-flash-latest" que
    # entrou no lugar vive sobrecarregado na faixa gratuita: 503 "high
    # demand" em 2 de 2 chamadas, e o prazo de 5 s estourado em producao
    # (07/10/2026). O "lite" respondeu 8 de 8, todas aceitas pelo validador
    # (4 do Laboratorio), em 1,6 a 3 s (08/10/2026).
    modelo = _get_secret("GEMINI_MODEL") or MODELO_GEMINI_PADRAO
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(modelo, safe='')}:generateContent?key={quote(api_key, safe='')}"
    )
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=_timeout_ia_segundos()) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini erro {exc.code}: {detalhe}") from exc

    dados = json.loads(raw)
    candidatos = dados.get("candidates") or []
    if not candidatos:
        raise RuntimeError(f"Gemini retornou resposta sem candidatos: {dados}")
    partes = ((candidatos[0].get("content") or {}).get("parts") or [])
    texto = "\n".join(str(parte.get("text") or "") for parte in partes).strip()
    if not texto:
        motivo = candidatos[0].get("finishReason") or dados.get("promptFeedback")
        raise RuntimeError(f"Gemini retornou resposta vazia. motivo={motivo}")
    return json.loads(_limpar_json_textual(texto))

# ── Singletons dos clientes de IA ────────────────────────────────────────────
# MELHORIA: clientes criados uma única vez por processo em vez de a cada chamada,
# evitando overhead de conexão HTTP desnecessário.
_groq_client = None
_openrouter_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        try:
            api_key = _get_secret("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY nao configurada")
            from groq import Groq

            _groq_client = Groq(
                api_key=api_key,
                timeout=_timeout_ia_segundos(),
                max_retries=0,
            )
        except Exception as e:
            print(f"[IA] Não foi possível inicializar cliente Groq: {e}")
    return _groq_client


def _get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None:
        try:
            api_key = _get_secret("OPENROUTER_API_KEY")
            if not api_key:
                raise RuntimeError("OPENROUTER_API_KEY nao configurada")
            from openai import OpenAI

            _openrouter_client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=_timeout_ia_segundos(),
                max_retries=0,
                default_headers={
                    "HTTP-Referer": _get_secret("OPENROUTER_SITE_URL") or "https://educagame.local",
                    "X-Title": _get_secret("OPENROUTER_APP_NAME") or "EducaGame",
                },
            )
        except Exception as e:
            print(f"[IA] Nao foi possivel inicializar cliente OpenRouter: {e}")
    return _openrouter_client


# MELHORIA: os blocos de tentativa baseados em SDK (hoje Groq e OpenRouter)
# tinham cada um sua propria copia identica de duas coisas: a checagem
# "esse provedor esta na lista de pular_provedores desta chamada" (com o
# mesmo formato de erro+log, so trocando nome/proximo) e o registro de
# sucesso (limpar ultimo erro, guardar qual provedor respondeu, log "OK").
# O restante de cada bloco (chamada ao SDK, timeout, parsing da resposta)
# fica diferente o suficiente entre provedores -- parametros que um aceita
# e outro nao -- que nao compensa forcar isso num wrapper generico so; o
# risco de mudar comportamento ja testado ao vivo seria maior que o ganho.
def _provedor_pulado(
    chave: str | tuple[str, ...], provedores_pulados: set[str], nome_exibicao: str, proximo: str
) -> Exception | None:
    chaves = (chave,) if isinstance(chave, str) else chave
    if not any(c in provedores_pulados for c in chaves):
        return None
    sufixo = f" tentando {proximo}..." if proximo else ""
    print(f"[IA] {nome_exibicao} pulado nesta rodada.{sufixo}")
    return RuntimeError(f"{nome_exibicao} pulado por rejeicao anterior")


# MELHORIA: o log dizia QUEM respondeu, nunca em QUANTO TEMPO. Dava para ver
# que uma questao desceu a cascata (cada falha vira uma linha), mas nao quanto
# o aluno esperou: a primeira tentativa, que e a mais cara, nao deixava marca
# nenhuma. Sem isso, decidir o prazo da cadeia (IA_CHAIN_TIMEOUT_SECONDS) era
# palpite -- foi o que faltou para fechar o item 10 do QA de 23/09/2026.
#
# threading.local, e nao uma variavel de modulo: o gunicorn roda com gthread,
# entao duas questoes podem estar sendo geradas ao mesmo tempo no mesmo
# processo, e uma marcaria o relogio da outra.
_relogio_da_cadeia = threading.local()


def _marcar_inicio_da_cadeia() -> None:
    _relogio_da_cadeia.inicio = time.monotonic()


def _tempo_da_cadeia() -> str:
    """" em 7.4 s", ou vazio quando a chamada nao veio da cascata."""
    inicio = getattr(_relogio_da_cadeia, "inicio", None)
    if inicio is None:
        return ""
    return f" em {time.monotonic() - inicio:.1f} s"


def _registrar_sucesso_provedor(chave: str, nome_exibicao: str, modelo: str = "") -> None:
    _registrar_ultimo_erro_ia("")
    _registrar_ultimo_provedor_ia(chave)
    sufixo = f" {modelo}" if modelo else ""
    print(f"[IA] OK {nome_exibicao}{sufixo}{_tempo_da_cadeia()}")


# O gpt-oss RACIOCINA antes de responder, e o raciocinio come o mesmo
# max_tokens da resposta: medido em 13/09, 24/09 e 28/09, ~1 em 3 chamadas
# do Groq terminava em json_validate_failed ("max completion tokens reached
# before generating a valid document", ou JSON cortado no meio). "low" corta
# o raciocinio, nao a resposta. So vale para gpt-oss: modelo que nao raciocina
# recusa o parametro.
#
# Medido em 02/10/2026, 34 chamadas validas com o prompt real (17 de cada
# lado): JSON valido 13 -> 16, resposta no teto de tokens 6 -> 0, questao
# aceita pelo validador 6 -> 11, tempo mediano 3,5 s -> 1,8 s.
#
# IA_REASONING_EFFORT troca o nivel ("medium", "high") e "padrao" desliga --
# volta ao comportamento antigo sem deploy.
ESFORCO_DE_RACIOCINIO_PADRAO = "low"
_SEM_ESFORCO = {"", "padrao", "nenhum", "off", "default"}


def _corpo_do_openrouter(modelo: str) -> dict:
    """Raciocinio desligado e, para modelo da NVIDIA, o servidor da NVIDIA.

    Os gratuitos do OpenRouter raciocinam ate gastar os tokens; desligado, o
    Nemotron respondeu 7 de 10 (08/10/2026). Mas o OpenRouter reparte o mesmo
    modelo entre servidores, e em 09/10 um deles devolveu 400 "Reasoning is
    mandatory for this endpoint and cannot be disabled". Preso ao da NVIDIA,
    3 de 3 aceitas. So para modelo "nvidia/": outro modelo, preso a um
    servidor que nao o serve, falharia sempre.
    """
    corpo: dict = {"reasoning": {"enabled": False}}
    if str(modelo or "").strip().lower().startswith("nvidia/"):
        corpo["provider"] = {"order": ["nvidia"], "allow_fallbacks": False}
    return corpo


def _extras_de_raciocinio(modelo: str) -> dict:
    esforco = _get_secret("IA_REASONING_EFFORT")
    esforco = ESFORCO_DE_RACIOCINIO_PADRAO if esforco is None else str(esforco).strip().lower()
    if esforco in _SEM_ESFORCO or "gpt-oss" not in str(modelo or "").lower():
        return {}
    return {"reasoning_effort": esforco}


def _tentar_provedor(
    chave,
    rotulo: str,
    proximo: str,
    obter_cliente,
    env_modelo: str,
    modelo_padrao: str,
    chamar,
    provedores_pulados: set[str],
    inicio_cadeia: float,
    limite_cadeia: float,
) -> tuple[dict | None, Exception | None]:
    """Uma tentativa da cascata. Devolve (dados, erro) -- dados nao-None e sucesso.

    MELHORIA: cinco provedores repetiam este mesmo encanamento de ~30 linhas
    (checar se foi pulado, pegar o cliente, ler o modelo, calcular o prazo,
    chamar, extrair o JSON, registrar sucesso, capturar excecao e logar).
    Um ajuste no padrao exigia cinco edicoes iguais, e esquecer uma passava
    despercebido. O que MUDA de verdade entre eles -- a chamada ao SDK, com
    os parametros proprios de cada um -- continua explicito no chamador, em
    vez de virar configuracao.
    """
    erro = _provedor_pulado(chave, provedores_pulados, rotulo, proximo)
    if erro is not None:
        return None, erro

    chave_registro = chave if isinstance(chave, str) else chave[0]
    try:
        client = obter_cliente()
        if client is None:
            return None, RuntimeError(f"Cliente {rotulo} nao inicializado")

        modelo = _get_secret(env_modelo) or modelo_padrao
        prazo = _timeout_restante_requisicao(inicio_cadeia, limite_cadeia)
        res = _com_prazo_rigido(lambda: chamar(client, modelo, prazo), timeout=prazo)
        dados = _json_da_resposta_ia(res, rotulo)
        _registrar_sucesso_provedor(chave_registro, rotulo, modelo)
        return dados, None
    except Exception as e:  # noqa: BLE001
        seguinte = f". tentando {proximo}..." if proximo else ""
        print(f"[IA] {rotulo} tambem falhou ({type(e).__name__}): {e}{seguinte}")
        return None, e


def chamar_ia(system_prompt: str, user_prompt: str, max_tokens: int = 1500,
              temperature_groq: float = 1.0,
              temperature_openrouter: float = 0.7,
              pular_provedores: set[str] | list[str] | tuple[str, ...] | None = None,
              deadline_seconds: float | None = None) -> dict | None:
    """
    Roteador de IA em cascata:
      1. Groq (GROQ_MODEL, padrao gpt-oss-120b)
      2. Gemini, via REST API, com prazo curto (GEMINI_TIMEOUT_SECONDS)
      3. Groq reserva (GROQ_MODEL_RESERVA, padrao qwen3.8-27b): outro
         modelo na mesma chave, com cota propria
      4. OpenRouter, via SDK OpenAI compativel
    Retorna dict com o JSON parsed ou None se todos falharem.
    Os clientes sao reutilizados entre chamadas (singleton).

    """
    erro_groq = None
    erro_gemini = None
    erro_groq_reserva = None
    erro_openrouter = None
    provedores_pulados = {str(provedor).strip().lower() for provedor in (pular_provedores or [])}
    _registrar_ultimo_provedor_ia("")
    _marcar_inicio_da_cadeia()
    inicio_cadeia = time.monotonic()
    limite_cadeia = _timeout_cadeia_ia_segundos()
    if deadline_seconds is not None:
        try:
            limite_cadeia = max(3.0, min(float(deadline_seconds), limite_cadeia))
        except (TypeError, ValueError):
            pass

    def _sem_orcamento_para(provedor: str) -> bool:
        restante = limite_cadeia - (time.monotonic() - inicio_cadeia)
        if restante >= 3.0:
            return False
        # MELHORIA: essa mensagem aparecia direto na tela do aluno (ver
        # obter_ultimo_erro_ia/aviso_*_ia nas rotas Flask) com jargao
        # tecnico interno ("cadeia de IA", "orcamento de tempo") que nao
        # significa nada pra quem esta jogando. Usa a mesma mensagem
        # amigavel ja usada quando todos os provedores falham
        # (_mensagem_amigavel_erro_ia), pro aluno so ver "IA indisponivel
        # no momento" em vez de detalhe de implementacao.
        _registrar_ultimo_erro_ia("IA indisponivel no momento. Usando banco de questoes local.")
        print(f"[IA] Orcamento de tempo esgotado antes de {provedor}{_tempo_da_cadeia()}. usando offline...")
        return True

    # MELHORIA: o Gemini era o PRIMEIRO da fila. Medido nos logs do Render de
    # 08 a 15/09/2026: 1 resposta boa ("OK Gemini") contra cerca de 70 falhas
    # -- 503 de sobrecarga, 429 de cota, JSON cortado e, a mais cara, o prazo
    # de 8 s estourado. Cada questao perdia ate 8 s do orcamento antes de chegar
    # ao Groq, que e quem respondia; no teste pelo Chrome de 15/09 isso empurrou
    # questoes para o banco offline.
    #
    # Agora o Groq vem primeiro e o Gemini entra logo depois dele, com prazo
    # proprio e curto (_timeout_gemini_segundos): quando o Groq falha, o Gemini
    # ainda tem a vez, mas nao come o tempo dos que vem depois dele.
    def _tentar_gemini() -> tuple[dict | None, Exception | None]:
        if "gemini" in provedores_pulados:
            print("[IA] Gemini pulado nesta rodada. tentando Groq reserva...")
            return None, RuntimeError("Gemini pulado por rejeicao anterior")
        if _gemini_em_cooldown_quota():
            motivo = _motivo_do_cooldown_gemini()
            print(f"[IA] Gemini em cooldown por {motivo} recente. tentando Groq reserva...")
            return None, RuntimeError(f"Gemini pulado temporariamente por {motivo} recente")
        try:
            prazo = min(_timeout_gemini_segundos(), _timeout_restante_requisicao(inicio_cadeia, limite_cadeia))
            dados = _com_prazo_rigido(
                lambda: _chamar_gemini_rest(
                    system_prompt,
                    user_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature_openrouter,
                ),
                timeout=prazo,
            )
            _registrar_ultimo_erro_ia("")
            _registrar_ultimo_provedor_ia("gemini")
            print(f"[IA] OK Gemini {_get_secret('GEMINI_MODEL') or MODELO_GEMINI_PADRAO}")
            return dados, None
        except Exception as e:
            if _erro_de_quota_ia(e):
                _registrar_cooldown_quota_gemini()
            elif _erro_de_indisponibilidade_ia(e):
                _registrar_cooldown_indisponivel_gemini()
            print(f"[IA] Gemini falhou ({type(e).__name__}): {e}. tentando Groq reserva...")
            return None, e

    # MELHORIA: os blocos abaixo eram ~30 linhas cada, identicas fora a
    # chamada ao SDK. O encanamento foi para _tentar_provedor; aqui fica so o
    # que difere de verdade em cada um -- modelo, metodo e parametros.
    def _mensagens():
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _chamar_openai_compativel(temperatura, **extras):
        def _chamada(client, modelo, prazo):
            return client.chat.completions.create(
                model=modelo,
                messages=_mensagens(),
                temperature=temperatura,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=prazo,
                # Extra da tabela pode ser funcao do modelo (o do OpenRouter e).
                # O do gpt-oss vence o da tabela: se alguem puser um gpt-oss
                # na reserva, ele recebe "low" -- e nao dois reasoning_effort.
                **{
                    **{k: (v(modelo) if callable(v) else v) for k, v in extras.items()},
                    **_extras_de_raciocinio(modelo),
                },
            )

        return _chamada

    tentativas = (
        # (chave, rotulo, proximo, cliente, env do modelo, modelo padrao, chamada)
        #
        # GROQ_MODEL: "llama-3.3-70b-versatile" saiu do catalogo (404
        # model_not_found em toda chamada). Testado ao vivo com o prompt do
        # Laboratorio: gpt-oss-120b acertou 3/3 em 2,5 s por questao, contra
        # 1/3 do gpt-oss-20b e 2/3 do groq/compound (esse a 11,3 s, que
        # estoura o orcamento por provedor).
        ("groq", "Groq", "Gemini", _get_groq_client, "GROQ_MODEL",
         "openai/gpt-oss-120b", _chamar_openai_compativel(temperature_groq, top_p=0.95)),
        # GROQ_MODEL_RESERVA: OUTRO modelo na mesma chave. O Groq conta a
        # cota por modelo (8.000 tokens/min e 1.000 pedidos/dia cada): quando
        # o gpt-oss-120b esgota, este tem a sua. E a chave e outra
        # ("groq_reserva"): a questao recusada que e refeita pulando o
        # "groq" ainda passa por aqui. Medido em 09/10/2026 com o prompt real
        # e o validador: qwen3.8-27b com o raciocinio desligado, 4 de 4
        # aceitas (2 do Laboratorio) em 1,6 a 3,3 s; o gpt-oss-20b, 4 de 8
        # (Laboratorio 1 de 4).
        ("groq_reserva", "Groq reserva", "OpenRouter", _get_groq_client, "GROQ_MODEL_RESERVA",
         "qwen/qwen3.8-27b", _chamar_openai_compativel(temperature_groq, top_p=0.95, reasoning_effort="none")),
        # Sairam da fila em 08 e 09/10/2026: o Mistral recusava toda chamada
        # desde ~09/09 (limite zero no plano) e ainda custava ate 5 s a quem
        # caia nele; o Cerebras estava sem chave no Render desde 02/09
        # (cobranca); o Hugging Face ficou sem credito ("no remaining
        # credits" -- so volta comprando credito ou assinando o PRO).
        # OPENROUTER_MODEL: "openrouter/free" sorteia um gratuito por pedido, e
        # os 15 gratuitos do catalogo raciocinam -- o sorteado gastava os
        # tokens pensando e devolvia vazio (finish_reason=length; 0 de 2 em
        # 08/10/2026). O Nemotron fixo, com o raciocinio DESLIGADO, deu 7 de
        # 10 (Oraculo 5/5) em 2 a 7 s; com effort "low" ainda gastava tudo
        # pensando. O "gpt-4o-mini" de antes e pago, e a conta e gratuita.
        ("openrouter", "OpenRouter", "", _get_openrouter_client, "OPENROUTER_MODEL",
         "nvidia/nemotron-3-super-120b-a12b:free",
         _chamar_openai_compativel(temperature_openrouter, extra_body=_corpo_do_openrouter)),
    )

    erros_por_chave: dict[str, Exception | None] = {}
    # O Gemini entra entre o Groq e a reserva do Groq: ver _tentar_gemini.
    for tentativa in (tentativas[0], "gemini", *tentativas[1:]):
        if tentativa == "gemini":
            if _sem_orcamento_para("Gemini"):
                return None
            dados, erro_gemini = _tentar_gemini()
            if dados is not None:
                return dados
            continue
        chave, rotulo, proximo, cliente, env_modelo, padrao, chamada = tentativa
        if _sem_orcamento_para(rotulo):
            return None
        dados, erro = _tentar_provedor(
            chave, rotulo, proximo, cliente, env_modelo, padrao, chamada,
            provedores_pulados, inicio_cadeia, limite_cadeia,
        )
        if dados is not None:
            return dados
        erros_por_chave[chave if isinstance(chave, str) else chave[0]] = erro

    erro_groq = erros_por_chave.get("groq")
    erro_groq_reserva = erros_por_chave.get("groq_reserva")
    erro_openrouter = erros_por_chave.get("openrouter")

    _registrar_ultimo_erro_ia(
        _mensagem_amigavel_erro_ia(
            erro_groq,
            erro_gemini,
            erro_groq_reserva,
            erro_openrouter,
        )
    )
    # A cascata inteira falhando nao deixava linha nenhuma: dava para ver as
    # falhas uma a uma, mas nao o desfecho nem o tempo gasto ate desistir.
    print(f"[IA] nenhum provedor respondeu{_tempo_da_cadeia()}. usando offline...")
    return None

def gerar_json_ia(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
    temperature_groq: float = 1.0,
    temperature_openrouter: float = 0.7,
    pular_provedores=None,
    deadline_seconds=None,
):
    """Nome que o resto do sistema usa para pedir JSON a cascata de IA.

    Repassa tudo para chamar_ia, sem mudar nada. Existe por dois motivos:
    o nome diz o que se espera de volta, e e o ponto onde os testes trocam
    a IA por um dublê (monkeypatch.setattr(modulo, "gerar_json_ia", ...)).

    MELHORIA: este corpo existia DUAS vezes, identico, em services/ia/enigma.py
    e em services/ia_service.py -- 18 linhas com sete parametros e seus
    defaults, cada copia servindo metade do sistema (Oraculo e Laboratorio de
    um lado; RPG e ENEM do outro). Ninguem estava errado, mas bastava alguem
    acrescentar um parametro numa delas para a outra seguir funcionando sem
    ele, em silencio. Agora mora aqui, embaixo do chamar_ia, e as duas
    importam deste lugar.
    """
    return chamar_ia(
        system_prompt,
        user_prompt,
        max_tokens=max_tokens,
        temperature_groq=temperature_groq,
        temperature_openrouter=temperature_openrouter,
        pular_provedores=pular_provedores,
        deadline_seconds=deadline_seconds,
    )
