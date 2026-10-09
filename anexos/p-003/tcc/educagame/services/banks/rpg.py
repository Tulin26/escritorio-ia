from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from core.config import MATERIAS, TEMAS_RPG, get_area_da_materia, normalizar_materia
from services.banks._base import (
    LazyMateriaBank,
    bncc_da_materia as _bncc_da_materia,
    chave_busca as _chave_busca,
    embaralhar as _embaralhar,
)


QUESTOES_RPG_POR_TEMA = 50

AMBIENTES_RPG = [
    "Biblioteca das Portas",
    "Ponte das Engrenagens",
    "Sala dos Mapas",
    "Jardim dos Simbolos",
    "Torre do Debate",
    "Forja das Evidencias",
    "Observatorio dos Reagentes",
    "Arquivo das Runas",
    "Galeria dos Ecos",
    "Camara Rubra",
]

CENARIOS_RPG = {
    "Matematica": ["um mapa de proporcoes", "um painel de padroes numericos", "uma balanca de escolhas", "um mosaico geometrico"],
    "Fisica": ["um portao movido por energia", "um corredor de ondas", "uma ponte suspensa por forcas", "um circuito antigo"],
    "Quimica": ["um altar com frascos rotulados", "um rio de solucao brilhante", "uma forja de vapores coloridos", "um filtro de cristais"],
    "Biologia": ["uma estufa subterranea", "um bestiario vivo", "um lago de microorganismos", "um jardim de adaptacoes"],
    "Portugues": ["um pergaminho fragmentado", "um mural de discursos", "uma carta enigmática", "um teatro de vozes"],
    "Historia": ["uma sala de fontes antigas", "um mapa de revoltas", "um arquivo imperial", "um corredor de memorias"],
    "Geografia": ["um atlas em movimento", "uma maquete de territorio", "um mapa climatico", "uma rota de migracoes"],
    "Ingles": ["a glowing notice board", "a coded dialogue", "an old travel poster", "a clockwork newspaper"],
    "Ciencias": ["um laboratorio escolar secreto", "uma trilha ecologica", "um planetario subterraneo", "uma bancada de evidencias"],
    "Educacao Fisica": ["uma arena cooperativa", "uma pista adaptada", "um campo de estrategias", "um dojo de respeito"],
    "Arte": ["uma galeria encantada", "um palco de sombras", "um atelie de simbolos", "um muro de grafites vivos"],
    "Filosofia": ["uma praça de dilemas", "um espelho socratico", "um tribunal de ideias", "uma biblioteca de argumentos"],
    "Sociologia": ["uma cidade em miniatura", "um mercado de relacoes sociais", "um conselho de guildas", "um mural de desigualdades"],
    "Ensino Religioso": ["um circulo de dialogo", "um jardim de simbolos", "um arquivo de tradicoes", "uma ponte de convivencias"],
}

PERFIS_RPG = {
    "Matematica": ("modelar relacoes e reconhecer padroes", "relacionar dados, representacoes e propriedades antes da resposta"),
    "Fisica": ("explicar fenomenos por grandezas e interacoes", "identificar principios fisicos e evidencias do sistema"),
    "Quimica": ("interpretar materia, propriedades e transformacoes", "relacionar particulas, interacoes, evidencias e condicoes"),
    "Biologia": ("explicar processos vitais e relacoes ecologicas", "usar evidencias biologicas para justificar a alternativa"),
    "Portugues": ("interpretar textos, generos e efeitos de sentido", "relacionar linguagem, contexto e finalidade"),
    "Historia": ("comparar fontes e processos historicos", "considerar sujeitos, contexto, causas e consequencias"),
    "Geografia": ("analisar territorio, escala e sociedade-natureza", "observar localizacao, redes, paisagem e impactos"),
    "Ingles": ("understand meaning from genre and context", "use context clues, purpose and known vocabulary"),
    "Ciencias": ("investigar fenomenos naturais com evidencias", "comparar dados, causas e consequencias"),
    "Educacao Fisica": ("compreender praticas corporais e inclusao", "considerar regras, seguranca, cooperacao e cultura corporal"),
    "Arte": ("interpretar linguagens artisticas e contexto", "observar forma, materialidade, intencao e repertorio cultural"),
    "Filosofia": ("avaliar conceitos, argumentos e dilemas", "identificar pressupostos e consequencias das ideias"),
    "Sociologia": ("analisar relacoes sociais e desigualdades", "ligar individuo, grupo, instituicoes e contexto historico"),
    "Ensino Religioso": ("compreender diversidade e convivencia", "comparar tradicoes com respeito e sem hierarquizar crencas"),
}

GANCHOS_RPG = [
    "uma inscricao muda de forma quando a equipe religa as pistas anteriores",
    "um guardiao exige que a resposta explique a causa do bloqueio",
    "o mapa treme e revela duas interpretacoes possiveis para o mesmo sinal",
    "um mecanismo antigo so abre quando a equipe separa evidencia de aparencia",
    "a sala repete uma cena do passado e pede uma decisao bem justificada",
    "um aliado deixa um registro incompleto que precisa ser confrontado com o contexto",
    "a passagem reage a uma conclusao apressada e cobra uma explicacao mais precisa",
    "um painel mostra efeitos diferentes para escolhas que parecem iguais",
]

ACOES_RPG = [
    "decifrar o registro antes que a porta se feche",
    "orientar os colegas sobre qual pista deve guiar a decisao",
    "corrigir a leitura de um simbolo que pode levar a uma armadilha",
    "escolher qual evidencia sustenta melhor o proximo passo",
    "montar uma explicacao curta para convencer o guardiao",
    "comparar duas pistas contraditorias sem perder o foco do tema",
    "transformar a teoria em uma acao concreta dentro da sala",
    "registrar o criterio que impedira a equipe de repetir o erro",
]

QUIMICA_MODELOS = {
    "solu": [
        (
            "Em {cenario}, dois frascos transparentes parecem iguais, mas apenas um tem soluto totalmente dissolvido no solvente. O que caracteriza uma solução?",
            "Mistura homogênea em que o soluto se distribui uniformemente no solvente.",
            ["Mistura heterogênea com fases visíveis.", "Substância pura formada por um único elemento.", "Reação que sempre libera gás e muda de cor."],
            "Solução é uma mistura homogênea: a olho nu, apresenta uma única fase.",
        ),
        (
            "Na bancada da guilda, sal desaparece visualmente ao ser colocado em água e agitado. Como esse sistema deve ser classificado?",
            "Como uma solução, porque forma uma mistura homogênea entre soluto e solvente.",
            ["Como substância simples, pois tem apenas um componente.", "Como mistura heterogênea, pois todo sal sempre fica visível.", "Como reação nuclear, pois houve desaparecimento de matéria."],
            "Dissolver não significa destruir matéria; significa dispersar partículas no solvente.",
        ),
        (
            "Um guardião mostra água com açúcar dissolvido e pergunta qual componente está em maior quantidade. Que nome ele recebe?",
            "Solvente.",
            ["Soluto.", "Precipitado.", "Indicador."],
            "Em geral, solvente é o componente em maior quantidade e que dissolve o soluto.",
        ),
        (
            "Em uma solução aquosa de sulfato de cobre, a cor azul está uniforme em todo o frasco. O que essa uniformidade indica?",
            "Que a mistura apresenta uma única fase visível.",
            ["Que ocorreu separação de fases.", "Que o sistema virou substância pura.", "Que não há partículas dissolvidas."],
            "A uniformidade visual é uma evidência macroscópica de mistura homogênea.",
        ),
    ],
    "concentr": [
        (
            "Dois frascos têm o mesmo volume, mas um recebeu mais soluto. Qual ideia explica a diferença entre eles?",
            "Concentração: quantidade de soluto em certa quantidade de solução ou solvente.",
            ["Densidade nuclear.", "Ponto de fusão do vidro.", "Número de fases visíveis apenas."],
            "Concentração compara a quantidade de soluto com o volume ou massa do sistema.",
        ),
        (
            "Uma poção fica mais intensa quando mais soluto é dissolvido sem mudar o volume. O que aumentou?",
            "A concentração da solução.",
            ["A quantidade de solvente puro.", "A separação de fases.", "A massa molar do recipiente."],
            "Mantendo o volume, mais soluto torna a solução mais concentrada.",
        ),
    ],
    "mol": [
        (
            "O alquimista usa 'mol' para contar partículas em vez de unidades comuns. O que essa grandeza representa?",
            "Uma quantidade de matéria associada a um número muito grande de entidades químicas.",
            ["A massa exata de qualquer objeto.", "A cor de uma solução.", "A velocidade de uma reação sem relação com partículas."],
            "Mol é unidade de quantidade de matéria, usada para átomos, moléculas ou íons.",
        ),
        (
            "Ao comparar amostras de substâncias diferentes com 1 mol cada, o que elas têm em comum?",
            "A quantidade de entidades químicas.",
            ["A mesma massa em gramas sempre.", "A mesma cor e o mesmo volume.", "O mesmo ponto de ebulição."],
            "Um mol sempre corresponde à mesma quantidade de entidades, mas a massa depende da substância.",
        ),
    ],
    "estequiometr": [
        (
            "Uma reação da forja só funciona quando os reagentes seguem a proporção indicada pela equação balanceada. Que estudo orienta essa relação?",
            "Estequiometria.",
            ["Isomeria óptica.", "Separação magnética.", "Geometria plana."],
            "Estequiometria usa proporções da equação química balanceada.",
        ),
        (
            "Por que uma equação química precisa estar balanceada antes de prever quantidades?",
            "Porque ela deve respeitar a conservação dos átomos.",
            ["Porque todo produto precisa ter massa zero.", "Porque reagentes sempre somem sem formar produtos.", "Porque balancear elimina a necessidade de proporções."],
            "O balanceamento garante o mesmo número de átomos de cada elemento nos dois lados.",
        ),
    ],
    "ph": [
        (
            "Um líquido da masmorra apresenta pH baixo e muda o indicador para cor ácida. O que isso sugere?",
            "Maior acidez, associada à presença de íons H+ em solução.",
            ["Neutralidade obrigatória.", "Ausência total de íons.", "Maior basicidade por definição."],
            "Quanto menor o pH, mais ácido é o meio aquoso.",
        ),
        (
            "Uma base altera o indicador de modo oposto ao ácido. Qual característica é esperada para seu pH?",
            "pH maior que 7 em condições usuais.",
            ["pH sempre igual a 0.", "pH sempre menor que 7.", "pH sem relação com acidez ou basicidade."],
            "Em escala usual, bases apresentam pH acima de 7.",
        ),
    ],
    "liga": [
        (
            "O selo da porta mostra átomos compartilhando elétrons. Que tipo de ligação isso representa?",
            "Ligação covalente.",
            ["Ligação iônica por transferência total.", "Decantação.", "Fusão nuclear escolar."],
            "Na ligação covalente, há compartilhamento de pares de elétrons.",
        ),
        (
            "Um cristal se forma pela atração entre íons positivos e negativos. Qual ligação predomina?",
            "Ligação iônica.",
            ["Ligação metálica apenas entre moléculas de água.", "Ligação covalente sem cargas.", "Ponte de hidrogênio como ligação principal do retículo."],
            "Ligação iônica envolve atração eletrostática entre íons de cargas opostas.",
        ),
    ],
    "period": [
        (
            "Na parede da torre, os elementos aparecem organizados por número atômico. Que ferramenta química é essa?",
            "Tabela periódica.",
            ["Cadeia alimentar.", "Escala cartográfica.", "Diagrama de classes sociais."],
            "A tabela periódica organiza elementos e permite prever propriedades.",
        ),
        (
            "Elementos de uma mesma família na tabela tendem a ter propriedades parecidas. Por quê?",
            "Porque apresentam semelhanças na configuração da camada de valência.",
            ["Porque têm exatamente a mesma massa.", "Porque ocupam sempre o mesmo período.", "Porque foram descobertos no mesmo ano."],
            "A camada de valência influencia reatividade e propriedades químicas.",
        ),
    ],
}


MATEMATICA_MODELOS = [
    (
        ("progressao geometrica", " pg", "(pg"),
        [
            (
                "Em {cenario}, os valores da passagem dobram a cada selo: 3, 6, 12, 24. Que ideia de progressao geometrica explica esse padrao?",
                "Cada termo e obtido multiplicando o anterior pela mesma razao.",
                ["Cada termo cresce somando sempre a mesma constante.", "A ordem dos termos nao interfere na sequencia.", "A media dos termos sempre determina a razao."],
                "Em uma PG, a razao multiplica um termo para formar o proximo.",
            ),
            (
                "Em {cenario}, uma PG tem primeiro termo 5 e razao 3. O que a razao informa?",
                "Que cada termo deve ser multiplicado por 3 para chegar ao seguinte.",
                ["Que cada termo deve receber mais 3 por soma.", "Que todos os termos precisam ser divididos por 5.", "Que a sequencia sempre termina no terceiro termo."],
                "A razao da PG e o fator multiplicativo entre termos consecutivos.",
            ),
            (
                "Uma trilha em {cenario} cresce como 2, 6, 18, 54. Qual verificacao confirma que ela e uma PG?",
                "O quociente entre termos consecutivos permanece constante.",
                ["A diferenca entre termos consecutivos permanece constante.", "Todos os termos precisam ser numeros pares.", "O ultimo termo precisa ser a soma dos anteriores."],
                "PG e identificada por quociente constante entre termos consecutivos.",
            ),
        ],
    ),
    (
        ("progressao aritmetica", " pa", "(pa"),
        [
            (
                "Em {cenario}, os degraus aparecem com marcas 4, 9, 14, 19. Que propriedade indica uma progressao aritmetica?",
                "A diferenca entre termos consecutivos e constante.",
                ["O quociente entre termos consecutivos e constante.", "Os termos precisam alternar sinal.", "O primeiro termo sempre deve ser zero."],
                "Na PA, a razao e a diferenca fixa entre termos consecutivos.",
            ),
            (
                "Em {cenario}, o mapa avanca sempre 7 casas por etapa. Como interpretar essa razao em uma PA?",
                "Somar 7 ao termo atual para obter o proximo termo.",
                ["Multiplicar todos os termos por 7.", "Dividir o ultimo termo pelo primeiro.", "Elevar o termo atual a potencia 7."],
                "A razao da PA e um acrescimo ou reducao constante por soma.",
            ),
        ],
    ),
    (
        ("funcao do 1o grau", "funcoes do 1o grau", "funcao linear"),
        [
            (
                "Em {cenario}, uma porta cobra 2 cristais fixos mais 3 por passo dado. Qual caracteristica de funcao do 1o grau aparece na regra?",
                "A variacao e constante: a cada passo, o total aumenta sempre 3.",
                ["A variacao dobra a cada passo.", "O grafico deve ser uma parabola.", "O valor inicial nao influencia a regra."],
                "Funcao do 1o grau tem taxa de variacao constante e grafico em reta.",
            ),
            (
                "Em {cenario}, um marcador segue f(x)=4x+1. O que o coeficiente 4 representa?",
                "A taxa de variacao: quanto f(x) muda quando x aumenta uma unidade.",
                ["O ponto maximo da parabola.", "A base de uma potencia.", "A quantidade de raizes reais da funcao."],
                "Em f(x)=ax+b, o coeficiente a indica a inclinacao ou taxa de variacao.",
            ),
        ],
    ),
    (
        ("funcao do 2o grau", "funcoes do 2o grau", "parabola", "2o grau"),
        [
            (
                "Em {cenario}, o arco da ponte forma uma parabola. Que elemento ajuda a identificar o ponto mais alto ou mais baixo da funcao?",
                "O vertice da parabola.",
                ["A razao de uma PG.", "A mediana dos dados.", "O solvente da mistura."],
                "Na funcao quadratica, o vertice indica maximo ou minimo da parabola.",
            ),
            (
                "Em {cenario}, um selo mostra uma funcao quadratica com concavidade para cima. O que isso indica sobre o vertice?",
                "Ele representa um ponto de minimo.",
                ["Ele representa sempre uma raiz negativa.", "Ele elimina o eixo de simetria.", "Ele transforma a funcao em uma reta."],
                "Com concavidade para cima, o vertice e o menor ponto da parabola.",
            ),
        ],
    ),
    (
        ("probabilidade", "probabilidade condicional"),
        [
            (
                "Em {cenario}, a equipe sorteia uma chave entre 10, mas apenas 2 abrem a porta. Que comparacao define a probabilidade?",
                "Casos favoraveis divididos pelos casos possiveis.",
                ["Casos impossiveis somados aos favoraveis.", "Maior numero observado menos o menor.", "Produto entre todos os resultados possiveis."],
                "Probabilidade compara resultados favoraveis com o total de resultados possiveis.",
            ),
            (
                "Em {cenario}, o guardiao pergunta por P(A|B). O que muda em uma probabilidade condicional?",
                "O espaco de analise fica restrito aos casos em que B ocorreu.",
                ["A probabilidade passa a ignorar os dados.", "A ordem dos eventos deixa de existir sempre.", "O resultado precisa ser maior que 1."],
                "Em P(A|B), calculamos a chance de A dentro do grupo em que B ja aconteceu.",
            ),
        ],
    ),
    (
        ("estatistica", "media", "mediana", "graficos", "tabelas"),
        [
            (
                "Em {cenario}, tres rotas receberam pontuacoes 6, 8 e 10. O que a media resume?",
                "Um valor central obtido pela soma dos dados dividida pela quantidade de dados.",
                ["O valor que obrigatoriamente aparece mais vezes.", "A diferenca fixa entre termos consecutivos.", "O quociente constante de uma sequencia."],
                "A media aritmetica resume os dados pela soma dividida pela quantidade de valores.",
            ),
            (
                "Em {cenario}, um grafico mostra crescimento rapido no ultimo trecho. Qual atitude e mais adequada na leitura estatistica?",
                "Comparar eixos, escala e valores antes de concluir a tendencia.",
                ["Olhar apenas a cor da linha.", "Ignorar a escala para acelerar a decisao.", "Trocar o grafico por uma formula qualquer."],
                "Graficos exigem leitura de escala, eixos, unidades e tendencia.",
            ),
        ],
    ),
    (
        ("porcentagem", "matematica financeira", "taxas", "indices"),
        [
            (
                "Em {cenario}, um tesouro aumenta de 100 para 125 moedas. Que leitura percentual descreve a mudanca?",
                "Houve aumento de 25% em relacao ao valor inicial.",
                ["Houve aumento de 125% porque esse e o valor final.", "Houve queda de 25% em relacao ao valor final.", "Nao ha variacao porque ambos sao valores monetarios."],
                "Variacao percentual compara a diferenca com o valor inicial.",
            ),
            (
                "Em {cenario}, uma loja oferece 20% de desconto. O que esse percentual significa?",
                "Retirar 20 partes de cada 100 do valor original.",
                ["Somar 20 ao valor final sempre.", "Multiplicar o preco por 20 sem dividir por 100.", "Dividir o valor final pelo numero de produtos."],
                "Percentual e uma razao com denominador 100.",
            ),
        ],
    ),
    (
        ("logarit", "funcao logaritmica"),
        [
            (
                "Em {cenario}, a inscricao diz log_2(32)=5. Que relacao essa escrita expressa?",
                "2 elevado a 5 resulta em 32.",
                ["32 elevado a 2 resulta em 5.", "5 dividido por 2 resulta em 32.", "2 somado a 32 resulta em 5."],
                "Logaritmo pergunta qual expoente transforma a base no logaritmando.",
            ),
            (
                "Em {cenario}, um painel pede interpretar um logaritmo. Qual cuidado e essencial?",
                "Identificar base, logaritmando e expoente correspondente.",
                ["Tratar todo logaritmo como porcentagem.", "Ignorar a base porque ela nunca altera o valor.", "Usar sempre a razao de uma PA."],
                "A base define qual potencia deve gerar o logaritmando.",
            ),
        ],
    ),
    (
        ("exponencial", "funcao exponencial"),
        [
            (
                "Em {cenario}, cada selo ativo duplica a luz do anterior. Que caracteristica indica crescimento exponencial?",
                "A quantidade e multiplicada por um fator constante a cada etapa.",
                ["A quantidade aumenta por soma fixa.", "A sequencia depende apenas da media.", "O grafico sempre e uma reta horizontal."],
                "Crescimento exponencial ocorre por multiplicacao repetida por uma base.",
            ),
        ],
    ),
    (
        ("geometria", "area", "volume", "trigonometria"),
        [
            (
                "Em {cenario}, a equipe precisa cobrir um piso retangular. Qual grandeza deve calcular?",
                "Area, porque mede a superficie ocupada.",
                ["Volume, porque mede apenas comprimento.", "Probabilidade, porque compara eventos.", "Razao da PG, porque multiplica termos."],
                "Area mede superficie; volume mede espaco tridimensional.",
            ),
            (
                "Uma rampa em {cenario} forma um triangulo retangulo. Qual relacao trigonometrica usa cateto oposto e hipotenusa?",
                "Seno do angulo.",
                ["Cosseno do angulo.", "Tangente do angulo.", "Determinante da matriz."],
                "No triangulo retangulo, seno relaciona cateto oposto e hipotenusa.",
            ),
        ],
    ),
]


FISICA_MODELOS = [
    (
        ("cinematica", "mru", "mruv", "velocidade", "movimento"),
        [
            (
                "Em {cenario}, marcas no chao indicam deslocamento e tempo. Qual relacao descreve a velocidade media?",
                "Velocidade media relaciona deslocamento total e intervalo de tempo.",
                ["Velocidade media depende apenas da massa do corpo.", "Velocidade media e sempre igual a aceleracao.", "Velocidade media ignora a unidade de tempo."],
                "Velocidade media e a razao entre deslocamento e tempo decorrido.",
            ),
            (
                "Um corredor de {cenario} mostra posicoes sucessivas em tempos iguais. O que indica movimento uniforme?",
                "Percorrer distancias iguais em intervalos de tempo iguais.",
                ["Aumentar a massa a cada intervalo.", "Mudar de direcao sem alterar posicao.", "Ter forca resultante obrigatoriamente crescente."],
                "No movimento uniforme, a velocidade permanece constante.",
            ),
        ],
    ),
    (
        ("newton", "forca", "dinamica"),
        [
            (
                "Em {cenario}, um bloco muda seu movimento quando uma empurrada maior e aplicada. Que ideia da dinamica explica isso?",
                "A forca resultante altera o estado de movimento do corpo.",
                ["A massa some quando ha movimento.", "A velocidade nao depende de interacoes.", "Toda forca sempre produz repouso absoluto."],
                "Leis de Newton relacionam forcas, massa e mudancas no movimento.",
            ),
            (
                "O mecanismo de {cenario} compara massa e aceleracao. Qual leitura combina com a segunda lei de Newton?",
                "Para uma mesma massa, maior forca produz maior aceleracao.",
                ["Maior forca sempre reduz a aceleracao.", "A massa nao influencia a resposta do corpo.", "Forca e temperatura sao sempre a mesma grandeza."],
                "Pela segunda lei, F = m.a relaciona forca, massa e aceleracao.",
            ),
        ],
    ),
    (
        ("trabalho", "energia", "potencia", "matrizes energeticas"),
        [
            (
                "Em {cenario}, uma forca desloca uma alavanca. Quando ha trabalho mecanico?",
                "Quando uma forca provoca deslocamento na direcao considerada.",
                ["Quando ha somente massa parada.", "Quando a temperatura fica constante.", "Quando nao existe deslocamento algum."],
                "Trabalho mecanico envolve forca e deslocamento.",
            ),
            (
                "Um motor em {cenario} realiza a mesma tarefa em menos tempo. Que grandeza compara essa rapidez?",
                "Potencia, pois relaciona energia ou trabalho com tempo.",
                ["Densidade, pois mede massa por volume.", "pH, pois mede acidez.", "Mediana, pois ordena dados."],
                "Potencia mede a taxa de realizacao de trabalho ou transferencia de energia.",
            ),
        ],
    ),
    (
        ("circuit", "ohm", "eletric", "corrente", "eletrostatica"),
        [
            (
                "Em {cenario}, uma lampada brilha menos quando a resistencia aumenta. Qual relacao da eletricidade explica isso?",
                "Com a mesma tensao, maior resistencia reduz a corrente eletrica.",
                ["Maior resistencia sempre aumenta a corrente.", "Corrente eletrica nao depende do circuito.", "Tensao e resistencia sao grandezas sem relacao."],
                "Na lei de Ohm, corrente, tensao e resistencia estao relacionadas.",
            ),
            (
                "O painel de {cenario} mostra cargas em movimento ordenado por um fio. Que grandeza descreve esse fluxo?",
                "Corrente eletrica.",
                ["Calor latente.", "Pressao atmosferica.", "Numero atomico."],
                "Corrente eletrica e o fluxo ordenado de cargas.",
            ),
        ],
    ),
    (
        ("onda", "som", "luz", "optica", "radiacoes", "espectro"),
        [
            (
                "Em {cenario}, ecos retornam de uma parede distante. Que propriedade ondulatoria esta sendo observada?",
                "Reflexao da onda.",
                ["Dissolucao do soluto.", "Conservacao dos atomos.", "Razao de uma PA."],
                "Eco ocorre pela reflexao de ondas sonoras.",
            ),
            (
                "Um feixe de luz muda de direcao ao atravessar um cristal em {cenario}. Que fenomeno isso representa?",
                "Refracao.",
                ["Condensacao.", "Fermentacao.", "Conjugacao verbal."],
                "Refracao ocorre quando a luz muda de meio e altera sua direcao de propagacao.",
            ),
        ],
    ),
    (
        ("calor", "temperatura", "termologia", "termodinamica", "calorimetria"),
        [
            (
                "Em {cenario}, dois corpos em contato trocam energia ate ficarem na mesma temperatura. Que processo ocorreu?",
                "Transferencia de calor do corpo mais quente para o mais frio.",
                ["Transferencia de massa atomica por numero atomico.", "Aumento de pH por neutralizacao.", "Formacao de uma progressao geometrica."],
                "Calor e energia em transito por diferenca de temperatura.",
            ),
            (
                "O termometro de {cenario} mede temperatura. O que essa grandeza indica?",
                "O estado termico associado a agitacao das particulas.",
                ["A quantidade de materia em mol.", "A razao entre termos de uma sequencia.", "A autoria de uma fonte historica."],
                "Temperatura esta ligada ao grau de agitacao microscopica.",
            ),
        ],
    ),
]


def _temas_materia(materia: str) -> list[str]:
    dados = TEMAS_RPG.get(materia, {})
    temas = list(dict.fromkeys((dados.get("EM") or []) + (dados.get("EF") or [])))
    return temas or ["conteudo geral"]


def _nivel(indice: int) -> str:
    return ("Facil", "Medio", "Dificil")[indice % 3]


def _quimica_modelo(tema: str, cenario: str, indice: int) -> tuple[str, str, list[str], int, str]:
    tema_key = _chave_busca(tema)
    for chave, modelos in QUIMICA_MODELOS.items():
        if chave in tema_key:
            pergunta, correta, distratores, explicacao = modelos[indice % len(modelos)]
            opcoes, correta_idx = _embaralhar(correta, distratores, indice)
            return (
                f"Runas químicas reagem ao tema {tema}.",
                pergunta.format(cenario=cenario),
                opcoes,
                correta_idx,
                explicacao,
            )
    return _modelo_teorico("Quimica", tema, cenario, indice)


def _matematica_modelo(tema: str, cenario: str, indice: int) -> tuple[str, str, list[str], int, str] | None:
    tema_key = f" {_chave_busca(tema)} "
    for chaves, modelos in MATEMATICA_MODELOS:
        if any(chave in tema_key for chave in chaves):
            pergunta, correta, distratores, explicacao = modelos[indice % len(modelos)]
            opcoes, correta_idx = _embaralhar(correta, distratores, indice)
            return (
                f"{cenario}: os simbolos respondem ao conceito de {tema}.",
                pergunta.format(cenario=cenario),
                opcoes,
                correta_idx,
                explicacao,
            )
    return None


def _fisica_modelo(tema: str, cenario: str, indice: int) -> tuple[str, str, list[str], int, str] | None:
    tema_key = f" {_chave_busca(tema)} "
    for chaves, modelos in FISICA_MODELOS:
        if any(chave in tema_key for chave in chaves):
            pergunta, correta, distratores, explicacao = modelos[indice % len(modelos)]
            opcoes, correta_idx = _embaralhar(correta, distratores, indice)
            return (
                f"{cenario}: instrumentos antigos registram pistas de {tema}.",
                pergunta.format(cenario=cenario),
                opcoes,
                correta_idx,
                explicacao,
            )
    return None


def _corretas_contextuais(materia: str, tema: str, cenario: str) -> list[str]:
    por_materia = {
        "Historia": [
            f"Relacionar {tema} a fontes, contexto historico, causas e consequencias.",
            f"Comparar sujeitos e interesses envolvidos em {tema} antes de interpretar a pista.",
            f"Analisar {tema} como processo historico, nao como fato isolado sem contexto.",
            f"Usar evidencias de {cenario} para explicar continuidades e rupturas ligadas a {tema}.",
        ],
        "Geografia": [
            f"Relacionar {tema} a territorio, escala, paisagem e atores sociais.",
            f"Interpretar {tema} observando localizacao, fluxos, redes e impactos no espaco.",
            f"Comparar fatores naturais e sociais que ajudam a explicar {tema}.",
            f"Usar escala e distribuicao espacial para justificar a leitura de {tema}.",
        ],
        "Biologia": [
            f"Relacionar {tema} a estrutura, funcao, ambiente e adaptacao dos seres vivos.",
            f"Explicar {tema} por evidencias biologicas observadas na cena.",
            f"Comparar processo vital, organismo e ambiente antes de concluir sobre {tema}.",
            f"Usar causa e consequencia biologica para interpretar {tema}.",
        ],
        "Portugues": [
            f"Analisar {tema} considerando genero textual, finalidade, contexto e efeito de sentido.",
            f"Observar marcas linguisticas que sustentam a interpretacao de {tema}.",
            f"Relacionar {tema} ao interlocutor, ao suporte e ao objetivo comunicativo do texto.",
            f"Comparar tese, argumento e recurso expressivo para resolver a pista sobre {tema}.",
        ],
        "Ingles": [
            f"Use context, genre and purpose to infer the meaning connected to {tema}.",
            f"Compare clues in the text before choosing the best interpretation of {tema}.",
            f"Identify the communicative function of {tema} in the scene.",
            f"Use vocabulary and context together to understand {tema}.",
        ],
        "Ciencias": [
            f"Relacionar {tema} a observacao, hipotese, evidencia e explicacao cientifica.",
            f"Comparar causas e consequencias do fenomeno ligado a {tema}.",
            f"Diferenciar fato observado e interpretacao ao explicar {tema}.",
            f"Usar evidencias de {cenario} para sustentar uma conclusao sobre {tema}.",
        ],
        "Educacao Fisica": [
            f"Relacionar {tema} a regras, seguranca, cooperacao e participacao do grupo.",
            f"Adaptar a pratica de {tema} respeitando limites corporais e inclusao.",
            f"Analisar {tema} como pratica corporal, cultural e coletiva.",
            f"Planejar a acao em {tema} considerando estrategia, cuidado e respeito.",
        ],
        "Arte": [
            f"Interpretar {tema} por linguagem, materialidade, intencao e contexto cultural.",
            f"Comparar forma, tecnica e repertorio para compreender {tema}.",
            f"Relacionar elementos visuais, sonoros ou corporais ao sentido de {tema}.",
            f"Observar composicao e contexto antes de concluir sobre {tema}.",
        ],
        "Filosofia": [
            f"Identificar conceitos, pressupostos e consequencias do argumento sobre {tema}.",
            f"Comparar posicoes filosoficas antes de justificar a escolha sobre {tema}.",
            f"Questionar a primeira impressao e explicitar o criterio usado em {tema}.",
            f"Avaliar a coerencia do raciocinio ligado a {tema}.",
        ],
        "Sociologia": [
            f"Relacionar {tema} a grupos sociais, instituicoes, normas e desigualdades.",
            f"Diferenciar experiencia individual e explicacao social ao analisar {tema}.",
            f"Observar poder, cultura e contexto historico na situacao ligada a {tema}.",
            f"Explicar {tema} conectando individuo, sociedade e instituicoes.",
        ],
        "Ensino Religioso": [
            f"Reconhecer a diversidade de crencas e praticas ao interpretar {tema}.",
            f"Analisar {tema} com respeito, contexto cultural e sem hierarquizar tradicoes.",
            f"Distinguir estudo das religioes de adesao religiosa ao tratar de {tema}.",
            f"Comparar simbolos e ritos de {tema} considerando convivencia e liberdade de crenca.",
        ],
    }
    return por_materia.get(
        materia,
        [
            f"Relacionar {tema} ao contexto da cena e justificar a resposta com evidencias.",
            f"Identificar o conceito central de {tema} antes de comparar as alternativas.",
            f"Usar {tema} para explicar o bloqueio apresentado e orientar a proxima acao.",
            f"Comparar pistas, contexto e conceito para interpretar {tema}.",
        ],
    )


# MELHORIA: havia duas _modelo_teorico neste arquivo. A primeira era uma
# versao antiga, generica, que NUNCA rodava: a segunda definicao vence em
# silencio no Python. Quem editasse a de cima veria a mudanca nao acontecer.
# A que fica e superconjunto -- despacha por materia e, sem modelo
# especifico, cai na mesma logica generica, com texto mais rico.
def _modelo_teorico(materia: str, tema: str, cenario: str, indice: int) -> tuple[str, str, list[str], int, str]:
    if materia == "Matematica":
        modelo_matematica = _matematica_modelo(tema, cenario, indice)
        if modelo_matematica:
            return modelo_matematica
    if materia == "Fisica":
        modelo_fisica = _fisica_modelo(tema, cenario, indice)
        if modelo_fisica:
            return modelo_fisica

    foco, estrategia = PERFIS_RPG.get(materia, PERFIS_RPG["Ciencias"])
    gancho = GANCHOS_RPG[indice % len(GANCHOS_RPG)]
    acao = ACOES_RPG[(indice + 2) % len(ACOES_RPG)]
    perguntas = [
        f"Em {cenario}, {gancho}. Para {acao}, que leitura de {tema} ajuda a equipe a avancar?",
        f"O desafio de {cenario} apresenta {tema} como chave da passagem. Qual decisao transforma o conceito em acao dentro da cena?",
        f"Antes de abrir a proxima passagem, a equipe encontra {gancho}. Qual raciocinio sobre {tema} sustenta melhor a escolha?",
        f"Em {cenario}, o grupo precisa {acao} usando {tema}. Qual alternativa responde ao problema da sala com melhor justificativa?",
        f"Uma memoria presa em {cenario} mostra consequencias diferentes para a mesma escolha. Como {tema} deve orientar a resposta?",
        f"O guardiao de {cenario} aceita apenas uma explicacao ligada ao que foi observado. Qual alternativa usa {tema} de modo adequado?",
    ]
    corretas = _corretas_contextuais(materia, tema, cenario)
    correta = corretas[indice % len(corretas)]
    distratores = [
        f"Trocar {tema} por outro assunto de {materia}, sem responder ao problema apresentado.",
        f"Citar uma palavra de {tema}, mas deixar de explicar como ela aparece em {cenario}.",
        f"Escolher uma conclusao sobre {tema} que contradiz as evidencias descritas na cena.",
        f"Desconsiderar o conceito de {tema} e decidir apenas pela aparencia do objeto observado.",
        f"Usar uma definicao incompleta de {tema}, sem ligar causa, efeito e contexto.",
        f"Generalizar {tema} como se toda situacao de {materia} tivesse a mesma resposta.",
    ]
    inicio = (indice * 2) % len(distratores)
    opcoes, correta_idx = _embaralhar(correta, [distratores[(inicio + i) % len(distratores)] for i in range(3)], indice)
    return (
        f"{cenario}: {gancho}.",
        perguntas[indice % len(perguntas)],
        opcoes,
        correta_idx,
        f"Neste desafio, o objetivo e {foco}. A resposta correta conecta a cena, as evidencias e o conceito de {tema}.",
    )


def _gerar_materia(materia: str) -> list[dict[str, Any]]:
    temas = _temas_materia(materia)
    cenarios = CENARIOS_RPG.get(materia, CENARIOS_RPG["Ciencias"])
    area = get_area_da_materia(materia, "1o Ano EM")
    questoes: list[dict[str, Any]] = []
    for tema_idx, tema in enumerate(temas):
        for variacao in range(QUESTOES_RPG_POR_TEMA):
            indice = tema_idx * QUESTOES_RPG_POR_TEMA + variacao
            cenario = cenarios[indice % len(cenarios)]
            if materia == "Quimica":
                enigma, pergunta, opcoes, correta_idx, explicacao = _quimica_modelo(tema, cenario, indice)
            else:
                enigma, pergunta, opcoes, correta_idx, explicacao = _modelo_teorico(materia, tema, cenario, indice)
            ambiente = AMBIENTES_RPG[indice % len(AMBIENTES_RPG)]
            questoes.append(
                {
                    "id_offline": f"RPG-{materia}-{indice + 1:04d}",
                    "materia": materia,
                    "serie_tipo": "RPG",
                    "tema_usado": tema,
                    "objeto_conhecimento": tema,
                    "dificuldade": _nivel(indice),
                    # MELHORIA: o RPG INVENTAVA a BNCC -- "RPG-QUI-01" nao e
                    # codigo de habilidade nenhum, e a competencia era "RPG
                    # educacional: <perfil>". Isso e pior que campo vazio:
                    # parece BNCC no painel do professor e nao e. Passa a usar
                    # a mesma tabela do banco EM, como o Laboratorio.
                    **_bncc_da_materia(materia),
                    "ambientacao": f"No setor {ambiente}, a equipe encontra um desafio ligado a {tema}.",
                    "enigma": enigma,
                    "pergunta": pergunta,
                    "opcoes": opcoes,
                    "correta": correta_idx,
                    "explicacao": [
                        {"tipo": "bold", "conteudo": f"RPG - {tema}"},
                        {"tipo": "texto", "conteudo": explicacao},
                        {"tipo": "resultado", "conteudo": "A alternativa correta conecta a pista da aventura ao conceito estudado."},
                    ],
                    "passos_resolucao": [],
                    "formula": "",
                    "subformulas": [],
                    "legenda_variaveis": "",
                    "rpg_local": ambiente,
                    "_origem_geracao": "offline",
                }
            )
    return questoes


BANCO_RPG_OFFLINE = LazyMateriaBank(MATERIAS, _gerar_materia, fallback="Ciencias")


def listar_questoes_rpg(materia: str) -> list[dict[str, Any]]:
    materia_norm = normalizar_materia(materia)
    return deepcopy(BANCO_RPG_OFFLINE.get(materia_norm) or BANCO_RPG_OFFLINE["Ciencias"])


def gerar_questao_rpg_offline(
    materia: str,
    tema: str = "",
    nivel: str = "",
    evitar_ids: list[str] | set[str] | tuple[str, ...] | None = None,
    chave_extra: str = "",
) -> dict[str, Any]:
    materia_norm = normalizar_materia(materia) or "Ciencias"
    questoes = BANCO_RPG_OFFLINE.get(materia_norm) or BANCO_RPG_OFFLINE["Ciencias"]
    tema_busca = _chave_busca(tema)
    candidatas = [
        questao
        for questao in questoes
        if tema_busca and tema_busca in _chave_busca(questao.get("tema_usado", ""))
    ] or questoes
    evitar = {str(item) for item in (evitar_ids or []) if str(item).strip()}
    livres = [questao for questao in candidatas if str(questao.get("id_offline", "")) not in evitar]
    if livres:
        candidatas = livres
    idx = int(hashlib.sha256(f"rpg|{materia_norm}|{tema}|{nivel}|{chave_extra}".encode("utf-8")).hexdigest(), 16) % len(candidatas)
    questao = deepcopy(candidatas[idx])
    if nivel:
        questao["dificuldade"] = str(nivel)
    return questao
