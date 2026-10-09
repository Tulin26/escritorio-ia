"""A letra citada numa explicacao tem de ser a da alternativa exibida.

A IA escreve a explicacao na ordem em que ELA propos as opcoes ("...
corresponde a alternativa B"), e o embaralhamento da exibicao vem depois.
Sem corrigir o texto, a explicacao passa a apontar para outra alternativa --
quase sempre um distrator. O relatorio de QA de 23/09/2026 (achado 3.1)
confirmou 29 ocorrencias em todos os modos que nao passam por
`enem_service._embaralhar_alternativas_questao` (que ja tinha esta correcao
para o ENEM e a Batalha contra Chefes).

Este modulo centraliza a logica para ser reaproveitada tanto pelo ENEM
quanto pelo embaralhamento generico em `services.ia.questoes` (usado pelo
Oraculo, Escape Room, RPG e Laboratorio de Exatas).
"""
from __future__ import annotations

import re

LETRAS_DAS_ALTERNATIVAS = "ABCDE"

# A palavra antes da letra e obrigatoria. Sozinha, a maiuscula e artigo ("A
# utilizacao de imagens...") ou unidade ("Resposta correta: 4,5 A", 44
# questoes do banco de reserva). "Opcao" e "item" ficam de fora: nomeiam
# planos e cenarios nos enunciados ("a opcao A, de aluguel").
_LETRA_CITADA = r"[(\"'“‘]?[A-E][)\"'”’]?(?![A-Za-zÀ-ÿ0-9])"
CITACAO_DE_ALTERNATIVA = re.compile(
    r"(?i:\b(?:alternativas?|letras?|gabarito)\b)"
    r"(?:\s+(?i:correta|certa|incorreta|errada)(?:\s+(?:é|e))?(?:\s+a)?)?"
    r"\s*:?\s*" + _LETRA_CITADA
    + r"(?:\s*(?:,|\be\b|\bou\b)\s*(?:a\s+)?" + _LETRA_CITADA + r")*"
)
_LETRA_SOLTA = re.compile(r"(?<![A-Za-zÀ-ÿ])[A-E](?![A-Za-zÀ-ÿ0-9])")


def trocar_letras_citadas(texto: str, nova_letra: dict[str, str]) -> str:
    def trocar(citacao: re.Match) -> str:
        return _LETRA_SOLTA.sub(lambda letra: nova_letra.get(letra.group(0), letra.group(0)), citacao.group(0))

    return CITACAO_DE_ALTERNATIVA.sub(trocar, texto)


def corrigir_bloco_textual(valor, corrigir):
    """Aplica `corrigir` a strings dentro de listas/dicts (chaves titulo/conteudo)."""
    if isinstance(valor, str):
        return corrigir(valor)
    if isinstance(valor, list):
        return [corrigir_bloco_textual(item, corrigir) for item in valor]
    if isinstance(valor, dict):
        dados = dict(valor)
        for chave in ("titulo", "conteudo"):
            if chave in dados:
                dados[chave] = corrigir_bloco_textual(dados[chave], corrigir)
        return dados
    return valor
