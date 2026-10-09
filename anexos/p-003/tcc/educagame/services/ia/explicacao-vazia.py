"""Uma explicacao sem corpo nao ajuda ninguem -- so titulo, ou um molde que
nunca foi preenchido pela IA.

Relatorio de QA de 23/09/2026, achado 4.1: 8 ocorrencias em que a
"Explicacao" trazia so uma frase de molde ("Esta questao trata de X em
Y") ou nem isso -- so o titulo, sem nenhum paragrafo. Confirmado AO VIVO
em 28/09/2026, no ENEM: uma questao de Ciencias da Natureza saiu com a
explicacao inteira sendo "Calculo da energia necessaria" (so o titulo,
bold), sem nenhum passo depois. Nem services/ia/validacao.py (Oraculo,
Escape Room, RPG, Treino Rapido, Laboratorio) nem services/enem_service.py
(ENEM, Batalha contra Chefes) checavam isso antes desta correcao -- os
dois usam esta mesma funcao agora, para nao duplicar o criterio.
"""

from __future__ import annotations

import re

# Curto o bastante para nao recusar uma explicacao real e objetiva; longo o
# bastante para separar "Calculo da energia necessaria" (29 chars, e so
# isso que veio) de um paragrafo de verdade.
TAMANHO_MINIMO_DO_CORPO = 20

# O caso concreto do relatorio: a IA as vezes escreve a propria instrucao do
# prompt ("<tema> em <materia>") em vez de uma explicacao.
_MOLDE_CONHECIDO = re.compile(r"(?i:esta questão trata de .+ em .+)")


def explicacao_tem_corpo(explicacao) -> bool:
    """False quando so ha titulo (tipo "bold") ou um molde nao preenchido.

    Conta como corpo qualquer bloco que NAO seja "bold" e cujo conteudo nao
    bata com o molde conhecido; soma o tamanho desses blocos e exige um
    minimo -- um titulo sozinho soma zero, e um molde reconhecido nao entra
    na soma mesmo vindo com "tipo": "texto".
    """
    if not isinstance(explicacao, list):
        return False

    corpo = []
    for bloco in explicacao:
        if not isinstance(bloco, dict):
            continue
        conteudo = str(bloco.get("conteudo", "") or "").strip()
        if not conteudo or bloco.get("tipo") == "bold":
            continue
        if _MOLDE_CONHECIDO.search(conteudo):
            continue
        corpo.append(conteudo)

    return sum(len(texto) for texto in corpo) >= TAMANHO_MINIMO_DO_CORPO
