from __future__ import annotations

import random

from services.ia.citacao_alternativas import (
    CITACAO_DE_ALTERNATIVA,
    LETRAS_DAS_ALTERNATIVAS,
    corrigir_bloco_textual,
    trocar_letras_citadas,
)


def embaralhar_opcoes_questao(dados: dict) -> dict:
    payload = dict(dados or {})
    opcoes = payload.get("opcoes", [])
    if not isinstance(opcoes, list) or len(opcoes) < 2:
        return payload

    try:
        idx_correta = int(payload.get("correta", 0))
    except Exception:
        idx_correta = 0

    if idx_correta < 0 or idx_correta >= len(opcoes):
        idx_correta = 0

    opcoes_traducao = payload.get("opcoes_traducao", [])
    tem_traducao_pareada = isinstance(opcoes_traducao, list) and len(opcoes_traducao) == len(opcoes)

    itens = []
    for idx, opcao in enumerate(opcoes):
        item = {
            "opcao": opcao,
            "correta": idx == idx_correta,
            "posicao": idx,
        }
        if tem_traducao_pareada:
            item["traducao"] = opcoes_traducao[idx]
        itens.append(item)

    random.shuffle(itens)

    payload["opcoes"] = [item["opcao"] for item in itens]
    payload["correta"] = next((idx for idx, item in enumerate(itens) if item["correta"]), 0)
    if tem_traducao_pareada:
        payload["opcoes_traducao"] = [item["traducao"] for item in itens]

    # MELHORIA: a IA escreve a explicacao na ordem em que ELA propos as
    # opcoes ("... alternativa B"), e o embaralhamento acima muda a posicao
    # sem reescrever o texto -- mesma causa-raiz ja corrigida no ENEM
    # (enem_service._embaralhar_alternativas_questao). Sem isso, a
    # explicacao do Oraculo/Escape Room/RPG/Laboratorio passa a apontar
    # para o distrator errado (relatorio de QA de 23/09/2026, achado 3.1:
    # 29 ocorrencias, a maioria fora do ENEM/Batalha).
    texto_enunciado = " ".join([str(payload.get("pergunta", ""))] + [str(opcao) for opcao in opcoes])
    if CITACAO_DE_ALTERNATIVA.search(texto_enunciado):
        # O proprio enunciado/opcoes ja falam em "alternativa A": a letra da
        # explicacao pode ser da historia, e nao da lista -- fica como esta.
        return payload

    nova_letra = {
        LETRAS_DAS_ALTERNATIVAS[item["posicao"]]: LETRAS_DAS_ALTERNATIVAS[nova]
        for nova, item in enumerate(itens)
        if max(nova, item["posicao"]) < len(LETRAS_DAS_ALTERNATIVAS)
    }
    for campo in ("explicacao", "passos_resolucao"):
        if campo in payload:
            payload[campo] = corrigir_bloco_textual(
                payload[campo], lambda texto: trocar_letras_citadas(texto, nova_letra)
            )

    return payload


def finalizar_questao(dados: dict, nivel_txt: str) -> dict:
    questao = embaralhar_opcoes_questao(dados)
    questao["dificuldade"] = nivel_txt
    return questao
