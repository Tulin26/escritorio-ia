from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.config import MATERIAS, TEMAS_RPG, get_area_da_materia, normalizar_materia
from services.banks._base import (
    LazyMateriaBank,
    chave_busca as _chave_busca,
    embaralhar as _embaralhar_opcoes,
    selecionar_questao_offline,
)
from services.fundamental_conteudo_especifico import BANCO_ESPECIFICO_EF


QUESTOES_EF_POR_TEMA = 50


PERFIS_EF = {
    "Matematica": (
        "resolver problemas, reconhecer padroes e usar representacoes matematicas",
        "identificar dados, relacoes entre grandezas e a estrategia adequada antes da conta",
        "EF07MA",
    ),
    "Ciencias": (
        "investigar fenomenos naturais com observacao, comparacao e evidencias",
        "relacionar causa, consequencia e dados observados para explicar o fenomeno",
        "EF07CI",
    ),
    "Portugues": (
        "interpretar textos, generos, finalidade e efeitos de sentido",
        "ler o comando, localizar pistas no texto e justificar a alternativa pelo contexto",
        "EF69LP",
    ),
    "Historia": (
        "analisar fontes, sujeitos historicos, permanencias e mudancas",
        "relacionar acontecimentos ao tempo, ao espaco e aos grupos sociais envolvidos",
        "EF07HI",
    ),
    "Geografia": (
        "compreender paisagens, territorio, mapas e relacoes sociedade-natureza",
        "observar escala, localizacao e impactos sociais ou ambientais",
        "EF07GE",
    ),
    "Ingles": (
        "understand simple texts, vocabulary and communicative purpose",
        "use context clues, genre and known words to infer meaning",
        "EF07LI",
    ),
    "Educacao Fisica": (
        "compreender praticas corporais, regras, cooperacao, saude e inclusao",
        "analisar participacao, seguranca, estrategia e respeito nas praticas corporais",
        "EF67EF",
    ),
    "Arte": (
        "interpretar linguagens artisticas, materialidades e patrimonio cultural",
        "observar forma, intencao, contexto e modo de expressao da obra",
        "EF69AR",
    ),
    "Ensino Religioso": (
        "reconhecer diversidade religiosa, valores, simbolos e convivencia respeitosa",
        "comparar tradicoes com respeito, sem hierarquizar crencas",
        "EF09ER",
    ),
    "Fisica": (
        "explicar fenomenos de energia, movimento, luz, som e eletricidade",
        "identificar grandezas e principios fisicos em situacoes observaveis",
        "EF07CI",
    ),
    "Quimica": (
        "relacionar materiais, misturas, propriedades e transformacoes",
        "observar evidencias e propriedades antes de classificar o fenomeno",
        "EF07CI",
    ),
    "Biologia": (
        "compreender seres vivos, corpo humano, saude e ecossistemas",
        "usar evidencias biologicas para explicar relacoes entre vida e ambiente",
        "EF07CI",
    ),
}


CENARIOS_EF = {
    "Matematica": ["uma feira da escola", "um jogo com pontuacao", "uma planta baixa simples", "uma tabela de pesquisa da turma"],
    "Ciencias": ["uma horta escolar", "um experimento em sala", "uma campanha de saude", "uma observacao do patio"],
    "Portugues": ["um bilhete escolar", "uma noticia curta", "uma tirinha", "uma campanha de convivencia"],
    "Historia": ["uma fonte historica simples", "um relato de familia", "uma linha do tempo", "uma imagem de museu"],
    "Geografia": ["um mapa do bairro", "uma paisagem fotografada", "uma rota ate a escola", "um grafico de populacao"],
    "Ingles": ["a short classroom dialogue", "a poster", "a simple comic strip", "a school notice"],
    "Educacao Fisica": ["um jogo coletivo", "uma atividade adaptada", "uma aula de alongamento", "um torneio da turma"],
    "Arte": ["uma pintura observada em aula", "uma musica regional", "uma cena teatral", "um grafite no bairro"],
    "Ensino Religioso": ["uma roda de conversa", "um simbolo cultural", "uma festa comunitaria", "um caso de respeito"],
}


def _nivel(indice: int) -> str:
    return ("Facil", "Medio", "Dificil")[indice % 3]


# O que `habilidade_bncc` passa a guardar no Fundamental: a descricao, e nao
# o codigo. Mesmos criterios da tabela do Ensino Medio (services/banks/em.py):
# sao RESUMOS do sentido, e nao transcricao literal -- o texto oficial esta no
# link que cada questao ja carrega em `fonte_bncc`.
HABILIDADES_BNCC_EF = {
    "Matematica": "Resolver problemas do cotidiano reconhecendo padrões, grandezas e operações.",
    "Fisica": "Investigar fenômenos físicos do dia a dia relacionando causa, efeito e medida.",
    "Quimica": "Reconhecer materiais, misturas e transformações presentes no cotidiano.",
    "Biologia": "Compreender os seres vivos, seus sistemas e as relações com o ambiente.",
    "Portugues": "Ler, interpretar e produzir textos adequados à situação de comunicação.",
    "Historia": "Compreender processos históricos e suas marcas no presente.",
    "Geografia": "Ler o espaço geográfico, relacionando sociedade, natureza e território.",
    "Ingles": "Compreender e usar a língua inglesa em situações simples de comunicação.",
    "Ciencias": "Investigar fenômenos naturais e tecnológicos com base em evidências.",
    "Educacao Fisica": "Experimentar e compreender práticas corporais, seus sentidos e regras.",
    "Arte": "Explorar e apreciar linguagens artísticas, reconhecendo formas de expressão.",
    "Filosofia": "Formular perguntas e argumentar sobre questões do convívio e da existência.",
    "Sociologia": "Reconhecer formas de organização social e a diversidade cultural.",
    "Ensino Religioso": "Respeitar a diversidade de crenças e o direito à liberdade de consciência.",
}


def _perfil(materia: str) -> tuple[str, str, str]:
    return PERFIS_EF.get(materia, PERFIS_EF["Ciencias"])


def _cenarios(materia: str) -> list[str]:
    return CENARIOS_EF.get(materia, CENARIOS_EF["Ciencias"])


def _modelo_matematica(tema: str, indice: int) -> tuple[str, str, list[str], int, str]:
    tema_norm = _chave_busca(tema)
    if "potencia" in tema_norm or "raiz" in tema_norm:
        pergunta = "Em Matemática, qual afirmação descreve corretamente a relação entre potências e raízes quadradas?"
        correta = "A raiz quadrada de um quadrado perfeito indica o número que, multiplicado por ele mesmo, gera esse valor."
        distratores = [
            "Toda raiz quadrada aumenta o número original.",
            "Potência e raiz quadrada são sempre operações sem relação entre si.",
            "A raiz quadrada de qualquer número natural é sempre outro número natural.",
        ]
        conceito = "Raiz quadrada e potenciação são operações relacionadas quando pensamos em quadrados perfeitos."
    elif "porcent" in tema_norm:
        pergunta = "Ao interpretar um desconto de 20%, o que essa porcentagem representa?"
        correta = "Representa 20 partes de cada 100 partes do valor inicial."
        distratores = [
            "Representa sempre uma retirada de 20 reais.",
            "Representa dobrar o valor inicial antes da compra.",
            "Representa dividir qualquer preço exatamente por 20.",
        ]
        conceito = "Porcentagem compara uma parte com um todo dividido em 100 partes."
    elif "fraco" in tema_norm or "decimal" in tema_norm:
        pergunta = "O que o denominador de uma fração indica em uma situação de partilha?"
        correta = "Indica em quantas partes iguais o inteiro foi dividido."
        distratores = [
            "Indica sempre quantas partes sobraram.",
            "Indica o resultado de uma multiplicação.",
            "Indica que a fração precisa ser maior que 1.",
        ]
        conceito = "Fração representa parte de um inteiro dividido em partes iguais."
    elif "equac" in tema_norm:
        pergunta = "Em uma equação do 1º grau, por que fazemos a mesma operação nos dois lados da igualdade?"
        correta = "Para manter a igualdade verdadeira enquanto isolamos a incógnita."
        distratores = [
            "Para mudar o valor da incógnita sem critério.",
            "Para transformar toda equação em multiplicação.",
            "Para eliminar automaticamente todos os números negativos.",
        ]
        conceito = "Resolver equações exige preservar o equilíbrio da igualdade."
    elif "area" in tema_norm:
        pergunta = "Qual ideia está ligada ao conceito de área de uma figura plana?"
        correta = "A medida da superfície ocupada pela figura."
        distratores = [
            "A soma dos comprimentos de todos os lados.",
            "A distância entre dois pontos da figura.",
            "A quantidade de vértices da figura.",
        ]
        conceito = "Área mede superfície; perímetro mede contorno."
    elif "perimetro" in tema_norm or "comprimento" in tema_norm:
        pergunta = "Quando calculamos o perímetro de uma figura, o que estamos medindo?"
        correta = "O comprimento total do contorno da figura."
        distratores = [
            "A superfície interna da figura.",
            "O volume ocupado pela figura.",
            "A quantidade de diagonais da figura.",
        ]
        conceito = "Perímetro está associado ao contorno."
    elif "probabilidade" in tema_norm:
        pergunta = "Qual interpretação combina melhor com a ideia de probabilidade?"
        correta = "Ela estima a chance de um acontecimento ocorrer entre os resultados possíveis."
        distratores = [
            "Ela garante exatamente o que vai acontecer em qualquer tentativa.",
            "Ela serve apenas para situações sem resultados possíveis.",
            "Ela elimina a necessidade de comparar casos favoráveis e possíveis.",
        ]
        conceito = "Probabilidade compara casos favoráveis com casos possíveis."
    else:
        pergunta = f"Em um problema sobre {tema}, qual atitude matemática é mais adequada antes de escolher a resposta?"
        correta = "Identificar os dados, a relação entre as grandezas e o conceito envolvido."
        distratores = [
            "Escolher a alternativa com o maior número.",
            "Usar uma operação ao acaso sem ler o comando.",
            "Ignorar unidades, tabelas e informações do enunciado.",
        ]
        conceito = "A interpretação do enunciado orienta a estratégia matemática."
    opcoes, correta_idx = _embaralhar_opcoes(correta, distratores, indice)
    return "O número deixa pistas antes de revelar seu padrão.", pergunta, opcoes, correta_idx, conceito


def _modelo_ciencias(tema: str, indice: int) -> tuple[str, str, list[str], int, str]:
    tema_norm = _chave_busca(tema)
    if "fotossintese" in tema_norm or "planta" in tema_norm:
        pergunta = "Qual descrição explica melhor a fotossíntese?"
        correta = "As plantas usam luz, água e gás carbônico para produzir alimento e liberar oxigênio."
        distratores = [
            "As plantas retiram alimento pronto apenas do solo.",
            "A fotossíntese acontece somente durante a noite.",
            "As plantas produzem gás carbônico como principal produto da fotossíntese.",
        ]
        conceito = "Fotossíntese é um processo de produção de matéria orgânica pelos seres produtores."
    elif "cadeia alimentar" in tema_norm:
        pergunta = "Em uma cadeia alimentar, qual é o papel dos produtores?"
        correta = "Produzir seu próprio alimento e iniciar a passagem de energia no ecossistema."
        distratores = [
            "Decompor todos os organismos antes dos consumidores.",
            "Alimentar-se apenas de animais carnívoros.",
            "Impedir que a energia circule entre os seres vivos.",
        ]
        conceito = "Produtores sustentam a cadeia alimentar por meio da produção de alimento."
    elif "mistura" in tema_norm:
        pergunta = "Como reconhecer uma mistura heterogênea?"
        correta = "Ela apresenta mais de uma fase visível ou perceptível."
        distratores = [
            "Ela sempre tem apenas uma substância pura.",
            "Ela nunca pode ser separada por métodos físicos.",
            "Ela possui obrigatoriamente a mesma aparência em todas as partes.",
        ]
        conceito = "Misturas podem ser classificadas pela quantidade de fases observáveis."
    elif "agua" in tema_norm:
        pergunta = "Por que a água é considerada essencial para os seres vivos?"
        correta = "Porque participa de processos vitais, transporte de substâncias e regulação do organismo."
        distratores = [
            "Porque todos os seres vivos vivem apenas em ambientes aquáticos.",
            "Porque substitui completamente a necessidade de alimento.",
            "Porque impede qualquer troca de calor no corpo.",
        ]
        conceito = "A água participa de muitas funções biológicas e ambientais."
    elif "vacina" in tema_norm:
        pergunta = "Qual é a função principal das vacinas?"
        correta = "Estimular o sistema imunológico a reconhecer agentes causadores de doenças."
        distratores = [
            "Curar instantaneamente qualquer doença já instalada.",
            "Substituir hábitos de higiene e saneamento.",
            "Aumentar a transmissão de doenças contagiosas.",
        ]
        conceito = "Vacinas ajudam o corpo a criar memória imunológica."
    else:
        pergunta = f"Qual explicação científica combina melhor com o estudo de {tema}?"
        correta = "Observar evidências, comparar informações e relacionar causa e consequência."
        distratores = [
            "Aceitar uma explicação sem evidências.",
            "Trocar observação por palpite.",
            "Ignorar dados quando eles contrariam a hipótese inicial.",
        ]
        conceito = "Ciências usa evidências para explicar fenômenos naturais."
    opcoes, correta_idx = _embaralhar_opcoes(correta, distratores, indice)
    return "A natureza responde melhor a quem observa com cuidado.", pergunta, opcoes, correta_idx, conceito


def _modelo_linguagens_humanas(materia: str, tema: str, indice: int) -> tuple[str, str, list[str], int, str]:
    if materia == "Portugues":
        pergunta = f"Em uma questão de Português sobre {tema}, que leitura sustenta melhor a resposta?"
        correta = "A leitura que considera o gênero, o contexto e as pistas do texto."
        distratores = ["A leitura baseada só no título.", "A escolha da frase mais longa.", "A resposta marcada antes de ler o comando."]
        conceito = "Interpretação textual depende de pistas linguísticas e contexto."
        enigma = "Entre linhas e vozes, o sentido se aproxima."
    elif materia == "Ingles":
        pergunta = f"In a text about {tema}, what is the best reading strategy?"
        correta = "Use context clues and known words to infer the meaning."
        distratores = ["Translate one isolated word and ignore the sentence.", "Choose the longest alternative.", "Ignore the text genre and the situation."]
        conceito = "Reading in English requires context, vocabulary and communicative purpose."
        enigma = "Meaning appears when context opens the door."
    elif materia == "Historia":
        pergunta = f"Para estudar {tema} em História, qual cuidado é mais importante?"
        correta = "Relacionar fontes, período histórico, sujeitos envolvidos e mudanças no tempo."
        distratores = ["Julgar o passado apenas com opiniões atuais.", "Ignorar quem produziu a fonte histórica.", "Memorizar datas sem compreender processos."]
        conceito = "História interpreta fontes e processos em seu contexto."
        enigma = "O tempo deixa marcas para quem sabe perguntar."
    elif materia == "Geografia":
        pergunta = f"Em Geografia, como analisar melhor uma situação ligada a {tema}?"
        correta = "Relacionar localização, paisagem, sociedade e transformações do espaço."
        distratores = ["Observar apenas um nome no mapa.", "Separar sociedade e natureza em qualquer análise.", "Ignorar escala, legenda e contexto territorial."]
        conceito = "O espaço geográfico resulta de relações naturais e sociais."
        enigma = "O mapa fala quando o território ganha contexto."
    elif materia == "Educacao Fisica":
        pergunta = f"Em uma prática corporal sobre {tema}, qual atitude favorece aprendizagem e inclusão?"
        correta = "Respeitar regras, adaptar participação quando necessário e cooperar com o grupo."
        distratores = ["Valorizar apenas quem vence.", "Excluir colegas com ritmos diferentes.", "Ignorar segurança e combinados da atividade."]
        conceito = "Educação Física envolve corpo, cultura, saúde, cooperação e respeito."
        enigma = "O movimento ensina quando todos podem participar."
    elif materia == "Arte":
        pergunta = f"Ao interpretar uma produção artística sobre {tema}, o que deve ser considerado?"
        correta = "Materialidade, linguagem, intenção expressiva e contexto cultural."
        distratores = ["Apenas se a obra parece bonita.", "Somente o preço da obra.", "Uma opinião rápida sem observar elementos visuais ou sonoros."]
        conceito = "Arte articula forma, expressão e contexto."
        enigma = "A forma guarda sentidos além da primeira impressão."
    elif materia == "Ensino Religioso":
        pergunta = f"Ao estudar {tema}, qual postura respeita a diversidade religiosa?"
        correta = "Comparar práticas e símbolos sem hierarquizar crenças ou ridicularizar tradições."
        distratores = ["Afirmar que só uma tradição merece estudo.", "Tratar diferenças como erro.", "Usar estereótipos para explicar uma crença."]
        conceito = "Ensino Religioso escolar estuda diversidade, valores e convivência respeitosa."
        enigma = "O respeito abre espaço para compreender diferenças."
    else:
        pergunta = f"Qual análise é mais adequada para estudar {tema}?"
        correta = "Usar conceitos da disciplina e justificar a resposta com evidências do contexto."
        distratores = ["Responder por palpite.", "Escolher a alternativa mais curta.", "Ignorar o comando da questão."]
        conceito = "Uma resposta escolar precisa articular conceito e evidência."
        enigma = "A resposta firme nasce de boas pistas."
    opcoes, correta_idx = _embaralhar_opcoes(correta, distratores, indice)
    return enigma, pergunta, opcoes, correta_idx, conceito


def _questao_teorica(materia: str, tema: str, indice: int) -> tuple[str, str, list[str], int, str]:
    if materia == "Matematica":
        return _modelo_matematica(tema, indice)
    if materia in {"Ciencias", "Fisica", "Quimica", "Biologia"}:
        return _modelo_ciencias(tema, indice)
    return _modelo_linguagens_humanas(materia, tema, indice)


def _explicacao(materia: str, tema: str, codigo: str) -> list[dict[str, str]]:
    foco, estrategia, _ = _perfil(materia)
    return [
        {"tipo": "bold", "conteudo": f"BNCC Ensino Fundamental ({codigo})"},
        {"tipo": "texto", "conteudo": f"Neste tema, o objetivo e {foco}."},
        {"tipo": "texto", "conteudo": f"Para responder bem, e importante {estrategia}."},
        {"tipo": "resultado", "conteudo": "A alternativa correta usa o contexto, o conceito e as evidencias do enunciado."},
    ]


def _gerar_materia(materia: str) -> list[dict[str, Any]]:
    temas = TEMAS_RPG.get(materia, {}).get("EF") or TEMAS_RPG.get("Ciencias", {}).get("EF", ["conteudo geral"])
    foco, _estrategia, habilidade_base = _perfil(materia)
    cenarios = _cenarios(materia)
    area = get_area_da_materia(materia, "7o Ano")
    banco_especifico_materia = BANCO_ESPECIFICO_EF.get(materia, {})
    questoes: list[dict[str, Any]] = []

    for tema_idx, tema in enumerate(temas):
        especificas = banco_especifico_materia.get(tema) or []
        for variacao in range(QUESTOES_EF_POR_TEMA):
            indice = tema_idx * QUESTOES_EF_POR_TEMA + variacao
            # MELHORIA: isto e o CODIGO ("EF07MA01"), nao a habilidade --
            # e ia para `habilidade_bncc` enquanto `codigo_bncc` ficava
            # vazio. Mesma troca corrigida no banco EM.
            codigo = f"{habilidade_base}{(tema_idx % 9) + 1:02d}"
            cenario = cenarios[indice % len(cenarios)]
            if especificas:
                # MELHORIA: quando ha conteudo especifico pra este tema (ver
                # services/fundamental_conteudo_especifico.py), ele substitui
                # o template generico, que so perguntava "qual analise e mais
                # adequada para estudar {tema}?" sem cobrar conteudo real.
                especifica = especificas[variacao % len(especificas)]
                pergunta = especifica["pergunta"]
                opcoes, correta_idx = _embaralhar_opcoes(
                    especifica["opcoes"][0], list(especifica["opcoes"][1:]), indice
                )
                explicacao = list(especifica["explicacao"])
                # MELHORIA: era "Desafio de {tema}." nas 4.050 questoes deste banco
                # (medido em 15/09/2026) -- o mesmo titulo generico, repetido. O
                # cenario ja sorteado para a questao da o contexto.
                enigma = f"{tema[:1].upper()}{tema[1:]} em {cenario}."
            else:
                enigma, pergunta, opcoes, correta_idx, conceito = _questao_teorica(materia, tema, indice)
                explicacao = _explicacao(materia, tema, codigo) + [
                    {"tipo": "texto", "conteudo": f"Exemplo de contexto: {cenario}. {conceito}"}
                ]
            questoes.append(
                {
                    "id_offline": f"EF-{materia}-{indice + 1:04d}",
                    "materia": materia,
                    "serie_tipo": "EF",
                    "tema_usado": tema,
                    "objeto_conhecimento": tema,
                    "dificuldade": _nivel(indice),
                    "area_bncc": area,
                    "competencia_bncc": f"Competencia BNCC EF: {foco}",
                    "habilidade_bncc": HABILIDADES_BNCC_EF.get(materia, ""),
                    "codigo_bncc": codigo,
                    "fonte_bncc": "https://www.gov.br/mec/pt-br/escola-em-tempo-integral/BNCC_EI_EF_110518_versaofinal.pdf",
                    "enigma": enigma,
                    "pergunta": pergunta,
                    "opcoes": opcoes,
                    "correta": correta_idx,
                    "explicacao": explicacao,
                    "passos_resolucao": [],
                    "formula": "",
                    "subformulas": [],
                    "legenda_variaveis": "",
                    "_origem_geracao": "offline",
                }
            )
    return questoes


BANCO_OFFLINE_EF = LazyMateriaBank(MATERIAS, _gerar_materia, fallback="Ciencias")


def listar_questoes_ef(materia: str) -> list[dict[str, Any]]:
    materia_norm = normalizar_materia(materia) or "Ciencias"
    return deepcopy(BANCO_OFFLINE_EF.get(materia_norm) or BANCO_OFFLINE_EF["Ciencias"])


def gerar_questao_offline_ef(
    materia: str,
    tema: str = "",
    nivel: str = "",
    evitar_ids: list[str] | set[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    materia_norm = normalizar_materia(materia) or "Ciencias"
    questoes = BANCO_OFFLINE_EF.get(materia_norm) or BANCO_OFFLINE_EF["Ciencias"]
    questao = selecionar_questao_offline(
        questoes, tema, seed=f"ef|{materia_norm}|{tema}|{nivel}", evitar_ids=evitar_ids
    )
    if nivel:
        questao["dificuldade"] = str(nivel)
    return questao
