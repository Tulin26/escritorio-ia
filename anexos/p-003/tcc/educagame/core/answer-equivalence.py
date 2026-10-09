from __future__ import annotations

import re
import unicodedata


def _numero(texto: str) -> float:
    return float(str(texto).replace(",", "."))


_PADRAO_NUMERO = r"(?<![\w])-?\d+(?:[.,]\d+)?(?![\w])"
_PADRAO_CONECTOR_RESIDUAL = re.compile(r"[\s,;]+|\be\b|\bou\b|\band\b")

# MELHORIA: "(3, 4)" e "(4, 3)" eram SEMPRE o mesmo par de raizes -- os dois
# numeros sao ordenados antes de comparar. Entre parenteses, porem, o par tanto
# pode ser conjunto de raizes ("Encontre as raizes": (0.5, -3)) quanto par
# ORDENADO -- vertice, ponto, solucao (x, y) de sistema --, e ai a ordem E a
# resposta: trocar as coordenadas e o distrator classico dessas questoes.
#
# O estrago aparecia na normalizacao, que apaga alternativa "equivalente".
# Medido nos bancos em 14/09/2026: 40 questoes perdiam uma alternativa -- as
# 20 de vertice do Laboratorio e as 20 de sistemas lineares do Ensino Medio --
# e em 22 delas a apagada era a CERTA, com outra marcada como certa no lugar.
# O vertice de (x - 3)^2 + 4 chegava ao aluno com "(-3, 4)" como resposta.
#
# So a alternativa nao basta para decidir: "(0.5, -3)" e raiz ou ponto
# conforme a PERGUNTA. Entao o par entre parenteses so vale como raiz quando a
# alternativa ou a pergunta fala em raiz ou zeros, e a pergunta nao fala em
# vertice, ponto, coordenada ou sistema. "Solucao" nao decide: "a solucao do
# sistema" e par ordenado. Sem pergunta, o par fica ordenado -- errar para esse
# lado so deixa de apagar uma raiz repetida; o outro lado apaga a certa.
_PAR_ORDENADO = re.compile(r"\(\s*-?\d+(?:[.,]\d+)?\s*[,;]\s*-?\d+(?:[.,]\d+)?\s*\)")
_FALA_DE_RAIZ = re.compile(r"x'|\braiz\b|\braizes\b|\bzeros\b")
_FALA_DE_PAR_ORDENADO = re.compile(r"\b(?:vertice|pontos?|coordenadas?|par ordenado|sistemas?)\b")


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return decomposto.encode("ascii", "ignore").decode("ascii")


def _par_entre_parenteses_e_raiz(opcao: str, pergunta: str) -> bool:
    if _FALA_DE_RAIZ.search(_sem_acento(opcao)):
        return True
    enunciado = _sem_acento(pergunta)
    if _FALA_DE_PAR_ORDENADO.search(enunciado):
        return False
    return bool(_FALA_DE_RAIZ.search(enunciado))


def conjunto_raizes_quadraticas(texto: str, pergunta: str = "") -> tuple[float, float] | None:
    texto_norm = str(texto or "").lower()
    numeros = re.findall(_PADRAO_NUMERO, texto_norm)
    if len(numeros) != 2:
        return None
    if _PAR_ORDENADO.search(texto_norm) and not _par_entre_parenteses_e_raiz(texto_norm, pergunta):
        return None
    tem_marcador = any(
        marcador in texto_norm for marcador in ("x'", "x''", "raiz", "raizes", "raízes", "solu", "(", "{")
    )
    if not tem_marcador:
        # MELHORIA: bug visto em producao -- opcoes como "-3 e -2" e "-2 e
        # -3" (mesmo par, ordem trocada) apareciam como duas alternativas
        # DIFERENTES na mesma questao (visto ao vivo: Bhaskara de
        # x^2+5x+6=0). O formato realmente gerado pelo app pra respostas
        # de duas raizes e so "N e M", sem nenhuma das palavras-marcadoras
        # acima -- entao esta funcao nunca reconhecia o par e a checagem de
        # equivalencia (tem_opcoes_equivalentes) nunca disparava. Aceita
        # tambem quando o texto e SO os dois numeros ligados por um
        # conector simples (e/ou/and/virgula), sem mais nenhuma palavra —
        # isso evita falso positivo em textos onde 2 numeros aparecem por
        # acaso com outro sentido (ex: "entre 2 e 5 dias", que sobra
        # "entre"/"dias" depois de tirar os numeros e os conectores).
        texto_residual = _PADRAO_CONECTOR_RESIDUAL.sub("", re.sub(_PADRAO_NUMERO, "", texto_norm))
        if texto_residual.strip():
            return None

    return tuple(sorted(_numero(numero) for numero in numeros))


def respostas_equivalentes(resposta_aluno: str, resposta_correta: str, pergunta: str = "") -> bool:
    if str(resposta_aluno).strip() == str(resposta_correta).strip():
        return True

    raizes_aluno = conjunto_raizes_quadraticas(resposta_aluno, pergunta)
    raizes_correta = conjunto_raizes_quadraticas(resposta_correta, pergunta)
    return bool(raizes_aluno and raizes_aluno == raizes_correta)


def tem_opcoes_equivalentes(opcoes: list[str], pergunta: str = "") -> bool:
    vistas = set()
    for opcao in opcoes or []:
        chave = conjunto_raizes_quadraticas(str(opcao), pergunta)
        if chave is None:
            continue
        if chave in vistas:
            return True
        vistas.add(chave)
    return False
