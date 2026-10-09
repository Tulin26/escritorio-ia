"""
Arquivo de configuracao do EduGame.
Contem constantes, badges, temas e estrutura curricular.
"""

import re
import unicodedata

# ====================== CONFIGURACOES GERAIS ======================

FASES_TOTAIS_RPG = 15

SERIES = ["6o Ano", "7o Ano", "8o Ano", "9o Ano", "1o Ano EM", "2o Ano EM", "3o Ano EM"]


def eh_ensino_medio(ano_escolar: str) -> bool:
    """Esta serie e de Ensino Medio? Vale para TODOS os modos.

    MELHORIA: esta decisao existia em CINCO lugares, cada modo com a sua
    lista, e elas nao eram iguais:

        services/banks/em.py       EM, MEDIO, MÉDIO, 1O ANO, 2O ANO, 3O ANO, 1º, 2º, 3º
        services/calculo_service   EM, MEDIO, MÉDIO, 1º, 2º, 3º
        web/routes/laboratorio_fla EM, MEDIO, MÉDIO
        services/rpg_service       em, medio, 1o ano, 2o ano, 3o ano
        st/ui/tela_laboratorio_st  EM, MÉDIO, 1º, 2º, 3º      <- sem "MEDIO"

    A ultima nao tinha "MEDIO" sem acento, entao para ano_escolar
    "Ensino Medio" ela respondia Fundamental enquanto o resto do sistema
    respondia Medio -- e a consequencia era o aluno abrir o Laboratorio no
    Streamlit e ver so Matematica, sem Fisica nem Quimica.

    Nos valores de SERIES as cinco concordavam, entao isto nunca apareceu
    com dado vindo do formulario. Bastava um ano_escolar digitado direto no
    banco, ou herdado, para as telas discordarem entre si sem nada no log.

    O acento agora e removido antes da comparacao, em vez de cada grafia
    entrar na lista: era justamente esquecer uma grafia que criava a quinta
    versao divergente.
    """
    serie = unicodedata.normalize("NFKD", str(ano_escolar or ""))
    serie = "".join(c for c in serie if not unicodedata.combining(c)).upper()
    return any(
        marcador in serie
        for marcador in ("EM", "MEDIO", "1O ANO", "2O ANO", "3O ANO", "1O", "2O", "3O")
    )

MATERIAS = [
    "Matematica",
    "Fisica",
    "Quimica",
    "Biologia",
    "Portugues",
    "Historia",
    "Geografia",
    "Ingles",
    "Ciencias",
    "Educacao Fisica",
    "Arte",
    "Filosofia",
    "Sociologia",
    "Ensino Religioso",
]

MAPEAMENTO_MATERIAS = {
    "Língua Portuguesa": "Portugues",
    "Lingua Portuguesa": "Portugues",
    "Português": "Portugues",
    "Portugues": "Portugues",
    "Matemática": "Matematica",
    "Matematica": "Matematica",
    "Física": "Fisica",
    "Fisica": "Fisica",
    "Química": "Quimica",
    "Quimica": "Quimica",
    "Biologia": "Biologia",
    "História": "Historia",
    "Historia": "Historia",
    "Geografia": "Geografia",
    "Inglês": "Ingles",
    "Ingles": "Ingles",
    "Ciências": "Ciencias",
    "Ciencias": "Ciencias",
    "Educação Física": "Educacao Fisica",
    "Educacao Fisica": "Educacao Fisica",
    "Arte": "Arte",
    "Filosofia": "Filosofia",
    "Sociologia": "Sociologia",
    "Ensino Religioso": "Ensino Religioso",
}

MATERIAS_COM_ACENTO = {
    "Matematica": "Matemática",
    "Fisica": "Física",
    "Quimica": "Química",
    "Biologia": "Biologia",
    "Portugues": "Português",
    "Historia": "História",
    "Geografia": "Geografia",
    "Ingles": "Inglês",
    "Ciencias": "Ciências",
    "Educacao Fisica": "Educação Física",
    "Arte": "Arte",
    "Filosofia": "Filosofia",
    "Sociologia": "Sociologia",
    "Ensino Religioso": "Ensino Religioso",
}

_MATERIAS_POR_CHAVE = {
    re.sub(
        r"\s+",
        " ",
        unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii").strip().lower(),
    ): valor
    for nome, valor in {
        **MAPEAMENTO_MATERIAS,
        **{materia: materia for materia in MATERIAS},
        **{nome_com_acento: materia for materia, nome_com_acento in MATERIAS_COM_ACENTO.items()},
    }.items()
}

NIVEIS_DIFICULDADE = ["Facil", "Medio", "Dificil"]

# MELHORIA: medido nos logs reais, a dificuldade chegava ao banco em QUATRO
# grafias -- "Medio" (RPG, Treino, Boss Rush, ENEM), "Médio" (Laboratorio,
# Oraculo, Escape Room), "Difícil" e "🔴 Difícil", esta ultima porque a tela
# do Laboratorio no Streamlit passava o rotulo do slider direto para o log.
#
# O painel do professor filtra e agrupa por este campo, entao "Medio" e
# "Médio" contavam como dificuldades DIFERENTES -- o mesmo defeito ja
# corrigido no prefixo de materia ("LAB-Fisica" x "Fisica"), que fragmentava
# a tela de Progresso.
#
# A regra e a mesma do resto do projeto: a CHAVE fica sem acento e sem
# emoji, e o ROTULO vem ao lado. Por isso a dupla abaixo espelha
# MATERIAS_COM_ACENTO / exibir_materia.
DIFICULDADES_COM_ACENTO = {
    "Facil": "Fácil",
    "Medio": "Médio",
    "Dificil": "Difícil",
}


# ====================== TEMAS POR DISCIPLINA ======================

TEMAS_RPG = {
    "Matematica": {
        "EF": [
            "numeros inteiros e operacoes basicas",
            "fracoes e numeros decimais",
            "porcentagem e desconto",
            "regra de tres simples",
            "equacoes do 1o grau",
            "areas de figuras planas",
            "perimetro e comprimento",
            "volume de solidos simples",
            "razao e proporcao",
            "expressoes algebricas simples",
            "graficos e tabelas",
            "probabilidade basica",
            "potencias e raizes quadradas",
            "sequencias numericas",
        ],
        "EM": [
            "equacoes do 2o grau e formula de Bhaskara",
            "sistemas de equacoes lineares",
            "funcoes do 1o grau",
            "funcoes do 2o grau e parabola",
            "funcao exponencial",
            "funcao logaritmica",
            "progressao aritmetica (PA)",
            "progressao geometrica (PG)",
            "trigonometria",
            "geometria analitica",
            "matrizes e determinantes",
            "combinatoria",
            "probabilidade condicional",
            "estatistica",
            "modelagem matematica em contextos reais",
            "taxas e indices socioeconomicos",
            "analise critica de graficos e tabelas",
            "matematica financeira",
            "geometria espacial aplicada a areas e volumes",
            "porcentagem",
            "geometria plana",
            "geometria espacial",
            "grandezas diretamente e inversamente proporcionais",
            "analise combinatoria",
            "logaritmos",
        ],
    },
    "Fisica": {
        "EF": [
            "energia e suas formas",
            "temperatura e calor",
            "estados da materia",
            "velocidade e movimento",
            "forcas e atrito",
            "luz e sombra",
            "som e ondas sonoras",
            "eletricidade basica",
            "magnetismo",
            "pressao e empuxo",
        ],
        "EM": [
            "cinematica: MRU e MRUV",
            "lancamento de projeteis",
            "leis de Newton",
            "trabalho, energia e potencia",
            "quantidade de movimento",
            "termologia",
            "termodinamica",
            "optica geometrica",
            "eletrostatica",
            "circuitos eletricos",
            "magnetismo",
            "ondas",
            "movimento circular uniforme",
            "hidrostatica",
            "matrizes energeticas e sustentabilidade",
            "radiacoes e espectro eletromagnetico",
            "equipamentos eletricos e eletronicos",
            "eficiencia de motores",
            "calorimetria",
            "lei de Ohm",
            "potencia eletrica",
            "corrente eletrica",
        ],
    },
    "Quimica": {
        "EF": [
            "misturas homogeneas e heterogeneas",
            "separacao de misturas",
            "propriedades dos materiais",
            "estados fisicos da materia",
            "atomos e moleculas",
            "reacoes quimicas",
            "acidos e bases",
            "agua",
        ],
        "EM": [
            "tabela periodica",
            "ligacoes quimicas",
            "estequiometria",
            "solucoes",
            "mol e massa molar",
            "reacoes acido-base e pH",
            "gases ideais",
            "termoquimica",
            "eletroquimica",
            "quimica organica",
            "cinetica quimica",
            "equilibrio quimico",
            "estrutura e propriedades dos materiais",
            "processos produtivos quimicos",
            "agroquimicos e impactos ambientais",
            "combustiveis e sustentabilidade",
            "atomistica",
            "distribuicao eletronica",
            "funcoes inorganicas",
            "unidades de concentracao",
            "radioatividade",
        ],
    },
    "Biologia": {
        "EF": [
            "seres vivos",
            "celulas",
            "sistema digestorio",
            "sistema respiratorio",
            "animais vertebrados",
            "plantas e fotossintese",
            "ecossistemas",
            "higiene e saude",
            "agua",
        ],
        "EM": [
            "citologia",
            "mitose e meiose",
            "genetica mendeliana",
            "evolucao",
            "sistematica",
            "virus e bacterias",
            "fungos",
            "sistema circulatorio",
            "sistema nervoso",
            "ecologia",
            "biomas brasileiros",
            "biotecnologia",
        ],
    },
    "Portugues": {
        "EF": [
            "ortografia e acentuacao",
            "substantivo e adjetivo",
            "verbos",
            "pontuacao",
            "interpretacao de texto",
            "sinonimos e antonimos",
        ],
        "EM": [
            "analise sintatica",
            "concordancia verbal e nominal",
            "regencia",
            "crase",
            "figuras de linguagem",
            "interpretacao de texto",
            "coesao e coerencia",
            "morfologia",
            "periodo composto",
            "literatura brasileira",
            "modernismo",
            "barroco",
            "romantismo",
        ],
    },
    "Historia": {
        "EF": [
            "pre-historia",
            "Egito e Mesopotamia",
            "Grecia Antiga",
            "Roma Antiga",
            "Idade Media",
            "Brasil indigena",
            "colonizacao",
            "escravidao",
            "independencia",
        ],
        "EM": [
            "Renascimento",
            "Reforma Protestante",
            "Grandes Navegacoes",
            "Revolucao Francesa",
            "Revolucao Industrial",
            "Imperialismo",
            "Primeira Guerra Mundial",
            "Revolucao Russa",
            "Segunda Guerra Mundial",
            "Guerra Fria",
            "Era Vargas",
            "Ditadura Militar",
            "Redemocratizacao",
        ],
    },
    "Geografia": {
        "EF": [
            "orientacao e mapas",
            "relevo",
            "hidrografia",
            "clima e vegetacao",
            "biomas brasileiros",
            "regioes do Brasil",
            "urbanizacao",
            "agricultura",
        ],
        "EM": [
            "geopolitica mundial",
            "globalizacao",
            "placas tectonicas",
            "demografia",
            "fluxos migratorios",
            "recursos naturais",
            "fontes de energia",
            "fusos horarios",
            "clima",
            "industria",
            "comercio internacional",
            "blocos economicos",
        ],
    },
    "Ingles": {
        "EF": [
            "vocabulario basico",
            "verbo to be",
            "simple present",
            "simple past",
            "there is/are",
            "pronomes",
            "numeros e cores",
            "WH-words",
        ],
        "EM": [
            "present perfect",
            "future (will/going to)",
            "conditional sentences",
            "passive voice",
            "modal verbs",
            "reported speech",
            "comparatives and superlatives",
            "phrasal verbs",
            "false cognates",
            "idioms",
            "text interpretation",
        ],
    },
    "Ciencias": {
        "EF": [
            "sistema solar",
            "fases da Lua",
            "estados da materia",
            "cadeia alimentar",
            "corpo humano",
            "agua",
            "ar e poluicao",
            "solo",
            "animais e plantas",
            "energia",
            "reciclagem",
            "saude e higiene",
            "vacinas",
        ],
        "EM": [
            "astronomia",
            "geologia",
            "ecologia avancada",
            "quimica ambiental",
            "fisica ambiental",
            "biologia molecular basica",
            "sustentabilidade",
            "mudancas climaticas",
            "biodiversidade",
        ],
    },
    "Educacao Fisica": {
        "EF": [
            "futebol",
            "basquete",
            "volei",
            "handebol",
            "futsal",
            "atletismo",
            "ginastica",
            "alongamento",
            "capacidades fisicas",
            "jogos cooperativos",
            "regras esportivas",
            "modalidades olimpicas",
            "historia do futebol",
            "regras do volei",
            "regras do basquete",
            "regras do handebol",
        ],
        "EM": [
            "historia do esporte",
            "treinamento esportivo",
            "fisiologia do exercicio",
            "nutricao esportiva",
            "psicologia do esporte",
            "esportes olimpicos",
            "regras oficiais",
            "arbitragem",
            "prevencao de lesoes",
            "esportes de aventura",
            "educacao fisica adaptada",
            "grandes atletas brasileiros",
            "copas do mundo",
        ],
    },
    "Arte": {
        "EF": ["artes visuais", "musica", "danca", "teatro", "cores e formas", "patrimonio cultural", "expressao corporal"],
        "EM": ["linguagens artisticas", "estetica e expressao", "arte contemporanea", "patrimonio cultural", "producao artistica", "interpretacao de obras"],
    },
    "Filosofia": {
        "EF": ["etica e convivencia", "identidade", "respeito", "argumentacao"],
        "EM": ["etica", "politica", "conhecimento", "logica", "filosofia antiga", "filosofia moderna", "cidadania"],
    },
    "Sociologia": {
        "EF": ["vida em sociedade", "cultura", "diversidade", "regras sociais"],
        "EM": ["cultura", "cidadania", "trabalho", "instituicoes sociais", "desigualdade social", "movimentos sociais", "identidade"],
    },
    "Ensino Religioso": {
        "EF": ["identidades e alteridades", "manifestacoes religiosas", "valores", "respeito a diversidade religiosa", "tradicoes religiosas"],
        "EM": ["diversidade religiosa", "etica", "dialogo inter-religioso", "sentido da vida", "direitos humanos e religiosidade"],
    },
}


# ====================== CURRICULO POR AREA ======================

AREAS_CURRICULARES = {
    "EF": {
        "Linguagens": ["Lingua Portuguesa", "Arte", "Educacao Fisica", "Ingles"],
        "Matematica": ["Matematica"],
        "Ciencias da Natureza": ["Ciencias"],
        "Ciencias Humanas": ["Historia", "Geografia"],
        "Ensino Religioso": ["Ensino Religioso"],
    },
    "EM": {
        "Linguagens e suas Tecnologias": ["Lingua Portuguesa", "Arte", "Ingles", "Educacao Fisica"],
        "Matematica e suas Tecnologias": ["Matematica"],
        "Ciencias da Natureza e suas Tecnologias": ["Biologia", "Fisica", "Quimica"],
        "Ciencias Humanas e Sociais Aplicadas": ["Historia", "Geografia", "Filosofia", "Sociologia"],
    },
}

COMPETENCIAS_AREA = {
    "EF": {
        "Linguagens": [
            "comunicar-se em diferentes linguagens e contextos",
            "interpretar, produzir e compartilhar sentidos",
            "valorizar manifestacoes artisticas, corporais e culturais",
        ],
        "Matematica": [
            "resolver problemas e argumentar com raciocinio logico",
            "representar informacoes com linguagem matematica",
            "usar conhecimentos matematicos em situacoes do cotidiano",
        ],
        "Ciencias da Natureza": [
            "investigar fenomenos naturais e tecnologicos",
            "compreender relacoes entre ciencia, ambiente e sociedade",
            "usar evidencias para explicar e tomar decisoes",
        ],
        "Ciencias Humanas": [
            "compreender processos historicos, espaciais e culturais",
            "analisar relacoes sociais e transformacoes no tempo e no espaco",
            "exercitar cidadania, empatia e pensamento critico",
        ],
        "Ensino Religioso": [
            "reconhecer diferentes tradicoes e experiencias religiosas",
            "promover respeito a diversidade de crencas",
            "dialogar com valores eticos e de convivencia",
        ],
    },
    "EM": {
        "Linguagens e suas Tecnologias": [
            "analisar criticamente discursos, linguagens e midias",
            "produzir sentidos em contextos artisticos, corporais e comunicativos",
            "usar linguagens para participacao social e projeto de vida",
        ],
        "Matematica e suas Tecnologias": [
            "modelar e resolver problemas em contextos diversos",
            "analisar dados, graficos, tabelas e situacoes quantitativas",
            "argumentar com base em padroes, relacoes e representacoes matematicas",
        ],
        "Ciencias da Natureza e suas Tecnologias": [
            "investigar fenomenos, processos e transformacoes da natureza",
            "avaliar implicacoes ambientais, sociais e tecnologicas",
            "mobilizar conceitos de Biologia, Fisica e Quimica de forma integrada",
        ],
        "Ciencias Humanas e Sociais Aplicadas": [
            "analisar processos politicos, historicos, geograficos e socioculturais",
            "interpretar relacoes de poder, cidadania, trabalho e diversidade",
            "construir argumentos criticos sobre sociedade e vida coletiva",
        ],
    },
}

# ====================== FUNCOES AUXILIARES ======================

def _chave_materia(materia: str) -> str:
    texto = unicodedata.normalize("NFKD", str(materia or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto.strip().lower())


def normalizar_materia(materia: str) -> str:
    texto = str(materia or "").strip()
    if not texto:
        return ""
    return _MATERIAS_POR_CHAVE.get(_chave_materia(texto), MAPEAMENTO_MATERIAS.get(texto, texto))


def exibir_materia(materia: str) -> str:
    materia_norm = normalizar_materia(materia)
    return MATERIAS_COM_ACENTO.get(materia_norm, materia_norm)


def normalizar_dificuldade(valor) -> str:
    """A chave da dificuldade: sem acento, sem emoji, sem espaco em volta.

    Aceita tudo o que as telas produzem hoje -- "Médio", "Medio",
    "🔴 Difícil", "dificil" -- e devolve uma forma so. Fora dessas, devolve
    o texto original limpo: inventar "Medio" para um valor desconhecido
    esconderia o problema em vez de mostrar.
    """
    # Vazio nao precisa de guarda propria: `_chave_materia("")` devolve "",
    # nada casa, e o retorno final ja e "" -- um mutante mostrou que o `if
    # not texto` era rede sem efeito.
    texto = str(valor or "").strip()
    # `_chave_materia` ja tira acento e normaliza espaco, e o
    # encode("ascii", "ignore") derruba o emoji de brinde -- e a mesma
    # normalizacao que a materia usa, entao nao vale duplicar.
    chave = _chave_materia(texto)
    for nivel in NIVEIS_DIFICULDADE:
        if chave == nivel.lower():
            return nivel
    return texto


def exibir_dificuldade(valor) -> str:
    """O rótulo que vai para a tela, com acento."""
    chave = normalizar_dificuldade(valor)
    return DIFICULDADES_COM_ACENTO.get(chave, chave)


# MELHORIA: esta funcao existia reimplementada 5 vezes (professor_service.py,
# gamification_service.py, web/routes/progresso_fla.py, pedagogical_feedback.py,
# services/relatorios/commons.py), cada uma tirando um subconjunto diferente
# dos prefixos de modo ("LAB-", "RPG-", "ENEM-") do campo "materia" dos logs
# -- so a versao de professor_service.py tirava os 3. As outras, por tirarem
# menos, faziam "LAB-Fisica" e "Fisica" contarem como materias DIFERENTES em
# telas como Progresso ("Por materia" fragmentado, visto ao vivo no
# navegador) e no calculo do badge "Mestre Supremo". Fonte unica agora.
PREFIXOS_MODO_MATERIA = ("ENEM-", "LAB-", "RPG-")


def materia_base(materia: str) -> str:
    texto = str(materia or "")
    for prefixo in PREFIXOS_MODO_MATERIA:
        texto = texto.replace(prefixo, "")
    return texto.strip()


def get_serie_tipo(serie: str) -> str:
    if "EM" in str(serie or "").upper():
        return "EM"
    return "EF"


def get_curriculo_por_serie(serie: str) -> dict:
    serie_tipo = get_serie_tipo(serie)
    if serie_tipo == "EM":
        return {"serie_tipo": "EM", "modelo": "integrado_area", "areas": AREAS_CURRICULARES["EM"]}
    return {"serie_tipo": "EF", "modelo": "disciplinas_por_area", "areas": AREAS_CURRICULARES["EF"]}


def get_materias_por_serie(serie: str) -> list[str]:
    curriculo = get_curriculo_por_serie(serie)
    materias = [
        normalizar_materia(materia)
        for materias_area in curriculo.get("areas", {}).values()
        for materia in materias_area
    ]
    return list(dict.fromkeys(materia for materia in materias if materia))


def filtrar_materias_por_serie(materias: list[str] | tuple[str, ...], serie: str) -> list[str]:
    permitidas = set(get_materias_por_serie(serie))
    filtradas = []
    for materia in materias:
        materia_norm = normalizar_materia(materia)
        if materia_norm in permitidas:
            filtradas.append(materia_norm)
    return filtradas


def get_area_da_materia(materia: str, serie: str) -> str:
    materia_norm = normalizar_materia(materia)
    curriculo = get_curriculo_por_serie(serie)
    for area, materias in curriculo["areas"].items():
        if materia_norm in [normalizar_materia(item) for item in materias]:
            return area
    return "Area nao identificada"


def get_competencias_area(area: str, serie: str) -> list[str]:
    return COMPETENCIAS_AREA.get(get_serie_tipo(serie), {}).get(area, [])


def get_temas_rpg(materia: str, serie: str) -> list:
    materia_norm = normalizar_materia(materia)
    if materia_norm not in TEMAS_RPG:
        return ["conteudo geral da disciplina"]
    etapa = get_serie_tipo(serie)
    temas = TEMAS_RPG[materia_norm].get(etapa, [])
    if not temas:
        temas = TEMAS_RPG[materia_norm].get("EF", [])
    return temas if temas else ["conteudo geral da disciplina"]


# ====================== HABILIDADES POR AREA ======================

# MELHORIA: HABILIDADES_AREA nao tem mais uso na parte Flask deste
# repositorio (a main removeu-o ao refatorar este arquivo, sem saber que
# st/ui/tela_oraculo_st.py ainda chama get_habilidades_area(...) direto) —
# removê-lo quebraria essa tela no boot do Streamlit. Mantido como estava
# antes da sincronizacao com a main.
HABILIDADES_AREA = {
    "EF": {
        "Linguagens": [
            "ler, escutar e produzir textos multimodais",
            "experimentar criacao artistica e expressao corporal",
            "usar ingles em situacoes simples de interacao e leitura",
        ],
        "Matematica": [
            "calcular, estimar e justificar procedimentos",
            "interpretar tabelas, graficos e medidas",
            "resolver problemas com numeros, grandezas e geometria",
        ],
        "Ciencias da Natureza": [
            "observar, comparar, classificar e testar hipoteses",
            "explicar relacoes entre corpo, ambiente e tecnologia",
            "comunicar resultados de investigacoes",
        ],
        "Ciencias Humanas": [
            "localizar, comparar e interpretar fontes e mapas",
            "relacionar acontecimentos historicos e organizacao do espaco",
            "debater direitos, cultura e diversidade",
        ],
        "Ensino Religioso": [
            "identificar simbolos, ritos e tradicoes",
            "reconhecer semelhancas e diferencas entre crencas",
            "praticar escuta respeitosa e convivencia",
        ],
    },
    "EM": {
        "Linguagens e suas Tecnologias": [
            "interpretar textos, performances e producoes midiaticas complexas",
            "produzir argumentos, projetos autorais e expressoes artisticas",
            "articular leitura critica, repertorio cultural e comunicacao",
        ],
        "Matematica e suas Tecnologias": [
            "selecionar modelos, variaveis e representacoes para resolver problemas",
            "avaliar informacoes quantitativas em contextos sociais e cientificos",
            "usar linguagem algebrica, geometrica e estatistica com autonomia",
        ],
        "Ciencias da Natureza e suas Tecnologias": [
            "integrar conceitos de materia, energia, vida e transformacao",
            "analisar experimentos, dados e evidencias cientificas",
            "propor solucoes responsaveis para desafios socioambientais",
        ],
        "Ciencias Humanas e Sociais Aplicadas": [
            "analisar fontes, territorios e processos sociais",
            "relacionar conceitos de historia, geografia, filosofia e sociologia",
            "debater problemas contemporaneos com argumentacao critica",
        ],
    },
}

# ====================== FUNCOES AUXILIARES ======================

def get_habilidades_area(area: str, serie: str) -> list[str]:
    return HABILIDADES_AREA.get(get_serie_tipo(serie), {}).get(area, [])
