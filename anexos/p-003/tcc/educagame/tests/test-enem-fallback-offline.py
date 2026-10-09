from __future__ import annotations

import pytest

from services.enem_service import (
    _FALLBACK_POR_AREA,
    _fallback,
    _fallback_autoral_por_area,
    _questoes_distintas,
)

AREAS = list(_FALLBACK_POR_AREA.keys())


def test_questoes_distintas_remove_repetidas_preservando_ordem():
    entrada = [
        {"pergunta": "A"},
        {"pergunta": "B"},
        {"pergunta": "A"},
        {"pergunta": "C"},
        {"pergunta": ""},
    ]
    assert [q["pergunta"] for q in _questoes_distintas(entrada)] == ["A", "B", "C"]


@pytest.mark.parametrize("area", AREAS)
def test_fallback_de_cada_area_tem_bastante_questao_distinta(area):
    # MELHORIA: regressao para um bug medido no banco real. O banco EM
    # guarda 80 variacoes CONSECUTIVAS do mesmo tema, entao o fallback do
    # ENEM, que fatiava "listar_questoes_em(materia)[:80]", levava 80
    # copias de um unico tema -- Linguagens e Ciencias Humanas ficavam com
    # 11 perguntas distintas cada, apesar de montarem listas de 320 itens.
    # Um simulado de 30 questoes repetia quase tudo.
    distintas = {q.get("pergunta", "") for q in (_FALLBACK_POR_AREA[area] + _fallback_autoral_por_area(area))}

    assert len(distintas) >= 150, f"{area} tem apenas {len(distintas)} questoes distintas no fallback"


@pytest.mark.parametrize("area", AREAS)
def test_simulado_offline_de_30_questoes_quase_nao_repete(area):
    historico: list[str] = []
    vistas = []
    for _ in range(30):
        questao = _fallback(area, "Medio", historico)
        pergunta = str(questao.get("pergunta", "")).strip()
        vistas.append(pergunta)
        historico = (historico + [pergunta])[-8:]

    assert len(set(vistas)) >= 25, f"{area} repetiu demais: {len(set(vistas))}/30 distintas"
