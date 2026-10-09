from __future__ import annotations

from core.config import (
    exibir_materia,
    filtrar_materias_por_serie,
    get_materias_por_serie,
    normalizar_materia,
)
from web.routes.flask_helpers_fla import materias_para_template


def test_normalizar_materia_aceita_acentos_caixa_e_espacos():
    assert normalizar_materia("  matemática  ") == "Matematica"
    assert normalizar_materia("FÍSICA") == "Fisica"
    assert normalizar_materia("Língua Portuguesa") == "Portugues"


def test_exibir_materia_usa_nome_com_acento():
    assert exibir_materia("Matematica") == "Matemática"
    assert exibir_materia("ingles") == "Inglês"


def test_materias_do_ensino_medio_nao_incluem_ciencias_generico():
    materias = get_materias_por_serie("1 Ano EM")

    assert "Ciencias" not in materias
    assert {"Biologia", "Fisica", "Quimica"}.issubset(set(materias))


def test_materias_do_fundamental_nao_incluem_avancadas_do_medio():
    materias = get_materias_por_serie("8 Ano")

    assert "Ciencias" in materias
    assert not {"Biologia", "Fisica", "Quimica", "Filosofia", "Sociologia"} & set(materias)


def test_filtrar_materias_por_serie_respeita_etapa():
    todas = ["Matematica", "Ciencias", "Biologia", "Fisica", "Quimica", "Filosofia", "Sociologia"]

    assert filtrar_materias_por_serie(todas, "7 Ano") == ["Matematica", "Ciencias"]
    assert filtrar_materias_por_serie(todas, "2 Ano EM") == [
        "Matematica",
        "Biologia",
        "Fisica",
        "Quimica",
        "Filosofia",
        "Sociologia",
    ]


def test_materias_para_template_marca_permissao_por_etapa():
    materias = {
        item["valor"]: item
        for item in materias_para_template(["Matematica", "Ciencias", "Fisica", "Filosofia"])
    }

    assert materias["Matematica"]["permitida_ef"] is True
    assert materias["Matematica"]["permitida_em"] is True
    assert materias["Ciencias"]["permitida_ef"] is True
    assert materias["Ciencias"]["permitida_em"] is False
    assert materias["Fisica"]["permitida_ef"] is False
    assert materias["Fisica"]["permitida_em"] is True
    assert materias["Filosofia"]["permitida_ef"] is False
    assert materias["Filosofia"]["permitida_em"] is True
