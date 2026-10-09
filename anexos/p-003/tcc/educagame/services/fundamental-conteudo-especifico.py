"""Banco de conteudo especifico para o Ensino Fundamental offline.

MELHORIA: o banco EF (services/banks/fundamental.py) gerava 100% das
questoes por template generico -- o mesmo padrao meta-cognitivo que ja
foi substituido no Ensino Medio (ver oraculo_conteudo_especifico.py).
As perguntas eram do tipo "Qual analise e mais adequada para estudar
{tema}?", com alternativas como "Responder por palpite" e "Escolher a
alternativa mais curta": nao testavam conteudo nenhum, so trocavam o
nome do tema. Medido antes: 120 perguntas distintas no EF inteiro, com
Filosofia e Sociologia tendo apenas 4 cada.

Este modulo traz perguntas reais, verificadas, para os temas de
TEMAS_RPG[materia]["EF"]. Temas sem entrada aqui continuam caindo no
template generico -- nada quebra, a cobertura so cresce.

Linguagem calibrada para 6o a 9o ano: enunciados curtos, contextos
concretos e contas conferidas uma a uma.

Sobre as materias cobertas: no Ensino Fundamental a BNCC tem "Ciencias"
como materia unica -- Fisica, Quimica e Biologia so se separam no Ensino
Medio, e Filosofia e Sociologia tambem sao exclusivas do EM. O app ja
respeita isso: filtrar_materias_por_serie() (core/config.py) nunca
oferece essas 5 a um aluno do EF, que ve apenas 9 materias.

Ainda assim ha conteudo aqui para essas 5, de proposito: o proprio banco
EF define as tres ciencias como apelidos de Ciencias nesse nivel (veja
PERFIS_EF em services/banks/fundamental.py, que mapeia Fisica, Quimica e
Biologia para o mesmo codigo EF07CI). Se algum caminho do codigo pedir
"Fisica" para um aluno do EF, ele recebe conteudo de Ciencias no nivel
certo em vez de cair no template generico. E rede de seguranca, nao
curriculo -- o aluno nunca chega nelas pelo fluxo normal.

Formato de cada pergunta (identico ao do EM):
{
    "pergunta": str,
    "opcoes": [str, str, str, str],   # a correta sempre no indice 0
    "correta": int,                    # sempre 0; o banco embaralha depois
    "explicacao": [{"tipo": "bold"|"texto"|"resultado", "conteudo": str}, ...],
}

Os dados moram em data/banco_especifico_ef.json (ver core/dados.py); este modulo
so os le, uma vez, na importacao.
"""

from __future__ import annotations

from core.dados import ler_json

BANCO_ESPECIFICO_EF: dict[str, dict[str, list[dict]]] = ler_json("banco_especifico_ef.json")
