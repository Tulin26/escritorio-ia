"""Fatos que a IA erra -- ancorados no prompt, por tema.

Duas listas do mesmo relatorio moram aqui, porque a correcao e a mesma.

Achado 4.2: fatos que a IA erra de forma INCONSISTENTE de uma questao pra
outra. Achado 4.3: fatos que ela erra e ponto -- UTC-4 para o Acre (e UTC-5),
NAFTA citado como bloco vigente (acabou em 2020, virou USMCA), taxa de
crescimento natural normalizada duas vezes, composto ionico descrito como
molecula, prisma triangular com "tres lados triangulares" (sao cinco faces, e
as laterais sao retangulos), decaimento beta-menos diminuindo o numero
atomico (aumenta), povo Xikrin na Bahia (sao Kayapo, do Para), meditacao
budista buscando "presenca divina" (o budismo e nao-teista), Finados catolico
com oferenda de alimentos (isso e o Dia de Muertos), lampada halogena com
eficiencia "intermediaria" (fica perto da incandescente), ponto de ebulicao
tratado como se nao fosse propriedade fisica.

O relatorio previa que 4.3 ficaria "fora do escopo de correcao automatica --
exigiria fixar respostas canonicas no banco, decisao de produto". Fixar a
QUESTAO no banco e mesmo decisao de produto; fixar o FATO no prompt nao e, e
resolve o mesmo problema sem congelar o enunciado.

Parte da lista nao e erro de conceito, e nome proprio inventado: uma usina
atribuida a empresa errada, um "Acordo de Livre Comercio da Uniao Europeia"
que nao existe, praticas religiosas ("Cantos de Oracao", "Pregacao dos
Coracoes") que nunca existiram. Para esses, a ancora do tema traz uma regra
de veracidade, e os prompts do Oraculo e do ENEM ganharam a regra geral --
no ENEM ela precisa ser geral porque ali nao ha tema sorteado em que ancorar.

Como o achado 4.2 foi tratado (o motivo do modulo existir):

Relatorio de QA de 23/09/2026, achado 4.2: o aluno recebia mensagens opostas
sobre o mesmo conteudo no mesmo dia -- Geografia Q1 atribuia os Andes a
colisao de duas placas continentais, enquanto Q18 e Q26 diziam (corretamente)
que se formam por subduccao oceanica-continental; uma questao tratava
"cidadania" como sinonimo de "direito ao voto", outra tratava exatamente essa
frase como alternativa ERRADA; Filosofia tinha origens diferentes para o
mesmo conceito em Platao.

Correcao sugerida no relatorio (prioridade #8): "para os conceitos canonicos
... vale fixar a resposta no banco autoral em vez de deixar a IA decidir".
Reescrever essas questoes como banco autoral e re-introduzir o proprio risco
de errar o fato (agora fixo, sem chance de corrigir por regeracao). Em vez
disso, este modulo ancora a IA no fato correto sempre que o tema sorteado
bate com um destes -- a IA continua escrevendo a pergunta e as alternativas,
mas nao pode mais inventar um fato diferente do estabelecido.

"Funcoes da linguagem" ficou de fora de proposito: a resposta correta
depende do trecho especifico que CADA questao cita (referencial, conativa,
emotiva...), entao nao ha UM fato unico pra fixar -- a contradicao do
relatorio (mesmo codigo BNCC, funcoes diferentes) e sobre classificacao
BNCC, nao sobre um fato de conteudo.
"""
from __future__ import annotations

import re
import unicodedata


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(ch for ch in sem_acento if not unicodedata.combining(ch))


# (padrao para casar no tema normalizado, fato canonico a ancorar)
_FATOS: tuple[tuple[re.Pattern, str], ...] = (
    (
        re.compile(r"\bandes\b"),
        "Fato correto e obrigatorio: a Cordilheira dos Andes se formou pela subduccao da "
        "placa oceanica de Nazca sob a placa continental Sul-Americana -- e um limite "
        "convergente OCEANICO-CONTINENTAL, nunca a colisao de duas placas continentais.",
    ),
    (
        re.compile(r"\bcidadania\b"),
        "Fato correto e obrigatorio: cidadania nao se resume ao direito de votar. Cidadania "
        "engloba direitos civis (ex: liberdade, propriedade), politicos (ex: votar e ser "
        "votado) e sociais (ex: saude, educacao). Tratar 'direito ao voto' como definicao "
        "completa de cidadania e um erro conceitual, nao a resposta certa.",
    ),
    (
        re.compile(r"\bplatao\b"),
        "Fato correto e obrigatorio sobre Platao: o conhecimento verdadeiro (episteme) vem "
        "do mundo das Ideias/Formas, acessado pela razao -- os sentidos e o mundo fisico "
        "fornecem apenas opiniao (doxa), nunca conhecimento verdadeiro.",
    ),
    # --- achado 4.3: erros factuais, um por tema da lista do relatorio ---
    (
        re.compile(r"\bfusos? horario"),
        "Fato correto e obrigatorio: o Brasil tem quatro fusos. UTC-5: Acre e o sudoeste do "
        "Amazonas. UTC-4: a maior parte do Amazonas, Roraima, Rondonia, Mato Grosso e Mato "
        "Grosso do Sul. UTC-3 (hora de Brasilia): a maior parte do pais. UTC-2: Fernando de "
        "Noronha e as demais ilhas oceanicas. O Acre nunca esta em UTC-4.",
    ),
    (
        re.compile(r"\bblocos? economico|\bmercosul\b|\bnafta\b|\busmca\b|comercio internacional"),
        "Fato correto e obrigatorio: o NAFTA deixou de existir em 1o de julho de 2020, "
        "substituido pelo USMCA (tambem chamado T-MEC) -- nao o cite como bloco vigente. A "
        "Uniao Europeia nao e um 'acordo de livre comercio': e um bloco de integracao com "
        "mercado comum, uniao aduaneira e instituicoes proprias. Use apenas blocos que "
        "existem (Mercosul, Uniao Europeia, USMCA, ASEAN, Alianca do Pacifico); nao invente "
        "nome de acordo nem de organizacao.",
    ),
    (
        re.compile(r"\bdemografia\b|crescimento (?:natural|vegetativo|populacional)|taxa de natalidade"),
        "Fato correto e obrigatorio: a taxa de crescimento natural (ou vegetativo) e a "
        "SUBTRACAO de duas taxas que ja estao por mil habitantes -- TCN = taxa de natalidade "
        "menos taxa de mortalidade. Nao divida de novo pela populacao nem multiplique de novo "
        "por 1000, porque isso normalizaria duas vezes. Migracao nao entra no crescimento "
        "natural: ela entra no crescimento total.",
    ),
    (
        re.compile(r"ligacoes? quimica|ligacao ionica|\bionico\b|\bionica\b"),
        "Fato correto e obrigatorio: composto ionico NAO forma molecula. Os ions se organizam "
        "num reticulo cristalino, e e esse reticulo que a atracao eletrostatica mantem unido. "
        "'Molecula' so vale para ligacao covalente. Dizer que a atracao eletrostatica mantem "
        "'a molecula' de um sal unida e erro conceitual.",
    ),
    (
        re.compile(r"geometria espacial|\bpoliedro|\bprisma\b|solidos geometricos|\bvolume de solidos"),
        "Fatos corretos e obrigatorios: o prisma triangular tem CINCO faces -- duas bases "
        "triangulares e tres faces laterais, que sao retangulos no prisma reto, nunca "
        "triangulos. O cubo nao e o unico solido com seis faces: todo paralelepipedo tem seis. "
        "Confira o numero de faces, vertices e arestas antes de afirmar qualquer um deles.",
    ),
    (
        re.compile(r"\bradioatividade\b|decaimento|\bradiacoes\b|\batomistica\b"),
        "Fato correto e obrigatorio: no decaimento beta-menos um neutron se transforma em "
        "proton, entao o numero atomico AUMENTA em uma unidade e o numero de massa nao muda. "
        "No decaimento alfa o numero atomico diminui em 2 e a massa em 4. O enunciado e a "
        "explicacao precisam dizer a MESMA coisa sobre isso.",
    ),
    (
        re.compile(r"\bindustria\b|industrializacao|\bsiderurgi|processos produtivos"),
        "Regra obrigatoria de veracidade: nao invente nome de empresa, usina ou unidade "
        "industrial, e nao atribua uma planta real a empresa errada. Prefira citar o setor "
        "(siderurgia, automobilistica, petroquimica) a nomear uma empresa. Se nomear: a "
        "Usiminas fica em Ipatinga (MG), e a siderurgica de Joao Monlevade (MG) e da "
        "ArcelorMittal.",
    ),
    (
        re.compile(r"religios|\bbudismo\b|\bbudista\b|tradicoes religiosas|diversidade religiosa"),
        "Fatos corretos e obrigatorios sobre tradicoes religiosas: o budismo e uma tradicao "
        "NAO-TEISTA -- a meditacao budista busca atencao plena e a superacao do sofrimento, e "
        "nunca 'aproximar-se da presenca divina' nem 'reconectar com o sagrado'. O Dia de "
        "Finados catolico (2 de novembro) e visita ao cemiterio, flores, velas e missa pelos "
        "mortos; oferenda de alimentos em altar e do Dia de Muertos mexicano, nao do "
        "catolicismo romano. Cite apenas praticas que existem, com o nome que elas tem de "
        "verdade -- nao invente nome de pratica religiosa.",
    ),
    (
        re.compile(r"\bindigen|povos originarios|\bbrasil indigena\b"),
        "Fato correto e obrigatorio: ao citar um povo indigena, acerte o povo, o estado e a "
        "terra. Os Xikrin sao um subgrupo Kayapo (Mebengokre) e vivem no PARA, nao na Bahia; "
        "no sul da Bahia vivem os Pataxo e os Tupinamba. Na duvida, escreva sobre povos "
        "indigenas em geral em vez de nomear um.",
    ),
    (
        re.compile(r"\blampada|eficiencia (?:de|energetica)|fontes? de energia|equipamentos eletricos"),
        "Fato correto e obrigatorio: a lampada halogena e uma incandescente aperfeicoada e tem "
        "eficiencia PROXIMA DA INCANDESCENTE, bem abaixo da fluorescente compacta e do LED. Do "
        "menos para o mais eficiente: incandescente, halogena, fluorescente compacta, LED. Nao "
        "descreva a halogena como intermediaria junto da fluorescente.",
    ),
    (
        re.compile(r"propriedades (?:dos|de) materiais|propriedades fisicas|estrutura e propriedades"),
        "Fato correto e obrigatorio: ponto de fusao, ponto de ebulicao, densidade, "
        "solubilidade, dureza e condutividade sao PROPRIEDADES FISICAS. Propriedade quimica e "
        "a que so aparece quando a substancia se transforma em outra (inflamabilidade, "
        "oxidacao, reatividade). Nao trate ponto de ebulicao como se nao fosse propriedade "
        "fisica.",
    ),
)


def fato_canonico_para_tema(tema: str) -> str:
    """O fato a ancorar no prompt, ou "" quando o tema nao e um destes."""
    tema_norm = _normalizar(tema)
    for padrao, fato in _FATOS:
        if padrao.search(tema_norm):
            return fato
    return ""
