from core.utils import preparar_formula_latex
from core.formula_formatting import separar_texto_formula_passo
from web.routes.laboratorio_fla import _preparar_desafio_para_template


def test_formula_de_desconto_usa_fracao_em_latex():
    assert preparar_formula_latex("P = V - (V * d/100)") == r"P = V - \frac{V \cdot d}{100}"


def test_ponto_medio_unicode_nao_e_apagado_em_silencio():
    # MELHORIA: regressao para um bug visto em producao. "·" (ponto medio,
    # U+00B7) e diferente de "×"/"⋅" e nao caia em nenhum intervalo aceito
    # pelo filtro de caracteres do LaTeX; era apagado em silencio, colando
    # os dois numeros vizinhos ("12·0,577" virava "120,577" na tela).
    resultado = preparar_formula_latex("h = 12·0,577")
    assert "120,577" not in resultado
    assert r"12 \cdot 0,577" in resultado


def test_tg_nao_e_quebrada_em_t_cdot_g():
    # MELHORIA: regressao para um bug visto em producao. A regex que insere
    # "\cdot" entre letras adjacentes (multiplicacao implicita, tipo "ab")
    # quebrava "tg(30)" (abreviacao pt-BR de tangente) em "t \cdot g(30)",
    # renderizando como "t·g(30)" na tela.
    resultado = preparar_formula_latex("tg(30)")
    assert r"t \cdot g" not in resultado
    assert r"\tan(30)" in resultado


def test_simbolos_quimicos_de_2_letras_nao_sao_quebrados():
    # MELHORIA: a mesma regex de "\cdot" entre letras quebrava simbolos
    # quimicos de 2 letras (Na, Cl, Mg, Fe, Cu, Ca...), muito comuns em
    # equacoes antes de formar um composto, ex: "Na + Cl -> N \cdot a + C \cdot l".
    assert preparar_formula_latex("Na + Cl") == "Na + Cl"
    assert preparar_formula_latex("Mg + O2") == "Mg + O2"
    assert "Ca" in preparar_formula_latex("Ca(OH)2")
    assert "OH" in preparar_formula_latex("Ca(OH)2")


def test_palavras_portuguesas_de_2_letras_nao_sao_quebradas():
    # MELHORIA: regressao para um bug visto em producao. Um texto de
    # justificativa da IA ("ajustado para duas casas decimais, ou exatos e
    # inteiro") virou ilegivel ("decimaiso · uexatos · einteiro") porque
    # cada palavra comum de 2 letras do portugues (ou, de, na, em, um...)
    # caia na mesma regra pensada pra multiplicacao implicita tipo "ab".
    frase = "ajustado para duas casas decimais, ou exatos e inteiro"
    assert preparar_formula_latex(frase) == frase
    assert preparar_formula_latex("de da do na no em um eu ou as os") == "de da do na no em um eu ou as os"
    # multiplicacao algebrica real continua funcionando
    assert preparar_formula_latex("xy") == r"x \cdot y"
    assert preparar_formula_latex("ab") == r"a \cdot b"


def test_laboratorio_nao_exibe_subformulas_que_sao_variaveis():
    desafio = {
        "enigma": "Desconto imperdivel",
        "pergunta": "Um livro que custava R$ 50,00 sofreu um desconto de 15%.",
        "formula": "P = V - (V * d/100)",
        "subformulas": ["d = desconto", "V = valor original", "P = preco final"],
        "passos_resolucao": [
            {
                "titulo": "2o Passo",
                "conteudo": "Calcular o valor do desconto: desconto = V * d/100 = R$50,00 * 15/100 = R$7,50",
            },
        ],
    }

    preparado = _preparar_desafio_para_template(desafio)

    assert preparado["subformulas_latex"] == []
    assert preparado["formula_latex"] == r"P = V - \frac{V \cdot d}{100}"
    assert preparado["passos_template"][0]["conteudo_texto"] == "Calcular o valor do desconto"
    assert r"\mathrm{desconto}" in preparado["passos_template"][0]["conteudo_latex"]
    assert r"\mathrm{R\$}\,50,00" in preparado["passos_template"][0]["conteudo_latex"]


def test_formula_fisica_preserva_unidade():
    assert preparar_formula_latex("v = 120 m/10 s") == r"v = \frac{120\,\mathrm{m}}{10\,\mathrm{s}}"


def test_passo_separa_texto_de_formula_com_parenteses():
    texto, formula = separar_texto_formula_passo("Identificar valores (V = R$50,00) e desconto.")

    assert texto == "Identificar valores  e desconto"
    assert formula == "V = R$50,00"


def test_passo_nao_manda_comentario_para_mathjax():
    texto, formula = separar_texto_formula_passo(
        r"C = \frac{0,342 mol}{0,5 L} = 0,684 mol/L, arredondado para 0,68 mol/L."
    )

    assert texto == "arredondado para 0,68 mol/L."
    assert formula == r"C = \frac{0,342 mol}{0,5 L} = 0,684 mol/L"


def test_laboratorio_exibe_subformula_auxiliar_declarada_sem_minerar_passos():
    desafio = {
        "enigma": "Area com altura escondida",
        "pergunta": "Um triangulo tem base 6 m e lados 10 m. Qual e a area?",
        "formula": "A = (b * h) / 2",
        "subformulas": ["b = base", "h = altura", "c^2 = a^2 + b^2"],
        "passos_resolucao": [
            {
                "titulo": "1o Passo",
                "conteudo": "Encontrar a altura usando o Teorema de Pitagoras: c^2 = a^2 + b^2, onde c = 10 m e a = 6 m",
            },
            {
                "titulo": "2o Passo",
                "conteudo": "Substituir na formula da area: A = (6 * 8) / 2 = 24",
            },
        ],
    }

    preparado = _preparar_desafio_para_template(desafio)

    assert preparado["formula_latex"] == r"A = (b \cdot h) / 2"
    assert preparado["subformulas_latex"] == [r"c^2 = a^2 + b^2"]
    assert all(r"\mathrm{base}" not in item for item in preparado["subformulas_latex"])


def test_laboratorio_nao_promove_substituicoes_dos_passos_para_subformulas():
    desafio = {
        "enigma": "Interceptos da parabola",
        "pergunta": "A equacao da parabola e y = -x^2 + 8x. Quais sao os interceptos?",
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [],
        "legenda_variaveis": "a = coeficiente de x^2, b = coeficiente de x, c = termo constante",
        "passos_resolucao": [
            {"titulo": "1o Passo", "conteudo": "a = -1, b = 8 e c = 0."},
            {"titulo": "2o Passo", "conteudo": r"x = (-8\sqrt(8 - 4\cdot(-1)\cdot0))/(2\cdot(-1))"},
            {"titulo": "Resultado Final", "conteudo": "x' = 0 e x'' = 8", "final": True},
        ],
    }

    preparado = _preparar_desafio_para_template(desafio)

    assert preparado["subformulas_latex"] == []


def test_laboratorio_monta_fracao_de_bhaskara_sem_repetir_as_partes():
    # MELHORIA: a divisao "(...)/(...)" vira um \frac de verdade, mas antes
    # saiam junto duas linhas "numerador = ..." e "denominador = ...",
    # montadas com as mesmas variaveis de dentro do \frac -- copia literal do
    # que o aluno acabara de ler. Na tela do 3o passo de Bhaskara a fracao
    # aparecia e logo abaixo se repetia inteira.
    desafio = {
        "enigma": "Interceptos da parabola",
        "pergunta": "A equacao da parabola e y = -x^2 + 8x. Quais sao os interceptos?",
        "formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "subformulas": [],
        "passos_resolucao": [
            {"titulo": "1o Passo", "conteudo": "a = -1, b = 8 e c = 0."},
            {"titulo": "2o Passo", "conteudo": r"x = (-8\sqrt(8 - 4\cdot(-1)\cdot0))/(2\cdot(-1))"},
        ],
    }

    preparado = _preparar_desafio_para_template(desafio)
    primeiro_passo = preparado["passos_template"][0]["conteudo_latex"]
    segundo_passo = preparado["passos_template"][1]["conteudo_latex"]

    # varias atribuicoes numa linha so continuam virando linhas alinhadas
    assert r"\begin{aligned}" in primeiro_passo
    assert r"\mathrm{a} &= -1" in primeiro_passo
    assert r"\mathrm{b} &= 8" in primeiro_passo

    assert r"\frac{" in segundo_passo
    assert r"\sqrt{8 - 4\cdot(-1)\cdot0}" in segundo_passo
    assert r"\mathrm{numerador}" not in segundo_passo, segundo_passo
    assert r"\mathrm{denominador}" not in segundo_passo, segundo_passo
    # a fracao aparece uma vez so
    assert segundo_passo.count(r"\frac{") == 1, segundo_passo


def test_laboratorio_nao_cola_frase_em_portugues_dentro_de_fracao():
    # MELHORIA: regressao para um bug visto em producao no Laboratorio de
    # progressao aritmetica. O passo "Calcular a razao" vinha com duas
    # contas encadeadas numa unica string, separadas por virgula em vez de
    # ponto final ("razao = (27-7)/4 = 5, substituir na formula: a12 = ..."),
    # e o splitter nao reconhecia "substituir" como marcador de transicao.
    # O texto inteiro (incluindo a parte em portugues) era tratado como uma
    # unica formula: a primeira "/" virava fracao, e tudo depois dela —
    # inclusive "substituir na formula" — ia parar dentro do denominador.
    # O MathJax renderiza espacos soltos em modo matematico como se nao
    # existissem, entao a tela mostrava "Substituirnaformula" grudado.
    desafio = {
        "enigma": "Sequencia numerica",
        "pergunta": "Em uma progressão aritmética, o primeiro termo vale 7 e o quinto termo vale 27. Qual é o décimo segundo termo da sequência?",
        "formula": r"a_n = a_1 + (n-1) \cdot r",
        "subformulas": [],
        "passos_resolucao": [
            {"titulo": "1o Passo", "conteudo": "a1 = 7, a5 = 27, n = 12."},
            {
                "titulo": "2o Passo",
                "conteudo": "r = (a5-a1)/(5-1) = (27-7)/4 = 5, substituir na fórmula a12 = 7+(12-1)*5",
            },
            {"titulo": "Resultado Final", "conteudo": "a12 = 62", "final": True},
        ],
    }

    preparado = _preparar_desafio_para_template(desafio)
    segundo_passo = preparado["passos_template"][1]

    assert "substituirnaformula" not in segundo_passo["conteudo_texto"].lower().replace(" ", "")
    assert "substituirnaformula" not in segundo_passo["conteudo_latex"].lower().replace(" ", "")
    # a frase em portugues nao pode vazar pra dentro de um \frac{}{}: um
    # numerador/denominador de fracao de verdade nunca contem "substituir"
    if r"\frac{" in segundo_passo["conteudo_latex"]:
        assert "substituir" not in segundo_passo["conteudo_latex"].lower()


def test_expressao_sem_igual_a_zero_vira_formula():
    # MELHORIA: regressao de uma quebra que eu mesmo causei. Ao tirar os
    # enunciados circulares, varios passaram a descrever a grandeza pela
    # EXPRESSAO ("a largura segue a expressao 2x^2 - 2x - 24") em vez da
    # equacao. O detector exigia "= <numero>" no fim, entao nada casava e a
    # linha inteira saia como texto puro -- com o "^" cru na tela do aluno.
    from web.routes.flask_helpers_fla import formatar_pergunta_exatas

    resultado = formatar_pergunta_exatas(
        "A largura de uma peca segue a expressao 2x^2 - 2x - 24. Para quais valores de x ela se anula?"
    )

    assert resultado["latex"], "expressao quadratica precisa virar formula"
    assert "x^2" in resultado["latex"]
    assert "^" not in resultado["texto"], "expoente cru sobrou no texto"
    assert "^" not in resultado["sufixo"]


def test_equacao_com_igual_a_zero_continua_funcionando():
    from web.routes.flask_helpers_fla import formatar_pergunta_exatas

    resultado = formatar_pergunta_exatas(
        "Resolva por Bhaskara a equacao x^2 - 6x + 8 = 0. Quais sao as raizes?"
    )

    assert "= 0" in resultado["latex"]
    assert "x^2" in resultado["latex"]


def test_enunciado_do_laboratorio_chega_acentuado():
    # O banco offline escreve em ASCII. Este caminho so tinha algumas trocas
    # manuais, entao "peca", "expressao" e "quadratica" chegavam cruas ao
    # aluno, ao lado de palavras ja acentuadas na mesma frase.
    from web.routes.flask_helpers_fla import formatar_pergunta_exatas

    resultado = formatar_pergunta_exatas(
        "A largura de uma peca segue a expressao 2x^2 - 2x - 24. Para quais valores de x ela se anula?"
    )
    tudo = resultado["texto"] + " " + resultado["sufixo"]

    assert "peça" in tudo
    assert "expressão" in tudo
    assert "peca" not in tudo
    assert "expressao" not in tudo


def test_nenhum_enunciado_do_laboratorio_mostra_expoente_cru():
    import re

    from services.banks.laboratorio import BANCO_LAB_OFFLINE, MATERIAS_LAB_OFFLINE
    from web.routes.flask_helpers_fla import formatar_pergunta_exatas

    crus = []
    for materia in MATERIAS_LAB_OFFLINE:
        for questao in BANCO_LAB_OFFLINE[materia] or []:
            resultado = formatar_pergunta_exatas(questao.get("pergunta", ""))
            # "^" fora do LaTeX significa expoente que o aluno le cru
            for campo in ("texto", "sufixo"):
                if re.search(r"\w\^\w", resultado[campo]):
                    crus.append((questao.get("pergunta", "")[:70], campo))

    assert not crus, f"{len(crus)} enunciados com expoente cru: {crus[:3]}"


def test_ordem_das_etapas_da_formula_esta_explicita():
    # MELHORIA: preparar_formula_latex eram 258 linhas seguidas de re.sub. A
    # ORDEM entre elas importa e ja causou bug: proteger a unidade DEPOIS de
    # inserir multiplicacao implicita quebraria "12 m", e converter "tg" para
    # "tan" DEPOIS da regra de duas letras renderizava "t·g(30)". Com as
    # etapas nomeadas, a ordem virou o corpo da funcao -- este teste cobra
    # que ela nao seja embaralhada sem querer.
    import inspect

    from core.utils import preparar_formula_latex

    fonte = inspect.getsource(preparar_formula_latex)
    ordem = [
        "_normalizar_entrada_formula",
        "_restaurar_latex_corrompido",
        "_remover_caracteres_nao_latex",
        "_desfazer_text_latex",
        "_proteger_unidades_e_simbolos",
        "_inserir_operadores",
        "_prefixar_comandos_latex",
        "_normalizar_frac",
        "_formatar_unidades_restantes",
        "_restaurar_protegidos",
        "_remover_rotulo_antes_da_formula",
    ]

    # procura a CHAMADA, nao o nome solto: o comentario do pipeline cita
    # _restaurar_protegidos antes da linha em que ele e chamado.
    posicoes = [fonte.find(f"= {nome}(") for nome in ordem]
    faltando = [n for n, p in zip(ordem, posicoes) if p < 0]
    assert not faltando, f"etapa sumiu do pipeline: {faltando}"
    assert posicoes == sorted(posicoes), "a ordem das etapas mudou"


def test_protecao_de_unidade_acontece_antes_da_multiplicacao_implicita():
    # A regra concreta que a ordem garante: sem proteger antes, "12 m" viraria
    # "1 \cdot 2 m" ou perderia a unidade, e "Na" viraria "N \cdot a".
    from core.utils import preparar_formula_latex

    assert r"12\,\mathrm{m}" in preparar_formula_latex("d = 12 m")
    assert preparar_formula_latex("Na + Cl") == "Na + Cl"


def test_etapas_sao_funcoes_puras_e_isoladas():
    # Cada etapa recebe e devolve string, sem estado escondido -- o que
    # permite testar uma sozinha quando um bug aparecer.
    from core.utils import _normalizar_entrada_formula, _normalizar_frac

    assert _normalizar_entrada_formula("x²") == "x^2"
    assert _normalizar_frac(r"frac{1}{2}") == r"\frac{1}{2}"
