"""Rede de comportamento do invocar_enigma_laboratorio, antes de mexer nele.

Ao contrario do Oraculo, esta funcao NAO tem loop: uma tentativa, e devolve
{} quando a resposta nao serve. Quem insiste e o calculo_service, que chama
de novo pulando o provedor que falhou. Entao o contrato que importa aqui e
estreito e preciso:

  serve   -> dict com a questao, _origem_geracao="ia" e _provedor_ia
  nao serve -> {} exatamente, com o motivo no log

Estes testes prendem esse contrato para que a extracao possa mexer na forma
sem mexer no resultado.
"""

from __future__ import annotations

import json

import pytest

import services.ia.enigma as enigma

# Fisica em m/s: passa na checagem de "questao de laboratorio tem conta".
QUESTAO_BOA = {
    "enigma": "O movimento deixa rastros onde os olhos veem apenas passagem.",
    "pergunta": "Um corpo percorre 100 m em 5 s. Qual a velocidade media?",
    "opcoes": ["20 m/s", "15 m/s", "25 m/s", "10 m/s"],
    "correta": 0,
    "formula": "v = d/t",
    "subformulas": [],
    "legenda_variaveis": "v = velocidade, d = distancia, t = tempo",
    "explicacao": [
        {"tipo": "bold", "conteudo": "Velocidade media"},
        {"tipo": "texto", "conteudo": "Divida a distancia pelo tempo."},
        {"tipo": "resultado", "conteudo": "20 m/s"},
    ],
    "passos_resolucao": [
        {"titulo": "1o Passo", "conteudo": "v = 100/5", "final": False},
        {"titulo": "Resultado Final", "conteudo": "v = 20 m/s", "final": True},
    ],
}


# "sistema" no enunciado pede resposta de varias partes, mas nenhuma das
# alternativas traz mais de um valor. Passa na validacao; so a checagem de
# resposta composta o pega.
QUESTAO_COMPOSTA_QUEBRADA = {
    "enigma": "Forcas silenciosas disputam o destino do problema.",
    "pergunta": "Em um sistema com 2 resistores de 10 ohm e 20 ohm em serie, qual a resistencia total?",
    "opcoes": ["30 ohm", "15 ohm", "10 ohm", "200 ohm"],
    "correta": 0,
    "formula": "R = R1 + R2",
    "subformulas": [],
    "legenda_variaveis": "R = resistencia total",
    "explicacao": [{"tipo": "resultado", "conteudo": "30 ohm"}],
    "passos_resolucao": [
        {"titulo": "1o Passo", "conteudo": "R = 10 + 20", "final": False},
        {"titulo": "Resultado Final", "conteudo": "R = 30 ohm", "final": True},
    ],
}


class IAFalsa:
    """Uma resposta so: esta funcao nao tem retry proprio."""

    def __init__(self, resposta, provedor="groq"):
        self.resposta = resposta
        self.chamadas: list[dict] = []
        self.provedor = provedor

    def __call__(self, system_prompt, user_prompt, **kwargs):
        self.chamadas.append({"system": system_prompt, "user": user_prompt, **kwargs})
        return dict(self.resposta) if isinstance(self.resposta, dict) else self.resposta

    @property
    def n(self) -> int:
        return len(self.chamadas)


def instalar(monkeypatch, resposta, provedor="groq"):
    ia = IAFalsa(resposta, provedor=provedor)
    monkeypatch.setattr(enigma, "gerar_json_ia", ia)
    monkeypatch.setattr(enigma, "obter_ultimo_provedor_ia", lambda: provedor)
    return ia


def invocar(**kwargs):
    base = {"materia": "Fisica", "ano_escolar": "1o Ano EM", "nivel": "Medio", "tema": "cinematica"}
    base.update(kwargs)
    return enigma.invocar_enigma_laboratorio(**base)


# --------------------------------------------------------------------------
# contrato: uma tentativa, ou a questao ou {}
# --------------------------------------------------------------------------


def test_payload_valido_vira_questao(monkeypatch):
    ia = instalar(monkeypatch, QUESTAO_BOA)

    questao = invocar()

    assert ia.n == 1, "esta funcao nao tem retry proprio"
    assert questao["_origem_geracao"] == "ia"
    assert questao["_provedor_ia"] == "groq"
    assert questao["dificuldade"] == "Medio"
    assert questao["formula"], "laboratorio sem formula nao serve"
    assert questao["opcoes"][questao["correta"]] == "20 m/s"


def test_nao_tenta_de_novo_por_conta_propria(monkeypatch):
    # Quem insiste e o calculo_service, pulando o provedor que falhou. Se
    # esta funcao tambem insistisse, o orcamento de tempo seria consumido
    # duas vezes e o Gunicorn derrubaria o worker.
    ia = instalar(monkeypatch, {"pergunta": "incompleto"})

    invocar()

    assert ia.n == 1


@pytest.mark.parametrize(
    "ruim, rotulo",
    [
        ({"pergunta": "so isso"}, "faltam opcoes e correta"),
        ({}, "vazio"),
        (None, "nem e dicionario"),
        (["a", "b"], "lista"),
        ("texto solto", "string"),
        (42, "numero"),
    ],
)
def test_payload_que_nao_serve_devolve_dicionario_vazio(monkeypatch, ruim, rotulo):
    instalar(monkeypatch, ruim)

    assert invocar() == {}, rotulo


def test_resposta_composta_espalhada_e_recusada(monkeypatch, capsys):
    # Quando o enunciado pede varias partes (um sistema, uma sequencia, um
    # conjunto-solucao), a resposta inteira tem que caber numa alternativa
    # so. Este payload passa na validacao de proposito: so a checagem de
    # resposta composta o pega.
    instalar(monkeypatch, QUESTAO_COMPOSTA_QUEBRADA)

    assert invocar() == {}
    saida = capsys.readouterr().out
    assert "resposta-composta-inconsistente" in saida
    assert "pergunta=" in saida, "o log nao mostra a questao rejeitada"


def test_questao_reprovada_pela_validacao_e_recusada(monkeypatch):
    instalar(monkeypatch, {**QUESTAO_BOA, "opcoes": ["20 m/s", "20 m/s", "15 m/s", "10 m/s"]})

    assert invocar() == {}


def test_exatas_conceitual_e_recusada_no_laboratorio(monkeypatch):
    # O outro lado de test_exatas_conceitual_e_aceita_no_oraculo: a MESMA
    # questao, os dois modos, resultados opostos. O que separa os dois e o
    # argumento `contexto` passado a validacao -- os dois modos passam pela
    # mesma funcao de rejeicao, entao esta dupla de testes e o que impede
    # um deles de herdar a regra do outro em silencio.
    conceitual = {
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
    instalar(monkeypatch, conceitual)

    assert invocar(materia="Matematica", tema="estatistica") == {}


def test_questao_sem_conta_e_recusada(monkeypatch):
    # O Laboratorio existe para exigir calculo; questao conceitual e do
    # Oraculo. Sem formula, nao passa.
    conceitual = {
        **QUESTAO_BOA,
        "pergunta": "O que e velocidade media?",
        "opcoes": ["A razao entre distancia e tempo", "A soma", "O produto", "A diferenca"],
        "formula": "",
        "explicacao": [{"tipo": "resultado", "conteudo": "A razao entre distancia e tempo"}],
        "passos_resolucao": [],
    }
    instalar(monkeypatch, conceitual)

    assert invocar() == {}


# --------------------------------------------------------------------------
# o que vai para a IA
# --------------------------------------------------------------------------


def test_prompt_leva_materia_ano_nivel_e_tema(monkeypatch):
    ia = instalar(monkeypatch, QUESTAO_BOA)

    invocar(materia="Quimica", ano_escolar="2o Ano EM", nivel="Dificil", tema="pH")

    user = ia.chamadas[0]["user"]
    assert "Quimica" in user
    assert "2o Ano EM" in user
    assert "Dificil" in user
    assert "pH" in user
    assert "Alquimista Numerico" in ia.chamadas[0]["system"]
    assert "Quimica" in ia.chamadas[0]["system"], "o system prompt e por materia"


def test_prompt_exige_questao_numerica(monkeypatch):
    ia = instalar(monkeypatch, QUESTAO_BOA)

    invocar()

    user = ia.chamadas[0]["user"]
    assert "a questao deve ser numerica, nunca teorica" in user
    assert "a pergunta deve ter valores explicitos" in user


def test_ensino_medio_e_fundamental_recebem_regras_diferentes(monkeypatch):
    ia_em = instalar(monkeypatch, QUESTAO_BOA)
    invocar(ano_escolar="3o Ano EM", materia="Matematica")
    user_em = ia_em.chamadas[0]["user"]

    ia_ef = instalar(monkeypatch, QUESTAO_BOA)
    invocar(ano_escolar="7o Ano EF", materia="Matematica")
    user_ef = ia_ef.chamadas[0]["user"]

    assert "Regras curriculares para Ensino Fundamental" in user_ef
    assert "Regras curriculares para Ensino Fundamental" not in user_em

    # A regra que protege o aluno do EF de receber conteudo de EM.
    assert "nao use progressao aritmetica" in user_ef
    assert "Bhaskara" in user_em


def test_orcamento_de_tempo_e_repassado(monkeypatch):
    # O Laboratorio compartilha um teto de tempo entre as tentativas que o
    # calculo_service faz. Se o prazo nao chegasse ate aqui, cada tentativa
    # usaria o orcamento inteiro do zero.
    ia = instalar(monkeypatch, QUESTAO_BOA)

    enigma.invocar_enigma_laboratorio("Fisica", "1o Ano EM", "Medio", deadline_seconds=7.5)

    assert ia.chamadas[0]["deadline_seconds"] == 7.5


def test_provedores_a_pular_sao_repassados(monkeypatch):
    ia = instalar(monkeypatch, QUESTAO_BOA)

    enigma.invocar_enigma_laboratorio("Fisica", "1o Ano EM", "Medio", pular_provedores={"groq"})

    assert ia.chamadas[0]["pular_provedores"] == {"groq"}


def test_orcamento_de_tokens_nao_muda_por_materia(monkeypatch):
    for materia in ("Matematica", "Fisica", "Quimica", "Ciencias"):
        ia = instalar(monkeypatch, QUESTAO_BOA)
        invocar(materia=materia)
        assert ia.chamadas[0]["max_tokens"] == 1500, materia


def test_tema_vazio_e_sorteado_e_vai_para_o_prompt(monkeypatch):
    ia = instalar(monkeypatch, QUESTAO_BOA)

    invocar(tema="")

    user = ia.chamadas[0]["user"]
    linha_tema = [ln for ln in user.splitlines() if ln.startswith("Tema:")]
    assert linha_tema, "o prompt perdeu a linha do tema"
    assert linha_tema[0].strip() != "Tema:", "mandou tema vazio para a IA"


# --------------------------------------------------------------------------
# enigma
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "enigma_ruim",
    [
        "",
        "Um corpo percorre 100 m em 5 s. Qual a velocidade media?",
        "Assinale a alternativa correta.",
        "Voce consegue achar a velocidade?",
    ],
)
def test_enigma_literal_e_trocado_por_profecia(monkeypatch, enigma_ruim):
    instalar(monkeypatch, {**QUESTAO_BOA, "enigma": enigma_ruim})

    questao = invocar()

    assert questao["enigma"] != enigma_ruim
    assert not questao["enigma"].endswith("?"), "o enigma virou pergunta"


def test_enigma_bom_e_preservado(monkeypatch):
    instalar(monkeypatch, QUESTAO_BOA)

    questao = invocar()

    assert questao["enigma"] == QUESTAO_BOA["enigma"]


def test_enigma_sai_da_materia_e_do_tema(monkeypatch):
    instalar(monkeypatch, {**QUESTAO_BOA, "enigma": ""})

    questao = invocar(tema="lei de Ohm")

    assert "lei de Ohm" in questao["enigma"], "o enigma generico ignorou o tema"


# --------------------------------------------------------------------------
# log de rejeicao: e por ele que se descobre se a validacao esta calibrada
# --------------------------------------------------------------------------


def test_log_de_rejeicao_diz_o_motivo_e_mostra_a_questao(monkeypatch, capsys):
    # MELHORIA ja existente: sem o resumo, o log dizia so o motivo e era
    # impossivel saber, so por ele, se a validacao acertou em rejeitar ou
    # se e ela que esta calibrada errado.
    instalar(monkeypatch, {**QUESTAO_BOA, "opcoes": ["20 m/s", "20 m/s", "15 m/s", "10 m/s"]})

    invocar()

    saida = capsys.readouterr().out
    assert "rejeitado no laboratorio" in saida
    assert "opcoes-repetidas" in saida
    assert "pergunta=" in saida, "o log nao mostra a questao que foi rejeitada"
    assert "velocidade media" in saida


def test_log_de_rejeicao_traz_a_questao_inteira_em_json(monkeypatch, capsys):
    # Investigacao de 14/09/2026: das 22 recusas reais do Laboratorio, 11 nao
    # davam para julgar -- as regras que mais recusam olham as alternativas,
    # e o log so tinha pergunta e resultado.
    opcoes = ["20 m/s", "20 m/s", "15 m/s", "10 m/s"]
    instalar(monkeypatch, {**QUESTAO_BOA, "opcoes": opcoes})

    invocar()

    linha = next(l for l in capsys.readouterr().out.splitlines() if "rejeitado no laboratorio" in l)
    questao = json.loads(linha.split("questao=", 1)[1])
    assert questao["opcoes"] == opcoes
    assert questao["correta"] == 0
    assert questao["formula"] == "v = d/t"
    assert [passo["conteudo"] for passo in questao["passos"]] == ["v = 100/5", "v = 20 m/s"]
    assert questao["passos"][-1]["final"] is True
    assert questao["resultado"] == ["20 m/s"]


def test_questao_longa_continua_json_valido_no_log():
    linha = enigma.questao_para_log({"pergunta": "x" * 5000, "opcoes": ["y" * 500] * 4, "passos_resolucao": "nao e lista"})

    questao = json.loads(linha)
    assert len(linha) < 1500
    assert questao["passos"] == []


def test_log_de_rejeicao_sai_calado_quando_nao_ha_provedor(monkeypatch, capsys):
    # Sem provedor identificado nao ha o que registrar contra ninguem.
    instalar(monkeypatch, {"pergunta": "incompleto"}, provedor="")

    assert invocar() == {}
    assert "rejeitado no laboratorio" not in capsys.readouterr().out


def test_payload_incompleto_tambem_aparece_no_log(monkeypatch, capsys):
    instalar(monkeypatch, {"pergunta": "so isso"})

    invocar()

    saida = capsys.readouterr().out
    assert "payload-incompleto" in saida
    assert "so isso" in saida


# --------------------------------------------------------------------------
# resposta final fora dos passos: nasceu so registrando (93431e9, 13/09) e
# recusa desde 02/10/2026 -- o caminho de observacao continua (ver
# observar_questao_gerada), hoje sem regra nenhuma nele
# --------------------------------------------------------------------------

# Do log de 11/09/2026, como chegou ao aluno: a resolucao para em
# P_d = 212,5, e a alternativa correta e 229,5.
QUESTAO_DESCONTO = {
    "enigma": "O preço troca de roupa duas vezes antes de chegar ao caixa.",
    "pergunta": (
        "Um produto custa R$ 250,00. Recebe 15% de desconto e, sobre o preço com "
        "desconto, incide um imposto de 8%. Qual o preço final?"
    ),
    "opcoes": ["237,0", "240,0", "225,0", "229,5"],
    "correta": 3,
    "formula": "P_f = P_0 (1 - d)(1 + t)",
    "subformulas": [],
    "legenda_variaveis": "P_0 = preço original; d = desconto (decimal); t = imposto (decimal); P_f = preço final",
    "explicacao": [
        {"tipo": "bold", "conteudo": "Cálculo do preço final"},
        {"tipo": "texto", "conteudo": "Aplica-se primeiro o desconto e depois o imposto sobre o preço já descontado."},
        {"tipo": "resultado", "conteudo": "Preço final = R$ 229,5"},
    ],
    "passos_resolucao": [
        {"titulo": "1º Passo", "conteudo": "P_0 = 250, d = 0,15, t = 0,08"},
        {"titulo": "2º Passo", "conteudo": "P_d = 250 \\times 0,85 = 212,5"},
    ],
}


def test_resolucao_que_para_no_meio_e_recusada_com_a_questao_no_log(monkeypatch, capsys):
    instalar(monkeypatch, QUESTAO_DESCONTO)

    questao = invocar(materia="Matematica", tema="porcentagem")

    assert questao == {}, "a resolucao que para no meio nao pode chegar ao aluno"
    saida = capsys.readouterr().out
    assert "rejeitado no laboratorio: resposta-final-fora-dos-passos" in saida
    assert "R$ 250,00" in saida, "o log nao mostra qual questao foi recusada"
    assert "questao={" in saida
    assert "observacao" not in saida


def test_questao_boa_nao_gera_observacao(monkeypatch, capsys):
    instalar(monkeypatch, QUESTAO_BOA)

    assert invocar()
    assert "observacao" not in capsys.readouterr().out


def test_erro_na_observacao_nao_custa_a_questao(monkeypatch, capsys):
    """Uma regra que so registra nao pode derrubar a questao por defeito proprio."""
    instalar(monkeypatch, QUESTAO_BOA)

    def regra_com_defeito(*args, **kwargs):
        raise RuntimeError("regra com defeito")

    monkeypatch.setattr(enigma, "observar_questao_gerada", regra_com_defeito)

    questao = invocar()

    assert questao and questao["_origem_geracao"] == "ia"
    assert "observacao do laboratorio falhou" in capsys.readouterr().out
