"""Confere a configuracao no boot e diz em voz alta o que esta faltando.

MELHORIA: as duas piores falhas deste projeto tiveram a mesma assinatura --
o app SOBE bem e funciona ERRADO, sem nada no log:

  - GROQ_MODEL com valor sem o prefixo do fornecedor ("gpt-oss-120b" em vez
    de "openai/gpt-oss-120b"): o Groq respondia 404 a cada questao e a
    cascata caia no proximo provedor. Passou semanas assim.
  - SUPABASE_URL/KEY inacessiveis no Streamlit Cloud: o app abriu normal,
    so que sem banco nenhum -- a falha so aparecia ao tentar listar escolas.

Nos dois casos o problema estava visivel na configuracao desde o primeiro
segundo. Faltava alguem olhar e falar.
"""

from __future__ import annotations

import sys
from typing import Any

# Sem estes o app nao tem banco: nao ha escola, aluno nem login.
#
# Cada item e uma lista de nomes ACEITOS, espelhando a resolucao real em
# repositories/supabase_client.py -- a chave pode vir com tres nomes
# diferentes. Checar so um deles faria o diagnostico acusar falta de
# configuracao num app que funciona, e um verificador que grita a toa
# ensina a ignorar o log.
OBRIGATORIAS = (
    ("SUPABASE_URL",),
    ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY", "SUPABASE_KEY"),
)

# Qualquer uma destas ja liga a cascata de IA. Nenhuma = so banco offline.
CHAVES_DE_IA = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
)

# Modelos que exigem prefixo de fornecedor no nome. Foi exatamente aqui que
# o Groq quebrou em silencio.
MODELOS_COM_FORNECEDOR = {
    "GROQ_MODEL": "openai/gpt-oss-120b",
    "GROQ_MODEL_RESERVA": "qwen/qwen3.8-27b",
}


def _lido(nome: str) -> str:
    """Le pelo mesmo caminho do app: variavel de ambiente e depois secrets.

    MELHORIA: esta era a TERCEIRA implementacao da mesma leitura -- as outras
    duas viviam como `_get_secret` em repositories/supabase_client.py e
    services/ia/providers.py. Um diagnostico que le a configuracao por um
    caminho diferente do que o app usa pode dar OK numa configuracao que o
    app nao enxerga, ou acusar falta do que existe. Agora e a mesma funcao;
    aqui so se acrescenta o contrato local (texto ja sem espacos, nunca
    None), que e o que o relatorio precisa.
    """
    from core.runtime_context import ler_segredo

    return str(ler_segredo(nome) or "").strip()


def verificar_configuracao() -> list[tuple[str, str]]:
    """Devolve [(nivel, mensagem)] com nivel em {"erro", "aviso"}."""
    achados: list[tuple[str, str]] = []

    ausentes = [
        aceitos[0] for aceitos in OBRIGATORIAS if not any(_lido(nome) for nome in aceitos)
    ]
    if ausentes:
        achados.append(
            (
                "erro",
                f"sem {' e '.join(ausentes)}: o app sobe mas fica sem banco "
                "(nenhuma escola, aluno ou login vai funcionar).",
            )
        )

    if not any(_lido(nome) for nome in CHAVES_DE_IA):
        achados.append(
            (
                "aviso",
                "nenhuma chave de IA configurada: todas as questoes virao do "
                "banco offline.",
            )
        )

    for nome, exemplo in MODELOS_COM_FORNECEDOR.items():
        valor = _lido(nome)
        if valor and "/" not in valor:
            achados.append(
                (
                    "erro",
                    f"{nome}={valor!r} nao tem prefixo de fornecedor. O provedor "
                    f"responde 404 e a cascata cai no proximo, sem erro visivel. "
                    f"Use {exemplo!r} ou apague a variavel para usar o padrao.",
                )
            )

    return achados


def _imprimir_com_flush(mensagem: str) -> None:
    # MELHORIA: print() comum ficava preso. Quando a saida do processo vai
    # para um pipe -- que e o caso do Streamlit Cloud e do Render -- o stdout
    # e bufferizado por bloco, e a mensagem so apareceria muito depois ou
    # nunca. Um diagnostico de boot que nao chega no log nao serve pra nada.
    print(mensagem, flush=True)


def tornar_saida_tolerante() -> bool:
    """Impede que escrever no log derrube o que estava sendo feito.

    MELHORIA: bug visto ao vivo. A IA gerou uma questao valida contendo
    "\\u202f" (espaco estreito sem quebra, que ela usa entre numero e
    unidade). O log do projeto imprime o enunciado junto do motivo da
    rejeicao, e no Windows o stdout sai em cp1252, onde esse caractere nao
    existe. O print levantou UnicodeEncodeError, a excecao subiu, foi
    capturada pelo `except Exception` de quem chamou -- e a questao inteira
    foi para o lixo, substituida pelo banco offline:

        [LAB] Falha ao gerar desafio; usando fallback offline seguro:
        UnicodeEncodeError: 'charmap' codec can't encode character '\\u202f'

    Uma linha de log matou uma questao boa. E o log e justamente a parte do
    sistema que nunca deveria ter esse poder: ele existe para contar o que
    aconteceu, nao para mudar o que acontece.

    A correcao nao troca a codificacao do terminal (isso mudaria como o
    texto aparece para quem le): so troca a politica de erro para
    "replace", que escreve "?" no lugar do caractere impossivel em vez de
    levantar. No Render e no Streamlit Cloud a saida ja e UTF-8 e nada
    muda; no Windows, para de quebrar.

    Devolve True quando conseguiu ajustar.
    """
    ajustou = False
    for fluxo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(fluxo, "reconfigure", None)
        if not callable(reconfigurar):
            continue
        try:
            if getattr(fluxo, "errors", None) not in ("replace", "backslashreplace", "ignore"):
                reconfigurar(errors="replace")
            ajustou = True
        except Exception:  # noqa: BLE001 - saida redirecionada, sem reconfigure
            continue
    return ajustou


def relatar_configuracao(imprimir: Any = _imprimir_com_flush) -> list[tuple[str, str]]:
    """Escreve o diagnostico no log do processo (Render, Streamlit Cloud)."""
    tornar_saida_tolerante()
    achados = verificar_configuracao()
    for nivel, mensagem in achados:
        imprimir(f"[CONFIG] {nivel.upper()}: {mensagem}")
    if not achados:
        imprimir("[CONFIG] OK: banco e IA configurados.")
    return achados
