from __future__ import annotations

from services.pedagogical_feedback import gerar_feedback_pedagogico


def test_feedback_detecta_produto_batendo_mas_soma_nao():
    # MELHORIA: caso real visto em producao (raizes de Bhaskara). Antes disso,
    # qualquer resposta numerica errada em exatas recebia a mesma mensagem
    # generica; agora o diagnostico usa os proprios numeros da resposta.
    resultado = gerar_feedback_pedagogico(
        dados={"pergunta": "raizes da equacao", "tema": "Bhaskara"},
        materia="Matematica",
        resposta_aluno="-2,1 e 0,8",
        resposta_correta="-1,1 e 1,5",
    )
    assert "produto" in resultado["confundiu"].lower()
    assert "a, b e c" in resultado["evitar"].lower()


def test_feedback_detecta_soma_batendo_mas_produto_nao():
    resultado = gerar_feedback_pedagogico(
        dados={},
        materia="Matematica",
        resposta_aluno="1 e 4",
        resposta_correta="2 e 3",
    )
    assert "delta" in resultado["confundiu"].lower() or "raiz quadrada" in resultado["confundiu"].lower()


def test_feedback_detecta_sinal_trocado_em_par_de_valores():
    resultado = gerar_feedback_pedagogico(
        dados={},
        materia="Matematica",
        resposta_aluno="2 e -3",
        resposta_correta="-2 e 3",
    )
    assert "sinal" in resultado["confundiu"].lower()


def test_feedback_detecta_sinal_trocado_em_valor_unico():
    resultado = gerar_feedback_pedagogico(
        dados={},
        materia="Fisica",
        resposta_aluno="-15",
        resposta_correta="15",
    )
    assert "sinal" in resultado["confundiu"].lower()


def test_feedback_detecta_resultado_proximo_como_arredondamento():
    resultado = gerar_feedback_pedagogico(
        dados={},
        materia="Quimica",
        resposta_aluno="3.2",
        resposta_correta="3.05",
    )
    assert "arredondamento" in resultado["confundiu"].lower() or "casa decimal" in resultado["confundiu"].lower()


def test_feedback_detecta_resultado_distante_como_erro_conceitual():
    resultado = gerar_feedback_pedagogico(
        dados={},
        materia="Fisica",
        resposta_aluno="100",
        resposta_correta="4",
    )
    assert "distante" in resultado["confundiu"].lower()


def test_feedback_sem_numeros_cai_no_fallback_generico_sem_quebrar():
    resultado = gerar_feedback_pedagogico(
        dados={},
        materia="Matematica",
        resposta_aluno="opcao B",
        resposta_correta="opcao C",
    )
    assert resultado["confundiu"]
    assert resultado["evitar"]


def test_feedback_materias_humanas_nao_usa_diagnostico_numerico():
    # O "confundiu" passou a nomear as duas alternativas em TODAS as matérias,
    # e não só em exatas (ver tests/test_explicacao_e_feedback.py) -- a
    # verificação da intenção deste teste mudou de lugar: quem carrega o
    # assunto agora é o "evitar", que continua sendo o de humanas.
    resultado = gerar_feedback_pedagogico(
        dados={"pergunta": "interprete o texto a seguir"},
        materia="Portugues",
        resposta_aluno="opcao A",
        resposta_correta="opcao B",
    )
    assert "texto" in resultado["evitar"].lower() or "interpreta" in resultado["evitar"].lower()
    for marca in ("conta", "arredondamento", "casa decimal", "fórmula"):
        assert marca not in resultado["confundiu"].lower(), f"diagnóstico de exatas vazou: {marca}"


def test_conceitual_de_exatas_cita_as_duas_alternativas():
    # MELHORIA: resposta NUMERICA errada ja recebia diagnostico especifico,
    # mas toda questao CONCEITUAL de exatas caia na mesma frase generica --
    # que nao dizia o que o aluno marcou nem qual era a certa.
    feedback = gerar_feedback_pedagogico(
        dados={
            "pergunta": "Qual solido geometrico possui todas as faces quadradas congruentes e exatamente seis faces?",
            "tema_usado": "geometria espacial",
        },
        materia="Matematica",
        resposta_aluno="Paralelepipedo",
        resposta_correta="Cubo",
    )

    assert "Paralelepipedo" in feedback["confundiu"]
    assert "Cubo" in feedback["confundiu"]
    assert "alternativa parecida" not in feedback["confundiu"]
    # pergunta de identificacao: a dica e eliminar por exigencia do enunciado
    assert "exigência" in feedback["evitar"]


def test_dica_muda_conforme_o_comando_da_pergunta():
    causa = gerar_feedback_pedagogico(
        dados={"pergunta": "Por que a agua ferve a temperatura menor no alto da montanha?"},
        materia="Fisica",
        resposta_aluno="Porque o ar e mais frio",
        resposta_correta="Porque a pressao atmosferica e menor",
    )
    comparacao = gerar_feedback_pedagogico(
        dados={"pergunta": "Qual a diferenca entre ligacao ionica e covalente?"},
        materia="Quimica",
        resposta_aluno="Ambas compartilham eletrons",
        resposta_correta="Uma transfere e a outra compartilha eletrons",
    )

    assert "explicação" in causa["evitar"]
    assert "comparação" in comparacao["evitar"]
    assert causa["evitar"] != comparacao["evitar"]


def test_alternativa_que_e_so_rotulo_nao_vira_citacao():
    # Citar "voce marcou C, a resposta e A" nao ensina nada: cai no texto
    # generico, que ao menos fala do raciocinio.
    feedback = gerar_feedback_pedagogico(
        dados={"pergunta": "Qual solido tem seis faces?"},
        materia="Matematica",
        resposta_aluno="C",
        resposta_correta="A",
    )

    assert "“C”" not in feedback["confundiu"]
    assert "alternativa parecida" in feedback["confundiu"]


def test_confundiu_nao_afirma_que_as_alternativas_sao_do_mesmo_assunto():
    # Relatorio de QA de 23/09/2026, item 5.4: "As duas pertencem ao mesmo
    # assunto" saia mesmo quando o distrator marcado nao tinha nenhuma
    # relacao com a resposta certa -- caso real do RPG, "Carnaval" numa
    # questao sobre peregrinacao religiosa.
    feedback = gerar_feedback_pedagogico(
        dados={"pergunta": "Qual dessas praticas e um exemplo classico de peregrinacao religiosa?"},
        materia="Ensino Religioso",
        resposta_aluno="Carnaval",
        resposta_correta="Caminho de Santiago",
    )

    assert "mesmo assunto" not in feedback["confundiu"]
    assert "Carnaval" in feedback["confundiu"]
    assert "Caminho de Santiago" in feedback["confundiu"]
