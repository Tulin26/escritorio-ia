from __future__ import annotations

from dataclasses import dataclass
import random
import unicodedata
from typing import Any

from core.config import FASES_TOTAIS_RPG, eh_ensino_medio, exibir_materia, get_temas_rpg, normalizar_materia
from core.text_cleanup import aplicar_acentos_pt, chave_busca
from services.ia.normalizacao import normalizar_payload_questao
from services.ia.questoes import embaralhar_opcoes_questao
from services.ia_service import gerar_json_ia, invocar_enigma, obter_ultimo_erro_ia
from services.banks.rpg import gerar_questao_rpg_offline


FASES_TOTAIS = FASES_TOTAIS_RPG


STORY_PRESETS = {
    "Matematica": {
        "antagonista": "Mestre Vesper, o arquiteto das contas impossiveis",
        "objetivo": "recuperar o Compasso Real antes que a masmorra distorca todas as medidas",
        "ameaca": "os corredores mudam de escala sempre que alguem aceita um resultado sem conferir",
        "reliquia": "Compasso Real",
        "segredo": "as salas obedecem a proporcoes escondidas nas escolhas do grupo",
    },
    "Fisica": {
        "antagonista": "Dama Inercia, guardia das maquinas paradas",
        "objetivo": "reativar o nucleo de movimento preso no fundo da torre",
        "ameaca": "forcas invisiveis travam portas, pontes e elevadores antigos",
        "reliquia": "Nucleo de Movimento",
        "segredo": "cada mecanismo responde a uma grandeza fisica ignorada",
    },
    "Quimica": {
        "antagonista": "Alquimista Vesper, senhor dos reagentes instaveis",
        "objetivo": "selar o caldeirao de vidro antes que a torre entre em reacao",
        "ameaca": "vapores mudam o estado das salas e confundem pistas verdadeiras com residuos",
        "reliquia": "Ampola de Equilibrio",
        "segredo": "as portas só reconhecem evidencias, nao aparencias",
    },
    "Historia": {
        "antagonista": "Cronista Sem Rosto, falsificador das memorias",
        "objetivo": "restaurar o arquivo original antes que as fontes sejam reescritas",
        "ameaca": "registros incompletos tentam convencer a equipe de uma unica versao dos fatos",
        "reliquia": "Selo da Memoria",
        "segredo": "cada sala preserva uma fonte que contradiz a anterior",
    },
    "Portugues": {
        "antagonista": "Editora do Silencio, senhora dos textos cortados",
        "objetivo": "recuperar a pagina central que organiza o labirinto",
        "ameaca": "frases mudam de intencao quando sao lidas fora de contexto",
        "reliquia": "Pagina Viva",
        "segredo": "o labirinto fala por genero, publico e finalidade",
    },
    "Ciencias": {
        "antagonista": "Diretor Vesper, colecionador de respostas sem prova",
        "objetivo": "acender o farol experimental no alto da escola subterranea",
        "ameaca": "hipoteses falsas ganham forma quando ninguem pede evidencia",
        "reliquia": "Farol Experimental",
        "segredo": "a masmorra muda quando uma conclusao e testada de verdade",
    },
}


DESTINOS = {
    "Conhecimento": {
        "icone": "📚",
        "titulo": "Arquiteto do Conhecimento",
        "descricao": "Voce avanca analisando pistas, conectando conceitos e transformando estudo em poder.",
    },
    "Estrategia": {
        "icone": "♟️",
        "titulo": "Tatico da Masmorra",
        "descricao": "Seu progresso vem de planejamento, leitura de cenario e decisoes bem calculadas.",
    },
    "Coragem": {
        "icone": "🛡️",
        "titulo": "Guardiao Audaz",
        "descricao": "Voce enfrenta riscos, aprende sob pressao e cresce em cada confronto.",
    },
    "Cooperacao": {
        "icone": "🤝",
        "titulo": "Lider de Aliancas",
        "descricao": "Seu caminho fica mais forte ao unir recursos, apoio e empatia em cada fase.",
    },
}


ROTAS = [
    {
        "rota": "Galeria dos Ecos",
        "texto": "Investigar os simbolos antigos gravados nas paredes.",
        "foco": "interpretacao de pistas",
        "recurso": "Mapa parcial da masmorra",
        "impacto": "Conhecimento",
        "destino": "Descoberta guiada",
        "risco": "baixo",
    },
    {
        "rota": "Ponte das Engrenagens",
        "texto": "Ajustar o mecanismo central para abrir uma nova passagem.",
        "foco": "planejamento e logica",
        "recurso": "Chave mecanica",
        "impacto": "Estrategia",
        "destino": "Vantagem tatica",
        "risco": "medio",
    },
    {
        "rota": "Camara Rubra",
        "texto": "Cruzar a area protegida antes que as defesas despertem.",
        "foco": "resolucao sob pressao",
        "recurso": "Escudo runico",
        "impacto": "Coragem",
        "destino": "Impulso heroico",
        "risco": "alto",
    },
    {
        "rota": "Sala dos Companheiros",
        "texto": "Convencer aliados locais a compartilhar recursos e informacoes.",
        "foco": "colaboracao e escuta",
        "recurso": "Kit de suporte",
        "impacto": "Cooperacao",
        "destino": "Alianca duradoura",
        "risco": "baixo",
    },
]

ROTAS.extend(
    [
        {
            "rota": "Arquivo das Runas",
            "texto": "Comparar registros antigos para descobrir qual deles continua confiavel.",
            "foco": "análise de evidencias",
            "recurso": "Lente de verificacao",
            "impacto": "Conhecimento",
            "destino": "Memoria decifrada",
            "risco": "medio",
        },
        {
            "rota": "Observatorio Subterraneo",
            "texto": "Usar o mapa celeste da masmorra para prever a proxima mudanca do caminho.",
            "foco": "leitura de padroes",
            "recurso": "Astrolabio escolar",
            "impacto": "Estrategia",
            "destino": "Rota antecipada",
            "risco": "baixo",
        },
        {
            "rota": "Forja das Evidencias",
            "texto": "Testar uma hipotese sob pressao antes que o mecanismo esfrie.",
            "foco": "validacao de conclusoes",
            "recurso": "Martelo de prova",
            "impacto": "Coragem",
            "destino": "Prova sob risco",
            "risco": "alto",
        },
        {
            "rota": "Jardim dos Simbolos",
            "texto": "Interpretar sinais de culturas diferentes sem apagar seus significados.",
            "foco": "contexto e respeito",
            "recurso": "Caderno de campo",
            "impacto": "Cooperacao",
            "destino": "Pacto de escuta",
            "risco": "baixo",
        },
        {
            "rota": "Torre do Debate",
            "texto": "Defender uma conclusao diante de vozes que apresentam contraexemplos.",
            "foco": "argumentacao",
            "recurso": "Selo de coerencia",
            "impacto": "Conhecimento",
            "destino": "Argumento firme",
            "risco": "medio",
        },
        {
            "rota": "Sala dos Mapas Vivos",
            "texto": "Reordenar caminhos que mudam conforme as escolhas feitas pela equipe.",
            "foco": "planejamento adaptativo",
            "recurso": "Bussola de retorno",
            "impacto": "Estrategia",
            "destino": "Atalho revelado",
            "risco": "medio",
        },
        {
            "rota": "Poco das Consequencias",
            "texto": "Descer ate uma memoria instavel para recuperar uma pista perdida.",
            "foco": "aprendizado com erro",
            "recurso": "Corda de seguranca",
            "impacto": "Coragem",
            "destino": "Resgate arriscado",
            "risco": "alto",
        },
        {
            "rota": "Mesa dos Pactos",
            "texto": "Dividir tarefas entre aliados para juntar pistas que fazem sentido apenas em conjunto.",
            "foco": "cooperacao estrategica",
            "recurso": "Insignia do grupo",
            "impacto": "Cooperacao",
            "destino": "Alianca coordenada",
            "risco": "medio",
        },
    ]
)


def _rng(*parts: Any) -> random.Random:
    seed = "|".join(str(part) for part in parts)
    return random.Random(seed)


def _risco_idx(risco: str) -> int:
    return {"baixo": 0, "medio": 1, "alto": 2}.get(str(risco or "").lower(), 1)


def _chave_tema(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    return base.encode("ascii", "ignore").decode("ascii").lower().strip()


def _serie_em(serie: str) -> bool:
    return eh_ensino_medio(serie)


def _ordenar_temas_matematica_rpg(temas: list[str], serie: str) -> list[str]:
    if not _serie_em(serie):
        return temas
    temas_unicos = list(dict.fromkeys(temas))
    temas_bhaskara = [
        tema
        for tema in temas_unicos
        if any(token in _chave_tema(tema) for token in ("bhaskara", "2o grau", "segundo grau"))
    ]
    outros = [tema for tema in temas_unicos if tema not in temas_bhaskara]
    return outros + temas_bhaskara


def _selecionar_tema_desafio(
    materia: str,
    serie: str,
    temas_usados: list[str] | None,
    jornada: dict[str, Any] | None,
    opcao: dict[str, Any] | None,
) -> str:
    temas = get_temas_rpg(materia, serie) or ["conteudo geral"]
    if materia == "Matematica":
        temas = _ordenar_temas_matematica_rpg(temas, serie)

    usados = {_chave_tema(item) for item in (temas_usados or []) if str(item).strip()}
    candidatas = [tema for tema in temas if _chave_tema(tema) not in usados] or temas
    escolhas = len((jornada or {}).get("escolhas", []) or [])
    rota = str((opcao or {}).get("rota", ""))
    offset = _rng("tema-rpg", materia, serie, rota).randrange(len(candidatas)) if candidatas else 0
    return candidatas[(len(usados) + escolhas + offset) % len(candidatas)]


def _usar_teoria_exatas_rpg(temas_usados: list[str] | None, jornada: dict[str, Any] | None) -> bool:
    if not isinstance(jornada, dict):
        return False
    total_desafios = len(temas_usados or [])
    escolhas = len((jornada or {}).get("escolhas", []) or [])
    return (total_desafios + escolhas) % 2 == 0


def _remover_campos_calculo(payload: dict[str, Any]) -> None:
    payload["passos_resolucao"] = []
    payload["formula"] = ""
    payload["subformulas"] = []
    payload["legenda_variaveis"] = ""


def _criar_story_state(materia: str = "Ciencias", titulo: str = "") -> dict[str, Any]:
    materia_norm = normalizar_materia(materia or "Ciencias")
    preset = STORY_PRESETS.get(materia_norm, STORY_PRESETS["Ciencias"])
    titulo_txt = str(titulo or _titulo_padrao(materia_norm))
    return {
        "campanha": titulo_txt,
        "materia": materia_norm,
        "antagonista": preset["antagonista"],
        "objetivo": preset["objetivo"],
        "ameaca": preset["ameaca"],
        "reliquia": preset["reliquia"],
        "segredo": preset["segredo"],
        "tensao": 1,
        "cicatriz": "o pulso do portal inicial ainda vibra atras da equipe",
        "ultimo_ganho": "o mapa inicial revelou que a masmorra reage ao raciocinio do grupo",
        "tom": "aventura escolar sombria, clara e heroica",
    }


def _story_state(jornada: dict[str, Any] | None, materia: str = "Ciencias", titulo: str = "") -> dict[str, Any]:
    jornada = jornada or {}
    story = jornada.get("story_state")
    base = _criar_story_state(materia or (story or {}).get("materia") or "Ciencias", titulo or (story or {}).get("campanha") or "")
    if isinstance(story, dict):
        base.update({chave: valor for chave, valor in story.items() if valor not in (None, "")})
    return base


def criar_jornada_inicial(materia: str = "Ciencias", titulo: str = "") -> dict[str, Any]:
    return {
        "placar": {chave: 0 for chave in DESTINOS},
        "trilhas": [],
        "recursos": [],
        "focos": [],
        "escolhas": [],
        "story_state": _criar_story_state(materia, titulo),
    }


def resumir_jornada(jornada: dict[str, Any] | None) -> dict[str, Any]:
    jornada = jornada or criar_jornada_inicial()
    placar = jornada.get("placar") or {}
    dominante = max(DESTINOS, key=lambda chave: int(placar.get(chave, 0)))
    destino = DESTINOS[dominante]
    # MELHORIA: as opcoes passavam por aplicar_acentos_pt mas o resumo nao,
    # entao no mesmo painel liam-se "Câmara Rubra" e, logo abaixo, "Tatico da
    # Masmorra" e "Voce avanca". O placar mantem a CHAVE sem acento (e ela
    # que indexa DESTINOS e o placar salvo na jornada) e ganha um rotulo
    # separado so para exibicao.
    return {
        "icone": destino["icone"],
        "titulo": aplicar_acentos_pt(destino["titulo"]),
        "descricao": aplicar_acentos_pt(destino["descricao"]),
        "placar": {chave: int(placar.get(chave, 0)) for chave in DESTINOS},
        "rotulos_placar": {chave: aplicar_acentos_pt(chave) for chave in DESTINOS},
        "trilhas": list(jornada.get("trilhas") or []),
        "recursos": list(jornada.get("recursos") or []),
        "focos": list(jornada.get("focos") or []),
        "story_state": _story_state(jornada),
    }


def obter_efeitos_risco(opcao: dict[str, Any] | None) -> dict[str, Any]:
    risco = str((opcao or {}).get("risco", "medio")).lower()
    tabela = {
        "baixo": {"xp_base": 20, "hp_perda": 8},
        "medio": {"xp_base": 30, "hp_perda": 14},
        "alto": {"xp_base": 45, "hp_perda": 20},
    }
    return {"risco": risco, **tabela.get(risco, tabela["medio"])}


def obter_efeitos_escolha(opcao: dict[str, Any] | None, jornada: dict[str, Any] | None, fase_atual: int) -> dict[str, Any]:
    opcao = opcao or {}
    jornada = jornada or criar_jornada_inicial()
    impacto = _chave_destino(opcao.get("impacto_destino", "Estrategia"))
    bonus_destino = int((jornada.get("placar") or {}).get(impacto, 0)) * 2
    risco = obter_efeitos_risco(opcao)
    chance_base = 84 - (_risco_idx(risco["risco"]) * 12) + min(10, fase_atual // 2) + min(12, bonus_destino)
    chance_sucesso = max(40, min(95, chance_base))
    xp_imediato_sucesso = 8 + (_risco_idx(risco["risco"]) * 4)
    hp_perda_falha = 4 + (_risco_idx(risco["risco"]) * 6)
    xp_bonus_desafio = 0 if risco["risco"] == "baixo" else 8 if risco["risco"] == "medio" else 15
    return {
        "chance_sucesso": chance_sucesso,
        "xp_imediato_sucesso": xp_imediato_sucesso,
        "hp_perda_falha": hp_perda_falha,
        "xp_bonus_desafio": xp_bonus_desafio,
    }


def resolver_tentativa_acao(opcao: dict[str, Any] | None, jornada: dict[str, Any] | None, fase_atual: int) -> dict[str, Any]:
    opcao = opcao or {}
    efeitos = obter_efeitos_escolha(opcao, jornada, fase_atual)
    rolagem = _rng(opcao.get("id"), opcao.get("rota"), fase_atual, (jornada or {}).get("escolhas")).randint(1, 100)
    sucesso = rolagem <= efeitos["chance_sucesso"]
    return {
        "sucesso": sucesso,
        "rota": opcao.get("rota", "rota desconhecida"),
        "chance_sucesso": efeitos["chance_sucesso"],
        "rolagem": rolagem,
        "xp_imediato": efeitos["xp_imediato_sucesso"] if sucesso else 0,
        "hp_perda_imediata": 0 if sucesso else efeitos["hp_perda_falha"],
        "xp_bonus_desafio": efeitos["xp_bonus_desafio"],
        "bonus_risco_ativo": sucesso,
        "texto_resultado": "deu_certo" if sucesso else "falhou",
    }


def registrar_escolha_jornada(jornada: dict[str, Any] | None, opcao: dict[str, Any] | None, fase_atual: int) -> dict[str, Any]:
    base = criar_jornada_inicial()
    if isinstance(jornada, dict):
        base.update(jornada)
        base["placar"] = {chave: int((jornada.get("placar") or {}).get(chave, 0)) for chave in DESTINOS}
        base["trilhas"] = list(jornada.get("trilhas") or [])
        base["recursos"] = list(jornada.get("recursos") or [])
        base["focos"] = list(jornada.get("focos") or [])
        base["escolhas"] = list(jornada.get("escolhas") or [])
        base["story_state"] = _story_state(jornada)

    opcao = opcao or {}
    impacto = _chave_destino(opcao.get("impacto_destino", "Estrategia"))
    if impacto in base["placar"]:
        base["placar"][impacto] += 1

    if opcao.get("rota"):
        base["trilhas"].append(str(opcao["rota"]))
        base["trilhas"] = base["trilhas"][-6:]
    if opcao.get("recurso"):
        base["recursos"].append(str(opcao["recurso"]))
        base["recursos"] = base["recursos"][-6:]
    if opcao.get("foco_aprendizado"):
        base["focos"].append(str(opcao["foco_aprendizado"]))
        base["focos"] = base["focos"][-6:]

    base["escolhas"].append(
        {
            "fase": fase_atual,
            "rota": opcao.get("rota", ""),
            "impacto": impacto,
        }
    )
    base["escolhas"] = base["escolhas"][-12:]

    story = _story_state(base)
    rota = str(opcao.get("rota") or "rota desconhecida")
    recurso = str(opcao.get("recurso") or story.get("reliquia") or "recurso")
    foco = str(opcao.get("foco_aprendizado") or "decisao")
    impacto_txt = _chave_destino(opcao.get("impacto_destino") or "Estrategia")
    consequencias = {
        "Conhecimento": f"uma inscrição {_com_artigo(rota, 'em')} revelou uma regra secreta ligada a {foco}",
        "Estrategia": f"o uso {_com_artigo(recurso, 'de')} abriu um atalho, mas tambem chamou a atencao do antagonista",
        "Coragem": f"a passagem {_com_artigo(rota, 'por')} deixou uma marca instavel que ainda pode cobrar um preco",
        "Cooperacao": f"um aliado {_com_artigo(rota, 'de')} prometeu ajuda se o grupo provar que entendeu {foco}",
    }
    story["tensao"] = min(5, int(story.get("tensao", 1) or 1) + (1 if opcao.get("risco") == "alto" else 0))
    story["cicatriz"] = consequencias.get(impacto_txt, f"{_com_artigo(rota)} mudou a masmorra de forma visivel")
    story["ultimo_ganho"] = f"O grupo carrega {_com_artigo(recurso)} e uma pista de {foco} para a fase {fase_atual + 1}."
    base["story_state"] = story
    return base


def deve_gerar_desafio(fase_atual: int, opcao: dict[str, Any] | None) -> bool:
    risco = str((opcao or {}).get("risco", "medio")).lower()
    return risco != "baixo" or fase_atual % 2 == 1 or fase_atual >= FASES_TOTAIS - 2


@dataclass
class CenaRpg:
    titulo: str
    local_atual: str
    narracao: str
    opcoes: list[dict[str, Any]]
    evento: str = "exploracao"

    def as_dict(self) -> dict[str, Any]:
        return {
            "titulo": self.titulo,
            "local_atual": self.local_atual,
            "narracao": self.narracao,
            "opcoes": self.opcoes,
            "evento": self.evento,
        }


def _historia_recente(historico: list[dict[str, Any]] | None, limite: int = 3) -> str:
    eventos = []
    for item in (historico or [])[-limite:]:
        rota = str(item.get("rota") or item.get("acao") or "").strip()
        status = str(item.get("status") or "").strip().lower()
        if rota:
            eventos.append(f"{rota} ({status})" if status else rota)
    return ", ".join(eventos)


def _resumo_memoria(jornada: dict[str, Any] | None, historico: list[dict[str, Any]] | None) -> dict[str, str]:
    jornada = jornada or criar_jornada_inicial()
    trilhas = list(jornada.get("trilhas") or [])
    recursos = list(jornada.get("recursos") or [])
    focos = list(jornada.get("focos") or [])
    story = _story_state(jornada)
    return {
        "ultima_rota": trilhas[-1] if trilhas else "Portal da Masmorra",
        "recurso": recursos[-1] if recursos else "mapa inicial",
        "foco": focos[-1] if focos else "observacao cuidadosa",
        "historico": _historia_recente(historico),
        "antagonista": story.get("antagonista", ""),
        "objetivo": story.get("objetivo", ""),
        "ameaca": story.get("ameaca", ""),
        "reliquia": story.get("reliquia", ""),
        "segredo": story.get("segredo", ""),
        "cicatriz": story.get("cicatriz", ""),
        "ultimo_ganho": story.get("ultimo_ganho", ""),
        "tensao": str(story.get("tensao", 1)),
    }


# MELHORIA: os moldes injetavam os nomes crus e saia "Forcar entrada em
# Camara Rubra usando Escudo runico e protegendo mapa inicial" -- sem artigo
# nenhum, com cara de texto montado por maquina. Os nomes vem de um conjunto
# FECHADO (as 12 rotas e seus recursos, mais os dois iniciais), entao o
# genero e dado aqui em vez de adivinhado por terminacao, que erraria em
# "Ponte", "Torre" e "Mapa".
_GENERO_NOMES = {
    # rotas
    "Galeria dos Ecos": "a",
    "Ponte das Engrenagens": "a",
    "Camara Rubra": "a",
    "Sala dos Companheiros": "a",
    "Arquivo das Runas": "o",
    "Observatorio Subterraneo": "o",
    "Forja das Evidencias": "a",
    "Jardim dos Simbolos": "o",
    "Torre do Debate": "a",
    "Sala dos Mapas Vivos": "a",
    "Poco das Consequencias": "o",
    "Mesa dos Pactos": "a",
    "Portal da Masmorra": "o",
    # recursos
    "Mapa parcial da masmorra": "o",
    "Chave mecanica": "a",
    "Escudo runico": "o",
    "Kit de suporte": "o",
    "Lente de verificacao": "a",
    "Astrolabio escolar": "o",
    "Martelo de prova": "o",
    "Caderno de campo": "o",
    "Selo de coerencia": "o",
    "Bussola de retorno": "a",
    "Corda de seguranca": "a",
    "Insignia do grupo": "a",
    # reliquias das historias (STORY_PRESETS), o local padrao e o antagonista
    # de quando a historia nao tem um
    "Compasso Real": "o",
    "Nucleo de Movimento": "o",
    "Ampola de Equilibrio": "a",
    "Selo da Memoria": "o",
    "Pagina Viva": "a",
    "Farol Experimental": "o",
    "Corredor Central": "o",
    "guardiao da masmorra": "o",
    "mapa inicial": "o",
}

_CONTRACOES = {
    ("em", "o"): "no",
    ("em", "a"): "na",
    ("de", "o"): "do",
    ("de", "a"): "da",
    ("por", "o"): "pelo",
    ("por", "a"): "pela",
    ("ate", "o"): "ate o",
    ("ate", "a"): "ate a",
    ("a", "o"): "ao",
    ("a", "a"): "à",
    ("", "o"): "o",
    ("", "a"): "a",
}


def _com_artigo(nome: str, preposicao: str = "") -> str:
    """"Camara Rubra" com "em" vira "na Camara Rubra".

    Nome fora da lista sai sem artigo, com a preposicao solta -- e o que
    acontece se a IA inventar um local novo.
    """
    limpo = str(nome or "").strip()
    # MELHORIA: a jornada guarda o nome ja acentuado para a tela ("Câmara
    # Rubra"), e a busca exata na tabela nao o achava: da segunda fase em
    # diante saia "em Câmara Rubra". A busca e sem acento e sem caixa.
    genero = _GENERO_POR_CHAVE.get(chave_busca(limpo))
    if not genero:
        return f"{preposicao} {limpo}".strip()
    return f"{_CONTRACOES[(preposicao, genero)]} {limpo}"


_GENERO_POR_CHAVE = {chave_busca(nome): genero for nome, genero in _GENERO_NOMES.items()}


def _maiuscula(texto: str) -> str:
    """So a primeira letra: "a Torre do Debate" -> "A Torre do Debate"."""
    return texto[:1].upper() + texto[1:]


def _aposto_fechado(nome: str) -> str:
    """"Mestre Vesper, o arquiteto..." ganha a virgula que fecha o aposto."""
    return f"{nome}," if "," in nome else nome


def _antagonista_curto(memoria: dict[str, str], preposicao: str = "") -> str:
    """O antagonista no meio da frase, so pelo nome.

    MELHORIA: o nome vinha com o aposto inteiro e sem a virgula que o fecha --
    "a armadilha de Mestre Vesper, o arquiteto das contas impossiveis e custar
    HP". O aposto completo fica para a apresentacao, no inicio da aventura.
    """
    nome = str(memoria.get("antagonista") or "").split(",")[0].strip()
    if not nome:
        return _com_artigo("guardiao da masmorra", preposicao)
    return f"{preposicao} {nome}".strip()


def _titulo_padrao(materia: str) -> str:
    return f"Expedição de {exibir_materia(materia)}"


_DESTINO_POR_CHAVE = {chave_busca(chave): chave for chave in DESTINOS}


def _chave_destino(impacto: Any) -> str:
    """A chave de DESTINOS para o impacto que a opcao carrega.

    MELHORIA: a opcao guarda o impacto ja acentuado para a tela
    ("Estratégia", "Cooperação"), e o placar, o bonus de chance e as
    consequencias usam a chave sem acento. Escolher uma rota de Estrategia ou
    de Cooperacao nao somava nada ao destino do heroi, nao dava bonus e caia
    na consequencia generica -- achado na varredura dos textos, 16/09/2026.
    """
    texto = str(impacto or "")
    return _DESTINO_POR_CHAVE.get(chave_busca(texto), texto)


def _texto_opcao_narrativa(modelo: dict[str, Any], fase: int, materia: str, memoria: dict[str, str]) -> tuple[str, str]:
    rota_atual = str(modelo.get("rota") or "rota desconhecida")
    recurso_rota = str(modelo.get("recurso") or memoria["recurso"])
    rota_anterior = memoria["ultima_rota"]
    recurso = memoria["recurso"]
    # MELHORIA: logo depois de escolher uma rota, o recurso guardado e o da
    # propria rota sao o MESMO, e as quatro frases abaixo juntam os dois:
    # "Levar o Caderno de campo e o Caderno de campo ate a ...". Visto na tela e
    # reproduzido em 15/09/2026 jogando 14 fases sem IA. O segundo vira o mapa.
    if recurso == recurso_rota:
        recurso = "mapa inicial"
    foco = memoria["foco"]
    ameaca = memoria.get("ameaca") or "a sala muda quando o grupo hesita"
    reliquia = memoria.get("reliquia") or recurso
    cicatriz = memoria.get("cicatriz") or f"as marcas {_com_artigo(rota_anterior, 'de')} ainda brilham"
    textos = {
        "Conhecimento": (
            f"Entrar {_com_artigo(rota_atual, 'em')} e comparar a pista de {foco} encontrada "
            f"{_com_artigo(rota_anterior, 'em')} com as marcas {_com_artigo(recurso_rota, 'de')}.",
            f"Se a leitura estiver certa, {_com_artigo(recurso_rota)} reage {_com_artigo(recurso, 'a')}, "
            f"revela uma falha na armadilha {_antagonista_curto(memoria, 'de')} e aproxima o grupo "
            f"{_com_artigo(reliquia, 'de')}.",
        ),
        "Estrategia": (
            f"Levar {_com_artigo(recurso_rota)} e {_com_artigo(recurso)} {_com_artigo(rota_atual, 'ate')} "
            f"para redesenhar a passagem antes que a lembranca {_com_artigo(rota_anterior, 'de')} desapareca.",
            f"A rota pode abrir um atalho para a fase {fase}, mas {ameaca}.",
        ),
        "Coragem": (
            f"Forcar entrada {_com_artigo(rota_atual, 'em')} usando {_com_artigo(recurso_rota)} "
            f"e protegendo {_com_artigo(recurso)}, mesmo sabendo que {cicatriz}, para arrancar uma pista "
            "antes que a sala se feche.",
            f"O risco é alto: um erro fortalece {_antagonista_curto(memoria)}, mas um acerto abre caminho direto para o proximo selo.",
        ),
        "Cooperacao": (
            f"Chamar aliados {_com_artigo(rota_atual, 'em')} e dividir funcoes para proteger "
            f"{_com_artigo(recurso_rota)} e {_com_artigo(recurso)} das marcas deixadas "
            f"{_com_artigo(rota_anterior, 'por')}.",
            f"A confianca cresce se cada pessoa usar {foco} em uma parte real do enigma de {materia}.",
        ),
    }
    return textos.get(modelo["impacto"], (modelo["texto"], f"Essa rota prepara a equipe para novos desafios em {materia}."))


def _detalhes_opcao_narrativa(
    modelo: dict[str, Any],
    fase: int,
    materia: str,
    memoria: dict[str, str],
    texto: str,
    consequencia: str,
) -> dict[str, str]:
    rota = str(modelo.get("rota") or "rota desconhecida")
    recurso_rota = str(modelo.get("recurso") or memoria["recurso"])
    foco = str(modelo.get("foco") or memoria["foco"])
    impacto = str(modelo.get("impacto") or "Conhecimento")
    risco = str(modelo.get("risco") or "medio").lower()
    ameaca = memoria.get("ameaca") or "a sala muda quando o grupo hesita"
    reliquia = memoria.get("reliquia") or memoria["recurso"]
    ultima_rota = memoria["ultima_rota"]
    cicatriz = memoria.get("cicatriz") or f"as marcas {_com_artigo(ultima_rota, 'de')} ainda brilham no caminho"

    cenas = {
        "Conhecimento": (
            f"{_maiuscula(_com_artigo(rota, 'em'))}, paredes cobertas de sinais contraditórios tentam esconder a "
            f"pista deixada {_com_artigo(ultima_rota, 'em')}. {_maiuscula(_com_artigo(recurso_rota))} vibra quando "
            "o grupo compara fontes, detalhes e ausencias antes de tocar no proximo selo."
        ),
        # "antes que" pediria subjuntivo, e a ameaca vem no indicativo ("os
        # corredores mudam de escala..."): "porque" aceita a frase como ela e.
        "Estrategia": (
            f"{_maiuscula(_com_artigo(rota))} se move como um mecanismo antigo: cada passo altera pontes, portas e "
            f"marcas no chão. O grupo precisa usar {_com_artigo(recurso_rota)} para montar um plano, porque {ameaca}."
        ),
        "Coragem": (
            f"O ar fica pesado {_com_artigo(rota, 'em')}; {cicatriz}, e as defesas parecem esperar uma decisao "
            "precipitada. Avancar exige proteger o recurso certo e aceitar que o erro terá custo real."
        ),
        "Cooperacao": (
            f"{_maiuscula(_com_artigo(rota, 'em'))}, nenhuma pista fica inteira nas maos de uma unica pessoa. "
            f"Aliados, vozes e marcas antigas precisam ser reunidos antes que {_antagonista_curto(memoria)} "
            "se aproveite da divisao."
        ),
    }
    riscos = {
        "baixo": f"Risco baixo: a equipe perde tempo se interpretar mal {foco}, mas ainda consegue recuar e rever as pistas.",
        "medio": f"Risco medio: uma decisao fraca pode ativar a armadilha {_antagonista_curto(memoria, 'de')} e custar HP no desafio.",
        "alto": (
            f"Risco alto: falhar fortalece {_antagonista_curto(memoria)}; vencer, porém, acelera a busca "
            f"{_com_artigo(reliquia, 'por')}."
        ),
    }
    recompensas = {
        "Conhecimento": f"Recompensa: uma prova nova revela como {memoria['segredo']} e prepara uma resposta melhor em {materia}.",
        "Estrategia": f"Recompensa: a equipe abre uma vantagem tatica para a fase {fase} e reduz a incerteza da proxima sala.",
        "Coragem": f"Recompensa: o grupo ganha impulso heroico e transforma pressao em caminho direto para o proximo selo.",
        "Cooperacao": f"Recompensa: uma alianca concreta divide tarefas e torna {foco} uma força coletiva.",
    }
    return {
        "gancho": str(texto).split(".")[0].strip() + ".",
        "cena": cenas.get(impacto, cenas["Conhecimento"]),
        "plano": texto,
        "risco_narrativo": riscos.get(risco, riscos["medio"]),
        "recompensa_narrativa": recompensas.get(impacto, recompensas["Conhecimento"]),
        "consequencia_completa": consequencia,
    }


def _criar_opcoes(
    fase: int,
    materia: str,
    jornada: dict[str, Any] | None = None,
    historico: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    memoria = _resumo_memoria(jornada, historico)
    usadas = {str(item.get("rota", "")) for item in (jornada or {}).get("escolhas", [])[-2:]}
    candidatas = [rota for rota in ROTAS if rota["rota"] not in usadas] or ROTAS
    rng = _rng("opcoes", fase, materia, memoria["ultima_rota"], memoria["historico"])
    # MELHORIA: sorteavam-se 3 rotas entre as 12 sem olhar o campo "impacto",
    # mas o texto da opcao vem de um molde POR IMPACTO (ver
    # _texto_opcao_narrativa) e ha 3 rotas para cada um. Resultado medido em
    # 400 telas: 49,8% mostravam duas opcoes com a mesma frase -- mudando so
    # os nomes proprios -- e 2,0% mostravam as tres iguais. Agora sorteia-se
    # um impacto de cada vez e uma rota dentro dele, entao as tres frases
    # sao sempre diferentes.
    por_impacto: dict[str, list[dict[str, Any]]] = {}
    for rota in candidatas:
        por_impacto.setdefault(str(rota.get("impacto") or ""), []).append(rota)
    impactos = sorted(por_impacto)
    rng.shuffle(impactos)
    base = [rng.choice(por_impacto[impacto]) for impacto in impactos[:3]]
    if len(base) < 3:
        # Menos de 3 impactos disponiveis: completa com o que sobrou.
        extras = [rota for rota in ROTAS if rota not in base]
        rng.shuffle(extras)
        base.extend(extras[: 3 - len(base)])
    opcoes: list[dict[str, Any]] = []
    for idx, modelo in enumerate(base, start=1):
        # A materia so aparece no texto: "Ciencias" e "Portugues" nao estao no
        # dicionario de acentos, entao vai o nome da tela.
        texto, consequencia = _texto_opcao_narrativa(modelo, fase, exibir_materia(materia), memoria)
        detalhes = _detalhes_opcao_narrativa(modelo, fase, exibir_materia(materia), memoria, texto, consequencia)
        opcoes.append(
            {
                "id": idx,
                "texto": aplicar_acentos_pt(texto),
                "consequencia_imediata": aplicar_acentos_pt(consequencia),
                "gancho": aplicar_acentos_pt(detalhes["gancho"]),
                "cena": aplicar_acentos_pt(detalhes["cena"]),
                "plano": aplicar_acentos_pt(detalhes["plano"]),
                "risco_narrativo": aplicar_acentos_pt(detalhes["risco_narrativo"]),
                "recompensa_narrativa": aplicar_acentos_pt(detalhes["recompensa_narrativa"]),
                "consequencia_completa": aplicar_acentos_pt(detalhes["consequencia_completa"]),
                "risco": modelo["risco"],
                "icone_destino": DESTINOS[modelo["impacto"]]["icone"],
                "destino_titulo": aplicar_acentos_pt(modelo["destino"]),
                "rota": aplicar_acentos_pt(modelo["rota"]),
                "foco_aprendizado": aplicar_acentos_pt(modelo["foco"]),
                "recurso": aplicar_acentos_pt(modelo["recurso"]),
                "impacto_destino": aplicar_acentos_pt(modelo["impacto"]),
            }
        )
    return opcoes


def _aplicar_narrativa_ia(cena_base: dict[str, Any], dados_ia: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(dados_ia, dict):
        return None
    local = str(dados_ia.get("local_atual") or "").strip()
    narracao = str(dados_ia.get("narracao") or "").strip()
    opcoes_ia = dados_ia.get("opcoes")
    if not local or not narracao or not isinstance(opcoes_ia, list):
        return None
    narracao_baixa = narracao.lower()
    trechos_genericos = (
        "é importante considerar",
        "e importante considerar",
        "planejar o proximo passo",
        "planejar o próximo passo",
        "as lições aprendidas",
        "as licoes aprendidas",
        "recursos disponíveis",
        "recursos disponiveis",
        "desenvolver uma estrategia",
        "desenvolver estrategia",
        "reforcar a confianca",
        "reforçar a confiança",
        "aplicacao prática",
        "aplicação prática",
        "habilidade matematica precisa",
        "habilidade matemática precisa",
    )
    if any(trecho in narracao_baixa for trecho in trechos_genericos):
        return None

    por_rota = {
        str(item.get("rota") or "").strip(): item
        for item in opcoes_ia
        if isinstance(item, dict) and str(item.get("rota") or "").strip()
    }
    if not por_rota:
        return None

    cena = dict(cena_base)
    cena["local_atual"] = local[:90]
    cena["narracao"] = narracao[:850]
    opcoes = []
    for opcao in cena_base.get("opcoes", []) or []:
        nova = dict(opcao)
        ajuste = por_rota.get(str(opcao.get("rota") or "").strip())
        if isinstance(ajuste, dict):
            texto = str(ajuste.get("texto") or "").strip()
            consequencia = str(ajuste.get("consequencia_imediata") or "").strip()
            if texto:
                nova["texto"] = texto[:180]
            if consequencia:
                nova["consequencia_imediata"] = consequencia[:220]
        opcoes.append(nova)
    cena["opcoes"] = opcoes
    cena["evento"] = cena.get("evento") or "exploracao"
    cena["_origem_narrativa"] = "ia"
    return normalizar_textos_cena(cena)


def _narracao_fallback(
    proxima_fase: int,
    materia: str,
    rota: str,
    acao: str,
    texto_resultado: str,
    memoria: dict[str, str],
    resumo: dict[str, Any],
    chefao: bool = False,
) -> tuple[str, str]:
    locais = [
        "Arquivo das Runas",
        "Observatorio Subterraneo",
        "Forja das Evidencias",
        "Jardim dos Simbolos",
        "Torre do Debate",
        "Sala dos Mapas Vivos",
        "Poco das Consequencias",
        "Mesa dos Pactos",
    ]
    local = "Sala do Chefe Final" if chefao else f"{locais[proxima_fase % len(locais)]} - fase {proxima_fase}"
    historico = f" A memoria recente ainda aponta para {memoria['historico']}." if memoria["historico"] else ""
    narracao = (
        f"Ao sair {_com_artigo(rota, 'de')}, a equipe percebe que a acao '{str(acao).rstrip(' .')}' deixou marcas "
        f"reais na masmorra: {memoria['cicatriz']}. {texto_resultado} Nas paredes, uma sombra assinada "
        f"{_antagonista_curto(memoria, 'por')} lembra a ameaca central: {memoria['ameaca']}. "
        f"{_maiuscula(_com_artigo(memoria['recurso']))} reage ao foco em {memoria['foco']} e mostra como {memoria['segredo']}. "
        f"Para {memoria['objetivo']}, o grupo precisa transformar o perfil de {resumo['titulo']} em escolha concreta "
        f"antes que a sala acorde de vez.{historico}"
    )
    return local, narracao


def _gerar_cena_ia(
    cena_base: dict[str, Any],
    config_rpg: dict[str, Any],
    historico: list[dict[str, Any]],
    resultado: str | None,
    jornada: dict[str, Any] | None,
    ultima_escolha: dict[str, Any] | None,
) -> dict[str, Any] | None:
    materia = normalizar_materia(config_rpg.get("materia", "Matematica"))
    memoria = _resumo_memoria(jornada, historico)
    resumo = resumir_jornada(jornada)
    story = _story_state(jornada, materia, config_rpg.get("titulo") or "")
    rotas_permitidas = [
        {
            "rota": opcao.get("rota"),
            "risco": opcao.get("risco"),
            "impacto": opcao.get("impacto_destino"),
            "recurso": opcao.get("recurso"),
            "foco": opcao.get("foco_aprendizado"),
        }
        for opcao in cena_base.get("opcoes", []) or []
    ]
    system = (
        "Voce e diretor narrativo de um RPG educacional em portugues brasileiro. "
        "Escreva cenas imersivas, com conflito concreto, causa e consequencia. "
        "A materia escolar deve virar pista, mecanismo, regra magica ou decisao do mundo, nunca palestra. "
        "Evite frases genericas como 'aplicar conhecimento', 'desenvolver estrategia', 'reforcar confianca' ou 'proximo desafio'. "
        "Responda somente em JSON valido. Nao altere nomes de rota, risco, impacto ou materia."
    )
    user = f"""
Crie a proxima cena do RPG com base nos acontecimentos anteriores.

Campanha: {config_rpg.get('titulo') or 'Aventura RPG'}
Materia: {materia}
Antagonista: {story.get('antagonista')}
Objetivo da aventura: {story.get('objetivo')}
Ameaca ativa: {story.get('ameaca')}
Reliquia/objeto central: {story.get('reliquia')}
Segredo revelado: {story.get('segredo')}
Consequencia permanente da ultima rota: {story.get('cicatriz')}
Ganho recente do grupo: {story.get('ultimo_ganho')}
Nivel de tensao de 1 a 5: {story.get('tensao')}
Resultado do ultimo desafio: {resultado or 'sem desafio academico'}
Ultima escolha: {(ultima_escolha or {}).get('texto', '')}
Ultima rota: {memoria['ultima_rota']}
Recurso recente: {memoria['recurso']}
Foco recente: {memoria['foco']}
Historico recente: {memoria['historico'] or 'inicio da jornada'}
Perfil dominante da jornada: {resumo['titulo']}
Cena base: {cena_base.get('narracao', '')}

Reescreva APENAS estas rotas, mantendo o campo rota exatamente igual:
{rotas_permitidas}

Regras de escrita:
- local_atual deve ser um lugar memoravel, nao "Sala de Reflexao".
- narracao deve ter 3 a 5 frases, mostrando uma mudanca fisica na sala, uma decisao do antagonista e uma pista ligada a {materia}.
- cada opcao.texto deve ser uma acao especifica com objeto, alvo e risco visivel.
- cada consequencia_imediata deve dizer o que muda no mundo se a rota funcionar.
- nao use texto de aula; use a materia como parte da aventura.

Formato:
{{
  "local_atual": "nome curto do novo local",
  "narracao": "paragrafo imersivo com consequencia clara da ultima escolha e gancho para a proxima decisao",
  "opcoes": [
    {{"rota": "nome exato da rota permitida", "texto": "acao especifica com objeto, alvo e risco", "consequencia_imediata": "mudanca concreta no mundo se a rota funcionar"}}
  ]
}}
"""
    dados = gerar_json_ia(system, user, max_tokens=900, temperature_groq=0.9, temperature_openrouter=0.75)
    return _aplicar_narrativa_ia(cena_base, dados)


def normalizar_textos_cena(cena: dict[str, Any] | None) -> dict[str, Any]:
    cena_norm = dict(cena or {})
    for campo in ("titulo", "local_atual", "narracao", "evento"):
        if campo in cena_norm:
            cena_norm[campo] = aplicar_acentos_pt(cena_norm[campo])
    opcoes = []
    for opcao in cena_norm.get("opcoes", []) or []:
        if not isinstance(opcao, dict):
            continue
        item = dict(opcao)
        for campo in (
            "texto",
            "consequencia_imediata",
            "gancho",
            "cena",
            "plano",
            "risco_narrativo",
            "recompensa_narrativa",
            "consequencia_completa",
            "destino_titulo",
            "rota",
            "foco_aprendizado",
            "recurso",
            "impacto_destino",
        ):
            if campo in item:
                item[campo] = aplicar_acentos_pt(item[campo])
        opcoes.append(item)
    cena_norm["opcoes"] = opcoes
    return cena_norm


def iniciar_aventura(config_rpg: dict[str, Any] | None) -> dict[str, Any]:
    config_rpg = config_rpg or {}
    materia = normalizar_materia(config_rpg.get("materia", "Matematica"))
    titulo = config_rpg.get("titulo") or _titulo_padrao(materia)
    jornada = criar_jornada_inicial(materia, titulo)
    story = _story_state(jornada, materia, titulo)
    cena = CenaRpg(
        titulo=titulo,
        local_atual="Portal da Masmorra",
        narracao=(
            f"A equipe atravessa o portal de “{titulo}” carregando um mapa incompleto e uma pista sobre "
            f"{exibir_materia(materia)}. Do outro lado, {_aposto_fechado(story['antagonista'])} ja moveu a primeira "
            f"sala para impedir o grupo de {story['objetivo']}. {_maiuscula(_com_artigo(story['reliquia']))} aparece "
            f"como uma sombra no centro do corredor, enquanto a ameaca fica clara: {story['ameaca']}."
        ),
        opcoes=_criar_opcoes(1, materia, jornada, []),
        evento="inicio",
    ).as_dict()
    return normalizar_textos_cena(cena)


def continuar_aventura(
    config_rpg: dict[str, Any] | None,
    historico: list[dict[str, Any]] | None,
    acao: str,
    resultado: str | None,
    ultima_checagem_escolha: dict[str, Any] | None,
    jornada: dict[str, Any] | None,
    ultima_escolha: dict[str, Any] | None,
) -> dict[str, Any]:
    config_rpg = config_rpg or {}
    historico = historico or []
    materia = normalizar_materia(config_rpg.get("materia", "Matematica"))
    # MELHORIA: era "len(historico) + 2". Uma fase com desafio academico
    # grava DOIS registros no historico (a escolha em web/routes/rpg_fla.py
    # ::escolher_opcao e a resposta em ::responder_desafio), uma fase sem
    # desafio grava so um -- entao o numero de fase crescia mais rapido que
    # o real, e o titulo da sala vazava um numero interno maior que o HUD
    # (visto ao vivo: sala "... - fase 11" com o HUD mostrando "Fase 6/15",
    # relatorio de QA de 23/09/2026). Contar fases DISTINTAS ja registradas
    # bate com estado["fase"] (web/routes/rpg_fla.py::_avancar_cena),
    # incrementado uma vez por fase de verdade.
    fases_concluidas = {item.get("fase") for item in historico if isinstance(item, dict) and item.get("fase") is not None}
    proxima_fase = len(fases_concluidas) + 1
    resumo = resumir_jornada(jornada)
    rota = (ultima_escolha or {}).get("rota", "Corredor Central")
    memoria = _resumo_memoria(jornada, historico)
    checagem = ultima_checagem_escolha or {}
    texto_resultado = {
        "acertou": (
            f"A resposta correta estabilizou as marcas deixadas {_com_artigo(rota, 'em')} e o grupo passou a "
            f"confiar mais em {memoria['foco']}."
        ),
        "errou": (
            f"O erro fez as defesas {_com_artigo(rota, 'de')} reagirem, mas o grupo guardou a pista principal "
            "para nao repetir a falha."
        ),
        None: (
            f"A tentativa {_com_artigo(rota, 'em')} {'funcionou' if checagem.get('sucesso') else 'saiu pela metade'}, "
            "e o caminho mudou sem exigir um duelo academico agora."
        ),
    }.get(resultado, "A jornada avanca para uma nova camada da masmorra.")

    if proxima_fase >= FASES_TOTAIS:
        local, narracao = _narracao_fallback(proxima_fase, materia, rota, acao, texto_resultado, memoria, resumo, chefao=True)
        cena_base = CenaRpg(
            titulo=config_rpg.get("titulo") or _titulo_padrao(materia),
            local_atual=local,
            narracao=narracao,
            opcoes=_criar_opcoes(FASES_TOTAIS, materia, jornada, historico),
            evento="chefao",
        ).as_dict()
        return _gerar_cena_ia(cena_base, config_rpg, historico, resultado, jornada, ultima_escolha) or normalizar_textos_cena(cena_base)

    local, narracao = _narracao_fallback(proxima_fase, materia, rota, acao, texto_resultado, memoria, resumo)
    cena_base = CenaRpg(
        titulo=config_rpg.get("titulo") or _titulo_padrao(materia),
        local_atual=local,
        narracao=narracao,
        opcoes=_criar_opcoes(proxima_fase, materia, jornada, historico),
    ).as_dict()
    return _gerar_cena_ia(cena_base, config_rpg, historico, resultado, jornada, ultima_escolha) or normalizar_textos_cena(cena_base)


def gerar_desafio_academico(
    config_rpg: dict[str, Any] | None,
    local_atual: str,
    narracao: str,
    temas_usados: list[str] | None,
    jornada: dict[str, Any] | None,
    opcao: dict[str, Any] | None,
) -> dict[str, Any]:
    config_rpg = config_rpg or {}
    materia = normalizar_materia(config_rpg.get("materia", "Matematica"))
    serie = str(config_rpg.get("serie", ""))
    tema = _selecionar_tema_desafio(materia, serie, temas_usados, jornada, opcao)
    teorico_exatas = False

    if materia in {"Matematica", "Fisica", "Quimica"}:
        from services.calculo_service import gerar_desafio_exatas

        if _usar_teoria_exatas_rpg(temas_usados, jornada):
            teorico_exatas = True
            chave_extra = "|".join(
                str(item)
                for item in (
                    local_atual,
                    narracao,
                    (opcao or {}).get("rota", ""),
                    (jornada or {}).get("escolhas", []),
                    len(temas_usados or []),
                )
            )
            desafio = invocar_enigma(materia, serie, config_rpg.get("nivel", "Medio"), tema) or {}
            aviso_ia = obter_ultimo_erro_ia()
            if not desafio.get("_origem_geracao"):
                desafio["_origem_geracao"] = "offline" if aviso_ia else "ia"
            if desafio.get("_origem_geracao") == "offline":
                desafio = gerar_questao_rpg_offline(
                    materia,
                    tema,
                    config_rpg.get("nivel", "Medio"),
                    chave_extra=chave_extra,
                )
                aviso_ia = aviso_ia or "IA indisponivel no momento. Usando banco RPG offline."
            _remover_campos_calculo(desafio)
        else:
            desafio = gerar_desafio_exatas(materia, tema, serie, config_rpg.get("nivel", "Medio")) or {}
            aviso_ia = obter_ultimo_erro_ia()
            if not desafio.get("_origem_geracao"):
                desafio["_origem_geracao"] = "offline" if aviso_ia else "ia"
    else:
        desafio = invocar_enigma(materia, serie, config_rpg.get("nivel", "Medio"), tema)
        aviso_ia = obter_ultimo_erro_ia()
        if not desafio.get("_origem_geracao"):
            desafio["_origem_geracao"] = "offline" if aviso_ia else "ia"

    if materia not in {"Matematica", "Fisica", "Quimica"} and desafio.get("_origem_geracao") == "offline":
        chave_extra = "|".join(
            str(item)
            for item in (
                local_atual,
                narracao,
                (opcao or {}).get("rota", ""),
                (jornada or {}).get("escolhas", []),
                len(temas_usados or []),
            )
        )
        desafio = gerar_questao_rpg_offline(
            materia,
            tema,
            config_rpg.get("nivel", "Medio"),
            chave_extra=chave_extra,
        )
        aviso_ia = aviso_ia or "IA indisponivel no momento. Usando banco RPG offline."
    desafio["aviso_ia"] = aviso_ia
    desafio["ambientacao"] = str(desafio.get("enigma", "")).strip() or f"Guardiao de {local_atual}"
    desafio["enigma"] = desafio["ambientacao"]
    desafio["tema_usado"] = tema
    payload = normalizar_payload_questao(desafio, modo_ingles=(materia == "Ingles"))
    payload["materia"] = materia
    payload["materia_label"] = exibir_materia(materia)
    if teorico_exatas:
        _remover_campos_calculo(payload)
    if "habilidade_bncc" not in payload or not payload.get("habilidade_bncc"):
        try:
            from services.banks.em import BNCC_REFERENCIAS, HABILIDADES_BNCC

            # A tupla traz o CODIGO no terceiro lugar; a descricao vem da
            # outra tabela. Antes o codigo ia para `habilidade_bncc` e
            # `codigo_bncc` ficava vazio -- ver o comentario em banks/em.py.
            area, competencia, codigo = BNCC_REFERENCIAS.get(materia, BNCC_REFERENCIAS["Ciencias"])
            payload["area_bncc"] = area
            payload["competencia_bncc"] = competencia
            payload["habilidade_bncc"] = HABILIDADES_BNCC.get(materia, "")
            payload["codigo_bncc"] = codigo
        except Exception:
            payload["habilidade_bncc"] = ""
    if materia != "Ingles":
        payload["pergunta"] = aplicar_acentos_pt(payload.get("pergunta", ""))
        payload["enigma"] = aplicar_acentos_pt(payload.get("enigma", ""))
        payload["opcoes"] = [aplicar_acentos_pt(opcao) for opcao in payload.get("opcoes", [])]
        for bloco in payload.get("explicacao", []) or []:
            if isinstance(bloco, dict) and "conteudo" in bloco:
                bloco["conteudo"] = aplicar_acentos_pt(bloco["conteudo"])
        for campo in ("ambientacao", "rpg_local", "aviso_ia"):
            if campo in payload:
                payload[campo] = aplicar_acentos_pt(payload[campo])
    if materia not in {"Matematica", "Fisica", "Quimica"}:
        payload["passos_resolucao"] = []
    return embaralhar_opcoes_questao(payload)


def calcular_resultado_desafio(ultima_escolha: dict[str, Any] | None, acertou: bool, bonus_risco_ativo: bool = True) -> dict[str, Any]:
    risco = obter_efeitos_risco(ultima_escolha)
    xp_bonus = 0
    if acertou and bonus_risco_ativo:
        xp_bonus = 0 if risco["risco"] == "baixo" else 8 if risco["risco"] == "medio" else 15
    return {
        "risco": risco["risco"],
        "xp_ganho": risco["xp_base"] + xp_bonus if acertou else 0,
        "xp_bonus": xp_bonus,
        "hp_perda": 0 if acertou else risco["hp_perda"],
        "bonus_risco_ativo": bonus_risco_ativo,
    }


def aplicar_resultado_desafio(
    estado: dict[str, Any],
    acertou: bool,
    ultima_escolha: dict[str, Any] | None = None,
    bonus_risco_ativo: bool = True,
) -> dict[str, Any]:
    """Aplica HP/XP em uma copia do estado, mantendo compatibilidade com testes."""
    novo_estado = dict(estado or {})
    resultado = calcular_resultado_desafio(ultima_escolha, acertou, bonus_risco_ativo)
    xp_atual = int(novo_estado.get("xp", 0) or 0)
    hp_atual = int(novo_estado.get("hp", 100) or 0)
    novo_estado["xp"] = max(0, xp_atual + int(resultado.get("xp_ganho", 0) or 0))
    novo_estado["hp"] = max(0, hp_atual - int(resultado.get("hp_perda", 0) or 0))
    novo_estado["ultimo_resultado_risco"] = resultado
    return novo_estado


# MELHORIA: gerar_recompensas_vitoria nao tem mais uso na parte Flask deste
# repositorio, mas st/ui/tela_rpg_st.py ainda chama
# "rpg_engine.gerar_recompensas_vitoria(...)" direto ao vencer uma campanha
# — removê-la quebraria esse fluxo. Mantida como estava antes da
# sincronizacao com a main.
def gerar_recompensas_vitoria(ultima_escolha: dict[str, Any] | None, fase_atual: int) -> list[dict[str, Any]]:
    risco = obter_efeitos_risco(ultima_escolha)
    bonus = 6 + fase_atual
    return [
        {"nome": "Pocao de Folego", "tipo": "hp", "valor": 10 + _risco_idx(risco["risco"]) * 4, "icone": "🧪"},
        {"nome": "Fragmento de XP", "tipo": "xp", "valor": bonus, "icone": "✨"},
        {"nome": "Tesouro da Rota", "tipo": "xp", "valor": bonus + 4, "icone": "🎁"},
    ]
