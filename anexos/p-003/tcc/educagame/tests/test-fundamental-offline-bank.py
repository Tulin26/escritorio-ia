from __future__ import annotations

from collections import Counter

from core.config import MATERIAS
from services.banks.fundamental import (
    BANCO_OFFLINE_EF,
    QUESTOES_EF_POR_TEMA,
    gerar_questao_offline_ef,
    listar_questoes_ef,
)
from services.ia_service import _montar_questao_offline


def test_banco_offline_ef_tem_50_questoes_por_tema():
    assert set(BANCO_OFFLINE_EF) == set(MATERIAS)
    for materia in MATERIAS:
        questoes = listar_questoes_ef(materia)
        contagem_temas = Counter(questao["objeto_conhecimento"] for questao in questoes)

        assert contagem_temas
        assert all(total >= QUESTOES_EF_POR_TEMA for total in contagem_temas.values())
        assert all(questao["serie_tipo"] == "EF" for questao in questoes)
        assert all(len(questao.get("opcoes", [])) == 4 for questao in questoes)
        # MELHORIA: este assert dizia que `habilidade_bncc` começa com "EF" —
        # ou seja, cobrava que o CÓDIGO estivesse no campo da descrição, que
        # era justamente o defeito. O código agora tem coluna própria, e a
        # habilidade guarda a frase que o professor consegue ler.
        assert all(questao.get("codigo_bncc", "").startswith("EF") for questao in questoes)
        assert all(len(questao.get("habilidade_bncc", "")) > 30 for questao in questoes)


def test_gerar_questao_offline_ef_filtra_tema_sem_acento():
    questao = gerar_questao_offline_ef("Matematica", "fracoes", "Medio")

    assert questao["materia"] == "Matematica"
    assert "fracoes" in questao["tema_usado"]
    assert questao["_origem_geracao"] == "offline"


def test_oraculo_ef_exatas_usa_teorica_sem_formula():
    questao = _montar_questao_offline("Matematica", "7o Ano", "Medio", "porcentagem")

    assert questao["serie_tipo"] == "EF"
    assert questao["materia"] == "Matematica"
    assert "porcentagem" in questao["tema_usado"]
    assert not questao.get("formula")
    assert not questao.get("passos_resolucao")


def test_banco_ef_nao_usa_enunciado_generico_de_placeholder():
    questao = gerar_questao_offline_ef("Matematica", "potencias", "Medio")
    texto = " ".join([questao.get("enigma", ""), questao.get("pergunta", ""), *questao.get("opcoes", [])])

    assert "Banco EF BNCC" not in texto
    assert "Contexto da questao" not in texto
    assert "Qual alternativa mostra melhor compreensao" not in texto
    assert "marcar por palpite" not in texto
    # MELHORIA: a asserção fixava o enunciado do template antigo ("relação
    # entre potências e raízes quadradas"). Com o conteúdo específico do EF
    # (services/fundamental_conteudo_especifico.py), a questão ficou ainda
    # mais concreta -- que é justamente o que este teste quer garantir.
    # Checa que o enunciado é do tema, sem prender a uma redação específica.
    assert any(termo in questao["pergunta"].lower() for termo in ("potência", "raiz quadrada", "²", "⁵"))
    assert "Qual análise é mais adequada" not in questao["pergunta"]


def test_banco_ef_comum_traz_teoria_e_nao_calculo_guiado():
    questao = gerar_questao_offline_ef("Ciencias", "vacinas", "Medio")

    # MELHORIA: a asserção original exigia a expressão exata "sistema
    # imunológico". Como a seleção agora avança a cada chamada (ver
    # _CICLO_SELECAO em services/banks/_base.py), o tema pode devolver
    # qualquer uma das suas questões -- prender o teste ao texto de uma
    # delas o tornaria dependente da ordem de execução. Verifica que a
    # questão é do tema, sem depender de qual delas saiu.
    texto = " ".join([questao["pergunta"], *questao["opcoes"]]).lower()
    assert "imun" in texto or "vacin" in texto
    assert not questao.get("formula")
    assert not questao.get("subformulas")
    assert not questao.get("passos_resolucao")


def test_todo_tema_do_ef_tem_conteudo_especifico():
    # MELHORIA: o banco EF era 100% template genérico ("Qual análise é mais
    # adequada para estudar {tema}?"), com alternativas como "Responder por
    # palpite" -- não testava conteúdo nenhum. Este teste trava a cobertura
    # conquistada: todo tema do EF precisa ter conteúdo específico escrito.
    from core.config import TEMAS_RPG
    from services.fundamental_conteudo_especifico import BANCO_ESPECIFICO_EF

    faltando = []
    for materia in MATERIAS:
        temas = TEMAS_RPG.get(materia, {}).get("EF") or []
        cobertos = BANCO_ESPECIFICO_EF.get(materia, {})
        faltando.extend(f"{materia}/{tema}" for tema in temas if tema not in cobertos)

    assert faltando == []


def test_banco_ef_nao_tem_mais_questao_do_template_generico():
    for materia in MATERIAS:
        for questao in BANCO_OFFLINE_EF[materia]:
            assert "Qual análise é mais adequada" not in questao["pergunta"]
            assert "Responder por palpite." not in questao["opcoes"]


def test_conteudo_especifico_do_ef_mantem_resposta_correta_apos_embaralhar():
    # O banco embaralha as alternativas por índice; o campo "correta" precisa
    # continuar apontando para a mesma alternativa da fonte (que é sempre a
    # de índice 0 em fundamental_conteudo_especifico.py).
    from services.fundamental_conteudo_especifico import BANCO_ESPECIFICO_EF

    correto_por_pergunta = {
        pergunta["pergunta"]: pergunta["opcoes"][0]
        for temas in BANCO_ESPECIFICO_EF.values()
        for perguntas in temas.values()
        for pergunta in perguntas
    }

    conferidas = 0
    for materia in MATERIAS:
        for questao in BANCO_OFFLINE_EF[materia]:
            esperado = correto_por_pergunta.get(questao["pergunta"])
            if esperado is None:
                continue
            conferidas += 1
            assert questao["opcoes"][questao["correta"]] == esperado

    assert conferidas > 0


def test_conteudo_especifico_do_ef_varia_a_posicao_da_resposta_correta():
    # Se a correta ficasse sempre na mesma posição, o aluno poderia acertar
    # sem ler a questão.
    posicoes = Counter(questao["correta"] for questao in BANCO_OFFLINE_EF["Matematica"])

    assert len(posicoes) == 4
