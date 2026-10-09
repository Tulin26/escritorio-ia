"""
Banco de conteudo especifico para o Oraculo offline.

MELHORIA: as perguntas offline do Oraculo eram geradas por um template
generico compartilhado entre as 14 materias (ver PERGUNTAS_REALISTAS em
flask_offline_bank.py), que nunca testava conteudo de verdade — so pedia
para o aluno julgar "qual leitura conceitual e mais adequada", trocando
so o nome do tema. Este arquivo comeca a substituir isso por perguntas
reais, verificadas, especificas de cada tema.

Cobertura inicial: os 3 primeiros temas de cada uma das 14 materias
(os mais foundacionais em cada lista de TEMAS_BASE_EM), com 2 perguntas
por tema. Temas sem entrada aqui continuam caindo no banco generico —
nada quebra, a cobertura so cresce com o tempo.

Formato de cada pergunta:
{
    "pergunta": str,
    "opcoes": [str, str, str, str],
    "correta": int (indice 0-3),
    "explicacao": [{"tipo": "bold"|"texto"|"resultado", "conteudo": str}, ...],
}

Os dados moram em data/banco_especifico_em.json (ver core/dados.py); este modulo
so os le, uma vez, na importacao.
"""

from __future__ import annotations

from core.dados import ler_json

BANCO_ESPECIFICO_EM: dict[str, dict[str, list[dict]]] = ler_json("banco_especifico_em.json")
