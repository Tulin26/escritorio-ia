from __future__ import annotations

import json
import os
import random
import re
import time

from core.config import exibir_materia, get_temas_rpg, normalizar_materia
from services import historico_perguntas
from services.banks.em import eh_ensino_medio, gerar_questao_offline_em
from services.banks.fundamental import gerar_questao_offline_ef
from services.ia.fatos_canonicos import fato_canonico_para_tema
from services.ia.ingles import resposta_ingles_offline as _resposta_ingles_offline
from services.ia.normalizacao import normalizar_payload_questao
from services.ia.providers import gerar_json_ia, obter_ultimo_provedor_ia
from services.ia.questoes import finalizar_questao as _finalizar_questao
from services.ia.validacao import observar_questao_gerada, validar_questao_gerada

# Materias em que o Oraculo cobra conceito e o Laboratorio cobra conta.
MATERIAS_EXATAS = frozenset({"Matematica", "Fisica", "Quimica"})


def _orcamento_ia_oraculo_segundos() -> float:
    # MELHORIA: o loop de retry do Oraculo (ate 5 tentativas) chamava
    # gerar_json_ia sem "deadline_seconds", entao cada tentativa usava o
    # orcamento maximo do zero — no pior caso, 5 tentativas podiam somar
    # ate ~130s, bem alem dos 60s do timeout do Gunicorn (visto em producao:
    # SIGKILL apos varias rejeicoes seguidas de "alternativa-correta-
    # inconsistente"). Mesma logica ja usada no Laboratorio
    # (_orcamento_ia_laboratorio_segundos), garantindo um teto de tempo
    # total compartilhado entre todas as tentativas.
    valor = os.getenv("ORACULO_IA_BUDGET_SECONDS")
    if valor is not None:
        try:
            return max(6.0, min(float(valor), 26.0))
        except (TypeError, ValueError):
            pass
    return 22.0


def _resolver_tema_questao(materia_norm: str, ano_escolar: str, tema: str = "") -> str:
    """Escolhe um tema quando o aluno nao pediu um especifico.

    MELHORIA: era "random.choice(temas)" simples, com reposicao -- pedir 30
    questoes de uma materia com 8-10 temas cadastrados sorteava o mesmo tema
    varias vezes so por acaso (relatorio de QA de 23/09/2026, achado 4.5:
    6 questoes de energias renovaveis em 30, 8 questoes sobre instituicoes
    sociais, etc). O historico de PERGUNTAS ja existia (_get_historico_oraculo)
    mas so pega repeticao LITERAL; o problema real e o mesmo assunto
    reescrito com outras palavras.

    Agora e sorteio sem reposicao dentro de uma sessao: guarda os ultimos
    temas escolhidos (por materia/ano) e evita repeti-los ate que todos os
    outros ja tenham saido pelo menos uma vez -- so entao o ciclo reinicia.
    Fora de uma requisicao Flask (scripts, Streamlit fora de sessao) o
    historico nao e gravado, entao cai de volta no sorteio simples.
    """
    tema_digitado = str(tema or "").strip()
    if tema_digitado:
        return tema_digitado

    temas = get_temas_rpg(materia_norm, str(ano_escolar or "")) or ["conteudo geral"]
    if len(temas) <= 1:
        return temas[0]

    chave = f"temas_recentes_{materia_norm}__{ano_escolar}"
    recentes = historico_perguntas.ler(chave)
    disponiveis = [t for t in temas if t not in recentes] or list(temas)
    escolhido = random.choice(disponiveis)
    historico_perguntas.gravar(chave, (recentes + [escolhido])[-(len(temas) - 1):], fora_do_flask=False)
    return escolhido


def _exemplo_curto_nao_exatas(materia: str, tema: str) -> str:
    materia_txt = str(materia or "").strip().lower()
    tema_txt = str(tema or "").strip().lower()

    if materia_txt == "portugues":
        if "regencia" in tema_txt:
            return "Exemplo: em 'Tenho necessidade de ajuda', o nome 'necessidade' pede a preposição 'de'; por isso dizemos 'necessidade de ajuda'."
        if "crase" in tema_txt:
            return "Exemplo: em 'Vou à escola', ocorre crase porque há a preposição 'a' exigida por 'vou' somada ao artigo 'a' de 'a escola'."
        if "concordancia" in tema_txt:
            return "Exemplo: em 'Os alunos estudam', o verbo fica no plural porque concorda com o sujeito 'os alunos'."
        if "sintatic" in tema_txt:
            return "Exemplo: em 'Maria comprou um livro', 'Maria' é o sujeito, 'comprou' é o verbo e 'um livro' é o objeto direto."
        if "figuras de linguagem" in tema_txt:
            return "Exemplo: em 'A cidade acordou cedo', há personificação, pois a cidade recebe uma ação humana."
        if "coesao" in tema_txt or "coerencia" in tema_txt:
            return "Exemplo: em 'João estudou muito. Por isso, foi bem na prova', a expressão 'por isso' liga causa e consequência."
        if "morfologia" in tema_txt:
            return "Exemplo: em 'felizmente', a palavra é formada por 'feliz' + 'mente', criando um advérbio de modo."
        if "interpretacao" in tema_txt:
            return "Exemplo: se o texto diz 'ele saiu apressado porque estava atrasado', a causa da pressa é o atraso."
        return ""

    # MELHORIA: aqui havia um "exemplo" por materia -- "Exemplo: ao estudar
    # {tema}, relacione os principais agentes envolvidos, o contexto da epoca
    # e as consequencias desse processo" em Historia, e parecidos nas outras.
    # Primeiro ele ignorava o tema (citava sempre a Revolucao Industrial);
    # depois passou a citar o tema, mas continuou sendo conselho de gaveta, que
    # serve igual para qualquer questao e nao exemplifica nada. Medido em
    # 13/09/2026: estava em 6 das 14 explicacoes reais do Oraculo. So fica o
    # exemplo CONCRETO (os de Portugues acima); sem ele, nenhum.
    return ""


def _normalizar_texto_dedup(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "").strip().lower())


def _texto_repetido_ou_contido(novo: str, existentes: list[str]) -> bool:
    novo_norm = _normalizar_texto_dedup(novo)
    if not novo_norm:
        return True
    for existente in existentes:
        existente_norm = _normalizar_texto_dedup(existente)
        if not existente_norm:
            continue
        if novo_norm == existente_norm:
            return True
        if len(novo_norm) >= 80 and novo_norm in existente_norm:
            return True
        if len(existente_norm) >= 80 and existente_norm in novo_norm:
            return True
    return False


def _adicionar_texto_unico(destino: list[str], texto: str):
    texto_limpo = str(texto or "").strip()
    if texto_limpo and not _texto_repetido_ou_contido(texto_limpo, destino):
        destino.append(texto_limpo)


def _explicacao_direta_nao_exatas(materia: str, tema: str, pergunta: str, explicacao, passos) -> list[dict]:
    blocos = explicacao if isinstance(explicacao, list) else []
    textos = []

    for bloco in blocos:
        if isinstance(bloco, dict):
            conteudo = str(bloco.get("conteudo", "")).strip()
            if conteudo and bloco.get("tipo") != "bold":
                _adicionar_texto_unico(textos, conteudo)
        else:
            conteudo = str(bloco or "").strip()
            if conteudo:
                _adicionar_texto_unico(textos, conteudo)

    if not textos:
        for passo in passos or []:
            if isinstance(passo, dict):
                conteudo = str(passo.get("conteudo", "")).strip()
                if conteudo:
                    _adicionar_texto_unico(textos, conteudo)

    pergunta_txt = str(pergunta or "").strip()
    tema_txt = str(tema or "este tema").strip()
    materia_txt = str(materia or "este conteúdo").strip()
    # MELHORIA: a materia chegava aqui NORMALIZADA -- "Educacao Fisica",
    # "Matematica", "Portugues" -- e era impressa assim na tela. A chave de
    # normalizacao nao e rotulo: 9 das 14 materias perdem acento nela. E a
    # regra "chave x rotulo" deste projeto, e `exibir_materia` ja existe
    # exatamente para isso.
    materia_visivel = exibir_materia(materia_txt) or materia_txt

    introducao = f"Esta questão trata de {tema_txt} em {materia_visivel}."
    if "renascimento" in tema_txt.lower() or "renascimento" in pergunta_txt.lower():
        introducao = "O Renascimento foi um movimento cultural e intelectual que ganhou força na Itália e valorizou a arte, a ciência e a retomada da cultura clássica."
    if materia_txt.lower() == "portugues":
        pergunta_lower = pergunta_txt.lower()
        if "sintagma nominal" in pergunta_lower and "núcleo" in pergunta_lower:
            trecho = ""
            match = re.search(r"'([^']+)'", pergunta_txt)
            if match:
                trecho = match.group(1)
            if trecho:
                partes = trecho.split()
                nucleo = next((p for p in partes if p.lower() not in {"o", "a", "os", "as", "um", "uma", "uns", "umas"}), "")
                if nucleo:
                    return [
                        {"tipo": "bold", "conteudo": "Núcleo do sintagma nominal"},
                        {"tipo": "texto", "conteudo": f"Um sintagma nominal é um grupo de palavras organizado em torno de um nome. Em '{trecho}', a palavra principal é '{nucleo}'."},
                        {"tipo": "texto", "conteudo": "Os artigos apenas acompanham o substantivo, e palavras como adjetivos acrescentam características, mas não funcionam como núcleo."},
                        {"tipo": "resultado", "conteudo": f"Por isso, o núcleo do sintagma nominal é '{nucleo}', pois ele é o substantivo central da expressão."},
                    ]

    # Sem nada da IA, quem abre e a introducao -- ela ao menos nomeia a
    # materia e o tema. O texto que ficava aqui ("Para responder, e
    # importante identificar a ideia central...") nao dizia nem isso.
    explicacao_principal = textos[0] if textos else introducao
    exemplo = next((texto for texto in textos if "exemplo" in texto.lower()), "")

    # MELHORIA: o molde tinha quatro vagas fixas -- introducao, explicacao,
    # exemplo, complemento -- e enchia as que sobravam com texto de gaveta.
    # Medido numa questao de Educacao Fisica sobre fisiologia do exercicio:
    # 335 dos 650 caracteres na tela (48%) eram molde, e o "exemplo" de
    # gaveta falava de "regras, cooperacao e o objetivo da pratica corporal"
    # numa pergunta sobre ATP e fosfocreatina -- generico a ponto de
    # contradizer o assunto.
    #
    # Pior: das quatro vagas, so DUAS podiam vir da IA (textos[0] e um
    # complemento), entao o terceiro e o quarto paragrafo que ela escreveu
    # eram jogados fora para dar lugar ao molde.
    #
    # Agora o que a IA escreveu tem preferencia, na ordem em que escreveu, e
    # o molde so aparece quando nao ha nada de verdade para mostrar.
    proprios = [
        texto
        for texto in textos[1:]
        if texto != exemplo and not _texto_repetido_ou_contido(texto, [explicacao_principal, exemplo])
    ]

    if not exemplo and len(proprios) < 2:
        exemplo = _exemplo_curto_nao_exatas(materia_txt, tema_txt)

    # `explicacao_principal` ja cai na introducao quando nao ha nada da IA, e
    # `textos` so guarda texto nao vazio -- entao esta lista nunca sai vazia.
    textos_finais: list[str] = []
    for parte in [explicacao_principal, exemplo, *proprios[:3]]:
        _adicionar_texto_unico(textos_finais, parte)

    return [
        {"tipo": "bold", "conteudo": f"Entendendo {tema_txt}"},
        *[{"tipo": "texto", "conteudo": texto} for texto in textos_finais],
    ]


def _questao_pede_resposta_composta(pergunta: str) -> bool:
    texto = str(pergunta or "").strip().lower()
    if not texto:
        return False
    marcadores = [
        "bhaskara",
        "equacao do 2o grau",
        "equação do 2º grau",
        "equacao quadratica",
        "equação quadrática",
        "raizes",
        "raízes",
        "solucoes",
        "soluções",
        "conjunto solucao",
        "conjunto-solucao",
        "conjunto solução",
        "conjunto-solução",
        "valores de x",
        "valor de x",
        "resolva a equacao",
        "resolva a equação",
        "pares ordenados",
        "par ordenado",
        "sistema",
        "sistemas",
        "ordem correta",
        "sequencia correta",
        "sequência correta",
        "associe",
        "associacao correta",
        "associação correta",
        "correspondencia correta",
        "correspondência correta",
        "itens corretos",
        "afirmacoes corretas",
        "afirmações corretas",
        "verdadeiro ou falso",
        "v ou f",
    ]
    if any(marcador in texto for marcador in marcadores):
        return True
    return any(padrao in texto for padrao in ("i, ii", "i, ii e iii"))


def _opcao_parece_resposta_composta(opcao: str) -> bool:
    texto = str(opcao or "").strip().lower()
    if not texto:
        return False
    if any(sinal in texto for sinal in ("{", "}", "s =", "s=", "x'", 'x"', "x''", " e ", "i e ii", "i, ii", "v, f", "f, v")):
        return True
    if re.search(r"\b[ivx]+\b.*\b[ivx]+\b", texto):
        return True
    numeros = re.findall(r"-?\d+(?:[.,]\d+)?", texto)
    if len(numeros) >= 2 and any(separador in texto for separador in ("->", "=>", ";", " / ", " e ")):
        return True
    if len(numeros) >= 2 and "," in texto:
        texto_sem_decimais = re.sub(r"\d,\d", "DECIMAL", texto)
        if "," in texto_sem_decimais:
            return True
    return len(numeros) >= 2 and any(separador in texto for separador in (",", ";", " e ", " / "))


def _questao_resposta_composta_inconsistente(dados: dict) -> bool:
    if not _questao_pede_resposta_composta(dados.get("pergunta", "")):
        return False
    opcoes = dados.get("opcoes", [])
    if not isinstance(opcoes, list) or len(opcoes) != 4:
        return True
    return not any(_opcao_parece_resposta_composta(opcao) for opcao in opcoes)


def _enigma_oracular(materia: str, tema: str) -> str:
    materia_norm = normalizar_materia(materia or "Matematica")
    tema_final = str(tema or "conteudo geral").strip() or "conteudo geral"

    modelos = {
        "Portugues": [
            f"Quando a voz se ergue, nem sempre o nome aparece; decifra o papel oculto em {tema_final}.",
            f"Nas entrelinhas do templo, uma funcao se esconde antes de ser nomeada em {tema_final}.",
        ],
        "Historia": [
            f"O passado nao fala em linha reta; siga os ecos e descubra o sinal de {tema_final}.",
            f"Um pergaminho rasgado sussurra que {tema_final} deixa marcas para quem sabe lê-las.",
        ],
        "Geografia": [
            f"Entre mapas e ventos, a terra muda de rosto para revelar {tema_final}.",
            f"O caminho nao está no mapa inteiro, mas na pista escondida por {tema_final}.",
        ],
        "Ciencias": [
            f"O invisível deixa vestígios; observa com calma o que {tema_final} tentou esconder.",
            f"Nem toda resposta brilha no frasco; algumas surgem do rastro deixado por {tema_final}.",
        ],
        "Biologia": [
            f"A vida raramente anuncia seus segredos; {tema_final} fala apenas a quem observa.",
            f"Entre os sinais mais discretos do vivo, {tema_final} revela sua pista.",
        ],
        "Matematica": [
            f"Os numeros nao mentem, mas tambem nao se entregam; {tema_final} exige decifração.",
            f"O símbolo parece simples, porém guarda o enigma central de {tema_final}.",
        ],
        "Fisica": [
            f"O movimento deixa rastros onde os olhos comuns veem apenas passagem; ali repousa {tema_final}.",
            f"Forcas silenciosas disputam o destino do problema em {tema_final}.",
        ],
        "Quimica": [
            f"No vidro e na fumaça, a materia troca de rosto antes de revelar {tema_final}.",
            f"O frasco nao responde de imediato; primeiro, esconde o segredo de {tema_final}.",
        ],
    }

    # MELHORIA: a primeira frase citava "o Oraculo" -- generico e reaproveitado
    # por Escape Room, RPG e Treino Rapido (todos usam invocar_enigma), o
    # nome do modo errado vazava pro aluno la (visto ao vivo no relatorio
    # de QA de 23/09/2026, achado de interface: "sinais de cidadania" e
    # "sinais de producao artistica" dentro do Escape Room).
    opcoes = modelos.get(materia_norm, [
        f"A resposta nao se mostra de frente; a bruma encobre e revela sinais de {tema_final}.",
        f"Nas brumas do templo, uma pista antiga aponta para {tema_final}.",
    ])
    # MELHORIA: era "return opcoes[0]". Cada materia tem duas frases escritas
    # aqui e so a primeira saia -- 9 das 18 nunca chegaram na tela, e o aluno
    # que pedia varias questoes da mesma materia via o mesmo enigma toda vez.
    return random.choice(opcoes)


# MELHORIA: estes sinais eram procurados como PEDACO DE TEXTO, nao como
# palavra -- "ela " casava dentro de "revela ", "eu " dentro de "museu ",
# "nos " dentro de "alunos ", "tu " dentro de "virtude ". Como o enigma e
# escrito no tom de profecia, "revela" e "desvela" sao das palavras mais
# provaveis de aparecer nele: numa amostra de 10 enigmas bem escritos, 7
# eram descartados por engano e trocados pela frase generica. Era essa a
# causa de o aluno ver quase sempre o mesmo enigma.
#
# Agora casam como palavra inteira. Os sinais em si nao mudaram.
_SINAIS_LITERALIDADE = re.compile(
    r"\b(?:qual\s+[eé]|marque|assinale|escolha|identifique|complete"
    r"|eu|tu|ele|ela|n[oó]s|voc[eê]s)\b"
)


def _enigma_precisa_de_ajuste(enigma: str, pergunta: str) -> bool:
    texto = str(enigma or "").strip().lower()
    pergunta_txt = str(pergunta or "").strip().lower()
    if not texto:
        return True
    if texto == pergunta_txt:
        return True
    if texto.endswith("?"):
        return True
    return bool(_SINAIS_LITERALIDADE.search(texto))


def _serializar_conteudo_textual(valor) -> str:
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list):
        partes = []
        for item in valor:
            if isinstance(item, dict):
                partes.append(str(item.get("titulo", "")))
                partes.append(str(item.get("conteudo", "")))
            else:
                partes.append(str(item))
        return " ".join(parte for parte in partes if parte)
    if isinstance(valor, dict):
        return " ".join(str(v) for v in valor.values())
    return str(valor or "")


# MELHORIA: "observe" era o unico marcador desta lista que TAMBEM e palavra
# inglesa -- "Observe the verb form" e ingles perfeito, e e exatamente o que a
# IA escreve numa explicacao de Ingles. Como a checagem casava por `any`, uma
# palavra bastava: a resposta inteira da IA era descartada e a questao vinha
# do banco offline **em silencio**, sem nem aparecer como rejeicao no log --
# pior que recusar, porque nao havia como notar.
#
# Atinge os QUATRO modos que geram Ingles pela IA (Treino, Oraculo, Escape
# Room e RPG), porque os quatro passam por `invocar_enigma`.
#
# Agora "observe" so conta como portugues quando vem acompanhado de uma
# palavra que nao existe em ingles. As da lista abaixo foram escolhidas por
# isso: "do", "no", "a", "as", "e" e "com" ficaram FORA de proposito, porque
# todas sao palavras inglesas validas.
_MARCADORES_AMBIGUOS = (" observe ",)

_PALAVRAS_SO_PORTUGUESAS = (
    " da ", " das ", " dos ", " na ", " nas ", " nos ", " para ", " que ",
    " uma ", " pelo ", " pela ", " ao ", " aos ", " seu ", " sua ", " isso ",
    " esta ", " essa ", " esse ", " cada ", " sao ", " são ", " frase ",
    " palavra ", " verbo ", " oracao ", " oração ",
)


def _texto_parece_portugues(valor) -> bool:
    texto = _serializar_conteudo_textual(valor).strip().lower()
    if not texto:
        return False

    marcadores_pt = [
        " qual ",
        " questao ",
        " questão ",
        " pergunta ",
        " resposta ",
        " explicacao ",
        " explicação ",
        " traducao ",
        " tradução ",
        " alternativa ",
        " alternativas ",
        " correto ",
        " correta ",
        " passo ",
        " passos ",
        " estrategia ",
        " estratégia ",
        " contexto ",
        " enunciado ",
        " leia ",
        " depois ",
        " porque ",
        " você ",
        " voce ",
        " nao ",
        " não ",
        " em ingles",
        " em inglês",
        " no texto",
        " na frase",
        " vocabulario",
        " vocabulário",
    ]
    texto_busca = f" {texto} "
    if any(marcador in texto_busca for marcador in marcadores_pt):
        return True
    return any(
        marcador in texto_busca for marcador in _MARCADORES_AMBIGUOS
    ) and any(palavra in texto_busca for palavra in _PALAVRAS_SO_PORTUGUESAS)


def _resposta_ingles_principal_esta_em_ingles(dados: dict) -> bool:
    campos_principais = [
        dados.get("enigma", ""),
        dados.get("pergunta", ""),
        dados.get("opcoes", []),
        dados.get("explicacao", []),
        dados.get("passos_resolucao", []),
    ]
    return not any(_texto_parece_portugues(campo) for campo in campos_principais)


def _resposta_ingles_esta_completa(dados: dict) -> bool:
    opcoes = dados.get("opcoes", [])
    opcoes_traducao = dados.get("opcoes_traducao", [])
    return all(
        dados.get(campo)
        for campo in [
            "enigma",
            "enigma_traducao",
            "pergunta",
            "pergunta_traducao",
            "explicacao",
            "explicacao_traducao",
            "passos_resolucao",
            "passos_resolucao_traducao",
        ]
    ) and isinstance(opcoes, list) and isinstance(opcoes_traducao, list) and len(opcoes) == len(opcoes_traducao) and len(opcoes) == 4


def _normalizar_resposta_ingles(dados: dict, tema_final: str) -> dict:
    if not _resposta_ingles_esta_completa(dados):
        return normalizar_payload_questao(_resposta_ingles_offline(tema_final), modo_ingles=True)
    if not _resposta_ingles_principal_esta_em_ingles(dados):
        return normalizar_payload_questao(_resposta_ingles_offline(tema_final), modo_ingles=True)
    return normalizar_payload_questao(dados, modo_ingles=True)


def _normalizar_resposta_nao_exatas(dados: dict, materia_norm: str, tema_final: str) -> dict:
    payload = normalizar_payload_questao(dados)
    payload["passos_resolucao"] = []
    payload["explicacao"] = _explicacao_direta_nao_exatas(
        materia_norm,
        tema_final,
        payload.get("pergunta", ""),
        payload.get("explicacao", []),
        dados.get("passos_resolucao", []),
    )
    return payload


def _montar_questao_offline(
    materia: str, ano_escolar: str, nivel: str, tema: str, evitar_ids: list[str] | None = None
) -> dict:
    materia_norm = normalizar_materia(materia or "Matematica")
    nivel_txt = str(nivel or "Medio")
    tema_final = _resolver_tema_questao(materia_norm, str(ano_escolar or ""), tema)

    if eh_ensino_medio(ano_escolar):
        bruta = gerar_questao_offline_em(materia_norm, tema_final, nivel_txt, evitar_ids=evitar_ids)
        questao = normalizar_payload_questao(bruta, modo_ingles=(materia_norm == "Ingles"))
        questao["id_offline"] = bruta.get("id_offline", "")
        if materia_norm in MATERIAS_EXATAS:
            questao["formula"] = ""
            questao["subformulas"] = []
            questao["legenda_variaveis"] = ""
            questao["passos_resolucao"] = []
        return questao

    bruta = gerar_questao_offline_ef(materia_norm, tema_final, nivel_txt, evitar_ids=evitar_ids)
    questao = normalizar_payload_questao(bruta, modo_ingles=(materia_norm == "Ingles"))
    questao["id_offline"] = bruta.get("id_offline", "")
    questao["formula"] = ""
    questao["subformulas"] = []
    questao["legenda_variaveis"] = ""
    questao["passos_resolucao"] = []
    return questao


def _finalizar_com_origem(questao: dict, nivel_txt: str, origem: str) -> dict:
    payload = dict(questao or {})
    payload["_origem_geracao"] = origem
    return _finalizar_questao(payload, nivel_txt)


def _get_historico_oraculo(chave: tuple) -> list[str]:
    # MELHORIA: sem isso, o Oraculo repetia a mesma questao offline sempre
    # que a IA falhava/estourava o orcamento de tempo pro mesmo
    # materia+tema+nivel (o fallback offline usa um indice deterministico
    # por esses tres valores). Guarda por sessao (mesmo padrao usado no
    # laboratorio, em services/calculo_service.py) as ultimas perguntas/ids
    # ja mostradas pra esse combo, pra rejeitar repeticao tanto da IA quanto
    # do banco offline.
    #
    # Guardado FORA do cookie desde 13/09/2026: ver services/historico_perguntas.py.
    # Fora de uma requisicao Flask o Oraculo nunca guardou historico, e segue sem.
    return historico_perguntas.ler(f"oraculo_hist_{'__'.join(str(item) for item in chave)}")


def _set_historico_oraculo(chave: tuple, historico: list[str]) -> None:
    historico_perguntas.gravar(
        f"oraculo_hist_{'__'.join(str(item) for item in chave)}", historico, fora_do_flask=False
    )


def _prompts_oraculo(
    materia_norm: str, ano_escolar: str, nivel_txt: str, tema_final: str
) -> tuple[str, str]:
    """Monta o par (system, user) que o Oraculo manda para a IA.

    Sao ~85 linhas de texto, e a maior parte de invocar_enigma era isto.
    Separado, da para ler a regra de negocio do loop sem rolar o prompt --
    e da para testar o prompt sozinho, que e onde as regras por materia
    (exatas conceitual, humanas sem passo numerado, ingles bilingue) de
    fato moram.
    """
    system_prompt = (
        "Voce e um gerador de questoes educacionais gamificadas. "
        "Responda somente em JSON valido, sem texto adicional fora do JSON. "
        "Cada questao deve ter exatamente uma alternativa correta. "
        "Se a resposta correta tiver mais de um elemento, toda ela deve aparecer dentro de uma unica alternativa. "
        "O campo enigma deve soar como uma profecia curta, misteriosa e indireta, sem repetir o enunciado da pergunta. "
        "Nao use frases literais do exercicio, nao transforme o enigma em pergunta e nao revele a resposta nele. "
        "A explicacao deve ser pedagogica, clara e realmente ajudar o aluno a entender o motivo da resposta correta. "
        "No Oraculo, questoes de Matematica, Fisica e Quimica devem ser teoricas/conceituais, sem exigir calculo numerico. "
        "Explique o conceito e inclua um exemplo curto, mas deixe calculos com formulas para o Laboratorio de Exatas. "
        "A pergunta conceitual precisa ter uma unica resposta correta e inequivoca: evite perguntas genericas do tipo "
        "'qual conceito e mais apropriado para X', pois varios conceitos diferentes costumam ser validos para o mesmo "
        "tema geral (ex: para analisar um conjunto de dados, tanto moda quanto desvio padrao sao conceitos legitimos, "
        "cada um respondendo a uma pergunta diferente). Em vez disso, descreva um objetivo especifico e concreto que so "
        "um dos conceitos resolve (ex: 'qual medida indica o valor que mais se repete' aponta so para moda; "
        "'qual medida indica o quanto os dados se afastam da media' aponta so para desvio padrao). "
        "Para linguagens e humanas, explique o criterio usado e inclua sempre um exemplo curto e concreto. "
        "Use acentuacao e ortografia correta em portugues brasileiro em todos os campos de texto. "
        "Se a pergunta mencionar um texto, trecho, tabela ou dado 'abaixo'/'a seguir', o campo suporte e "
        "OBRIGATORIO e precisa trazer esse conteudo de verdade (tipo texto com o texto em si, ou tipo tabela "
        "com colunas e linhas preenchidas) -- sem isso a questao fica impossivel de responder. Se a pergunta "
        "nao depende de nenhum suporte, deixe o campo suporte com tipo nenhum. NUNCA escreva uma pergunta que "
        "dependa de um grafico, figura ou imagem: o sistema so consegue exibir texto e tabela. Se o tema pedir "
        "leitura de grafico, descreva os mesmos dados como tabela em vez de mencionar um grafico. "
        "NUNCA escreva as alternativas dentro do campo pergunta (nada como 'A) ... B) ... C) ...'): "
        "as opcoes vao somente no array opcoes, e o enunciado nunca deve citar letra de alternativa."
    )
    user_prompt = f"""
Crie uma questao para:
Materia: {materia_norm}
Ano/serie: {ano_escolar}
Nivel: {nivel_txt}
Tema: {tema_final}

Formato obrigatorio:
{{
  "enigma": "frase curta, misteriosa e indireta, como uma profecia",
  "pergunta": "pergunta objetiva",
  "suporte": {{
    "tipo": "nenhum | texto | tabela",
    "titulo": "titulo curto do suporte, se houver",
    "texto": "o texto/trecho citado pela pergunta, so quando tipo=texto",
    "tabela": {{"colunas": ["Coluna 1", "Coluna 2"], "linhas": [["valor", "valor"]]}}
  }},
  "opcoes": ["A", "B", "C", "D"],
  "correta": 0,
  "explicacao": [
    {{"tipo": "bold", "conteudo": "titulo curto"}},
    {{"tipo": "texto", "conteudo": "explicacao pedagogica, clara e objetiva"}},
    {{"tipo": "resultado", "conteudo": "resultado final ou criterio correto"}}
  ],
  "passos_resolucao": [
    {{"titulo": "1º Passo", "conteudo": "primeiro raciocinio", "final": false}},
    {{"titulo": "2º Passo", "conteudo": "segundo raciocinio", "final": false}},
    {{"titulo": "Resultado Final", "conteudo": "resposta final ou criterio correto", "final": true}}
  ]
  }}

Deixe "suporte" com tipo "nenhum" (e os outros campos do suporte vazios) na
maioria das questoes -- so preencha quando "pergunta" realmente citar um
texto ou uma tabela.
"""

    if materia_norm in MATERIAS_EXATAS:
        user_prompt += """

Regras adicionais para Exatas no Oraculo:
- gere questoes teoricas, conceituais ou de interpretacao;
- nao peça para calcular resultado numerico;
- nao inclua formula, subformulas ou legenda de variaveis;
- nao use passos numerados de resolucao;
- as alternativas devem comparar conceitos, propriedades, interpretacoes ou aplicacoes;
- a explicacao deve dizer por que o conceito correto faz sentido e trazer um exemplo curto sem conta.
"""
    else:
        user_prompt += """

Regras adicionais para Linguagens, Humanas e demais áreas não exatas:
- não use "1º passo", "2º passo" ou sequência mecânica de resolução;
- explique de forma direta, como um professor: o que o conceito significa, qual contexto importa e por que a alternativa correta faz sentido;
- evite repetir o enunciado com outras palavras;
- inclua obrigatoriamente um exemplo curto e concreto, com frase, caso ou situação aplicada ao tema;
- o campo "passos_resolucao" deve vir vazio ou com no máximo um resumo final, sem etapas numeradas.
"""

    user_prompt += f"""

Regra de materia e de nivel:
- a questao tem de cobrar um conceito de {materia_norm}. Tema de atualidades so vale se a pergunta cobrar o conceito da materia sobre ele: numa sala de Fisica, "matriz energetica" tem de perguntar sobre energia, potencia ou rendimento, e nao sobre opiniao ou politica;
- nivel Facil: reconhecer ou aplicar UM conceito de forma direta;
- nivel Medio: exige relacionar dois conceitos ou interpretar uma situacao. Nao vale lista de nomes, data solta, nem media de tres numeros;
- nivel Dificil: exige comparar, justificar ou aplicar o conceito num caso novo;
- os distratores precisam ser do MESMO tipo da resposta certa (se a resposta e uma lei, os outros tres tambem sao leis) e plausiveis para quem estudou -- nada de "uma pedra" ou "um rio" como alternativa de uma questao conceitual;
- as quatro alternativas tem de ter tamanho parecido: a correta nao pode ser a mais longa e detalhada ao lado de tres curtas e absurdas, senao o aluno acerta pelo tamanho sem saber o conteudo;
- o enunciado NAO pode conter a resposta escrita. Se a alternativa correta for "taxa de crescimento natural", a pergunta nao pode terminar com "indicando seu crescimento natural"; se a resposta e uma frase, a pergunta nao pode repetir essa frase.
"""

    user_prompt += """

Regra geral de veracidade:
- nao invente nome proprio: empresa, usina, lei, acordo, bloco economico, obra, povo indigena ou pratica religiosa;
- nao atribua um fato real a lugar, autor, data ou instituicao de que voce nao tenha certeza;
- na duvida, escreva de forma generica (o setor, a regiao, o periodo) em vez de nomear.
"""

    user_prompt += """

Regra geral para respostas compostas:
- quando a resposta correta envolver mais de um item, mais de um valor, uma ordem, uma sequencia, uma associacao ou combinacoes como I e II, mantenha tudo em uma unica alternativa;
- nunca distribua partes da resposta correta em alternativas separadas.
"""

    if materia_norm != "Ingles":
        user_prompt += """

Regra geral de idioma:
- escreva pergunta, opcoes, explicacao e passos_resolucao inteiramente em portugues do Brasil;
- traduza nome de periodo, movimento ou conceito historiografico que tenha equivalente consagrado em portugues (ex.: "Novo Imperialismo", nunca "New Imperialism"; "Guerra Fria", nunca "Cold War"; "Revolucao Cientifica", nunca "Scientific Revolution");
- mantenha no idioma original so o nome proprio de programa, politica ou termo sem traducao consagrada em portugues (ex.: "New Deal", "Big Bang", "laissez-faire", "apartheid").
"""

    if materia_norm == "Ingles":
        user_prompt += """

Regras adicionais para a materia de Ingles:
- escreva enigma, pergunta, opcoes, explicacao e passos_resolucao em ingles;
- inclua tambem traducao para pt-BR nos campos:
  "enigma_traducao", "pergunta_traducao", "opcoes_traducao", "explicacao_traducao", "passos_resolucao_traducao";
- mantenha as opcoes_traducao na mesma ordem das opcoes em ingles;
- nao misture portugues no conteudo principal em ingles.
"""

    fato = fato_canonico_para_tema(tema_final)
    if fato:
        user_prompt += f"\n\n{fato}\n"

    return system_prompt, user_prompt


def _motivo_rejeicao(
    dados, materia_norm: str, contexto: str, historico: tuple[str, ...] | list[str] = ()
) -> tuple[dict, str]:
    """Diz por que esta resposta da IA nao serve. Vazio = serve.

    Devolve tambem o payload, porque a validacao pode corrigir o indice da
    alternativa correta pelo caminho.

    MELHORIA: no Oraculo, as quatro checagens estavam inline no loop, cada
    uma seguida do mesmo trio "marca o provedor, loga, continue -- a menos
    que nao haja provedor, ai break". No Laboratorio, as tres equivalentes
    estavam inline com o mesmo "loga e devolve {}". Sete copias de dois
    desvios, e a mesma politica escrita duas vezes.

    O que de fato muda entre os dois modos e o `contexto` (a validacao cobra
    calculo no laboratorio e aceita questao conceitual no oraculo) e o
    historico de perguntas ja vistas, que so o Oraculo mantem.
    """
    if not isinstance(dados, dict) or not {"pergunta", "opcoes", "correta"}.issubset(dados.keys()):
        return (dados if isinstance(dados, dict) else {}), "payload-incompleto"

    if _questao_resposta_composta_inconsistente(dados):
        return dados, "resposta-composta-inconsistente"

    dados, questao_valida, motivo_validacao = validar_questao_gerada(
        dados, materia_norm, contexto=contexto
    )
    if not questao_valida:
        return dados, motivo_validacao

    assinatura = str(dados.get("pergunta", "")).strip()
    if assinatura and assinatura in historico:
        return dados, "pergunta-repetida"

    return dados, ""


def _normalizar_questao_oraculo(dados: dict, materia_norm: str, tema_final: str) -> dict:
    """Poe a questao no formato que a tela espera, por grupo de materia."""
    if materia_norm == "Ingles":
        return _normalizar_resposta_ingles(dados, tema_final)

    if materia_norm not in MATERIAS_EXATAS:
        return _normalizar_resposta_nao_exatas(dados, materia_norm, tema_final)

    # No Oraculo, exatas e conceitual: conta com formula e passo a passo e o
    # Laboratorio de Exatas.
    questao = normalizar_payload_questao(dados)
    questao["formula"] = ""
    questao["subformulas"] = []
    questao["legenda_variaveis"] = ""
    questao["passos_resolucao"] = []
    return questao


def invocar_enigma(
    materia: str,
    ano_escolar: str,
    nivel: str,
    tema: str = "",
    pular_provedores=None,
):
    materia_norm = normalizar_materia(materia or "Matematica")
    tema_final = _resolver_tema_questao(materia_norm, str(ano_escolar or ""), tema)
    nivel_txt = str(nivel or "Medio")
    chave_historico = (materia_norm, tema_final, nivel_txt)
    historico = _get_historico_oraculo(chave_historico)

    system_prompt, user_prompt = _prompts_oraculo(
        materia_norm, ano_escolar, nivel_txt, tema_final
    )
    max_tokens = 1400 if materia_norm == "Ingles" else 900
    provedores_rejeitados = {str(provedor).strip().lower() for provedor in (pular_provedores or [])}
    inicio_ia = time.monotonic()
    orcamento_ia = _orcamento_ia_oraculo_segundos()

    for _ in range(5):
        restante_ia = orcamento_ia - (time.monotonic() - inicio_ia)
        if restante_ia < 4.0:
            print("[IA] Oraculo atingiu limite de tempo. usando offline...")
            break

        dados = gerar_json_ia(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            pular_provedores=provedores_rejeitados,
            deadline_seconds=restante_ia,
        )
        provedor = obter_ultimo_provedor_ia()

        dados, motivo = _motivo_rejeicao(dados, materia_norm, "oraculo", historico)
        if motivo:
            if not provedor:
                # Sem saber quem respondeu, nao ha quem pular: a proxima
                # tentativa cairia no mesmo provedor e no mesmo erro.
                break
            provedores_rejeitados.add(str(provedor).strip().lower())
            print(f"[IA] {provedor} rejeitado no oraculo: {motivo}")
            continue

        if _enigma_precisa_de_ajuste(dados.get("enigma", ""), dados.get("pergunta", "")):
            dados["enigma"] = _enigma_oracular(materia_norm, tema_final)

        questao = _normalizar_questao_oraculo(dados, materia_norm, tema_final)
        if provedor:
            questao["_provedor_ia"] = provedor
        assinatura = str(dados.get("pergunta", "")).strip()
        _set_historico_oraculo(chave_historico, (historico + [assinatura])[-12:])
        return _finalizar_com_origem(questao, nivel_txt, "ia")

    questao_offline = _montar_questao_offline(
        materia_norm, str(ano_escolar or ""), nivel_txt, tema_final, evitar_ids=historico
    )
    assinatura_offline = str(questao_offline.get("id_offline") or questao_offline.get("pergunta", "")).strip()
    if assinatura_offline:
        _set_historico_oraculo(chave_historico, (historico + [assinatura_offline])[-12:])
    questao = normalizar_payload_questao(questao_offline)
    return _finalizar_com_origem(questao, nivel_txt, "offline")


def _resumo_diagnostico_questao(dados: dict) -> str:
    """
    MELHORIA: antes so logavamos o motivo da rejeicao (ex: "nao-parece-calculo"),
    sem nenhuma pista do que a IA realmente gerou. Isso tornava impossivel saber,
    so pelo log, se a validacao estava certa em rejeitar ou se e ela mesma que
    esta calibrada errado. Este resumo curto (pergunta + resultado final, se
    houver) vai junto do motivo a partir de agora.
    """
    if not isinstance(dados, dict):
        return ""
    pergunta = str(dados.get("pergunta", "") or "").strip().replace("\n", " ")
    resultado_final = ""
    for passo in dados.get("passos_resolucao", []) or []:
        if isinstance(passo, dict) and passo.get("final"):
            resultado_final = str(passo.get("conteudo", "") or "").strip().replace("\n", " ")
            break
    partes = []
    if pergunta:
        partes.append(f"pergunta='{pergunta[:120]}'")
    if resultado_final:
        partes.append(f"resultado='{resultado_final[:80]}'")
    return " | " + ", ".join(partes) if partes else ""


def _resposta_marcada_no_log(dados: dict) -> str:
    """A alternativa marcada como certa, para a linha de observacao."""
    if not isinstance(dados, dict):
        return ""
    opcoes = dados.get("opcoes") or []
    try:
        indice = int(dados.get("correta"))
    except (TypeError, ValueError):
        return ""
    if not (0 <= indice < len(opcoes)):
        return ""
    return f" | resposta='{str(opcoes[indice])[:60]}'"


def questao_para_log(dados) -> str:
    """A questao inteira, em JSON de uma linha, para a linha de rejeicao.

    MELHORIA: o log de rejeicao trazia so a pergunta e o resultado. Na
    investigacao de 14/09/2026 isso travou a medicao: de 22 recusas reais do
    Laboratorio, 11 nao davam para julgar, porque as regras que mais recusam
    (unidade nas alternativas, alternativa inferida) olham as ALTERNATIVAS, e
    elas nao estavam no log. Com a questao inteira, a recusa real vira caso de
    teste sem reconstruir nada.

    Corta cada texto, e nao o JSON, para a linha continuar legivel por
    json.loads. Buscar no Render: "questao={".
    """
    if not isinstance(dados, dict):
        return "{}"

    def curto(valor, limite=200):
        return str(valor if valor is not None else "")[:limite]

    def lista(valor):
        return valor if isinstance(valor, list) else []

    resumo = {
        "pergunta": curto(dados.get("pergunta"), 400),
        "opcoes": [curto(opcao, 80) for opcao in lista(dados.get("opcoes"))[:6]],
        "correta": dados.get("correta"),
        "formula": curto(dados.get("formula")),
        "subformulas": [curto(item) for item in lista(dados.get("subformulas"))[:4]],
        "legenda_variaveis": curto(dados.get("legenda_variaveis")),
        "passos": [
            {"conteudo": curto(passo.get("conteudo")), "final": bool(passo.get("final"))}
            for passo in lista(dados.get("passos_resolucao"))[:8]
            if isinstance(passo, dict)
        ],
        "resultado": [
            curto(bloco.get("conteudo"))
            for bloco in lista(dados.get("explicacao"))[:8]
            if isinstance(bloco, dict) and bloco.get("tipo") in ("resultado", "final")
        ],
    }
    return json.dumps(resumo, ensure_ascii=False, default=str)


def _prompts_laboratorio(
    materia_norm: str, ano_escolar: str, nivel_txt: str, tema_final: str
) -> tuple[str, str]:
    """Monta o par (system, user) que o Laboratorio manda para a IA.

    Sao ~75 linhas de texto, a maior parte de invocar_enigma_laboratorio.
    Separado, as regras por serie ficam visiveis: o Ensino Fundamental
    recebe uma lista propria que PROIBE Bhaskara, PA, PG e trigonometria --
    conteudo de Ensino Medio caindo na tela de um aluno do 7o ano.
    """
    system_prompt = (
        f"Voce e o Alquimista Numerico, especialista em desafios de laboratorio de {materia_norm}. "
        "Responda somente em JSON valido, sem texto fora do JSON. "
        "Gere apenas problemas de calculo numerico com valores explicitos e exatamente uma alternativa correta. "
        "A questao deve obrigar o aluno a substituir numeros em uma formula e efetuar a conta. "
        "Nao gere perguntas teoricas, conceituais, de definicao, identificacao ou classificacao. "
        "Se a conta depender de algum valor de referencia que o aluno nao pode calcular so com os dados do "
        "problema (ex: massa molar de uma substancia, constante fisica, densidade, aceleracao da gravidade), "
        "informe esse valor explicitamente na pergunta ou na legenda_variaveis; nunca deixe implicito que o "
        "aluno ja sabe ou deve consultar esse valor de memoria. Por exemplo, uma questao sobre concentracao molar "
        "de NaCl deve informar a massa molar do NaCl (58,5 g/mol) no proprio enunciado. "
        "O campo formula deve trazer a formula principal em notacao curta e util para st.latex. "
        "O campo subformulas deve vir vazio na maioria dos casos. "
        "Use subformulas apenas quando houver uma formula auxiliar real, como Delta = b^2 - 4ac; "
        "nao use subformulas para explicar variaveis, pois isso pertence a legenda_variaveis. "
        # MELHORIA: as duas frases acima empurram para subformulas vazio, e a
        # IA obedecia ate quando a formula auxiliar era indispensavel. Visto na
        # tela: "triangulo equilatero de lado 12, calcule a area do circulo
        # circunscrito", com formula "A = pi R^2" e legenda citando "a = lado
        # do triangulo" -- sem nenhuma formula ligando a a R. O aluno recebia a
        # area em funcao de um raio que nao tinha como achar.
        "REGRA QUE VENCE AS DUAS ACIMA: toda variavel citada na legenda_variaveis "
        "precisa ter valor dado na pergunta OU aparecer em alguma formula (principal "
        "ou subformula). Se para chegar na formula principal o aluno precisar de uma "
        "relacao que voce nao escreveu (raio do circulo circunscrito a partir do lado, "
        "altura a partir do lado, apotema, conversao de unidade), essa relacao e "
        "OBRIGATORIA em subformulas. Sem ela a questao nao tem como ser resolvida. "
        "Os passos devem ser curtos, objetivos e mostrar a substituicao dos valores. "
        "Cada passo (campo conteudo) deve conter EXATAMENTE uma conta, nunca duas encadeadas. "
        "Se a resolucao exigir calcular um valor auxiliar antes de usar na formula final (razao de uma PA, "
        "diferenca, area parcial, delta de Bhaskara, constante intermediaria etc.), isso e um passo separado, "
        "com seu proprio titulo — nunca junte 'calcular o valor auxiliar' com 'substituir na formula final' na "
        "mesma string de conteudo. Nunca escreva frases de transicao como 'substituir na formula', 'agora "
        "aplicando' ou 'logo' dentro do campo conteudo: o titulo do passo seguinte ja indica essa transicao; o "
        "conteudo em si deve ser só a notacao/conta, sem nenhuma palavra de portugues fora de legenda_variaveis "
        "e titulo. "
        # MELHORIA: esta regra ja existia e a IA a violava assim mesmo, porque o
        # MODELO logo abaixo a contradizia: ele trazia "conteudo": "identificar
        # os valores", que e prosa e e um valor plausivel para o campo. A IA
        # copiava o modelo e anexava a conta -- "identificar os valores a = -2,
        # b = 8, c = 10" --, o texto era classificado como formula e a tela
        # mostrava "identificarosvaloresa = -2". O modelo virou "<...>", que
        # nao se confunde com conteudo.
        "Nunca repita no conteudo o que o titulo do passo ja diz: o titulo e "
        "\"1º Passo\" e o conteudo e \"a = 2, b = -7, c = 3\", nunca "
        "\"identificar os valores a = 2, b = -7, c = 3\"."
    )
    user_prompt = f"""
Crie uma questao de LABORATORIO para:
Materia: {materia_norm}
Ano/serie: {ano_escolar}
Nivel: {nivel_txt}
Tema: {tema_final}

Formato obrigatorio:
{{
  "enigma": "frase curta, misteriosa e indireta",
  "pergunta": "problema numerico com pelo menos dois valores explicitos",
  "opcoes": ["alternativa numerica 1", "alternativa numerica 2", "alternativa numerica 3", "alternativa numerica 4"],
  "correta": 0,
  "formula": "formula principal em LaTeX curto",
  "subformulas": [],
  "legenda_variaveis": "significado de cada variavel",
  "explicacao": [
    {{"tipo": "bold", "conteudo": "titulo curto"}},
    {{"tipo": "texto", "conteudo": "explicacao objetiva do calculo"}},
    {{"tipo": "resultado", "conteudo": "resultado final"}}
  ],
  "passos_resolucao": [
    {{"titulo": "1º Passo", "conteudo": "<SO NOTACAO: os valores dados>", "final": false}},
    {{"titulo": "2º Passo", "conteudo": "<SO NOTACAO: a conta do valor auxiliar, se houver>", "final": false}},
    {{"titulo": "3º Passo", "conteudo": "<SO NOTACAO: a formula final JA COM OS NUMEROS>", "final": false}},
    {{"titulo": "Resultado Final", "conteudo": "<SO NOTACAO: o resultado>", "final": true}}
  ]
}}

Os "<...>" acima sao BURACOS para voce preencher, nunca texto para copiar.
Preenchidos, os quatro passos de uma Bhaskara em 2x^2 - 7x + 3 = 0 ficam:
  1º Passo: "a = 2, b = -7, c = 3"
  2º Passo: "\\Delta = (-7)^2 - 4 \\cdot 2 \\cdot 3 = 25"
  3º Passo: "x = (7 \\pm 5)/(2 \\cdot 2)"     <- NUMEROS, nao letras
  Resultado Final: "x_1 = 3, x_2 = 0,5"      <- rotulado, nunca "-1, 5"

Repare no 3º Passo: ele NAO e "x = (-b \\pm \\sqrt{{\\Delta}})/(2a)". Escrever a
formula com letras nesse passo deixa um buraco entre a formula e o resultado, e
o aluno nao ve de onde sairam os numeros.

E repare no 1º Passo: ele e "a = 2, b = -7, c = 3", NAO "identificar os valores
a = 2, b = -7, c = 3". O que o passo faz ja esta no titulo; repetir no conteudo
gruda a frase na conta e a tela mostra "identificarosvaloresa = 2".

Regras obrigatorias:
- a questao deve ser numerica, nunca teorica;
- a pergunta deve ter valores explicitos;
- a formula deve existir e conter apenas a expressao matematica, sem frase explicativa;
- deixe subformulas vazio quando houver apenas uma formula principal;
- nunca use subformulas para escrever significados como "V = valor original" ou "d = desconto";
- use legenda_variaveis para explicar o significado de cada variavel;
- preencha subformulas apenas se existir formula auxiliar real e indispensavel, por exemplo "\\Delta = b^2 - 4ac";
- ANTES de responder, confira: cada letra citada na legenda_variaveis tem valor na pergunta ou aparece em
  alguma formula? Se alguma nao tem nem uma coisa nem outra, falta uma subformula — escreva-a. Exemplo do
  erro: legenda com "a = lado do triangulo" e "R = raio do circulo circunscrito", formula so "A = \\pi R^2",
  sem nada ligando a a R: o aluno tem o lado, precisa do raio e nao tem como sair de um para o outro;
- o 3o passo mostra a formula final COM OS NUMEROS substituidos, nunca com as letras; a versao com letras ja
  esta no campo formula, repeti-la no passo nao ensina nada e esconde de onde vem o resultado;
- o passo a passo deve mostrar a conta, um calculo por passo — se precisar calcular algo auxiliar antes de
  substituir na formula final (ex: a razao de uma progressao, a diferenca entre dois termos, o delta de
  Bhaskara), use um passo so pra isso e outro passo separado so pra substituicao final; nunca escreva as duas
  contas juntas numa mesma string de conteudo, e nunca inclua frases como "substituir na formula" dentro do
  campo conteudo — isso e o titulo do passo seguinte, nao o conteudo dele;
- em "Resultado Final", escreva apenas a expressao final e o resultado correto; nao comente alternativas erradas;
- quando o Resultado Final tiver DOIS valores, rotule cada um ("x_1 = -1, x_2 = 5" ou "x' = -1 e x'' = 5") e
  nunca escreva so "-1, 5": em portugues a virgula e separador DECIMAL, entao "-1, 5" se le como o numero
  -1,5 e o aluno leva a resposta errada da propria tela de resolucao;
- se a incognita for uma grandeza que nao pode ser negativa (tempo, comprimento, distancia, area, massa,
  quantidade, idade), DESCARTE a raiz negativa no proprio passo a passo e diga em uma expressao curta por que
  ela sai — ex: "t = -1 s (descartada, t > 0); t = 5 s". Apresentar as duas raizes como se ambas valessem
  ensina errado: numa questao de "quando o projetil atinge o solo", t = -1 s nao existe;
- se arredondar, mantenha somente o valor arredondado correto no final, sem dizer que outra opcao seria correta;
- as quatro alternativas devem ser numericas e plausiveis;
- quando a resposta correta tiver dois valores, duas raizes ou um conjunto-solucao, coloque tudo junto em uma unica alternativa, por exemplo "{-1, -1,5}" ou "x' = -1 e x'' = -1,5";
"""

    if eh_ensino_medio(ano_escolar):
        user_prompt += """
- se a materia for Matematica, prefira porcentagem, desconto, area, progressao aritmetica, Bhaskara ou trigonometria;
- se a materia for Fisica, prefira velocidade media, leis de Newton, trabalho ou lei de Ohm;
- se a materia for Quimica, prefira concentracao, pH, mol ou termoquimica.
"""
    else:
        user_prompt += """
Regras curriculares para Ensino Fundamental:
- gere conteudo adequado ao 6o, 7o, 8o ou 9o ano informado;
- se a materia for Matematica, prefira numeros inteiros, fracoes, decimais, porcentagem, regra de tres simples, equacao do 1o grau, area, perimetro, volume simples, razao, proporcao, graficos e tabelas;
- se a materia for Ciencias, prefira velocidade simples, forcas basicas, energia, eletricidade basica, densidade, concentracao simples, agua, vacinas, reciclagem e saude;
- nao use progressao aritmetica, progressao geometrica, PA, PG, Bhaskara, equacao do 2o grau, trigonometria, logaritmos, matrizes ou determinantes para Ensino Fundamental.
"""

    return system_prompt, user_prompt


def invocar_enigma_laboratorio(
    materia: str,
    ano_escolar: str,
    nivel: str,
    tema: str = "",
    pular_provedores=None,
    deadline_seconds=None,
):
    materia_norm = normalizar_materia(materia or "Matematica")
    tema_final = _resolver_tema_questao(materia_norm, str(ano_escolar or ""), tema)
    nivel_txt = str(nivel or "Medio")

    system_prompt, user_prompt = _prompts_laboratorio(
        materia_norm, ano_escolar, nivel_txt, tema_final
    )

    dados = gerar_json_ia(
        system_prompt,
        user_prompt,
        max_tokens=1500,
        pular_provedores=pular_provedores,
        deadline_seconds=deadline_seconds,
    )
    provedor = obter_ultimo_provedor_ia()

    dados, motivo = _motivo_rejeicao(dados, materia_norm, "laboratorio")
    if motivo:
        # Devolver {} e o contrato: quem insiste e o calculo_service, que
        # chama de novo pulando este provedor.
        if provedor:
            print(
                f"[IA] {provedor} rejeitado no laboratorio: "
                f"{motivo}{_resumo_diagnostico_questao(dados)} | questao={questao_para_log(dados)}"
            )
        return {}

    if _enigma_precisa_de_ajuste(dados.get("enigma", ""), dados.get("pergunta", "")):
        dados["enigma"] = _enigma_oracular(materia_norm, tema_final)

    questao = normalizar_payload_questao(dados)

    # MELHORIA: regra nova entra primeiro so registrando (ver
    # observar_questao_gerada). A questao segue para o aluno, e o log diz
    # quantas vezes a regra teria recusado -- e qual questao, para conferir
    # uma a uma se ela acertou. Buscar no log do Render: "observacao no
    # laboratorio".
    #
    # Olha a questao JA normalizada, e nao a resposta crua da IA: e ela que o
    # aluno ve. Um passo que a normalizacao descarte some da tela, e a regra
    # tem de ver o mesmo buraco que o aluno.
    #
    # Nunca pode custar a questao: um erro aqui vira linha de log, nao {}.
    try:
        observacoes = observar_questao_gerada(questao, "laboratorio")
    except Exception as exc:
        observacoes = []
        print(f"[IA] observacao do laboratorio falhou ({type(exc).__name__}): {exc}")
    for observacao in observacoes:
        print(
            f"[IA] {provedor or 'IA'} observacao no laboratorio (questao aceita): "
            f"{observacao}{_resumo_diagnostico_questao(questao)}{_resposta_marcada_no_log(questao)}"
        )

    if provedor:
        questao["_provedor_ia"] = provedor
    return _finalizar_com_origem(questao, nivel_txt, "ia")
