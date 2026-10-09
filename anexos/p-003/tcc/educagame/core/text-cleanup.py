from __future__ import annotations

import re
import unicodedata
from typing import Any


def chave_busca(texto: str) -> str:
    """Reduz um texto a uma chave ASCII minuscula, usada para casar temas/buscas."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or ""))
    return sem_acento.encode("ascii", "ignore").decode("ascii").strip().lower()


_MOJIBAKE = {
    "Ã¡": "á",
    "Ã ": "à",
    "Ã¢": "â",
    "Ã£": "ã",
    "Ã©": "é",
    "Ãª": "ê",
    "Ã­": "í",
    "Ã³": "ó",
    "Ã´": "ô",
    "Ãµ": "õ",
    "Ãº": "ú",
    "Ã§": "ç",
    "Ã": "Á",
    "Ã€": "À",
    "Ã‚": "Â",
    "Ãƒ": "Ã",
    "Ã‰": "É",
    "ÃŠ": "Ê",
    "Ã": "Í",
    "Ã“": "Ó",
    "Ã”": "Ô",
    "Ã•": "Õ",
    "Ãš": "Ú",
    "Ã‡": "Ç",
    "Âº": "º",
    "Â²": "²",
    "Â³": "³",
}

_PALAVRAS_PT = {
    "acido": "ácido",
    "acidos": "ácidos",
    "aceleracao": "aceleração",
    "agua": "água",
    "angulo": "ângulo",
    "area": "área",
    "aritmetica": "aritmética",
    "atencao": "atenção",
    "ate": "até",
    "alianca": "aliança",
    "alguem": "alguém",
    "ameaca": "ameaça",
    "atras": "atrás",
    "avancar": "avançar",
    "basica": "básica",
    "calculo": "cálculo",
    "camara": "câmara",
    "cinetica": "cinética",
    "colaboracao": "colaboração",
    "condicoes": "condições",
    "concentracao": "concentração",
    "confianca": "confiança",
    "contem": "contém",
    "conteudo": "conteúdo",
    "decisao": "decisão",
    "desapareca": "desapareça",
    "eletrica": "elétrica",
    "eletricos": "elétricos",
    "evidencias": "evidências",
    "equacao": "equação",
    "equacoes": "equações",
    "fisica": "física",
    "formula": "fórmula",
    "formulas": "fórmulas",
    "forcar": "forçar",
    "funcao": "função",
    "funcoes": "funções",
    "hidrogenionica": "hidrogeniônica",
    "impossiveis": "impossíveis",
    "interacoes": "interações",
    "interpretacao": "interpretação",
    "ja": "já",
    "laboratorio": "laboratório",
    "lembranca": "lembrança",
    "matematica": "matemática",
    "materia": "matéria",
    "mecanica": "mecânica",
    "mecanico": "mecânico",
    "medio": "médio",
    "mes": "mês",
    "movel": "móvel",
    "numero": "número",
    "numerica": "numérica",
    "numericas": "numéricas",
    "numerico": "numérico",
    "numericos": "numéricos",
    "operacao": "operação",
    "operacoes": "operações",
    "oraculo": "oráculo",
    "observatorio": "observatório",
    "bussola": "bússola",
    "particulas": "partículas",
    "padrao": "padrão",
    "padroes": "padrões",
    "possiveis": "possíveis",
    "poco": "poço",
    "potencia": "potência",
    "pressao": "pressão",
    "proxima": "próxima",
    "proximo": "próximo",
    "progressao": "progressão",
    "proporcao": "proporção",
    "proporcoes": "proporções",
    "questao": "questão",
    "quimica": "química",
    "quimicos": "químicos",
    "raizes": "raízes",
    "razao": "razão",
    "razoes": "razões",
    "relacao": "relação",
    "relacoes": "relações",
    "reacao": "reação",
    "reacoes": "reações",
    "resolucao": "resolução",
    "runico": "rúnico",
    "retangulo": "retângulo",
    "sao": "são",
    "sera": "será",
    "serao": "serão",
    "seguranca": "segurança",
    "situacao": "situação",
    "solucao": "solução",
    "solucoes": "soluções",
    "substancia": "substância",
    "tatica": "tática",
    "transformacoes": "transformações",
    "tensao": "tensão",
    "teorica": "teórica",
    "teorico": "teórico",
    "triangulo": "triângulo",
    "variacao": "variação",
    "valvulas": "válvulas",
    "variavel": "variável",
    "variaveis": "variáveis",
    "velocidade media": "velocidade média",
    # MELHORIA: mesma saida da linha acima, pelo mesmo motivo. "media"
    # sozinha nao entra no dicionario porque em ingles e palavra correta
    # (social media), e a funcao nao sabe a materia. Mas a FRASE nao e
    # ambigua em lingua nenhuma, e "Idade Media" chegava crua ao aluno em
    # dois lugares: "Tema: Idade Media" no RPG e "Desafio de Idade Media"
    # no enigma do banco do Fundamental.
    "idade media": "idade média",
    "compreensao": "compreensão",
    "nao": "não",
    "voce": "você",
}

_PALAVRAS_PT.update(
    {
        # Narrativa do RPG (15/09/2026): "a acao", "de forma visivel", "duelo
        # academico" -- 40 ocorrencias em 14 fases jogadas sem IA.
        "acao": "ação",
        "visivel": "visível",
        "academico": "acadêmico",
        "conclusao": "conclusão",
        "conclusoes": "conclusões",
        "consequencia": "consequência",
        "consequencias": "consequências",
        "contraditorias": "contraditórias",
        "criterio": "critério",
        "historico": "histórico",
        "historicos": "históricos",
    }
)

# MELHORIA: o RPG escreve seus textos em ASCII e conta com este dicionario
# para acentuar na hora de exibir. As palavras abaixo faltavam, e na mesma
# tela conviviam "Bússola de retorno" e "Lente de verificacao", "Câmara
# Rubra" e "Jardim dos Simbolos". Palavras curtas e ambiguas ("so", "da",
# "e") ficam de fora de proposito: casam com trechos legitimos -- inclusive
# em ingles -- e sao corrigidas na origem.
_PALAVRAS_PT.update(
    {
        "aliancas": "alianças",
        "argumentacao": "argumentação",
        "expressao": "expressão",
        "condicao": "condição",
        "condicoes": "condições",
        "distancia": "distância",
        "necessario": "necessário",
        "parabola": "parábola",
        "parabolico": "parabólico",
        "populacao": "população",
        "preparacao": "preparação",
        "resistencia": "resistência",
        "revisao": "revisão",
        "simulacao": "simulação",
        "unico": "único",
        "expressoes": "expressões",
        "peca": "peça",
        "pecas": "peças",
        "projetil": "projétil",
        "quadratica": "quadrática",
        "avanca": "avança",
        # Os temas do app (core/config.py::TEMAS_RPG) passaram a ir para a
        # tela do professor em 29/09/2026, no foco de estudo; "ecologia
        # avancada" era o unico dos 286 com palavra que o dicionario nao
        # conhecia. Sem forma verbal sem cedilha: nao ha ambiguidade.
        "avancada": "avançada",
        "avancadas": "avançadas",
        "avancado": "avançado",
        "avancados": "avançados",
        "caldeirao": "caldeirão",
        "divisao": "divisão",
        "intencao": "intenção",
        "mudanca": "mudança",
        "validacao": "validação",
        "astrolabio": "astrolábio",
        "cenario": "cenário",
        "coerencia": "coerência",
        "confiavel": "confiável",
        "cooperacao": "cooperação",
        "decisoes": "decisões",
        "distorca": "distorça",
        "equilibrio": "equilíbrio",
        "estrategia": "estratégia",
        "estrategica": "estratégica",
        "evidencia": "evidência",
        "forcas": "forças",
        "genero": "gênero",
        "guardia": "guardiã",
        "guardiao": "guardião",
        "hipoteses": "hipóteses",
        "inercia": "inércia",
        "informacoes": "informações",
        "insignia": "insígnia",
        "instaveis": "instáveis",
        "invisiveis": "invisíveis",
        "lider": "líder",
        "logica": "lógica",
        "maquinas": "máquinas",
        "memoria": "memória",
        "memorias": "memórias",
        "ninguem": "ninguém",
        "nucleo": "núcleo",
        "observacao": "observação",
        "pagina": "página",
        "publico": "público",
        "residuos": "resíduos",
        "silencio": "silêncio",
        "simbolos": "símbolos",
        "subterranea": "subterrânea",
        "subterraneo": "subterrâneo",
        "tatico": "tático",
        "unica": "única",
        "verificacao": "verificação",
        "versao": "versão",
    }
)

_FRASES_PT = {
    # "pre" sozinho nao entra como palavra: e prefixo, e acentuar todo
    # "pre" solto seria regra larga demais para um caso so. Tema do app.
    "pre-historia": "pré-história",
    "qual e": "qual é",
    "qual sera": "qual será",
    "qual sera o": "qual será o",
    "qual e sua": "qual é sua",
    "qual e a": "qual é a",
    "qual e o": "qual é o",
    "qual e f": "qual é f",
    # MELHORIA: estas onze eram " e a corrente", " e a forca"... -- sem o
    # "qual" -- e pegavam CONJUNCAO: "indústria de base e a nova capital"
    # virava "base é a nova capital", "a frequência aumenta e sua velocidade
    # permanece" virava "aumenta é sua velocidade". Antes do conserto do espaco
    # (ver _manter_capitalizacao) isso saia colado, "baseé", e se via; depois,
    # passaria por certo. Medido no banco inteiro: das 688 vezes em que elas
    # agiam, 648 vinham depois de "Qual" (verbo, certo) e 40 eram esses dois
    # textos (conjuncao, errado). Presas a "qual", as 648 saem iguais, as 40
    # voltam a "e", e nenhum acento se perde.
    #
    # Nao da para simplesmente tira-las: "Qual e a forca" perderia a cedilha,
    # e "forca" nao pode ir para _PALAVRAS_PT -- e tambem a da execucao
    # ("condenado à forca", em Historia).
    "qual e sua area": "qual é sua área",
    "qual e sua velocidade": "qual é sua velocidade",
    "qual e o termo": "qual é o termo",
    "qual e a probabilidade": "qual é a probabilidade",
    "qual e a distancia": "qual é a distância",
    "qual e a densidade": "qual é a densidade",
    "qual e a nova": "qual é a nova",
    "qual e a corrente": "qual é a corrente",
    "qual e a forca": "qual é a força",
    "qual e a potencia": "qual é a potência",
    "qual e a velocidade": "qual é a velocidade",
    "risco e alto": "risco é alto",
    # "principal e" -> "principal é" SAIU pelo mesmo motivo: as 29 vezes em
    # que agia no banco eram "rio principal e seus afluentes" (conjuncao), e
    # nenhuma era verbo.
    "objetivo e": "objetivo é",
    "apos ": "após ",
    "mudara": "mudará",
    "podem ser usados para avancar": "podem ser usados para avançar",
    # MELHORIA: temas com palavra que SOZINHA e ambigua (ver o bloco de
    # 13/09/2026 em _PALAVRAS_PT): "analise" tambem e o imperativo de "Analise
    # o grafico"; "comercio" e "dialogo" tambem sao verbo. Presas ao que vem
    # junto, so casam o substantivo. Medido nos bancos: "uma analise de" (89),
    # "Na analise de" (88), "de analise combinatoria" (48), "de comercio
    # internacional" (48), "de dialogo" (40).
    "analise combinatoria": "análise combinatória",
    "analise sintatica": "análise sintática",
    "analise critica": "análise crítica",
    "uma analise": "uma análise",
    "na analise": "na análise",
    "comercio internacional": "comércio internacional",
    "dialogo inter-religioso": "diálogo inter-religioso",
    "de dialogo": "de diálogo",
    "taxas e indices": "taxas e índices",
    # MELHORIA: "respeito a diversidade religiosa" e tema do RPG e aparece em
    # 852 textos, sempre pedindo crase (quem respeita, respeita A algo). Fica
    # aqui, e nao em _PALAVRAS_PT, porque so o "a" antes de "diversidade"
    # vira "a" com crase -- "a diversidade e grande" continua sem.
    "respeito a diversidade": "respeito à diversidade",
}


# MELHORIA: palavras que o banco offline e a IA escrevem em ASCII e chegavam
# cruas ao aluno, ao lado de palavras ja acentuadas na MESMA frase -- medido
# no simulado do ENEM: "Uma familia fara uma viagem... A distancia total".
#
# "farao" ficou de fora de proposito: em portugues mesmo ele e ambiguo --
# "farao" (do verbo fazer) e "faraó" (do Egito) escrevem igual sem acento, e
# a segunda aparece em questao de Historia.
_PALAVRAS_PT.update(
    {
        "aparencia": "aparência",
        "aparencias": "aparências",
        "aplicacao": "aplicação",
        "aplicacoes": "aplicações",
        "ausencias": "ausências",
        "basico": "básico",
        "combustivel": "combustível",
        "competencia": "competência",
        "competencias": "competências",
        "disponivel": "disponível",
        "distancias": "distâncias",
        "estrategia": "estratégia",
        "exercicio": "exercício",
        "exercicios": "exercícios",
        "familia": "família",
        "familias": "famílias",
        "fara": "fará",
        "grafico": "gráfico",
        "graficos": "gráficos",
        "hipotese": "hipótese",
        "instavel": "instável",
        "maximo": "máximo",
        "memorizacao": "memorização",
        "minimo": "mínimo",
        "niveis": "níveis",
        "nivel": "nível",
        "numeros": "números",
        "perimetro": "perímetro",
        "possiveis": "possíveis",
        "possivel": "possível",
        "propria": "própria",
        "proprio": "próprio",
        "situacoes": "situações",
        "tambem": "também",
        "titulo": "título",
        "util": "útil",
        "veiculo": "veículo",
        "veiculos": "veículos",
    }
)

# Vocabulario de exatas que chegava cru ao aluno -- visto no RPG, num
# enunciado de Matematica: "tem vertice em qual ponto?".
#
# "vertices" e tambem o plural ingles de "vertex". Entra assim mesmo: em
# frase inglesa o reconhecimento de idioma (texto_parece_ingles) desliga o
# dicionario inteiro, e em portugues "vertices" e muito mais frequente.
_PALAVRAS_PT.update(
    {
        "circunferencia": "circunferência",
        "diametro": "diâmetro",
        "divisivel": "divisível",
        "dominio": "domínio",
        "fracao": "fração",
        "fracoes": "frações",
        "incognita": "incógnita",
        "multiplo": "múltiplo",
        "multiplos": "múltiplos",
        "parabolas": "parábolas",
        "polinomio": "polinômio",
        "polinomios": "polinômios",
        "sequencia": "sequência",
        "trapezio": "trapézio",
        "vertice": "vértice",
        "vertices": "vértices",
    }
)

# Segunda leva, de palavras comuns em enunciado e explicacao.
#
# Ficam de fora, e o motivo importa mais que a lista: "ciencia(s)",
# "historia" e "materias" encostam em CHAVE -- "Ciencias da Natureza e suas
# Tecnologias" e chave de AREAS_ENEM, "Historia" e nome normalizado de
# materia, e normalizar_payload_questao acentua o campo "area_bncc". Acentuar
# ali nao seria ortografia: seria a chave deixar de casar. Quem exibe com
# acento e LABEL_AREA / MATERIAS_COM_ACENTO.
#
# "series" fica de fora por outro motivo: e palavra em ingles.
_PALAVRAS_PT.update(
    {
        "automatico": "automático",
        "codigo": "código",
        "coracao": "coração",
        "eficiencia": "eficiência",
        "especifico": "específico",
        "experiencia": "experiência",
        "experiencias": "experiências",
        "frequencia": "frequência",
        "importancia": "importância",
        "industria": "indústria",
        "industrias": "indústrias",
        "musica": "música",
        "musicas": "músicas",
        "periodo": "período",
        "periodos": "períodos",
        "pratico": "prático",
        "proximos": "próximos",
        "questoes": "questões",
        "quimico": "químico",
        "referencia": "referência",
        "referencias": "referências",
        "relatorio": "relatório",
        "saida": "saída",
        "serie": "série",
        "sessao": "sessão",
        "silaba": "sílaba",
        "substancias": "substâncias",
        "tecnico": "técnico",
        "tendencia": "tendência",
        "ultimo": "último",
        "ultimos": "últimos",
        "unicos": "únicos",
        "usuario": "usuário",
    }
)

# MELHORIA: os temas do banco do Fundamental chegavam a tela sem acento --
# "regra de tres simples", "celulas", "atomos e moleculas", "danca", "volei".
# Medido: 39 dos 121 temas. O dicionario e palavra a palavra e nao flexiona,
# entao tinha "area" e nao "areas", "fisica" e nao "fisicas", "historico" e
# nao "historia". Entram singular e plural de cada uma.
#
# "media" continua FORA de proposito: em ingles e palavra correta (social
# media) e o dicionario nao sabe a materia. "Idade Media" ganha rotulo, que
# e a regra deste projeto -- a chave fica, o rotulo vem ao lado.
_PALAVRAS_PT.update(
    {
        "tres": "três",
        "areas": "áreas",
        "solido": "sólido",
        "solidos": "sólidos",
        "potencia": "potência",
        "potencias": "potências",
        "sequencia": "sequência",
        "sequencias": "sequências",
        "poluicao": "poluição",
        "saude": "saúde",
        "homogenea": "homogênea",
        "homogeneas": "homogêneas",
        "heterogenea": "heterogênea",
        "heterogeneas": "heterogêneas",
        "separacao": "separação",
        "atomo": "átomo",
        "atomos": "átomos",
        "molecula": "molécula",
        "moleculas": "moléculas",
        "quimicas": "químicas",
        "celula": "célula",
        "celulas": "células",
        "digestorio": "digestório",
        "respiratorio": "respiratório",
        "fotossintese": "fotossíntese",
        "acentuacao": "acentuação",
        "pontuacao": "pontuação",
        "sinonimo": "sinônimo",
        "sinonimos": "sinônimos",
        "antonimo": "antônimo",
        "antonimos": "antônimos",
        "historia": "história",
        "historias": "histórias",
        "indigena": "indígena",
        "indigenas": "indígenas",
        "colonizacao": "colonização",
        "orientacao": "orientação",
        "regiao": "região",
        "regioes": "regiões",
        "urbanizacao": "urbanização",
        "volei": "vôlei",
        "ginastica": "ginástica",
        "fisicas": "físicas",
        "olimpica": "olímpica",
        "olimpicas": "olímpicas",
        "olimpico": "olímpico",
        "olimpicos": "olímpicos",
        "danca": "dança",
        "dancas": "danças",
        "patrimonio": "patrimônio",
        "etica": "ética",
        "convivencia": "convivência",
        "manifestacao": "manifestação",
        "manifestacoes": "manifestações",
        "tradicao": "tradição",
        "tradicoes": "tradições",
    }
)

# MELHORIA: o tema sorteado sai de core/config.py em ASCII e so ganha acento
# aqui, na tela. Visto em 13/09/2026 em explicacoes reais do Oraculo:
# "Entendendo Redemocratizacao". Medido: 80 dos 286 temas mostravam palavra sem
# acento, e nenhuma era problema de maiuscula -- faltava a entrada.
#
# Ficam DE FORA as que tambem sao verbo: "analise" ("Analise o grafico"),
# "critica" ("o autor critica"), "comercio", "dialogo" e "indices" (indice/
# indicar). Palavra solta aqui vale para todo texto do app.
_PALAVRAS_PT.update(
    {
        "agroquimicos": "agroquímicos",
        "algebricas": "algébricas",
        "analitica": "analítica",
        "artistica": "artística",
        "artisticas": "artísticas",
        "atomistica": "atomística",
        "bacterias": "bactérias",
        "basicas": "básicas",
        "cinematica": "cinemática",
        "circulatorio": "circulatório",
        "climaticas": "climáticas",
        "coesao": "coesão",
        "combinatoria": "combinatória",
        "combustiveis": "combustíveis",
        "concordancia": "concordância",
        "contemporanea": "contemporânea",
        "distribuicao": "distribuição",
        "economicos": "econômicos",
        "educacao": "educação",
        "eletromagnetico": "eletromagnético",
        "eletronica": "eletrônica",
        "eletronicos": "eletrônicos",
        "eletroquimica": "eletroquímica",
        "eletrostatica": "eletrostática",
        "energeticas": "energéticas",
        "escravidao": "escravidão",
        "estatistica": "estatística",
        "estetica": "estética",
        "evolucao": "evolução",
        "fisicos": "físicos",
        "genetica": "genética",
        "geometrica": "geométrica",
        "geopolitica": "geopolítica",
        "globalizacao": "globalização",
        "grecia": "grécia",
        "hidrostatica": "hidrostática",
        "horarios": "horários",
        "independencia": "independência",
        "inorganicas": "inorgânicas",
        "instituicoes": "instituições",
        "lancamento": "lançamento",
        "lesoes": "lesões",
        "ligacoes": "ligações",
        "logaritmica": "logarítmica",
        "mesopotamia": "mesopotâmia",
        "migratorios": "migratórios",
        "mudancas": "mudanças",
        "navegacoes": "navegações",
        "nutricao": "nutrição",
        "optica": "óptica",
        "organica": "orgânica",
        "periodica": "periódica",
        "politica": "política",
        "prevencao": "prevenção",
        "producao": "produção",
        "projeteis": "projéteis",
        "radiacoes": "radiações",
        "redemocratizacao": "redemocratização",
        "regencia": "regência",
        "revolucao": "revolução",
        "sintatica": "sintática",
        "sistematica": "sistemática",
        "socioeconomicos": "socioeconômicos",
        "tectonicas": "tectônicas",
        "termodinamica": "termodinâmica",
        "termoquimica": "termoquímica",
        "vegetacao": "vegetação",
        "virus": "vírus",
        "vocabulario": "vocabulário",
    }
)


# MELHORIA: o relatorio de QA de 23/09/2026 (item 5.1) listou ~30 palavras
# sem acento na tela, "a maioria no banco autoral". Varrido o projeto inteiro
# em 28/09/2026, eram muito mais: so "explicacao" aparece em 26.004 textos, e
# nenhuma destas estava no dicionario. Entre parenteses, os textos afetados.
_PALAVRAS_PT.update(
    {
        "explicacao": "explicação",     # 26.004
        "explicacoes": "explicações",
        "impedira": "impedirá",         # 977
        "cientifica": "científica",     # 550
        "atomico": "atômico",           # 452
        "atomica": "atômica",
        "atomicos": "atômicos",
        "atomicas": "atômicas",
        "chao": "chão",                 # 261
        "crencas": "crenças",           # 254
        "crenca": "crença",
        "diluicao": "diluição",         # 178
        "diluicoes": "diluições",
        "maquina": "máquina",           # 88
        "havera": "haverá",             # 40
        "indice": "índice",             # 40
        "alcanca": "alcança",           # 40
        "favoraveis": "favoráveis",     # 20
        "favoravel": "favorável",
        "entao": "então",               # 20
        # Achadas em 28/09 junto com o detector de idioma: os moldes do RPG
        # e do Escape Room em Ingles ficavam sem elas.
        "raciocinio": "raciocínio",
        "raciocinios": "raciocínios",
        "interpretacoes": "interpretações",
    }
)


def _manter_capitalizacao(correto: str, original: str) -> str:
    # MELHORIA: so a PRIMEIRA letra era preservada, e isso bastava enquanto as
    # entradas eram de uma palavra. Com frase no dicionario o resultado ficava
    # errado em nome proprio: "Idade Media" virava "Idade média".
    #
    # Agora a capitalizacao acompanha palavra a palavra, quando a substituicao
    # tem a mesma quantidade de palavras que o original.
    palavras_originais = original.split()
    palavras_corretas = correto.split()
    if len(palavras_originais) == len(palavras_corretas) > 1:
        # MELHORIA: o split()/join() jogava fora o espaco das pontas, e o
        # dicionario tem frases que COMECAM com espaco (" e a corrente"). O
        # trecho trocado voltava sem ele e colava na palavra anterior: "Qual e
        # a corrente?" virava "Qualé a corrente?". Medido: 628 perguntas do
        # banco proprio saiam assim, e 10 das 17 questoes reais de 11/09/2026.
        inicio = correto[: len(correto) - len(correto.lstrip())]
        fim = correto[len(correto.rstrip()):]
        miolo = " ".join(
            p[:1].upper() + p[1:] if o[:1].isupper() else p
            for o, p in zip(palavras_originais, palavras_corretas)
        )
        return f"{inicio}{miolo}{fim}"

    if not original[:1].isupper():
        return correto
    return correto[:1].upper() + correto[1:]


# MELHORIA: o dicionario de acentos e de portugues, mas ele roda em texto de
# TODOS os modos -- e o Oraculo de Ingles escreve em ingles. Duas entradas
# legitimas em portugues sao palavra comum em ingles:
#
#     "ate"  -> "até"     mas "ate" e o passado de "eat"
#     "area" -> "área"    mas "area" e a mesma palavra em ingles
#
# Visto assim, de ponta a ponta: a explicacao da resposta certa de uma
# questao de simple past chegava ao aluno como
#
#     The simple past of "eat" is "até". She até lunch...
#
# ou seja, o app introduzia o erro exatamente onde a grafia E a licao.
#
# services/ia/normalizacao.py ja tomava esse cuidado (todo aplicar_acentos_pt
# la esta sob "if not modo_ingles"), mas a camada de apresentacao do Flask
# refazia a correcao sem saber a materia: web/routes/flask_helpers_fla.py
# ::texto_explicacao chama esta funcao em cima do que o servico ja protegeu.
# Passar a materia por seis rotas seria remendar cada chamada; reconhecer o
# idioma aqui protege todas de uma vez, inclusive as que nao tem como saber.
#
# So marcadores que NAO sao tambem palavra em portugues: "a", "as", "e", "no",
# "na", "ha" e "ate" ficam de fora justamente por serem das duas linguas.
_MARCADORES_INGLES = frozenset(
    """the of and is are was were does did which what that this with for in on to
    he she they you your his her their from by it be been has have not or an at
    about when where how why would should could will than then there these those
    some any all more most very also because while after before into out about"""
    .split()
)

# MELHORIA: bastavam dois marcadores ingleses para o dicionario desistir do
# texto INTEIRO -- e as questoes de Ingles sao escritas em portugues com o
# tema em ingles no meio. "Qual raciocinio sobre future (will/going to)
# sustenta melhor a escolha?" tem "will" e "to", entao a frase perdia todos
# os acentos: proxima, interpretacoes, possiveis, raciocinio. Foram 250
# textos do banco, achados em 28/09/2026 ao fechar as sobras do item 5.1 do
# relatorio de QA de 23/09.
#
# Agora o portugues tem voto. A lista abaixo e a mesma ja vetada em
# services/ia/enigma.py::_PALAVRAS_SO_PORTUGUESAS: nenhuma delas existe em
# ingles. So e ingles quando os marcadores ingleses SUPERAM esses -- assim
# uma frase inglesa que cite uma palavra portuguesa ("The Portuguese word
# 'para' means 'for'") continua sendo tratada como ingles.
_PALAVRAS_SO_PORTUGUESAS = frozenset(
    """da das dos na nas nos para que uma pelo pela ao aos seu sua isso esta essa esse cada sao
    frase palavra verbo oracao qual quais porque sobre entao tambem""".split()
)

# Dois marcadores DISTINTOS. Frase em portugues nao chega a um: nenhum destes
# e palavra portuguesa. Duas em vez de tres para alcancar frase curta como
# "She ate lunch at school" (she, at).
_MINIMO_DE_MARCADORES = 2


def texto_parece_ingles(texto: Any) -> bool:
    if not isinstance(texto, str) or not texto:
        return False
    # Sem acento dos dois lados: "entao" e "então" contam igual, e marcador
    # ingles nenhum tem acento.
    palavras = {p for p in re.findall(r"[a-z']+", chave_busca(texto))}
    ingleses = len(palavras & _MARCADORES_INGLES)
    if ingleses < _MINIMO_DE_MARCADORES:
        return False
    return len(palavras & _PALAVRAS_SO_PORTUGUESAS) < ingleses


# MELHORIA: estas entradas, SEM acento, tambem sao verbo -- e a IA escreve o
# verbo certo. "O uso da antítese evidencia o contraste" chegava ao aluno como
# "antítese evidência o contraste": visto numa captura do TG em 17/09/2026. No
# banco offline acentuado, "Cada tradição formula esse princípio" virava
# "tradição fórmula".
#
# Tirar as palavras do dicionario (como "analise" e "critica", no bloco de
# 13/09/2026) nao serve aqui: nos bancos escritos sem acento elas sao
# substantivo, e muitas vezes sem artigo antes -- "qual evidencia sustenta"
# (494 vezes), "hipotese, evidencia e explicacao" (275), "Numero atomico"
# (150), "Diferenciar experiencia individual" (125). Medido em 17/09/2026:
# das 4.501 vezes em que elas aparecem sem acento nos bancos, 4.493 estao em
# texto ASCII, todas substantivo; as outras 8 sao o "tradição formula" acima.
#
# O que separa os dois casos e o resto do texto. Quem escreveu "antítese" e
# "princípio" sabe acentuar, e o "evidencia" que deixou sem acento e o verbo.
# Entao estas so ganham acento em texto sem letra acentuada nenhuma -- o texto
# em ASCII para o qual o dicionario existe -- e nunca com pronome pendurado
# ("evidencia-se", "formula-la"), que so o verbo leva.
_PALAVRAS_QUE_TAMBEM_SAO_VERBO = frozenset(
    {
        # 3a pessoa: "o texto evidencia", "o autor formula", "a obra referencia"
        "evidencia",
        "formula",
        "referencia",
        "potencia",
        "distancia",
        "experiencia",
        "sequencia",
        # 1a pessoa: "eu calculo", "eu numero", "eu pratico"
        "calculo",
        "numero",
        "pratico",
        # Entraram com o item 5.1 do QA de 23/09/2026: "a fabrica maquina uma
        # saida" (maquinar), "o juiz indicie o suspeito" (indiciar), "a lei
        # cientifica o interessado" (cientificar). Nos bancos em ASCII as
        # tres sao substantivo ou adjetivo.
        "maquina",
        "indice",
        "cientifica",
    }
)
_LETRA_ACENTUADA = re.compile(r"[áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]")
_SEM_PRONOME_DEPOIS = r"(?!-(?:se|lo|la|los|las|lhe|lhes|me|te|nos|vos|o|a|os|as)\b)"


def aplicar_acentos_pt(valor: Any) -> Any:
    if not isinstance(valor, str):
        return valor
    texto = valor
    # A troca de mojibake e conserto de codificacao, nao de idioma: vale
    # para os dois. So o dicionario de portugues fica de fora do ingles.
    for bruto, correto in _MOJIBAKE.items():
        texto = texto.replace(bruto, correto)
    if texto_parece_ingles(texto):
        return texto
    # Olhado ANTES das trocas: o acento que conta e o de quem escreveu.
    escrito_sem_acento = _LETRA_ACENTUADA.search(texto) is None
    for bruto, correto in sorted(_FRASES_PT.items(), key=lambda item: len(item[0]), reverse=True):
        # MELHORIA: a frase era procurada SEM limite de palavra, entao "qual e"
        # casava com o comeco de "Qual estrutura" e o aluno lia "Qual
        # éstrutura do neurônio...?" -- visto numa questao de Biologia do
        # Oraculo em 11/09/2026. O mesmo valia para "objetivo e" (objetivo
        # éducacional) e "mudara" (mudarám).
        #
        # No COMECO o limite vale sempre: toda chave de _FRASES_PT comeca com
        # letra. No FIM ele so entra quando a frase termina em letra: "apos "
        # termina em espaco, e o que vem depois dele ja e outra palavra.
        texto = re.sub(
            r"\b" + re.escape(bruto) + (r"\b" if bruto[-1:].isalnum() else ""),
            lambda m, c=correto: _manter_capitalizacao(c, m.group(0)),
            texto,
            flags=re.IGNORECASE,
        )
    for bruto, correto in sorted(_PALAVRAS_PT.items(), key=lambda item: len(item[0]), reverse=True):
        padrao = rf"\b{re.escape(bruto)}\b"
        if bruto in _PALAVRAS_QUE_TAMBEM_SAO_VERBO:
            if not escrito_sem_acento:
                continue
            padrao += _SEM_PRONOME_DEPOIS
        texto = re.sub(
            padrao,
            lambda m, c=correto: _manter_capitalizacao(c, m.group(0)),
            texto,
            flags=re.IGNORECASE,
        )
    texto = re.sub(r"\b(\d+)o\b", r"\1º", texto)
    return texto
