"""
Testes unitários para repositories/log_repo.py

Execute com: pytest tests/test_log_repo.py -v
"""
import pytest
from repositories.log_repo import (
    _normalizar_tempo_resposta,
    _inferir_modo_log,
    preparar_payload_log,
    tempo_resposta_para_media,
)


class TestNormalizarTempoResposta:
    def test_none_retorna_none(self):
        assert _normalizar_tempo_resposta(None) is None

    def test_string_vazia_retorna_none(self):
        assert _normalizar_tempo_resposta("") is None

    def test_valor_negativo_vira_zero(self):
        assert _normalizar_tempo_resposta(-5) == 0.0

    def test_valor_positivo_arredondado(self):
        assert _normalizar_tempo_resposta(3.14159) == 3.14

    def test_string_numerica(self):
        assert _normalizar_tempo_resposta("12.5") == 12.5

    def test_string_invalida_retorna_none(self):
        assert _normalizar_tempo_resposta("abc") is None

    def test_zero_valido(self):
        assert _normalizar_tempo_resposta(0) == 0.0


class TestTempoRespostaParaMedia:
    def test_zero_excluido_da_media(self):
        assert tempo_resposta_para_media(0) is None

    def test_negativo_excluido_da_media(self):
        assert tempo_resposta_para_media(-1) is None

    def test_none_excluido_da_media(self):
        assert tempo_resposta_para_media(None) is None

    def test_positivo_incluido(self):
        assert tempo_resposta_para_media(5.0) == 5.0


class TestInferirModoLog:
    def test_modo_explicito_retornado(self):
        assert _inferir_modo_log({"modo": "rpg"}) == "rpg"

    def test_modo_maiusculo_normalizado(self):
        assert _inferir_modo_log({"modo": "RPG"}) == "rpg"

    def test_materia_rpg_infere_modo(self):
        assert _inferir_modo_log({"materia": "RPG-Aventura"}) == "rpg"

    def test_materia_lab_infere_modo(self):
        assert _inferir_modo_log({"materia": "LAB-Fisica"}) == "laboratorio"

    def test_materia_enem_infere_modo(self):
        assert _inferir_modo_log({"materia": "ENEM-Matematica"}) == "enem"

    def test_default_oraculo(self):
        assert _inferir_modo_log({"materia": "Matematica"}) == "oraculo"

    def test_sem_materia_default_oraculo(self):
        assert _inferir_modo_log({}) == "oraculo"


class TestPrepararPayloadLog:
    def test_filtra_colunas_invalidas(self):
        payload = preparar_payload_log({
            "aluno_id": "abc",
            "campo_invalido": "valor",
        })
        assert "campo_invalido" not in payload
        assert "aluno_id" in payload

    def test_modo_inferido_automaticamente(self):
        payload = preparar_payload_log({"materia": "RPG-Aventura"})
        assert payload["modo"] == "rpg"

    def test_tempo_resposta_normalizado(self):
        payload = preparar_payload_log({"aluno_id": "x"}, tempo_resposta=-1)
        assert payload["tempo_resposta"] == 0.0

    def test_tempo_none_quando_invalido(self):
        payload = preparar_payload_log({"aluno_id": "x"}, tempo_resposta=None)
        assert payload["tempo_resposta"] is None
