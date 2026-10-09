"""Rede de comportamento do invocar_enigma, antes de mexer nele.

O Oraculo tem 5 tentativas com a IA e um banco offline atras. O que decide
se uma tentativa vale ou vai pro lixo esta espalhado no meio de um loop de
70 linhas, e cada rejeicao repete o mesmo trio "marca o provedor, loga,
continue -- a menos que nao haja provedor, ai break".

Estes testes prendem o COMPORTAMENTO (o que entra, o que sai, quantas vezes
a IA e chamada) para que a refatoracao possa mexer na forma sem mexer no
resultado. Sem isso, extrair funcao daqui seria aposta.
"""

from __future__ import annotations

import pytest

import services.ia.enigma as enigma

QUESTAO_BOA = {
    "enigma": "Nas brumas do templo, um sinal antigo aguarda.",
    "pergunta": "Qual movimento cultural valorizou a retomada da cultura classica?",
    "opcoes": ["O Renascimento", "A Reforma Protestante", "O Iluminismo", "A Revolucao Industrial"],
    "correta": 0,
    "explicacao": [
        {"tipo": "bold", "conteudo": "Entendendo o periodo"},
        {"tipo": "texto", "conteudo": "O movimento retomou a arte e a ciencia da Antiguidade."},
        {"tipo": "resultado", "conteudo": "O Renascimento"},
    ],
    "passos_resolucao": [],
}

QUESTAO_INGLES = {
    "enigma": "In the mist of the temple, an ancient sign waits.",
    "enigma_traducao": "Nas brumas do templo, um sinal antigo aguarda.",
    "pergunta": "Which sentence describes a daily routine?",
    "pergunta_traducao": "Qual frase descreve uma rotina diaria?",
    "opcoes": [
        "She walks to school every morning",
        "She travelled abroad last summer",
        "She will graduate next December",
        "She bought a bicycle yesterday",
    ],
    "opcoes_traducao": [
        "Ela caminha para a escola toda manha",
        "Ela viajou para o exterior no verao passado",
        "Ela vai se formar em dezembro",
        "Ela comprou uma bicicleta ontem",
    ],
    "correta": 0,
    "explicacao": [{"tipo": "resultado", "conteudo": "She walks to school every morning"}],
    "explicacao_traducao": [{"tipo": "resultado", "conteudo": "Ela caminha para a escola"}],
    "passos_resolucao": [{"titulo": "Step", "conteudo": "Look for the simple present", "final": True}],
    "passos_resolucao_traducao": [
        {"titulo": "Passo", "conteudo": "Procure o presente simples", "final": True}
    ],
}


# Exatas sem formula e sem conta: o Oraculo aceita (e conceitual), o
# Laboratorio recusa (existe para cobrar calculo). Quem decide isso e o
# argumento `contexto` que cada modo passa para a validacao.
QUESTAO_EXATAS_CONCEITUAL = {
    "enigma": "Os numeros nao mentem, mas tambem nao se entregam.",
    "pergunta": "Qual medida indica o valor que mais se repete em um conjunto de dados?",
    "opcoes": ["A moda", "A media aritmetica", "A mediana", "O desvio padrao"],
    "correta": 0,
    "formula": "",
    "subformulas": [],
    "legenda_variaveis": "",
    "explicacao": [
        {"tipo": "bold", "conteudo": "Medidas de tendencia central"},
        {"tipo": "texto", "conteudo": "Cada medida responde a uma pergunta diferente."},
        {"tipo": "resultado", "conteudo": "A moda"},
    ],
    "passos_resolucao": [],
}


class IAFalsa:
    """Fila de respostas. Guarda os prompts e os kwargs de cada chamada."""

    def __init__(self, *respostas, provedor="groq"):
        self.respostas = list(respostas)
        self.chamadas: list[dict] = []
        self.provedor = provedor

    def __call__(self, system_prompt, user_prompt, **kwargs):
        self.chamadas.append({"system": system_prompt, "user": user_prompt, **kwargs})
        if not self.respostas:
            return {}
        proxima = self.respostas.pop(0)
        return dict(proxima) if isinstance(proxima, dict) else proxima

    @property
    def n(self) -> int:
        return len(self.chamadas)


@pytest.fixture
def sem_historico(monkeypatch):
    """Isola do session do Flask: historico controlado, escritas gravadas."""
    escrito: list[list[str]] = []
    monkeypatch.setattr(enigma, "_get_historico_oraculo", lambda chave: [])
    monkeypatch.setattr(
        enigma, "_set_historico_oraculo", lambda chave, hist: escrito.append(list(hist))
    )
    return escrito


def instalar(monkeypatch, ia, provedor="groq"):
    monkeypatch.setattr(enigma, "gerar_json_ia", ia)
    monkeypatch.setattr(enigma, "obter_ultimo_provedor_ia", lambda: provedor)
    return ia


# --------------------------------------------------------------------------
# caminho feliz
# --------------------------------------------------------------------------


def test_payload_valido_e_aceito_na_primeira_tentativa(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 1, "tentou de novo mesmo com payload bom"
    assert questao["_origem_geracao"] == "ia"
    assert questao["_provedor_ia"] == "groq"
    assert questao["dificuldade"] == "Medio"
    # as opcoes sao embaralhadas na finalizacao: o indice tem que acompanhar
    assert questao["opcoes"][questao["correta"]] == "O Renascimento"


def test_pergunta_aceita_entra_no_historico(monkeypatch, sem_historico):
    instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert sem_historico, "aceitou a questao e nao anotou no historico"
    assert QUESTAO_BOA["pergunta"] in sem_historico[-1]


@pytest.mark.parametrize(
    "materia, payload, tema",
    [
        ("Historia", QUESTAO_BOA, "Renascimento"),
        ("Ingles", QUESTAO_INGLES, "simple present"),
    ],
)
def test_historico_nao_cresce_sem_limite(monkeypatch, materia, payload, tema):
    # A chave mora no session do Flask, que vai inteiro no cookie: sem teto,
    # uma aula longa estoura o limite de tamanho do cookie. Ingles tem caminho
    # de saida proprio, entao precisa do mesmo teto.
    escrito: list[list[str]] = []
    monkeypatch.setattr(enigma, "_get_historico_oraculo", lambda chave: [f"q{i}" for i in range(30)])
    monkeypatch.setattr(
        enigma, "_set_historico_oraculo", lambda chave, hist: escrito.append(list(hist))
    )
    instalar(monkeypatch, IAFalsa(payload))

    enigma.invocar_enigma(materia, "3o Ano EM", "Medio", tema=tema)

    assert len(escrito[-1]) == 12


# --------------------------------------------------------------------------
# rejeicoes: cada motivo queima o provedor e tenta o proximo
# --------------------------------------------------------------------------


def test_payload_incompleto_queima_o_provedor_e_tenta_de_novo(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa({"pergunta": "so isso"}, QUESTAO_BOA))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 2
    assert "groq" in ia.chamadas[1]["pular_provedores"], "tentou o mesmo provedor de novo"
    assert questao["_origem_geracao"] == "ia"


@pytest.mark.parametrize("lixo", [None, [], ["a", "b"], "texto solto", 42])
def test_resposta_que_nem_e_dicionario_nao_derruba_o_oraculo(monkeypatch, sem_historico, lixo):
    # O provedor as vezes devolve uma lista ou um texto solto em vez do JSON
    # pedido. Sem o guard, isso vira AttributeError no meio do loop -- ou
    # seja, tela de erro pro aluno em vez de questao offline.
    ia = instalar(monkeypatch, IAFalsa(lixo, QUESTAO_BOA))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 2
    assert questao["_origem_geracao"] == "ia"


def test_resposta_composta_espalhada_em_varias_opcoes_e_rejeitada(monkeypatch, sem_historico):
    # A IA as vezes quebra uma resposta de varias partes (uma sequencia, um
    # conjunto-solucao) em alternativas separadas, e ai nenhuma delas esta
    # certa sozinha. Este payload passa na validacao geral de proposito: so
    # a checagem de resposta composta o pega.
    composta_quebrada = {
        **QUESTAO_BOA,
        "pergunta": "Assinale a sequencia correta dos movimentos culturais.",
    }
    ia = instalar(monkeypatch, IAFalsa(composta_quebrada, QUESTAO_BOA))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 2, "aceitou resposta composta espalhada"
    assert "groq" in ia.chamadas[1]["pular_provedores"], "tentou o mesmo provedor de novo"
    assert questao["_origem_geracao"] == "ia"


def test_questao_reprovada_pela_validacao_e_rejeitada(monkeypatch, sem_historico):
    opcoes_repetidas = {
        **QUESTAO_BOA,
        "opcoes": ["O Renascimento", "O Renascimento", "O Iluminismo", "A Reforma"],
    }
    ia = instalar(monkeypatch, IAFalsa(opcoes_repetidas, QUESTAO_BOA))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 2
    assert "groq" in ia.chamadas[1]["pular_provedores"], "tentou o mesmo provedor de novo"
    assert questao["_origem_geracao"] == "ia"


def test_pergunta_ja_vista_e_rejeitada(monkeypatch):
    # Sem isso, a mesma questao voltava toda vez que o aluno pedia outra.
    monkeypatch.setattr(enigma, "_get_historico_oraculo", lambda chave: [QUESTAO_BOA["pergunta"]])
    monkeypatch.setattr(enigma, "_set_historico_oraculo", lambda chave, hist: None)
    outra = {**QUESTAO_BOA, "pergunta": "Qual movimento retomou a arte greco-romana?"}
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA, outra))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 2, "serviu de novo a pergunta que o aluno acabou de ver"
    assert questao["pergunta"] == outra["pergunta"]


def test_sem_provedor_identificado_para_de_tentar(monkeypatch, sem_historico):
    # Se nem da pra saber quem respondeu, nao ha quem pular: insistir so
    # gasta o orcamento de tempo. O certo e cair no offline na hora.
    ia = instalar(monkeypatch, IAFalsa({"pergunta": "incompleto"}), provedor="")

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 1, "insistiu sem ter provedor pra pular"
    assert questao["_origem_geracao"] == "offline"


# --------------------------------------------------------------------------
# fallback offline
# --------------------------------------------------------------------------


def test_cinco_falhas_caem_no_banco_offline(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa(*[{"pergunta": "incompleto"}] * 6))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.n == 5
    assert questao["_origem_geracao"] == "offline"
    assert questao["pergunta"]
    assert len(questao["opcoes"]) == 4


def test_offline_tambem_anota_no_historico(monkeypatch, sem_historico):
    # O fallback offline escolhe por indice deterministico de
    # materia+tema+nivel: sem anotar, repetiria a mesma questao pra sempre.
    instalar(monkeypatch, IAFalsa())

    enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert sem_historico, "caiu no offline e nao anotou nada"


# --------------------------------------------------------------------------
# formato do que sai, por grupo de materia
# --------------------------------------------------------------------------


def test_exatas_no_oraculo_saem_sem_formula_e_sem_passos(monkeypatch, sem_historico):
    # O Oraculo e conceitual; conta com formula e passo a passo e o
    # Laboratorio de Exatas.
    com_formula = {
        **QUESTAO_BOA,
        "formula": "x = -b/2a",
        "subformulas": ["\\Delta = b^2 - 4ac"],
        "legenda_variaveis": "b = coeficiente",
        "passos_resolucao": [{"titulo": "1o Passo", "conteudo": "substituir", "final": True}],
    }
    instalar(monkeypatch, IAFalsa(com_formula))

    questao = enigma.invocar_enigma("Matematica", "3o Ano EM", "Medio", tema="funcoes")

    assert questao["formula"] == ""
    assert questao["subformulas"] == []
    assert questao["legenda_variaveis"] == ""
    assert questao["passos_resolucao"] == []


def test_exatas_conceitual_e_aceita_no_oraculo(monkeypatch, sem_historico):
    # Esta e a diferenca entre o Oraculo e o Laboratorio, e ela vive num
    # unico argumento (contexto="oraculo") passado a validacao. A mesma
    # questao, sem formula e sem conta, e recusada no Laboratorio -- ver
    # test_laboratorio_invocar_enigma.
    instalar(monkeypatch, IAFalsa(QUESTAO_EXATAS_CONCEITUAL))

    questao = enigma.invocar_enigma("Matematica", "3o Ano EM", "Medio", tema="estatistica")

    assert questao["_origem_geracao"] == "ia", "o Oraculo recusou uma questao conceitual"
    assert questao["opcoes"][questao["correta"]] == "A moda"


def test_nao_exatas_saem_sem_passo_numerado(monkeypatch, sem_historico):
    # "1o Passo / 2o Passo" em questao de Historia e mecanica sem sentido.
    com_passos = {
        **QUESTAO_BOA,
        "passos_resolucao": [{"titulo": "1o Passo", "conteudo": "leia o enunciado", "final": False}],
    }
    instalar(monkeypatch, IAFalsa(com_passos))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert questao["passos_resolucao"] == []
    assert questao["explicacao"], "trocou os passos por nada"
    assert questao["explicacao"][0]["tipo"] == "bold"


def test_ingles_completo_e_preservado_com_os_dois_idiomas(monkeypatch, sem_historico):
    instalar(monkeypatch, IAFalsa(QUESTAO_INGLES))

    questao = enigma.invocar_enigma("Ingles", "3o Ano EM", "Medio", tema="simple present")

    assert questao["_origem_geracao"] == "ia", "descartou uma questao de ingles boa"
    assert questao["pergunta"] == QUESTAO_INGLES["pergunta"]
    assert questao["pergunta_traducao"] == QUESTAO_INGLES["pergunta_traducao"]
    assert len(questao["opcoes"]) == len(questao["opcoes_traducao"]) == 4


def test_ingles_sem_os_pares_traduzidos_cai_na_resposta_offline(monkeypatch, sem_historico):
    # Ingles exige os pares traduzidos; sem eles a tela fica sem a coluna em
    # portugues. Aqui falta so a traducao -- o resto do payload esta certo.
    sem_traducao = {k: v for k, v in QUESTAO_INGLES.items() if not k.endswith("_traducao")}
    instalar(monkeypatch, IAFalsa(sem_traducao))

    questao = enigma.invocar_enigma("Ingles", "3o Ano EM", "Medio", tema="simple present")

    assert questao["pergunta"] != sem_traducao["pergunta"], "serviu ingles sem traducao"
    assert questao["pergunta_traducao"], "questao de ingles saiu sem traducao"
    assert len(questao["opcoes"]) == len(questao["opcoes_traducao"])


def test_ingles_respondido_em_portugues_cai_na_resposta_offline(monkeypatch, sem_historico):
    # Acontece de verdade: o provedor preenche todos os campos, inclusive os
    # de traducao, mas escreve o conteudo principal em portugues -- o que
    # esvazia o proposito da aula de ingles. O payload esta completo de
    # proposito: so a checagem de idioma o pega.
    em_portugues = {
        **QUESTAO_INGLES,
        "enigma": QUESTAO_BOA["enigma"],
        "pergunta": QUESTAO_BOA["pergunta"],
        "opcoes": list(QUESTAO_BOA["opcoes"]),
        "explicacao": list(QUESTAO_BOA["explicacao"]),
    }
    instalar(monkeypatch, IAFalsa(em_portugues))

    questao = enigma.invocar_enigma("Ingles", "3o Ano EM", "Medio", tema="simple present")

    assert questao["pergunta"] != em_portugues["pergunta"], "serviu aula de ingles em portugues"
    assert questao["pergunta_traducao"], "questao de ingles saiu sem traducao"


# --------------------------------------------------------------------------
# enigma
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "enigma_ruim",
    [
        "",
        "Qual movimento cultural valorizou a retomada da cultura classica?",
        "Assinale a alternativa correta.",
        "Voce sabe o que e o Renascimento?",
    ],
)
def test_enigma_literal_e_trocado_por_profecia(monkeypatch, sem_historico, enigma_ruim):
    instalar(monkeypatch, IAFalsa({**QUESTAO_BOA, "enigma": enigma_ruim}))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert questao["enigma"] != enigma_ruim
    assert not questao["enigma"].endswith("?"), "o enigma virou pergunta"


def test_enigma_bom_e_preservado(monkeypatch, sem_historico):
    instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert questao["enigma"] == QUESTAO_BOA["enigma"]


# --------------------------------------------------------------------------
# prompts
# --------------------------------------------------------------------------


def test_prompt_leva_materia_ano_nivel_e_tema(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    enigma.invocar_enigma("Historia", "3o Ano EM", "Dificil", tema="Renascimento")

    user = ia.chamadas[0]["user"]
    assert "Historia" in user
    assert "3o Ano EM" in user
    assert "Dificil" in user
    assert "Renascimento" in user


def test_tema_vazio_e_sorteado_uma_vez_so(monkeypatch, sem_historico):
    # O tema e sorteado uma vez so: se o prompt e o fallback sorteassem
    # separado, o aluno pediria um tema e receberia outro.
    ia = instalar(monkeypatch, IAFalsa(), provedor="")

    questao = enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="")

    assert questao["_origem_geracao"] == "offline"
    assert ia.n == 1


def test_prompt_de_exatas_pede_questao_conceitual(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    enigma.invocar_enigma("Matematica", "3o Ano EM", "Medio", tema="funcoes")

    user = ia.chamadas[0]["user"]
    assert "Regras adicionais para Exatas no Oraculo" in user
    assert "nao inclua formula" in user
    assert "Regras adicionais para Linguagens" not in user


def test_prompt_de_humanas_proibe_passo_numerado(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    user = ia.chamadas[0]["user"]
    assert "Regras adicionais para Linguagens" in user
    assert "Regras adicionais para Exatas no Oraculo" not in user


def test_prompt_de_ingles_pede_os_dois_idiomas(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    enigma.invocar_enigma("Ingles", "3o Ano EM", "Medio", tema="verb to be")

    user = ia.chamadas[0]["user"]
    assert "Regras adicionais para a materia de Ingles" in user
    assert "enigma_traducao" in user
    assert ia.chamadas[0]["max_tokens"] == 1400, "ingles precisa de mais tokens: sai em dobro"


def test_prompt_das_demais_materias_usa_orcamento_menor(monkeypatch, sem_historico):
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    enigma.invocar_enigma("Historia", "3o Ano EM", "Medio", tema="Renascimento")

    assert ia.chamadas[0]["max_tokens"] == 900


@pytest.mark.parametrize("materia", ["Matematica", "Historia", "Ingles"])
def test_regra_de_resposta_composta_vale_para_toda_materia(monkeypatch, sem_historico, materia):
    ia = instalar(monkeypatch, IAFalsa(QUESTAO_BOA))

    enigma.invocar_enigma(materia, "3o Ano EM", "Medio", tema="tema")

    assert "Regra geral para respostas compostas" in ia.chamadas[0]["user"]
