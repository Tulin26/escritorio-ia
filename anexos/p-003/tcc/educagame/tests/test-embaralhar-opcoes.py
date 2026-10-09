"""
Testes unitarios para _embaralhar_opcoes_questao em services/ia_service.py

Execute com: pytest tests/test_embaralhar_opcoes.py -v
"""

from services.ia_service import _embaralhar_opcoes_questao


QUESTAO_BASE = {
    "pergunta": "Qual e a capital do Brasil?",
    "opcoes": ["Sao Paulo", "Rio de Janeiro", "Brasilia", "Belo Horizonte"],
    "correta": 2,
}


class TestEmbaralharOpcoes:
    def test_resposta_correta_preservada_apos_embaralhamento(self):
        for _ in range(50):
            resultado = _embaralhar_opcoes_questao(dict(QUESTAO_BASE))
            assert resultado["opcoes"][resultado["correta"]] == "Brasilia"

    def test_todas_opcoes_preservadas(self):
        resultado = _embaralhar_opcoes_questao(dict(QUESTAO_BASE))
        assert sorted(resultado["opcoes"]) == sorted(QUESTAO_BASE["opcoes"])

    def test_nao_modifica_questao_original(self):
        original = dict(QUESTAO_BASE)
        opcoes_antes = list(original["opcoes"])
        _embaralhar_opcoes_questao(original)
        assert original["opcoes"] == opcoes_antes
        assert original["correta"] == QUESTAO_BASE["correta"]

    def test_sem_opcoes_retorna_intacto(self):
        questao = {"pergunta": "Aberta", "correta": 0}
        assert _embaralhar_opcoes_questao(questao) == questao

    def test_uma_opcao_retorna_intacto(self):
        questao = {"opcoes": ["unica"], "correta": 0}
        resultado = _embaralhar_opcoes_questao(questao)
        assert resultado["opcoes"] == ["unica"]
        assert resultado["correta"] == 0

    def test_opcoes_none_retorna_intacto(self):
        questao = {"opcoes": None, "correta": 0}
        assert _embaralhar_opcoes_questao(questao) == questao

    def test_indice_correta_fora_do_range_usa_zero(self):
        questao = {"opcoes": ["A", "B", "C"], "correta": 99}
        resultado = _embaralhar_opcoes_questao(questao)
        assert resultado["opcoes"][resultado["correta"]] == "A"

    def test_indice_correta_negativo_usa_zero(self):
        questao = {"opcoes": ["A", "B", "C"], "correta": -1}
        resultado = _embaralhar_opcoes_questao(questao)
        assert resultado["opcoes"][resultado["correta"]] == "A"

    def test_indice_correta_string_numerica(self):
        questao = {"opcoes": ["X", "Y", "Z"], "correta": "1"}
        resultado = _embaralhar_opcoes_questao(questao)
        assert resultado["opcoes"][resultado["correta"]] == "Y"

    def test_indice_correta_string_invalida_usa_zero(self):
        questao = {"opcoes": ["X", "Y", "Z"], "correta": "abc"}
        resultado = _embaralhar_opcoes_questao(questao)
        assert resultado["opcoes"][resultado["correta"]] == "X"


class TestEmbaralharOpcoesTraduzidas:
    QUESTAO_INGLES = {
        "opcoes": ["dog", "cat", "fish", "bird"],
        "opcoes_traducao": ["cachorro", "gato", "peixe", "passaro"],
        "correta": 2,
    }

    def test_traducao_acompanha_opcao(self):
        for _ in range(50):
            resultado = _embaralhar_opcoes_questao(dict(self.QUESTAO_INGLES))
            idx = resultado["correta"]
            assert resultado["opcoes"][idx] == "fish"
            assert resultado["opcoes_traducao"][idx] == "peixe"

    def test_traducao_despareada_ignorada(self):
        questao = {
            "opcoes": ["A", "B", "C"],
            "opcoes_traducao": ["X", "Y"],
            "correta": 0,
        }
        resultado = _embaralhar_opcoes_questao(questao)
        assert resultado["opcoes_traducao"] == ["X", "Y"]

    def test_sem_traducao_nao_adiciona_campo(self):
        resultado = _embaralhar_opcoes_questao(dict(QUESTAO_BASE))
        assert "opcoes_traducao" not in resultado
