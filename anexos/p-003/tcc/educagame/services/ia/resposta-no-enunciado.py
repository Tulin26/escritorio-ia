"""O enunciado nao pode dizer, com todas as letras, qual e a resposta.

Relatorio de QA de 23/09/2026, achado 5.5 ("itens mal formulados, ambiguos
ou auto-respondidos"). Dois casos da tabela sao o mesmo defeito:

  * Escape Room / Geografia (08:45:20): "o comando termina com 'indicando
    seu crescimento natural' e a alternativa correta e 'Taxa de crescimento
    natural'";
  * Geografia Q17 e Q20 (Oraculo): "cada alternativa traz sua propria
    definicao e a correta repete literalmente o enunciado".

Medido nos 554 registros reais de 28/09/2026, a IA repete a resposta assim em
duas questoes ("Qual formulacao tradicional da epistemologia classica define
conhecimento como cren,ca verdadeira justificada?" -> "Cren,ca verdadeira
justificada"; e a mesma coisa em Ingles, com a voz passiva). Uma terceira
questao pega aqui ja era recusada pela regra de opcoes embutidas.

Nao da para consertar sem regerar: a resposta esta no enunciado, e reescrever
o enunciado mudaria a questao. Por isso esta regra RECUSA, como a de opcoes
embutidas -- e ao contrario do suporte ausente, que o prompt passou a gerar
em vez de recusar.

A guarda de leitura e a parte importante. Questao de interpretacao TEM a
resposta no enunciado de proposito: "Leia: 'O filme dura 120 minutos... e o
melhor da serie.' Qual parte do trecho e uma opiniao?" tem como gabarito um
pedaco do proprio texto. Sem a guarda, a regra recusaria 36 questoes assim so
nos bancos offline -- todas corretas.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Sinais de que a pergunta manda LER algo: aspas de qualquer formato, mencao
# ao texto/trecho/frase, ou o equivalente em ingles.
_PEDE_LEITURA = re.compile(
    r"['\"‘’“”«»]|\bno texto\b|\bdo texto\b|\bno trecho\b|"
    r"\bdo trecho\b|\bna passagem\b|\bda passagem\b|\bsegundo o (?:texto|autor|trecho)\b|"
    r"\bqual parte\b|\bna frase\b|\bda frase\b|\bno poema\b|\bna tabela\b|\bnos dados\b|"
    r"\bpassage\b|\btext above\b|\bread (?:the|this)\b",
    re.IGNORECASE,
)

# Palavra que conta: so letra, pelo menos tres. Sem isso "5 g/L" viraria tres
# palavras ("5", "g", "l") e 20 questoes de diluicao dos bancos -- corretas --
# cairiam na regra, porque "5 g/L" aparece no enunciado.
_PALAVRA_DE_CONTEUDO = re.compile(r"[a-z]{3,}")

# Duas palavras seguidas ja bastam quando SO a correta as tem: o caso do
# relatorio e exatamente esse -- o enunciado termina em "indicando seu
# crescimento natural" e a correta e "Taxa de crescimento natural". Cobrar a
# alternativa inteira deixaria justamente ele passar.
_MINIMO_EM_SEQUENCIA = 2

# Quanto a correta precisa vencer o melhor distrator. Sem essa folga, toda
# questao em que um distrator reaproveita duas palavras do enunciado ficaria
# de fora -- e e o que acontece em Ingles, onde "the report" e "the manager"
# aparecem em varias alternativas.
_VANTAGEM_SOBRE_O_DISTRATOR = 2

# Quanto da alternativa correta o trecho repetido precisa cobrir. E a guarda
# que separa "o enunciado diz a resposta" de "a resposta cita o assunto da
# pergunta". Medido nos bancos: sem ela, "O MST, fundado no Brasil na decada
# de 1980, luta principalmente por:" seria recusada porque a correta fala em
# "trabalhadores rurais" -- duas palavras que estao no NOME do movimento, nao
# na resposta. Idem "Qual e uma diferenca entre uma lei e uma regra moral?",
# em que a correta precisa repetir "regra moral" para comparar as duas.
_COBERTURA_MINIMA = 0.5


def _chave(texto: Any) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "").lower())
    sem_acento = "".join(ch for ch in sem_acento if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", sem_acento)).strip()


def _texto_da_correta(opcoes: Any, correta: Any) -> str:
    itens = [str(opcao) for opcao in (opcoes or [])]
    if isinstance(correta, bool):
        return ""
    if isinstance(correta, int) and 0 <= correta < len(itens):
        return itens[correta]
    texto = str(correta or "").strip()
    return texto if texto in itens else ""


def _maior_sequencia_no_enunciado(enunciado: str, opcao: str) -> int:
    """Maior numero de palavras SEGUIDAS da opcao que aparecem no enunciado."""
    palavras = _PALAVRA_DE_CONTEUDO.findall(_chave(opcao))
    if not palavras:
        return 0

    texto = f" {' '.join(_PALAVRA_DE_CONTEUDO.findall(_chave(enunciado)))} "
    maior = 0
    for inicio in range(len(palavras)):
        for fim in range(len(palavras), inicio + maior, -1):
            if f" {' '.join(palavras[inicio:fim])} " in texto:
                maior = fim - inicio
                break
    return maior


def pergunta_entrega_a_resposta(pergunta: Any, opcoes: Any, correta: Any) -> bool:
    """O enunciado tem um trecho que aponta so para a alternativa correta."""
    correta_txt = _texto_da_correta(opcoes, correta)
    if not correta_txt:
        return False

    enunciado = str(pergunta or "")
    # O suporte (o texto/tabela do achado 3.2) NAO abre excecao: ele mora em
    # campo proprio, e o enunciado que repete a resposta se entrega do mesmo
    # jeito. A guarda tentada para ele foi arrancada quando a mutacao mostrou
    # que nenhum caso real -- nem inventado -- precisava dela.
    if _PEDE_LEITURA.search(enunciado):
        return False

    palavras_da_correta = len(_PALAVRA_DE_CONTEUDO.findall(_chave(correta_txt)))
    da_correta = _maior_sequencia_no_enunciado(enunciado, correta_txt)
    if da_correta < _MINIMO_EM_SEQUENCIA:
        return False
    if da_correta < _COBERTURA_MINIMA * max(1, palavras_da_correta):
        return False

    dos_outros = max(
        (
            _maior_sequencia_no_enunciado(enunciado, opcao)
            for opcao in (opcoes or [])
            if str(opcao) != str(correta_txt)
        ),
        default=0,
    )
    return da_correta >= dos_outros + _VANTAGEM_SOBRE_O_DISTRATOR
