"""De onde veio a questão, e o que dizer ao aluno quando não veio da IA.

A nona heurística de Nielsen: ajudar a reconhecer, diagnosticar e se recuperar
de um erro. Aqui o "erro" é a geração por IA ter falhado -- e o aluno não era
avisado em metade dos modos.

Medido antes de mexer, nos oito modos do Flask:

    Oráculo, Treino, Laboratório, RPG   avisavam
    ENEM                                mostrava uma pílula escrita "offline"
    Boss Rush                           montava o rótulo e não o mostrava
    Escape Room                         guardava o aviso no estado e não o passava
    Guildas                             não gera questão

Ou seja: três modos faziam o trabalho e jogavam fora na última etapa.

E havia DOIS marcadores para a mesma coisa -- `_origem_geracao` (Laboratório,
RPG, cálculo) e `_origem` (ENEM, Boss Rush) --, o que é como o aviso do ENEM
acabou virando uma pílula em vez de uma frase. Este módulo entende os dois e
é a única fonte da mensagem, para os dois frontends.
"""

from __future__ import annotations

# MELHORIA: a frase era "A IA não retornou uma questão válida agora. Usei o
# banco offline para manter o treino funcionando." Três problemas para quem
# lê com 15 anos, no meio de uma atividade valendo nota:
#
#   - "Usei" -- quem é "eu"?
#   - "banco offline" é jargão nosso, não do aluno;
#   - e, principalmente, ela conta o problema e não diz o que fazer. O aluno
#     fica sem saber se a questão vale, se deve responder, se deu errado.
#
# A nona heurística pede linguagem simples, o problema indicado com precisão e
# uma saída construtiva. A questão do banco é revisada e vale pontos igual --
# dizer isso é o que transforma um susto em informação.
AVISO_BANCO_PROPRIO = (
    "Esta questão veio do banco de questões do próprio EducaGame, já revisado — "
    "a geração por inteligência artificial não respondeu a tempo. "
    "Pode responder normalmente: a questão vale pontos como qualquer outra."
)

# Os dois nomes que o projeto usa para a mesma informação.
_CAMPOS_DE_ORIGEM = ("_origem_geracao", "_origem")


def veio_do_banco_proprio(questao) -> bool:
    """A questão foi servida pelo banco offline, e não pela IA."""
    if not isinstance(questao, dict):
        return False
    for campo in _CAMPOS_DE_ORIGEM:
        if str(questao.get(campo, "") or "").strip().lower() == "offline":
            return True
    return False


def aviso_de_origem(questao, erro_ia: str = "") -> str:
    """A frase para o aluno, ou string vazia quando não há o que avisar.

    `erro_ia` é o último erro da cascata (services/ia_service.py). Ele conta
    como sinal porque nem todo caminho de fallback marca a questão: o erro
    existir já significa que a IA não entregou.
    """
    if veio_do_banco_proprio(questao) or str(erro_ia or "").strip():
        return AVISO_BANCO_PROPRIO
    return ""
