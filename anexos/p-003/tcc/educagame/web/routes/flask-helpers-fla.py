from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from copy import deepcopy

from flask import request, session

from core.config import exibir_materia, get_materias_por_serie, normalizar_materia
from core.origem_questao import AVISO_BANCO_PROPRIO, aviso_de_origem
from core.text_cleanup import aplicar_acentos_pt
from core.utils import formatar_unidades_texto, preparar_formula_latex
from services.dados_service import (
    buscar_aluno_por_id,
    buscar_alunos,
    carregar_estado_temporario,
    carregar_progresso_rpg,
    limpar_caches_de_pontos,
    remover_estado_temporario,
    remover_progresso_rpg,
    salvar_estado_temporario,
    salvar_progresso_rpg,
)
from repositories.meta_repo import registrar_conclusao
from services.historico_perguntas import id_estado_sessao


# MELHORIA: o formulario de resposta mandava so o INDICE da alternativa
# ("resposta=2"), sem nada que dissesse a QUE questao aquele indice pertencia,
# e a rota comparava o indice com a questao guardada no estado NAQUELE
# instante. Se a questao guardada trocasse entre o desenho da tela e o envio
# -- pagina velha reenviada, botao voltar, duas abas --, o indice 2 do que o
# aluno viu era lido como o indice 2 de OUTRA questao: ele perdia ponto tendo
# acertado. Foi o achado 3.4 do relatorio de QA de 23/09/2026 (uma ocorrencia
# vista no Escape Room, nao reproduzida na hora).
#
# A assinatura sai sempre da questao GUARDADA, nos dois momentos (ao desenhar
# e ao receber), e nunca do texto renderizado: acento, LaTeX e espaco mudam na
# apresentacao e fariam a comparacao falhar numa resposta legitima.
AVISO_QUESTAO_TROCADA = (
    "Esta resposta era de uma questão que já tinha saído da tela, então ela não foi contada "
    "— nem como acerto, nem como erro. Responda a questão que está aqui agora."
)


def assinatura_da_questao(questao) -> str:
    """Identifica a questao que estava na tela. Vazio quando nao ha questao."""
    if not isinstance(questao, dict) or not (
        questao.get("pergunta") or questao.get("opcoes") or questao.get("alternativas")
    ):
        return ""
    base = json.dumps(
        [
            str(questao.get("pergunta", "")),
            # O ENEM e a Batalha chamam a lista de "alternativas".
            [str(opcao) for opcao in (questao.get("opcoes") or questao.get("alternativas") or [])],
            str(questao.get("correta", "")),
        ],
        ensure_ascii=False,
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def resposta_veio_de_outra_questao(questao) -> bool:
    """Se a resposta enviada e de uma questao que ja saiu da tela.

    Sem assinatura no formulario a resposta e aceita como antes: e a pagina
    que ja estava aberta quando esta versao subiu, e tirar o ponto dela seria
    punir o aluno por um deploy.
    """
    enviada = str(request.form.get("assinatura_questao", "")).strip()
    atual = assinatura_da_questao(questao)
    return bool(enviada) and bool(atual) and enviada != atual


def _id_estado_sessao() -> str:
    # Um id so para a questao em andamento e para os historicos de perguntas
    # (services/historico_perguntas.py): o logout apaga este id, e os dois
    # saem juntos.
    return id_estado_sessao()


def _chave_estado(nome: str) -> str:
    return f"{_id_estado_sessao()}:{nome}"


def obter_estado_flask(nome: str, padrao=None):
    estado = carregar_estado_temporario(_chave_estado(nome))
    if estado is not None:
        return deepcopy(estado)
    return deepcopy(padrao)


def salvar_estado_flask(nome: str, estado) -> None:
    salvar_estado_temporario(_chave_estado(nome), estado)


def limpar_estado_flask(nome: str) -> None:
    remover_estado_temporario(_chave_estado(nome))


def nome_estado_por_aluno(nome: str) -> str:
    escola_id = str(session.get("escola_id") or "sem_escola")
    aluno_id = str(session.get("aluno_id") or request.form.get("aluno_id") or "sem_aluno")
    return f"{nome}:{escola_id}:{aluno_id}"


def carregar_estado_persistido(nome: str, progresso_id: str, padrao=None):
    estado = obter_estado_flask(nome, None)
    if estado:
        return estado

    escola_id = session.get("escola_id")
    aluno_id = session.get("aluno_id")
    if not escola_id or not aluno_id:
        return deepcopy(padrao)

    salvo = carregar_progresso_rpg(str(escola_id), str(aluno_id), progresso_id)
    estado_salvo = salvo.get("estado") if isinstance(salvo, dict) else None
    if isinstance(estado_salvo, dict):
        salvar_estado_flask(nome, estado_salvo)
        return deepcopy(estado_salvo)
    return deepcopy(padrao)


def salvar_estado_persistido(nome: str, progresso_id: str, estado) -> None:
    salvar_estado_flask(nome, estado)
    escola_id = session.get("escola_id")
    aluno_id = session.get("aluno_id")
    if escola_id and aluno_id:
        salvar_progresso_rpg(str(escola_id), str(aluno_id), progresso_id, estado, origem="flask")


def limpar_estado_persistido(nome: str, progresso_id: str) -> None:
    limpar_estado_flask(nome)
    escola_id = session.get("escola_id")
    aluno_id = session.get("aluno_id")
    if escola_id and aluno_id:
        remover_progresso_rpg(str(escola_id), str(aluno_id), progresso_id)


def materias_para_template(materias: tuple[str, ...] | list[str]) -> list[dict[str, str]]:
    materias_ef = set(get_materias_por_serie("6o Ano"))
    materias_em = set(get_materias_por_serie("1o Ano EM"))
    return [
        {
            "valor": materia,
            "label": exibir_materia(materia),
            "permitida_ef": normalizar_materia(materia) in materias_ef,
            "permitida_em": normalizar_materia(materia) in materias_em,
        }
        for materia in materias
    ]


def _formatar_notacao_matematica_texto(texto: str) -> str:
    saida = str(texto or "")
    saida = re.sub(
        r"\blog_([A-Za-z0-9]+)\(([^)]+)\)",
        lambda match: f"log base {match.group(1)} de {match.group(2)}",
        saida,
    )
    saida = re.sub(
        r"\b([A-Za-z])\^([A-Za-z0-9]+)\b",
        lambda match: f"{match.group(1)} elevado a {match.group(2)}",
        saida,
    )
    return re.sub(r"[ \t]+", " ", saida).strip()


def texto_explicacao(explicacao) -> str:
    if isinstance(explicacao, list):
        partes = []
        for bloco in explicacao:
            if isinstance(bloco, dict):
                conteudo = str(bloco.get("conteudo", "") or "").strip()
            else:
                conteudo = str(bloco or "").strip()
            if conteudo:
                partes.append(conteudo)
        return _limpar_rotulos_explicacao(_formatar_notacao_matematica_texto(aplicar_acentos_pt("\n\n".join(partes))))
    return _limpar_rotulos_explicacao(_formatar_notacao_matematica_texto(aplicar_acentos_pt(str(explicacao or ""))))


def passos_para_template(passos) -> list[dict]:
    r"""Os passos da resolucao prontos para a tela: prosa e formula separadas.

    A formula vai entre `$$` (MathJax) e a prosa passa por `formula_html` no
    template. Era o miolo de rpg_fla._preparar_passos_resolucao, igual ao do
    Laboratorio; mora aqui para o ENEM e a Batalha usarem o MESMO preparo.

    MELHORIA: a questao do ENEM e da Batalha que vem do banco do Laboratorio
    ja trazia os passos, mas a tela mostrava so a explicacao -- e a do banco e
    a frase de gaveta "Identifique as grandezas, substitua os valores na
    formula e confira a unidade final" (3 das 4 questoes reais de 13/09/2026).
    Mostrar os passos como TEXTO nao servia: sao escritos em LaTeX
    ("P = \frac{8}{100}\cdot 160"), e 1.220 das 2.235 questoes do ENEM
    chegariam com o comando cru na tela -- medido antes de publicar.
    """
    from core.formula_formatting import formatar_formula_passo_latex, separar_texto_formula_passo

    preparados = []
    for passo in passos or []:
        if not isinstance(passo, dict):
            continue
        conteudo = str(passo.get("conteudo", "") or "").strip()
        texto_passo, formula_passo = separar_texto_formula_passo(conteudo)
        formula_passo = re.sub(r"\s+e\s+(?=[A-Za-z]\s*=)", ", ", formula_passo).strip().rstrip(".")
        preparados.append(
            {
                "titulo": aplicar_acentos_pt(str(passo.get("titulo", "Etapa") or "Etapa")),
                "conteudo": aplicar_acentos_pt(conteudo),
                # o passo que sobra como PROSA tambem carrega conta no meio
                # ("(x - 4)^2"); sem isto o expoente chega cru.
                "conteudo_texto": expoentes_em_sobrescrito(aplicar_acentos_pt(texto_passo)),
                "conteudo_latex": formatar_formula_passo_latex(formula_passo) if formula_passo else "",
                "final": bool(passo.get("final")),
            }
        )
    return preparados


def explicacao_sem_frase_generica(questao: dict):
    """A explicacao sem a frase de gaveta do Laboratorio, quando ha passos no lugar."""
    from services.banks.laboratorio import EXPLICACAO_GENERICA_LAB

    explicacao = questao.get("explicacao")
    tem_passos = any(isinstance(p, dict) and str(p.get("conteudo", "") or "").strip() for p in questao.get("passos_resolucao") or [])
    if not tem_passos or not isinstance(explicacao, list):
        return explicacao
    # Pela chave sem acento: no ENEM a explicacao ja passou por
    # _normalizar_textos_questao, e "formula" chega como "fórmula".
    from core.text_cleanup import chave_busca

    generica = chave_busca(EXPLICACAO_GENERICA_LAB)
    return [bloco for bloco in explicacao if not (isinstance(bloco, dict) and chave_busca(bloco.get("conteudo", "")) == generica)]


def _limpar_rotulos_explicacao(texto: str) -> str:
    saida = str(texto or "")
    saida = re.sub(
        r"(?im)^\s*Quest[aã]o\s+autoral\s*(?:\(([^)]+)\))?\s*\.?\s*$",
        lambda match: f"Habilidade BNCC: {match.group(1)}" if match.group(1) else "",
        saida,
    )
    saida = re.sub(r"\n{3,}", "\n\n", saida)
    return saida.strip()


def aluno_travado_id() -> str:
    """Id do aluno quando quem entrou e o proprio aluno (senao, string vazia).

    MELHORIA: o aluno_id vinha do formulario/URL e sobrescrevia a sessao,
    entao um aluno ja autenticado trocava de identidade so escolhendo outro
    nome no seletor -- e passava a jogar, pontuar e ver o desempenho no
    lugar do colega. Isso fazia sentido quando nao havia login (entrava-se
    pelo slug da escola, um codigo compartilhado pela turma); com usuario e
    senha, quem e aluno fica preso a propria conta. Professor e
    desenvolvedor seguem com o seletor, porque precisam abrir a tela de um
    aluno especifico para acompanhar a turma.
    """
    if session.get("usuario_role") != "aluno":
        return ""
    return str(session.get("aluno_id") or "")


def sincronizar_aluno_da_requisicao():
    # O id do proprio aluno tem prioridade sobre o que veio no formulario:
    # nao adianta forjar outro aluno_id no POST.
    aluno_id = aluno_travado_id() or request.form.get("aluno_id") or session.get("aluno_id")
    if not aluno_id:
        return None

    aluno = buscar_aluno_por_id(str(aluno_id))
    if not aluno:
        return None

    session["aluno_id"] = aluno.get("id") or aluno_id
    session["aluno_nome"] = aluno.get("nome", "")
    session["ano_escolar"] = aluno.get("ano_escolar", "")
    return aluno


def alunos_para_selecao() -> list[dict]:
    escola_id = session.get("escola_id")
    if not escola_id:
        return []
    alunos = buscar_alunos(escola_id)
    travado = aluno_travado_id()
    if travado:
        return [a for a in alunos if str(a.get("id")) == travado]
    return alunos


def contexto_aluno_template() -> dict[str, str]:
    return {
        "aluno_id": session.get("aluno_id", ""),
        "aluno_nome": session.get("aluno_nome", ""),
        "ano_escolar": session.get("ano_escolar", "1º EM"),
        "escola_nome": session.get("escola_nome", ""),
        # O template mostra o nome fixo em vez do seletor (ver
        # partials/student_selector.html). A tranca de verdade e no servidor.
        "aluno_travado": bool(aluno_travado_id()),
    }


_MODOS_LABEL = {
    "treino": "Treino Rápido",
    "oraculo": "Oráculo",
    "laboratorio": "Laboratório de Exatas",
    "rpg": "RPG",
    "escape_room": "Escape Room",
    "enem": "ENEM",
    "boss_rush_enem": "Batalha de Chefes",
    "boss_rush": "Batalha de Chefes",
}


def exibir_modo(modo: str) -> str:
    # MELHORIA: o campo "modo" grava o nome tecnico da rota que gerou o log
    # (ex: "treino-flask"), as vezes sem o sufixo "-flask" em registros mais
    # antigos ("treino"). Sem normalizar, "Por modo" mostrava o mesmo modo
    # duas vezes (uma com sufixo, outra sem) e o historico exibia o nome cru
    # pro usuario. Aqui os dois formatos caem no mesmo rotulo amigavel.
    chave = str(modo or "").strip().lower().removesuffix("-flask")
    if not chave:
        return ""
    return _MODOS_LABEL.get(chave, chave.replace("_", " ").title())


def latex(valor: str) -> str:
    return preparar_formula_latex(str(valor or ""))


# MELHORIA: o expoente cru no enunciado ja tinha sido caçado duas vezes,
# sempre acrescentando UM formato ao padrao que vira LaTeX: primeiro a equacao
# com "= n", depois a expressao quadratica sozinha. Visto no RPG, um terceiro:
#
#     A funcao f(x) = (x - 4)^2 + 5 tem vertice em qual ponto?
#
# O quadrado da binomial nao casa com nenhum dos dois (o "^2" vem depois de
# ")", nao de "x"), e o "^2" chegava cru na tela.
#
# Perseguir formato por formato nao termina. Isto e a rede embaixo: o que
# sobrar com "^n" vira sobrescrito de verdade. Nao substitui o LaTeX -- uma
# equacao reconhecida continua indo para o MathJax, que fica bem melhor --,
# mas garante que nada chegue ao aluno com acento circunflexo no meio da
# conta.
_SOBRESCRITO = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "-": "⁻", "+": "⁺",
}

# So depois de algo que possa ser base: letra, digito ou fecha-parentese.
# E so digitos depois do "^" -- "10^{-3}" (LaTeX, com chave) fica de fora de
# proposito, porque quem cuida dele e o padrao de pH logo abaixo.
_EXPOENTE_CRU = re.compile(r"(?<=[\w\)\]])\^([+-]?\d+)")


def expoentes_em_sobrescrito(texto: str) -> str:
    return _EXPOENTE_CRU.sub(
        lambda m: "".join(_SOBRESCRITO[c] for c in m.group(1)), str(texto or "")
    )


def formatar_texto_simples_pergunta(texto: str) -> str:
    texto = str(texto or "")
    texto = re.sub(r"\b(\d+)o grau\b", r"\1º grau", texto, flags=re.IGNORECASE)
    texto = texto.replace("formula", "fórmula")
    texto = texto.replace("equacoes", "equações")
    texto = texto.replace("equacao", "equação")
    texto = texto.replace("qual e", "qual é")
    # MELHORIA: o enunciado chegava ao aluno com o expoente cru ("Qual e a
    # area em m^2?") enquanto as alternativas do Laboratorio ja vinham
    # formatadas ("48 m²") -- as duas coisas na mesma tela. O MathJax nao
    # resolve isso: ele so processa o que esta entre delimitadores, e o
    # "m^2" do texto corrido fica de fora.
    # MELHORIA: o enunciado vinha do banco offline em ASCII e so recebia as
    # poucas trocas manuais acima -- "peca", "expressao" e "quadratica"
    # chegavam cruas ao aluno, ao lado de palavras ja acentuadas na mesma
    # frase. O dicionario de core/text_cleanup ja resolvia isso no resto do
    # app; faltava chamar aqui.
    texto = aplicar_acentos_pt(texto)
    return expoentes_em_sobrescrito(formatar_unidades_texto(texto))


def formatar_pergunta_exatas(pergunta: str) -> dict[str, str]:
    texto = formatar_texto_simples_pergunta(pergunta).strip()

    def _limpar_sufixo_formula(valor: str) -> str:
        valor = str(valor or "").strip()
        valor = valor.lstrip(" .,;:")
        return valor

    padrao_ph = re.compile(
        r"\[H\+\]\s*=\s*10\^\{+\s*(-?\d+)\s*\}+(\s*mol/L)?",
        flags=re.IGNORECASE,
    )
    match_ph = padrao_ph.search(texto)
    if match_ph:
        expoente = match_ph.group(1)
        unidade = r"\,\mathrm{mol/L}" if match_ph.group(2) else ""
        prefixo = texto[: match_ph.start()].strip().rstrip(" ,.;:")
        pergunta_texto = texto[match_ph.end():].strip().lstrip(" ,.;:")
        return {
            "texto": prefixo or "Se",
            "latex": rf"[H^+] = 10^{{{expoente}}}{unidade}",
            "sufixo": _limpar_sufixo_formula(pergunta_texto),
        }

    # MELHORIA: o "=<numero>" no fim era obrigatorio, entao so EQUACAO virava
    # LaTeX. Quando os enunciados do banco passaram a descrever a grandeza
    # pela EXPRESSAO ("a largura segue a expressao 2x^2 - 2x - 24"), nada
    # casava e a linha inteira saia como texto puro, com o "^" cru na tela.
    # Agora o "= n" e opcional: expressao quadratica sozinha tambem e formula.
    padrao_equacao = re.compile(
        r"([+-]?\s*\d*\s*x\s*(?:\^2|²)\s*(?:[+-]\s*\d*\s*x\s*)?(?:[+-]\s*\d+\s*)(?:=\s*-?\d+)?)(\?)?",
        flags=re.IGNORECASE,
    )
    match = padrao_equacao.search(texto)
    if not match:
        return {"texto": texto, "latex": "", "sufixo": ""}

    equacao = match.group(1).replace("²", "^2")
    equacao = re.sub(r"\b1x", "x", equacao)
    pergunta_texto = texto[: match.start()].strip()
    pergunta_texto = pergunta_texto.rstrip(" ,.;:")
    sufixo = _limpar_sufixo_formula(texto[match.end():])
    if match.group(2):
        equacao = f"{equacao}?"
    elif sufixo == "?":
        equacao = f"{equacao}?"
        sufixo = ""
    return {
        "texto": pergunta_texto,
        "latex": latex(equacao),
        "sufixo": sufixo,
    }


def aviso_offline(entidade: dict, tipo: str = "questao", aviso_atual: str = "") -> str:
    """O aviso de que a questão veio do banco próprio.

    MELHORIA: a frase morava aqui, e o Streamlit tinha a dele -- duas versões
    do mesmo recado, e uma terceira no ENEM, que virou uma pílula escrita
    "offline". Agora o texto e a decisão moram em core/origem_questao.py, que
    os dois frontends usam.

    O parâmetro `tipo` ("questao"/"desafio") deixou de mudar a frase: ele só
    servia para escolher entre "uma questão válida" e "um desafio válido", e
    a mensagem nova não fala nem de um nem de outro -- fala do que o aluno
    precisa saber, que é poder responder normalmente. Continua aceito para
    não quebrar as quatro chamadas que já existem.
    """
    # MELHORIA: aqui havia uma peneira, e ela deixava passar quase tudo. Só a
    # redação antiga ("A IA não retornou ... offline") virava a frase do
    # aluno; qualquer outra caía num `return texto` e ia crua para a tela.
    #
    # Eram SEIS textos para o mesmo estado -- três em services/ia/providers.py
    # (indisponível, limite de uso, autenticação), um em services/rpg_service.py,
    # um dentro da própria rota do Laboratório, e este. Foi assim que
    # "IA indisponivel no momento. Usando banco de questoes local." -- sem
    # acento e em jargão nosso -- apareceu na tela de um aluno.
    #
    # A distinção entre cota, autenticação e indisponibilidade não se perde:
    # ela continua inteira em `obter_ultimo_erro_ia()`, que é o que o painel
    # do ADM mostra ao desenvolvedor. Ela só não vai mais para o aluno, para
    # quem as três significam a mesma coisa: responda, vale pontos igual.
    #
    # Qualquer aviso presente já quer dizer "a IA não entregou" -- o erro é
    # limpo a cada sucesso (providers.py:463 e 582), então não há risco de um
    # erro velho avisar numa questão boa.
    if aviso_atual:
        return AVISO_BANCO_PROPRIO
    return aviso_de_origem(entidade)


def pontuacao_por_dificuldade(dificuldade: str) -> int:
    texto = unicodedata.normalize("NFKD", str(dificuldade or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    if "dificil" in texto or texto.startswith("dif"):
        return 30
    if "facil" in texto:
        return 10
    return 20


def perda_pontuacao_por_dificuldade(dificuldade: str) -> int:
    texto = unicodedata.normalize("NFKD", str(dificuldade or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    if "dificil" in texto or texto.startswith("dif"):
        return 15
    if "facil" in texto:
        return 5
    return 10


def registrar_pontuacao_acerto(aluno_id: str | None, acertou: bool, dificuldade: str) -> int:
    """Quantos pontos esta resposta vale -- o numero que a tela mostra.

    MELHORIA: esta funcao tambem SOMAVA os pontos na tabela alunos, e o
    gatilho `trg_atualizar_pontos` somava de novo quando o log era gravado,
    linhas antes, na mesma rota. O Streamlit ja confiava so no gatilho, e
    avisava por escrito que somar no app "causaria double-count".

    Quem soma agora e so o banco, pela MESMA tabela de pontuacao_por_dificuldade
    e perda_pontuacao_por_dificuldade (o SQL repete os valores, e
    tests/test_pontos_so_no_banco.py prende os dois juntos). Aqui fica o calculo
    para a tela e a renovacao dos caches de ranking.
    """
    pontos = pontuacao_por_dificuldade(dificuldade) if acertou else -perda_pontuacao_por_dificuldade(dificuldade)
    if not aluno_id:
        return 0
    limpar_caches_de_pontos()
    return pontos


def registrar_partida_concluida(modo: str, historico) -> bool:
    """Grava que uma partida de Escape Room, Batalha ou RPG chegou ao fim.

    A meta semanal conta PARTIDA nesses três modos, não questão (ver
    core/metas.py), e partida concluída não existia em lugar nenhum: o
    `historico` mora no estado da sessão, que é sobrescrito quando a próxima
    corrida começa. Aqui vira uma linha própria, com quantas o aluno acertou.

    Perder também conclui: quem ficou sem vidas na Batalha jogou a partida
    inteira. O que não conta é abandonar no meio -- estas três chamadas ficam
    só nos ramos que encerram a corrida de verdade.
    """
    itens = list(historico or [])
    return registrar_conclusao(
        str(session.get("aluno_id") or ""),
        str(session.get("escola_id") or ""),
        modo,
        acertos=sum(1 for item in itens if isinstance(item, dict) and item.get("acertou")),
        total=len(itens),
    )


def tempo_resposta(estado: dict) -> float | None:
    inicio = estado.get("tempo_inicio")
    if not isinstance(inicio, (int, float)):
        return None
    return max(0.0, time.time() - float(inicio))


def calcular_percentual(acertos: int, total: int) -> int:
    return int(acertos / total * 100) if total else 0


def resumo_historico(historico: list[dict]) -> dict:
    total = len(historico)
    acertos = sum(1 for item in historico if item.get("acertou"))
    return {"total": total, "acertos": acertos, "percentual": calcular_percentual(acertos, total)}
