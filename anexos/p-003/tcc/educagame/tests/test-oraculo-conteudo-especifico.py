from __future__ import annotations

from services.banks.em import TEMAS_BASE_EM, gerar_questao_offline_em, listar_questoes_em
from services.oraculo_conteudo_especifico import BANCO_ESPECIFICO_EM


def test_todos_os_temas_especificos_existem_em_temas_base_em():
    # MELHORIA: garante que nenhuma entrada do banco especifico tenha um erro
    # de digitacao/acentuacao no nome do tema, o que faria ela nunca ser
    # usada (cairia sempre no fallback generico silenciosamente).
    for materia, temas in BANCO_ESPECIFICO_EM.items():
        assert materia in TEMAS_BASE_EM, f"materia desconhecida: {materia}"
        for tema in temas:
            assert tema in TEMAS_BASE_EM[materia], f"{materia}: tema '{tema}' nao existe em TEMAS_BASE_EM"


def test_todas_as_perguntas_especificas_tem_estrutura_valida():
    for materia, temas in BANCO_ESPECIFICO_EM.items():
        for tema, perguntas in temas.items():
            for pergunta in perguntas:
                assert len(pergunta["opcoes"]) == 4, f"{materia}/{tema}: precisa ter 4 opcoes"
                assert len(set(pergunta["opcoes"])) == 4, f"{materia}/{tema}: opcoes duplicadas"
                assert 0 <= pergunta["correta"] < 4, f"{materia}/{tema}: indice correta invalido"
                assert pergunta["pergunta"].strip(), f"{materia}/{tema}: pergunta vazia"
                assert pergunta["explicacao"], f"{materia}/{tema}: explicacao vazia"


def test_analise_combinatoria_retorna_conteudo_especifico_nao_generico():
    # MELHORIA: regressao para o caso exato reportado (print do Oraculo de
    # Matematica mostrando uma pergunta generica e vaga sobre combinatoria).
    questao = gerar_questao_offline_em("Matematica", tema="análise combinatória", nivel="Medio")
    assert "leitura conceitual" not in questao["pergunta"].lower()
    assert "combinat" in questao["pergunta"].lower() or "escolher" in questao["pergunta"].lower()


def test_todos_os_temas_especificos_realmente_bypassam_o_generico():
    # MELHORIA: garante, para TODOS os temas com conteudo especifico, que a
    # pergunta gerada realmente usa esse conteudo (nao o template generico).
    # Sem este teste, adicionar conteudo especifico pra um tema que um outro
    # teste ja usava como exemplo do comportamento generico quebra em
    # silencio (ja aconteceu com "ecologia" em Biologia e "probabilidade"
    # em Matematica).
    # Usa listar_questoes_em + filtro exato por tema_usado (prefixo antes do
    # " - contexto") em vez de gerar_questao_offline_em, ja que essa ultima
    # faz correspondencia por substring: buscar "cultura" tambem bate com
    # "indústria cultural", que e um tema diferente (e ainda generico).
    marcadores_genericos = ("Situacao:", "Conceito em foco", "qual leitura conceitual")
    for materia, temas in BANCO_ESPECIFICO_EM.items():
        todas = listar_questoes_em(materia)
        for tema in temas:
            do_tema = [q for q in todas if q.get("tema_usado", "").split(" - ")[0] == tema]
            assert do_tema, f"{materia}/{tema}: nenhuma questao encontrada"
            for questao in do_tema[:3]:
                texto_completo = questao["pergunta"] + " ".join(
                    b.get("conteudo", "") for b in questao.get("explicacao", [])
                )
                for marcador in marcadores_genericos:
                    assert marcador not in texto_completo, (
                        f"{materia}/{tema}: ainda usando template generico (marcador {marcador!r} encontrado)"
                    )


def test_tema_sem_conteudo_especifico_ainda_cai_no_generico_sem_quebrar():
    # Confirma que o fallback continua funcionando para temas que ainda nao
    # tem conteudo especifico escrito. "estatística" ainda nao foi coberto.
    questao = gerar_questao_offline_em("Matematica", tema="estatística", nivel="Medio")
    assert questao["pergunta"].strip()
    assert len(questao["opcoes"]) >= 2


def test_posicao_da_resposta_correta_varia_entre_chamadas():
    # MELHORIA: as perguntas especificas foram escritas com a resposta certa
    # sempre na posicao 0 (mais facil de revisar o conteudo); sem embaralhar,
    # o aluno poderia aprender a sempre marcar a primeira opcao.
    # gerar_questao_offline_em e deterministico para a mesma materia+tema+
    # nivel (por design, pra sempre entregar a mesma pergunta pro mesmo
    # pedido); a variedade precisa ser checada entre as varias instancias
    # cacheadas do mesmo tema, nao entre chamadas repetidas identicas.
    todas = listar_questoes_em("Matematica")
    do_tema = [q for q in todas if "progressão aritmética" in q.get("tema_usado", "")]
    assert len(do_tema) > 1
    posicoes = {q["correta"] for q in do_tema}
    assert len(posicoes) > 1
