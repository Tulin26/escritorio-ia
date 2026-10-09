from __future__ import annotations

from repositories.supabase_client import supabase
from core.config import normalizar_dificuldade
from core.runtime_context import get_runtime

runtime = get_runtime()


# Todas as colunas existentes em public.logs_pedagogicos.
# Campos fora deste conjunto são descartados antes do insert para evitar erro 400.
LOG_COLUMNS = {
    # identificação
    "aluno_id", "escola_id",
    # conteúdo da questão
    "materia", "resultado",
    "pergunta_texto", "resposta_correta", "resposta_aluno", "explicacao_ia",
    # métricas
    "tempo_resposta",
    # classificação
    "modo", "area_bncc", "competencia_bncc", "habilidade_bncc",
    "codigo_bncc", "dificuldade", "matriz_enem",
    # a resolução, para poder medir validações contra dado real
    "passos_json",
    # a fórmula e a legenda, pelo mesmo motivo: a validação
    # `legenda-com-variavel-sem-formula` cruza os três, e até aqui só dava
    # para medi-la contra o banco offline — que engana (ver a migração
    # 20260909120000).
    "formula", "subformulas", "legenda_variaveis",
    # as alternativas, pelo mesmo motivo dos tres acima: sem elas nao ha
    # como medir, contra dado real, se a explicacao contradiz o gabarito.
    # O log guardava o TEXTO da resposta certa, e nao a lista -- e sem a
    # lista nao da para saber se a explicacao nomeia OUTRA alternativa.
    "opcoes",
}

# MELHORIA: o log guardava pergunta, alternativas e explicacao, mas NAO os
# passos de resolucao -- que sao justamente o que varias validacoes da IA
# julgam. Sem eles nao havia como medir o risco de ligar uma regra nova, e
# pelo menos uma ficou parada por isso (recusar resolucao que nao calcula
# nada, deixando o Delta como simbolo).
#
# O banco offline nao substitui: sao 2.200 questoes do Laboratorio em apenas
# 81 FORMAS distintas de resolucao, e escrever moldes novos de proposito
# tornaria a medicao circular.
#
# Os limites existem porque isto entra em TODA resposta de exatas: 12 passos
# e o dobro do que o Laboratorio usa, e 600 caracteres cabem uma linha de
# Bhaskara inteira com folga.
_MAX_PASSOS_LOG = 12
_MAX_CHARS_POR_PASSO = 600

# A formula principal e curta ("x = (-b \pm \sqrt{\Delta})/(2a)"); a legenda
# lista uma frase por variavel e cresce mais. Sao subformulas de verdade, nao
# uma lista de significados -- por isso o teto baixo.
_MAX_SUBFORMULAS_LOG = 6
_MAX_CHARS_FORMULA = 400
_MAX_CHARS_LEGENDA = 800

# Alternativas: cinco cabe o ENEM (A-E), que e o modo com mais opcoes. O
# limite por alternativa e generoso porque em Linguagens elas sao frases
# inteiras -- cortar curto demais estragaria justamente a medicao, que
# precisa saber se a explicacao NOMEIA a alternativa.
_MAX_OPCOES_LOG = 5
_MAX_CHARS_OPCAO = 400


def _passos_para_json(valor) -> list[dict]:
    """A resolucao em forma enxuta: titulo, conteudo e a marca de final.

    Devolve lista vazia quando nao ha o que guardar -- quem chama ja decide
    com `if passos:`, entao um `or None` aqui seria so uma segunda forma de
    dizer a mesma coisa (um mutante mostrou que era rede sem efeito).
    """
    if not isinstance(valor, list) or not valor:
        return []
    passos = []
    for item in valor[:_MAX_PASSOS_LOG]:
        if not isinstance(item, dict):
            continue
        conteudo = str(item.get("conteudo", "") or "").strip()
        if not conteudo:
            continue
        passo = {"conteudo": conteudo[:_MAX_CHARS_POR_PASSO]}
        titulo = str(item.get("titulo", "") or "").strip()
        if titulo:
            passo["titulo"] = titulo[:80]
        if item.get("final"):
            passo["final"] = True
        passos.append(passo)
    return passos


def _subformulas_para_json(valor) -> list[str]:
    """As formulas auxiliares, so as que sao texto de verdade.

    Lista vazia quando nao ha o que guardar. Quem chama decide com `if`, do
    mesmo jeito que `_passos_para_json` -- devolver None aqui seria uma
    segunda forma de dizer a mesma coisa.
    """
    if not isinstance(valor, list) or not valor:
        return []
    limpas = []
    for item in valor[:_MAX_SUBFORMULAS_LOG]:
        texto = str(item or "").strip()
        if texto:
            limpas.append(texto[:_MAX_CHARS_FORMULA])
    return limpas


def _opcoes_para_json(valor) -> list[str]:
    """As alternativas, so as que sao texto de verdade.

    Guardadas para dar como medir, contra dado REAL, se a explicacao da IA
    contradiz o gabarito -- a regra `_explicacao_aponta_para_outra_alternativa`
    precisa da lista, e nao so do texto da resposta certa.

    Uma alternativa vazia no meio nao e descartada em silencio: ela vira ""
    para o indice do gabarito continuar valendo. Compactar a lista faria a
    medicao apontar para a alternativa errada, que e pior do que nao medir.
    """
    if not isinstance(valor, (list, tuple)):
        return []
    limpas = [str(item or "").strip()[:_MAX_CHARS_OPCAO] for item in valor[:_MAX_OPCOES_LOG]]
    return limpas if any(limpas) else []


def _normalizar_tempo_resposta(valor):
    if valor is None or valor == "":
        return None
    try:
        return round(max(0.0, float(valor)), 2)
    except (TypeError, ValueError):
        return None


def tempo_resposta_para_media(valor) -> float | None:
    tempo = _normalizar_tempo_resposta(valor)
    if tempo is None or tempo <= 0:
        return None
    return tempo


def _inferir_modo_log(payload: dict) -> str:
    modo = str(payload.get("modo") or "").strip().lower()
    if modo:
        return modo
    materia = str(payload.get("materia") or "").strip().upper()
    if materia.startswith("RPG-"):
        return "rpg"
    if materia.startswith("LAB-"):
        return "laboratorio"
    if materia.startswith("ENEM-") or "ENEM" in materia:
        return "enem"
    return "oraculo"


def _normalizar_resultado(valor) -> str:
    texto = str(valor or "").strip().lower()
    if texto in {"acertou", "acerto", "correto", "true", "1", "sim", "yes"}:
        return "Acertou"
    return "Errou"


def _truncar_texto(valor, limite: int = 5000) -> str | None:
    """Evita payloads gigantes em campos de texto livre."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto[:limite] if len(texto) > limite else texto or None


def preparar_payload_log(payload: dict, tempo_resposta: float | None = None) -> dict:
    # Filtra apenas colunas conhecidas
    dados: dict = {chave: valor for chave, valor in payload.items() if chave in LOG_COLUMNS}

    # A tela entrega a resolucao no formato dela ("passos_resolucao"); a
    # coluna guarda a versao enxuta. Aceita tambem "passos_json" ja pronto,
    # porque o Streamlit passa por `extras`.
    passos = _passos_para_json(payload.get("passos_resolucao") or dados.get("passos_json"))
    if passos:
        dados["passos_json"] = passos
    else:
        dados.pop("passos_json", None)

    # Campos obrigatórios / normalizados
    dados["modo"] = _inferir_modo_log(payload)
    dados["resultado"] = _normalizar_resultado(payload.get("resultado"))
    # MELHORIA: a dificuldade chegava em QUATRO grafias -- "Medio", "Médio",
    # "Difícil" e "🔴 Difícil" (o rotulo do slider do Streamlit ia direto).
    # O painel filtra por este campo, entao "Medio" e "Médio" contavam como
    # dificuldades diferentes. Normalizar AQUI conserta os oito modos de uma
    # vez, no mesmo lugar onde `resultado` e `modo` ja sao normalizados --
    # corrigir tela por tela deixaria a proxima nascer torta.
    if "dificuldade" in dados:
        dados["dificuldade"] = normalizar_dificuldade(dados["dificuldade"]) or None
    dados["tempo_resposta"] = _normalizar_tempo_resposta(
        tempo_resposta if tempo_resposta is not None else dados.get("tempo_resposta")
    )
    if not dados.get("materia"):
        dados["materia"] = "Geral"

    # A formula e a legenda: guardadas para dar como medir a validacao
    # `legenda-com-variavel-sem-formula` contra dado REAL. Vazio nao vira
    # linha -- a maioria dos modos nao tem esses campos, e gravar "" faria
    # a consulta contar como "tem legenda" o que nao tem.
    subformulas = _subformulas_para_json(dados.get("subformulas"))
    if subformulas:
        dados["subformulas"] = subformulas
    else:
        dados.pop("subformulas", None)

    # As alternativas. Mesma regra dos campos acima: lista vazia nao vira
    # linha, senao a consulta contaria como "tem alternativas" o que nao tem.
    opcoes = _opcoes_para_json(payload.get("opcoes") or dados.get("opcoes"))
    if opcoes:
        dados["opcoes"] = opcoes
    else:
        dados.pop("opcoes", None)

    for campo, limite in (
        ("formula", _MAX_CHARS_FORMULA),
        ("legenda_variaveis", _MAX_CHARS_LEGENDA),
    ):
        texto = str(dados.get(campo, "") or "").strip()
        if texto:
            dados[campo] = texto[:limite]
        else:
            dados.pop(campo, None)

    # Trunca campos de texto livre para evitar payloads excessivos
    for campo in ("pergunta_texto", "resposta_correta", "resposta_aluno", "explicacao_ia"):
        if campo in dados:
            dados[campo] = _truncar_texto(dados[campo])

    return dados


def registrar_log(dados: dict):
    try:
        result = (
            supabase.table("logs_pedagogicos")
            .insert(preparar_payload_log(dados))
            .execute()
        )
        buscar_logs.clear()
        listar_logs_por_aluno.clear()
        return result
    except Exception as e:
        print(f"Erro ao registrar log: {e}")
        return None


def registrar_log_com_tempo(dados: dict, tempo_resposta: float | None = None):
    try:
        payload = preparar_payload_log(dados, tempo_resposta)
        result = (
            supabase.table("logs_pedagogicos")
            .insert(payload)
            .execute()
        )
        buscar_logs.clear()
        listar_logs_por_aluno.clear()
        return result
    except Exception as e:
        print(f"Erro ao registrar log com tempo: {e}")
        return None


@runtime.cache_data(ttl=60)
def buscar_logs(escola_id: str, aluno_id: str | None = None):
    try:
        query = (
            supabase.table("logs_pedagogicos")
            .select("*")
            .eq("escola_id", escola_id)
        )
        if aluno_id:
            query = query.eq("aluno_id", aluno_id)
        return query.order("data_hora", desc=True).execute().data or []
    except Exception as e:
        print(f"Erro ao buscar logs: {e}")
        return []


@runtime.cache_data(ttl=60)
def listar_logs_por_aluno(aluno_id: str, escola_id: str):
    try:
        return (
            supabase.table("logs_pedagogicos")
            .select("*")
            .eq("aluno_id", aluno_id)
            .eq("escola_id", escola_id)
            .order("data_hora", desc=True)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"Erro ao listar logs do aluno: {e}")
        return []
