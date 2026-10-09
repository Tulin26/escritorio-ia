"""
Testes unitários para services/enem_service.py

Execute com: pytest tests/test_enem_service.py -v
"""
import pytest
from unittest.mock import patch
from services.enem_service import (
    _validar_questao,
    _embaralhar_alternativas_questao,
    _fallback,
    _fallback_autoral_por_area,
    _gerar_via_ia,
    _normalizar_textos_questao,
    montar_sequencia_questoes,
    sortear_areas,
    inferir_dificuldade_aluno,
    AREAS_ENEM,
)


class TestValidarQuestao:
    def test_none_invalido(self):
        assert _validar_questao(None) is False

    def test_sem_pergunta_invalido(self):
        assert _validar_questao({"alternativas": ["A", "B", "C", "D"], "correta": "A"}) is False

    def test_poucas_alternativas_invalido(self):
        q = {"pergunta": "P?", "alternativas": ["A", "B", "C"], "correta": "A"}
        assert _validar_questao(q) is False

    def test_correta_fora_das_alternativas_invalido(self):
        q = {
            "pergunta": "P?",
            "alternativas": ["A", "B", "C", "D", "E"],
            "correta": "F",
        }
        assert _validar_questao(q) is False

    def test_questao_valida(self):
        q = {
            "pergunta": "Qual é a capital do Brasil?",
            "alternativas": ["Brasília", "São Paulo", "Rio de Janeiro", "Salvador", "Manaus"],
            "correta": "Brasília",
            "explicacao": [{"tipo": "resultado", "conteudo": "Brasília é a capital federal do Brasil desde 1960."}],
        }
        assert _validar_questao(q) is True

    def test_quatro_alternativas_aceito(self):
        q = {
            "pergunta": "P?",
            "alternativas": ["A", "B", "C", "D"],
            "correta": "A",
            "explicacao": [{"tipo": "resultado", "conteudo": "A alternativa A é a única que atende ao enunciado."}],
        }
        assert _validar_questao(q) is True

    def test_matematica_combustivel_rejeita_correta_incompativel(self):
        q = {
            "pergunta": "Um carro percorre 700 km, consome 12 km/l e a gasolina custa R$ 5,50. Qual o custo?",
            "alternativas": ["R$ 303,13", "R$ 243,75", "R$ 200,00", "R$ 175,00"],
            "correta": "R$ 303,13",
            "area_bncc": "Matematica e suas Tecnologias",
        }
        assert _validar_questao(q) is False

    def test_matematica_combustivel_aceita_correta_compativel(self):
        q = {
            "pergunta": "Um carro percorre 240 km, consome 12 km/l e a gasolina custa R$ 4,50. Qual o custo?",
            "alternativas": ["R$ 80,00", "R$ 90,00", "R$ 120,00", "R$ 180,00"],
            "correta": "R$ 90,00",
            "area_bncc": "Matematica e suas Tecnologias",
            "explicacao": [{"tipo": "resultado", "conteudo": "O carro consome 20 litros e cada litro custa R$ 4,50."}],
        }
        assert _validar_questao(q) is True


class TestEmbaralharAlternativas:
    def test_preserva_correta_e_alternativas(self):
        q = {
            "pergunta": "P?",
            "alternativas": ["A", "B", "C", "D", "E"],
            "correta": "C",
        }

        for _ in range(50):
            resultado = _embaralhar_alternativas_questao(q)
            assert sorted(resultado["alternativas"]) == ["A", "B", "C", "D", "E"]
            assert resultado["correta"] == "C"
            assert resultado["correta"] in resultado["alternativas"]


class TestFallback:
    def test_retorna_dict(self):
        q = _fallback("Matematica e suas Tecnologias", "Medio")
        assert isinstance(q, dict)

    def test_tem_campos_obrigatorios(self):
        q = _fallback("Matematica e suas Tecnologias", "Facil")
        assert "pergunta" in q
        assert "alternativas" in q
        assert "correta" in q

    def test_area_inexistente_usa_fallback_alternativo(self):
        q = _fallback("Area Inexistente XYZ", "Medio")
        assert isinstance(q, dict)
        assert "pergunta" in q

    def test_dificuldade_preservada(self):
        q = _fallback("Matematica e suas Tecnologias", "Dificil")
        assert q["dificuldade"] == "Dificil"

    def test_origem_offline(self):
        q = _fallback("Matematica e suas Tecnologias", "Medio")
        assert q["_origem"] == "offline"

    def test_fallback_matematica_evitar_repetir_historico_quando_possivel(self):
        primeira = _fallback("Matematica e suas Tecnologias", "Medio")
        segunda = _fallback("Matematica e suas Tecnologias", "Medio", [primeira["pergunta"]])
        assert segunda["pergunta"] != primeira["pergunta"]

    def test_fallback_autoral_tem_pelo_menos_10_por_area(self):
        for area in AREAS_ENEM:
            banco = _fallback_autoral_por_area(area)
            assert len(banco) >= 10
            assert all(q["area_bncc"] == area for q in banco)
            assert all(len(q.get("alternativas", [])) >= 4 for q in banco)


def test_gerar_via_ia_matematica_define_area_antes_de_validar(monkeypatch):
    def fake_gerar_json_ia(*args, **kwargs):
        return {
            "pergunta": "Um carro percorre 700 km, consome 12 km/l e a gasolina custa R$ 5,50. Qual o custo?",
            "alternativas": ["R$ 303,13", "R$ 243,75", "R$ 200,00", "R$ 175,00"],
            "correta": "R$ 303,13",
            "explicacao": [],
        }

    monkeypatch.setattr("services.enem_service.gerar_json_ia", fake_gerar_json_ia)

    assert _gerar_via_ia("Matematica e suas Tecnologias", "Medio") is None


def test_normalizar_textos_questao_corrige_erros_comuns_todas_areas():
    q = _normalizar_textos_questao({
        "pergunta": "Qual acao ajuda a reducir a temperatura do solo atraves da sombra?",
        "alternativas": ["Reducir a temperatura", "Aumentar a populaçao"],
        "correta": "Reducir a temperatura",
        "explicacao": [{"tipo": "resultado", "conteudo": "Isso ajuda no calculo do impacto na regiao."}],
    })

    assert "reduzir" in q["pergunta"]
    assert q["alternativas"][0] == "Reduzir a temperatura"
    assert q["correta"] == "Reduzir a temperatura"
    assert "cálculo" in q["explicacao"][0]["conteudo"]


def test_normalizar_textos_questao_preserva_decimais_monetarios():
    q = _normalizar_textos_questao({
        "pergunta": "O preco e R$ 5,20.",
        "alternativas": ["R$ 104,00"],
        "correta": "R$ 104,00",
        "explicacao": [{"tipo": "resultado", "conteudo": "O custo e 20 x R$ 5,20 = R$ 104,00."}],
    })

    assert "R$ 5,20" in q["pergunta"]
    assert "R$ 5,20 = R$ 104,00" in q["explicacao"][0]["conteudo"]


class TestMontarSequencia:
    def test_tamanho_correto(self):
        seq = montar_sequencia_questoes(list(AREAS_ENEM.keys()), 10)
        assert len(seq) == 10

    def test_todas_areas_representadas(self):
        areas = list(AREAS_ENEM.keys())
        seq = montar_sequencia_questoes(areas, 20)
        areas_presentes = {s[0] for s in seq}
        assert areas_presentes == set(areas)

    def test_sequencia_vazia_usa_todas_areas(self):
        seq = montar_sequencia_questoes([], 5)
        assert len(seq) == 5

    def test_retorna_tuplas(self):
        seq = montar_sequencia_questoes(list(AREAS_ENEM.keys()), 3)
        for item in seq:
            assert isinstance(item, tuple)
            assert len(item) == 2


class TestInferirDificuldade:
    def test_sem_logs_retorna_medio(self):
        assert inferir_dificuldade_aluno([]) == "Medio"

    def test_poucos_logs_retorna_medio(self):
        logs = [{"resultado": "Acertou"}] * 3
        assert inferir_dificuldade_aluno(logs) == "Medio"

    def test_alto_desempenho_retorna_dificil(self):
        logs = [{"resultado": "Acertou"}] * 8 + [{"resultado": "Errou"}] * 2
        assert inferir_dificuldade_aluno(logs) == "Dificil"

    def test_baixo_desempenho_retorna_facil(self):
        logs = [{"resultado": "Errou"}] * 8 + [{"resultado": "Acertou"}] * 2
        assert inferir_dificuldade_aluno(logs) == "Facil"

    def test_desempenho_medio(self):
        logs = [{"resultado": "Acertou"}] * 5 + [{"resultado": "Errou"}] * 5
        assert inferir_dificuldade_aluno(logs) == "Medio"


class TestSortearAreas:
    def test_retorna_lista(self):
        resultado = sortear_areas(2)
        assert isinstance(resultado, list)
        assert len(resultado) == 2

    def test_sem_repeticao(self):
        resultado = sortear_areas(4)
        assert len(resultado) == len(set(resultado))

    def test_maximo_areas_disponiveis(self):
        resultado = sortear_areas(100)
        assert len(resultado) == len(AREAS_ENEM)
