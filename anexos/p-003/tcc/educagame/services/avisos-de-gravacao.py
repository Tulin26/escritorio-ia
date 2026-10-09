"""Motivos de recusa que a tela descobre antes de ir ao banco.

Os que so o banco descobre (sem conexao, recusada, nao encontrada) moram em
repositories/gravacao.py. Cada assunto -- matricula, aventura, escola,
preferencias -- tem o seu mapa motivo -> texto, porque "nao foi encontrada"
diz coisas diferentes para uma aventura e para uma escola.
"""

from __future__ import annotations

FALTA_ESCOLA = "sem_escola"
FALTAM_DADOS = "sem_dados"
CONFIRMACAO_INVALIDA = "confirmacao_invalida"
