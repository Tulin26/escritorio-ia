from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from copy import deepcopy
from typing import Any

from core.config import normalizar_materia
from services.banks._base import LazyMateriaBank, bncc_da_materia as _bncc_da_materia


QUESTOES_LAB_POR_TEMA = 20
QUESTOES_LAB_POR_MATERIA = 440
MATERIAS_LAB_OFFLINE = ("Matematica", "Fisica", "Quimica")
MATERIAS_LAB_EF_OFFLINE = ("Matematica", "Ciencias")
_CICLO_OFFLINE: dict[str, int] = {}


ALIASES_TEMAS_LAB = {
    "Matematica": {
        "equacao do 2o grau": ("equacao do 2o grau", "equacoes do 2o grau", "bhaskara", "parabola"),
        "sistemas lineares": ("sistema de equacoes", "sistemas de equacoes", "sistemas lineares", "equacoes lineares"),
        "funcao do 1o grau": ("funcao do 1o grau", "funcoes do 1o grau", "funcao linear"),
        "funcao do 2o grau": ("funcao do 2o grau", "funcoes do 2o grau", "parabola"),
        "funcao exponencial": ("funcao exponencial", "exponencial"),
        "funcao logaritmica": ("funcao logaritmica", "logaritmos", "logaritmica"),
        "progressao aritmetica": ("progressao aritmetica", "pa"),
        "progressao geometrica": ("progressao geometrica", "pg"),
        "trigonometria": ("trigonometria", "seno", "cosseno", "tangente"),
        "geometria analitica": ("geometria analitica", "distancia entre pontos", "plano cartesiano"),
        "matrizes e determinantes": ("matrizes", "determinantes", "matriz", "determinante"),
        "combinatoria": ("combinatoria", "analise combinatoria", "arranjo", "combinacao"),
        "probabilidade condicional": ("probabilidade condicional",),
        "estatistica": ("estatistica", "media", "mediana"),
        "taxas e indices": ("taxas", "indices", "socioeconomicos", "variacao percentual"),
        "porcentagem": ("porcentagem", "matematica financeira", "desconto", "juros", "escala"),
        "geometria espacial": ("geometria espacial", "volume", "areas e volumes"),
        "area do retangulo": ("geometria plana", "areas de figuras planas", "area"),
        "area do triangulo": ("geometria plana", "triangulo"),
        "proporcao": ("grandezas diretamente", "inversamente proporcionais", "razao", "proporcao"),
    },
    "Fisica": {
        "velocidade media": ("cinematica", "mru", "mruv", "velocidade", "movimento"),
        "movimento uniformemente variado": ("mruv", "aceleracao", "lancamento de projeteis"),
        "segunda lei de Newton": ("leis de newton", "forca", "dinamica"),
        "trabalho mecanico": ("trabalho", "energia", "potencia"),
        "potencia mecanica": ("potencia", "eficiencia de motores"),
        "lei de Ohm": ("lei de ohm", "circuitos eletricos", "corrente eletrica"),
        "potencia eletrica": ("potencia eletrica", "equipamentos eletricos", "eletronicos"),
        "calorimetria": ("calorimetria", "termologia", "termodinamica"),
        "energia cinetica": ("energia cinetica", "quantidade de movimento"),
        "pressao": ("pressao", "hidrostatica", "empuxo"),
    },
    "Quimica": {
        "concentracao comum": ("solucoes", "unidades de concentracao", "concentracao"),
        "mol e massa molar": ("mol", "massa molar", "atomistica"),
        "massa a partir de mol": ("estequiometria", "massa a partir de mol"),
        "pH": ("ph", "acido-base", "acidos e bases", "funcoes inorganicas"),
        "diluicao": ("diluicao", "solucoes"),
        "termoquimica": ("termoquimica", "calor"),
        "estequiometria": ("estequiometria", "reacoes quimicas"),
        "densidade": ("estrutura e propriedades", "propriedades dos materiais", "densidade"),
        "porcentagem em massa": ("porcentagem em massa", "concentracao"),
        "gases ideais": ("gases ideais", "gases"),
    },
}


def _fmt(valor: float | int) -> str:
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, float):
        return str(round(valor, 2)).replace(".", ",")
    return str(valor)


def _normalizar_busca(texto: str) -> str:
    base = str(texto or "").replace("º", "o").replace("°", "o")
    base = unicodedata.normalize("NFKD", base)
    base = base.encode("ascii", "ignore").decode("ascii").lower()
    for antigo, novo in (
        ("2 grau", "2o grau"),
        ("1 grau", "1o grau"),
        ("funcoes", "funcao"),
        ("equacoes", "equacao"),
        ("progressoes", "progressao"),
    ):
        base = base.replace(antigo, novo)
    return " ".join(base.replace("-", " ").replace(":", " ").replace("(", " ").replace(")", " ").split())


# Contencao so vale quando o lado curto tem corpo. Sem isso "pa" -- apelido de
# progressao aritmetica -- casa dentro de "geometria esPAcial", e pedir
# geometria espacial devolvia PA. E a forma que a tabela de cartoes do
# Laboratorio ja tinha aprendido (la o marcador e " pa ", com espacos).
_MINIMO_PARA_CONTENCAO = 4


def _contem_com_corpo(busca: str, questao: str) -> bool:
    if busca not in questao and questao not in busca:
        return False
    return min(len(busca), len(questao)) >= _MINIMO_PARA_CONTENCAO


def _apelido_na_busca(apelido: str, busca: str) -> bool:
    """O apelido tem de aparecer como PALAVRA, nao como pedaco.

    MELHORIA: era `apelido in busca`. Assim "dinamica" (apelido da segunda lei
    de Newton) casava dentro de "termoDINAMICA", e pedir termodinamica devolvia
    questao de forca; "pa" casava dentro de "paRAbola" e de "esPAcial".

    Medido nas 158 consultas do mapa: muda 6, e as 6 sao casamentos espurios
    saindo -- nenhum legitimo se perde.
    """
    return re.search(rf"(?<![a-z0-9]){re.escape(apelido)}(?![a-z0-9])", busca) is not None


def _rank_tema(tema_busca: str, tema_questao: str) -> int:
    """Quao direto e o casamento: 0 exato, 1 contencao, 2 apelido.

    O seletor fica so com o melhor rank disponivel. E o que faz "energia
    cinetica" devolver energia cinetica em vez de trabalho mecanico (que casa
    por ter "energia" entre os apelidos): o nome do tema vence o apelido de
    outro tema.
    """
    busca = _normalizar_busca(tema_busca)
    questao = _normalizar_busca(tema_questao)
    if busca == questao:
        return 0
    if _contem_com_corpo(busca, questao):
        return 1
    return 2


def _tema_compativel(materia: str, tema_busca: str, tema_questao: str) -> bool:
    busca = _normalizar_busca(tema_busca)
    questao = _normalizar_busca(tema_questao)
    if not busca:
        return False
    if busca == questao or _contem_com_corpo(busca, questao):
        return True
    aliases = ALIASES_TEMAS_LAB.get(materia, {})
    for tema_canonico, termos in aliases.items():
        canonico = _normalizar_busca(tema_canonico)
        if canonico != questao and canonico not in questao and questao not in canonico:
            continue
        return any(_apelido_na_busca(_normalizar_busca(termo), busca) for termo in termos)
    return False


def _passo(titulo: str, conteudo: str, final: bool = False) -> dict[str, Any]:
    return {"titulo": titulo, "conteudo": conteudo, "final": final}


_NUMERO_NA_OPCAO = re.compile(r"-?\d+(?:[.,]\d+)?")


def _chave_opcao(texto: str) -> str:
    """Compara alternativas preservando acento e unidade -- sao eles que
    distinguem "15" de "15 m" e, em outras materias, "as" de "as"."""
    return re.sub(r"\s+", " ", str(texto or "")).strip().rstrip(".")


def _variar_numero(texto: str, delta: float) -> str | None:
    """Distrator de reserva: mexe no primeiro numero e mantem o resto
    (prefixo, unidade, formato)."""
    achado = _NUMERO_NA_OPCAO.search(texto or "")
    if not achado:
        return None
    bruto = achado.group(0)
    decimal = "," in bruto or "." in bruto
    try:
        valor = float(bruto.replace(",", "."))
    except ValueError:
        return None
    novo = valor + delta
    if novo == valor or novo < 0:
        return None
    if decimal:
        formatado = f"{novo:.1f}"
        if "," in bruto:
            formatado = formatado.replace(".", ",")
    else:
        formatado = str(int(novo))
    return texto[: achado.start()] + formatado + texto[achado.end() :]


def _opcoes(correta: str, distratores: list[str], seed: str) -> tuple[list[str], int]:
    # MELHORIA: os distratores iam para a tela sem nenhuma conferencia, e
    # varias formulas daqui produzem exatamente o valor da resposta para
    # certos numeros -- na sequencia que comeca em r e cresce de r em r o
    # distrator "inicio * posicao" e igual ao 5o termo em TODOS os casos, e
    # no cubo 6*a^2 == a^3 quando a = 6. O aluno via a resposta certa duas
    # vezes e so uma delas contava como acerto. Agora a colisao e descartada
    # e reposta por uma variacao numerica da propria resposta.
    escolhidas = [correta]
    vistos = {_chave_opcao(correta)}
    for distrator in distratores:
        chave = _chave_opcao(distrator)
        if chave in vistos:
            continue
        vistos.add(chave)
        escolhidas.append(distrator)
        if len(escolhidas) == 4:
            break

    for delta in (1, -1, 2, -2, 3, -3, 5, 10):
        if len(escolhidas) == 4:
            break
        reserva = _variar_numero(correta, delta)
        if not reserva or _chave_opcao(reserva) in vistos:
            continue
        vistos.add(_chave_opcao(reserva))
        escolhidas.append(reserva)

    opcoes = escolhidas[:4]
    random.Random(seed).shuffle(opcoes)
    return opcoes, opcoes.index(correta)


# A tela do Laboratorio mostra os passos, e nao esta frase. Ela so aparecia no
# ENEM e na Batalha, que usam este banco -- e la sai quando ha passos para
# mostrar no lugar (web/routes/flask_helpers_fla.py::explicacao_sem_frase_generica).
EXPLICACAO_GENERICA_LAB = "Identifique as grandezas, substitua os valores na formula e confira a unidade final."


# Que nivel cada modelo do banco REALMENTE pede.
#
# Achado 5.6 do QA de 23/09/2026: 'Laboratorio - Quimica "Dificil" recebeu o
# mesmo modelo basico de estequiometria do nivel Facil; "Dificil" em outro
# caso era Q = m.c.DT direto'. A causa estava aqui: a dificuldade saia de
# ("Facil", "Medio", "Dificil")[indice % 3], e o numero de modelos (22 em
# Matematica, 10 nas outras) nao e multiplo de 3 -- entao TODO modelo
# aparecia nos tres niveis. O campo nao dizia nada sobre a questao, e o
# seletor de dificuldade do Laboratorio nao mudava nada de verdade.
#
# O criterio abaixo e quantas etapas a conta pede e que conceito ela exige:
# "Qual e 8% de R$ 160?" e uma substituicao direta; "Resolva por Bhaskara" e
# discriminante mais duas raizes. E uma primeira classificacao, feita lendo
# os 63 modelos um a um -- se o professor discordar de alguma, muda-se a
# linha, e nada mais no app precisa saber.
_NIVEL_DO_MODELO: dict[tuple[str, str], str] = {
    # --- Matematica (Ensino Medio): 22 modelos ---
    ("Matematica", "porcentagem"): "Facil",
    ("Matematica", "area do retangulo"): "Facil",
    ("Matematica", "area do triangulo"): "Facil",
    ("Matematica", "funcao do 1o grau"): "Facil",
    ("Matematica", "probabilidade"): "Facil",
    ("Matematica", "estatistica"): "Facil",
    ("Matematica", "geometria espacial"): "Facil",
    ("Matematica", "proporcao"): "Facil",
    ("Matematica", "progressao aritmetica"): "Medio",
    ("Matematica", "progressao geometrica"): "Medio",
    ("Matematica", "juros simples"): "Medio",
    ("Matematica", "sistemas lineares"): "Medio",
    ("Matematica", "funcao exponencial"): "Medio",
    ("Matematica", "funcao logaritmica"): "Medio",
    ("Matematica", "combinatoria"): "Medio",
    ("Matematica", "taxas e indices"): "Medio",
    ("Matematica", "escala e variacao percentual"): "Medio",
    ("Matematica", "equacao do 2o grau"): "Dificil",
    ("Matematica", "geometria analitica"): "Dificil",
    ("Matematica", "funcao do 2o grau"): "Dificil",
    ("Matematica", "matrizes e determinantes"): "Dificil",
    ("Matematica", "probabilidade condicional"): "Dificil",
    ("Matematica", "trigonometria"): "Dificil",
    # --- Fisica: 10 modelos ---
    ("Fisica", "velocidade media"): "Facil",
    ("Fisica", "segunda lei de Newton"): "Facil",
    ("Fisica", "trabalho mecanico"): "Facil",
    ("Fisica", "potencia eletrica"): "Facil",
    ("Fisica", "potencia mecanica"): "Medio",
    ("Fisica", "lei de Ohm"): "Medio",
    ("Fisica", "pressao"): "Medio",
    ("Fisica", "movimento uniformemente variado"): "Medio",
    ("Fisica", "calorimetria"): "Dificil",
    ("Fisica", "energia cinetica"): "Dificil",
    # --- Quimica: 10 modelos ---
    ("Quimica", "concentracao comum"): "Facil",
    ("Quimica", "densidade"): "Facil",
    ("Quimica", "porcentagem em massa"): "Facil",
    ("Quimica", "mol e massa molar"): "Medio",
    ("Quimica", "massa a partir de mol"): "Medio",
    ("Quimica", "diluicao"): "Medio",
    ("Quimica", "estequiometria"): "Medio",
    ("Quimica", "pH"): "Dificil",
    ("Quimica", "termoquimica"): "Dificil",
    ("Quimica", "gases ideais"): "Dificil",
    # --- Matematica (Ensino Fundamental): 10 modelos ---
    # O teto do EF e mais baixo: "Dificil" aqui e a conta de duas etapas.
    ("Matematica", "numeros inteiros e operacoes basicas"): "Facil",
    ("Matematica", "fracoes e numeros decimais"): "Facil",
    ("Matematica", "equacoes do 1o grau"): "Facil",
    ("Matematica", "areas de figuras planas"): "Facil",
    ("Matematica", "perimetro e comprimento"): "Facil",
    ("Matematica", "regra de tres simples"): "Medio",
    ("Matematica", "sequencias numericas"): "Medio",
    ("Matematica", "razao e proporcao"): "Medio",
    ("Matematica", "porcentagem e desconto"): "Dificil",
    ("Matematica", "volume de solidos simples"): "Dificil",
    # --- Ciencias (Ensino Fundamental): 10 modelos ---
    ("Ciencias", "velocidade e movimento"): "Facil",
    ("Ciencias", "agua"): "Facil",
    ("Ciencias", "ar e poluicao"): "Facil",
    ("Ciencias", "forcas e atrito"): "Medio",
    ("Ciencias", "energia e suas formas"): "Medio",
    ("Ciencias", "eletricidade basica"): "Medio",
    ("Ciencias", "vacinas"): "Medio",
    ("Ciencias", "reciclagem"): "Medio",
    ("Ciencias", "propriedades dos materiais"): "Dificil",
    ("Ciencias", "misturas homogeneas e heterogeneas"): "Dificil",
}


def _nivel_normalizado(valor: Any) -> str:
    """"Médio", "MEDIO" e "Medio" sao o mesmo nivel."""
    sem_acento = unicodedata.normalize("NFKD", str(valor or "").strip().lower())
    return "".join(ch for ch in sem_acento if not unicodedata.combining(ch))


def _payload(materia: str, indice: int, tema: str, pergunta: str, correta: str, distratores: list[str], formula: str, legenda: str, passos: list[dict[str, Any]], subformulas: list[str] | None = None, serie_tipo: str = "EM") -> dict[str, Any]:
    opcoes, correta_idx = _opcoes(correta, distratores, f"{materia}|{indice}|{tema}|{correta}")
    return {
        "id_offline": f"LAB-{serie_tipo}-{materia}-{indice + 1:04d}",
        "materia": materia,
        "serie_tipo": serie_tipo,
        "tema_usado": tema,
        "objeto_conhecimento": tema,
        # Modelo fora da tabela volta ao rodizio antigo: banco novo entra sem
        # ficar sem dificuldade nenhuma, e a falta aparece no teste.
        "dificuldade": _NIVEL_DO_MODELO.get((materia, tema), ("Facil", "Medio", "Dificil")[indice % 3]),
        # Sem "Banco de formulas:" na frente: o titulo vai para a tela (15/09/2026).
        "enigma": f"{tema[:1].upper()}{tema[1:]} em uma situacao numerica.",
        "pergunta": pergunta,
        "opcoes": opcoes,
        "correta": correta_idx,
        "formula": formula,
        "subformulas": subformulas or [],
        "legenda_variaveis": legenda,
        "explicacao": [
            {"tipo": "bold", "conteudo": tema},
            {"tipo": "texto", "conteudo": EXPLICACAO_GENERICA_LAB},
            {"tipo": "resultado", "conteudo": f"Resposta correta: {correta}."},
        ],
        "passos_resolucao": passos,
        # MELHORIA: o Laboratorio e o modo MAIS usado (53 de 107 logs reais) e
        # era o unico de exatas sem BNCC nenhuma -- 0% dos logs. As materias
        # dele (Matematica, Fisica, Quimica, Ciencias) ja estao mapeadas em
        # BNCC_REFERENCIAS; faltava so trazer.
        **_bncc_da_materia(materia),
        "_origem_geracao": "offline",
    }


def _matematica_escala(tema: str, indice: int = 0) -> dict[str, Any]:
    pares = [(80, 100), (120, 150), (200, 260), (90, 117), (240, 300), (160, 184)]
    valor_inicial, valor_final = pares[indice % len(pares)]
    aumento = valor_final - valor_inicial
    percentual = aumento / valor_inicial * 100
    return _payload(
        "Matematica",
        10_000 + indice,
        "escala e variacao percentual",
        (
            f"Uma loja aumenta um produto de R$ {valor_inicial} para R$ {valor_final}. "
            "Qual e o percentual de aumento?"
        ),
        f"{_fmt(percentual)}%",
        ["20%", "80%", "125%"],
        r"p=\frac{V_f-V_i}{V_i}\cdot100",
        "Vi: valor inicial; Vf: valor final; p: percentual de aumento.",
        [
            _passo("1o Passo", f"Valor inicial = R$ {valor_inicial}; valor final = R$ {valor_final}."),
            _passo("2o Passo", f"Aumento = {valor_final} - {valor_inicial} = {aumento}."),
            _passo("3o Passo", rf"p = \frac{{{aumento}}}{{{valor_inicial}}}\cdot100 = {_fmt(percentual)}\%"),
            _passo("Resultado Final", f"O aumento foi de {_fmt(percentual)}%.", True),
        ],
        [r"\Delta V=V_f-V_i"],
    )


def _fmt_coeficiente(valor: int, variavel: str) -> str:
    sinal = "+" if valor >= 0 else "-"
    return f" {sinal} {abs(valor)}{variavel}"


def _fmt_constante(valor: int) -> str:
    sinal = "+" if valor >= 0 else "-"
    return f" {sinal} {abs(valor)}"


def _expressao_quadratica(a: int, b: int, c: int) -> str:
    """So o lado esquerdo, sem "= 0" -- para enunciados que descrevem uma
    grandeza modelada pela funcao (altura, largura, area)."""
    termo_a = "x^2" if a == 1 else f"{a}x^2"
    return f"{termo_a}{_fmt_coeficiente(b, 'x')}{_fmt_constante(c)}"


def _equacao_quadratica(a: int, b: int, c: int) -> str:
    return f"{_expressao_quadratica(a, b, c)} = 0"


def _opcoes_raizes(x1: int, x2: int) -> tuple[str, list[str]]:
    correta = f"x' = {x1} e x'' = {x2}"
    # MELHORIA: os distratores eram sempre (x1+1, x2), (-x1, -x2) e
    # (x1, x2+1). Quando a raiz e dupla (x1 == x2), o primeiro e o terceiro
    # descrevem o MESMO par em ordem trocada -- para x^2-6x+9=0 saiam
    # "x' = 4 e x'' = 3" e "x' = 3 e x'' = 4", duas alternativas
    # equivalentes na mesma questao. Agora a comparacao e pelo par
    # ordenado, com candidatos de reserva para repor o descartado.
    candidatos = [
        (x1 + 1, x2),
        (-x1, -x2),
        (x1, x2 + 1),
        (x1 - 1, x2),
        (x1, x2 - 1),
        (x1 + 2, x2),
    ]
    vistos = {tuple(sorted((x1, x2)))}
    distratores = []
    for par in candidatos:
        chave = tuple(sorted(par))
        if chave in vistos:
            continue
        vistos.add(chave)
        distratores.append(f"x' = {par[0]} e x'' = {par[1]}")
        if len(distratores) == 3:
            break
    return correta, distratores


def _contextualizar_laboratorio(pergunta: str, materia: str, indice: int) -> str:
    base = str(pergunta or "").strip()
    if not base:
        return base
    prefixos = {
        "Fisica": [
            "{base}",
            "Em um experimento escolar, {base_lc}",
            "Durante uma analise de laboratorio, {base_lc}",
            "Em uma situacao de engenharia simples, {base_lc}",
            "Na revisao de grandezas fisicas, {base_lc}",
        ],
        "Quimica": [
            "{base}",
            "Em uma bancada de laboratorio, {base_lc}",
            "Durante a preparacao de uma amostra, {base_lc}",
            "Em um controle de qualidade, {base_lc}",
            "Na analise de uma solucao, {base_lc}",
        ],
    }
    modelos = prefixos.get(materia, ["{base}"])
    base_lc = f"{base[:1].lower()}{base[1:]}" if base else base
    base_busca = _normalizar_busca(base)

    # MELHORIA: o prefixo era sorteado so pela posicao, e em Quimica batia com
    # o comeco da pergunta: "Na analise de uma solucao, uma solucao 3 mol/L..."
    # e "Durante a preparacao de uma amostra, uma amostra tem massa..." -- 88 das
    # 440 questoes, medido em 15/09/2026 no teste pelo Chrome. E as 44 de gas
    # ideal saiam com "Na analise de uma solucao, um gas ocupa...". Agora o
    # prefixo que repete o sujeito, ou fala de solucao numa questao sem solucao,
    # passa a vez ao seguinte da lista.
    def _combina(modelo: str) -> bool:
        prefixo = _normalizar_busca(modelo.split("{", 1)[0])
        if "de uma solucao" in prefixo and "soluc" not in base_busca:
            return False
        return not any(sujeito in prefixo and base_busca.startswith(sujeito) for sujeito in ("uma solucao", "uma amostra"))

    candidatos = [modelos[(indice + passo) % len(modelos)] for passo in range(len(modelos))]
    modelo = next((candidato for candidato in candidatos if _combina(candidato)), "{base}")
    return modelo.format(base=base, base_lc=base_lc)


def _passos_bhaskara(a: int, b: int, c: int, x1: int, x2: int) -> list[dict[str, Any]]:
    delta = b * b - 4 * a * c
    raiz_delta = abs(a * (x2 - x1))
    denominador = 2 * a
    return [
        _passo("1o Passo", f"a = {a}, b = {b}, c = {c}."),
        _passo("2o Passo", rf"\Delta = ({b})^2 - 4\cdot {a}\cdot {c} = {delta}"),
        _passo("3o Passo", rf"x = \frac{{{-b}\pm\sqrt{{{delta}}}}}{{{denominador}}} = \frac{{{-b}\pm {raiz_delta}}}{{{denominador}}}"),
        _passo("Resultado Final", rf"x' = {x1};\; x'' = {x2}", True),
    ]


def _matematica_equacao_2o_grau(indice: int, k: int) -> dict[str, Any]:
    casos = [
        {"raizes": (2, 4), "a": 1, "modelo": 0},
        {"raizes": (-3, -5), "a": 1, "modelo": 1},
        {"raizes": (1, 6), "a": 2, "modelo": 2},
        {"raizes": (-2, 5), "a": 1, "modelo": 3},
        {"raizes": (3, 3), "a": 1, "modelo": 4},
        {"raizes": (-4, 2), "a": 2, "modelo": 5},
        {"raizes": (4, 7), "a": 1, "modelo": 6},
        {"raizes": (-6, -1), "a": 1, "modelo": 7},
        {"raizes": (2, 8), "a": 3, "modelo": 8},
        {"raizes": (-5, 3), "a": 2, "modelo": 9},
        {"raizes": (5, 9), "a": 1, "modelo": 10},
        {"raizes": (-7, -2), "a": 2, "modelo": 11},
        {"raizes": (1, 1), "a": 3, "modelo": 12},
        {"raizes": (-3, 4), "a": 2, "modelo": 13},
        {"raizes": (6, 10), "a": 1, "modelo": 14},
        {"raizes": (-8, 1), "a": 1, "modelo": 15},
        {"raizes": (3, 9), "a": 2, "modelo": 16},
        {"raizes": (-4, -4), "a": 1, "modelo": 17},
        {"raizes": (-2, 6), "a": 3, "modelo": 18},
        {"raizes": (4, 4), "a": 2, "modelo": 19},
    ]
    # MELHORIA: era `casos[(indice // 20) % len(casos)]` -- um 20 fixo que
    # duplicava a quantidade de templates de _matematica, justamente o numero
    # que a funcao ja recebe pronto em `k` (k = indice // templates + 1).
    # Enquanto os dois valores coincidiram ninguem notou; ao acrescentar
    # trigonometria e proporcao (20 -> 22 templates) as duas contas
    # divergiram e duas equacoes passaram a se repetir na mesma rodada.
    caso = casos[(k - 1) % len(casos)]
    modelos = caso["modelo"]
    x1, x2 = caso["raizes"]
    a = caso["a"]
    b = -a * (x1 + x2)
    c = a * x1 * x2
    equacao = _equacao_quadratica(a, b, c)
    expressao = _expressao_quadratica(a, b, c)
    correta, distratores = _opcoes_raizes(x1, x2)

    # MELHORIA: o verbo do encontro com o eixo x vinha fixo na posicao da
    # lista, nao das raizes do caso -- o modelo 4 dizia "cruza" justamente
    # para x^2-6x+9=0, que tem raiz dupla (a parabola apenas tangencia), e
    # pedia "pontos" no plural para um unico ponto. Agora sai do caso.
    # As alternativas sempre listam x' e x'' (ver _opcoes_raizes), entao a
    # pergunta precisa pedir as raizes -- nao "a coordenada" no singular,
    # que nao casaria com o formato da resposta na raiz dupla.
    if x1 == x2:
        encontro_eixo = "tangencia o eixo x em um unico ponto"
        pergunta_coordenada = "Qual alternativa traz a raiz dupla dessa equacao?"
    else:
        encontro_eixo = "cruza o eixo x em dois pontos"
        pergunta_coordenada = "Quais sao as coordenadas x desses pontos?"

    # MELHORIA: varios enunciados tratavam {equacao} como se fosse uma
    # expressao, mas ela ja vem com "= 0" embutido. Isso produzia frases
    # circulares ou erradas: "A altura de um projetil e modelada por
    # 2x^2-14x+12 = 0" (altura modelada por algo ja igualado a zero) e
    # "Uma funcao quadratica tem zeros obtidos ao resolver x^2-16x+60 = 0.
    # Quais sao esses zeros?" (define a resposta e depois pede a resposta).
    # Quem descreve uma grandeza usa {expressao}; quem pede para resolver
    # usa {equacao}.
    perguntas = [
        f"Resolva por Bhaskara a equacao {equacao}. Quais sao as raizes?",
        f"Uma equacao do 2o grau aparece como {equacao}. Qual alternativa traz o conjunto-solucao?",
        f"A altura de um projetil segue a expressao {expressao}, com x em segundos. Em que instantes a altura chega a zero?",
        f"Fatorando a equacao {equacao}, quais valores de x anulam o produto?",
        f"Uma parabola {encontro_eixo} quando {equacao}. {pergunta_coordenada}",
        f"Em um projeto de arco parabolico, a funcao fica nula quando {equacao}. Quais valores de x atendem a condicao?",
        f"Uma area foi modelada por uma expressao quadratica e precisa satisfazer {equacao}. Quais sao as solucoes reais?",
        f"No estudo de uma trajetoria, os instantes de contato com o solo aparecem em {equacao}. Quais sao esses instantes?",
        f"O grafico de uma funcao quadratica encontra o eixo x nos valores que resolvem {equacao}. Quais sao eles?",
        f"Para calibrar um simulador, e preciso resolver {equacao}. Qual alternativa apresenta as duas raizes?",
        f"Um sensor registra zero quando a equacao {equacao} e satisfeita. Quais sao os valores possiveis de x?",
        f"Na montagem de uma ponteira parabolica, a equacao {equacao} define os pontos de ajuste. Quais sao as raizes?",
        f"Em uma atividade de revisao, a turma precisa resolver {equacao} usando Bhaskara. Qual e o resultado?",
        f"A largura de uma peca segue a expressao {expressao}. Para quais valores de x ela se anula?",
        f"Uma funcao quadratica tem a expressao {expressao}. Quais sao os zeros dessa funcao?",
        f"Em uma simulacao de lancamento, resolver {equacao} indica dois momentos importantes. Quais sao eles?",
        f"Para comparar duas curvas, e necessario achar as solucoes de {equacao}. Qual alternativa esta correta?",
        f"Um aplicativo de estudos gerou a equacao {equacao}. Quais raizes a formula de Bhaskara fornece?",
        f"Em uma analise de grafico, os interceptos no eixo x obedecem a {equacao}. Quais sao os interceptos?",
        f"Uma area foi modelada pela expressao {expressao}. Que valores de x zeram essa area?",
    ]

    return _payload(
        "Matematica",
        indice,
        "equacao do 2o grau",
        perguntas[modelos],
        correta,
        distratores,
        r"x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}",
        "a, b e c: coeficientes da equacao do 2o grau.",
        _passos_bhaskara(a, b, c, x1, x2),
        [r"\Delta = b^2 - 4ac"],
    )


def _matematica(indice: int) -> dict[str, Any]:
    tipo, k = indice % 22, indice // 22 + 1
    if tipo == 0:
        valor, taxa = 120 + 40 * k, 5 + 3 * k
        res = valor * taxa / 100
        return _payload("Matematica", indice, "porcentagem", f"Um projeto escolar custa R$ {valor}. Qual e {taxa}% desse valor?", f"R$ {_fmt(res)}", [f"R$ {_fmt(res + 8)}", f"R$ {_fmt(max(1, res - 6))}", f"R$ {_fmt(res + 15)}"], r"P = \frac{p}{100}\cdot V", "p: taxa percentual; V: valor total.", [_passo("1o Passo", f"p = {taxa} e V = {valor}."), _passo("2o Passo", rf"P = \frac{{{taxa}}}{{100}}\cdot {valor} = {_fmt(res)}"), _passo("Resultado Final", f"P = {_fmt(res)}", True)])
    if tipo == 1:
        a1, r, n = 2 + k, 3 + k, 6 + k
        an = a1 + (n - 1) * r
        return _payload("Matematica", indice, "progressao aritmetica", f"Em uma PA, a1 = {a1}, razao = {r} e n = {n}. Qual e o termo an?", str(an), [str(an + r), str(an - r), str(an + 2 * r)], r"a_n = a_1 + (n-1)\cdot r", "a1: primeiro termo; r: razao; n: posicao.", [_passo("1o Passo", f"a1 = {a1}, r = {r}, n = {n}."), _passo("2o Passo", rf"Saltos de r ate o termo pedido: ({n}-1)\cdot {r} = {n - 1}\cdot {r} = {(n - 1) * r}"), _passo("3o Passo", rf"a_n = {a1} + {(n - 1) * r} = {an}"), _passo("Resultado Final", f"a_n = {an}", True)])
    if tipo == 2:
        # MELHORIA: a razao E a posicao cresciam juntas (q = 2+k, n = 3+k),
        # entao o termo estourava -- em k = 18 a resposta tinha 23 digitos e
        # os distratores (an+q, an//q, an+a1) diferiam so nos ultimos
        # algarismos: a questao virava comparacao de digitos, nao
        # progressao geometrica. Agora as tres variaveis giram em faixas
        # escolares; como lcm(5, 4, 3) = 60 > 20 valores de k, cada k ainda
        # produz uma combinacao diferente.
        a1, q, n = 1 + (k % 5), 2 + (k % 4), 4 + (k % 3)
        an = a1 * (q ** (n - 1))
        return _payload("Matematica", indice, "progressao geometrica", f"Em uma PG, a1 = {a1}, razao = {q} e n = {n}. Qual e o termo an?", str(an), [str(an + q), str(max(1, an // q)), str(an + a1)], r"a_n = a_1\cdot q^{n-1}", "a1: primeiro termo; q: razao; n: posicao.", [_passo("1o Passo", f"a1 = {a1}, q = {q}, n = {n}."), _passo("2o Passo", rf"Potencia da razao: {q}^{{{n - 1}}} = {q ** (n - 1)}"), _passo("3o Passo", rf"a_n = {a1}\cdot {q ** (n - 1)} = {an}"), _passo("Resultado Final", f"a_n = {an}", True)])
    if tipo == 3:
        b, h = 5 + k, 7 + k
        area = b * h
        return _payload("Matematica", indice, "area do retangulo", f"Uma sala retangular mede {b} m por {h} m. Qual e sua area?", f"{area} m^2", [f"{area + b} m^2", f"{area + h} m^2", f"{2 * (b + h)} m^2"], r"A = b\cdot h", "b: base; h: altura.", [_passo("1o Passo", f"b = {b}, h = {h}."), _passo("2o Passo", rf"A = {b}\cdot {h} = {area}"), _passo("Resultado Final", f"A = {area} m^2", True)])
    if tipo == 4:
        b, h = 8 + k, 4 + k
        area = b * h / 2
        return _payload("Matematica", indice, "area do triangulo", f"Um triangulo tem base {b} cm e altura {h} cm. Qual e sua area?", f"{_fmt(area)} cm^2", [f"{_fmt(b*h)} cm^2", f"{_fmt(area + b)} cm^2", f"{_fmt(max(1, area - h))} cm^2"], r"A = \frac{b\cdot h}{2}", "b: base; h: altura.", [_passo("1o Passo", f"b = {b}, h = {h}."), _passo("2o Passo", rf"A = \frac{{{b}\cdot {h}}}{{2}} = {_fmt(area)}"), _passo("Resultado Final", f"A = {_fmt(area)} cm^2", True)])
    if tipo == 5:
        c, taxa, t = 200 + 80 * k, 2 + k, 3 + k
        j = c * taxa * t / 100
        return _payload("Matematica", indice, "juros simples", f"Um valor de R$ {c} rende juros simples de {taxa}% ao mes por {t} meses. Qual e o juro?", f"R$ {_fmt(j)}", [f"R$ {_fmt(j + 20)}", f"R$ {_fmt(max(1, j - 12))}", f"R$ {_fmt(c + j)}"], r"J = C\cdot i\cdot t", "C: capital; i: taxa decimal; t: tempo.", [_passo("1o Passo", f"C = {c}, t = {t}."), _passo("2o Passo", rf"Taxa em decimal: i = \frac{{{taxa}}}{{100}} = {_fmt(taxa / 100)}"), _passo("3o Passo", rf"J = {c}\cdot {_fmt(taxa / 100)}\cdot {t} = {_fmt(j)}"), _passo("Resultado Final", f"J = R$ {_fmt(j)}", True)])
    if tipo == 6:
        a, b, x = 2 + k, 4 + k, 5 + k
        y = a * x + b
        return _payload("Matematica", indice, "funcao do 1o grau", f"Na funcao f(x) = {a}x + {b}, qual e f({x})?", str(y), [str(y + a), str(y - b), str(y + 2 * a)], r"f(x)=ax+b", "a: coeficiente angular; b: termo constante.", [_passo("1o Passo", f"a = {a}, b = {b}, x = {x}."), _passo("2o Passo", rf"f({x}) = {a}\cdot {x} + {b} = {y}"), _passo("Resultado Final", f"f({x}) = {y}", True)])
    if tipo == 7:
        return _matematica_equacao_2o_grau(indice, k)
    if tipo == 8:
        fav, total = 2 + k, 8 + 2 * k
        return _payload("Matematica", indice, "probabilidade", f"Em uma caixa ha {total} fichas, sendo {fav} premiadas. Qual e a probabilidade de retirar uma premiada?", f"{fav}/{total}", [f"{total}/{fav}", f"{fav}/{total - fav}", f"{total - fav}/{total}"], r"P(A)=\frac{n(A)}{n(S)}", "n(A): casos favoraveis; n(S): casos possiveis.", [_passo("1o Passo", f"Favoraveis = {fav}, possiveis = {total}."), _passo("2o Passo", rf"P = \frac{{{fav}}}{{{total}}}"), _passo("Resultado Final", f"P = {fav}/{total}", True)])
    if tipo == 9:
        x1, y1, x2, y2 = k, 2 * k, k + 3, 2 * k + 4
        return _payload("Matematica", indice, "geometria analitica", f"No plano cartesiano, qual e a distancia entre A({x1},{y1}) e B({x2},{y2})?", "5", ["6", "4", "7"], r"d=\sqrt{(x_2-x_1)^2+(y_2-y_1)^2}", "x e y: coordenadas dos pontos.", [_passo("1o Passo", rf"\Delta x = {x2} - {x1} = {x2 - x1}"), _passo("2o Passo", rf"\Delta y = {y2} - {y1} = {y2 - y1}"), _passo("3o Passo", rf"Soma dos quadrados: {x2 - x1}^2 + {y2 - y1}^2 = {(x2 - x1) ** 2} + {(y2 - y1) ** 2} = {(x2 - x1) ** 2 + (y2 - y1) ** 2}"), _passo("4o Passo", r"d = \sqrt{25} = 5"), _passo("Resultado Final", "d = 5", True)])
    if tipo == 10:
        x, y = 2 + k, 1 + k
        soma, diferenca = x + y, x - y
        return _payload("Matematica", indice, "sistemas lineares", f"Em um sistema, x + y = {soma} e x - y = {diferenca}. Qual e o valor de x?", str(x), [str(y), str(soma), str(diferenca)], r"\begin{cases}x+y=s\\x-y=d\end{cases}", "s: soma; d: diferenca.", [_passo("1o Passo", f"Some as equacoes: 2x = {soma} + {diferenca}."), _passo("2o Passo", f"2x = {2*x}, entao x = {x}."), _passo("Resultado Final", f"x = {x}", True)])
    if tipo == 11:
        a, h, k_vert = 1, 2 + k, 3 + k
        return _payload("Matematica", indice, "funcao do 2o grau", f"A funcao f(x) = (x - {h})^2 + {k_vert} tem vertice em qual ponto?", f"({h}, {k_vert})", [f"({-h}, {k_vert})", f"({h}, {-k_vert})", f"({k_vert}, {h})"], r"f(x)=a(x-h)^2+k", "V: vertice; h e k: coordenadas do vertice na forma a(x - h)^2 + k.", [_passo("1o Passo", "O vertice fica em (h, k) na forma: f(x) = a(x - h)^2 + k"), _passo("2o Passo", f"Comparando com f(x) = (x - {h})^2 + {k_vert}: h = {h} e k = {k_vert}"), _passo("Resultado Final", f"V = ({h}, {k_vert})", True)])
    if tipo == 12:
        p0, t = 100 + 20 * k, 3
        res = p0 * (2 ** t)
        return _payload("Matematica", indice, "funcao exponencial", f"Uma populacao inicial de {p0} bacterias dobra a cada hora. Quantas bacterias havera apos {t} horas?", str(res), [str(res // 2), str(res + p0), str(p0 * t)], r"P=P_0\cdot2^t", "P0: quantidade inicial; t: tempo.", [_passo("1o Passo", f"P0 = {p0}, t = {t}."), _passo("2o Passo", rf"A cada hora a populacao dobra: 2^{t} = {2 ** t}"), _passo("3o Passo", rf"P = {p0}\cdot {2 ** t} = {res}"), _passo("Resultado Final", f"P = {res}", True)])
    if tipo == 13:
        # MELHORIA: era `2, 3 + (k % 4)` -- base fixa e quatro expoentes, ou
        # seja 4 questoes distintas para 20 valores de k. Eram as unicas 16
        # perguntas repetidas do banco de Matematica. Cinco bases vezes quatro
        # expoentes dao exatamente 20 pares, um por k, sem repetir nenhum.
        bases = (2, 3, 4, 5, 10)
        base, expoente = bases[(k - 1) % 5], 2 + (k - 1) // 5
        valor = base ** expoente
        return _payload("Matematica", indice, "funcao logaritmica", f"Qual e o valor de log base {base} de {valor}?", str(expoente), [str(expoente + 1), str(max(1, expoente - 1)), str(valor)], r"\log_b(a)=x \Leftrightarrow b^x=a", "b: base; a: logaritmando; x: expoente.", [_passo("1o Passo", f"Procure x tal que {base}^x = {valor}."), _passo("2o Passo", f"{base}^{expoente} = {valor}."), _passo("Resultado Final", f"log_{base}({valor}) = {expoente}", True)])
    if tipo == 14:
        a, b, c, d = 1 + k, 2, 3, 4 + k
        det = a * d - b * c
        return _payload("Matematica", indice, "matrizes e determinantes", f"Qual e o determinante da matriz 2x2 de linhas ({a}, {b}) e ({c}, {d})?", str(det), [str(det + 2), str(a + d), str(b * c - a * d)], r"D=ad-bc", "a,b,c,d: elementos da matriz 2x2.", [_passo("1o Passo", rf"Produto da diagonal principal: {a}\cdot {d} = {a * d}"), _passo("2o Passo", rf"Produto da outra diagonal: {b}\cdot {c} = {b * c}"), _passo("3o Passo", rf"D = {a * d} - {b * c} = {det}"), _passo("Resultado Final", f"D = {det}", True)])
    if tipo == 15:
        n = 5 + k
        res = n * (n - 1) // 2
        return _payload("Matematica", indice, "combinatoria", f"De {n} alunos, quantas duplas diferentes podem ser formadas?", str(res), [str(n * (n - 1)), str(res + n), str(max(1, res - n))], r"C_{n,2}=\frac{n(n-1)}{2}", "n: total de elementos; 2: tamanho da dupla.", [_passo("1o Passo", "Numa dupla a ordem nao importa: Ana com Bia e Bia com Ana sao a mesma dupla."), _passo("2o Passo", rf"Escolhendo em ordem: {n}\cdot {n - 1} = {n * (n - 1)}"), _passo("3o Passo", rf"Cada dupla foi contada duas vezes: \frac{{{n * (n - 1)}}}{{2}} = {res}"), _passo("Resultado Final", f"{res} duplas", True)])
    if tipo == 16:
        total, grupo, favor = 40 + 5 * k, 20 + 2 * k, 5 + k
        return _payload("Matematica", indice, "probabilidade condicional", f"Em uma turma de {total} alunos, {grupo} fazem clube de ciencias. Desses, {favor} tambem fazem teatro. Qual e P(teatro | clube)?", f"{favor}/{grupo}", [f"{favor}/{total}", f"{grupo}/{total}", f"{grupo-favor}/{grupo}"], r"P(A|B)=\frac{n(A\cap B)}{n(B)}", "A: teatro; B: clube.", [_passo("1o Passo", f"Restrinja o espaco aos {grupo} alunos do clube."), _passo("2o Passo", rf"P = \frac{{{favor}}}{{{grupo}}}"), _passo("Resultado Final", f"{favor}/{grupo}", True)])
    if tipo == 17:
        a, b, c = 5 + k, 7 + k, 9 + k
        media = (a + b + c) / 3
        return _payload("Matematica", indice, "estatistica", f"As notas de um grupo foram {a}, {b} e {c}. Qual e a media?", _fmt(media), [_fmt(media + 1), _fmt(media - 1), str(a + b + c)], r"\bar{x}=\frac{x_1+x_2+x_3}{3}", "x: valores observados.", [_passo("1o Passo", f"Soma = {a} + {b} + {c} = {a+b+c}."), _passo("2o Passo", rf"\bar{{x}} = \frac{{{a+b+c}}}{{3}} = {_fmt(media)}"), _passo("Resultado Final", _fmt(media), True)])
    if tipo == 18:
        inicial, final = 100 + 20 * k, 120 + 25 * k
        taxa = (final - inicial) / inicial * 100
        return _payload("Matematica", indice, "taxas e indices", f"Um indice passou de {inicial} para {final}. Qual foi a taxa percentual de variacao?", f"{_fmt(taxa)}%", [f"{_fmt(taxa + 5)}%", f"{_fmt(max(0, taxa - 5))}%", f"{_fmt(final/inicial)}%"], r"t=\frac{V_f-V_i}{V_i}\cdot100", "Vi: valor inicial; Vf: valor final.", [_passo("1o Passo", f"Variacao = {final} - {inicial} = {final-inicial}."), _passo("2o Passo", rf"t = \frac{{{final-inicial}}}{{{inicial}}}\cdot100 = {_fmt(taxa)}\%"), _passo("Resultado Final", f"{_fmt(taxa)}%", True)])
    if tipo == 19:
        aresta = 3 + k
        volume = aresta ** 3
        return _payload("Matematica", indice, "geometria espacial", f"Um cubo tem aresta {aresta} cm. Qual e seu volume?", f"{volume} cm^3", [f"{aresta*aresta} cm^3", f"{6*aresta*aresta} cm^3", f"{volume+aresta} cm^3"], r"V=a^3", "a: medida da aresta.", [_passo("1o Passo", f"a = {aresta} cm."), _passo("2o Passo", rf"V = {aresta}^3 = {volume}"), _passo("Resultado Final", f"{volume} cm^3", True)])
    if tipo == 20:
        # MELHORIA: "trigonometria" ja estava prometida em ALIASES_TEMAS_LAB
        # (com os apelidos seno, cosseno e tangente) e NAO existia no banco.
        # Quem pedia o tema recebia estatistica ou probabilidade condicional --
        # e o cartao "onde usamos isso" de trigonometria nunca era alcancado,
        # porque nenhuma questao offline chegava perto dele.
        #
        # 30 graus de proposito: sen(30) = 0,5 exato, entao a conta fecha em
        # numero redondo e a alternativa nao vira comparacao de decimais.
        comprimento = 12 + 2 * k
        altura = comprimento // 2
        return _payload("Matematica", indice, "trigonometria", f"Uma rampa de acesso tem {comprimento} m de comprimento e forma 30 graus com o chao. Qual e a altura que ela alcanca?", f"{altura} m", [f"{comprimento} m", f"{altura + 2} m", f"{comprimento * 2} m"], r"h = c\cdot sen(\theta)", "c: comprimento da rampa; sen: seno do angulo com o chao; h: altura.", [_passo("1o Passo", f"c = {comprimento} m e o seno de 30 graus vale 0,5."), _passo("2o Passo", rf"h = {comprimento}\cdot 0,5 = {altura}"), _passo("Resultado Final", f"h = {altura} m", True)])
    if tipo == 21:
        # A outra prometida-e-inexistente. Regra de tres direta.
        medida, rende, pedido = 3, 12, 3 * (1 + k)
        total = pedido * rende // medida
        return _payload("Matematica", indice, "proporcao", f"Uma receita usa {medida} xicaras de farinha para render {rende} paes. Quantos paes rendem {pedido} xicaras, na mesma proporcao?", str(total), [str(total + rende), str(max(1, total - rende)), str(pedido * medida)], r"\frac{a}{b}=\frac{c}{d}", "a e b: receita original; c e d: quantidade pedida.", [_passo("1o Passo", f"{medida} xicaras estao para {rende} paes."), _passo("2o Passo", rf"p = \frac{{{pedido}\cdot {rende}}}{{{medida}}} = {total}"), _passo("Resultado Final", f"{total} paes", True)])
    aresta = 3 + k
    volume = aresta ** 3
    return _payload("Matematica", indice, "geometria espacial", f"Um cubo tem aresta {aresta} cm. Qual e seu volume?", f"{volume} cm^3", [f"{aresta*aresta} cm^3", f"{6*aresta*aresta} cm^3", f"{volume+aresta} cm^3"], r"V=a^3", "a: medida da aresta.", [_passo("1o Passo", f"a = {aresta} cm."), _passo("2o Passo", rf"V = {aresta}^3 = {volume}"), _passo("Resultado Final", f"{volume} cm^3", True)])


def _fisica(indice: int) -> dict[str, Any]:
    tipo, k = indice % 10, indice // 10 + 1
    formulas = [
        ("velocidade media", "m/s", r"v=\frac{\Delta s}{\Delta t}", "v: velocidade; Δs: deslocamento; Δt: tempo.", 80 + 20 * k, 4 + k, lambda a, b: a / b, "Um estudante percorre {a} m em {b} s. Qual e a velocidade media?"),
        ("segunda lei de Newton", "N", r"F=m\cdot a", "F: força; m: massa; a: aceleracao.", 3 + k, 2 + k, lambda a, b: a * b, "Um corpo de {a} kg acelera a {b} m/s^2. Qual e a forca resultante?"),
        ("trabalho mecanico", "J", r"\tau=F\cdot d", "tau: trabalho; F: força; d: deslocamento.", 20 + 5 * k, 3 + k, lambda a, b: a * b, "Uma força de {a} N desloca um objeto por {b} m. Qual e o trabalho?"),
        ("potencia mecanica", "W", r"P=\frac{\tau}{t}", "P: potencia; tau: trabalho; t: tempo.", 120 + 40 * k, 4 + k, lambda a, b: a / b, "Uma maquina realiza {a} J em {b} s. Qual e a potencia media?"),
        ("lei de Ohm", "A", r"i=\frac{U}{R}", "i: corrente; U: tensao; R: resistencia.", 12 + 6 * k, 3 + k, lambda a, b: a / b, "Um circuito tem tensao de {a} V e resistencia de {b} ohm. Qual e a corrente?"),
        ("potencia eletrica", "W", r"P=U\cdot i", "P: potencia; U: tensao; i: corrente.", 10 + 2 * k, 2 + k, lambda a, b: a * b, "Um aparelho opera com {a} V e {b} A. Qual e sua potencia?"),
        ("calorimetria", "J", r"Q=m\cdot c\cdot \Delta T", "Q: calor; m: massa; c: calor especifico; ΔT: variacao de temperatura.", 100 + 50 * k, 5 + k, lambda a, b: a * 4.2 * b, "Quantos joules aquecem {a} g de agua em {b} C, usando c = 4,2 J/gC?"),
        ("energia cinetica", "J", r"E_c=\frac{m\cdot v^2}{2}", "Ec: energia cinetica; m: massa; v: velocidade.", 2 + k, 4 + k, lambda a, b: a * b * b / 2, "Um corpo de {a} kg move-se a {b} m/s. Qual e a energia cinetica?"),
        ("pressao", "Pa", r"p=\frac{F}{A}", "p: pressao; F: força; A: area.", 60 + 10 * k, 3 + k, lambda a, b: a / b, "Uma força de {a} N atua em uma area de {b} m^2. Qual e a pressao?"),
        ("movimento uniformemente variado", "m/s", r"v=v_0+a\cdot t", "v0: velocidade inicial; a: aceleracao; t: tempo.", 2 + k, 3 + k, lambda a, b: a + (1 + k) * b, "Um movel tem v0 = {a} m/s, aceleracao {ak} m/s^2 por {b} s. Qual e a velocidade final?"),
    ]
    tema, unidade, formula, legenda, a, b, conta, texto = formulas[tipo]
    res = conta(a, b)
    correta = f"{_fmt(res)} {unidade}"
    pergunta = _contextualizar_laboratorio(texto.format(a=a, b=b, ak=1 + k), "Fisica", indice)
    if tipo == 0:
        passos = [_passo("1o Passo", rf"\Delta s = {a} m, \Delta t = {b} s"), _passo("2o Passo", rf"v = \frac{{{a} m}}{{{b} s}} = {_fmt(res)} m/s"), _passo("Resultado Final", rf"v = {_fmt(res)} m/s", True)]
    elif tipo == 1:
        passos = [_passo("1o Passo", rf"m = {a} kg, a = {b} m/s^2"), _passo("2o Passo", rf"F = {a} kg \cdot {b} m/s^2 = {_fmt(res)} N"), _passo("Resultado Final", rf"F = {_fmt(res)} N", True)]
    elif tipo == 2:
        passos = [_passo("1o Passo", rf"F = {a} N, d = {b} m"), _passo("2o Passo", rf"\tau = {a} N \cdot {b} m = {_fmt(res)} J"), _passo("Resultado Final", rf"\tau = {_fmt(res)} J", True)]
    elif tipo == 3:
        passos = [_passo("1o Passo", rf"\tau = {a} J, t = {b} s"), _passo("2o Passo", rf"P = \frac{{{a} J}}{{{b} s}} = {_fmt(res)} W"), _passo("Resultado Final", rf"P = {_fmt(res)} W", True)]
    elif tipo == 4:
        passos = [_passo("1o Passo", rf"U = {a} V, R = {b} ohm"), _passo("2o Passo", rf"i = \frac{{{a} V}}{{{b} ohm}} = {_fmt(res)} A"), _passo("Resultado Final", rf"i = {_fmt(res)} A", True)]
    elif tipo == 5:
        passos = [_passo("1o Passo", rf"U = {a} V, i = {b} A"), _passo("2o Passo", rf"P = {a} V \cdot {b} A = {_fmt(res)} W"), _passo("Resultado Final", rf"P = {_fmt(res)} W", True)]
    elif tipo == 6:
        passos = [_passo("1o Passo", rf"m = {a} g, c = 4,2 J/gC, \Delta T = {b} C"), _passo("2o Passo", rf"Q = {a} g \cdot 4,2 J/gC \cdot {b} C = {_fmt(res)} J"), _passo("Resultado Final", rf"Q = {_fmt(res)} J", True)]
    elif tipo == 7:
        passos = [_passo("1o Passo", rf"m = {a} kg, v = {b} m/s"), _passo("2o Passo", rf"Velocidade ao quadrado: {b}^2 = {b * b}"), _passo("3o Passo", rf"E_c = \frac{{{a}\cdot {b * b}}}{{2}} = {_fmt(res)} J"), _passo("Resultado Final", rf"E_c = {_fmt(res)} J", True)]
    elif tipo == 8:
        passos = [_passo("1o Passo", rf"F = {a} N, A = {b} m^2"), _passo("2o Passo", rf"p = \frac{{{a} N}}{{{b} m^2}} = {_fmt(res)} Pa"), _passo("Resultado Final", rf"p = {_fmt(res)} Pa", True)]
    else:
        ak = 1 + k
        passos = [_passo("1o Passo", rf"v_0 = {a} m/s, a = {ak} m/s^2, t = {b} s"), _passo("2o Passo", rf"v = {a} m/s + {ak} m/s^2 \cdot {b} s = {_fmt(res)} m/s"), _passo("Resultado Final", rf"v = {_fmt(res)} m/s", True)]
    return _payload("Fisica", indice, tema, pergunta, correta, [f"{_fmt(res + 2)} {unidade}", f"{_fmt(max(0.1, res - 1))} {unidade}", f"{_fmt(res + 4)} {unidade}"], formula, legenda, passos)


def _quimica(indice: int) -> dict[str, Any]:
    tipo, k = indice % 10, indice // 10 + 1
    formulas = [
        ("concentracao comum", "g/L", r"C=\frac{m}{V}", "C: concentracao; m: massa; V: volume.", 20 + 10 * k, 2 + k, lambda a, b: a / b, "Uma solucao tem {a} g de soluto em {b} L. Qual e a concentracao comum?"),
        ("mol e massa molar", "mol", r"n=\frac{m}{M}", "n: quantidade de materia; m: massa; M: massa molar.", 18 * (k + 1), 18, lambda a, b: a / b, "Quantos mol existem em {a} g de substancia com massa molar {b} g/mol?"),
        ("massa a partir de mol", "g", r"m=n\cdot M", "m: massa; n: mol; M: massa molar.", 2 + k, 44, lambda a, b: a * b, "Qual massa corresponde a {a} mol de uma substancia com M = {b} g/mol?"),
        # pH so existe entre 0 e 14: "k + 2" chegava a 10^{-45}, pH 45 (32 das 44).
        # O volume da amostra varia para a pergunta nao se repetir; ele nao
        # entra na conta, e o primeiro passo diz isso.
        ("pH", "", r"pH=-\log[H^+]", "[H+]: concentracao hidrogenionica.", 1 + (k + 1) % 13, 20 + 5 * k, lambda a, _b: a, "Uma amostra de {b} mL tem [H+] = 10^{{-{a}}} mol/L. Qual e o pH?"),
        # "2 + k" chegava a 46 mol/L, concentracao que nao existe; e "100 mL e
        # diluida" nao tinha verbo. O volume final continua variando.
        ("diluicao", "mol/L", r"C_1V_1=C_2V_2", "C: concentracao; V: volume.", 1 + (k + 1) % 6, 200 + 50 * k, lambda a, b: a * 100 / b, "Uma solucao de {a} mol/L com 100 mL foi diluída até {b} mL. Qual e a nova concentracao?"),
        ("termoquimica", "cal", r"Q=m\cdot c\cdot \Delta T", "Q: calor; m: massa; c: calor especifico; ΔT: variacao de temperatura.", 100 + 25 * k, 5 + k, lambda a, b: a * 4 * b, "Qual calor aquece {a} g de material com c = 4 cal/gC em {b} C?"),
        ("estequiometria", "mol", r"n_B=n_A\cdot proporcao", "nA: mol do reagente; nB: mol do produto.", 2 + k, 2, lambda a, b: a * b, "Numa reacao 1 mol de A gera {b} mol de B. Quantos mol de B sao formados a partir de {a} mol de A?"),
        ("densidade", "g/mL", r"d=\frac{m}{V}", "d: densidade; m: massa; V: volume.", 30 + 10 * k, 10 + 2 * k, lambda a, b: a / b, "Uma amostra tem massa {a} g e volume {b} mL. Qual e a densidade?"),
        ("porcentagem em massa", "%", r"C_{m/m}=\frac{m_{soluto}}{m_{solucao}}\cdot100", "C_m/m: percentual em massa; m_soluto: massa do soluto; m_solucao: massa da solucao.", 5 + k, 100 + 20 * k, lambda a, b: a / b * 100, "Uma solucao tem {a} g de soluto em {b} g de solucao. Qual e o percentual em massa?"),
        ("gases ideais", "mol", r"PV=nRT", "P: pressao; V: volume; n: mol; R: constante; T: temperatura.", 1 + k, 2 + k, lambda a, b: a * b / (0.082 * 300), "Um gás ocupa {b} L a {a} atm e 300 K. Use R = 0,082. Quantos mol aproximadamente há?"),
    ]
    tema, unidade, formula, legenda, a, b, conta, texto = formulas[tipo]
    res = conta(a, b)
    correta = f"{_fmt(res)} {unidade}".strip()
    if tipo == 0:
        passos = [_passo("1o Passo", rf"m = {a} g, V = {b} L"), _passo("2o Passo", rf"C = \frac{{{a} g}}{{{b} L}} = {_fmt(res)} g/L"), _passo("Resultado Final", rf"C = {_fmt(res)} g/L", True)]
    elif tipo == 1:
        passos = [_passo("1o Passo", rf"m = {a} g, M = {b} g/mol"), _passo("2o Passo", rf"n = \frac{{{a} g}}{{{b} g/mol}} = {_fmt(res)} mol"), _passo("Resultado Final", rf"n = {_fmt(res)} mol", True)]
    elif tipo == 2:
        passos = [_passo("1o Passo", rf"n = {a} mol, M = {b} g/mol"), _passo("2o Passo", rf"m = {a} mol \cdot {b} g/mol = {_fmt(res)} g"), _passo("Resultado Final", rf"m = {_fmt(res)} g", True)]
    elif tipo == 3:
        passos = [_passo("1o Passo", "O pH depende só da concentração de H+: o volume da amostra não entra na conta."), _passo("2o Passo", rf"[H^+] = 10^{{-{a}}} mol/L"), _passo("3o Passo", rf"O logaritmo devolve o expoente da potencia de dez: \log(10^{{-{a}}}) = -{a}"), _passo("4o Passo", rf"pH = -(-{a}) = {_fmt(res)}"), _passo("Resultado Final", rf"pH = {_fmt(res)}", True)]
    elif tipo == 4:
        passos = [_passo("1o Passo", rf"C_1 = {a} mol/L, V_1 = 100 mL, V_2 = {b} mL"), _passo("2o Passo", rf"C_2 = \frac{{{a} mol/L \cdot 100 mL}}{{{b} mL}} = {_fmt(res)} mol/L"), _passo("Resultado Final", rf"C_2 = {_fmt(res)} mol/L", True)]
    elif tipo == 5:
        passos = [_passo("1o Passo", rf"m = {a} g, c = 4 cal/gC, \Delta T = {b} C"), _passo("2o Passo", rf"Q = {a} g \cdot 4 cal/gC \cdot {b} C = {_fmt(res)} cal"), _passo("Resultado Final", rf"Q = {_fmt(res)} cal", True)]
    elif tipo == 6:
        passos = [_passo("1o Passo", rf"n_A = {a} mol, proporcao = {b}"), _passo("2o Passo", rf"n_B = {a} mol \cdot {b} = {_fmt(res)} mol"), _passo("Resultado Final", rf"n_B = {_fmt(res)} mol", True)]
    elif tipo == 7:
        passos = [_passo("1o Passo", rf"m = {a} g, V = {b} mL"), _passo("2o Passo", rf"d = \frac{{{a} g}}{{{b} mL}} = {_fmt(res)} g/mL"), _passo("Resultado Final", rf"d = {_fmt(res)} g/mL", True)]
    elif tipo == 8:
        passos = [_passo("1o Passo", rf"m_{{soluto}} = {a} g, m_{{solucao}} = {b} g"), _passo("2o Passo", rf"C_{{m/m}} = \frac{{{a} g}}{{{b} g}}\cdot100 = {_fmt(res)}\%"), _passo("Resultado Final", rf"C_{{m/m}} = {_fmt(res)}\%", True)]
    else:
        passos = [_passo("1o Passo", rf"P = {a} atm, V = {b} L, R = 0,082, T = 300 K"), _passo("2o Passo", r"R\cdot T = 0,082\cdot 300 = 24,6"), _passo("3o Passo", rf"n = \frac{{{a}\cdot {b}}}{{24,6}} = {_fmt(res)} mol"), _passo("Resultado Final", rf"n = {_fmt(res)} mol", True)]
    pergunta = _contextualizar_laboratorio(texto.format(a=a, b=b), "Quimica", indice)
    return _payload("Quimica", indice, tema, pergunta, correta, [f"{_fmt(res + 1)} {unidade}".strip(), f"{_fmt(max(0.1, res - 0.5))} {unidade}".strip(), f"{_fmt(res + 2)} {unidade}".strip()], formula, legenda, passos)


def _matematica_ef(indice: int) -> dict[str, Any]:
    tipo, k = indice % 10, indice // 10 + 1
    if tipo == 0:
        total, parte = 80 + 10 * k, 10 + k
        res = total - parte
        return _payload("Matematica", indice, "numeros inteiros e operacoes basicas", f"Uma turma tinha {total} pontos e perdeu {parte}. Com quantos pontos ficou?", str(res), [str(res + 5), str(res - 3), str(total + parte)], r"R=T-P", "T: total inicial; P: pontos perdidos.", [_passo("1o Passo", f"T = {total}, P = {parte}."), _passo("2o Passo", f"R = {total} - {parte} = {res}"), _passo("Resultado Final", f"R = {res}", True)], serie_tipo="EF")
    if tipo == 1:
        numerador, denominador = 1 + k, 4 + k
        return _payload("Matematica", indice, "fracoes e numeros decimais", f"Em uma receita, usa-se {numerador}/{denominador} de uma xicara. Qual fracao representa essa quantidade?", f"{numerador}/{denominador}", [f"{denominador}/{numerador}", f"{numerador}/{denominador + 1}", f"{numerador + 1}/{denominador}"], r"parte/total", "numerador: parte; denominador: total de partes.", [_passo("1o Passo", f"A parte usada e {numerador} de {denominador} partes."), _passo("Resultado Final", f"{numerador}/{denominador}", True)], serie_tipo="EF")
    if tipo == 2:
        valor, taxa = 50 + 10 * k, 5 + k
        desconto = valor * taxa / 100
        final = valor - desconto
        return _payload("Matematica", indice, "porcentagem e desconto", f"Um item custa R$ {valor} e tem desconto de {taxa}%. Qual e o valor final?", f"R$ {_fmt(final)}", [f"R$ {_fmt(desconto)}", f"R$ {_fmt(final + 5)}", f"R$ {_fmt(valor + desconto)}"], r"V_f=V-\frac{p}{100}V", "V: valor inicial; p: percentual.", [_passo("1o Passo", f"Desconto = {taxa}% de {valor} = {_fmt(desconto)}."), _passo("2o Passo", f"Valor final = {valor} - {_fmt(desconto)} = {_fmt(final)}"), _passo("Resultado Final", f"R$ {_fmt(final)}", True)], serie_tipo="EF")
    if tipo == 3:
        a, b, c = 2 + k, 3 + k, 6 + k
        x = b * c / a
        return _payload("Matematica", indice, "regra de tres simples", f"Se {a} cadernos custam R$ {b}, quanto custam {c} cadernos?", f"R$ {_fmt(x)}", [f"R$ {_fmt(x + 2)}", f"R$ {_fmt(max(1, x - 1))}", f"R$ {_fmt(b + c)}"], r"x=\frac{b\cdot c}{a}", "a: quantidade inicial; b: custo inicial; c: nova quantidade.", [_passo("1o Passo", f"a = {a}, b = {b}, c = {c}."), _passo("2o Passo", rf"x = \frac{{{b}\cdot {c}}}{{{a}}} = {_fmt(x)}"), _passo("Resultado Final", f"R$ {_fmt(x)}", True)], serie_tipo="EF")
    if tipo == 4:
        a, b = 3 + k, 7 + k
        x = b - a
        return _payload("Matematica", indice, "equacoes do 1o grau", f"Resolva x + {a} = {b}. Qual e x?", str(x), [str(x + 1), str(a + b), str(max(0, x - 1))], r"x=b-a", "a: termo somado; b: resultado.", [_passo("1o Passo", f"Para deixar x sozinho, tire {a} dos dois lados da igualdade."), _passo("2o Passo", f"x = {b} - {a} = {x}"), _passo("Resultado Final", f"x = {x}", True)], serie_tipo="EF")
    if tipo == 5:
        base, altura = 4 + k, 5 + k
        area = base * altura
        return _payload("Matematica", indice, "areas de figuras planas", f"Um retangulo mede {base} cm por {altura} cm. Qual e sua area?", f"{area} cm^2", [f"{base + altura} cm^2", f"{2 * (base + altura)} cm^2", f"{area + base} cm^2"], r"A=b\cdot h", "b: base; h: altura.", [_passo("1o Passo", f"b = {base}, h = {altura}."), _passo("2o Passo", f"A = {base} * {altura} = {area}"), _passo("Resultado Final", f"{area} cm^2", True)], serie_tipo="EF")
    if tipo == 6:
        lado1, lado2 = 3 + k, 5 + k
        perimetro = 2 * (lado1 + lado2)
        return _payload("Matematica", indice, "perimetro e comprimento", f"Um retangulo tem lados {lado1} m e {lado2} m. Qual e o perimetro?", f"{perimetro} m", [f"{lado1 + lado2} m", f"{lado1 * lado2} m", f"{perimetro + 2} m"], r"P=2(a+b)", "a e b: lados do retangulo.", [_passo("1o Passo", f"a = {lado1}, b = {lado2}."), _passo("2o Passo", f"P = 2 * ({lado1} + {lado2}) = {perimetro}"), _passo("Resultado Final", f"{perimetro} m", True)], serie_tipo="EF")
    if tipo == 7:
        a, b, c = 2 + k, 3 + k, 4 + k
        volume = a * b * c
        return _payload("Matematica", indice, "volume de solidos simples", f"Uma caixa mede {a} cm, {b} cm e {c} cm. Qual e o volume?", f"{volume} cm^3", [f"{a+b+c} cm^3", f"{volume + a} cm^3", f"{2*(a+b+c)} cm^3"], r"V=a\cdot b\cdot c", "a, b e c: dimensoes da caixa.", [_passo("1o Passo", f"Dimensoes: {a}, {b}, {c}."), _passo("2o Passo", f"V = {a} * {b} * {c} = {volume}"), _passo("Resultado Final", f"{volume} cm^3", True)], serie_tipo="EF")
    if tipo == 8:
        a, b = 2 + k, 5 + k
        return _payload("Matematica", indice, "razao e proporcao", f"A razao entre {a} alunos e {b} livros e:", f"{a}/{b}", [f"{b}/{a}", f"{a+b}/{b}", f"{a}/{a+b}"], r"razao=a/b", "a: primeira grandeza; b: segunda grandeza.", [_passo("1o Passo", f"Compare {a} com {b}."), _passo("Resultado Final", f"{a}/{b}", True)], serie_tipo="EF")
    inicio, passo, pos = 2 + k, 2 + k, 5
    valor = inicio + (pos - 1) * passo
    return _payload("Matematica", indice, "sequencias numericas", f"Na sequencia que comeca em {inicio} e aumenta de {passo} em {passo}, qual e o 5o termo?", str(valor), [str(valor + passo), str(valor - passo), str(inicio * pos)], r"a_n=a_1+(n-1)r", "a1: primeiro termo; r: aumento; n: posicao.", [_passo("1o Passo", f"a1 = {inicio}, r = {passo}, n = {pos}."), _passo("2o Passo", f"a5 = {inicio} + 4 * {passo} = {valor}"), _passo("Resultado Final", str(valor), True)], serie_tipo="EF")


def _ciencias_ef(indice: int) -> dict[str, Any]:
    tipo, k = indice % 10, indice // 10 + 1
    if tipo == 0:
        distancia, tempo = 40 + 10 * k, 4 + k
        v = distancia / tempo
        return _payload("Ciencias", indice, "velocidade e movimento", f"Um carrinho percorre {distancia} m em {tempo} s. Qual e sua velocidade media?", f"{_fmt(v)} m/s", [f"{_fmt(v+1)} m/s", f"{_fmt(max(0.1, v-1))} m/s", f"{distancia+tempo} m/s"], r"v=\frac{d}{t}", "d: distancia; t: tempo.", [_passo("1o Passo", f"d = {distancia} m, t = {tempo} s."), _passo("2o Passo", rf"v = \frac{{{distancia}}}{{{tempo}}} = {_fmt(v)}"), _passo("Resultado Final", f"{_fmt(v)} m/s", True)], serie_tipo="EF")
    if tipo == 1:
        massa, acel = 2 + k, 1 + k
        f = massa * acel
        return _payload("Ciencias", indice, "forcas e atrito", f"Um objeto de {massa} kg tem aceleracao de {acel} m/s^2. Qual e a forca aproximada?", f"{f} N", [f"{f+2} N", f"{max(1, f-1)} N", f"{massa+acel} N"], r"F=m\cdot a", "m: massa; a: aceleracao.", [_passo("1o Passo", f"m = {massa}, a = {acel}."), _passo("2o Passo", f"F = {massa} * {acel} = {f}"), _passo("Resultado Final", f"{f} N", True)], serie_tipo="EF")
    if tipo == 2:
        potencia, tempo = 20 + 5 * k, 3 + k
        energia = potencia * tempo
        return _payload("Ciencias", indice, "energia e suas formas", f"Um aparelho de {potencia} W funciona por {tempo} s. Qual energia usa?", f"{energia} J", [f"{energia+10} J", f"{potencia+tempo} J", f"{max(1, energia-5)} J"], r"E=P\cdot t", "P: potencia; t: tempo.", [_passo("1o Passo", f"P = {potencia}, t = {tempo}."), _passo("2o Passo", f"E = {potencia} * {tempo} = {energia}"), _passo("Resultado Final", f"{energia} J", True)], serie_tipo="EF")
    if tipo == 3:
        tensao, resistencia = 12 + k, 3 + k
        corrente = tensao / resistencia
        return _payload("Ciencias", indice, "eletricidade basica", f"Um circuito tem {tensao} V e resistencia de {resistencia} ohm. Qual e a corrente?", f"{_fmt(corrente)} A", [f"{_fmt(corrente+1)} A", f"{_fmt(max(0.1, corrente-0.5))} A", f"{tensao+resistencia} A"], r"i=\frac{U}{R}", "U: tensao; R: resistencia.", [_passo("1o Passo", f"U = {tensao}, R = {resistencia}."), _passo("2o Passo", rf"i = \frac{{{tensao}}}{{{resistencia}}} = {_fmt(corrente)}"), _passo("Resultado Final", f"{_fmt(corrente)} A", True)], serie_tipo="EF")
    if tipo == 4:
        massa, volume = 20 + 5 * k, 4 + k
        dens = massa / volume
        return _payload("Ciencias", indice, "propriedades dos materiais", f"Uma amostra tem massa {massa} g e volume {volume} mL. Qual e a densidade?", f"{_fmt(dens)} g/mL", [f"{_fmt(dens+1)} g/mL", f"{massa+volume} g/mL", f"{_fmt(max(0.1, dens-0.5))} g/mL"], r"d=\frac{m}{V}", "m: massa; V: volume.", [_passo("1o Passo", f"m = {massa}, V = {volume}."), _passo("2o Passo", rf"d = \frac{{{massa}}}{{{volume}}} = {_fmt(dens)}"), _passo("Resultado Final", f"{_fmt(dens)} g/mL", True)], serie_tipo="EF")
    if tipo == 5:
        soluto, volume = 10 + 2 * k, 1 + k
        conc = soluto / volume
        return _payload("Ciencias", indice, "misturas homogeneas e heterogeneas", f"Uma mistura tem {soluto} g de sal em {volume} L de agua. Qual e a concentracao?", f"{_fmt(conc)} g/L", [f"{_fmt(conc+2)} g/L", f"{soluto+volume} g/L", f"{_fmt(max(0.1, conc-1))} g/L"], r"C=\frac{m}{V}", "m: massa de soluto; V: volume.", [_passo("1o Passo", f"m = {soluto}, V = {volume}."), _passo("2o Passo", rf"C = \frac{{{soluto}}}{{{volume}}} = {_fmt(conc)}"), _passo("Resultado Final", f"{_fmt(conc)} g/L", True)], serie_tipo="EF")
    if tipo == 6:
        agua, dias = 2 + k, 5 + k
        total = agua * dias
        return _payload("Ciencias", indice, "agua", f"Uma planta recebe {agua} L de agua por dia durante {dias} dias. Qual o total?", f"{total} L", [f"{total+2} L", f"{agua+dias} L", f"{max(1, total-2)} L"], r"T=a\cdot d", "a: agua por dia; d: dias.", [_passo("1o Passo", f"a = {agua}, d = {dias}."), _passo("2o Passo", f"T = {agua} * {dias} = {total}"), _passo("Resultado Final", f"{total} L", True)], serie_tipo="EF")
    if tipo == 7:
        vacinados, total = 12 + k, 30 + 2 * k
        pct = vacinados / total * 100
        return _payload("Ciencias", indice, "vacinas", f"Em um grupo de {total} pessoas, {vacinados} foram vacinadas. Qual percentual aproximado?", f"{_fmt(pct)}%", [f"{_fmt(pct+5)}%", f"{_fmt(max(1, pct-5))}%", f"{total-vacinados}%"], r"p=\frac{v}{T}\cdot100", "v: vacinados; T: total.", [_passo("1o Passo", f"v = {vacinados}, T = {total}."), _passo("2o Passo", rf"p = \frac{{{vacinados}}}{{{total}}}\cdot100 = {_fmt(pct)}"), _passo("Resultado Final", f"{_fmt(pct)}%", True)], serie_tipo="EF")
    if tipo == 8:
        reciclado, total = 5 + k, 20 + k
        pct = reciclado / total * 100
        return _payload("Ciencias", indice, "reciclagem", f"A turma reciclou {reciclado} kg de um total de {total} kg de residuos. Qual percentual foi reciclado?", f"{_fmt(pct)}%", [f"{_fmt(pct+10)}%", f"{_fmt(max(1, pct-5))}%", f"{total-reciclado}%"], r"p=\frac{r}{T}\cdot100", "r: reciclado; T: total.", [_passo("1o Passo", f"r = {reciclado}, T = {total}."), _passo("2o Passo", rf"p = \frac{{{reciclado}}}{{{total}}}\cdot100 = {_fmt(pct)}"), _passo("Resultado Final", f"{_fmt(pct)}%", True)], serie_tipo="EF")
    entrada, saida = 30 + 3 * k, 10 + k
    saldo = entrada - saida
    return _payload("Ciencias", indice, "ar e poluicao", f"Um filtro reteve {saida} unidades de particulas de um total de {entrada}. Quantas passaram?", str(saldo), [str(saldo+2), str(entrada+saida), str(max(0, saldo-2))], r"P=T-R", "T: total; R: retidas.", [_passo("1o Passo", f"T = {entrada}, R = {saida}."), _passo("2o Passo", f"P = {entrada} - {saida} = {saldo}"), _passo("Resultado Final", str(saldo), True)], serie_tipo="EF")


_GERADORES = {"Matematica": _matematica, "Fisica": _fisica, "Quimica": _quimica}
_GERADORES_EF = {"Matematica": _matematica_ef, "Ciencias": _ciencias_ef}


def _banco_lab(materias: tuple[str, ...], geradores: dict[str, Any]) -> LazyMateriaBank:
    def gerar(materia: str) -> list[dict[str, Any]]:
        gerador = geradores[materia]
        return [gerador(indice) for indice in range(QUESTOES_LAB_POR_MATERIA)]

    return LazyMateriaBank(materias, gerar, fallback="Matematica")


BANCO_LAB_OFFLINE = _banco_lab(MATERIAS_LAB_OFFLINE, _GERADORES)
BANCO_LAB_EF_OFFLINE = _banco_lab(MATERIAS_LAB_EF_OFFLINE, _GERADORES_EF)


def listar_questoes_laboratorio(materia: str, serie_tipo: str = "EM") -> list[dict[str, Any]]:
    materia_norm = normalizar_materia(materia)
    if str(serie_tipo or "").upper() == "EF":
        return deepcopy(BANCO_LAB_EF_OFFLINE.get(materia_norm) or BANCO_LAB_EF_OFFLINE["Matematica"])
    return deepcopy(BANCO_LAB_OFFLINE.get(materia_norm) or BANCO_LAB_OFFLINE["Matematica"])


def gerar_desafio_laboratorio_offline(materia: str, tema: str = "", nivel: str = "", evitar_ids: list[str] | set[str] | tuple[str, ...] | None = None, serie_tipo: str = "EM") -> dict[str, Any]:
    materia_norm = normalizar_materia(materia) or "Matematica"
    tema_busca = str(tema or "").strip()
    if materia_norm == "Matematica" and "escala" in _normalizar_busca(tema_busca) and str(serie_tipo or "").upper() != "EF":
        chave_escala = f"{materia_norm}|escala|{nivel}|{serie_tipo}"
        ciclo = _CICLO_OFFLINE.get(chave_escala, 0)
        _CICLO_OFFLINE[chave_escala] = ciclo + 1
        return _matematica_escala(tema, ciclo)

    banco = BANCO_LAB_EF_OFFLINE if str(serie_tipo or "").upper() == "EF" else BANCO_LAB_OFFLINE
    questoes = banco.get(materia_norm) or banco["Matematica"]
    candidatas = [
        q
        for q in questoes
        if _tema_compativel(materia_norm, tema_busca, str(q.get("tema_usado", "")))
    ] or questoes
    if tema_busca:
        # So o casamento mais direto: nome do tema vence apelido de outro tema.
        melhor = min(_rank_tema(tema_busca, str(q.get("tema_usado", ""))) for q in candidatas)
        candidatas = [
            q for q in candidatas
            if _rank_tema(tema_busca, str(q.get("tema_usado", ""))) == melhor
        ]
    # O nivel pedido passa a ESCOLHER a questao, em vez de so carimbar o rotulo
    # em cima do que saiu (achado 5.6 do QA). O tema continua mandando mais que
    # o nivel: quem escolheu "estequiometria" quer estequiometria, e se esse
    # tema so existir num nivel e ele que vai.
    if nivel:
        no_nivel = [q for q in candidatas if _nivel_normalizado(q.get("dificuldade")) == _nivel_normalizado(nivel)]
        if no_nivel:
            candidatas = no_nivel
    evitar = {str(item) for item in (evitar_ids or []) if str(item).strip()}
    livres = [
        q
        for q in candidatas
        if str(q.get("id_offline", "")) not in evitar and str(q.get("pergunta", "")).strip() not in evitar
    ]
    if livres:
        candidatas = livres
    chave = f"{materia_norm}|{_normalizar_busca(tema_busca)}|{nivel}|{serie_tipo}"
    offset = int(hashlib.sha256(chave.encode("utf-8")).hexdigest(), 16)
    ciclo = _CICLO_OFFLINE.get(chave, 0)
    _CICLO_OFFLINE[chave] = ciclo + 1
    idx = (offset + ciclo) % len(candidatas)
    # Sem carimbar o nivel pedido por cima: quando o tema escolhido so existe
    # em outro nivel, a tela mostra o nivel VERDADEIRO da questao servida, e a
    # pontuacao (que sai da dificuldade) para de premiar um "Dificil" que era
    # uma substituicao direta.
    return deepcopy(candidatas[idx])
