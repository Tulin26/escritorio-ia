from __future__ import annotations

from typing import Any
import re

from services.ia.base import _passo as _passo_base

def _nivel(nivel: str) -> str:
    return str(nivel or "").lower()


_CORRECOES_PT = {
    "conteudo": "conteúdo",
    "calculo": "cálculo",
    "matematica": "matemática",
    "fisica": "física",
    "quimica": "química",
    "numero": "número",
    "numeros": "números",
    "operacao": "operação",
    "operacoes": "operações",
    "basica": "básica",
    "basicas": "básicas",
    "fracao": "fração",
    "fracoes": "frações",
    "raiz": "raiz",
    "raizes": "raízes",
    "equacao": "equação",
    "equacoes": "equações",
    "funcao": "função",
    "funcoes": "funções",
    "formula": "fórmula",
    "resolucao": "resolução",
    "divisao": "divisão",
    "variavel": "variável",
    "variaveis": "variáveis",
    "sao": "são",
    "triangulo": "triângulo",
    "retangulo": "retângulo",
    "angulo": "ângulo",
    "area": "área",
    "razao": "razão",
    "posicao": "posição",
    "progressao": "progressão",
    "aritmetica": "aritmética",
    "sequencia": "sequência",
    "padrao": "padrão",
    "oraculo": "oráculo",
    "grimorio": "grimório",
    "movel": "móvel",
    "cinematica": "cinemática",
    "aceleracao": "aceleração",
    "velocidade media": "velocidade média",
    "forca": "força",
    "forcas": "forças",
    "mecanico": "mecânico",
    "eletrica": "elétrica",
    "eletricos": "elétricos",
    "tensao": "tensão",
    "resistencia": "resistência",
    "circuitos eletricos": "circuitos elétricos",
    "espaco": "espaço",
    "salao": "salão",
    "atencao": "atenção",
    "solucao": "solução",
    "solucoes": "soluções",
    "concentracao": "concentração",
    "hidrogenionica": "hidrogeniônica",
    "substancia": "substância",
    "relacao": "relação",
    "laboratorio": "laboratório",
    "materia": "matéria",
    "balanca": "balança",
    "necessaria": "necessária",
    "agua": "água",
    "especifico": "específico",
    "variacao": "variação",
    "termoquimica": "termoquímica",
    "equilibrio": "equilíbrio",
    "acidos": "ácidos",
    "acido": "ácido",
    "reacoes": "reações",
    "periodica": "periódica",
    "quimicos": "químicos",
    "ph": "pH",
}


_CORRECOES_FRASES_PT = {
    "qual e": "qual é",
    "a velocidade media e": "a velocidade média é",
    "a forca resultante e": "a força resultante é",
    "a concentracao e": "a concentração é",
    "a quantidade de materia e": "a quantidade de matéria é",
    "a area e": "a área é",
    "o resultado e": "o resultado é",
    "o trabalho realizado e": "o trabalho realizado é",
    "o ph e": "o pH é",
    " e R$": " é R$",
    " e obtida": " é obtida",
    " e encontrada": " é encontrada",
    " e necessaria": " é necessária",
    " e a taxa": " é a taxa",
    " e o valor": " é o valor",
    " e a area": " é a área",
    " e a base": " é a base",
    " e a altura": " é a altura",
    " e o primeiro": " é o primeiro",
    " e a razao": " é a razão",
    " e a posicao": " é a posição",
    " e a corrente": " é a corrente",
    " e a forca": " é a força",
    " e o deslocamento": " é o deslocamento",
    " e o calor": " é o calor",
    " e a quantidade": " é a quantidade",
    " e a massa": " é a massa",
    " e a aceleracao": " é a aceleração",
    " sao ": " são ",
}


def _manter_capitalizacao(texto: str, original: str) -> str:
    if not original.strip()[:1].isupper():
        return texto
    indice = len(texto) - len(texto.lstrip())
    return f"{texto[:indice]}{texto[indice:indice + 1].upper()}{texto[indice + 1:]}"


def _texto_pt(texto: str) -> str:
    texto_corrigido = str(texto or "")
    for bruto, correto in _CORRECOES_FRASES_PT.items():
        texto_corrigido = re.sub(
            re.escape(bruto),
            lambda m, valor=correto: _manter_capitalizacao(valor, m.group(0)),
            texto_corrigido,
            flags=re.IGNORECASE,
        )
    texto_corrigido = re.sub(
        r"\b(O\s+\d+o\s+termo)\s+e\b",
        lambda m: f"{m.group(1)} é",
        texto_corrigido,
        flags=re.IGNORECASE,
    )
    for bruto, correto in sorted(_CORRECOES_PT.items(), key=lambda item: len(item[0]), reverse=True):
        texto_corrigido = re.sub(
            rf"\b{re.escape(bruto)}\b",
            lambda m, valor=correto: _manter_capitalizacao(valor, m.group(0)),
            texto_corrigido,
            flags=re.IGNORECASE,
        )
    return texto_corrigido


def _passo(titulo: str, conteudo: str, final: bool = False) -> dict[str, Any]:
    return _passo_base(_texto_pt(titulo), _texto_pt(conteudo), final)


def gerar_desafio_exatas(
    materia: str,
    tema: str,
    nivel: str,
    contexto: str = "lab",
    evitar_ids: list[str] | set[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    from services.banks.laboratorio import gerar_desafio_laboratorio_offline

    desafio = gerar_desafio_laboratorio_offline(materia, tema, nivel, evitar_ids=evitar_ids)
    if contexto:
        desafio["contexto"] = contexto
    return desafio
