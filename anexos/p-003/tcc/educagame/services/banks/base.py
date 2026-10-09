"""Infraestrutura comum dos bancos de questoes offline.

Os bancos (EM, EF/fundamental, RPG, laboratorio) compartilhavam a mesma
maquinaria: normalizar texto para busca, embaralhar alternativas de forma
deterministica e carregar as questoes de cada materia sob demanda (lazy).
Este modulo concentra essas pecas para evitar copias divergentes.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any, Callable, Iterable

from core.config import normalizar_materia
from core.text_cleanup import chave_busca  # re-exportado para os bancos


# MELHORIA: contador de quantas vezes cada combinacao (materia|tema|nivel)
# ja foi pedida neste processo. Sem ele, a selecao era totalmente
# determinada pelo hash do seed, entao TODA nova sessao comecava com a
# mesma questao: medido no banco real, 5 sessoes seguidas de Treino de
# Matematica abriam as cinco com "Qual e a mediana do conjunto {3, 7, 5,
# 9, 1}?". O historico de evitar_ids nao ajudava nisso, porque ele nasce
# vazio a cada sessao nova (ver "historico": [] em web/routes/treino_fla.py).
# Mesma solucao ja usada pelo banco do Laboratorio (_CICLO_OFFLINE em
# services/banks/laboratorio.py), que por isso nao tinha esse problema.
_CICLO_SELECAO: dict[str, int] = {}


def selecionar_questao_offline(
    questoes: list[dict[str, Any]],
    tema: str,
    seed: str,
    evitar_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Escolhe uma questao do banco evitando repetir o que o aluno ja viu.

    MELHORIA: dois problemas medidos no banco real, que faziam o aluno ver
    a mesma pergunta varias vezes numa mesma sessao mesmo havendo dezenas
    de questoes distintas disponiveis:

    1. A exclusao era so por ``id_offline``, mas o banco repete a MESMA
       pergunta em varias entradas com ids diferentes (ex: 40 copias de
       uma questao de Filosofia EM, ids EM-Filosofia-001/-003/-005...).
       Filtrar so por id deixava a copia seguinte passar limpa. Agora
       resolve os ids ja vistos para os TEXTOS deles e exclui qualquer
       questao com texto repetido.
    2. O indice saia de ``hash(seed) % len(candidatas)`` com um seed fixo
       (materia|tema|nivel). Como o seed nao mudava conforme o aluno
       respondia, a variacao acontecia so por efeito colateral de a lista
       encolher e o resto da divisao cair em outro lugar -- por isso
       Matematica EM repetia ja na 2a questao, com 49 outras disponiveis.
       Incluir a quantidade de questoes ja vistas no seed faz a selecao
       andar de verdade, e evita travar numa unica questao quando o
       conteudo distinto acaba e e preciso reaproveitar o banco.
    """
    tema_busca = chave_busca(tema)
    candidatas = [
        questao
        for questao in questoes
        if tema_busca and tema_busca in chave_busca(questao.get("tema_usado", ""))
    ] or questoes

    evitar = {str(item) for item in (evitar_ids or []) if str(item).strip()}
    textos_vistos = {
        str(questao.get("pergunta", "")).strip()
        for questao in questoes
        if str(questao.get("id_offline", "")) in evitar
    }
    livres = [
        questao
        for questao in candidatas
        if str(questao.get("id_offline", "")) not in evitar
        and str(questao.get("pergunta", "")).strip() not in textos_vistos
    ]
    if livres:
        candidatas = livres

    # MELHORIA: o banco guarda a mesma pergunta em varias entradas (40
    # copias por questao no EM, 50 no EF), e copias identicas ficam em
    # posicoes vizinhas. Sortear um indice dentro dessa lista com repeticao
    # fazia a selecao "andar" entre copias iguais em vez de entre questoes
    # diferentes -- com isso, 5 sessoes novas rendiam so 2 enunciados
    # distintos. Seleciona sobre a lista sem duplicatas de enunciado.
    vistas: set[str] = set()
    distintas: list[dict[str, Any]] = []
    for questao in candidatas:
        texto = str(questao.get("pergunta", "")).strip()
        if texto in vistas:
            continue
        vistas.add(texto)
        distintas.append(questao)
    if distintas:
        candidatas = distintas

    ciclo = _CICLO_SELECAO.get(seed, 0)
    _CICLO_SELECAO[seed] = ciclo + 1
    semente = f"{seed}|{len(evitar)}"
    offset = int(hashlib.sha256(semente.encode("utf-8")).hexdigest(), 16)
    idx = (offset + ciclo) % len(candidatas)
    return deepcopy(candidatas[idx])


def embaralhar(correta: str, distratores: list[str], indice: int) -> tuple[list[str], int]:
    """Monta as alternativas e rotaciona de forma deterministica pelo indice."""
    opcoes = [correta, *distratores[:3]]
    giro = indice % len(opcoes)
    opcoes = opcoes[giro:] + opcoes[:giro]
    return opcoes, opcoes.index(correta)


def bncc_da_materia(materia: str) -> dict[str, str]:
    """Area, competencia, habilidade e codigo -- da mesma tabela do banco EM.

    Era copiado igual em laboratorio.py e rpg.py. Importado aqui dentro para
    nao criar dependencia de modulo no import: os dois bancos sao carregados
    no boot dos dois frontends.
    """
    try:
        from services.banks.em import BNCC_REFERENCIAS, HABILIDADES_BNCC

        area, competencia, codigo = BNCC_REFERENCIAS.get(
            materia, BNCC_REFERENCIAS["Ciencias"]
        )
        return {
            "area_bncc": area,
            "competencia_bncc": competencia,
            "habilidade_bncc": HABILIDADES_BNCC.get(materia, ""),
            "codigo_bncc": codigo,
        }
    except Exception:
        return {}


class LazyMateriaBank(dict):
    """Banco de questoes por materia, gerado sob demanda e cacheado.

    - ``materias``: chaves aceitas pelo banco.
    - ``gerar``: funcao que produz a lista de questoes de uma materia.
    - ``fallback``: materia usada quando a pedida nao existe; se ``None``,
      materias desconhecidas retornam lista vazia.
    """

    def __init__(self, materias: Iterable[str], gerar: Callable[[str], list[Any]], fallback: str | None = None):
        super().__init__({materia: None for materia in materias})
        self._gerar = gerar
        self._fallback = fallback

    def _carregar(self, materia: str) -> list[Any]:
        materia_norm = normalizar_materia(materia) or (self._fallback or "")
        if materia_norm not in self:
            if self._fallback is None:
                return []
            materia_norm = self._fallback
        if dict.get(self, materia_norm) is None:
            dict.__setitem__(self, materia_norm, self._gerar(materia_norm))
        return dict.__getitem__(self, materia_norm)

    def __getitem__(self, materia: str) -> list[Any]:
        return self._carregar(materia)

    def get(self, materia: str, default: Any = None):
        materia_norm = normalizar_materia(materia)
        if self._fallback is not None:
            materia_norm = materia_norm or self._fallback
        if materia_norm in self:
            return self._carregar(materia_norm)
        return default
