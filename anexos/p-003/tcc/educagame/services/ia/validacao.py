from __future__ import annotations

import re
import ast
import math
import operator
import unicodedata

from core.answer_equivalence import tem_opcoes_equivalentes
from core.simbolos import converter_simbolos_latex
from services.ia.explicacao_vazia import explicacao_tem_corpo
from services.ia.opcoes_no_enunciado import pergunta_embute_opcoes_com_letra
from services.ia.resposta_no_enunciado import pergunta_entrega_a_resposta
from services.ia.normalizacao import normalizar_payload_questao

from core.unidades import (
    UNIDADE_APOS_NUMERO,
    UNIDADES_FISICA,
    UNIDADES_QUIMICA,
    eh_unidade,
    normalizar_unidade,
    simplificar_unidade_latex,
)


_OPERADORES_SEGUROS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _texto_normalizado_simples(valor: str) -> str:
    return re.sub(r"\s+", " ", str(valor or "").strip().lower())


def _texto_ascii_simples(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", texto)


def _extrair_numeros_normalizados(texto: str) -> list[str]:
    numeros = re.findall(r"-?\d+(?:[.,]\d+)?", str(texto or ""))
    return [numero.replace(",", ".") for numero in numeros]


# MELHORIA: o expoente da UNIDADE era lido como numero -- "a = 4 m/s^2" dava
# 2 como ultimo numero, e "\frac{70 N}{4 m^2}" era avaliado como 70/4^2.
# _valor_do_passo_final ja tratava "48 m^2", mas so com unidade de letras e so
# ali; o leitor do ultimo numero (regras de resultado conflitante e de
# alternativa inferida) e o avaliador de conta nao tratavam nada. Medido em
# 14/09/2026: as 44 questoes de pressao do banco recusadas por conta "errada",
# e uma questao certa de F = m.a recusada duas vezes no Render ("a = 4
# \text{ m/s}^2" lido como 2, "alternativa-correta-inconsistente").
_UNIDADE_COM_EXPOENTE = re.compile(
    # Chave so em par: em "\frac{70 N}{4 m^2}" a chave depois do 2 e do \frac.
    r"(\d[\d.,]*)(\s*)([a-zà-ÿ°µωΩ][a-zà-ÿ°µωΩ/·.]*?)\s*\^\s*(?:\{\s*\d\s*\}|\d)",
    re.IGNORECASE,
)


def _sem_expoente_de_unidade(texto: str) -> str:
    """"4 m/s^2" -> "4 m/s"; "2x^2" continua "2x^2".

    So sai o expoente de UNIDADE CONHECIDA -- cada pedaco de "kg/m" tem de ser
    unidade --, e letra sozinha colada no numero e variavel ("2a^2"), nao
    ampere. A unidade que sobra o avaliador ja descarta.
    """
    def trocar(achado: re.Match) -> str:
        numero, espaco, unidade = achado.groups()
        pedacos = [pedaco for pedaco in re.split(r"[/·.]", unidade) if pedaco]
        if not pedacos or not all(eh_unidade(pedaco) for pedaco in pedacos):
            return achado.group(0)
        if not espaco and len(unidade) == 1:
            return achado.group(0)
        return f"{numero}{espaco}{unidade}"

    return _UNIDADE_COM_EXPOENTE.sub(trocar, simplificar_unidade_latex(texto))


def _ultimo_numero_normalizado(texto: str) -> str:
    numeros = _extrair_numeros_normalizados(_sem_expoente_de_unidade(texto))
    return numeros[-1] if numeros else ""


def _coletar_textos_resultado_exatas(dados: dict) -> list[str]:
    # MELHORIA: a ordem aqui importa pra quem consome esta lista de tras pra
    # frente (_resposta_marcada_diverge_do_resultado_final) em busca do
    # numero "de verdade" da resposta -- o passo marcado final=True e o
    # UNICO sinal inequivoco do payload de que aquele e o resultado final;
    # blocos de "explicacao" tipo resultado costumam ser so uma descricao
    # em palavras (às vezes sem numero nenhum, às vezes citando um numero
    # de contexto que nao e a resposta). Por isso o passo final vem por
    # ULTIMO na lista -- e o candidato mais confiavel, e deve ser o
    # primeiro a ser considerado por quem busca de tras pra frente.
    candidatos: list[str] = []
    passos_com_conteudo: list[str] = []
    passo_final_conteudo: str = ""

    for passo in dados.get("passos_resolucao", []) or []:
        if isinstance(passo, dict):
            conteudo = str(passo.get("conteudo", "")).strip()
            if conteudo:
                passos_com_conteudo.append(conteudo)
                if passo.get("final"):
                    passo_final_conteudo = conteudo

    for bloco in dados.get("explicacao", []) or []:
        if isinstance(bloco, dict) and bloco.get("tipo") in ("resultado", "final"):
            conteudo = str(bloco.get("conteudo", "")).strip()
            if conteudo:
                candidatos.append(conteudo)

    if passo_final_conteudo:
        candidatos.append(passo_final_conteudo)

    if not candidatos and passos_com_conteudo:
        candidatos.append(passos_com_conteudo[-1])

    return candidatos


def _coletar_textos_referencia_resposta(dados: dict) -> list[str]:
    candidatos: list[str] = []

    for passo in dados.get("passos_resolucao", []) or []:
        if isinstance(passo, dict):
            conteudo = str(passo.get("conteudo", "")).strip()
            if conteudo:
                candidatos.append(conteudo)

    for bloco in dados.get("explicacao", []) or []:
        if isinstance(bloco, dict):
            conteudo = str(bloco.get("conteudo", "")).strip()
            if conteudo:
                candidatos.append(conteudo)

    return candidatos


def _coletar_valores_finais_exatas(dados: dict) -> list[str]:
    valores: list[str] = []
    for texto in _coletar_textos_resultado_exatas(dados):
        ultimo = _ultimo_numero_normalizado(texto)
        if ultimo:
            valores.append(ultimo)
    return valores


def _resultado_exatas_conflitante(dados: dict) -> bool:
    # MELHORIA: comparava os textos CRUS ("10" x "10,0"/"10.0"), e a IA
    # as vezes escreve o mesmo valor com casas decimais diferentes no bloco
    # "resultado" e no passo final -- "v = 10\,\text{m/s}" contra
    # "v = 10,0\,\text{m/s}". Como numero os dois sao iguais; como string
    # nunca sao, e a questao certa caia em "resultado-exatas-conflitante"
    # (visto em producao, 30/09/2026, carrinho em MUV). Converte para float
    # antes de comparar -- "14" x "15" (valor realmente diferente) continua
    # pegando conflito.
    valores = _coletar_valores_finais_exatas(dados)
    numeros = {numero for numero in (_normalizar_numero_float(v) for v in valores) if numero is not None}
    return len(numeros) > 1


# MELHORIA: passo final com raiz nao era conferido por NINGUEM. "sqrt" esta
# na lista de funcoes transcendentes, e essa lista faz o passo inteiro ser
# PULADO -- justamente o passo onde a resposta nasce em Pitagoras, na lei dos
# cossenos e em Bhaskara.
#
# Visto em producao (03/09/2026), lei dos cossenos: os tres primeiros passos
# certos ate "BC^2 = 475", e o final dizia "BC = raiz de 475 ~ 19,4". A raiz
# de 475 e 21,79 -- 19,4 e a raiz de 375. O aluno respondeu 21,8, que esta
# certo, levou "Errou" e perdeu 15 pontos.
#
# A checagem de divergencia que ja existia nao pega este caso: ela pergunta
# se a alternativa marcada bate com o resultado final ESCRITO, e batia -- o
# passo dizia 19,4 e a alternativa era 19,4. Ninguem perguntava se a raiz
# confere com o radicando.
_RADICANDO = (
    r"(?:\\sqrt\s*\{([^{}]+)\}"
    r"|\\sqrt\s*\(([^()]+)\)"
    r"|\bsqrt\s*\(([^()]+)\)"
    r"|\braiz(?:\s+quadrada\s+de)?\s*\(?\s*([\d.,]+)\s*\)?"
    r"|√\s*\(?\s*([\d.,]+)\s*\)?)"
)
_APROXIMACAO = r"\s*(?:\\approx|≈|\\cong|≅|=)\s*"
_RAIZ_APROXIMADA = re.compile(_RADICANDO + _APROXIMACAO + r"(-?\d+(?:[.,]\d+)?)")


def _casas_decimais(escrito: str) -> int:
    texto = str(escrito or "").strip().replace(",", ".")
    return len(texto.split(".", 1)[1]) if "." in texto else 0


def _tolerancia_de_arredondamento(escrito: str) -> float:
    """Meia unidade na ultima casa que o proprio texto mostrou.

    Arredondar e legitimo: a raiz de 475 vale 21,7945, e escrever "21,8" ou
    "22" esta certo. O que nao pode passar e "19,4". Uma tolerancia fixa
    recusaria o arredondamento honesto para inteiro; esta acompanha a
    precisao declarada.
    """
    return 0.5 * (10 ** -_casas_decimais(escrito)) + 1e-9


def _raiz_aproximada_incorreta(dados: dict) -> bool:
    textos = list(_coletar_textos_resultado_exatas(dados))
    textos.extend(
        str((passo or {}).get("conteudo", ""))
        for passo in (dados.get("passos_resolucao", []) or [])
        if isinstance(passo, dict)
    )

    for texto in textos:
        for achado in _RAIZ_APROXIMADA.finditer(str(texto or "")):
            grupos = achado.groups()
            radicando_txt = next((g for g in grupos[:5] if g), None)
            escrito_txt = grupos[5]
            radicando = _avaliar_expressao_numerica(radicando_txt)
            escrito = _normalizar_numero_float(escrito_txt)
            if radicando is None or escrito is None or radicando < 0:
                continue
            if abs(math.sqrt(radicando) - escrito) > _tolerancia_de_arredondamento(escrito_txt):
                return True
    return False


# MELHORIA: a mesma cegueira da raiz vale para o resto da lista de funcoes
# transcendentes -- sin, cos, tan e log tambem fazem o passo final ser pulado
# inteiro, e e nele que a resposta nasce em trigonometria e em logaritmo.
#
# A armadilha aqui e grau x radiano, e ela e severa: sin(30) vale 0,5 em graus
# e -0,988 em radianos. O Ensino Medio brasileiro trabalha em graus, mas a IA
# as vezes escreve o angulo em radianos (pi/6). Por isso esta regra recusa
# somente quando NENHUMA leitura plausivel fecha: se a conta bate em graus OU
# em radianos, passa. O mesmo para o log sem base -- log(100) pode ser 2
# (decimal), 4,605 (natural) ou 6,64 (base 2).
#
# Recusar so o indefensavel e de proposito. Uma validacao que erra joga fora
# questao boa e empurra a aula para o banco offline sem necessidade.
_TRIGONOMETRICAS = {
    "sin": math.sin,
    "sen": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "tg": math.tan,
}

_FUNCAO_APROXIMADA = re.compile(
    # `(?![a-z])` no lugar de `\b`: "_" e caractere de palavra, entao `\b` nao
    # existe entre "log" e "_{2}" -- a forma com base escrita nunca casava, e
    # `\log_{2}(8) = 4` passava sem ser conferido. O lookahead ainda barra
    # "logaritmo" e "sinal", que era o que o `\b` protegia.
    #
    # `(-\s*)?` antes da funcao: pH = -log(10^-3) = 3 e uma formula real do
    # banco de Quimica, e o sinal muda o resultado esperado. Sem capturar o
    # sinal, log10(0,001) = -3 era comparado direto com o "3" escrito e as 8
    # questoes de pH do banco offline seriam recusadas -- eram todas
    # verdadeiras, so o sinal ficava de fora da conta.
    r"(-\s*)?\\?\b(sen|sin|cos|tg|tan|log|ln)(?![a-z])"
    r"(?:\s*_\s*\{?\s*(\d+(?:[.,]\d+)?)\s*\}?)?"     # base do log, quando escrita
    r"\s*\(?\s*([^()=≈]{1,40}?)\s*\)?\s*"
    r"(?:\\approx|≈|\\cong|≅|=)\s*"
    r"(-?\d+(?:[.,]\d+)?)"
)

# MELHORIA: achado ao rodar a suite depois de ligar a checagem -- um teste
# ja existente usava "h = 50 \cdot tan(60) = 86,6". Comparar tan(60) puro
# (1,73) com o 86,6 escrito reprovava uma questao certa: o resultado inclui
# o coeficiente "50 *", nao e so o valor da funcao. So da para julgar quando
# a funcao e o unico termo do lado esquerdo do "="; com coeficiente na
# frente ("50 \cdot tan(...)"), o valor final depende da multiplicacao
# tambem, que esta fora do alcance desta checagem.
_MULTIPLICADOR_ANTES = re.compile(r"(?:[0-9A-Za-z)\}]|\\cdot|\\times|[*×·])\s*$")

_MARCA_DE_GRAU = re.compile(r"°|\bgraus?\b|\\circ|\^\s*\{?\s*o\s*\}?", re.IGNORECASE)
_MARCA_DE_PI = re.compile(r"\\pi\b|π")

# MELHORIA: o banco de Quimica escreve "10⁻³" com expoente em sobrescrito
# Unicode, nao "10^{-3}" ou "10^-3". Sem resolver, "⁻³" nao e letra (passa
# pelo filtro acima) nem digito ascii comum -- o normalizador that avalia a
# expressao apaga os dois caracteres em silencio e "10⁻³" virava so "10".
_SUPERSCRITO = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_EXPOENTE_SUPERSCRITO = re.compile(r"(\d)([⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)")


def _resolver_expoente_superscrito(texto: str) -> str:
    return _EXPOENTE_SUPERSCRITO.sub(
        lambda m: f"{m.group(1)}**({m.group(2).translate(_SUPERSCRITO)})", texto
    )


def _numero_do_argumento(texto: str) -> float | None:
    """O valor numerico do que esta dentro da funcao, com pi resolvido.

    MELHORIA: `_avaliar_expressao_numerica` APAGA letra sobrando em silencio
    (mantem so digito/operador) em vez de recusar. Achado contra o proprio
    banco offline: o template "log 6 = log 2 + log 3 ≈ 0,30 + 0,48 = 0,78"
    nao tem parenteses, entao o argumento capturado do PRIMEIRO "log" (regex
    gulosa ate o proximo "=" ou "≈") engolia "2 + log 3" inteiro -- e a
    mutilacao virava "2 + 3" = 5 em vez de recusar por nao saber avaliar.
    Uma letra sobrando so pode significar outra funcao dentro do argumento
    ou uma incognita: nos dois casos, a resposta certa e "nao julgar".
    """
    bruto = _resolver_expoente_superscrito(str(texto or ""))
    bruto = _MARCA_DE_PI.sub(f"({math.pi})", bruto)
    bruto = _MARCA_DE_GRAU.sub(" ", bruto)
    bruto = _traduzir_operadores_latex(bruto)
    if re.search(r"[A-Za-z]", bruto):
        return None
    return _avaliar_expressao_numerica(bruto)


def _valores_plausiveis(nome: str, base_txt: str, argumento_txt: str) -> list[float]:
    """Todo resultado que uma leitura honesta do texto poderia produzir."""
    valor = _numero_do_argumento(argumento_txt)
    if valor is None:
        return []

    if nome in _TRIGONOMETRICAS:
        funcao = _TRIGONOMETRICAS[nome]
        if _MARCA_DE_GRAU.search(argumento_txt):
            leituras = [math.radians(valor)]
        elif _MARCA_DE_PI.search(argumento_txt):
            leituras = [valor]                        # pi/6 ja e radiano
        else:
            leituras = [math.radians(valor), valor]   # ambiguo: vale qualquer uma
        resultados = []
        for radianos in leituras:
            try:
                obtido = funcao(radianos)
            except ValueError:
                continue
            # tan(90 graus) estoura: nao ha valor para comparar.
            if math.isfinite(obtido) and abs(obtido) < 1e12:
                resultados.append(obtido)
        return resultados

    if valor <= 0:
        return []
    base = _normalizar_numero_float(base_txt) if base_txt else None
    if base is not None and base > 0 and base != 1:
        return [math.log(valor, base)]
    if nome == "ln":
        return [math.log(valor)]
    # "log" sem base: decimal e o padrao da escola, mas natural e base 2
    # aparecem escritos assim tambem.
    return [math.log10(valor), math.log(valor), math.log2(valor)]


# MELHORIA: com coeficiente na frente ("h = 50 \cdot tan(60) = 86,6") a
# checagem se desligava, porque comparar tan(60) puro (1,73) com o 86,6
# escrito reprovaria uma questao certa -- o resultado inclui a multiplicacao.
# O buraco era que "h = 50 \cdot tan(60) = 999,9" tambem passava.
#
# Agora a funcao e resolvida DENTRO da expressao e o todo e avaliado. A regra
# de ouro continua a mesma das outras checagens: como grau x radiano e
# ambiguo, cada leitura plausivel gera uma versao da expressao, e so recusa
# quando NENHUMA fecha.
_CHAMADA_DE_FUNCAO = re.compile(
    r"\\?\b(sen|sin|cos|tg|tan|log|ln)(?:\s*_\s*\{?\s*(\d+)\s*\}?)?\s*\(([^()]{1,40})\)"
)

# Onde a linha declara um resultado. Os mesmos marcadores de _APROXIMACAO,
# sem os espacos em volta, para achar a POSICAO de cada um.
_SEPARADOR_DE_RESULTADO = re.compile(r"\\approx|≈|\\cong|≅|=")


def _leituras_da_expressao(expressao: str) -> list[str]:
    """A expressao com cada funcao trocada pelo valor, em todas as leituras.

    Devolve [] quando ha funcao que nao da para resolver (incognita dentro,
    angulo indefinido): nesse caso nao ha o que julgar.
    """
    achados = list(_CHAMADA_DE_FUNCAO.finditer(expressao))
    if not achados:
        return []
    versoes = [expressao]
    for achado in achados:
        valores = _valores_plausiveis(
            achado.group(1).lower(), achado.group(2) or "", achado.group(3)
        )
        if not valores:
            return []
        versoes = [
            versao.replace(achado.group(0), f"({valor})")
            for versao in versoes
            for valor in valores
        ]
        # Uma linha com muitas funcoes multiplicaria as versoes sem limite.
        if len(versoes) > 16:
            return []
    return versoes


def _expressao_com_funcao_diverge(texto: str, fim_do_achado: int) -> bool:
    """O resultado escrito bate com a expressao inteira, funcao resolvida?"""
    trecho = texto[:fim_do_achado]
    # MELHORIA: partia so no "=", e a IA escreve "50 * tan(60) ≈ 86,6" tambem
    # -- sem "=" a linha inteira virava o "resultado" e o caso escapava. Um
    # mutante mostrou: "50 * tan(60) ≈ 999,9" passava incontestado.
    separadores = list(_SEPARADOR_DE_RESULTADO.finditer(trecho))
    if not separadores:
        return False
    ultimo = separadores[-1]
    esquerda, direita = trecho[: ultimo.start()], trecho[ultimo.end():]
    escrito = _normalizar_numero_float(_ultimo_numero_normalizado(direita))
    if escrito is None:
        return False

    # A expressao e o que vem depois do separador anterior, quando ha um
    # ("h = 50 * tan(60)" -> "50 * tan(60)"). Sem esse recorte, o "=" some no
    # normalizador e cola os numeros vizinhos: "5 + 2 = 7 * tan(30)" viraria
    # "5+27*tan(30)".
    anteriores = list(_SEPARADOR_DE_RESULTADO.finditer(esquerda))
    expressao = esquerda[anteriores[-1].end():] if anteriores else esquerda
    valores = [
        _avaliar_expressao_numerica(versao) for versao in _leituras_da_expressao(expressao)
    ]
    valores = [valor for valor in valores if valor is not None]
    if not valores:
        return False

    tolerancia = _tolerancia_de_arredondamento(_ultimo_numero_normalizado(direita))
    return not any(abs(valor - escrito) <= tolerancia for valor in valores)


def _funcao_aproximada_incorreta(dados: dict) -> bool:
    textos = list(_coletar_textos_resultado_exatas(dados))
    textos.extend(
        str((passo or {}).get("conteudo", ""))
        for passo in (dados.get("passos_resolucao", []) or [])
        if isinstance(passo, dict)
    )

    for texto in textos:
        texto = str(texto or "")
        for achado in _FUNCAO_APROXIMADA.finditer(texto):
            if _MULTIPLICADOR_ANTES.search(texto[: achado.start()]):
                # A funcao esta dentro de uma expressao maior: julga o todo.
                if _expressao_com_funcao_diverge(texto, achado.end()):
                    return True
                continue
            sinal_txt, nome, base_txt, argumento_txt, escrito_txt = achado.groups()
            escrito = _normalizar_numero_float(escrito_txt)
            if escrito is None:
                continue
            plausiveis = _valores_plausiveis(nome.lower(), base_txt or "", argumento_txt)
            if sinal_txt:
                plausiveis = [-valor for valor in plausiveis]
            if not plausiveis:
                continue
            tolerancia = _tolerancia_de_arredondamento(escrito_txt)
            if not any(abs(valor - escrito) <= tolerancia for valor in plausiveis):
                return True
    return False


def _resposta_marcada_diverge_do_resultado_final(dados: dict) -> bool:
    """
    MELHORIA: generaliza o bug do Bhaskara (resposta calculada certa nos
    passos, mas a alternativa marcada como correta era outro numero sem
    relacao) para QUALQUER tipo de questao de exatas — nao so equacao do
    2o grau. Os detectores especificos (_valor_esperado_progressao_aritmetica
    etc.) so cobrem alguns poucos padroes reconheciveis por regex; esta
    funcao usa o mesmo "resultado final" que _resultado_exatas_conflitante
    ja coleta (dos passos_resolucao/explicacao) e confere se pelo menos um
    dos numeros ali aparece na alternativa marcada, para qualquer conta.
    """
    candidatos = _coletar_textos_resultado_exatas(dados)
    if not candidatos:
        return False
    # MELHORIA: usava candidatos[-1] (o ultimo item da lista), mas o ultimo
    # candidato costuma ser um bloco "explicacao" tipo "resultado" que so
    # descreve o resultado em palavras (ex: "Forca resultante", sem nenhum
    # numero), inserido DEPOIS do passo final numerico na ordem de coleta.
    # Isso zerava numeros_resultado e a funcao nunca detectava divergencia
    # nenhuma (visto ao vivo: Groq gerando "5 N" como passo final, cuja
    # conta nem batia, mas a alternativa marcada passou incontestada porque
    # o candidato realmente checado era um texto sem digitos). Percorre de
    # tras pra frente e usa o primeiro candidato que de fato tem numero.
    numeros_resultado: list[float] = []
    for texto in reversed(candidatos):
        numeros_resultado = [
            valor
            for valor in (_normalizar_numero_float(n) for n in _extrair_numeros_normalizados(texto))
            if valor is not None
        ]
        if numeros_resultado:
            break
    if not numeros_resultado:
        return False

    opcoes = dados.get("opcoes", []) or []
    try:
        correta_idx = int(dados.get("correta", 0))
    except Exception:
        return False
    if not (0 <= correta_idx < len(opcoes)):
        return False

    opcao_correta = str(opcoes[correta_idx])
    return not any(_opcao_contem_valor(opcao_correta, valor) for valor in numeros_resultado)


def _textos_questao_completos(dados: dict) -> str:
    partes = [
        str(dados.get("pergunta", "") or ""),
        str(dados.get("formula", "") or ""),
        " ".join(str(item) for item in (dados.get("subformulas", []) or [])),
    ]
    for passo in dados.get("passos_resolucao", []) or []:
        if isinstance(passo, dict):
            partes.append(str(passo.get("titulo", "") or ""))
            partes.append(str(passo.get("conteudo", "") or ""))
        else:
            partes.append(str(passo or ""))
    for bloco in dados.get("explicacao", []) or []:
        if isinstance(bloco, dict):
            partes.append(str(bloco.get("conteudo", "") or ""))
        else:
            partes.append(str(bloco or ""))
    return " ".join(partes).lower()


def _formula_matematica_incoerente(dados: dict) -> bool:
    pergunta = str(dados.get("pergunta", "") or "").lower()
    formula = str(dados.get("formula", "") or "").lower()
    texto = _textos_questao_completos(dados)

    formula_bhaskara = any(token in formula for token in ("sqrt", "delta", "\\pm", "b^2", "4ac"))
    assunto_pa = any(token in texto for token in ("progressao aritmetica", "progressão aritmética", " pa ", "a_1", "a1", "razao", "razão", "n-1"))
    if formula_bhaskara and assunto_pa and not any(token in pergunta for token in ("bhaskara", "2o grau", "2º grau", "quadratica", "quadrática")):
        return True

    formula_pa = any(token in formula for token in ("a_n", "a_1", "n-1", "raz"))
    assunto_bhaskara = any(token in pergunta for token in ("bhaskara", "2o grau", "2º grau", "quadratica", "quadrática"))
    if formula_pa and assunto_bhaskara:
        return True

    return False


def _avaliar_no_seguro(no):
    if isinstance(no, ast.Expression):
        return _avaliar_no_seguro(no.body)
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return float(no.value)
    if isinstance(no, ast.BinOp) and type(no.op) in _OPERADORES_SEGUROS:
        return _OPERADORES_SEGUROS[type(no.op)](_avaliar_no_seguro(no.left), _avaliar_no_seguro(no.right))
    if isinstance(no, ast.UnaryOp) and type(no.op) in _OPERADORES_SEGUROS:
        return _OPERADORES_SEGUROS[type(no.op)](_avaliar_no_seguro(no.operand))
    raise ValueError("expressao-insegura")


def _traduzir_operadores_latex(texto: str) -> str:
    # MELHORIA: normalizacao de simbolos LaTeX (\times, \div, \cdot,
    # \frac{}{}, etc.) compartilhada entre _avaliar_expressao_numerica e
    # _tem_operador_binario -- antes cada uma reimplementava seu proprio
    # subconjunto dessas substituicoes, e so a primeira sabia converter
    # "\frac{20}{4}" pra "(20)/(4)". Isso fazia _tem_operador_binario
    # concluir (errado) que um passo com \frac nao tinha operador nenhum
    # (\frac{20}{4} virava so os digitos colados "204", sem operador),
    # desligando a checagem de divergencia silenciosamente pra esse formato.
    #
    # Separada de _normalizar_expressao_para_avaliacao porque aquela APAGA as
    # letras no fim, e quem precisa distinguir "2x + 5" (tem incognita) de
    # "15 - 5" (conta pronta) nao pode receber o texto ja sem letras.
    expr = str(texto or "").replace(",", ".").replace("^", "**")
    expr = expr.replace(r"\times", "*").replace(r"\div", "/")
    expr = expr.replace(r"\cdot", "*").replace("×", "*").replace("÷", "/").replace("·", "*")
    return re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", expr)


def _normalizar_expressao_para_avaliacao(texto: str) -> str:
    expr = _traduzir_operadores_latex(texto)
    expr = re.sub(r"[^0-9\.\+\-\*\/\(\)\s]", "", expr)
    expr = re.sub(r"\s+", "", expr)
    return expr


def _avaliar_expressao_numerica(texto: str) -> float | None:
    # MELHORIA: expressoes com +/- (duas raizes numa linha so, como no
    # formato padrao de Bhaskara) ou com radiciacao nao resolvida nao tem um
    # unico valor numerico determinado. Sem este corte, o proximo passo (que
    # so mantem digitos/operadores) apagava "\pm"/"\sqrt{" silenciosamente e
    # concatenava os digitos sobrando (ex: "\frac{-5 \pm \sqrt{25-24}}{2}"
    # virava "-525-242" = -767), um numero fantasma que era comparado como se
    # fosse o resultado real, rejeitando respostas corretas (visto em producao
    # com Groq/Bhaskara: "-2 e -3" acusado de "resultado-aritmetico-invalido").
    # O expoente da unidade nao e da conta: ver _sem_expoente_de_unidade.
    bruto = _sem_expoente_de_unidade(str(texto or ""))
    if _SINAIS_DE_DUAS_SOLUCOES.search(bruto):
        return None
    # MELHORIA: so o "\sqrt" do LaTeX era barrado aqui. Escrita em ASCII,
    # "x = raiz(25)" seguia adiante -- e o normalizador, que mantem apenas
    # digitos e operadores, apagava o "raiz" e devolvia 25 em vez de 5. Um
    # numero errado e pior que nenhum: ele e comparado com a resposta e
    # recusa a questao. A mesma lista de funcoes que a outra guarda usa
    # resolve os dois casos.
    if _texto_tem_funcao_transcendente(_texto_ascii_simples(bruto)):
        return None
    expr = _normalizar_expressao_para_avaliacao(bruto)
    if not expr or not re.search(r"\d", expr):
        return None
    try:
        return float(_avaliar_no_seguro(ast.parse(expr, mode="eval")))
    except Exception:
        return None


def _normalizar_numero_float(valor: str) -> float | None:
    texto = str(valor or "").strip().replace(",", ".")
    try:
        return float(texto)
    except Exception:
        return None


def _valores_proximos(a: float, b: float, tolerancia: float | None = None) -> bool:
    tol = tolerancia if tolerancia is not None else max(0.02, abs(b) * 0.02)
    return abs(a - b) <= tol


def _extrair_primeiro_float(padrao: str, texto: str, flags: int = re.IGNORECASE) -> float | None:
    match = re.search(padrao, texto, flags=flags)
    if not match:
        return None
    return _normalizar_numero_float(match.group(1))


def _questao_quimica_molar_inconsistente(dados: dict) -> bool:
    texto = _textos_questao_completos(dados)
    texto_norm = texto.lower()
    if not any(token in texto_norm for token in ("concentracao molar", "concentração molar", "molaridade")):
        return False

    massa = _extrair_primeiro_float(r"(-?\d+(?:[.,]\d+)?)\s*g\b(?!\s*/\s*mol)", texto)
    massa_molar = _extrair_primeiro_float(r"(-?\d+(?:[.,]\d+)?)\s*g\s*/\s*mol\b", texto)
    volume_match = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(mL|L)\b", texto, flags=re.IGNORECASE)
    if massa is None or massa_molar in (None, 0) or not volume_match:
        return False

    volume = _normalizar_numero_float(volume_match.group(1))
    unidade_volume = volume_match.group(2).lower()
    if volume in (None, 0):
        return False
    volume_l = volume / 1000 if unidade_volume == "ml" else volume
    esperado = massa / massa_molar / volume_l

    opcoes = [str(opcao) for opcao in (dados.get("opcoes", []) or [])]
    try:
        correta_idx = int(dados.get("correta", 0))
    except Exception:
        correta_idx = 0
    opcao_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""
    valor_opcao_correta = _ultimo_numero_normalizado(opcao_correta)
    valor_opcao = _normalizar_numero_float(valor_opcao_correta)
    if valor_opcao is not None and not _valores_proximos(valor_opcao, esperado):
        return True

    for texto_resultado in _coletar_textos_resultado_exatas(dados):
        resultado_norm = texto_resultado.lower()
        ultimo = _normalizar_numero_float(_ultimo_numero_normalizado(texto_resultado))
        if ultimo is None:
            continue
        if any(token in resultado_norm for token in ("resposta correta", "deve ser", "deveria ser")):
            if not _valores_proximos(ultimo, esperado):
                return True

    return False


# MELHORIA: a checagem antiga era "tan"/"sen"/"sin"/"cos" como SUBSTRING
# solta (ex: `"tan" in texto`) pra pular passos com funcao trigonometrica
# (que essas checagens nao sabem avaliar direito). Isso tambem casava com
# palavras comunissimas de Fisica que nada tem a ver com trigonometria --
# "dis_tan_cia", "cons_tan_te", "in_stan_te" -- desligando a checagem
# inteira toda vez que o passo so menciona "distancia" ou "constante".
# Usa termos completos (palavra por extenso ou "nome(" de chamada de
# funcao) em vez de fragmentos de 3 letras.
_TERMOS_FUNCAO_TRANSCENDENTE = (
    "tangente",
    "tan(",
    "cosseno",
    "cos(",
    "seno",
    "sen(",
    "sin(",
    "sqrt",
    # MELHORIA: havia "raiz quadrada" e "sqrt", mas nao "raiz(" -- a forma
    # que a IA usa quando escreve em ASCII em vez de LaTeX. Sem isto,
    # "x = raiz(25)" era AVALIADO, e o normalizador (que so mantem digitos e
    # operadores) apagava o "raiz" e devolvia 25 em vez de 5. A validacao
    # entao comparava 25 com a resposta 5 e recusava uma questao certa.
    "raiz quadrada",
    "raiz(",
    "raiz (",
    "logaritmo",
    "log(",
    # MELHORIA: "log(" nao casa com "log_2(4)", a forma com base escrita --
    # e "_" e caractere de palavra, entao nem um \b ajudaria. O passo
    # "log_2(4) = 2" era comparado como aritmetica comum contra o passo
    # anterior ("2^2 = 4"), dando 4 != 2: falso positivo em 88 questoes de
    # logaritmo do banco do Laboratorio. Mesma armadilha do "_" corrigida
    # em _FUNCAO_APROXIMADA.
    "log_",
)

# "+/-" quer dizer DUAS solucoes numa linha so (o formato padrao de
# Bhaskara), entao aquele trecho nao tem um valor unico para comparar.
#
# MELHORIA: so o LaTeX (\pm, \mp) e o unicode (±, ∓) eram reconhecidos. Em
# ASCII -- "+-", "+/-", "mais ou menos" -- a expressao passava adiante e era
# reduzida a UM numero: "(-5 +- 1)/2" virava -3, que e uma das duas raizes.
# A validacao entao comparava essa raiz sozinha com a alternativa marcada e,
# quando a marcada era a OUTRA, recusava a questao.
#
# Ser generoso aqui e seguro: reconhecer a mais significa apenas nao
# comparar um trecho que talvez desse para comparar. Reconhecer a menos
# significa recusar questao certa.
_SINAIS_DE_DUAS_SOLUCOES = re.compile(
    r"\\pm|\\mp|±|∓|\+\s*/\s*-|-\s*/\s*\+|\+-|-\+|mais\s+ou\s+menos",
    re.IGNORECASE,
)


def _texto_tem_funcao_transcendente(texto_ascii: str) -> bool:
    return any(termo in texto_ascii for termo in _TERMOS_FUNCAO_TRANSCENDENTE)


def _deve_pular_comparacao_numerica(*textos: str) -> bool:
    # MELHORIA: as duas checagens de "esse trecho nao tem um unico valor
    # numerico bem definido pra comparar" (funcao trigonometrica/log/raiz,
    # ou "+/-" com duas solucoes numa linha so) estavam duplicadas entre
    # _resultado_aritmetico_incorreto e _passo_final_diverge_do_calculo_
    # anterior -- uma delas nem tinha a guarda de "\pm" explicita (contava
    # com _avaliar_expressao_numerica pular por conta propria, o que
    # funciona mas deixa a intencao implicita). Unificado num so lugar.
    texto_junto = " ".join(textos)
    if _texto_tem_funcao_transcendente(_texto_ascii_simples(texto_junto)):
        return True
    return bool(_SINAIS_DE_DUAS_SOLUCOES.search(texto_junto))


def _resultado_aritmetico_incorreto(dados: dict) -> bool:
    textos = _coletar_textos_resultado_exatas(dados)
    textos.extend(
        str((passo or {}).get("conteudo", "")).strip()
        for passo in (dados.get("passos_resolucao", []) or [])
        if isinstance(passo, dict)
    )

    for texto in textos:
        if _deve_pular_comparacao_numerica(texto):
            continue
        partes = [parte.strip() for parte in str(texto or "").split("=") if parte.strip()]
        if len(partes) < 2:
            continue
        avaliacoes = [(_avaliar_expressao_numerica(parte), parte) for parte in partes]
        numericas = [(valor, parte) for valor, parte in avaliacoes if valor is not None]
        if len(numericas) < 2:
            continue
        valor_anterior, parte_anterior = numericas[-2]
        valor_final, parte_final = numericas[-1]
        # MELHORIA: usava um "any(op in parte_anterior for op in (...))"
        # proprio, que nao tinha a guarda de "sinal no inicio nao e
        # operador" que _tem_operador_binario ja tem (ver seu comentario) --
        # um "parte_anterior" que fosse so um numero negativo como "-98"
        # seria tratado como se fosse uma conta de verdade, so por causa do
        # sinal. Reaproveita a mesma checagem usada em
        # _passo_final_diverge_do_calculo_anterior pra nao ter essa mesma
        # classe de bug corrigida num lugar e nao no outro.
        if _tem_operador_binario(parte_anterior) and abs(valor_anterior - valor_final) > 0.01:
            return True
    return False


_VARIAVEL_COM_INDICE_PATTERN = re.compile(r"\b[a-zA-Zα-ωΑ-Ω]_\d+\b")


def _remover_variaveis_com_indice(texto: str) -> str:
    # MELHORIA: variaveis tipo "a_5" ou "F_1" (letra + indice/subscrito com
    # "_") tem um digito colado que _avaliar_expressao_numerica nao
    # diferencia de um numero de verdade -- ao tirar so as letras, o digito
    # do indice sobra solto e se cola no proximo numero da expressao,
    # formando um numero fantasma (visto em teste real: "a_5 = 2 + (5-1)*3"
    # virava "52+(5-1)*3" = 64 em vez do 2+4*3 = 14 esperado). Remove a
    # variavel inteira (letra + indice) em vez de so a letra, pra nao deixar
    # digito solto pra tras. Exige o "_" de proposito (nao casa "O2"/"H2"/
    # "N2" sem underscore) pra nao apagar formulas quimicas de Laboratorio
    # de Exatas -- o padrao de variavel com indice usado pela IA neste app
    # sempre vem com "_" (ver formulas com \frac, \cdot etc.).
    return _VARIAVEL_COM_INDICE_PATTERN.sub(" ", str(texto or ""))


def _tem_operador_binario(texto: str) -> bool:
    expr = _normalizar_expressao_para_avaliacao(texto)
    # MELHORIA: um sinal no INICIO da expressao ("-98") e so o sinal do
    # numero, nao uma operacao entre dois valores -- remove pra nao tratar
    # um passo com um unico numero negativo como se fosse uma conta.
    expr = re.sub(r"^[+\-]", "", expr)
    return bool(re.search(r"[+\-*/]", expr))


# MELHORIA: `_ultimo_numero_normalizado` pegava o ULTIMO numero literal do
# passo final, e em tres formatos comuns esse numero nao e o resultado:
#
#   "A = 48 m^2"        -> lia 2   (o expoente da UNIDADE), nao 48
#   "V = 125 cm^3"      -> lia 3
#   "P = 3/10"          -> lia 10  (o denominador), nao 0,3
#   "Vertice = (3, 4)"  -> lia 4   (um par ordenado nao e um numero)
#
# Medido contra os bancos offline: os tres formatos respondiam por 140 dos
# 228 falsos positivos desta checagem -- e eram todos defeito do verificador,
# nao das questoes.
_PAR_ORDENADO = re.compile(r"\(\s*-?\d+(?:[.,]\d+)?\s*,\s*-?\d+(?:[.,]\d+)?\s*\)")

# "48 m^2", "125 cm³": o expoente pertence a unidade. Exige letra entre o
# numero e o expoente, entao "2^3 = 8" (expoente matematico) nao casa.
_EXPOENTE_DE_UNIDADE = re.compile(
    r"(\d[\d.,]*)\s*([a-zà-ÿ°µ]+)\s*(?:\^\s*\{?\s*\d\s*\}?|[¹²³])",
    re.IGNORECASE,
)


def _valor_do_passo_final(texto: str) -> float | None:
    """O numero que o passo final de fato afirma como resultado."""
    bruto = str(texto or "")
    if _PAR_ORDENADO.search(bruto):
        # (3, 4) e um ponto, nao um valor: nao ha o que comparar.
        return None

    bruto = _EXPOENTE_DE_UNIDADE.sub(lambda m: f"{m.group(1)} ", bruto)

    # O resultado e o que vem depois do ultimo "=", quando ha um.
    lado = bruto.rsplit("=", 1)[-1] if "=" in bruto else bruto

    # A unidade que SOBRA ("48 m", "3,5 m/s") nao precisa de tratamento: o
    # avaliador ja descarta letra. So o expoente dela atrapalhava, e isso e
    # resolvido acima -- um mutante mostrou que uma limpeza extra aqui era
    # rede que nao pegava nada.
    #
    # Avaliar preserva a fracao ("3/10" -> 0,3); o ultimo numero solto a
    # quebraria no denominador.
    valor = _avaliar_expressao_numerica(lado)
    if valor is not None:
        return valor
    return _normalizar_numero_float(_ultimo_numero_normalizado(lado))


def _valor_so_repetido(texto: str) -> float | None:
    """O numero que um passo so REPETE, sem fazer conta: "v = 18 m/s" -> 18.

    So e chamado para passo que nao e conta (ver
    _passo_final_diverge_do_calculo_anterior). None quando nao da para dizer
    que o passo apenas repete um resultado: mais de um "=" ("v_0 = 0, a = 3")
    ou mais de um numero ("v = 18 m/s (64,8 km/h)").
    """
    bruto = str(texto or "")
    if bruto.count("=") > 1:
        return None
    numeros = _extrair_numeros_normalizados(_sem_expoente_de_unidade(bruto.rpartition("=")[2]))
    if len(numeros) != 1:
        return None
    return _normalizar_numero_float(numeros[0])


# "Resultado Final", "Resultado", "Resposta final" -- nao "Resultados parciais".
_TITULO_DE_RESULTADO = re.compile(r"\b(?:resultado|resposta)\b")


def _indice_do_passo_final(passos: list[dict]) -> int | None:
    """O passo que traz o resultado: o marcado final=True; sem marca, o ultimo,
    se o titulo dele diz que e o resultado. None quando nao da para saber.

    MELHORIA: sem a marca, a regra do passo final nao rodava. A tela nao olha a
    marca -- laboratorio.html escreve o TITULO do passo --, entao a 08c do TG
    sem "final": true aparecia igualzinha ("Resultado Final  15 m/s", depois de
    "v = 0 + 3 * 6 = 18") e passava. A marca falta de verdade: 1 das 6
    questoes inteiras do Render e 1 das 29 resolucoes de logs_pedagogicos.

    So o ULTIMO passo, e so com titulo de resultado: um "3º Passo" sem marca
    pode ser conta intermediaria, e ai nao ha o que concluir.
    """
    marcados = [indice for indice, passo in enumerate(passos) if passo.get("final")]
    if marcados:
        return marcados[-1]
    if passos and _TITULO_DE_RESULTADO.search(_texto_ascii_simples(passos[-1].get("titulo", ""))):
        return len(passos) - 1
    return None


def _passo_final_diverge_do_calculo_anterior(dados: dict) -> bool:
    """
    MELHORIA: quando a IA escreve os passos como expressoes soltas, sem "="
    ligando uma linha a outra (ex: "20 N - 15 N - 98 N" numa linha e "-98 N +
    5 N" na seguinte, terminando com "5 N" como passo final) o
    _resultado_aritmetico_incorreto nunca dispara, porque ele so compara os
    dois lados de um "=" na MESMA linha -- aqui nao ha nenhum "=". Visto ao
    vivo com Groq no Laboratorio de Exatas: o passo final ("5 N") nao batia
    com a conta do passo anterior (20-15-98 = -93), e a questao passou pela
    validacao inteira sem ser pega. Aqui pega o passo final (ver
    _indice_do_passo_final) e confere se o numero dele bate com o valor da
    ultima conta antes dele (um passo com operador binario, nao so um numero
    com sinal), pulando os passos que apenas repetem esse valor.
    """
    passos = [
        passo
        for passo in (dados.get("passos_resolucao", []) or [])
        if isinstance(passo, dict) and str(passo.get("conteudo", "")).strip()
    ]
    idx_final = _indice_do_passo_final(passos)
    if idx_final is None or idx_final == 0:
        return False

    texto_final = _remover_variaveis_com_indice(passos[idx_final].get("conteudo", ""))

    # MELHORIA: o passo final era comparado so com o IMEDIATAMENTE anterior, e
    # so quando ele era uma conta. A IA costuma pôr entre os dois um passo que
    # apenas repete o valor, e esse passo desligava a checagem:
    #
    #     2º Passo         v = 0 + 3 * 6 = 18
    #     3º Passo         v = 18 m/s
    #     Resultado Final  15 m/s        <- e 15 m/s marcado como certo
    #
    # Foi assim que a captura 08c do TG (10/09/2026, Hugging Face) mostrou
    # "Acertou" com a resposta errada. Agora a busca volta por cima dos passos
    # que so repetem um valor ate achar a conta -- desde que TODOS repitam o
    # resultado dela. Um passo com outro numero ("t = 6 s") pode ser outra
    # grandeza, e ai nao ha o que concluir.
    repetidos: list[float] = []
    for indice in range(idx_final - 1, -1, -1):
        texto = _remover_variaveis_com_indice(passos[indice].get("conteudo", ""))
        if _deve_pular_comparacao_numerica(texto, texto_final):
            return False
        valor_conta, tem_operador = _valor_e_operador_do_passo(texto)
        if tem_operador and valor_conta is not None:
            if not all(_valores_proximos(repetido, valor_conta) for repetido in repetidos):
                return False
            valor_final = _valor_do_passo_final(texto_final)
            if valor_final is None:
                return False
            return not _valores_proximos(valor_conta, valor_final)
        repetido = _valor_so_repetido(texto)
        if repetido is None:
            return False
        repetidos.append(repetido)
    return False


def _valor_e_operador_do_passo(texto: str) -> tuple[float | None, bool]:
    # MELHORIA: quando o passo em si ja tem "=" (ex: "20 N - 15 N - 98 N =
    # -93 N", formato comum em passos de Laboratorio de Exatas — ver
    # tests/test_validacao_ia.py:116-117), _avaliar_expressao_numerica
    # tratava a linha inteira como UMA expressao so, sem separador onde o
    # "=" foi removido, e colava os digitos dos dois lados (20-15-98-93
    # virava -186 em vez de -93), rejeitando uma questao correta como se o
    # passo final divergisse. Quando ha "=", usa o valor que o PROPRIO
    # passo afirma como resultado (o que vem depois do ultimo "="), assim
    # como o passo final tambem e lido pelo seu ultimo numero — a conta em
    # si (antes do "=") ja e conferida por _resultado_aritmetico_incorreto.
    if "=" in texto:
        antes, _, depois = texto.rpartition("=")
        if _tem_operador_binario(antes):
            return _normalizar_numero_float(_ultimo_numero_normalizado(depois)), True
        if _tem_operador_binario(depois):
            return _avaliar_expressao_numerica(depois), True
        return None, False
    if not _tem_operador_binario(texto):
        return None, False
    return _avaliar_expressao_numerica(texto), True


_ORDINAIS_TERMO_PA = {
    "primeiro": 1,
    "segundo": 2,
    "terceiro": 3,
    "quarto": 4,
    "quinto": 5,
    "sexto": 6,
    "setimo": 7,
    "oitavo": 8,
    "nono": 9,
    "decimo": 10,
    "decimo primeiro": 11,
    "decimo segundo": 12,
    "decimo terceiro": 13,
    "decimo quarto": 14,
    "decimo quinto": 15,
    "decimo sexto": 16,
    "decimo setimo": 17,
    "decimo oitavo": 18,
    "decimo nono": 19,
    "vigesimo": 20,
}

_ORDINAL_TERMO_PATTERN = re.compile(
    r"\b(\d+|"
    + "|".join(re.escape(chave) for chave in sorted(_ORDINAIS_TERMO_PA, key=len, reverse=True))
    + r")\s*[ºo]?\s*termo\b"
)


def _posicao_ordinal_termo(token: str) -> int | None:
    token = token.strip()
    if token.isdigit():
        return int(token)
    return _ORDINAIS_TERMO_PA.get(token)


def _termos_progressao_citados(texto_ascii: str) -> list[tuple[int, float | None]]:
    """Extrai pares (posicao, valor) de mencoes a termos de PA/PG no texto,
    tanto em forma numeral ("5o termo") quanto por extenso ("quinto termo").
    Quando a mencao nao vem seguida de um valor, e o termo que a questao
    pede pra descobrir, entao o valor volta None.
    """
    termos = []
    for match in _ORDINAL_TERMO_PATTERN.finditer(texto_ascii):
        posicao = _posicao_ordinal_termo(match.group(1))
        if posicao is None:
            continue
        resto = texto_ascii[match.end():match.end() + 20]
        valor_match = re.match(r"\s*(?:vale|=)\s*(-?\d+(?:\.\d+)?)", resto)
        valor = _normalizar_numero_float(valor_match.group(1)) if valor_match else None
        termos.append((posicao, valor))
    return termos


def _valor_esperado_progressao_aritmetica(dados: dict) -> float | None:
    texto = _textos_questao_completos(dados).replace(",", ".")
    texto_norm = texto.lower()
    if not any(token in texto_norm for token in ("progressao aritmetica", "progressão aritmética", " pa ", "a_n", "a1", "a_1")):
        return None
    # MELHORIA: "a1", "a_n" e "razao" tambem sao da PROGRESSAO GEOMETRICA, e o
    # detector calculava a1 + (n - 1)r para ela: "Em uma PG, a1 = 2, razao = 3
    # e n = 5" esperava 14 e recusava o 162 certo. Para "a soma dos oito
    # termos" esperava o oitavo termo. Medido em 14/09/2026: as 20 PGs do banco
    # recusadas, e uma soma de PA certa (124) recusada no Render. O detector
    # nao sabe essas contas; nao julgar e o certo.
    if re.search(r"progressao geometrica|\bpg\b|\bq\s*=|\bq\s*\^|\bsoma\b|\bs_\{?(?:n\b|\d)", _texto_ascii_simples(texto)):
        return None

    a1 = _extrair_primeiro_float(r"(?:a_?1|primeiro\s+termo\s+a?)\s*(?:=|vale)\s*(-?\d+(?:[.,]\d+)?)", texto)
    razao = _extrair_primeiro_float(r"(?:r|razao|razão|d|diferença\s+comum|diferenca\s+comum)\s*=\s*(-?\d+(?:[.,]\d+)?)", texto)
    n = _extrair_primeiro_float(r"\bn\s*=\s*(-?\d+(?:[.,]\d+)?)", texto)
    if n is None:
        n = _extrair_primeiro_float(r"\b(\d+)\s*[ºo]\s*termo\b", texto)
    if a1 is not None and razao is not None and n is not None:
        return a1 + (n - 1) * razao

    # MELHORIA: bug visto em producao — quando a questao da dois termos
    # quaisquer da PA (ex: "o primeiro termo vale 7 e o quinto termo vale
    # 27") e pede um terceiro por extenso ("qual e o decimo segundo
    # termo"), nao ha nenhum "razao =" no texto (o aluno tem que deduzir a
    # razao a partir dos dois termos) e as posicoes vem por extenso, nao em
    # numeral — a extracao acima nao achava nada e a validacao ficava cega
    # pra esse formato, deixando passar silenciosamente uma alternativa
    # marcada como correta que nao batia com a conta. Aqui reconstroi a PA
    # a partir de dois termos quaisquer com valor conhecido, mais o termo
    # citado sem valor (o que a pergunta esta pedindo).
    texto_ascii = _texto_ascii_simples(texto)
    termos_citados = _termos_progressao_citados(texto_ascii)
    conhecidos = [(pos, valor) for pos, valor in termos_citados if valor is not None]
    alvos = [pos for pos, valor in termos_citados if valor is None]
    if len(conhecidos) >= 2 and alvos:
        (pos1, val1), (pos2, val2) = conhecidos[0], conhecidos[1]
        if pos1 == pos2:
            return None
        razao_derivada = (val2 - val1) / (pos2 - pos1)
        alvo = alvos[-1]
        return val1 + (alvo - pos1) * razao_derivada

    return None


def _valor_esperado_trigonometria_altura(dados: dict) -> float | None:
    texto = _texto_ascii_simples(_textos_questao_completos(dados)).replace(",", ".")
    # MELHORIA: "tan" e "angulo" eram procurados como PEDACO de palavra, e
    # "retangular"/"retangulo" contem os dois ("re-tan-gular", "ret-angulo").
    # "Uma sala retangular mede 6 m por 8 m" virava tangente com h = 8, e o
    # 48 m^2 certo era recusado -- as 20 areas de retangulo do banco. A mesma
    # armadilha de "dis-tan-cia" que _TERMOS_FUNCAO_TRANSCENDENTE ja corrigiu.
    if not re.search(r"\btan\b|\btangente\b", texto):
        return None
    if "altura" not in texto and not re.search(r"\bh\s*=", texto):
        return None

    distancia = None
    match_distancia = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:m|metro|metros)\b", texto)
    if match_distancia:
        distancia = _normalizar_numero_float(match_distancia.group(1))

    angulo = None
    match_angulo = re.search(r"\bangulo[^\d-]*(-?\d+(?:\.\d+)?)", texto)
    if match_angulo:
        angulo = _normalizar_numero_float(match_angulo.group(1))
    else:
        numeros = [_normalizar_numero_float(numero) for numero in _extrair_numeros_normalizados(texto)]
        candidatos = [valor for valor in numeros if valor is not None and 0 < valor < 90 and valor != distancia]
        if candidatos:
            angulo = candidatos[-1]

    if distancia in (None, 0) or angulo is None:
        return None
    return distancia * math.tan(math.radians(angulo))


def _valores_esperados_equacao_2o_grau(dados: dict) -> tuple[float, float] | None:
    """
    MELHORIA: nenhum dos dois detectores acima cobre equacao do 2o grau
    (Bhaskara), que e um dos tipos de questao mais comuns do Laboratorio.
    Bug visto em producao: a IA calculou certo nos passos (raizes 1 e -5/3
    para 3x^2+2x-5=0), mas a alternativa marcada como correta era outro
    par de numeros que nao correspondia a nenhuma raiz real, sem que nada
    detectasse a inconsistencia. Este detector extrai a, b, c (do texto
    explicito "a = .. b = .. c = .." nos passos, ou direto da equacao
    "axˆ2 + bx + c = 0") e recalcula as raizes de verdade para comparar
    com a alternativa marcada.
    """
    texto = _texto_ascii_simples(_textos_questao_completos(dados)).replace(",", ".")
    if "equacao" not in texto and "grau" not in texto and not re.search(r"x\s*\^?\s*2", texto):
        return None

    a = _extrair_primeiro_float(r"\ba\s*=\s*(-?\d+(?:\.\d+)?)", texto)
    b = _extrair_primeiro_float(r"\bb\s*=\s*(-?\d+(?:\.\d+)?)", texto)
    c = _extrair_primeiro_float(r"\bc\s*=\s*(-?\d+(?:\.\d+)?)", texto)

    if a is None or b is None or c is None:
        match_eq = re.search(
            r"(-?\d+(?:\.\d+)?)\s*x\s*\^?\s*2\s*([+-]\s*\d+(?:\.\d+)?)\s*x\s*([+-]\s*\d+(?:\.\d+)?)\s*=\s*0",
            texto,
        )
        if not match_eq:
            return None
        a = _normalizar_numero_float(match_eq.group(1))
        b = _normalizar_numero_float(match_eq.group(2).replace(" ", ""))
        c = _normalizar_numero_float(match_eq.group(3).replace(" ", ""))

    if a in (None, 0) or b is None or c is None:
        return None

    delta = b * b - 4 * a * c
    if delta < 0:
        return None
    raiz_delta = math.sqrt(delta)
    x1 = (-b + raiz_delta) / (2 * a)
    x2 = (-b - raiz_delta) / (2 * a)
    return (x1, x2)


def _opcao_contem_valor(opcao: str, esperado: float) -> bool:
    for numero in _extrair_numeros_normalizados(opcao):
        valor = _normalizar_numero_float(numero)
        if valor is not None and _valores_proximos(valor, esperado, tolerancia=max(0.001, abs(esperado) * 0.01)):
            return True
    return False


def _opcao_contem_par_valores(opcao: str, v1: float, v2: float) -> bool:
    return _opcao_contem_valor(opcao, v1) and _opcao_contem_valor(opcao, v2)


def _resposta_calculavel_nao_aparece_ou_esta_errada(dados: dict) -> bool:
    par_esperado = _valores_esperados_equacao_2o_grau(dados)
    if par_esperado is not None:
        opcoes = [str(opcao) for opcao in (dados.get("opcoes", []) or [])]
        if not any(_opcao_contem_par_valores(opcao, *par_esperado) for opcao in opcoes):
            return True
        try:
            correta_idx = int(dados.get("correta", 0))
        except Exception:
            correta_idx = 0
        if not (0 <= correta_idx < len(opcoes)) and 1 <= correta_idx <= len(opcoes):
            correta_idx -= 1
        opcao_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""
        return not _opcao_contem_par_valores(opcao_correta, *par_esperado)

    esperado = _valor_esperado_progressao_aritmetica(dados)
    if esperado is None:
        esperado = _valor_esperado_trigonometria_altura(dados)
    if esperado is None:
        return False

    opcoes = [str(opcao) for opcao in (dados.get("opcoes", []) or [])]
    if not any(_opcao_contem_valor(opcao, esperado) for opcao in opcoes):
        return True

    try:
        correta_idx = int(dados.get("correta", 0))
    except Exception:
        correta_idx = 0
    if not (0 <= correta_idx < len(opcoes)) and 1 <= correta_idx <= len(opcoes):
        correta_idx -= 1
    opcao_correta = opcoes[correta_idx] if 0 <= correta_idx < len(opcoes) else ""
    return not _opcao_contem_valor(opcao_correta, esperado)


def _resposta_exatas_sem_estrutura(dados: dict) -> bool:
    formula = str(dados.get("formula", "") or "").strip()
    subformulas = dados.get("subformulas", []) or []
    passos = dados.get("passos_resolucao", []) or []

    if formula:
        return False
    if isinstance(subformulas, list) and any(str(item).strip() for item in subformulas):
        return False
    if isinstance(passos, list) and any(
        str((item or {}).get("conteudo", "")).strip() if isinstance(item, dict) else str(item).strip()
        for item in passos
    ):
        return False
    return True


def _questao_fisica_quimica_conceitual(dados: dict) -> bool:
    pergunta = str(dados.get("pergunta", "") or "")
    opcoes = " ".join(str(opcao) for opcao in (dados.get("opcoes", []) or []))
    texto_completo = f"{pergunta} {opcoes}"
    return not bool(re.search(r"\d", texto_completo))


# Funcao aplicada a um numero ainda e um valor CALCULADO, nao uma incognita:
# "50 * tan(60)" e conta feita. O nome da funcao sai antes da varredura para
# nao quebrar o trecho ao meio -- sem isto, uma questao de trigonometria
# (tema que o proprio prompt do Laboratorio pede) seria recusada.
_FUNCAO_MATEMATICA = re.compile(
    r"\\?\b(?:sen|sin|cos|tan|tg|cotg|sec|cossec|log|ln|exp|sqrt|raiz|mod)\b"
)

# Um trecho que so tem numero, operador, ponto e parentese -- nenhuma letra.
# E onde a substituicao ja aconteceu: "15 - 5", "(6+8+10)/3", "200*15/100".
_TRECHO_SEM_INCOGNITA = re.compile(r"\d[\d\s.+\-*/()]*")
# Operador binario ENTRE dois numeros. Exige os dois lados para nao contar o
# sinal de um numero negativo ("-98") como se fosse uma conta. Os parenteses
# no meio sao para o \frac do LaTeX, que vira "(240)/(3)".
_CONTA_ENTRE_NUMEROS = re.compile(r"\d\s*\)*\s*[+\-*/]\s*\(*\s*-?\d")
# O ultimo numero do trecho, junto com o operador que o traz -- usado para
# descartar um coeficiente ("... + 2" de "+ 2x") sem perder a conta que
# venha antes dele no mesmo trecho ("15 - 5 + 2x" ainda tem "15 - 5").
_COEFICIENTE_NO_FIM = re.compile(r"[+\-*/]\s*\(*\s*\d+(?:\.\d+)?$")


def _resolucao_efetua_alguma_conta(trechos: list[str]) -> bool:
    """Existe, no passo a passo, uma linha em que a conta foi FEITA?

    MELHORIA: no lugar disto havia uma lista de doze palavras procuradas no
    enunciado ("r$", "%", "desconto", "juros", "area", "altura", "termo",
    "equacao"...). A questao era aceita ou recusada conforme o enunciado
    sortear uma delas:

        aceita   "Resolva a equacao 2x + 5 = 15."
        recusa   "Calcule o valor de x em 2x + 5 = 15."

    A mesma conta. E a lista rodava DEPOIS de quatro portas que ja tinham
    exigido formula com "=", dois numeros no enunciado, quatro nas
    alternativas e dois na resolucao -- julgava pela palavra o que as outras
    ja tinham julgado pelo conteudo. Medido: recusava 9 de 15 questoes boas.

    O que o Laboratorio quer garantir e outra coisa: que a conta apareca
    feita, e nao so anunciada. Entao e isso que se procura -- um trecho sem
    incognita nenhuma, com operador entre dois numeros. "15 - 5" conta;
    "2x + 5 = 15" nao, porque ainda tem x e e so o enunciado repetido.

    So remover a lista nao bastaria: passariam a valer resolucoes que apenas
    repetem o enunciado ou que so mostram o resultado (medido: 2 falsos
    negativos novos). Por isso a troca, e nao a remocao.
    """
    for trecho in trechos:
        expressao = _FUNCAO_MATEMATICA.sub("", _traduzir_operadores_latex(trecho))
        for achado in _TRECHO_SEM_INCOGNITA.finditer(expressao):
            candidato = achado.group()
            # Numero colado numa letra e COEFICIENTE, nao parcela: em
            # "3 + 2x = 15" o pedaco "3 + 2" parece uma soma, mas o 2 e do x
            # e nada foi calculado. Sem isto, o criterio dependeria da ordem
            # em que a IA escreve -- "2x + 5" era recusado e "5 + 2x" nao.
            depois = expressao[achado.end():achado.end() + 1]
            if depois.isalpha() and candidato[-1:].isdigit():
                candidato = _COEFICIENTE_NO_FIM.sub("", candidato)
            if _CONTA_ENTRE_NUMEROS.search(candidato):
                return True
    return False


# MELHORIA: as unidades eram procuradas como PEDACO DE TEXTO dentro das
# alternativas juntas, e a lista de Fisica tinha letras soltas -- "n", "j",
# "v", "a", "w". Resultado nas duas direcoes:
#
#   "12 bananas" era aceito como Fisica (tem a letra "a")
#   "80 km/h"    era recusado          (nao tem nenhuma daquelas letras)
#
# Ou seja: a checagem passava unidade inventada e barrava a unidade de
# velocidade mais usada no Ensino Medio. Em Quimica era pior: "l" na lista
# fazia qualquer alternativa com a letra L passar ("azul", "cristal").
#
# Agora a unidade e lida como TOKEN logo depois do numero e conferida
# contra uma lista fechada. Medido sobre 28 questoes boas e 11 ruins:
# 11 falsos positivos -> 0, e 5 falsos negativos -> 0.
# Grandezas de Quimica que sao adimensionais POR DEFINICAO: a resposta certa
# e um numero puro, e cobrar unidade dela seria cobrar o que nao existe. O
# prompt do Laboratorio pede pH como tema, entao isto nao e caso de canto.
_GRANDEZAS_ADIMENSIONAIS = ("ph", "poh", "pka", "pkb")


def _alternativas_carregam_unidade(
    opcoes: list[str], pergunta: str, unidades: frozenset[str]
) -> bool:
    if any(termo in _texto_ascii_simples(pergunta) for termo in _GRANDEZAS_ADIMENSIONAIS):
        return True

    for opcao in opcoes:
        # "3 \text{A}" e "mol·L⁻¹" tambem sao unidade: ver core/unidades.py.
        for bruta in UNIDADE_APOS_NUMERO.findall(simplificar_unidade_latex(str(opcao or ""))):
            if normalizar_unidade(bruta) in unidades:
                return True
    return False


# Alternativa que e so um numero: "25", "0,33", "-4", "1.5".
_SO_NUMERO = re.compile(r"[-−]?\d+(?:[.,]\d+)?")

# Um numero e a unidade logo depois dele: "s = 25 m", "R = 4 Ω", "0,01 mol".
# O token da unidade e o mesmo de core/unidades.UNIDADE_APOS_NUMERO.
_NUMERO_E_UNIDADE = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*([a-zà-ÿ°ωΩ%][a-zà-ÿ0-9¹²³°ωΩ/.·-]*)",
    re.IGNORECASE,
)

# A pergunta pede a unidade: "qual a resistencia, em ohms?", "(em mol)",
# "em g/L". O token depois do "em" so vale se for unidade de verdade -- "em
# um circuito" e "em 5 s" nao pedem nada.
_EM_UNIDADE = re.compile(r"\bem\s+([a-zà-ÿ°ωΩ%][a-zà-ÿ0-9¹²³°ωΩ/.·-]*)", re.IGNORECASE)

# Por extenso, como a pergunta costuma escrever. Chave sem acento.
_UNIDADE_POR_EXTENSO = {
    "ohm": "Ω", "ohms": "Ω", "watt": "W", "watts": "W", "volt": "V", "volts": "V",
    "ampere": "A", "amperes": "A", "metro": "m", "metros": "m", "segundo": "s", "segundos": "s",
    "minuto": "min", "minutos": "min", "hora": "h", "horas": "h",
    "joule": "J", "joules": "J", "newton": "N", "newtons": "N",
    "quilograma": "kg", "quilogramas": "kg", "grama": "g", "gramas": "g",
    "litro": "L", "litros": "L", "mililitro": "mL", "mililitros": "mL",
    "quilometro": "km", "quilometros": "km", "centimetro": "cm", "centimetros": "cm",
    "pascal": "Pa", "pascals": "Pa", "hertz": "Hz", "coulomb": "C", "coulombs": "C",
    "caloria": "cal", "calorias": "cal", "kelvin": "K",
}


def _como_numero(texto: str) -> float | None:
    try:
        return float(str(texto).replace("−", "-").replace(",", "."))
    except ValueError:
        return None


def _unidade_da_resposta_no_resultado(payload: dict, valor: float, unidades: frozenset[str]) -> str:
    """A unidade que o resultado poe depois do MESMO numero da alternativa certa.

    "s = 25 m" com a certa "25" -> "m". Procurar o numero da resposta, e nao
    pegar a ultima unidade do texto, evita "n = 0,01 mol em 40 mL" -> "mL".

    O resultado mora em dois lugares do JSON da IA: no bloco da explicacao do
    tipo "resultado" (ou "final") e no passo marcado como final. Nao ha
    campo "resultado" -- quem o escreve e o log (enigma.questao_para_log).
    """
    textos = [
        bloco.get("conteudo")
        for bloco in payload.get("explicacao") or []
        if isinstance(bloco, dict) and bloco.get("tipo") in ("resultado", "final")
    ]
    for passo in payload.get("passos_resolucao") or []:
        if isinstance(passo, dict) and passo.get("final"):
            textos.append(passo.get("conteudo"))
    for texto in textos:
        for numero, unidade in _NUMERO_E_UNIDADE.findall(simplificar_unidade_latex(str(texto or ""))):
            unidade = unidade.rstrip(".,;:")
            if _como_numero(numero) == valor and normalizar_unidade(unidade) in unidades:
                return unidade
    return ""


def _unidade_pedida_na_pergunta(pergunta: str, unidades: frozenset[str]) -> str:
    """"qual a resistencia, em ohms?" -> "Ω"; "(em mol)" -> "mol". A ultima vale."""
    for token in reversed(_EM_UNIDADE.findall(simplificar_unidade_latex(str(pergunta or "")))):
        token = token.rstrip(".,;:)")
        if normalizar_unidade(token) in unidades:
            return token
        simbolo = _UNIDADE_POR_EXTENSO.get(_texto_ascii_simples(token))
        if simbolo and normalizar_unidade(simbolo) in unidades:
            return simbolo
    return ""


def _completar_unidade_nas_alternativas(payload: dict, materia_norm: str) -> dict:
    """Alternativas so com numero ganham a unidade que a propria questao da.

    Visto em 15/09 e 30/09/2026: a IA mandava "20 / 25 / 30 / 35" com o
    resultado "s = 25 m", ou "2 / 3 / 4 / 6" com a pergunta "qual a
    resistencia, em ohms?" -- questoes CERTAS, recusadas como
    "laboratorio-sem-calculo" porque a alternativa nao carregava unidade. Foram
    6 de 6 recusas reais em 15/09 e 3 de 3 nas geracoes de 30/09.

    A unidade sai do resultado (depois do numero da resposta certa) e, sem
    ela, do "em ..." da pergunta. Sem unidade em nenhum dos dois, nada muda e
    a regra recusa como antes -- ai a questao e ambigua de verdade. So mexe
    quando TODAS as alternativas sao numero puro, e devolve a questao com a
    unidade escrita: e assim que ela chega a tela do aluno.
    """
    unidades = {"Fisica": UNIDADES_FISICA, "Quimica": UNIDADES_QUIMICA}.get(materia_norm)
    opcoes = payload.get("opcoes") or []
    if not unidades or len(opcoes) < 2 or not all(_SO_NUMERO.fullmatch(str(o).strip()) for o in opcoes):
        return payload
    try:
        valor = _como_numero(str(opcoes[int(payload.get("correta", -1))]).strip())
    except (TypeError, ValueError, IndexError):
        return payload
    unidade = ""
    if valor is not None:
        unidade = _unidade_da_resposta_no_resultado(payload, valor, unidades)
    unidade = unidade or _unidade_pedida_na_pergunta(payload.get("pergunta"), unidades)
    if not unidade:
        return payload
    separador = "" if unidade == "%" else " "
    return {**payload, "opcoes": [f"{str(o).strip()}{separador}{unidade}" for o in opcoes]}


def _questao_exatas_sem_calculo_laboratorio(dados: dict, materia_norm: str) -> bool:
    pergunta = str(dados.get("pergunta", "") or "")
    opcoes = [str(opcao) for opcao in (dados.get("opcoes", []) or [])]
    formula = str(dados.get("formula", "") or "").strip()
    subformulas = [str(item).strip() for item in (dados.get("subformulas", []) or []) if str(item).strip()]
    passos = dados.get("passos_resolucao", []) or []

    if not formula or "=" not in formula:
        return True

    textos_passos = []
    for passo in passos:
        if isinstance(passo, dict):
            conteudo = str(passo.get("conteudo", "")).strip()
        else:
            conteudo = str(passo or "").strip()
        if conteudo:
            textos_passos.append(conteudo)

    texto_substituicao = " ".join(subformulas + textos_passos)
    numeros_pergunta = _extrair_numeros_normalizados(pergunta)
    numeros_opcoes = _extrair_numeros_normalizados(" ".join(opcoes))
    numeros_substituicao = _extrair_numeros_normalizados(texto_substituicao)

    if len(numeros_pergunta) < 2:
        return True
    if len(numeros_opcoes) < 4:
        return True
    if len(numeros_substituicao) < 2:
        return True

    if materia_norm == "Matematica":
        return not _resolucao_efetua_alguma_conta(subformulas + textos_passos)

    if materia_norm == "Fisica":
        return not _alternativas_carregam_unidade(opcoes, pergunta, UNIDADES_FISICA)

    if materia_norm == "Quimica":
        return not _alternativas_carregam_unidade(opcoes, pergunta, UNIDADES_QUIMICA)

    return False


def _inferir_indice_correto_exatas(dados: dict) -> int | None:
    opcoes = [str(opcao) for opcao in (dados.get("opcoes", []) or [])]
    if not opcoes:
        return None

    textos_resultado = _coletar_textos_resultado_exatas(dados)
    if not textos_resultado:
        return None

    correspondencias: set[int] = set()
    opcoes_norm = [_texto_normalizado_simples(opcao) for opcao in opcoes]
    numeros_opcoes = [_extrair_numeros_normalizados(opcao) for opcao in opcoes]
    ultimos_numeros_opcoes = [_ultimo_numero_normalizado(opcao) for opcao in opcoes]

    valores_finais = [valor for valor in _coletar_valores_finais_exatas(dados) if valor]
    if valores_finais:
        valor_final_mais_comum = max(set(valores_finais), key=valores_finais.count)
        matches_valor_final = {
            idx for idx, ultimo_numero in enumerate(ultimos_numeros_opcoes) if ultimo_numero == valor_final_mais_comum
        }
        if len(matches_valor_final) == 1:
            return next(iter(matches_valor_final))

    for texto in textos_resultado:
        texto_norm = _texto_normalizado_simples(texto)
        numeros_texto = _extrair_numeros_normalizados(texto)

        for idx, opcao_norm in enumerate(opcoes_norm):
            if not opcao_norm:
                continue
            if texto_norm == opcao_norm or texto_norm.endswith(opcao_norm) or opcao_norm in texto_norm:
                correspondencias.add(idx)
                continue

            numeros_opcao = numeros_opcoes[idx]
            if numeros_texto and numeros_opcao and numeros_texto == numeros_opcao:
                correspondencias.add(idx)

    return next(iter(correspondencias)) if len(correspondencias) == 1 else None


def _texto_menciona_opcao(texto_norm: str, opcao_norm: str) -> bool:
    if not texto_norm or not opcao_norm:
        return False
    if len(opcao_norm) < 4:
        return False
    if opcao_norm in texto_norm:
        return True

    tokens_opcao = [token for token in re.findall(r"[a-z0-9]+", opcao_norm) if len(token) >= 4]
    if not tokens_opcao:
        return False
    if all(token in texto_norm for token in tokens_opcao):
        return True

    stopwords = {
        "para", "pela", "pelo", "quando", "antes", "durante", "todas", "todos",
        "completa", "direta", "melhor", "necessidade", "tendencia",
    }
    tokens_texto = set(re.findall(r"[a-z0-9]+", texto_norm))

    def _raiz_token(token: str) -> str:
        return token[:-1] if len(token) > 5 and token.endswith("s") else token

    opcoes_filtradas = [_raiz_token(token) for token in tokens_opcao if token not in stopwords]
    texto_filtrado = {_raiz_token(token) for token in tokens_texto if token not in stopwords}
    if len(opcoes_filtradas) < 3:
        return False
    sobreposicao = sum(1 for token in opcoes_filtradas if token in texto_filtrado)
    return sobreposicao >= 2 and sobreposicao / len(opcoes_filtradas) >= 0.3


def _explicacao_aponta_para_outra_alternativa(dados: dict) -> bool:
    """A explicacao nomeia OUTRA alternativa, e nao a que foi marcada?

    MELHORIA: no lugar disto havia "indice_inferido is None", ou seja: a
    questao era recusada sempre que a explicacao nao apontasse para UMA
    unica alternativa. Isso cobrava PROVA, quando o que a checagem existe
    para pegar e CONTRADICAO -- a IA marcar uma alternativa e explicar
    outra. Tres formas de escrever certo caiam nessa exigencia:

      1. a explicacao cita a marcada junto de outra palavra que tambem e
         alternativa. "modifica o verbo, entao e um adverbio de modo" casa
         com "Adverbio" E com "Verbo" -- as duas legitimamente;
      2. as alternativas se distinguem por palavras curtas, entao todas
         casam pelo trecho longo em comum. "Vou a escola" / "Vou as
         escola" / "Vou a as escola" compartilham "escola";
      3. a explicacao parafraseia em vez de repetir ao pe da letra: opcao
         "Amazonia", explicacao "a floresta amazonica...". Nenhuma casa, e
         a ausencia de casamento virava motivo de recusa.

    Medido sobre 10 questoes bem formadas de humanas e linguagens: 3 eram
    recusadas. Nenhuma delas contradizia a alternativa marcada.

    A regra agora e estreita e verificavel: so recusa quando alguma
    alternativa e nomeada pela explicacao E a marcada nao esta entre elas.
    """
    opcoes = [str(opcao) for opcao in (dados.get("opcoes", []) or [])]
    if len(opcoes) < 2:
        return False

    textos = _coletar_textos_referencia_resposta(dados)
    if not textos:
        return False

    try:
        marcada = int(dados.get("correta", 0))
    except Exception:
        return False
    if not 0 <= marcada < len(opcoes):
        return False

    opcoes_norm = [_texto_normalizado_simples(opcao) for opcao in opcoes]
    citadas = {
        idx
        for texto in textos
        for idx, opcao_norm in enumerate(opcoes_norm)
        if _texto_menciona_opcao(_texto_normalizado_simples(texto), opcao_norm)
    }

    # nenhuma citada: sem evidencia, e ausencia de evidencia nao e
    # evidencia de erro. marcada entre as citadas: nao ha contradicao.
    return bool(citadas) and marcada not in citadas


def _inferir_indice_correto_geral(dados: dict) -> int | None:
    opcoes = [str(opcao) for opcao in (dados.get("opcoes", []) or [])]
    if not opcoes:
        return None

    textos_referencia = _coletar_textos_referencia_resposta(dados)
    if not textos_referencia:
        return None

    correspondencias: set[int] = set()
    opcoes_norm = [_texto_normalizado_simples(opcao) for opcao in opcoes]

    for texto in textos_referencia:
        texto_norm = _texto_normalizado_simples(texto)
        for idx, opcao_norm in enumerate(opcoes_norm):
            if _texto_menciona_opcao(texto_norm, opcao_norm):
                correspondencias.add(idx)

    return next(iter(correspondencias)) if len(correspondencias) == 1 else None


def _ajustar_indice_correto(dados: dict, materia_norm: str) -> tuple[dict, bool, int | None]:
    payload = dict(dados or {})
    opcoes = payload.get("opcoes", [])
    total_opcoes = len(opcoes) if isinstance(opcoes, list) else 0
    houve_inconsistencia = False

    try:
        correta = int(payload.get("correta", 0))
    except Exception:
        correta = 0

    if total_opcoes:
        if 0 <= correta < total_opcoes:
            pass
        elif 1 <= correta <= total_opcoes:
            correta -= 1
        else:
            correta = 0

    if materia_norm in {"Matematica", "Fisica", "Quimica"}:
        # MELHORIA: bug visto ao vivo em producao -- quando a heuristica de
        # _inferir_indice_correto_exatas nao consegue determinar um indice
        # (None), o codigo tratava isso como "achou uma inconsistencia" e
        # rejeitava a questao mesmo sem nenhuma evidencia de erro. Isso
        # acontece sempre que a questao e conceitual/definicional (sem
        # numero pra casar) ou a explicacao apenas parafraseia a opcao em
        # vez de repeti-la ao pe da letra -- exatamente o caso mais comum
        # de questao teorica de exatas. Reproduzido ao vivo: a mesma
        # pergunta de juros simples, com a IA acertando e a explicacao
        # batendo com a opcao marcada, foi rejeitada duas vezes seguidas so
        # porque a heuristica numerica nao tinha nada pra comparar. As
        # outras 5 checagens de consistencia numerica (resultado-exatas-
        # -conflitante, resultado-aritmetico-invalido, resposta-calculavel-
        # -nao-aparece-ou-esta-errada, passo-final-diverge-do-calculo-
        # -anterior, resposta-marcada-diverge-do-resultado-final) ja rodam
        # ANTES desta e cobrem o caso de "conta bate errado" -- esta
        # inferencia so deve reforcar quando ACHA um indice divergente
        # (sinal de que a explicacao aponta pra outra opcao), nunca quando
        # simplesmente nao consegue confirmar nada, igual ao branch "geral"
        # logo abaixo.
        indice_inferido = _inferir_indice_correto_exatas(payload)
        if indice_inferido is not None:
            if total_opcoes and correta != indice_inferido:
                houve_inconsistencia = True
            correta = indice_inferido
    else:
        indice_inferido = _inferir_indice_correto_geral(payload)
        if indice_inferido is not None and total_opcoes and correta != indice_inferido:
            houve_inconsistencia = True
            correta = indice_inferido

    payload["correta"] = correta
    return payload, houve_inconsistencia, indice_inferido


_ROTULO_DE_ALTERNATIVA = re.compile(r"^(?:alternativa\s+)?([a-e])\s*[\).:\-]?$", re.IGNORECASE)


def _opcoes_sao_apenas_rotulos(opcoes: list[str]) -> bool:
    """A IA devolveu os ROTULOS no lugar do conteudo das alternativas.

    MELHORIA: visto em producao no RPG -- "Qual solido geometrico possui
    todas as faces quadradas congruentes, todas as arestas de mesmo
    comprimento e exatamente seis faces?" chegou ao aluno com as quatro
    opcoes sendo "A", "B", "C" e "D". A questao e a explicacao estavam
    certas; so as alternativas perderam o texto, e nao havia como responder
    a nao ser chutando.

    Exige a sequencia completa a partir de "a", em vez de barrar qualquer
    letra solta: letra sozinha e resposta legitima em quimica ("C", "O",
    "N", "H") e em biologia ("A", "T", "C", "G") -- e nenhum desses
    conjuntos e {a, b, c, d}.
    """
    letras = []
    for opcao in opcoes:
        achado = _ROTULO_DE_ALTERNATIVA.match(str(opcao).strip())
        if not achado:
            return False
        letras.append(achado.group(1).lower())
    esperado = [chr(ord("a") + indice) for indice in range(len(letras))]
    return sorted(letras) == esperado


def _validar_estrutura_basica_questao(dados: dict) -> tuple[bool, str]:
    if not isinstance(dados, dict):
        return False, "payload-nao-e-dicionario"
    if not str(dados.get("pergunta", "") or "").strip():
        return False, "pergunta-vazia"
    opcoes = dados.get("opcoes", [])
    if not isinstance(opcoes, list):
        return False, "opcoes-nao-sao-lista"
    opcoes_validas = [str(opcao).strip() for opcao in opcoes if str(opcao).strip()]
    if len(opcoes_validas) != 4:
        return False, "quantidade-de-opcoes-invalida"
    if len(set(_texto_normalizado_simples(opcao) for opcao in opcoes_validas)) != 4:
        return False, "opcoes-repetidas"
    if _opcoes_sao_apenas_rotulos(opcoes_validas):
        return False, "opcoes-sao-apenas-rotulos"
    if tem_opcoes_equivalentes(opcoes_validas, str(dados.get("pergunta", "") or "")):
        return False, "opcoes-equivalentes"
    try:
        correta = int(dados.get("correta", 0))
    except Exception:
        return False, "indice-correto-invalido"
    if not (0 <= correta < len(opcoes_validas) or 1 <= correta <= len(opcoes_validas)):
        return False, "indice-correto-fora-do-intervalo"
    return True, ""


# Frase que cita suporte externo -- nao a palavra sozinha. "Figura de
# linguagem" (Portugues) e "com base na tabela periodica"/"segundo a tabela
# de conversao" (referencia universal, nao um suporte desta questao) NAO
# podem cair aqui -- medido: uma primeira versao com "com base"/"segundo"
# como gatilho pegava exatamente esses dois casos.
#
# Exige a palavra JUNTO do adverbio que aponta pra algo que deveria estar
# visivel NA TELA ("abaixo", "a seguir", "acima") -- e so isso: e o padrao
# dos dois casos reais do relatorio (achado 3.2) e nao tem ambiguidade com
# referencia a conhecimento comum.
_PALAVRA_DE_SUPORTE = r"(?:texto|trecho|tabela|gr[aá]fico|quadro|figura|imagem)"
_REFERENCIA_A_SUPORTE = re.compile(
    r"(?i:\b" + _PALAVRA_DE_SUPORTE + r"\b\s*(?:acima|abaixo|a seguir))"
    r"|(?i:\bthe passage\b)"
    r"|(?i:\bin the (?:text|chart|graph|table|image|figure)\s+below\b)"
)


def _pergunta_cita_suporte_ausente(dados: dict) -> bool:
    """A pergunta promete um texto/tabela que o campo "suporte" nao entrega.

    MELHORIA: relatorio de QA de 23/09/2026 (achado 3.2) -- Escape Room de
    Ingles perguntava "In the passage, what is..." sem nenhum passage
    exibido, e o de Matematica citava "a tabela abaixo" que tambem nunca
    aparecia. As duas questoes eram logicamente impossiveis de responder.
    services/ia/enigma.py (_prompts_oraculo) agora pede o campo suporte
    quando a pergunta citar algo assim; esta funcao e a rede de seguranca
    para quando o prompt nao for suficiente.
    """
    pergunta = str(dados.get("pergunta", "") or "")
    if not _REFERENCIA_A_SUPORTE.search(pergunta):
        return False

    suporte = dados.get("suporte")
    if not isinstance(suporte, dict):
        return True
    tipo = str(suporte.get("tipo") or "").strip().lower()
    if tipo == "texto":
        return not str(suporte.get("texto") or "").strip()
    if tipo == "tabela":
        tabela = suporte.get("tabela") if isinstance(suporte.get("tabela"), dict) else {}
        return not (tabela.get("colunas") and tabela.get("linhas"))
    return True


# "R = raio do circulo (cm)" declara R. A ancora e o inicio da legenda ou o
# ";" que separa as declaracoes -- sem ela, o "(cm)" e qualquer "=" solto no
# meio de uma descricao virariam declaracao.
_DECLARACAO_NA_LEGENDA = re.compile(
    # A barra e opcional porque a legenda tanto escreve "Δ = discriminante"
    # quanto "\Delta = discriminante". Sem aceita-la, a segunda forma nao era
    # sequer reconhecida como declaracao e escapava da checagem inteira.
    r"(?:^|;)\s*(\\?[A-Za-zΑ-Ωα-ω][A-Za-z0-9_]{0,5})\s*=",
    re.UNICODE,
)


def _variaveis_orfas_da_legenda(dados: dict) -> list[str]:
    """Variaveis que a legenda declara e nenhuma formula usa.

    O defeito que isto pega, visto na tela: "Um triangulo equilatero tem lado
    12 cm, calcule a area do circulo circunscrito", com

        formula:  A = \\pi R^2
        legenda:  a = lado do triangulo (cm); R = raio do circulo
                  circunscrito (cm); pi = 3.14; A = area do circulo

    Nenhuma formula liga "a" a "R". O aluno tem o lado, precisa do raio, e nao
    recebeu como sair de um para o outro -- a questao nao fecha. Faltava a
    subformula R = a\\sqrt{3}/3.

    A comparacao e SENSIVEL A MAIUSCULA de proposito, e o exemplo acima mostra
    por que: a legenda declara "a" (lado) e "A" (area), e "A" esta na formula.
    Ignorando a caixa, o "a" orfao seria dado como presente e o defeito
    passaria batido.

    Medido: 0 de 5.280 questoes do banco offline com legenda e formula
    disparam esta regra. Mesmo perfil das validacoes ja ligadas -- com a
    ressalva que o proprio banco ja carrega: sao muitas questoes em poucas
    formas distintas.
    """
    legenda = str(dados.get("legenda_variaveis", "") or "")
    if not legenda.strip():
        return []

    formulas = [str(dados.get("formula", "") or "")]
    formulas += [str(sub or "") for sub in (dados.get("subformulas", []) or [])]
    texto_formulas = " ".join(formulas)
    if not texto_formulas.strip():
        # Sem formula nenhuma nao ha o que cruzar. Questao sem formula ja e
        # assunto de _resposta_exatas_sem_estrutura; nao e este o julgamento.
        return []

    presentes = _nomes_usados_nas_formulas(texto_formulas)
    orfas = []
    for nome in _DECLARACAO_NA_LEGENDA.findall(legenda):
        # A legenda pode escrever "π" onde a formula escreve "\pi".
        chave = converter_simbolos_latex(nome).strip() or nome
        if chave not in presentes:
            orfas.append(nome)
    return orfas


# Nomes de funcao NAO sao variaveis. Sem tirar "sen" antes de quebrar em
# letras, um "sen(x)" na formula passaria a "provar" que existem variaveis
# chamadas s, e e n -- e a regra deixaria de pegar qualquer coisa.
_FUNCOES_NA_FORMULA = re.compile(
    r"\b(?:sen|sin|cos|tan|tg|cotg|sec|cossec|log|ln|exp|max|min|mmc|mdc|abs|det|lim|mod|raiz)\b",
    re.IGNORECASE,
)


def _nomes_usados_nas_formulas(texto: str) -> set[str]:
    """Os nomes de variavel que aparecem nas formulas.

    Nao da para usar fronteira de palavra aqui: em matematica as variaveis
    vem COLADAS. Em "x = (-b \\pm \\sqrt{\\Delta})/(2a)" o "a" gruda no 2, e em
    "\\Delta = b^2 - 4ac" o "a" e o "c" grudam no 4 e um no outro. Com
    "(?<![A-Za-z0-9_])" os tres eram dados como ausentes, e a regra recusava
    uma Bhaskara perfeitamente correta -- exatamente o tipo de falso positivo
    que ja tirou do ar a `exatas-sem-estrutura`.

    Tambem nao da para procurar a letra crua no texto: "\\Delta" contem um "a",
    e "\\sqrt" contem um "r". Por isso os comandos LaTeX viram simbolo ANTES
    (\\pi -> pi, \\Delta -> Delta, \\sqrt -> sqrt) e os nomes de funcao saem
    da conta; o que sobra e variavel de verdade.
    """
    convertido = converter_simbolos_latex(texto)
    # O que o conversor nao conhece continua com barra ("\frac", "\mathrm"):
    # some com o comando inteiro, senao as letras dele viram variaveis.
    convertido = re.sub(r"\\[A-Za-z]+", " ", convertido)
    convertido = _FUNCOES_NA_FORMULA.sub(" ", convertido)

    nomes: set[str] = set()
    # Primeiro os nomes com subscrito, que sao uma unidade so ("v_0", "E_c").
    for composto in re.findall(r"[A-Za-zΑ-Ωα-ω]_\{?[A-Za-z0-9]+\}?", convertido):
        nomes.add(composto)
        nomes.add(composto.split("_", 1)[0])
    # Depois cada letra solta: em "4ac" as variaveis sao "a" e "c".
    for letra in re.findall(r"[A-Za-zΑ-Ωα-ωΔδπθ]", convertido):
        nomes.add(letra)
    return nomes


# "a = 2", "b = -7", "Δ = 25". O valor tem de ser NUMERO puro: "Δ = b^2-4ac"
# nao da numero ao Δ, so o define em funcao de outras letras.
_ATRIBUICAO_NUMERICA = re.compile(
    r"(?:^|[,;])\s*([A-Za-zΑ-Ωα-ωΔ][A-Za-z0-9_]{0,3})\s*=\s*[-+]?\s*\d+(?:[.,]\d+)?\s*(?=$|[,;])"
)

def _variaveis_do_passo(texto: str) -> set[str]:
    """As letras que aparecem como VARIAVEL num passo.

    Duas armadilhas, as duas descobertas medindo contra resolucao real:

    1. **Prosa dentro do passo.** "substituir na formula de Bhaskara: (-8 ±
       sqrt(144))/(2·(-2))" entregava as letras de cada palavra -- b, a e c
       inclusive --, e a regra acusava um passo que tinha substituido
       certinho. Variavel e letra SOZINHA; corrida de 2+ letras e palavra.
    2. **Subscrito.** "P_f" virava {P, f}; como "P = 150" existia num passo
       anterior, a regra concluia que P nao fora substituido. "P_f" e outra
       variavel, nao o "P" com um enfeite.
    """
    limpo = re.sub(r"\\[A-Za-z]+", " ", str(texto or ""))

    nomes = set(re.findall(r"[A-Za-zΑ-Ωα-ωΔ]_\{?[A-Za-z0-9]+\}?", limpo))
    for nome in nomes:
        limpo = limpo.replace(nome, " ")

    # Tira toda corrida de 2+ letras. Isso cobre a prosa E os nomes de funcao
    # ("sen", "log", "tg"): havia aqui uma segunda regra so para eles, e a
    # mutacao mostrou que era codigo morto -- nenhum nome de funcao tem uma
    # letra so, entao esta linha ja os alcancava.
    limpo = re.sub(r"[A-Za-zÀ-ÿ]{2,}", " ", limpo)
    return nomes | set(re.findall(r"[A-Za-zΑ-Ωα-ωΔ]", limpo))


def _resolucao_nao_substitui_os_valores(dados: dict) -> bool:
    """O ultimo passo antes do resultado ainda usa letra que ja tinha numero.

    O defeito, visto na tela do Laboratorio:

        1º Passo:  a = 2, b = -7, c = 3       <- a, b, c ganham numero
        2º Passo:  Δ = (-7)^2 - 4 · 2 · 3     <- substituiu, certo
        3º Passo:  x = (-b ± √Δ)/(2a)         <- voltou para as LETRAS
        Resultado: x = 3, x = 0,5             <- de onde vieram?

    O aluno recebe a formula e o resultado, e nada entre os dois.

    Por que so o ULTIMO passo antes do resultado: escrever a formula com
    letras e legitimo como enunciado de etapa ("Δ = b² - 4ac") DESDE QUE um
    passo seguinte substitua. No ultimo nao ha mais essa chance.

    Medido: 0 de 2.114 resolucoes distintas do banco offline, e 1 de 8
    resolucoes REAIS da IA -- justamente a da tela. As outras duas Bhaskaras
    reais, resolvidas certo, passam. A amostra real e pequena (8), mas ela
    contem o caso dificil: separar a Bhaskara errada das certas.

    E fica o aviso que esta medicao deixou: no banco offline os tres desenhos
    anteriores (A, B, C) e este davam 0%, e contra dado real a primeira versao
    DESTE deu 25% de falso positivo. O banco autoral nao mostra as formas que
    a IA inventa. O script da medicao, scripts/medir_resolucao_simbolica.py,
    saiu do repositorio em 08/10/2026 e continua no historico do git.
    """
    passos = dados.get("passos_resolucao") or []
    conteudos = [
        str(p.get("conteudo", "") or "").strip()
        for p in passos
        if isinstance(p, dict) and str(p.get("conteudo", "") or "").strip()
    ]
    # So para nao indexar [-2] numa lista de um item. O resto do trabalho e da
    # intersecao la embaixo: numa resolucao de dois passos, "os passos ANTES
    # do penultimo" e uma lista vazia, entao nao ha variavel com numero e a
    # regra nao dispara sozinha. Havia aqui um "< 3" e um early-return por
    # com_numero vazio; a mutacao mostrou que os dois eram decorativos.
    if len(conteudos) < 2:
        return False

    com_numero: set[str] = set()
    for c in conteudos[:-2]:
        com_numero.update(_ATRIBUICAO_NUMERICA.findall(c))

    return bool(com_numero & _variaveis_do_passo(conteudos[-2]))


# --------------------------------------------------------------------------
# OBSERVACOES: defeito que ja se sabe ver e que ainda NAO recusa questao.
# --------------------------------------------------------------------------
#
# Uma regra nova nasce aqui, so registrando no log, e passa para
# validar_questao_gerada quando a medicao contra o que a IA escreve de verdade
# mostrar que ela nao recusa questao boa. Cada recusa e uma questao da IA a
# menos e uma do banco offline a mais; um registro nao custa nada ao aluno.

_NUMERO_ESCRITO = re.compile(r"\d+(?:[.,]\d+)*")


def _numeros_com_casas(texto) -> list[tuple[float, int]]:
    """Cada numero do texto, em modulo, e com quantas casas decimais veio.

    Em modulo porque o sinal chega de muitos jeitos ("-93", "−93", "- 93") e
    aqui so importa se o numero aparece. As casas dizem quanto arredondamento
    aceitar: "21,0" casa com "21,006", e "21" casa com "20,6".
    """
    saida: list[tuple[float, int]] = []
    for bruto in _NUMERO_ESCRITO.findall(str(texto or "")):
        if "," in bruto and "." in bruto:                      # 1.200,50
            normal = bruto.replace(".", "").replace(",", ".")
        elif bruto.count(".") > 1 or bruto.count(",") > 1:     # 1.200.000
            normal = bruto.replace(".", "").replace(",", "")
        else:                                                  # 229,5 / 229.5
            normal = bruto.replace(",", ".")
        try:
            valor = float(normal)
        except ValueError:
            continue
        saida.append((valor, len(normal.partition(".")[2])))
    return saida


def _resposta_final_fora_dos_passos(dados: dict) -> bool:
    """Nenhum numero da alternativa correta aparece em passo nenhum.

    O defeito, visto no Laboratorio em 11/09/2026 -- desconto de 15% e imposto
    de 8% sobre R$ 250,00, alternativa correta 229,5:

        1º Passo:  P_0 = 250, d = 0,15, t = 0,08
        2º Passo:  P_d = 250 × 0,85 = 212,5
                   <- e acabou: o imposto nunca foi aplicado

    A resolucao para no meio e o aluno nao ve de onde saiu o 229,5. Nenhuma
    regra pegava: havia numero no ultimo passo, e a conta que havia estava
    certa.

    So o CONTEUDO dos passos conta: o titulo "3º Passo" poria um 3 falso na
    comparacao. Porcentagem casa tambem com a fracao ("15%" com "0,15").

    Medido: 2 de 13 resolucoes reais da IA, e 0 falso positivo nas 16 do banco
    que estavam nos mesmos logs. Pouco para recusar -- por isso nasce como
    observacao.
    """
    nos_passos = [
        valor
        for passo in dados.get("passos_resolucao", []) or []
        if isinstance(passo, dict)
        for valor, _ in _numeros_com_casas(passo.get("conteudo", ""))
    ]
    if not nos_passos:
        return False

    opcoes = dados.get("opcoes", []) or []
    try:
        correta_idx = int(dados.get("correta", -1))
    except (TypeError, ValueError):
        return False
    if not (0 <= correta_idx < len(opcoes)):
        return False
    resposta = str(opcoes[correta_idx])
    na_resposta = _numeros_com_casas(resposta)
    if not na_resposta:
        return False

    for valor, casas in na_resposta:
        tolerancia = 0.5 * 10 ** -casas + 1e-9
        alvos = [(valor, tolerancia)]
        if "%" in resposta:
            alvos.append((valor / 100, tolerancia / 100))
        if any(abs(p - alvo) <= tol for alvo, tol in alvos for p in nos_passos):
            return False
    return True


def observar_questao_gerada(dados: dict, contexto: str = "rpg") -> list[str]:
    """Os defeitos que a questao TEM e que a validacao ainda nao recusa.

    Chamada depois de validar_questao_gerada aceitar. Quem chama registra no
    log e segue com a questao.

    Hoje nenhuma regra esta em observacao: resposta-final-fora-dos-passos
    passou a recusar em 02/10/2026 (ver validar_questao_gerada). O caminho
    continua para a proxima regra nascer do mesmo jeito -- registrando
    antes de recusar.
    """
    return []


def validar_questao_gerada(dados: dict, materia_norm: str, contexto: str = "rpg") -> tuple[dict, bool, str]:
    payload = dict(dados or {})
    ok, motivo = _validar_estrutura_basica_questao(payload)
    if not ok:
        return payload, False, motivo

    if _pergunta_cita_suporte_ausente(payload):
        return payload, False, "suporte-ausente"

    if not explicacao_tem_corpo(payload.get("explicacao")):
        return payload, False, "explicacao-sem-corpo"

    if pergunta_embute_opcoes_com_letra(payload.get("pergunta")):
        return payload, False, "opcoes-embutidas-no-enunciado"

    if pergunta_entrega_a_resposta(payload.get("pergunta"), payload.get("opcoes"), payload.get("correta")):
        return payload, False, "resposta-no-enunciado"

    eh_exatas = materia_norm in {"Matematica", "Fisica", "Quimica"}
    contexto_norm = str(contexto or "").strip().lower()

    if eh_exatas and _resultado_exatas_conflitante(payload):
        return payload, False, "resultado-exatas-conflitante"
    if eh_exatas and _resultado_aritmetico_incorreto(payload):
        return payload, False, "resultado-aritmetico-invalido"
    if contexto_norm == "laboratorio" and materia_norm == "Quimica" and _questao_quimica_molar_inconsistente(payload):
        return payload, False, "concentracao-molar-invalida"
    # MELHORIA: esta checagem valia so no Laboratorio. A guarda existia porque
    # ela recusava 228 das 14.310 questoes offline de exatas (1,6%) -- e as
    # 228 eram falso positivo do verificador, nao defeito das questoes: ele
    # lia o expoente da unidade ("A = 48 m^2" -> 2), o denominador da fracao
    # ("P = 3/10" -> 10), o par ordenado ("Vertice = (3, 4)" -> 4) e tratava
    # "log_2(4) = 2" como aritmetica comum. Corrigidos os quatro, a medicao
    # foi a ZERO e a guarda deixou de ter motivo.
    #
    # O que ela pega e grave e valia para os cinco modos desde sempre: com a
    # guarda, "d = 12 * 5" seguido de "d = 50" era ACEITO no Treino, no
    # Oraculo, no Escape Room e no RPG, e recusado so no Laboratorio.
    if eh_exatas and _passo_final_diverge_do_calculo_anterior(payload):
        return payload, False, "passo-final-diverge-do-calculo-anterior"
    if eh_exatas and contexto_norm != "oraculo" and _resposta_exatas_sem_estrutura(payload):
        return payload, False, "exatas-sem-estrutura"
    if materia_norm == "Matematica" and _formula_matematica_incoerente(payload):
        return payload, False, "formula-matematica-incoerente"
    if eh_exatas and _resposta_calculavel_nao_aparece_ou_esta_errada(payload):
        return payload, False, "alternativa-correta-calculavel-invalida"
    if eh_exatas and _resposta_marcada_diverge_do_resultado_final(payload):
        return payload, False, "alternativa-correta-diverge-do-resultado-final"
    if eh_exatas and _raiz_aproximada_incorreta(payload):
        return payload, False, "raiz-aproximada-incorreta"
    if eh_exatas and _funcao_aproximada_incorreta(payload):
        return payload, False, "funcao-aproximada-incorreta"
    if contexto_norm != "oraculo" and materia_norm in {"Fisica", "Quimica"} and _questao_fisica_quimica_conceitual(payload):
        return payload, False, "fisica-quimica-conceitual"

    payload, houve_inconsistencia, indice_inferido = _ajustar_indice_correto(payload, materia_norm)
    if eh_exatas and contexto_norm == "oraculo" and indice_inferido is None:
        indice_teorico = _inferir_indice_correto_geral(payload)
        if indice_teorico is not None:
            houve_inconsistencia = int(payload.get("correta", 0)) != indice_teorico
            indice_inferido = indice_teorico
    if houve_inconsistencia:
        return payload, False, "alternativa-correta-inconsistente"
    if not eh_exatas and _explicacao_aponta_para_outra_alternativa(payload):
        return payload, False, "alternativa-correta-nao-comprovada"

    if contexto_norm == "laboratorio":
        payload = _completar_unidade_nas_alternativas(payload, materia_norm)
        questao_normalizada = normalizar_payload_questao(payload)
        if _questao_exatas_sem_calculo_laboratorio(questao_normalizada, materia_norm):
            return payload, False, "laboratorio-sem-calculo"
        # Nasceu so registrando em 93431e9 (13/09/2026). Recusa desde
        # 02/10/2026, com o "sim" do usuario: os casos reais registrados eram
        # todos resolucao incompleta, e nenhum do banco era marcado.
        if _resposta_final_fora_dos_passos(questao_normalizada):
            return payload, False, "resposta-final-fora-dos-passos"
        # So no Laboratorio: e o unico modo que preserva formula e legenda.
        # _normalizar_questao_oraculo apaga as duas de proposito nos outros,
        # entao la a regra nao teria o que cruzar e recusaria tudo.
        if eh_exatas and _variaveis_orfas_da_legenda(payload):
            return payload, False, "legenda-com-variavel-sem-formula"
        # Mesma razao de escopo: os passos so sobrevivem aqui.
        if eh_exatas and _resolucao_nao_substitui_os_valores(payload):
            return payload, False, "resolucao-nao-substitui-os-valores"

    return payload, True, ""