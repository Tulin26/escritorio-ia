"""O conteúdo da ajuda, num lugar só.

Por que este módulo existe
--------------------------
A única documentação do EducaGame era um PDF **fora** do sistema, entregue à
mão. Isso falha a décima heurística de Nielsen por dois lados: o aluno que
trava no meio de uma questão não tem onde olhar, e quem tem o PDF pode estar
lendo uma versão velha.

Já houve um episódio disso: o guia de acesso envelheceu em três pontos e
mandava o leitor para o lugar errado logo na primeira tela, porque era um
arquivo avulso sem fonte no repositório. A correção foi um gerador com teste
(`scripts/gerar_guia_acesso.py`, `tests/test_guia_de_acesso.py`).

Escrever agora um texto de ajuda **novo**, dentro do app, repetiria o erro
noutra forma: seriam duas descrições dos mesmos oito modos, e a segunda vez
que alguém mexesse numa delas as duas passariam a discordar. Então o conteúdo
mora aqui, sem marcação, e cada lugar aplica a sua:

- o PDF (`scripts/gerar_guia_acesso.py`) embrulha em `<b>` para o ReportLab;
- a tela do Flask (`web/templates/ajuda.html`) e a do Streamlit renderizam
  como HTML.

Sem marcação de propósito: `<b>` no meio da frase é o que impede o mesmo
texto de servir aos dois.
"""

from __future__ import annotations

ENDERECO = "educagame.onrender.com"
URL_LIMPA = f"https://{ENDERECO}/"


# ====================== COMO ENTRAR ======================
#
# A ordem importa, e é a razão de o guia antigo travar: escola e código vêm
# ANTES do usuário e da senha.

def passos_de_entrada(nome_escola: str = "", codigo: str = "") -> list[str]:
    """Os quatro passos da tela de entrada, em texto puro."""
    escola = nome_escola or "a sua escola"
    codigo_txt = codigo or "o código da sua escola"
    return [
        f"Abra {URL_LIMPA} no navegador do computador ou do celular.",
        f"Na lista de escolas, escolha {escola}.",
        f"Digite {codigo_txt}. Ele não é uma senha — é o combinado que evita "
        "entrar na unidade errada por engano, e o professor passa para a turma.",
        "Só então informe o seu usuário e a sua senha.",
    ]


# ====================== O QUE PODE ASSUSTAR ======================
#
# As três coisas que parecem defeito e não são. Estar na ajuda é o que
# transforma "travou" em "ah, é assim mesmo".

TEXTO_ESPERA = (
    "O servidor fica em repouso quando ninguém usa o sistema por cerca de 15 minutos. "
    "A primeira página depois desse repouso pode levar até um minuto para carregar. "
    "Isso é normal e não é erro — da segunda tela em diante a navegação fica rápida."
)

TEXTO_SESSAO = (
    "Se ficar {minutos} minutos sem clicar em nada, o sistema encerra a sessão e devolve "
    "à tela de escolher a escola, com um aviso explicando. Em sala isso protege o "
    "computador compartilhado; é só repetir os passos de entrada."
)

TEXTO_QUESTOES = (
    "As questões são geradas por inteligência artificial e passam por uma verificação "
    "automática antes de chegar à tela: a alternativa marcada como correta precisa bater "
    "com a resolução apresentada. Quando a geração falha ou demora demais, o sistema usa "
    "um banco próprio com mais de 50 mil questões já revisadas. Na prática, a atividade "
    "nunca fica indisponível para o aluno."
)

TEXTO_SENHA = (
    "Quem tem e-mail cadastrado pode pedir uma senha nova pela própria tela de login, "
    "em “Esqueci minha senha”. Quem entrou com usuário criado pelo professor pede a ele: "
    "o painel do professor gera uma senha nova na hora."
)


# ====================== OS MODOS ======================

MODOS = [
    (
        "Estudar",
        [
            ("Treino Rápido", "Questões em sequência, por matéria e tema, com controle de acertos. É o modo mais direto e o melhor ponto de partida."),
            ("ENEM", "Simulado no formato da prova, com revisão e desempenho separado por área."),
            ("Laboratório de Exatas", "Problemas de cálculo com fórmula, resolução passo a passo e aplicação no dia a dia. No Ensino Médio cobre Matemática, Física e Química."),
        ],
    ),
    (
        "Modos de jogo",
        [
            ("Desafio do Oráculo", "Questões conceituais apresentadas como enigma, escolhidas por matéria, tema e dificuldade. Cobra entendimento, não conta."),
            ("RPG", "Campanha em fases, com chefes, pontos de experiência, escolhas e recompensas. O professor pode configurar a aventura pelo painel."),
            ("Escape Room", "Salas em sequência: cada acerto libera a próxima. Ao final, um relatório do que precisa ser revisto."),
            ("Batalha contra Chefes", "Chefes por área do ENEM, com vidas e pontuação por acerto. Formato mais competitivo, bom para fechar um conteúdo."),
        ],
    ),
    (
        "Turma e acompanhamento",
        [
            ("Perfil do Aluno", "Conquistas, pontos, sequência de acertos e desempenho geral."),
            ("Meu Progresso", "Histórico recente e aproveitamento por matéria."),
            ("Batalha de Guildas", "Duelo semanal entre turmas, medindo participação e acertos."),
        ],
    ),
]


# ====================== O PAINEL DO PROFESSOR ======================

PAINEL_PROFESSOR = [
    ("Desempenho dos Alunos", "Total de questões respondidas, erros e percentual de acerto da turma. Dá para abrir um aluno específico e ver o desempenho dele por matéria."),
    ("Ranking dos Alunos", "Classificação por questões respondidas, acertos e pontos."),
    ("Resumo da Turma", "Visão consolidada: quantos alunos, quantas questões, média de acerto e tempo médio por questão — e o mesmo recorte por matéria."),
    ("Professores", "Quem está cadastrado e em que escola cada um entra. O professor vê a própria escola; o desenvolvedor vê todas."),
    ("Configurar Aventura RPG", "Define o conteúdo da campanha de RPG que a turma vai jogar."),
    ("Matrícula de Novo Aluno", "Cadastra um aluno na hora, gerando usuário e senha. É por aqui que a turma inteira entra no sistema."),
    ("Contas de Login", "Lista as contas de professor, vincula cada uma à sua escola e gera senha nova. Conta sem escola aparece marcada, porque ela não entra em lugar nenhum."),
]


def secoes_da_ajuda(minutos_sessao: int, eh_professor: bool = False) -> list[dict]:
    """A ajuda montada, pronta para a tela.

    O prazo da sessão é PERGUNTADO ao código (core/sessao.py) e não escrito
    aqui: foi assim que o guia antigo passou a mentir -- alguém escreveu um
    número, o código mudou embaixo e não havia nada que reclamasse.

    O painel do professor só entra para quem é professor: pôr na ajuda do
    aluno uma seção que ele não consegue abrir é ruído, e ruído é o que faz
    ninguém ler a ajuda da próxima vez.
    """
    secoes = [
        {
            "id": "entrar",
            "titulo": "Como entrar",
            "itens": [(f"Passo {i}", texto) for i, texto in enumerate(passos_de_entrada(), 1)],
        },
        {
            "id": "modos",
            "titulo": "O que dá para fazer",
            "itens": [item for _, itens in MODOS for item in itens],
        },
        {
            "id": "duvidas",
            "titulo": "Parece defeito, mas não é",
            "itens": [
                ("A primeira tela demorou muito", TEXTO_ESPERA),
                ("Fui devolvido para a tela de escolher escola", TEXTO_SESSAO.format(minutos=minutos_sessao)),
                ("De onde vêm as questões", TEXTO_QUESTOES),
                ("Esqueci a minha senha", TEXTO_SENHA),
            ],
        },
    ]
    if eh_professor:
        secoes.append(
            {"id": "professor", "titulo": "Painel do professor", "itens": list(PAINEL_PROFESSOR)}
        )
    return secoes
