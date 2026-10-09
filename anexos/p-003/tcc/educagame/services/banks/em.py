from __future__ import annotations

from copy import deepcopy

from core.config import MATERIAS, eh_ensino_medio, normalizar_materia
from services.banks._base import LazyMateriaBank, selecionar_questao_offline
from services.ia.questoes import embaralhar_opcoes_questao
from services.oraculo_conteudo_especifico import BANCO_ESPECIFICO_EM


QUESTOES_POR_TEMA_EM = 80
QUESTOES_POR_MATERIA_EM = 2000


# Banco autoral, inspirado em habilidades públicas da BNCC do Ensino Médio.
# Referências consultadas:
# - Matemática EM: https://catalogobncc.github.io/metadados/2022/03/30/emmat
# - Ciências Humanas EM: https://catalogobncc.github.io/metadados/2022/03/30/emchs
# - Linguagens EM13LP01: https://bncc.digital/EM13LP01
# - Ciências da Natureza EM13CNT101: https://bncc.digital/EM13CNT101

TEMAS_BASE_EM = {
    "Matematica": [
        "funções do 1º grau", "funções do 2º grau", "progressão aritmética", "progressão geométrica",
        "porcentagem e juros", "logaritmos", "trigonometria", "geometria espacial", "matrizes",
        "determinantes", "probabilidade", "estatística", "análise combinatória", "geometria analítica",
        "sistemas lineares", "função exponencial", "modelagem matemática", "áreas e volumes",
        "sequências numéricas", "interpretação de gráficos", "razões e proporções", "escala",
        "matemática financeira", "medidas de tendência central", "geometria plana",
    ],
    "Fisica": [
        "movimento uniforme", "movimento uniformemente variado", "leis de Newton", "força de atrito",
        "trabalho e energia", "potência", "quantidade de movimento", "gravidade", "hidrostática",
        "calorimetria", "termodinâmica", "ondas", "óptica geométrica", "eletricidade", "lei de Ohm",
        "circuitos elétricos", "campo magnético", "indução eletromagnética", "física moderna",
        "energia mecânica", "pressão", "empuxo", "dilatação térmica", "espelhos e lentes", "radioatividade",
    ],
    "Quimica": [
        "estrutura atômica", "tabela periódica", "ligações químicas", "geometria molecular",
        "polaridade", "forças intermoleculares", "soluções", "concentração comum", "mol",
        "massa molar", "estequiometria", "termoquímica", "cinética química", "equilíbrio químico",
        "pH e pOH", "eletroquímica", "química orgânica", "funções orgânicas", "isomeria",
        "polímeros", "separação de misturas", "reações químicas", "oxirredução", "química ambiental",
        "combustíveis",
    ],
    "Biologia": [
        "citologia", "membrana plasmática", "metabolismo celular", "fotossíntese", "respiração celular",
        "genética mendeliana", "DNA e RNA", "biotecnologia", "evolução", "seleção natural",
        "ecologia", "cadeias alimentares", "ciclos biogeoquímicos", "fisiologia humana",
        "sistema nervoso", "sistema endócrino", "imunologia", "botânica", "zoologia", "saúde pública",
        "bioenergética", "divisão celular", "hereditariedade", "relações ecológicas", "biodiversidade",
    ],
    "Portugues": [
        "interpretação de texto", "gêneros textuais", "coesão", "coerência", "argumentação",
        "figuras de linguagem", "funções da linguagem", "variedade linguística", "regência", "crase",
        "concordância", "pontuação", "literatura brasileira", "modernismo", "romantismo", "realismo",
        "intertextualidade", "redação argumentativa", "análise do discurso", "semântica",
        "morfologia", "sintaxe", "efeitos de sentido", "repertório sociocultural", "norma padrão",
    ],
    "Historia": [
        "Antigo Regime", "Iluminismo", "Revolução Francesa", "Revolução Industrial", "Imperialismo",
        "Primeira Guerra Mundial", "Revolução Russa", "Crise de 1929", "Segunda Guerra Mundial",
        "Guerra Fria", "descolonização", "Brasil Colonial", "Independência do Brasil", "Primeiro Reinado",
        "Segundo Reinado", "República Velha", "Era Vargas", "Ditadura Militar", "redemocratização",
        "movimentos sociais", "escravidão no Brasil", "cidadania no Brasil", "populismo", "nova ordem mundial",
        "história indígena",
    ],
    "Geografia": [
        "cartografia", "fusos horários", "climatologia", "relevo", "hidrografia", "biomas",
        "urbanização", "industrialização", "globalização", "geopolítica", "população",
        "migrações", "agropecuária", "fontes de energia", "meio ambiente", "desenvolvimento sustentável",
        "comércio internacional", "blocos econômicos", "questão agrária", "território brasileiro",
        "demografia", "redes de transporte", "matriz energética", "conflitos territoriais", "mudanças climáticas",
    ],
    "Ingles": [
        "reading comprehension", "main idea", "context clues", "false cognates", "simple present",
        "simple past", "present perfect", "future forms", "modal verbs", "conditionals",
        "passive voice", "reported speech", "relative clauses", "linking words", "phrasal verbs",
        "prefixes and suffixes", "advertisements", "news texts", "scientific texts", "argumentative texts",
        "skimming", "scanning", "multimodal texts", "digital genres", "opinion articles",
    ],
    "Ciencias": [
        "método científico", "energia", "matéria", "sistemas do corpo humano", "saúde e prevenção",
        "ecologia", "astronomia", "genética", "evolução", "ondas", "eletricidade", "química ambiental",
        "tecnologia e sociedade", "sustentabilidade", "mudanças climáticas", "biodiversidade",
        "vacinas", "alimentação", "recursos naturais", "impactos ambientais", "solo e água",
        "microorganismos", "máquinas simples", "luz e visão", "cadeias alimentares",
    ],
    "Educacao Fisica": [
        "esportes coletivos", "esportes individuais", "lutas", "ginástica", "danças", "jogos e brincadeiras",
        "práticas corporais de aventura", "saúde e qualidade de vida", "atividade física", "sedentarismo",
        "treinamento físico", "capacidades físicas", "inclusão no esporte", "mídia e esporte",
        "corpo e cultura", "regras esportivas", "cooperação", "competição", "lazer", "primeiros socorros",
        "esporte adaptado", "ritmo e expressão", "alongamento", "frequência cardíaca", "fair play",
    ],
    "Arte": [
        "arte rupestre", "arte clássica", "renascimento", "barroco", "neoclassicismo", "romantismo na arte",
        "realismo na arte", "impressionismo", "expressionismo", "cubismo", "surrealismo", "modernismo",
        "arte contemporânea", "arte brasileira", "música", "teatro", "dança", "cinema", "fotografia",
        "patrimônio cultural", "grafite", "instalação artística", "performance", "cultura popular", "design",
    ],
    "Filosofia": [
        "mito e filosofia", "Sócrates", "Platão", "Aristóteles", "ética", "política", "epistemologia",
        "racionalismo", "empirismo", "contratualismo", "Iluminismo", "Kant", "existencialismo",
        "filosofia da ciência", "lógica", "estética", "liberdade", "justiça", "ideologia", "bioética",
        "direitos humanos", "felicidade", "verdade", "moral", "tecnologia e ética",
    ],
    "Sociologia": [
        "cultura", "socialização", "instituições sociais", "trabalho", "classes sociais", "desigualdade",
        "estratificação", "poder", "Estado", "cidadania", "democracia", "movimentos sociais",
        "globalização", "indústria cultural", "mídia", "gênero", "raça e etnia", "violência",
        "urbanização", "juventudes", "família", "religião e sociedade", "consumo", "participação política",
        "direitos sociais",
    ],
    "Ensino Religioso": [
        "diversidade religiosa", "diálogo inter-religioso", "ética", "alteridade", "ritos", "mitos",
        "símbolos religiosos", "textos sagrados", "tradições orais", "religiosidades brasileiras",
        "matrizes africanas", "povos indígenas", "secularização", "intolerância religiosa",
        "direitos humanos", "convivência", "valores", "projeto de vida", "cultura de paz", "solidariedade",
        "liberdade de crença", "patrimônio religioso", "festas religiosas", "espiritualidade", "respeito",
    ],
}


# MELHORIA: o terceiro elemento da tupla e o CODIGO da habilidade
# ("EM13MAT101"), mas era desempacotado numa variavel chamada `habilidade` e
# gravado em `habilidade_bncc` -- campo que deveria trazer a DESCRICAO. A
# coluna `codigo_bncc` existe exatamente para o codigo, e ficava vazia em
# 100% dos logs.
#
# O nome da variavel passa a dizer o que ela e. A troca so afetava o log: as
# duas funcoes que injetariam o codigo na explicacao do aluno
# (_explicacao_teorica_exatas e _explicacao_para_materia) sao codigo morto --
# as 28.000 questoes vao todas pelo ramo "especifica".
BNCC_REFERENCIAS = {
    "Matematica": ("Matemática e suas Tecnologias", "Competência específica 1", "EM13MAT101"),
    "Fisica": ("Ciências da Natureza e suas Tecnologias", "Competência específica 1", "EM13CNT101"),
    "Quimica": ("Ciências da Natureza e suas Tecnologias", "Competência específica 2", "EM13CNT205"),
    "Biologia": ("Ciências da Natureza e suas Tecnologias", "Competência específica 3", "EM13CNT303"),
    "Portugues": ("Linguagens e suas Tecnologias", "Competência específica 1", "EM13LP01"),
    "Historia": ("Ciências Humanas e Sociais Aplicadas", "Competência específica 1", "EM13CHS101"),
    "Geografia": ("Ciências Humanas e Sociais Aplicadas", "Competência específica 2", "EM13CHS206"),
    "Ingles": ("Linguagens e suas Tecnologias", "Competência específica 4", "EM13LGG403"),
    "Ciencias": ("Ciências da Natureza e suas Tecnologias", "Competência específica 1", "EM13CNT101"),
    "Educacao Fisica": ("Linguagens e suas Tecnologias", "Competência específica 5", "EM13LGG501"),
    "Arte": ("Linguagens e suas Tecnologias", "Competência específica 6", "EM13LGG604"),
    "Filosofia": ("Ciências Humanas e Sociais Aplicadas", "Competência específica 5", "EM13CHS501"),
    "Sociologia": ("Ciências Humanas e Sociais Aplicadas", "Competência específica 6", "EM13CHS603"),
    "Ensino Religioso": ("Ensino Religioso", "Competências gerais da BNCC", "EF09ER08"),
}

# O que `habilidade_bncc` passa a guardar: a descricao, e nao o codigo.
#
# Sao RESUMOS do sentido de cada competencia especifica, no mesmo espirito do
# resto deste arquivo ("banco autoral, inspirado em habilidades publicas da
# BNCC"), e nao transcricao literal -- o texto oficial completo esta no link
# que `_fonte_bncc` ja devolve por materia, para quem precisar conferir.
#
# Vale para relatorio de professor e para a defesa do alinhamento curricular:
# "EM13MAT101" nao diz nada a quem le; a frase diz.
HABILIDADES_BNCC = {
    "Matematica": "Interpretar situações do cotidiano, das ciências e da tecnologia com estratégias e conceitos matemáticos.",
    "Fisica": "Analisar fenômenos naturais e processos tecnológicos a partir das relações entre matéria e energia.",
    "Quimica": "Analisar transformações da matéria e seus usos, avaliando impactos e aplicações tecnológicas.",
    "Biologia": "Investigar situações-problema e avaliar aplicações do conhecimento científico sobre a vida.",
    "Portugues": "Relacionar o texto às suas condições de produção e ao contexto sócio-histórico em que circula.",
    "Historia": "Analisar processos políticos, econômicos, sociais e culturais em diferentes tempos e espaços.",
    "Geografia": "Analisar a formação de territórios e fronteiras e as dinâmicas do espaço geográfico.",
    "Ingles": "Compreender a língua como fenômeno cultural, histórico e social, sensível ao contexto de uso.",
    "Ciencias": "Analisar fenômenos naturais e processos tecnológicos a partir das relações entre matéria e energia.",
    "Educacao Fisica": "Compreender a produção de sentidos nas práticas corporais e seus efeitos sobre o corpo.",
    "Arte": "Apreciar esteticamente produções artísticas e culturais, reconhecendo seus modos de criação.",
    "Filosofia": "Identificar e questionar formas de injustiça, preconceito e violência, sustentando argumentos.",
    "Sociologia": "Participar do debate público de forma crítica, considerando diferentes posições e direitos humanos.",
    "Ensino Religioso": "Reconhecer o direito à liberdade de consciência e crença, questionando práticas que a violam.",
}


PERFIS = {
    "Matematica": ("modelar relações quantitativas e interpretar dados", "selecionar variáveis, representar relações e conferir o resultado no contexto"),
    "Fisica": ("analisar transformações e conservações de energia, matéria e movimento", "identificar grandezas, unidades e princípios físicos antes de calcular"),
    "Quimica": ("interpretar transformações químicas e propriedades da matéria", "relacionar evidências, proporções, fórmulas e condições do processo químico"),
    "Biologia": ("explicar processos vitais, diversidade e relações ecológicas", "usar evidências biológicas para justificar a alternativa"),
    "Portugues": ("interpretar textos em seus contextos de produção e circulação", "relacionar gênero, público, objetivo, autoria e contexto histórico-social"),
    "Historia": ("comparar fontes, narrativas e processos históricos", "avaliar contexto, agentes sociais, permanências e mudanças"),
    "Geografia": ("analisar território, escala, redes e relações socioambientais", "observar localização, distribuição, conexão e impacto espacial"),
    "Ingles": ("understand meanings in English from context and genre", "use context clues, communicative purpose and genre conventions"),
    "Ciencias": ("integrar evidências de fenômenos naturais e tecnológicos", "comparar dados, reconhecer causas e propor explicações responsáveis"),
    "Educacao Fisica": ("compreender práticas corporais, saúde, cultura e inclusão", "analisar regras, participação, segurança e contexto social da prática"),
    "Arte": ("interpretar linguagens artísticas e contextos culturais", "observar materialidade, forma, intenção, circulação e repertório cultural"),
    "Filosofia": ("avaliar conceitos, argumentos e problemas éticos", "comparar ideias, pressupostos e consequências para a vida coletiva"),
    "Sociologia": ("analisar relações sociais, cultura, poder e desigualdades", "ligar indivíduo, grupo, instituições e contexto histórico"),
    "Ensino Religioso": ("compreender diversidade, símbolos e convivência", "analisar tradições com respeito, sem hierarquizar crenças"),
}


CENARIOS = {
    "Matematica": ["uma planilha de orçamento escolar", "um gráfico publicado em notícia", "um projeto de reforma da quadra", "uma pesquisa por amostragem"],
    "Fisica": ["um experimento com carrinho em rampa", "uma conta de energia da escola", "um estudo de eficiência de motores", "uma análise de ondas sonoras"],
    "Quimica": ["um rótulo de solução doméstica", "uma reação em laboratório", "um processo de tratamento de água", "uma análise de combustível"],
    "Biologia": ["um relatório de biodiversidade local", "um heredograma familiar fictício", "um estudo sobre vacinação", "um esquema de cadeia alimentar"],
    "Portugues": ["uma notícia compartilhada em rede social", "um artigo de opinião", "uma campanha pública", "um texto literário em contexto histórico"],
    "Historia": ["duas fontes sobre o mesmo acontecimento", "um mapa histórico comentado", "um manifesto político", "um registro de memória coletiva"],
    "Geografia": ["um mapa temático", "uma série de dados demográficos", "uma imagem de satélite", "um estudo de impacto ambiental"],
    "Ingles": ["a short news text", "an advertisement", "a social media post", "a scientific infographic"],
    "Ciencias": ["um projeto de investigação escolar", "um infográfico científico", "uma situação de saúde coletiva", "um problema socioambiental"],
    "Educacao Fisica": ["uma proposta de torneio inclusivo", "um plano de atividade física", "uma aula sobre esporte adaptado", "uma análise de segurança na prática corporal"],
    "Arte": ["uma obra em exposição", "uma performance escolar", "um registro de patrimônio cultural", "uma intervenção urbana"],
    "Filosofia": ["um dilema ético cotidiano", "um debate sobre liberdade", "um argumento sobre justiça", "uma situação envolvendo tecnologia"],
    "Sociologia": ["uma pesquisa sobre juventudes", "um gráfico de desigualdade", "uma campanha de cidadania", "um estudo sobre trabalho"],
    "Ensino Religioso": ["uma roda de diálogo inter-religioso", "um estudo de símbolos religiosos", "uma situação de intolerância", "uma ação de cultura de paz"],
}


def _titulo_no_cenario(tema: str, cenario: str) -> str:
    """"funções do 1º grau" em "uma planilha" -> "Funções do 1º grau em uma planilha."."""
    texto = f"{tema} em {cenario}."
    return texto[:1].upper() + texto[1:]


CONTEXTOS = [
    "leitura de contexto",
    "aplicacao em problema",
    "analise de evidencias",
    "interpretacao de dados",
    "argumentacao responsavel",
    "comparacao de alternativas",
    "situacao interdisciplinar",
    "tomada de decisao",
    "validacao de conclusao",
    "revisao conceitual",
]


EVIDENCIAS = [
    "o grupo registrou duas informações que parecem se contradizer",
    "a turma precisa justificar a escolha com base em dados e contexto",
    "há uma alternativa tentadora que repete um termo do enunciado, mas ignora o comando",
    "o enunciado apresenta uma situação real e pede uma conclusão responsável",
    "a resposta exige comparar evidências antes de aplicar uma regra",
]
EVIDENCIAS.extend(
    [
        "um estudante encontrou uma fonte confiavel, mas ainda precisa interpretar o recorte apresentado",
        "a situacao envolve uma decisao pratica e pede justificativa para evitar conclusoes automaticas",
        "dois grupos chegaram a respostas diferentes porque escolheram criterios de analise distintos",
        "o texto traz dados suficientes, mas uma leitura apressada pode confundir causa e consequencia",
        "a proposta pede que a conclusao seja coerente com o problema e com os limites das informacoes",
        "um registro visual, uma tabela ou um relato precisa ser lido junto ao contexto da atividade",
        "a turma deve separar opiniao, evidencia e explicacao antes de escolher a alternativa",
    ]
)


SITUACOES_APLICADAS = [
    "planejar uma intervencao na escola",
    "avaliar uma noticia antes de compartilha-la",
    "comparar solucoes propostas por dois grupos",
    "preparar uma apresentacao com dados e justificativas",
    "decidir qual procedimento seria mais adequado em um estudo de caso",
    "revisar um relatorio para eliminar conclusoes sem evidencia",
    "interpretar um material de campanha publica",
    "transformar observacoes em argumento verificavel",
]


PERGUNTAS_REALISTAS = {
    "conceitual": (
        "Situacao: em {cenario}, estudantes investigam {tema}. "
        "Dados do enunciado: {evidencia}. "
        "Qual alternativa explica melhor o conceito central envolvido nessa situacao?"
    ),
    "pratica": (
        "Situacao: uma turma precisa {acao} usando {tema} em {cenario}. "
        "Dados do enunciado: {evidencia}. "
        "Qual procedimento pratico torna a resposta mais consistente?"
    ),
    "analise": (
        "Situacao: ao analisar {cenario}, a classe relaciona {tema} com um problema real. "
        "Dados do enunciado: {evidencia}. "
        "Qual analise respeita melhor os dados, o contexto e o comando da questao?"
    ),
    "comparacao": (
        "Situacao: dois grupos discutem {tema} a partir de {cenario}. "
        "Dados do enunciado: {evidencia}. "
        "Qual criterio ajuda a comparar as respostas sem depender de palpite?"
    ),
    "decisao": (
        "Situacao: em {cenario}, uma decisao precisa ser tomada com base em {tema}. "
        "Dados do enunciado: {evidencia}. "
        "Qual escolha demonstra uso responsavel do conhecimento estudado?"
    ),
    "fonte": (
        "Situacao: a turma consulta materiais diferentes sobre {tema} em {cenario}. "
        "Dados do enunciado: {evidencia}. "
        "Qual atitude melhora a confiabilidade da conclusao?"
    ),
    "erro": (
        "Situacao: durante uma atividade sobre {tema}, um erro de interpretacao aparece em {cenario}. "
        "Dados do enunciado: {evidencia}. "
        "Qual alternativa corrige melhor esse erro?"
    ),
    "projeto": (
        "Situacao: estudantes montam um pequeno projeto sobre {tema} ligado a {cenario}. "
        "Dados do enunciado: {evidencia}. "
        "Qual encaminhamento une teoria, pratica e justificativa?"
    ),
}


CORRETAS_APLICADAS = {
    "Matematica": [
        "Identificar variaveis, escolher uma representacao adequada e verificar se o resultado faz sentido no contexto.",
        "Comparar tabela, grafico ou texto antes de decidir qual relacao matematica modela a situacao.",
        "Usar estimativa, unidade de medida e validacao para evitar uma resposta numerica sem significado.",
        "Explicar o padrao observado e testar a conclusao com pelo menos um caso do enunciado.",
    ],
    "Fisica": [
        "Reconhecer as grandezas envolvidas, as interacoes do sistema e o principio fisico que explica o fenomeno.",
        "Separar observacao cotidiana de explicacao fisica, relacionando causa, efeito e unidades.",
        "Analisar o sistema antes de aplicar qualquer formula, verificando quais forcas ou transformacoes atuam.",
        "Conferir se a conclusao respeita conservacao, transferencia de energia ou relacao entre grandezas.",
    ],
    "Quimica": [
        "Relacionar evidencias observaveis a particulas, ligacoes, propriedades e condicoes da transformacao.",
        "Distinguir mistura, substancia e reacao usando criterios de composicao e evidencias experimentais.",
        "Verificar se a explicacao considera estrutura da materia e nao apenas aparencia visual.",
        "Comparar dados do processo quimico com o objetivo do problema antes de classificar a situacao.",
    ],
    "Biologia": [
        "Relacionar estrutura, funcao e ambiente usando evidencias biologicas do enunciado.",
        "Analisar o processo vital ou ecologico considerando causas, consequencias e escala adequada.",
        "Usar dados sobre organismos, populacoes ou sistemas do corpo para justificar a conclusao.",
        "Evitar generalizacoes e explicar o caso com base nas relacoes biologicas apresentadas.",
    ],
    "Portugues": [
        "Ler genero, finalidade, interlocutor e contexto de circulacao para explicar o efeito de sentido.",
        "Relacionar marcas linguisticas ao objetivo do texto e ao publico a que ele se dirige.",
        "Comparar tese, argumento e recurso expressivo antes de escolher a interpretacao.",
        "Justificar a resposta por pistas do texto, sem isolar uma palavra fora do contexto.",
    ],
    "Historia": [
        "Comparar fonte, autoria, contexto e interesses envolvidos no processo historico.",
        "Identificar permanencias, mudancas e grupos sociais antes de explicar o acontecimento.",
        "Relacionar o fato ao tempo historico e evitar julgar o passado apenas por valores atuais.",
        "Usar evidencias das fontes para diferenciar interpretacao historica de opiniao solta.",
    ],
    "Geografia": [
        "Relacionar escala, localizacao, territorio e impacto socioambiental do fenomeno.",
        "Interpretar mapa, dado ou paisagem considerando distribuicao espacial e conexoes entre lugares.",
        "Comparar fatores naturais, economicos e sociais antes de explicar a organizacao do espaco.",
        "Avaliar consequencias territoriais da decisao, considerando atores e desigualdades envolvidas.",
    ],
    "Ingles": [
        "Use genre, context clues and communicative purpose to infer meaning before choosing an option.",
        "Identify the main idea and check how key words work in the text, not in isolation.",
        "Compare the options with evidence from the text and avoid translating word by word.",
        "Connect vocabulary, audience and purpose to understand the message in context.",
    ],
    "Ciencias": [
        "Formular uma explicacao que conecte observacao, evidencia, causa e consequencia.",
        "Comparar hipoteses com os dados apresentados antes de aceitar uma conclusao.",
        "Usar criterio cientifico para diferenciar fato observado, interpretacao e opiniao.",
        "Propor uma resposta que considere riscos, limites e impactos da situacao estudada.",
    ],
    "Educacao Fisica": [
        "Considerar regras, seguranca, participacao e inclusao ao adaptar a pratica corporal.",
        "Relacionar movimento, saude e cultura corporal sem reduzir a atividade a rendimento.",
        "Planejar a pratica respeitando limites corporais, cooperacao e objetivos da aula.",
        "Avaliar a situacao pelo bem-estar coletivo, pela estrategia e pelo respeito as diferencas.",
    ],
    "Arte": [
        "Observar linguagem, materialidade, contexto e intencao para interpretar a producao artistica.",
        "Relacionar forma, repertorio cultural e circulacao da obra antes de atribuir sentido.",
        "Comparar elementos visuais, sonoros ou corporais com o contexto de producao.",
        "Reconhecer autoria, tecnica e recepcao sem reduzir a obra a gosto pessoal.",
    ],
    "Filosofia": [
        "Identificar conceitos, pressupostos e consequencias do argumento apresentado.",
        "Comparar posicoes e justificar a escolha por coerencia argumentativa.",
        "Questionar a primeira resposta e explicitar os criterios usados no julgamento.",
        "Relacionar o dilema ao problema filosofico sem transformar a discussao em opiniao sem fundamento.",
    ],
    "Sociologia": [
        "Relacionar individuo, grupo, instituicoes e desigualdades ao analisar o fenomeno social.",
        "Diferenciar experiencia individual de explicacao sociologica considerando contexto historico.",
        "Observar como normas, poder e cultura influenciam a situacao apresentada.",
        "Usar dados sociais para explicar padroes coletivos sem culpar apenas escolhas individuais.",
    ],
    "Ensino Religioso": [
        "Reconhecer diversidade de crencas e praticas sem hierarquizar tradicoes.",
        "Promover dialogo respeitoso, distinguindo conhecimento sobre religioes de adesao religiosa.",
        "Analisar simbolos e ritos pelo contexto cultural e pelo direito a liberdade de crenca.",
        "Valorizar convivencia, escuta e direitos humanos diante da diferenca religiosa.",
    ],
}


EXATAS_TEORICAS = {
    "Matematica": {
        "conceito": "representar relacoes, padroes e propriedades para interpretar uma situacao",
        "corretas": [
            "Usar o conceito para reconhecer padroes, relacoes entre grandezas e propriedades envolvidas.",
            "Interpretar o significado das relacoes matematicas antes de escolher qualquer procedimento.",
            "Relacionar representacoes, como texto, tabela, grafico ou figura, ao conceito estudado.",
            "Identificar o que o conceito explica sobre a situacao, sem reduzir a questao a uma conta.",
        ],
        "distratores": [
            "Aplicar uma formula decorada mesmo sem compreender o que as grandezas representam.",
            "Escolher a alternativa com mais numeros, pois ela parece mais matematica.",
            "Ignorar o contexto e procurar apenas uma operacao para executar.",
            "Tratar qualquer grafico ou figura como detalhe decorativo do enunciado.",
        ],
    },
    "Fisica": {
        "conceito": "explicar fenomenos por meio de grandezas, interacoes e conservacoes",
        "corretas": [
            "Relacionar o fenomeno as grandezas fisicas envolvidas e ao principio que o explica.",
            "Observar quais interacoes, transformacoes ou conservacoes estao presentes na situacao.",
            "Interpretar causa e efeito do fenomeno antes de pensar em qualquer calculo.",
            "Diferenciar a descricao cotidiana do fenomeno da explicacao fisica adequada.",
        ],
        "distratores": [
            "Afirmar que todo fenomeno fisico depende apenas de velocidade.",
            "Escolher a alternativa que cita uma unidade de medida, mesmo fora do contexto.",
            "Explicar o fenomeno por senso comum, sem considerar grandezas ou interacoes.",
            "Supor que a presenca de movimento sempre elimina outras forcas do sistema.",
        ],
    },
    "Quimica": {
        "conceito": "relacionar estrutura da materia, propriedades e transformacoes quimicas",
        "corretas": [
            "Analisar propriedades, estrutura e evidencias para explicar a transformacao quimica.",
            "Relacionar o comportamento das substancias a sua composicao e as interacoes envolvidas.",
            "Interpretar a mudanca observada considerando particulas, ligacoes e condicoes do sistema.",
            "Distinguir evidencia experimental de conclusao quimica sobre a materia.",
        ],
        "distratores": [
            "Concluir que toda mudanca visual e necessariamente uma reacao quimica.",
            "Escolher a alternativa que cita uma substancia conhecida, mesmo sem relacao com o caso.",
            "Ignorar evidencias como formacao de gas, precipitado, energia ou mudanca de propriedades.",
            "Explicar a transformacao apenas pela cor, sem considerar estrutura e interacoes.",
        ],
    },
}


def _pergunta_teorica_exatas(materia: str, tema: str, cenario: str, indice: int) -> str:
    modelos = [
        "Em {cenario}, estudantes discutem {tema} pela perspectiva teorica. Qual alternativa expressa melhor a ideia central desse conceito?",
        "Antes de resolver exercicios, uma turma precisa compreender {tema} em {cenario}. Qual leitura conceitual e mais adequada?",
        "Ao analisar {cenario}, o tema {tema} aparece como explicacao teorica. Qual afirmacao interpreta melhor o conceito?",
        "Em uma conversa sobre {tema}, baseada em {cenario}, qual alternativa evita decorar procedimentos e prioriza compreensao?",
        "Situacao: em {cenario}, a turma observa {tema} aplicado a um caso real. Qual interpretacao usa o conceito sem transformar a questao em conta mecanica?",
        "Durante uma revisao de {tema}, estudantes comparam exemplos de {cenario}. Qual criterio teorico ajuda a separar conclusao valida de chute?",
        "Em {cenario}, uma solucao parece correta porque repete palavras do tema {tema}. Qual alternativa mostra compreensao real do conceito?",
        "Ao preparar uma explicacao sobre {tema} para colegas, usando {cenario}, qual afirmacao conecta teoria e aplicacao de modo adequado?",
        "Em um estudo orientado sobre {tema}, a classe registra observacoes de {cenario}. Qual leitura conceitual permite justificar a resposta?",
        "Situacao: dois grupos analisam {cenario} e discordam sobre {tema}. Qual alternativa indica o melhor caminho para resolver a divergencia?",
        "Ao avaliar uma resposta pronta sobre {tema} em {cenario}, qual ponto precisa aparecer para que a explicacao seja teoricamente correta?",
        "Em uma atividade aplicada de {tema}, com base em {cenario}, qual alternativa evita usar formulas sem entender as relacoes envolvidas?",
    ]
    return modelos[indice % len(modelos)].format(cenario=cenario, tema=tema)


def _opcoes_teoricas_exatas(materia: str, indice: int, tema: str = "", cenario: str = "") -> tuple[list[str], int]:
    perfil = EXATAS_TEORICAS[materia]
    corretas = perfil["corretas"] + CORRETAS_APLICADAS.get(materia, [])
    corretas.extend(
        [
            f"Explicar {tema} a partir das relacoes observadas em {cenario}, conferindo coerencia conceitual.",
            f"Diferenciar o conceito de {tema} de uma receita de resolucao, usando o contexto como criterio.",
        ]
    )
    correta = corretas[indice % len(corretas)]
    distratores_base = perfil["distratores"]
    distratores_base = distratores_base + [
        f"Tratar {tema} como termo suficiente para responder, sem analisar o caso.",
        f"Usar {cenario} apenas como enfeite do enunciado, sem relaciona-lo ao conceito.",
        "Aceitar a primeira conclusao que parece familiar, mesmo sem evidencias.",
        "Misturar definicoes parecidas sem verificar qual delas se aplica ao problema.",
    ]
    inicio = (indice * 2) % len(distratores_base)
    opcoes = [distratores_base[(inicio + offset) % len(distratores_base)] for offset in range(3)]
    correta_idx = indice % 4
    opcoes.insert(correta_idx, correta)
    return opcoes, correta_idx


def _explicacao_teorica_exatas(materia: str, tema: str, habilidade: str) -> list[dict[str, str]]:
    conceito = EXATAS_TEORICAS[materia]["conceito"]
    return [
        {"tipo": "bold", "conteudo": f"Conceito em foco ({habilidade})"},
        {"tipo": "texto", "conteudo": f"Em {tema}, o ponto principal e {conceito}."},
        {"tipo": "texto", "conteudo": "No Oraculo, a questao prioriza compreensao teorica; contas e formulas ficam para o Laboratorio de Exatas."},
        {"tipo": "resultado", "conteudo": "A alternativa correta explica o conceito, nao apenas um procedimento de calculo."},
    ]


def _nivel_por_indice(indice: int) -> str:
    return ("Facil", "Medio", "Dificil")[indice % 3]


def _fonte_bncc(materia: str) -> str:
    if materia == "Matematica":
        return "https://catalogobncc.github.io/metadados/2022/03/30/emmat"
    if materia in {"Historia", "Geografia", "Filosofia", "Sociologia"}:
        return "https://catalogobncc.github.io/metadados/2022/03/30/emchs"
    if materia == "Portugues":
        return "https://bncc.digital/EM13LP01"
    return "https://bncc.digital/EM13CNT101"


def _pergunta_realista(materia: str, tema: str, cenario: str, indice: int) -> str:
    evidencia = EVIDENCIAS[indice % len(EVIDENCIAS)]
    modelos = list(PERGUNTAS_REALISTAS.values())
    return modelos[indice % len(modelos)].format(
        acao=SITUACOES_APLICADAS[indice % len(SITUACOES_APLICADAS)],
        cenario=cenario,
        evidencia=evidencia,
        tema=tema,
    )


def _opcoes_realistas(materia: str, indice: int, tema: str, cenario: str) -> tuple[list[str], int]:
    _foco, estrategia = PERFIS.get(materia, PERFIS["Ciencias"])
    corretas = CORRETAS_APLICADAS.get(materia, CORRETAS_APLICADAS["Ciencias"]) + [
        f"Selecionar dados relevantes de {cenario}, aplicar {tema} e conferir se a conclusao responde ao comando.",
        f"Relacionar {tema} ao contexto apresentado, justificar a resposta e comparar as alternativas com evidencias.",
        estrategia.capitalize(),
        f"Explicar {tema} usando o dado central do enunciado, sem isolar palavras-chave.",
    ]
    distratores = [
        f"Escolher a alternativa que apenas menciona {tema}, mesmo sem responder ao problema.",
        "Resolver pela primeira impressao, pois o contexto e apenas decorativo.",
        "Priorizar a opcao mais longa, ja que ela tende a parecer mais completa.",
        "Ignorar os dados apresentados e aplicar uma regra memorizada.",
        "Usar somente uma palavra do enunciado como pista para marcar a resposta.",
        "Comparar alternativas pelo vocabulario, sem verificar coerencia com a situacao.",
        "Confundir opiniao pessoal com justificativa baseada no material analisado.",
        "Desconsiderar autoria, finalidade, escala ou limite dos dados apresentados.",
        "Escolher a resposta que parece mais moderna, mesmo sem relacao com o problema.",
        "Generalizar um exemplo isolado como se ele explicasse toda a situacao.",
    ]
    correta = corretas[indice % len(corretas)]
    inicio = (indice * 2) % len(distratores)
    opcoes = [distratores[(inicio + offset) % len(distratores)] for offset in range(3)]
    correta_idx = indice % 4
    opcoes.insert(correta_idx, correta)
    return opcoes, correta_idx


def _explicacao_para_materia(materia: str, tema: str, habilidade: str) -> list[dict[str, str]]:
    foco, estrategia = PERFIS.get(materia, PERFIS["Ciencias"])
    return [
        {"tipo": "bold", "conteudo": f"Relação com a BNCC ({habilidade})"},
        {"tipo": "texto", "conteudo": f"Em {tema}, o objetivo é {foco}."},
        {"tipo": "texto", "conteudo": f"A melhor saída é {estrategia}, conferindo contexto, dados e alternativas."},
        {"tipo": "resultado", "conteudo": "A alternativa correta conecta o tema ao raciocínio pedido e às evidências do enunciado."},
    ]


def _gerar_banco_materia(materia: str) -> list[dict]:
    temas = TEMAS_BASE_EM.get(materia, TEMAS_BASE_EM["Ciencias"])
    cenarios = CENARIOS.get(materia, CENARIOS["Ciencias"])
    area, competencia, codigo = BNCC_REFERENCIAS.get(materia, BNCC_REFERENCIAS["Ciencias"])
    banco_especifico_materia = BANCO_ESPECIFICO_EM.get(materia, {})
    questoes = []

    for tema_indice, tema_base in enumerate(temas):
        especificas = banco_especifico_materia.get(tema_base) or []
        for variacao in range(QUESTOES_POR_TEMA_EM):
            indice = tema_indice * QUESTOES_POR_TEMA_EM + variacao
            contexto = CONTEXTOS[variacao % len(CONTEXTOS)]
            tema_unico = f"{tema_base} - {contexto}"
            cenario = cenarios[indice % len(cenarios)]
            if especificas:
                # MELHORIA: quando ha conteudo especifico pra este tema (ver
                # services/oraculo_conteudo_especifico.py), ele substitui o
                # template generico que so testava raciocinio meta-cognitivo
                # ("qual leitura conceitual e mais adequada"), sem cobrar
                # conhecimento de conteudo de verdade.
                especifica = especificas[variacao % len(especificas)]
                embaralhada = embaralhar_opcoes_questao(
                    {"opcoes": list(especifica["opcoes"]), "correta": int(especifica["correta"])}
                )
                pergunta = especifica["pergunta"]
                opcoes = embaralhada["opcoes"]
                correta_idx = embaralhada["correta"]
                explicacao = list(especifica["explicacao"])
                # MELHORIA: o titulo era "Oraculo: {tema} aparece em {cenario}." --
                # e "Oraculo teorico:"/"Banco offline BNCC:" nos ramos abaixo --, e
                # ele vai como titulo da questao no Treino, no Oraculo e no Escape:
                # o aluno lia o nome interno do banco. Medido em 15/09/2026: as
                # 24.000 questoes deste banco.
                enigma = _titulo_no_cenario(tema_base, cenario)
            elif materia in EXATAS_TEORICAS:
                pergunta = _pergunta_teorica_exatas(materia, tema_base, cenario, indice)
                opcoes, correta_idx = _opcoes_teoricas_exatas(materia, indice, tema_base, cenario)
                explicacao = _explicacao_teorica_exatas(materia, tema_base, codigo)
                enigma = _titulo_no_cenario(tema_base, cenario)
            else:
                pergunta = _pergunta_realista(materia, tema_base, cenario, indice)
                opcoes, correta_idx = _opcoes_realistas(materia, indice, tema_base, cenario)
                explicacao = _explicacao_para_materia(materia, tema_base, codigo)
                enigma = _titulo_no_cenario(tema_base, cenario)
            questoes.append(
                {
                    "id_offline": f"EM-{materia}-{indice + 1:03d}",
                    "materia": materia,
                    "serie_tipo": "EM",
                    "tema_usado": tema_unico,
                    "objeto_conhecimento": tema_base,
                    "dificuldade": _nivel_por_indice(indice),
                    "area_bncc": area,
                    "competencia_bncc": competencia,
                    "habilidade_bncc": HABILIDADES_BNCC.get(materia, ""),
                    "codigo_bncc": codigo,
                    "fonte_bncc": _fonte_bncc(materia),
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


BANCO_OFFLINE_EM = LazyMateriaBank(MATERIAS, _gerar_banco_materia, fallback=None)


# eh_ensino_medio mora em core/config.py, junto de SERIES: a decisao vale
# para todos os modos e vivia repetida em cinco lugares, com listas
# diferentes. Fica re-exportada aqui porque services/ia/enigma.py a importa
# deste modulo.


def listar_questoes_em(materia: str) -> list[dict]:
    materia_norm = normalizar_materia(materia)
    return deepcopy(BANCO_OFFLINE_EM.get(materia_norm, []))


def gerar_questao_offline_em(
    materia: str,
    tema: str = "",
    nivel: str = "",
    evitar_ids: list[str] | set[str] | tuple[str, ...] | None = None,
) -> dict:
    materia_norm = normalizar_materia(materia)
    questoes = BANCO_OFFLINE_EM.get(materia_norm) or BANCO_OFFLINE_EM["Ciencias"]
    questao = selecionar_questao_offline(
        questoes, tema, seed=f"{materia_norm}|{tema}|{nivel}", evitar_ids=evitar_ids
    )
    if nivel:
        questao["dificuldade"] = str(nivel)
    return questao
