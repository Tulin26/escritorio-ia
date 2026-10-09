from __future__ import annotations

import unicodedata

from services.ia_service import (
    _exemplo_curto_nao_exatas,
    _explicacao_direta_nao_exatas,
    _montar_questao_offline,
    _questao_fisica_quimica_conceitual,
    _questao_resposta_composta_inconsistente,
    _resolver_tema_questao,
    _resultado_exatas_conflitante,
)
from services.ia.validacao import validar_questao_gerada


def test_questao_fisica_quimica_conceitual_rejeita_payload_sem_numeros():
    dados = {
        "pergunta": "Qual conceito explica melhor a lei de Newton?",
        "opcoes": ["Inercia", "Velocidade", "Energia", "Massa"],
    }

    assert _questao_fisica_quimica_conceitual(dados) is True


def test_questao_fisica_quimica_conceitual_aceita_payload_com_numeros():
    dados = {
        "pergunta": "Um corpo de massa 4 kg acelera a 3 m/s^2. Qual e a forca resultante?",
        "opcoes": ["12 N", "10 N", "9 N", "15 N"],
    }

    assert _questao_fisica_quimica_conceitual(dados) is False


def test_oraculo_aceita_fisica_teorica_sem_calculo():
    dados = {
        "pergunta": "Qual ideia explica melhor a inercia em uma freada brusca?",
        "opcoes": [
            "A tendencia de manter o estado de movimento quando nao ha mudanca resultante suficiente.",
            "A transformacao direta de massa em temperatura.",
            "A eliminacao completa de todas as forcas durante o movimento.",
            "A necessidade de calcular velocidade antes de interpretar o fenomeno.",
        ],
        "correta": 0,
        "explicacao": [
            {"tipo": "texto", "conteudo": "A inercia descreve resistencia a mudancas no estado de movimento."}
        ],
    }

    _payload, valido, motivo = validar_questao_gerada(dados, "Fisica", contexto="oraculo")

    assert valido is True
    assert motivo == ""


def test_bhaskara_com_duas_raizes_separadas_e_inconsistente():
    dados = {
        "pergunta": "Resolva a equacao do 2o grau 2x^2 + 5x + 3 = 0 usando a formula de Bhaskara.",
        "opcoes": ["-3", "0,5", "-1", "-1,5"],
        "correta": 2,
    }

    assert _questao_resposta_composta_inconsistente(dados) is True


def test_resultado_exatas_conflitante_detecta_final_diferente():
    dados = {
        "pergunta": "Em uma PA, a1 = 2 e r = 3. Qual e o 5o termo?",
        "opcoes": ["14", "15", "17", "20"],
        "correta": 1,
        "formula": "a_n = a_1 + (n-1)r",
        "passos_resolucao": [
            {"titulo": "1o Passo", "conteudo": "a_5 = 2 + (5-1) * 3", "final": False},
            {"titulo": "Resultado Final", "conteudo": "a_5 = 14", "final": True},
        ],
        "explicacao": [
            {"tipo": "bold", "conteudo": "Progressao Aritmetica"},
            {"tipo": "resultado", "conteudo": "O 5o termo e 15."},
        ],
    }

    assert _resultado_exatas_conflitante(dados) is True


def test_resultado_exatas_conflitante_ignora_formula_simbolica():
    dados = {
        "pergunta": "Um corpo de massa 4 kg acelera a 3 m/s^2. Qual e a forca resultante?",
        "opcoes": ["12 N", "10 N", "9 N", "15 N"],
        "correta": 0,
        "formula": "F = m.a",
        "subformulas": ["F = 4 * 3", "F = 12"],
        "passos_resolucao": [
            {"titulo": "Resultado Final", "conteudo": "F = 12 N", "final": True},
        ],
        "explicacao": [
            {"tipo": "resultado", "conteudo": "A forca resultante e 12 N."},
        ],
    }

    assert _resultado_exatas_conflitante(dados) is False


def test_resolver_tema_questao_preserva_tema_digitado():
    assert _resolver_tema_questao("Portugues", "2 Ano EM", "crase") == "crase"


def test_resolver_tema_questao_sorteia_tema_quando_vazio(monkeypatch):
    monkeypatch.setattr("services.ia.enigma.random.choice", lambda temas: temas[-1])

    assert _resolver_tema_questao("Portugues", "2 Ano EM", "") == "romantismo"


def test_offline_oraculo_em_exatas_usa_questao_teorica_sem_formula():
    # MELHORIA: services/oraculo_conteudo_especifico.py chegou a 100% de
    # cobertura, entao "areas e volumes" agora tem conteudo especifico (nao
    # cai mais no template generico "Oraculo teorico: ..."). O que este
    # teste protege de verdade e que o Oraculo de exatas NUNCA mostra
    # formula/passos de resolucao (isso e o Laboratorio de Exatas que faz),
    # seja a questao generica ou especifica -- entao a checagem do prefixo
    # exato do enigma foi afrouxada pra aceitar os dois formatos.
    questao = _montar_questao_offline("Matematica", "1 Ano EM", "Medio", "areas e volumes")
    enigma_sem_acento = unicodedata.normalize("NFKD", questao.get("enigma", "")).encode("ascii", "ignore").decode("ascii")

    assert not questao.get("formula")
    assert not questao.get("passos_resolucao")
    # Desde 15/09/2026 o titulo do banco nao traz mais o rotulo interno
    # ("Oraculo: ... aparece em ...", ver tests/test_defeitos_visiveis.py):
    # e o tema no cenario. O que se cobra aqui e que ele fale do tema.
    assert not enigma_sem_acento.startswith(("Oraculo", "Banco"))
    assert "volumes" in enigma_sem_acento.lower()
    assert "qual estrat" not in questao.get("pergunta", "").lower()


def test_exemplo_curto_portugues_regencia():
    exemplo = _exemplo_curto_nao_exatas("Portugues", "regencia")

    assert "necessidade de ajuda" in exemplo


def test_sem_exemplo_concreto_nao_entra_exemplo_de_gaveta():
    # MELHORIA: primeiro o exemplo de Historia citava sempre a "Revolucao
    # Industrial", ate numa questao sobre a Era Vargas; o conserto foi pôr o
    # tema na frase. Mas a frase continuou de gaveta -- "ao estudar Era
    # Vargas, relacione os principais agentes envolvidos..." serve para
    # qualquer tema e nao exemplifica nada. Medido em 13/09/2026: 6 das 14
    # explicacoes reais do Oraculo traziam uma dessas. Sem exemplo concreto,
    # nenhum exemplo.
    for materia in ("Historia", "Geografia", "Biologia", "Arte", "Educacao Fisica", "Filosofia", "Sociologia", "Ensino Religioso"):
        assert _exemplo_curto_nao_exatas(materia, "Era Vargas") == "", materia

    explicacao = _explicacao_direta_nao_exatas(
        "Historia",
        "Guerra Fria",
        "O que caracterizou a Guerra Fria?",
        [{"tipo": "texto", "conteudo": "A Guerra Fria foi a disputa entre EUA e URSS sem confronto direto."}],
        [],
    )

    assert not any("Exemplo:" in bloco["conteudo"] for bloco in explicacao)


def test_explicacao_nao_exatas_inclui_exemplo_quando_ia_nao_traz():
    explicacao = _explicacao_direta_nao_exatas(
        "Portugues",
        "regencia",
        "Qual a função da regência nominal?",
        [{"tipo": "texto", "conteudo": "A regência mostra a relação entre termos."}],
        [],
    )

    conteudos = [bloco["conteudo"] for bloco in explicacao]
    assert any("Exemplo:" in conteudo for conteudo in conteudos)


def test_explicacao_nao_exatas_nao_duplica_texto_com_exemplo_embutido():
    texto_ia = (
        "A coesao e coerencia sao fundamentais para que um texto seja claro. "
        "Elas permitem que as ideias sejam ligadas de forma logica. "
        "Um exemplo e: 'Eu fui ao mercado porque precisava comprar leite'."
    )
    explicacao = _explicacao_direta_nao_exatas(
        "Portugues",
        "coesao e coerencia",
        "Qual e a funcao da coesao?",
        [{"tipo": "texto", "conteudo": texto_ia}],
        [],
    )

    conteudos = [bloco["conteudo"] for bloco in explicacao]
    assert conteudos.count(texto_ia) == 1


def test_explicacao_nao_exatas_deduplica_textos_de_passos():
    texto_ia = "A Revolucao Industrial transformou a producao e o trabalho urbano."
    explicacao = _explicacao_direta_nao_exatas(
        "Historia",
        "Revolucao Industrial",
        "Qual foi um efeito desse processo?",
        [{"tipo": "texto", "conteudo": texto_ia}],
        [{"titulo": "Etapa", "conteudo": texto_ia}],
    )

    conteudos = [bloco["conteudo"] for bloco in explicacao]
    assert conteudos.count(texto_ia) == 1
