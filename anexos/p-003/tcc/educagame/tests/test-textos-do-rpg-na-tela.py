"""Os textos do RPG quando a IA não responde: artigo, gênero, aposto e acento.

Varredura de 16/09/2026, jornadas inteiras simuladas sem IA (630 telas):

    "em Torre do Debate", "de Portal da Masmorra"          6.186
    "Sala dos Mapas Vivos se move" (nome abrindo frase)       960
    "reage a o mapa inicial"                                  280
    "aproxima o grupo da Compasso Real", "O Ampola"         1.554
    "antes que os corredores mudam" (pede subjuntivo)         468
    "Mestre Vesper, o arquiteto ... e custar HP"            2.710
    "contraditorios", "chao", "inscricao", "tera", "porem",
    "Ciencias", "Expedicao"                                 sem acento

Todos foram a zero. Duas causas não eram de texto:

- a jornada guarda os nomes JÁ acentuados ("Câmara Rubra"), e o artigo era
  buscado pelo nome exato, sem acento -- da segunda fase em diante, sumia;
- a opção carrega o destino acentuado ("Estratégia", "Cooperação") e o placar
  usa a chave sem acento: escolher essas rotas não somava nada ao destino do
  herói, não dava bônus de chance e caía na consequência genérica.
"""
from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

import pytest
from jinja2 import Environment

import services.rpg_service as rpg
from core.text_cleanup import aplicar_acentos_pt

RAIZ = Path(__file__).resolve().parents[1]


def sem_ia(monkeypatch):
    monkeypatch.setattr(rpg, "gerar_json_ia", lambda *a, **k: None)


# ====================== ARTIGO E GÊNERO ======================


@pytest.mark.parametrize(
    "nome, preposicao, esperado",
    [
        # o nome como a jornada guarda: já acentuado
        ("Câmara Rubra", "em", "na Câmara Rubra"),
        ("Forja das Evidências", "de", "da Forja das Evidências"),
        ("Escudo rúnico", "", "o Escudo rúnico"),
        ("Observatório Subterrâneo", "por", "pelo Observatório Subterrâneo"),
        # "a" + artigo
        ("mapa inicial", "a", "ao mapa inicial"),
        ("Bussola de retorno", "a", "à Bussola de retorno"),
        # as relíquias das histórias e o antagonista padrão
        ("Compasso Real", "de", "do Compasso Real"),
        ("Ampola de Equilíbrio", "por", "pela Ampola de Equilíbrio"),
        ("Pagina Viva", "", "a Pagina Viva"),
        ("Corredor Central", "em", "no Corredor Central"),
        ("guardiao da masmorra", "por", "pelo guardiao da masmorra"),
    ],
)
def test_o_artigo_acha_o_nome_com_ou_sem_acento(nome, preposicao, esperado):
    assert rpg._com_artigo(nome, preposicao) == esperado


def test_nome_desconhecido_continua_sem_artigo():
    assert rpg._com_artigo("Caverna Nova", "a") == "a Caverna Nova"


MEMORIA = {
    "recurso": "mapa inicial", "ultima_rota": "Câmara Rubra", "foco": "observacao",
    "reliquia": "Compasso Real", "antagonista": "Mestre Vesper, o arquiteto das contas impossiveis",
    "ameaca": "os corredores mudam de escala", "cicatriz": "", "segredo": "a pista se fecha",
}


def test_a_opcao_de_conhecimento_le_certo():
    modelo = {"rota": "Torre do Debate", "recurso": "Selo de coerencia", "impacto": "Conhecimento", "texto": "x"}

    texto, consequencia = rpg._texto_opcao_narrativa(modelo, 3, "Matemática", MEMORIA)

    assert "comparar a pista de observacao encontrada na Câmara Rubra com as marcas do Selo" in texto
    assert "o Selo de coerencia reage ao mapa inicial" in consequencia
    assert "armadilha de Mestre Vesper e aproxima o grupo do Compasso Real." in consequencia


@pytest.mark.parametrize(
    "impacto, trecho",
    [
        ("Conhecimento", "Na Torre do Debate, paredes cobertas de sinais contraditórios"),
        ("Conhecimento", "deixada na Câmara Rubra. O Selo de coerencia vibra"),
        ("Estrategia", "A Torre do Debate se move como um mecanismo antigo"),
        ("Estrategia", "marcas no chão. O grupo precisa usar o Selo de coerencia para montar um plano, "
                       "porque os corredores mudam de escala."),
        ("Coragem", "O ar fica pesado na Torre do Debate; as marcas da Câmara Rubra ainda brilham no caminho, e"),
        ("Coragem", "o erro terá custo real"),
        ("Cooperacao", "Na Torre do Debate, nenhuma pista fica inteira"),
        ("Cooperacao", "antes que Mestre Vesper se aproveite da divisao."),
    ],
)
def test_a_cena_de_cada_rota_le_certo(impacto, trecho):
    modelo = {"rota": "Torre do Debate", "recurso": "Selo de coerencia", "impacto": impacto, "risco": "medio"}

    detalhes = rpg._detalhes_opcao_narrativa(modelo, 2, "Matemática", MEMORIA, "Texto.", "c")

    assert trecho in detalhes["cena"]


@pytest.mark.parametrize(
    "risco, trecho",
    [
        ("medio", "ativar a armadilha de Mestre Vesper e custar HP"),
        ("alto", "falhar fortalece Mestre Vesper; vencer, porém, acelera a busca pelo Compasso Real."),
    ],
)
def test_o_risco_usa_so_o_nome_do_antagonista(risco, trecho):
    modelo = {"rota": "Torre do Debate", "recurso": "Selo de coerencia", "impacto": "Coragem", "risco": risco}

    detalhes = rpg._detalhes_opcao_narrativa(modelo, 2, "Matemática", MEMORIA, "Texto.", "c")

    assert trecho in detalhes["risco_narrativo"]


def test_sem_antagonista_entra_o_guardiao_com_artigo():
    memoria = dict(MEMORIA, antagonista="")

    assert rpg._antagonista_curto(memoria) == "o guardiao da masmorra"
    assert rpg._antagonista_curto(memoria, "de") == "do guardiao da masmorra"
    assert rpg._antagonista_curto(MEMORIA, "por") == "por Mestre Vesper"


def test_o_aposto_so_ganha_virgula_quando_existe():
    assert rpg._aposto_fechado("Mestre Vesper, o arquiteto") == "Mestre Vesper, o arquiteto,"
    assert rpg._aposto_fechado("Mestre Vesper") == "Mestre Vesper"


def test_a_coragem_sem_cicatriz_usa_as_marcas_da_rota_anterior():
    modelo = {"rota": "Torre do Debate", "recurso": "Selo de coerencia", "impacto": "Coragem", "texto": "x"}

    texto, _ = rpg._texto_opcao_narrativa(modelo, 3, "Matemática", MEMORIA)

    assert "mesmo sabendo que as marcas da Câmara Rubra ainda brilham, para arrancar" in texto


def test_a_historia_nova_tem_titulo_e_cicatriz_que_cabem_na_frase():
    """A cicatriz entra em "mesmo sabendo que ...": precisa de verbo conjugado."""
    story = rpg.criar_jornada_inicial("Quimica", "")["story_state"]

    assert story["campanha"] == "Expedição de Química"
    assert story["cicatriz"] == "o pulso do portal inicial ainda vibra atras da equipe"


def test_a_coragem_nao_junta_mesmo_com_e_oracao():
    modelo = {"rota": "Torre do Debate", "recurso": "Selo de coerencia", "impacto": "Coragem", "texto": "x"}
    memoria = dict(MEMORIA, cicatriz="uma inscrição na Câmara Rubra revelou uma regra")

    texto, consequencia = rpg._texto_opcao_narrativa(modelo, 3, "Matemática", memoria)

    assert "mesmo sabendo que uma inscrição na Câmara Rubra revelou uma regra, para arrancar" in texto
    assert consequencia.startswith("O risco é alto: um erro fortalece Mestre Vesper, mas")


# ====================== O DESTINO QUE NÃO SOMAVA ======================


@pytest.mark.parametrize(
    "na_tela, chave",
    [("Estratégia", "Estrategia"), ("Cooperação", "Cooperacao"), ("Conhecimento", "Conhecimento"), ("xyz", "xyz")],
)
def test_a_chave_do_destino_sai_sem_acento(na_tela, chave):
    assert rpg._chave_destino(na_tela) == chave


@pytest.mark.parametrize("na_tela, chave", [("Estratégia", "Estrategia"), ("Cooperação", "Cooperacao")])
def test_escolher_a_rota_soma_no_destino(na_tela, chave):
    jornada = rpg.criar_jornada_inicial("Matematica", "Teste")
    opcao = {"rota": "Torre do Debate", "recurso": "Selo de coerência", "impacto_destino": na_tela, "risco": "medio"}

    depois = rpg.registrar_escolha_jornada(jornada, opcao, 1)

    assert depois["placar"][chave] == 1
    assert depois["escolhas"][-1]["impacto"] == chave


def test_o_destino_acentuado_da_bonus_de_chance():
    jornada = rpg.criar_jornada_inicial("Matematica", "Teste")
    jornada["placar"]["Estrategia"] = 3
    opcao = {"impacto_destino": "Estratégia", "risco": "medio"}

    com_placar = rpg.obter_efeitos_escolha(opcao, jornada, 1)["chance_sucesso"]
    sem_placar = rpg.obter_efeitos_escolha(opcao, rpg.criar_jornada_inicial("Matematica", "Teste"), 1)["chance_sucesso"]

    assert com_placar == sem_placar + 6


@pytest.mark.parametrize(
    "na_tela, comeco",
    [
        ("Estratégia", "o uso do Selo de coerência abriu um atalho"),
        ("Cooperação", "um aliado da Torre do Debate prometeu ajuda"),
        ("Conhecimento", "uma inscrição na Torre do Debate revelou"),
        ("Coragem", "a passagem pela Torre do Debate deixou"),
    ],
)
def test_a_consequencia_e_a_da_rota_escolhida(na_tela, comeco):
    jornada = rpg.criar_jornada_inicial("Matematica", "Teste")
    opcao = {"rota": "Torre do Debate", "recurso": "Selo de coerência", "impacto_destino": na_tela,
             "foco_aprendizado": "argumentação", "risco": "medio"}

    depois = rpg.registrar_escolha_jornada(jornada, opcao, 1)

    assert depois["story_state"]["cicatriz"].startswith(comeco)


def test_rota_de_impacto_desconhecido_cai_na_consequencia_generica():
    jornada = rpg.criar_jornada_inicial("Matematica", "Teste")
    opcao = {"rota": "Sala dos Mapas Vivos", "impacto_destino": "Outro", "risco": "medio"}

    depois = rpg.registrar_escolha_jornada(jornada, opcao, 1)

    assert depois["story_state"]["cicatriz"] == "a Sala dos Mapas Vivos mudou a masmorra de forma visivel"
    assert sum(depois["placar"].values()) == 0


# ====================== A ABERTURA E A NARRAÇÃO ======================


def test_a_abertura_apresenta_a_historia_com_virgula_artigo_e_acento(monkeypatch):
    sem_ia(monkeypatch)

    cena = rpg.iniciar_aventura({"materia": "Quimica", "titulo": ""})

    assert cena["titulo"] == "Expedição de Química"
    assert "portal de “Expedição de Química”" in cena["narracao"]
    assert "Alquimista Vesper, senhor dos reagentes instáveis, já moveu" in cena["narracao"]
    assert "A Ampola de Equilíbrio aparece como uma sombra" in cena["narracao"]


def test_a_abertura_de_ciencias_tem_acento(monkeypatch):
    sem_ia(monkeypatch)

    cena = rpg.iniciar_aventura({"materia": "Ciencias", "titulo": "Laboratório Perdido"})

    assert "uma pista sobre Ciências" in cena["narracao"]
    assert "Ciencias" not in " ".join(str(v) for o in cena["opcoes"] for v in o.values())


def test_a_narracao_de_reserva_le_certo():
    memoria = dict(MEMORIA, cicatriz="a passagem pela Câmara Rubra deixou uma marca", objetivo="recuperar o Compasso Real",
                   historico="")
    local, narracao = rpg._narracao_fallback(
        3, "Matematica", "Forja das Evidências", "Forçar entrada na Câmara Rubra.", "Deu certo.",
        memoria, {"titulo": "Guardião Audaz"},
    )

    assert narracao.startswith("Ao sair da Forja das Evidências, a equipe percebe que a acao 'Forçar entrada na Câmara Rubra' deixou")
    assert "uma sombra assinada por Mestre Vesper lembra" in narracao
    assert "O mapa inicial reage ao foco" in narracao
    assert "transformar o perfil de Guardião Audaz em escolha concreta" in narracao


@pytest.mark.parametrize(
    "resultado, trecho",
    [
        ("acertou", "as marcas deixadas na Torre do Debate"),
        ("errou", "as defesas da Torre do Debate reagirem"),
        (None, "A tentativa na Torre do Debate"),
    ],
)
def test_o_resultado_da_fase_usa_o_artigo(monkeypatch, resultado, trecho):
    sem_ia(monkeypatch)
    jornada = rpg.criar_jornada_inicial("Matematica", "Teste")
    escolha = {"rota": "Torre do Debate", "texto": "Entrar.", "impacto_destino": "Conhecimento"}

    cena = rpg.continuar_aventura({"materia": "Matematica", "titulo": ""}, [], "Entrar.", resultado,
                                  {"sucesso": True}, jornada, escolha)

    assert trecho in cena["narracao"]
    assert cena["titulo"] == "Expedição de Matemática"


# ====================== A JORNADA INTEIRA ======================


def _jornada(materia):
    config = {"materia": materia, "titulo": ""}
    jornada = rpg.criar_jornada_inicial(rpg.normalizar_materia(materia), "")
    cena = rpg.iniciar_aventura(config)
    historico = []
    yield cena
    for fase in range(1, rpg.FASES_TOTAIS):
        opcao = cena["opcoes"][fase % len(cena["opcoes"])]
        checagem = rpg.resolver_tentativa_acao(opcao, jornada, fase)
        jornada = rpg.registrar_escolha_jornada(jornada, opcao, fase)
        historico.append({"fase": fase, "acao": opcao["texto"], "rota": opcao["rota"], "status": "Sucesso"})
        cena = rpg.continuar_aventura(config, historico, opcao["texto"], [None, "acertou", "errou"][fase % 3],
                                      checagem, jornada, opcao)
        yield cena


def _textos(cena):
    yield cena["narracao"]
    for opcao in cena["opcoes"]:
        for campo in ("texto", "consequencia_imediata", "cena", "plano", "risco_narrativo",
                      "recompensa_narrativa", "consequencia_completa"):
            yield opcao[campo]


def _nomes():
    nomes = set()
    for nome in rpg._GENERO_NOMES:
        nomes |= {nome, aplicar_acentos_pt(nome)}
    return "|".join(re.escape(n) for n in sorted(nomes, key=len, reverse=True))


@pytest.mark.parametrize("materia", list(rpg.STORY_PRESETS) + ["Geografia"])
def test_a_jornada_inteira_sem_ia_le_certo(monkeypatch, materia):
    sem_ia(monkeypatch)
    nomes = _nomes()
    ameacas = "|".join(re.escape(" ".join(aplicar_acentos_pt(p["ameaca"]).split()[:3])) for p in rpg.STORY_PRESETS.values())
    antagonistas = "|".join(re.escape(aplicar_acentos_pt(p["antagonista"])) for p in rpg.STORY_PRESETS.values())
    defeitos = {
        "sem artigo": rf"(?<![A-Za-zÀ-ÿ])(?:[Ee]m|[Dd]e|[Pp]or|at[eé])\s+(?:{nomes})\b",
        "frase sem artigo": rf"(?:^|[.!?;:]\s+)(?:{nomes})\b",
        "a o": r"(?<![A-Za-zÀ-ÿ])a (?:o|a)(?= )",
        "antes que + indicativo": rf"antes que (?:{ameacas})",
        "aposto aberto": rf"(?:{antagonistas}) (?=[a-zà-ÿ])",
        "sem acento": r"\b(?:contraditorios|chao|inscricao|tera|porem|Ciencias|Expedicao)\b",
    }

    achados = []
    with contextlib.redirect_stdout(io.StringIO()):
        for cena in _jornada(materia):
            # o título vale até a sala do chefe, que tem molde próprio
            assert "Expedicao" not in cena["titulo"]
            for texto in _textos(cena):
                achados += [(nome, texto) for nome, padrao in defeitos.items() if re.search(padrao, texto)]

    assert not achados, achados[:3]


# ====================== A TELA E OS ENIGMAS ======================


def _linha(template: str, trecho: str) -> str:
    html = (RAIZ / "web" / "templates" / template).read_text(encoding="utf-8-sig")
    return next(l.strip() for l in html.splitlines() if trecho in l)


@pytest.mark.parametrize(
    "status, rotulo",
    [("em_andamento", "Em andamento"), ("vitoria", "Vitória"), ("derrota", "Derrota"), ("outro", "outro")],
)
def test_o_status_da_aventura_aparece_com_rotulo(status, rotulo):
    linha = _linha("rpg.html", 'class="pill">{{ {"em_andamento"')

    assert Environment().from_string(linha).render(estado={"status": status}) == f'<span class="pill">{rotulo}</span>'


def test_os_rotulos_fixos_da_tela_tem_acento():
    html = (RAIZ / "web" / "templates" / "rpg.html").read_text(encoding="utf-8-sig")

    assert "<strong>Vitória!</strong>" in html
    assert "Feedback pedagógico" in html
    assert "{{ estado.status }}" not in html


def test_os_enigmas_de_reserva_saem_acentuados(monkeypatch):
    import services.ia.enigma as enigma

    sem_acento = re.compile(r"\b(?:invisivel|vestigios|esta no mapa|le-las|simbolo|porem|decifracao|fumaca)\b")
    vistos = set()
    for materia in ["Portugues", "Historia", "Geografia", "Ciencias", "Biologia", "Matematica", "Fisica", "Quimica", "Arte"]:
        for indice in range(2):
            monkeypatch.setattr(enigma.random, "choice", lambda opcoes, i=indice: opcoes[i])
            vistos.add(aplicar_acentos_pt(enigma._enigma_oracular(materia, "porcentagem")))

    assert len(vistos) == 18
    assert not [v for v in vistos if sem_acento.search(v)]
    assert "Os números não mentem, mas também não se entregam; porcentagem exige decifração." in vistos
