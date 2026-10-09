from __future__ import annotations

import core.utils as core_utils
import st.ui.mode_common_st as mode_common


def test_formatar_pergunta_trata_superscrito_como_formula():
    resultado = mode_common.formatar_pergunta(
        "Resolva a equacao do 2º grau 2x² + 5x + 3 = 0, utilizando a formula de Bhaskara."
    )

    assert "x^" in resultado or "x^{" in resultado


def test_formatar_pergunta_move_interrogacao_para_antes_do_bloco_latex():
    resultado = mode_common.formatar_pergunta(
        "Qual é o valor de x que satisfaz a equação 2x² + 5x + 3 = 0?"
    )

    assert "equação ?" not in resultado
    assert resultado.count("?") == 1
    assert resultado.index("?") < resultado.index("$$")


def test_formatar_pergunta_corrige_2o_grau_antes_de_equacao_latex():
    resultado = mode_common.formatar_pergunta(
        "Encontre as raizes da equacao do 2o grau 3x^2 + 2x - 5 = 0"
    )

    assert "2º grau" in resultado
    assert "2o grau" not in resultado
    assert "$$" in resultado


def test_extrair_texto_e_formula_quando_passo_mistura_descricao_e_latex():
    prefixo, formula = mode_common._extrair_texto_e_formula(
        r"Continuar a substituicao: \frac{-5 \pm \sqrt{1}}{2(2)} = \frac{-5 \pm 1}{4}"
    )

    assert prefixo == "Continuar a substituicao"
    assert r"\frac" in formula


def test_preparar_formula_latex_melhora_multiplicacao_implicita():
    resultado = core_utils.preparar_formula_latex(r"2(5)^2 - 4(2)(3)")

    assert r"2 \cdot (5)^2" in resultado
    assert r"4 \cdot (2) \cdot (3)" in resultado


def test_preparar_formula_latex_formata_fracao_simples_e_asterisco():
    resultado = core_utils.preparar_formula_latex("A = (1/2)5*12 = 30")

    assert r"\frac{1}{2} \cdot 5 \cdot 12" in resultado


def test_preparar_formula_latex_recupera_frac_e_times_sem_escape():
    resultado = core_utils.preparar_formula_latex(r"P = 100 imes rac{15}{100}")

    assert r"\times" in resultado
    assert r"\frac{15}{100}" in resultado


def test_preparar_formula_latex_preserva_pm_de_bhaskara():
    resultado = core_utils.preparar_formula_latex(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}")

    assert r"\pm" in resultado
    assert r"\p \cdot m" not in resultado
    assert r"\text{a}" not in resultado


def test_preparar_formula_latex_formata_fracao_com_variaveis():
    resultado = core_utils.preparar_formula_latex("A = (1/2)bh")

    assert r"\frac{1}{2} \cdot b \cdot h" in resultado


def test_conteudo_passo_parece_formula_com_unidade_em_exatas():
    assert mode_common._conteudo_passo_parece_formula("F = 4*3 = 12 N") is True
    assert mode_common._conteudo_passo_parece_formula("Q = (1/2)5*12 = 30 cal") is True


def test_usos_dia_a_dia_laboratorio_explica_desconto():
    titulo, usos = mode_common._usos_dia_a_dia_laboratorio(
        {"pergunta": "Um produto sofreu desconto de 15%. Qual é o novo preço?"},
        "Matematica",
    )
    texto = " ".join(f"{subtitulo}: {descricao}" for subtitulo, descricao in usos)

    assert "porcentagem" in titulo.lower()
    assert "Compras e promoções" in texto
    assert "compensa" in texto


def test_usos_dia_a_dia_laboratorio_explica_quimica():
    titulo, usos = mode_common._usos_dia_a_dia_laboratorio(
        {"pergunta": "Uma solução tem 20 g em 2 L. Qual é a concentração?"},
        "Quimica",
    )
    texto = " ".join(f"{subtitulo}: {descricao}" for subtitulo, descricao in usos)

    assert "concentração" in titulo.lower()
    assert "Produtos de limpeza" in texto
    assert "segurança" in texto


def test_usos_dia_a_dia_laboratorio_lista_aplicacoes_de_area():
    titulo, usos = mode_common._usos_dia_a_dia_laboratorio(
        {"pergunta": "Calcule a altura de um triângulo com base de 10 cm e área de 40 cm²."},
        "Matematica",
    )

    textos = " ".join(titulo for titulo, _ in usos) + " " + " ".join(desc for _, desc in usos)
    assert "área" in titulo.lower()
    assert "Construção civil" in textos
    assert "Terrenos" in textos
    assert len(usos) >= 5


def test_usos_dia_a_dia_laboratorio_nao_mostra_formula_ou_resultado():
    _, usos = mode_common._usos_dia_a_dia_laboratorio(
        {"pergunta": "Em uma PA, com a1 = 4 e razão 5, qual é o 10o termo?"},
        "Matematica",
    )

    texto = " ".join(f"{titulo} {desc}" for titulo, desc in usos)
    assert "Passo" not in texto
    assert "Resultado Final" not in texto
    assert "=" not in texto


def test_formula_tem_moeda_detecta_real_sem_quebrar():
    assert mode_common._formula_tem_moeda("P = R$ 68,00") is True


def test_escapar_moeda_markdown_escapa_cifrao_uma_vez():
    assert mode_common._escapar_moeda_markdown("R$ 5,20 = R$ 104,00") == r"R\$ 5,20 = R\$ 104,00"


def test_subformula_auxiliar_nao_mostra_definicao_de_variavel():
    assert mode_common._subformula_auxiliar_visivel("h = altura do objeto") is False
    assert mode_common._subformula_auxiliar_visivel("S = comprimento da sombra do poste") is False


def test_subformula_auxiliar_mostra_formula_simbolica_util():
    assert mode_common._subformula_auxiliar_visivel(r"\Delta = b^2 - 4ac") is True


def test_preparar_formula_latex_formata_unidade_fisica():
    # MELHORIA: o commit e47d3fa ("Arrumando problemas") trocou \text{} por
    # \mathrm{} de proposito nas unidades -- \text{} depende do pacote
    # amsmath/amstext e renderiza mal no KaTeX usado pelo st.latex() do
    # Streamlit; \mathrm{} e um primitivo do LaTeX puro, suportado sem
    # ambiguidade. Este teste ficou desatualizado depois dessa correcao.
    resultado = core_utils.preparar_formula_latex("v = 25 m/s")

    assert r"25\,\mathrm{m/s}" in resultado


def test_preparar_formula_latex_formata_unidade_quimica():
    resultado = core_utils.preparar_formula_latex("C = 5 g/L")

    assert r"5\,\mathrm{g/L}" in resultado


def test_preparar_formula_latex_preserva_centimetro_quadrado():
    resultado = core_utils.preparar_formula_latex("A = 22,5 cm^2")

    assert r"22,5\,\mathrm{cm^2}" in resultado
    assert r"c \cdot m" not in resultado


def test_formatar_unidades_texto_exibe_centimetro_quadrado():
    assert core_utils.formatar_unidades_texto("22,5 cm^2") == "22,5 cm²"


def test_conteudo_passo_parece_formula_com_decimal_e_funcao_latex():
    assert mode_common._conteudo_passo_parece_formula(r"\tan(\theta) = 0.75") is True


def test_conteudo_passo_nao_trata_frase_com_ponto_como_formula():
    assert mode_common._conteudo_passo_parece_formula("A tangente vale 0.75.") is False


def test_limpar_formula_no_texto_evitar_ambiguidade_entre_numero_e_raiz():
    resultado = core_utils.limpar_formula_no_texto(
        r"x = \frac{-5\sqrt{1}}{4}"
    )

    assert "5·√(1)" in resultado
