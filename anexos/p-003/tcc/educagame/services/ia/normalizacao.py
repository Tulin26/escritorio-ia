import json
import re
from core.answer_equivalence import conjunto_raizes_quadraticas
from core.marcacao_crua import limpar_marcacao_crua
from core.simbolos import converter_simbolos_latex
from core.text_cleanup import aplicar_acentos_pt


# ====================== LIMPEZA DE TEXTO ======================

def normalizar_texto(t):
    """Limpa espaços extras e caracteres estranhos."""
    if not t:
        return ''
    t = re.sub(r'[^\x00-\x7F\u00C0-\u024F\u0370-\u03FF\u2200-\u22FF'
               r'$\\{}^_\+\-\*\/\=\(\)\[\]\s\.\,\;\:\!\?\'\"\n]', '', str(t))
    t = re.sub(r'([\.,;:!?])(?=[A-Za-zÀ-ÿ0-9\\$])', r'\1 ', t)
    return re.sub(r'\s+', ' ', t).strip()


def _coletar_textos_em_lista(valor) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return []
        try:
            parsed = json.loads(texto)
        except Exception:
            parsed = None
        if parsed is not None and parsed is not valor:
            return _coletar_textos_em_lista(parsed)
        return [linha.strip(" -\t\r") for linha in re.split(r"\n+|(?<=\.)\s+(?=[A-ZÀ-Ý0-9])", texto) if linha.strip()]
    if isinstance(valor, dict):
        partes = []
        if valor.get("titulo"):
            partes.append(str(valor.get("titulo")).strip())
        if valor.get("conteudo"):
            partes.append(str(valor.get("conteudo")).strip())
        return [parte for parte in partes if parte]
    if isinstance(valor, list):
        itens: list[str] = []
        for item in valor:
            itens.extend(_coletar_textos_em_lista(item))
        return itens
    return [str(valor).strip()]


def _extrair_rotulo_alternativa(texto: str) -> tuple[str | None, str]:
    valor = str(texto or "").strip()
    match = re.match(r"^([A-Ea-e])(?:\s*[\)\]\.\:\;\-]\s*|\s+)(.+)$", valor)
    if not match:
        return None, valor
    return match.group(1).upper(), match.group(2).strip()


def limpar_rotulos_alternativas(opcoes: list) -> list[str]:
    itens = [str(opcao) for opcao in (opcoes or [])]
    extraidos = [_extrair_rotulo_alternativa(opcao) for opcao in itens]
    rotulos = [rotulo for rotulo, _ in extraidos if rotulo]
    if len(set(rotulos)) < 2:
        return itens
    return [texto if rotulo else original for original, (rotulo, texto) in zip(itens, extraidos)]


def _normalizar_opcoes_monetarias(pergunta: str, opcoes: list[str]) -> list[str]:
    if "R$" not in str(pergunta or ""):
        return opcoes

    padrao_valor = re.compile(r"^\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*|\d+)(,\d{2})\s*$")
    opcoes_texto = [str(opcao or "").strip() for opcao in opcoes]
    if not any(padrao_valor.match(opcao) for opcao in opcoes_texto):
        return opcoes

    normalizadas: list[str] = []
    for opcao in opcoes_texto:
        match = padrao_valor.match(opcao)
        if match:
            normalizadas.append(f"R$ {match.group(1)}{match.group(2)}")
        else:
            normalizadas.append(opcao)
    return normalizadas


def _normalizar_blocos_explicacao(explicacao) -> list[dict]:
    if explicacao is None:
        return []
    if isinstance(explicacao, str):
        texto = explicacao.strip()
        if not texto:
            return []
        try:
            parsed = json.loads(texto)
        except Exception:
            parsed = None
        if parsed is not None and parsed is not explicacao:
            return _normalizar_blocos_explicacao(parsed)
        return [{"tipo": "texto", "conteudo": texto}]
    if isinstance(explicacao, dict):
        conteudo = str(explicacao.get("conteudo", "")).strip()
        if not conteudo:
            return []
        return [{
            "tipo": str(explicacao.get("tipo", "texto")).strip() or "texto",
            "conteudo": conteudo,
        }]
    if isinstance(explicacao, list):
        blocos: list[dict] = []
        for bloco in explicacao:
            blocos.extend(_normalizar_blocos_explicacao(bloco))
        return blocos
    return [{"tipo": "texto", "conteudo": str(explicacao).strip()}]


def _remover_opcoes_equivalentes(opcoes: list[str], correta: int, pergunta: str = "") -> tuple[list[str], int]:
    opcoes_limpas: list[str] = []
    correta_nova = 0
    vistas: set[object] = set()

    for idx, opcao in enumerate(opcoes or []):
        # A pergunta diz se "(3, 4)" e raiz ou ponto: ver core/answer_equivalence.py.
        raiz = conjunto_raizes_quadraticas(str(opcao), pergunta)
        chave = ("raizes", raiz) if raiz is not None else ("texto", re.sub(r"\s+", " ", str(opcao).strip().lower()))
        if chave in vistas:
            continue
        if idx == correta:
            correta_nova = len(opcoes_limpas)
        vistas.add(chave)
        opcoes_limpas.append(opcao)

    return opcoes_limpas, correta_nova


def _normalizar_passos(passos, explicacao=None) -> list[dict]:
    passos_normalizados: list[dict] = []

    if isinstance(passos, str):
        texto = passos.strip()
        if texto:
            try:
                parsed = json.loads(texto)
            except Exception:
                parsed = None
            if parsed is not None and parsed is not passos:
                passos = parsed
            else:
                passos = [texto]
        else:
            passos = []

    if isinstance(passos, dict):
        passos = [passos]

    if isinstance(passos, list):
        for idx, passo in enumerate(passos, 1):
            if isinstance(passo, dict):
                titulo = str(passo.get("titulo", f"Etapa {idx}")).strip() or f"Etapa {idx}"
                conteudo = str(passo.get("conteudo", "")).strip()
                if conteudo:
                    passos_normalizados.append({
                        "titulo": titulo,
                        "conteudo": conteudo,
                        "final": bool(passo.get("final")),
                    })
            else:
                conteudo = str(passo or "").strip()
                if conteudo:
                    passos_normalizados.append({
                        "titulo": f"Etapa {idx}",
                        "conteudo": conteudo,
                        "final": False,
                    })

    if not passos_normalizados:
        blocos = _normalizar_blocos_explicacao(explicacao)
        textos = []
        resultado_final = None
        for bloco in blocos:
            conteudo = str(bloco.get("conteudo", "")).strip()
            if not conteudo:
                continue
            if bloco.get("tipo") in ("resultado", "final"):
                resultado_final = conteudo
            elif bloco.get("tipo") != "bold":
                textos.append(conteudo)

        for idx, conteudo in enumerate(textos, 1):
            passos_normalizados.append({
                "titulo": f"Etapa {idx}",
                "conteudo": conteudo,
                "final": False,
            })
        if resultado_final:
            passos_normalizados.append({
                "titulo": "Resultado Final",
                "conteudo": resultado_final,
                "final": True,
            })

    return passos_normalizados


def _normalizar_legenda_variaveis(valor) -> str:
    """MELHORIA: a legenda chegava a tela com o comando LaTeX cru --
    "\alpha: angulo agudo procurado" em vez de "alpha" virar a letra.

    A formula logo acima renderiza certo porque passa pelo LaTeX; a legenda
    e texto solto nas tres telas que a desenham (laboratorio.html,
    treino.html e o st.caption do Streamlit), e nenhuma convertia nada.

    Medido: das 50.900 questoes offline, nenhuma legenda tem barra
    invertida -- so as geradas por IA traziam o problema. Por isso a
    correcao mora aqui, na normalizacao da resposta da IA, e nao nas telas:
    um lugar so, e as tres passam a mostrar o simbolo.
    """
    # MELHORIA: a troca por simbolo nao pegava sobrescrito -- "(35^{°})" nao
    # tem barra invertida, e converter_simbolos_latex devolve intacto o que
    # nao tem. A ordem importa: primeiro \circ vira °, depois "^°" vira °.
    from core.simbolos import converter_sobrescritos

    def _texto(parte) -> str:
        return converter_sobrescritos(converter_simbolos_latex(parte))

    if valor is None:
        return ""
    if isinstance(valor, str):
        # MELHORIA: o dicionario ja virava "P: potencia; V: tensao", mas a IA
        # tambem manda a estrutura escrita como TEXTO -- "{'n': 'quantidade de
        # materia'}" -- ou como lista, e as duas chegavam cruas a tela. Visto no
        # log do Laboratorio em 15/09/2026, nas questoes do Hugging Face.
        estrutura = _estrutura_escrita_como_texto(valor)
        if estrutura is not None:
            return _normalizar_legenda_variaveis(estrutura)
        return _texto(valor)
    if isinstance(valor, dict):
        partes = []
        for chave, descricao in valor.items():
            chave_txt = _texto(chave)
            desc_txt = _texto(descricao)
            if chave_txt and desc_txt:
                partes.append(f"{chave_txt}: {desc_txt}")
        return "; ".join(partes)
    if isinstance(valor, (list, tuple)):
        return "; ".join(parte for parte in (_normalizar_legenda_variaveis(item) for item in valor) if parte)
    return _texto(valor)


def _estrutura_escrita_como_texto(texto: str):
    """"{'n': 'mol'}" ou "['a: termo']" -> o dicionario ou a lista; senao None."""
    import ast

    limpo = texto.strip()
    if not ((limpo.startswith("{") and limpo.endswith("}")) or (limpo.startswith("[") and limpo.endswith("]"))):
        return None
    for ler in (json.loads, ast.literal_eval):
        try:
            lido = ler(limpo)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            continue
        if isinstance(lido, (dict, list, tuple)):
            return lido
    return None


def _subformula_auxiliar_valida(texto: str) -> bool:
    texto = str(texto or "").strip()
    if not texto or "=" not in texto:
        return False
    esquerda, direita = [parte.strip() for parte in texto.split("=", 1)]
    if not esquerda or not direita:
        return False
    if re.fullmatch(r"[A-Za-z]", esquerda) and re.fullmatch(r"[A-Za-zÀ-ÿ ]+", direita):
        return False
    return any(token in direita for token in ("\\", "^", "/", "*", "+", "-", "(", ")")) or bool(re.search(r"\d", direita))


_TIPOS_SUPORTE_VALIDOS = {"nenhum", "texto", "tabela"}


def _normalizar_suporte_questao(suporte, modo_ingles: bool = False) -> dict:
    """O campo "suporte": o texto ou a tabela que o enunciado referencia.

    MELHORIA: a IA as vezes escreve "veja a tabela abaixo" ou "no texto a
    seguir" sem nenhum suporte de verdade -- a questao fica logicamente
    impossivel de responder. Relatorio de QA de 23/09/2026 (achado 3.2):
    Escape Room de Ingles citava um "passage" que nunca aparecia na tela, e
    o de Matematica citava uma "tabela" que tambem nao. Este campo da a IA
    onde colocar esse conteudo; _pergunta_cita_suporte_ausente, em
    services/ia/validacao.py, recusa a questao quando o enunciado cita
    suporte e este campo continua vazio -- rede de seguranca para quando a
    instrucao do prompt nao for suficiente.

    So dois tipos: "texto" (uma passagem) e "tabela" (colunas + linhas).
    Grafico fica de fora de proposito -- o prompt instrui a IA a nunca
    escrever questao que dependa de um, porque o sistema so tem como
    renderizar texto e tabela.
    """
    dados = suporte if isinstance(suporte, dict) else {}
    tipo = str(dados.get("tipo") or "nenhum").strip().lower()
    if tipo not in _TIPOS_SUPORTE_VALIDOS:
        tipo = "nenhum"

    titulo = str(dados.get("titulo") or "").strip()
    texto = str(dados.get("texto") or "").strip()

    tabela_bruta = dados.get("tabela") if isinstance(dados.get("tabela"), dict) else {}
    colunas = [str(c).strip() for c in (tabela_bruta.get("colunas") or []) if str(c).strip()]
    linhas = [
        [str(c).strip() for c in linha]
        for linha in (tabela_bruta.get("linhas") or [])
        if isinstance(linha, list) and any(str(c).strip() for c in linha)
    ]

    if not modo_ingles:
        titulo = aplicar_acentos_pt(titulo)
        texto = aplicar_acentos_pt(texto)
        colunas = [aplicar_acentos_pt(coluna) for coluna in colunas]
        linhas = [[aplicar_acentos_pt(celula) for celula in linha] for linha in linhas]

    # Tipo declarado sem o conteudo correspondente nao vale nada -- a
    # validacao trata como se a IA nunca tivesse preenchido o campo.
    if tipo == "texto" and not texto:
        tipo = "nenhum"
    if tipo == "tabela" and (not colunas or not linhas):
        tipo = "nenhum"

    return {
        "tipo": tipo,
        "titulo": titulo,
        "texto": texto if tipo == "texto" else "",
        "tabela": {"colunas": colunas, "linhas": linhas} if tipo == "tabela" else {"colunas": [], "linhas": []},
    }


def normalizar_payload_questao(dados: dict | None, modo_ingles: bool = False) -> dict:
    payload = dict(dados or {})
    # A marcacao crua sai ANTES do acento, e vale tambem no modo de Ingles: o
    # "*should*" do achado 4.4 do QA veio de uma explicacao em ingles. So os
    # campos de PROSA -- formula, subformulas e passos sao LaTeX de verdade e
    # vao para o MathJax (ver core/marcacao_crua.py).
    for campo in ("enigma", "pergunta"):
        if campo in payload:
            payload[campo] = limpar_marcacao_crua(payload[campo])
    if not modo_ingles:
        for campo in (
            "enigma",
            "pergunta",
            "tema_usado",
            "objeto_conhecimento",
            "dificuldade",
            "area_bncc",
            "competencia_bncc",
            "habilidade_bncc",
        ):
            if campo in payload:
                payload[campo] = aplicar_acentos_pt(payload[campo])

    opcoes = payload.get("opcoes", [])
    if not isinstance(opcoes, list):
        opcoes = _coletar_textos_em_lista(opcoes)
    opcoes = [limpar_marcacao_crua(opcao) for opcao in opcoes]
    if not modo_ingles:
        opcoes = [aplicar_acentos_pt(opcao) for opcao in opcoes]
    opcoes = limpar_rotulos_alternativas(opcoes)
    if not modo_ingles:
        opcoes = _normalizar_opcoes_monetarias(str(payload.get("pergunta", "")), opcoes)
    payload["opcoes"] = opcoes

    try:
        payload["correta"] = int(payload.get("correta", 0))
    except Exception:
        payload["correta"] = 0
    opcoes, payload["correta"] = _remover_opcoes_equivalentes(
        opcoes, payload["correta"], str(payload.get("pergunta", "") or "")
    )
    payload["opcoes"] = opcoes

    payload["explicacao"] = _normalizar_blocos_explicacao(payload.get("explicacao"))
    for bloco in payload["explicacao"]:
        if isinstance(bloco, dict) and "conteudo" in bloco:
            bloco["conteudo"] = limpar_marcacao_crua(bloco["conteudo"])
    payload["passos_resolucao"] = _normalizar_passos(payload.get("passos_resolucao"), payload["explicacao"])
    if not modo_ingles:
        for bloco in payload["explicacao"]:
            if isinstance(bloco, dict) and "conteudo" in bloco:
                bloco["conteudo"] = aplicar_acentos_pt(bloco["conteudo"])
        for passo in payload["passos_resolucao"]:
            if isinstance(passo, dict):
                passo["titulo"] = aplicar_acentos_pt(passo.get("titulo", ""))
                passo["conteudo"] = aplicar_acentos_pt(passo.get("conteudo", ""))
    payload["formula"] = str(payload.get("formula") or payload.get("formula_principal") or "").strip()

    subformulas = payload.get("subformulas", [])
    if not isinstance(subformulas, list):
        subformulas = _coletar_textos_em_lista(subformulas)
    payload["subformulas"] = [
        str(item).strip()
        for item in subformulas
        if _subformula_auxiliar_valida(str(item))
    ]
    payload["legenda_variaveis"] = _normalizar_legenda_variaveis(payload.get("legenda_variaveis", ""))
    if not modo_ingles:
        payload["legenda_variaveis"] = aplicar_acentos_pt(payload["legenda_variaveis"])

    payload["suporte"] = _normalizar_suporte_questao(payload.get("suporte"), modo_ingles)

    if modo_ingles:
        opcoes_traducao = payload.get("opcoes_traducao", [])
        if not isinstance(opcoes_traducao, list):
            opcoes_traducao = _coletar_textos_em_lista(opcoes_traducao)
        payload["opcoes_traducao"] = limpar_rotulos_alternativas(opcoes_traducao)
        payload["explicacao_traducao"] = _normalizar_blocos_explicacao(payload.get("explicacao_traducao"))
        payload["passos_resolucao_traducao"] = _normalizar_passos(
            payload.get("passos_resolucao_traducao"),
            payload["explicacao_traducao"],
        )

    return payload
