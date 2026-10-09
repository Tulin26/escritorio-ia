from __future__ import annotations

import re

from core.formatters import _preparar_formula_passo
from core.unidades import UNIDADE_APOS_NUMERO, eh_unidade
from core.utils import preparar_formula_latex


def formatar_formula_principal_latex(formula: str) -> str:
    return preparar_formula_latex(str(formula or ""))


def formatar_formula_passo_latex(formula: str) -> str:
    return _preparar_formula_passo(str(formula or ""))


# MELHORIA: a linha do "any(token ...)" dizia "tem '^' ou '=' em algum lugar?
# entao e formula" -- sem olhar quanta PROSA vinha junto. Visto no RPG:
#
#     Compare f(x) = (x - 4)^2 + 5 com f(x) = a(x - h)^2 + k
#
# A frase inteira virava formula, ia para o MathJax e voltava com as palavras
# em portugues tipografadas como variaveis, sem espaco nenhum:
#
#     Comparef(x)=(x-4)2+5comf(x)=a(x-h)2+k
#
# A ultima linha desta funcao ja tinha a guarda certa (no maximo 14 palavras);
# aquela nao tinha nenhuma. Palavra de uma ou duas letras nao conta: e nome de
# variavel (x, a, h, k). Nome de funcao matematica tambem nao, porque "sen",
# "log" e "raiz" aparecem DENTRO da formula.
_PALAVRA_DE_PROSA = re.compile(r"[A-Za-zÀ-ɏ]{3,}")
_PALAVRAS_QUE_VIVEM_EM_FORMULA = frozenset(
    {
        "sen", "sin", "cos", "tan", "cotg", "sec", "cossec", "log", "exp",
        "sqrt", "raiz", "mod", "frac", "cdot", "delta", "max", "min", "mmc",
        "mdc", "abs", "det", "lim",
    }
)


def _sem_unidades(texto: str) -> str:
    """Tira as unidades de medida antes de contar prosa.

    MELHORIA: a contagem nao sabia o que e unidade, e passo de Quimica e de
    Fisica e feito delas:

        n = \\frac{18 g}{44 g/mol} = 0,41 mol

    "mol" e "cal" tem tres letras e nao vivem na lista de palavras de formula,
    entao viravam prosa e a formula era rebaixada a texto -- 348 passos do
    banco (5%) quebraram assim numa primeira tentativa de correcao.

    A segunda tentativa foi pior de outro jeito: tratar QUALQUER palavra depois
    de um numero como unidade. Ai "5 com", em "... + 5 com f(x) = ...", sumia
    da contagem, e a frase do RPG voltava inteira para o MathJax.

    O que funciona e cruzar as duas coisas: vir depois de um numero E estar na
    lista de unidades conhecidas (core/unidades.py), que ja existia para a
    validacao do Laboratorio.
    """
    def trocar(match: re.Match) -> str:
        return " " if eh_unidade(match.group(1)) else match.group(0)

    return UNIDADE_APOS_NUMERO.sub(trocar, str(texto or ""))


def _prosa_demais(texto: str) -> bool:
    """Palavras de portugues suficientes para isto ser FRASE, nao formula."""
    palavras = [p.lower() for p in _PALAVRA_DE_PROSA.findall(_sem_unidades(texto))]
    return sum(1 for p in palavras if p not in _PALAVRAS_QUE_VIVEM_EM_FORMULA) >= 2


# Uma "palavra" aqui e uma sequencia de 2+ letras. Variavel e uma letra so
# ("x", "a"), entao qualquer palavra de 2+ letras que nao seja nome de funcao
# nem unidade e sinal de portugues -- inclusive as curtinhas ("de", "em",
# "ou"), que a contagem de _PALAVRA_DE_PROSA (3+ letras) deixa passar.
_PALAVRA_DE_DUAS_LETRAS = re.compile(r"[A-Za-zÀ-ɏ]{2,}")

# Operadores que ligam duas coisas. O "-" entra porque "(-8 ± 12)/(-4)" e
# conta, mesmo que ali ele seja sinal e nao operacao.
#
# Os comandos LaTeX entram na MESMA lista porque a IA escreve das duas formas:
# "12 × 3" e "12 \times 3". Sem eles, `_so_notacao_matematica` tirava o
# comando (senao "times" viraria palavra de portugues) e a busca por operador
# nao achava mais nada -- "12 \times 3" ficava sem operador e voltava a ser
# prosa. Os dois testes que pegaram isso nasceram de um mutante sobrevivente.
_OPERADOR = re.compile(
    r"[+\-*/^±·×÷√]|\\(?:pm|mp|cdot|times|div|approx|frac|sqrt)\b"
)


def _so_notacao_matematica(texto: str) -> bool:
    """Isto e notacao pura, sem uma palavra de portugues no meio?

    Evidencia POSITIVA, de proposito. As outras quatro portas perguntam "nao
    tem prosa demais?", e "nao tem prosa" nao e o mesmo que "e formula" -- foi
    por essa fresta que frase virou formula duas vezes seguidas nesta funcao
    (ver tests/test_passo_com_prosa.py). Aqui a pergunta e outra: sobra alguma
    palavra depois de tirar numeros, operadores, comandos LaTeX, nomes de
    funcao e unidades? Se sobra, nao e notacao.
    """
    limpo = _sem_unidades(str(texto or ""))
    limpo = re.sub(r"\\[A-Za-z]+", " ", limpo)  # \frac, \sqrt, \cdot...
    for palavra in _PALAVRA_DE_DUAS_LETRAS.findall(limpo):
        if palavra.lower() not in _PALAVRAS_QUE_VIVEM_EM_FORMULA:
            return False
    return True


def parece_formula_laboratorio(texto: str) -> bool:
    texto = str(texto or "").strip()
    if not texto:
        return False

    texto_norm = texto.lower()
    # MELHORIA: esta checagem ("comeca com nome =") tambem nao olhava a prosa,
    # e foi por ela que passou:
    #
    #     c = 50 m e o seno de 30 graus vale 0,5.
    #         -> c = 50 meosenode30grausvale0,5
    #
    # A guarda de prosa foi acrescentada so na terceira checagem, mais abaixo;
    # esta continuou aceitando qualquer frase que comecasse com "letra =".
    #
    # A guarda aqui olha SO O QUE VEM DEPOIS DO "=", e nao a frase inteira,
    # porque nome de grandeza com varias palavras e legitimo do lado esquerdo:
    #
    #     velocidade media = 80     -> depois do "=" nao ha prosa: e formula
    #     c = 50 m e o seno de ...  -> depois do "=" e frase: nao e formula
    if re.match(r"^[A-Za-z\u00C0-\u024F_ ]+\s*=", texto) and (
        any(token in texto for token in ("\\", "^", "/", "*", "+", "-", "(", ")"))
        or len(re.findall(r"\d", texto)) >= 2
    ) and not _prosa_demais(texto.split("=", 1)[1]):
        return True

    termos_descritivos = (
        "identificar",
        "calcular",
        "subtrair",
        "valor original",
        "valororiginal",
        "desconto",
        "preco final",
        "precofinal",
        "livro",
        "produto",
    )
    if any(termo in texto_norm for termo in termos_descritivos) and len(texto) > 28:
        return False

    if any(token in texto for token in ("\\frac", "\\sqrt", "\\Delta", "\\cdot", "^", "=")) and not _prosa_demais(texto):
        return True
    # A quarta porta. O limite de 14 palavras era a unica guarda dela, e uma
    # frase de 12 palavras comecando com "c =" passava direto. Sao CINCO
    # entradas nesta funcao, e a guarda de prosa precisa estar em todas --
    # fechar uma de cada vez foi o que fez o mesmo defeito voltar duas vezes.
    if (
        bool(re.search(r"\b[A-Za-z]\s*=", texto))
        and len(texto.split()) <= 14
        and not _prosa_demais(texto)
    ):
        return True

    # MELHORIA: a quinta porta. As quatro acima exigem um "=" (ou um comando
    # LaTeX, ou um "^"). Conta sem igual nenhum caia fora e o passo inteiro
    # descia para prosa -- visto na tela do Laboratorio, num passo de Bhaskara:
    #
    #     (-8 ± sqrt(144)) / (2*(-2))
    #
    # que apareceu como texto cru, com "sqrt" e "*" literais em vez de √ e ·.
    # E um passo perfeitamente legitimo: mostrar a substituicao ANTES de
    # resolver e exatamente o que o prompt pede.
    #
    # Esta porta nao pergunta "tem prosa?", pergunta "e so notacao?" -- ver
    # _so_notacao_matematica. O digito e o operador de fora garantem que ha
    # conta, e nao um numero solto ("144") nem uma lista ("1, 2, 3").
    #
    # UM digito, e nao dois: o dois era chute meu, e a mutacao mostrou que
    # nenhum teste o sustentava. Medido nos 5.784 passos, baixar para um
    # aceita exatamente 4 casos a mais -- "3 g/L", "4 g/L", "5 g/mL",
    # "6 g/L" --, que sao valor com unidade, e nenhuma frase de controle
    # passa a entrar. Exigir dois recusava "x + 1", que e formula.
    return (
        _so_notacao_matematica(texto)
        and bool(re.search(r"\d", texto))
        and bool(_OPERADOR.search(texto))
    )


def _separar_formula_de_comentario(conteudo: str) -> tuple[str, str]:
    conteudo = str(conteudo or "").strip()
    if not conteudo:
        return "", ""

    marcadores = (
        "arredondad",
        "portanto",
        "logo",
        "assim",
        "por isso",
        "porém",
        "porem",
        "mas ",
        "então",
        "entao",
        "resposta correta",
        "deve ser",
        "deveria ser",
        # MELHORIA: passos de Laboratorio (PA/PG, trigonometria etc.) as vezes
        # encadeiam duas contas numa unica string separadas por virgula, tipo
        # "razao = (27-7)/4 = 5, substituir na formula: a12 = 7+(12-1)*5" —
        # sem "substituir"/"substituindo" na lista, o texto inteiro (incluindo
        # a parte em portugues) era tratado como uma unica formula e acabava
        # colado sem espaco dentro de um \frac{}{} pelo MathJax.
        "substituir",
        "substituindo",
        "aplicando",
    )
    padrao_marcador = "|".join(re.escape(marcador) for marcador in marcadores)
    match_delimitador = re.search(
        rf"\s*[,.;]\s*(?=({padrao_marcador}))",
        conteudo,
        flags=re.IGNORECASE,
    )
    if match_delimitador:
        formula = conteudo[: match_delimitador.start()].strip()
        comentario = conteudo[match_delimitador.end():].strip()
        if parece_formula_laboratorio(formula):
            return comentario, formula

    match_marcador_colado = re.search(
        rf"({padrao_marcador})",
        conteudo,
        flags=re.IGNORECASE,
    )
    if match_marcador_colado:
        formula = conteudo[: match_marcador_colado.start()].strip(" ,.;")
        comentario = conteudo[match_marcador_colado.start():].strip()
        if parece_formula_laboratorio(formula):
            return comentario, formula

    return "", conteudo


def separar_texto_formula_passo(conteudo: str) -> tuple[str, str]:
    conteudo = str(conteudo or "").strip()
    if not conteudo:
        return "", ""

    if ":" in conteudo:
        texto, candidato = conteudo.split(":", 1)
        candidato = candidato.strip()
        comentario, formula = _separar_formula_de_comentario(candidato)
        if comentario and formula:
            texto_completo = " ".join(parte for parte in (texto.strip().rstrip("."), comentario) if parte)
            return texto_completo, formula
        if parece_formula_laboratorio(candidato):
            return texto.strip().rstrip("."), candidato

    match_formula_parenteses = re.search(r"\(([^()]*=[^()]*)\)", conteudo)
    if match_formula_parenteses and parece_formula_laboratorio(match_formula_parenteses.group(1)):
        texto = (conteudo[: match_formula_parenteses.start()] + conteudo[match_formula_parenteses.end():]).strip()
        return texto.rstrip(" ."), match_formula_parenteses.group(1).strip()

    comentario, formula = _separar_formula_de_comentario(conteudo)
    if comentario and formula:
        return comentario, formula

    if parece_formula_laboratorio(conteudo):
        return "", conteudo
    return conteudo, ""


def _parece_subformula_auxiliar(formula: str) -> bool:
    formula = str(formula or "").strip()
    if not formula or "=" not in formula:
        return False

    esquerda, direita = formula.split("=", 1)
    esquerda = esquerda.strip()
    direita = direita.strip()
    if not esquerda or not direita:
        return False

    if re.fullmatch(r"[A-Za-z\u00C0-\u024F_][A-Za-z\u00C0-\u024F_ ]+", esquerda) and "\\" not in esquerda:
        return False

    if re.fullmatch(r"[A-Za-z\u00C0-\u024F_][A-Za-z\u00C0-\u024F_ ]*", esquerda) and re.fullmatch(
        r"[A-Za-z\u00C0-\u024F_][A-Za-z\u00C0-\u024F_ ]*", direita
    ):
        return False

    marcadores_formula = ("\\", "^", "²", "/", "*", "+", "-", "(", ")", r"\cdot", r"\sqrt", r"\Delta")
    if any(marcador in formula for marcador in marcadores_formula):
        return True

    return len(re.findall(r"[A-Za-z]", formula)) >= 2 and len(re.findall(r"\d", formula)) >= 1


def extrair_subformula_auxiliar(formula: str) -> str:
    formula = str(formula or "").strip()
    if not formula:
        return ""

    candidatos = [formula]
    partes = re.split(r"\s*(?:,|;|\bonde\b|\bcom\b)\s*", formula, maxsplit=1, flags=re.IGNORECASE)
    if partes and partes[0].strip() != formula:
        candidatos.insert(0, partes[0].strip())

    for candidato in candidatos:
        candidato = candidato.strip(" .")
        if _parece_subformula_auxiliar(candidato):
            return candidato
    return ""


def formatar_subformulas_auxiliares_latex(_subformulas: list | None) -> list[str]:
    subformulas = []
    vistos = set()
    for item in _subformulas or []:
        formula = extrair_subformula_auxiliar(str(item or ""))
        if not formula:
            continue
        latex = preparar_formula_latex(formula)
        chave = re.sub(r"\s+", "", latex)
        if chave and chave not in vistos:
            vistos.add(chave)
            subformulas.append(latex)
    return subformulas
