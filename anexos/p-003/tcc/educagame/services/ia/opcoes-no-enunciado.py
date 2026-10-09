"""O enunciado nao pode listar as proprias alternativas com letra fixa.

Relatorio de QA de 23/09/2026, achado 3.1 (Batalha contra Chefes, Batalha 7,
Chefe 3): a IA devolveu o enunciado com as opcoes ja escritas e rotuladas
("A) adubos inorganicos; B) plantar leguminosas; C) fosforo...") enquanto a
lista exibida na tela, apos o embaralhamento, mostrava outra ordem. O aluno
que le a letra no proprio enunciado e marca por ela erra sem cometer erro de
conteudo -- a correcao da explicacao (services/ia/citacao_alternativas.py)
nao alcanca esse caso, porque o texto problematico esta na pergunta, nao na
explicacao.

Este modulo detecta o padrao -- pelo menos duas letras de opcao (A-E)
seguidas de ")" ou "." e mais texto, na ordem alfabetica de uma lista real --
para a validacao recusar a questao antes de exibi-la.
"""
from __future__ import annotations

import re

_MARCADOR_OPCAO = re.compile(r"(?:^|[\s;:])([A-E])[).]\s+\S")


def pergunta_embute_opcoes_com_letra(pergunta) -> bool:
    texto = str(pergunta or "")
    letras = _MARCADOR_OPCAO.findall(texto)
    if len(letras) < 2:
        return False

    # Exige ordem alfabetica nao decrescente: e o que distingue uma lista de
    # opcoes real ("A) ... B) ... C) ...") de letras soltas que aparecerem
    # por coincidencia em ordem qualquer no meio do texto.
    indices = [ord(letra) for letra in letras]
    return indices == sorted(indices) and len(set(letras)) >= 2
