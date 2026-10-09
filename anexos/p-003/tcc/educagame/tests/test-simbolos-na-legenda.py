"""A legenda de variáveis mostra o símbolo, não o comando LaTeX.

MELHORIA: no Laboratório, a fórmula saía certa — α = arctan(a/b) — e logo
abaixo dela a legenda dizia:

    \\alpha: ângulo agudo procurado; a: cateto oposto; b: cateto adjacente.

A fórmula renderiza porque passa pelo LaTeX. A legenda é texto solto nas
três telas que a desenham (`laboratorio.html`, `treino.html` e o
`st.caption` de `mode_common_st.py`), e nenhuma convertia nada.

Medido: das **50.900** questões dos bancos offline, nenhuma legenda tem
barra invertida — o problema era só das questões geradas por IA. Por isso a
correção está na normalização da resposta da IA, e não nas telas: um lugar
só conserta as três.

A legenda não pode ir para o renderizador de LaTeX. Ela é meia símbolo,
meia prosa em português, e a frase inteira sairia em itálico matemático —
o mesmo estrago que a guarda de quatro portas de `core/formula_formatting`
existe para impedir. Por isso a troca é caractere a caractere.
"""

from __future__ import annotations

import pytest

from core.simbolos import SIMBOLOS_LATEX, converter_simbolos_latex
from services.ia.normalizacao import normalizar_payload_questao


def legenda_de(valor):
    return normalizar_payload_questao({"legenda_variaveis": valor})["legenda_variaveis"]


# ====================== O CASO QUE APARECEU NA TELA ======================


def test_o_caso_medido_no_laboratorio():
    """A legenda exata do print, com a fórmula α = arctan(a/b) acima dela."""
    bruto = "\\alpha: ângulo agudo procurado; a: cateto oposto; b: cateto adjacente."

    assert legenda_de(bruto) == "α: ângulo agudo procurado; a: cateto oposto; b: cateto adjacente."


def test_nenhuma_barra_invertida_sobrevive_nas_letras_gregas():
    for nome in ("alpha", "beta", "gamma", "theta", "lambda", "mu", "omega", "Delta", "Sigma"):
        saida = converter_simbolos_latex(f"\\{nome}: medida")
        assert "\\" not in saida, f"{nome} escapou"
        assert saida.endswith(": medida")


# ====================== A PROSA AO REDOR FICA INTACTA ======================


def test_a_descricao_em_portugues_nao_e_tocada():
    """É o ponto de não renderizar como LaTeX: o texto tem de sair texto."""
    bruto = "\\theta: ângulo de inclinação da rampa em relação ao solo"

    assert legenda_de(bruto) == "θ: ângulo de inclinação da rampa em relação ao solo"


@pytest.mark.parametrize(
    "palavra",
    ["delta", "beta", "pi", "in", "to", "sim", "ne", "le"],
)
def test_a_palavra_solta_nao_vira_simbolo(palavra):
    """`core/utils.py` também troca a palavra sem barra, e ali cabe — o texto
    já é sabidamente uma fórmula. Em prosa seria armadilha: "delta" é palavra
    portuguesa (o delta do rio), e "in", "to" e "sim" aparecem em texto comum.

    A frase TEM de trazer uma barra invertida junto. Sem ela, o atalho de
    saída de `converter_simbolos_latex` devolve o texto intacto antes de
    chegar ao regex — e o teste passava com a regra arrancada, provando nada.
    """
    frase = f"\\theta: medida no {palavra} do exercício"
    esperado = f"θ: medida no {palavra} do exercício"

    assert converter_simbolos_latex(frase) == esperado


def test_legenda_sem_latex_atravessa_sem_mudanca():
    limpa = "a: cateto oposto; b: cateto adjacente; c: hipotenusa."

    assert legenda_de(limpa) == limpa


# ====================== O QUE NÃO TEM SÍMBOLO ======================


def test_comando_desconhecido_fica_visivel_em_vez_de_mutilado():
    """`\\frac{a}{b}` não tem caractere único. Tirar só a barra deixaria
    "frac{a}{b}", que é pior que o original: um comando cru é um defeito que
    se enxerga, um texto mutilado em silêncio não.
    """
    assert converter_simbolos_latex("\\frac{a}{b}: razão") == "\\frac{a}{b}: razão"


def test_o_comando_e_lido_inteiro_e_nao_por_prefixo():
    """`\\thetazinho` não pode virar "θzinho": a captura pega o nome inteiro,
    então o que não está na tabela fica como estava."""
    assert converter_simbolos_latex("\\thetazinho") == "\\thetazinho"
    assert converter_simbolos_latex("\\alphabeta") == "\\alphabeta"


# ====================== EMBRULHOS DE MODO MATEMÁTICO ======================


def test_os_cifroes_saem():
    assert converter_simbolos_latex("$\\alpha$: ângulo") == "α: ângulo"


def test_o_text_embrulhado_perde_o_embrulho():
    assert converter_simbolos_latex("\\text{massa}: em kg") == "massa: em kg"
    assert converter_simbolos_latex("\\mathrm{v}_0: inicial") == "v_0: inicial"


def test_o_grau_sai_do_circ():
    assert converter_simbolos_latex("\\alpha: ângulo em \\circ") == "α: ângulo em °"


# ====================== AS OUTRAS FORMAS QUE A IA DEVOLVE ======================


def test_a_legenda_em_dicionario_tambem_e_convertida():
    """A IA às vezes devolve {símbolo: descrição} em vez de uma frase."""
    bruto = {"\\beta": "ângulo de refração", "n": "índice do meio"}

    assert legenda_de(bruto) == "β: ângulo de refração; n: índice do meio"


def test_a_descricao_do_dicionario_tambem_e_convertida():
    """O par do teste acima. Com LaTeX só na chave, converter a descrição
    podia ser arrancado com tudo verde — o símbolo aparece dos dois lados
    ("θ: ângulo medido a partir de \\alpha").
    """
    bruto = {"n": "índice medido em relação a \\theta", "d": "distância em \\circ"}

    assert legenda_de(bruto) == "n: índice medido em relação a θ; d: distância em °"


def test_legenda_ausente_ou_vazia_nao_quebra():
    assert legenda_de(None) == ""
    assert legenda_de("") == ""
    assert legenda_de({}) == ""


# ====================== OS BANCOS OFFLINE NÃO MUDAM ======================


def test_os_bancos_offline_nao_tem_latex_na_legenda():
    """A medição que decidiu onde consertar: 0 de 50.900. Se um dia uma
    questão offline nascer com `\\alpha` na legenda, este teste avisa — e a
    correção passa a ser no banco, que é escrito à mão, não na IA.
    """
    import services.banks.em as em
    import services.banks.fundamental as ef
    import services.banks.laboratorio as lab
    import services.banks.rpg as rp

    culpadas = []
    for materia in em.MATERIAS:
        culpadas += [q for q in em.listar_questoes_em(materia)
                     if "\\" in str(q.get("legenda_variaveis") or "")]
    for materia in ef.MATERIAS:
        culpadas += [q for q in ef.listar_questoes_ef(materia)
                     if "\\" in str(q.get("legenda_variaveis") or "")]
    for materia in rp.MATERIAS:
        culpadas += [q for q in rp.listar_questoes_rpg(materia)
                     if "\\" in str(q.get("legenda_variaveis") or "")]
    for materia in lab.MATERIAS_LAB_OFFLINE:
        culpadas += [q for q in lab.listar_questoes_laboratorio(materia, "EM")
                     if "\\" in str(q.get("legenda_variaveis") or "")]
    for materia in lab.MATERIAS_LAB_EF_OFFLINE:
        culpadas += [q for q in lab.listar_questoes_laboratorio(materia, "EF")
                     if "\\" in str(q.get("legenda_variaveis") or "")]

    assert not culpadas, f"{len(culpadas)} legendas offline com LaTeX cru"


# ====================== A TABELA ======================


def test_a_tabela_cobre_o_alfabeto_grego_inteiro():
    """A tabela antiga de `core/utils.py` tinha sete entradas e `alpha` não
    estava entre elas — foi por isso que o defeito passou. Quem escreve a
    legenda é a IA, e não dá para adivinhar de qual letra ela vai precisar.
    """
    faltando = [
        letra for letra in
        ("alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
         "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho",
         "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega")
        if letra not in SIMBOLOS_LATEX
    ]

    assert not faltando, f"faltam no dicionário: {faltando}"


def test_nenhum_simbolo_da_tabela_e_o_proprio_comando():
    """Um valor copiado errado (\"alpha\": \"alpha\") não converteria nada e
    passaria despercebido."""
    iguais = [k for k, v in SIMBOLOS_LATEX.items() if v == k or "\\" in v]

    assert not iguais, iguais


# ====================== SOBRESCRITO (visto em 11/09/2026) ======================
#
# No Laboratório, a legenda veio assim da IA:
#
#     θ = ângulo de elevação (35^{°})
#
# e foi para a tela exatamente assim. converter_simbolos_latex não alcançava:
# sem barra invertida nem cifrão, o atalho de saída dela devolve o texto
# intacto. A troca de sobrescrito mora numa função própria, e só no caminho da
# legenda -- ver o último teste desta seção.

from core.simbolos import converter_sobrescritos  # noqa: E402


def test_o_caso_do_farol():
    bruto = "h = altura do farol; d = distância horizontal até a base (30,0 m); θ = ângulo de elevação (35^{°})"

    saida = legenda_de(bruto)

    assert saida.endswith("θ = ângulo de elevação (35°)"), saida
    assert "^" not in saida


@pytest.mark.parametrize("bruto", ["θ = ângulo (35^\\circ)", "θ = ângulo (35^{\\circ})", "θ = ângulo (35^{ ° })"])
def test_o_grau_em_qualquer_das_formas_do_latex(bruto):
    """`35^\\circ` é o jeito padrão de escrever grau em LaTeX. Depois que
    \\circ vira °, sobra o circunflexo solto -- e ele também tem de sair."""
    assert legenda_de(bruto) == "θ = ângulo (35°)"


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("a = aceleração (m/s^2)", "a = aceleração (m/s²)"),
        ("k = constante (N·m^{2}/C^{2})", "k = constante (N·m²/C²)"),
        ("f = frequência (s^{-1})", "f = frequência (s⁻¹)"),
        ("V = volume (cm^{3})", "V = volume (cm³)"),
    ],
)
def test_potencia_inteira_vira_sobrescrito(bruto, esperado):
    assert converter_sobrescritos(bruto) == esperado


def test_sobrescrito_sem_caractere_unico_fica_visivel():
    """`r^{n-1}` não tem caractere único. Tirar só as chaves deixaria "rn-1",
    que é pior que o original -- a mesma regra do \\frac acima."""
    assert converter_sobrescritos("a_n = termo (a_1 · r^{n-1})") == "a_n = termo (a_1 · r^{n-1})"


def test_legenda_sem_circunflexo_atravessa_intacta():
    limpa = "P_0 = preço original; d = desconto (decimal); t = imposto (decimal)"

    assert converter_sobrescritos(limpa) == limpa
    assert legenda_de(limpa) == limpa


def test_o_sobrescrito_nao_muda_o_que_a_validacao_le_da_legenda():
    """A regra `legenda-com-variavel-sem-formula` lê as declarações da
    legenda. Converter o sobrescrito não pode fazer ela ler uma declaração a
    mais nem a menos -- a troca é de tela, não de regra."""
    from services.ia.validacao import _DECLARACAO_NA_LEGENDA

    bruto = "θ = ângulo (35^{°}); a = aceleração (m/s^2); k = constante (N·m^{2})"

    assert _DECLARACAO_NA_LEGENDA.findall(converter_sobrescritos(bruto)) == _DECLARACAO_NA_LEGENDA.findall(bruto)


def test_converter_simbolos_latex_continua_sem_mexer_em_sobrescrito():
    """O par estrutural do teste acima. converter_simbolos_latex também lê as
    FÓRMULAS na validação; se alguém mover a troca de sobrescrito para dentro
    dela, "b^2" passa a "b²" nas fórmulas e as regras mudam sem ninguém ver."""
    assert converter_simbolos_latex("\\Delta = b^2 - 4ac") == "Δ = b^2 - 4ac"
