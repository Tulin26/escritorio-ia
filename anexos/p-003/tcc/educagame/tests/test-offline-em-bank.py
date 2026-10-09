from __future__ import annotations

from collections import Counter

from core.config import MATERIAS
from services.banks.em import (
    BANCO_OFFLINE_EM,
    QUESTOES_POR_MATERIA_EM,
    QUESTOES_POR_TEMA_EM,
    _explicacao_para_materia,
    _explicacao_teorica_exatas,
    _opcoes_realistas,
    _opcoes_teoricas_exatas,
    _pergunta_realista,
    _pergunta_teorica_exatas,
    eh_ensino_medio,
    gerar_questao_offline_em,
    listar_questoes_em,
)
from services.banks.fundamental import gerar_questao_offline_ef


def test_banco_offline_flask_tem_50_questoes_por_tema():
    assert set(BANCO_OFFLINE_EM) == set(MATERIAS)
    for materia in MATERIAS:
        questoes = listar_questoes_em(materia)
        assert len(questoes) == QUESTOES_POR_MATERIA_EM
        assert all(questao["materia"] == materia for questao in questoes)
        assert all(len(questao["opcoes"]) == 4 for questao in questoes)
        contagem_temas = Counter(questao["objeto_conhecimento"] for questao in questoes)
        assert contagem_temas
        assert all(total >= QUESTOES_POR_TEMA_EM for total in contagem_temas.values())
        assert all(questao.get("area_bncc") for questao in questoes)
        assert all(questao.get("competencia_bncc") for questao in questoes)
        assert all(questao.get("habilidade_bncc") for questao in questoes)
        assert all(questao.get("fonte_bncc") for questao in questoes)


def test_gerar_questao_offline_em_filtra_por_tema_quando_possivel():
    questao = gerar_questao_offline_em("Matematica", "probabilidade", "Medio")

    assert questao["materia"] == "Matematica"
    assert questao["tema_usado"].startswith("probabilidade")
    assert questao["_origem_geracao"] == "offline"


def test_gerar_questao_offline_em_consegue_evitar_repeticao():
    primeira = gerar_questao_offline_em("Matematica", "", "Medio")
    segunda = gerar_questao_offline_em("Matematica", "", "Medio", evitar_ids={primeira["id_offline"]})

    assert segunda["id_offline"] != primeira["id_offline"]


def test_banco_offline_varia_opcoes_e_posicao_correta():
    questoes = listar_questoes_em("Matematica")[:8]

    assert len({tuple(questao["opcoes"]) for questao in questoes}) > 1
    assert len({questao["correta"] for questao in questoes}) > 1


def test_banco_offline_tem_enunciados_contextualizados():
    # MELHORIA: services/oraculo_conteudo_especifico.py chegou a 100% de
    # cobertura (todo tema de TEMAS_BASE_EM tem conteudo especifico), entao
    # nao ha mais nenhum tema real que caia no template generico pra testar
    # via gerar_questao_offline_em. Testa a funcao geradora do template
    # generico diretamente (_pergunta_realista), que continua existindo
    # como fallback pra temas futuros sem conteudo especifico ainda.
    pergunta = _pergunta_realista("Biologia", "tema hipotetico de teste", "um cenario de teste", indice=0)

    assert "Situacao:" in pergunta or "Situa" in pergunta
    assert "Dados do enunciado:" in pergunta
    assert len(pergunta) > 150
    assert "Qual procedimento evita uma resposta superficial" not in pergunta


def test_offline_em_exatas_do_oraculo_e_teorico_sem_formula():
    # MELHORIA: services/oraculo_conteudo_especifico.py chegou a 100% de
    # cobertura (todo tema de TEMAS_BASE_EM tem conteudo especifico), entao
    # nao ha mais nenhum tema real de Matematica/Fisica/Quimica que caia no
    # template generico teorico via gerar_questao_offline_em. Testa as
    # funcoes geradoras do template generico diretamente, que continuam
    # existindo como fallback pra temas futuros sem conteudo especifico.
    pergunta = _pergunta_teorica_exatas("Matematica", "tema hipotetico de teste", "um cenario de teste", indice=0)
    explicacao = _explicacao_teorica_exatas("Matematica", "tema hipotetico de teste", "EM13MAT101")
    texto = " ".join(bloco.get("conteudo", "") for bloco in explicacao)

    assert "Conceito em foco" in texto
    assert "EM13MAT101" in texto
    assert "Oraculo" in texto
    assert "Laboratorio de Exatas" in texto
    assert "tema hipotetico de teste" in pergunta.lower()
    assert "qual estrat" not in pergunta.lower()


def _simular_sessao(gerar, materia: str, total: int) -> list[str]:
    """Simula um aluno respondendo N questoes seguidas, como as telas fazem:
    acumulando os ids ja vistos e passando em evitar_ids."""
    vistos: set[str] = set()
    textos: list[str] = []
    for _ in range(total):
        questao = gerar(materia, "", "Medio", evitar_ids=vistos)
        vistos.add(questao["id_offline"])
        textos.append(questao["pergunta"])
    return textos


def test_sessao_nao_repete_pergunta_enquanto_houver_conteudo_distinto():
    # MELHORIA: regressao para um bug medido no banco real. O banco repete
    # a MESMA pergunta em varias entradas com id_offline diferente (ex: 40
    # copias por questao no EM), e o evitar_ids so comparava id -- entao a
    # copia seguinte passava limpa e o aluno via a mesma pergunta de novo.
    # Medido antes da correcao: Matematica repetia ja na 2a questao, com 49
    # outras perguntas distintas disponiveis no banco.
    textos = _simular_sessao(gerar_questao_offline_em, "Matematica", 20)
    assert len(set(textos)) == 20


def test_sessao_usa_todo_o_conteudo_distinto_antes_de_repetir():
    # Filosofia EM tem 50 perguntas distintas; pedir 50 nao pode repetir
    # nenhuma, e passar disso nao pode travar sempre na mesma questao.
    textos = _simular_sessao(gerar_questao_offline_em, "Filosofia", 50)
    assert len(set(textos)) == 50

    textos_alem = _simular_sessao(gerar_questao_offline_em, "Filosofia", 60)
    assert len(set(textos_alem[50:])) > 1


def test_sessao_do_fundamental_tambem_evita_repetir_pergunta():
    textos = _simular_sessao(gerar_questao_offline_ef, "Matematica", 10)
    assert len(set(textos)) == 10


def test_sessoes_novas_nao_comecam_sempre_com_a_mesma_questao():
    # MELHORIA: regressao para um bug medido no banco real. Cada sessao de
    # Treino nasce com historico vazio (ver "historico": [] em
    # web/routes/treino_fla.py), e a selecao era 100% determinada pelo hash
    # de (materia|tema|nivel) -- entao TODA sessao nova abria com a mesma
    # questao. Medido antes: 5 sessoes seguidas de Matematica EM abriam as
    # cinco com "Qual e a mediana do conjunto {3, 7, 5, 9, 1}?".
    primeiras_em = [gerar_questao_offline_em("Matematica", "", "Medio")["pergunta"] for _ in range(10)]
    assert len(set(primeiras_em)) == 10

    primeiras_ef = [gerar_questao_offline_ef("Ciencias", "", "Medio")["pergunta"] for _ in range(10)]
    assert len(set(primeiras_ef)) == 10


def test_selecao_ignora_copias_duplicadas_do_mesmo_enunciado():
    # O banco guarda a mesma pergunta em varias entradas (40 copias por
    # questao no EM). A selecao precisa andar entre questoes diferentes, e
    # nao entre copias identicas vizinhas.
    from services.banks._base import selecionar_questao_offline

    questoes = [
        {"id_offline": f"X-{i:03d}", "tema_usado": "tema", "pergunta": f"Pergunta {i % 3}"}
        for i in range(30)
    ]
    escolhidas = {
        selecionar_questao_offline(questoes, "", seed="teste-duplicatas")["pergunta"] for _ in range(3)
    }
    assert escolhidas == {"Pergunta 0", "Pergunta 1", "Pergunta 2"}


def test_eh_ensino_medio_detecta_series_em():
    assert eh_ensino_medio("1o Ano EM") is True
    assert eh_ensino_medio("3 Ano EM") is True
    assert eh_ensino_medio("9o Ano") is False
