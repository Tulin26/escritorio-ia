"""A letra que a explicação do ENEM cita tem de ser a da tela.

A IA escreve a explicação na ordem em que ELA pôs as alternativas ("... que
corresponde à alternativa B"), e o ENEM embaralha depois. Na captura 07c do TG
(10/09/2026) a certa aparecia como C e a explicação dizia "a alternativa A está
correta". Numa amostra de 16/09/2026, 5 das 10 explicações da IA citavam a
letra -- sempre a da certa, na ordem original. A Batalha contra Chefes usa o
mesmo gerador (`gerar_questao_enem`).
"""
from __future__ import annotations

import copy
import itertools
import re

import pytest

import services.enem_service as enem
from services.enem_service import _embaralhar_alternativas_questao, _trocar_letras_citadas

LETRAS = "ABCDE"
# A ordem invertida: A<->E, B<->D, C fica.
INVERTIDA = {"A": "E", "B": "D", "C": "C", "D": "B", "E": "A"}


def questao_da_07c(frase_final: str = "Portanto, a alternativa A está correta.") -> dict:
    """A questão da captura, com a certa em A na ordem da IA."""
    return {
        "pergunta": (
            "Uma escola organizou uma excursão a um parque a 120 km da cidade. O ônibus "
            "consome 15 km por litro de diesel, a R$ 5,80 o litro. Considerando ida e "
            "volta, qual será o gasto total com diesel?"
        ),
        "alternativas": ["R$ 92,80", "R$ 78,40", "R$ 64,00", "R$ 103,20", "R$ 115,60"],
        "correta": "R$ 92,80",
        "explicacao": [
            {"tipo": "bold", "conteudo": "Cálculo do consumo de combustível"},
            {"tipo": "texto", "conteudo": "A distância total é 240 km; com 15 km/L, são 16 L."},
            {"tipo": "resultado", "conteudo": f"O custo é 16 L × R$ 5,80 = R$ 92,80. {frase_final}"},
        ],
    }


def na_ordem(ordem):
    """Um random.shuffle que sempre põe os itens nesta ordem."""
    def embaralhar(itens):
        itens[:] = [itens[i] for i in ordem]

    return embaralhar


def letra_da_certa(questao: dict) -> str:
    return LETRAS[questao["alternativas"].index(questao["correta"])]


# ====================== O CASO DA CAPTURA ======================


def test_a_captura_07c_passa_a_citar_a_letra_da_tela(monkeypatch):
    """Na captura, R$ 92,80 (a A da IA) foi parar na terceira posição."""
    monkeypatch.setattr(enem.random, "shuffle", na_ordem((1, 2, 0, 3, 4)))

    questao = _embaralhar_alternativas_questao(questao_da_07c())

    assert letra_da_certa(questao) == "C"
    assert questao["explicacao"][-1]["conteudo"].endswith("a alternativa C está correta.")


def test_a_letra_acompanha_a_certa_em_todas_as_ordens(monkeypatch):
    for ordem in itertools.permutations(range(5)):
        monkeypatch.setattr(enem.random, "shuffle", na_ordem(ordem))

        questao = _embaralhar_alternativas_questao(questao_da_07c())

        esperado = f"a alternativa {letra_da_certa(questao)} está correta."
        assert questao["explicacao"][-1]["conteudo"].endswith(esperado), ordem


def test_o_resto_da_explicacao_nao_muda(monkeypatch):
    monkeypatch.setattr(enem.random, "shuffle", na_ordem((4, 3, 2, 1, 0)))
    original = questao_da_07c()

    questao = _embaralhar_alternativas_questao(copy.deepcopy(original))

    assert questao["explicacao"][:2] == original["explicacao"][:2]


# ====================== OS FORMATOS ======================


@pytest.mark.parametrize(
    "texto, esperado",
    [
        # os quatro vistos na amostra da IA
        ("R$ 1.464,00, que corresponde à alternativa B.", "R$ 1.464,00, que corresponde à alternativa D."),
        ("A alternativa B contempla a mobilidade.", "A alternativa D contempla a mobilidade."),
        ("Por isso, a alternativa B está correta:", "Por isso, a alternativa D está correta:"),
        ("Alternativa B está correta.", "Alternativa D está correta."),
        # os outros jeitos de dizer a mesma coisa
        ("A resposta é a letra B.", "A resposta é a letra D."),
        ("A alternativa correta é a B.", "A alternativa correta é a D."),
        ("Gabarito: B", "Gabarito: D"),
        ("(alternativa A)", "(alternativa E)"),
        ("Alternativa (A).", "Alternativa (E)."),
        ("As alternativas A, B e D estão erradas.", "As alternativas E, D e B estão erradas."),
        ("As alternativas A ou B.", "As alternativas E ou D."),
    ],
)
def test_a_letra_citada_e_trocada(texto, esperado):
    assert _trocar_letras_citadas(texto, INVERTIDA) == esperado


@pytest.mark.parametrize(
    "texto, rotulo",
    [
        ("Resposta correta: 4,5 A", "ampere -- 44 questões do banco de reserva"),
        ("A utilização de imagens aproxima o público.", "artigo"),
        ("A alternativa é a mais adequada ao contexto.", "sem letra"),
        ("A alternativa Ecológica é a mais barata.", "palavra que começa com A-E"),
        ("Alternativamente, A e B podem ser somados.", "outra palavra"),
        ("A vitamina B e a classe C.", "letra que não é de alternativa"),
        ("A empresa comparou a opção A com a opção B.", "opção nomeia plano no enunciado"),
        ("O item B do edital.", "item também"),
        ("A letra da música fala de saudade.", "letra de música"),
    ],
)
def test_o_que_nao_cita_alternativa_fica_como_esta(texto, rotulo):
    assert _trocar_letras_citadas(texto, INVERTIDA) == texto, rotulo


def test_os_passos_da_resolucao_tambem_acompanham(monkeypatch):
    """O ENEM e a Batalha mostram os passos da resolução no cartão de
    resultado; eles passam pela mesma troca."""
    monkeypatch.setattr(enem.random, "shuffle", na_ordem((4, 3, 2, 1, 0)))
    original = questao_da_07c()
    original["passos_resolucao"] = [
        {"titulo": "1º Passo", "conteudo": "240 km ÷ 15 km/L = 16 L"},
        {"titulo": "Resultado Final", "conteudo": "16 × 5,80 = 92,80: alternativa A", "final": True},
    ]

    questao = _embaralhar_alternativas_questao(original)

    assert questao["passos_resolucao"][-1]["conteudo"] == "16 × 5,80 = 92,80: alternativa E"
    assert questao["passos_resolucao"][0] == original["passos_resolucao"][0]


def test_enunciado_que_usa_alternativa_na_historia_nao_e_mexido(monkeypatch):
    """Quando o próprio enunciado fala em "alternativa A", a letra da
    explicação pode ser a da história, e não a da lista."""
    monkeypatch.setattr(enem.random, "shuffle", na_ordem((4, 3, 2, 1, 0)))
    original = questao_da_07c("A alternativa A do plano é a mais barata.")
    original["pergunta"] = "A prefeitura avalia a alternativa A (ônibus) e a alternativa B (metrô). " + original["pergunta"]

    questao = _embaralhar_alternativas_questao(copy.deepcopy(original))

    assert questao["explicacao"] == original["explicacao"]


def test_seis_alternativas_nao_quebram(monkeypatch):
    """A tela só tem letra até E; a sexta alternativa não entra na troca."""
    monkeypatch.setattr(enem.random, "shuffle", na_ordem((5, 0, 1, 2, 3, 4)))
    original = questao_da_07c()
    original["alternativas"].append("R$ 120,00")

    questao = _embaralhar_alternativas_questao(original)

    assert questao["alternativas"][:2] == ["R$ 120,00", "R$ 92,80"]
    assert questao["explicacao"][-1]["conteudo"].endswith("a alternativa B está correta.")


# ====================== O CAMINHO DA IA ======================


def test_a_questao_da_ia_sai_com_a_letra_da_tela(monkeypatch):
    """O formato real da IA: alternativas rotuladas "A) ", explicação citando
    a letra na ordem dela."""
    def ia(*_args, **_kwargs):
        return {
            "pergunta": "Qual estratégia amplia a mobilidade e distribui os benefícios de forma justa?",
            "alternativas": [
                "A) Construir ciclovias apenas nas avenidas principais",
                "B) Destinar recursos para campanhas de conscientização",
                "C) Priorizar ciclovias nos bairros de menor renda",
                "D) Oferecer subsídios para a compra de bicicletas",
                "E) Implementar um programa de bicicletas compartilhadas",
            ],
            "correta": "C) Priorizar ciclovias nos bairros de menor renda",
            "explicacao": [
                {"tipo": "resultado", "conteudo": "A alternativa C propõe a estratégia que alinha mobilidade e justiça social."},
            ],
        }

    monkeypatch.setattr(enem, "gerar_json_ia", ia)
    for ordem in [(0, 1, 2, 3, 4), (2, 0, 1, 3, 4), (4, 3, 2, 1, 0), (1, 2, 3, 4, 0)]:
        monkeypatch.setattr(enem.random, "shuffle", na_ordem(ordem))

        questao = enem._gerar_via_ia("Ciencias Humanas e Sociais Aplicadas", "Medio")

        assert questao is not None
        assert questao["correta"] == "Priorizar ciclovias nos bairros de menor renda"
        assert questao["explicacao"][0]["conteudo"].startswith(f"A alternativa {letra_da_certa(questao)} propõe"), ordem


# ====================== O BANCO DE RESERVA ======================


def test_o_banco_de_reserva_nao_tem_letra_para_trocar():
    """Medido em 16/09/2026: nenhuma das 2.235 questões de reserva cita
    alternativa pela letra. As 44 que escrevem "Resposta correta: 4,5 A" falam
    de ampere -- e têm de continuar falando."""
    banco = enem._fallback_matematica_variantes()
    for area in enem.AREAS_ENEM:
        banco += enem._FALLBACK_POR_AREA.get(area, []) + enem._fallback_autoral_por_area(area)

    def trocar(texto):
        return _trocar_letras_citadas(texto, INVERTIDA)

    amperes = 0
    for questao in banco:
        for campo in ("explicacao", "passos_resolucao"):
            valor = questao.get(campo, [])
            assert enem._corrigir_bloco_textual(valor, trocar) == valor
            amperes += bool(re.search(r"Resposta correta: [\d,]+ A\b", str(valor)))
    assert amperes >= 44
