from __future__ import annotations

import inspect

import st.ui.tela_laboratorio_st as tela_laboratorio


def test_laboratorio_usa_contexto_do_dia_a_dia_sem_resolucao_antiga():
    fonte = inspect.getsource(tela_laboratorio.renderizar_tela_laboratorio)

    assert "Onde isso aparece no dia a dia" in fonte
    assert "Resolução do Alquimista" not in fonte
    assert "renderizar_resolucao_detalhada" not in fonte

