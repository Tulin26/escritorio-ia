from __future__ import annotations

from collections import Counter
import re
import unicodedata

from core.config import MATERIAS
from services.banks.laboratorio import QUESTOES_LAB_POR_TEMA, listar_questoes_laboratorio
from services.banks.rpg import QUESTOES_RPG_POR_TEMA, listar_questoes_rpg


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()


def test_banco_laboratorio_tem_20_questoes_por_tema_de_exatas():
    for materia in ("Matematica", "Fisica", "Quimica"):
        questoes = listar_questoes_laboratorio(materia)
        contagem_temas = Counter(q["tema_usado"] for q in questoes)

        assert contagem_temas
        assert all(total >= QUESTOES_LAB_POR_TEMA for total in contagem_temas.values())
        assert len({q["id_offline"] for q in questoes}) == len(questoes)
        assert all(q.get("formula") for q in questoes)
        assert all(len(q.get("opcoes", [])) == 4 for q in questoes)


def test_banco_laboratorio_ef_tem_20_questoes_por_tema():
    for materia in ("Matematica", "Ciencias"):
        questoes = listar_questoes_laboratorio(materia, serie_tipo="EF")
        contagem_temas = Counter(q["tema_usado"] for q in questoes)

        assert contagem_temas
        assert all(total >= QUESTOES_LAB_POR_TEMA for total in contagem_temas.values())
        assert len({q["id_offline"] for q in questoes}) == len(questoes)
        assert all(q["serie_tipo"] == "EF" for q in questoes)
        assert all(q.get("formula") for q in questoes)
        assert all(len(q.get("opcoes", [])) == 4 for q in questoes)


def test_banco_laboratorio_offline_mostra_substituicao_nos_passos():
    for materia in ("Matematica", "Fisica", "Quimica"):
        for questao in listar_questoes_laboratorio(materia):
            passos = questao.get("passos_resolucao", [])

            assert passos
            assert any("=" in str(passo.get("conteudo", "")) for passo in passos)
            assert not any("Substituindo na formula, obtemos" in str(passo.get("conteudo", "")) for passo in passos)


def test_banco_laboratorio_percentual_em_massa_usa_notacao_clara():
    questoes = [
        questao
        for questao in listar_questoes_laboratorio("Quimica")
        if _sem_acento(questao["tema_usado"]) == "porcentagem em massa"
    ]

    assert questoes
    for questao in questoes:
        texto = " ".join(
            [
                questao.get("formula", ""),
                questao.get("legenda_variaveis", ""),
                *[str(passo.get("conteudo", "")) for passo in questao.get("passos_resolucao", [])],
            ]
        )
        assert r"\%m/m" not in texto
        assert "C_{m/m}" in texto or "C_m/m" in texto
        assert "percentual em massa" in texto


def test_banco_laboratorio_bhaskara_varia_modelos_de_pergunta():
    questoes = [
        questao
        for questao in listar_questoes_laboratorio("Matematica")
        if _sem_acento(questao["tema_usado"]) == "equacao do 2o grau"
    ]

    assert len(questoes) >= QUESTOES_LAB_POR_TEMA
    perguntas = {_sem_acento(questao["pergunta"]) for questao in questoes}
    assert len(perguntas) >= 10
    assert any("projetil" in pergunta for pergunta in perguntas)
    assert any("parabola" in pergunta for pergunta in perguntas)
    assert any("conjunto-solucao" in pergunta for pergunta in perguntas)
    assert any("simulador" in pergunta for pergunta in perguntas)


def test_banco_laboratorio_bhaskara_usa_coeficientes_didaticos():
    questoes = [
        questao
        for questao in listar_questoes_laboratorio("Matematica")
        if _sem_acento(questao["tema_usado"]) == "equacao do 2o grau"
    ]

    assert questoes
    for questao in questoes:
        numeros = [abs(int(numero)) for numero in re.findall(r"-?\d+", questao["pergunta"])]
        assert max(numeros) <= 200


def test_banco_laboratorio_fisica_e_quimica_variam_contexto():
    for materia in ("Fisica", "Quimica"):
        questoes = listar_questoes_laboratorio(materia)
        perguntas = {_sem_acento(questao["pergunta"]) for questao in questoes[:80]}

        assert any("laboratorio" in pergunta for pergunta in perguntas)
        assert any("analise" in pergunta or "controle de qualidade" in pergunta for pergunta in perguntas)


def test_banco_rpg_tem_50_questoes_por_tema():
    for materia in MATERIAS:
        questoes = listar_questoes_rpg(materia)
        contagem_temas = Counter(q["tema_usado"] for q in questoes)

        assert contagem_temas
        assert all(total >= QUESTOES_RPG_POR_TEMA for total in contagem_temas.values())
        assert len({q["id_offline"] for q in questoes}) == len(questoes)
        assert all(q.get("ambientacao") for q in questoes)
        assert all(len(q.get("opcoes", [])) == 4 for q in questoes)


def test_banco_rpg_quimica_varia_questoes_de_solucoes():
    questoes = [
        questao
        for questao in listar_questoes_rpg("Quimica")
        if _sem_acento(questao["tema_usado"]) == "solucoes"
    ]

    assert len(questoes) >= QUESTOES_RPG_POR_TEMA
    assert len({questao["pergunta"] for questao in questoes}) >= 4
    assert any("soluto" in " ".join([questao["pergunta"], *questao["opcoes"]]).lower() for questao in questoes)
    assert any("solvente" in " ".join([questao["pergunta"], *questao["opcoes"]]).lower() for questao in questoes)


def test_banco_rpg_matematica_pg_tem_opcoes_conectadas_ao_tema():
    questoes = [
        questao
        for questao in listar_questoes_rpg("Matematica")
        if "progressao geometrica" in _sem_acento(questao["tema_usado"])
    ]

    assert len(questoes) >= QUESTOES_RPG_POR_TEMA
    for questao in questoes[:12]:
        texto = _sem_acento(" ".join([questao["pergunta"], *questao["opcoes"]]))
        assert any(termo in texto for termo in ("razao", "multiplic", "quociente", "termo"))
        assert "repetir uma definicao sem mostrar" not in texto
        assert "ignorar autoria, escala" not in texto


def test_banco_rpg_fisica_cinematica_tem_opcoes_conectadas_ao_tema():
    questoes = [
        questao
        for questao in listar_questoes_rpg("Fisica")
        if "cinematica" in _sem_acento(questao["tema_usado"])
    ]

    assert len(questoes) >= QUESTOES_RPG_POR_TEMA
    for questao in questoes[:12]:
        texto = _sem_acento(" ".join([questao["pergunta"], *questao["opcoes"]]))
        assert any(termo in texto for termo in ("velocidade", "deslocamento", "tempo", "movimento"))
        assert "repetir uma definicao sem mostrar" not in texto
        assert "tratar o cenario como decoracao" not in texto


def test_banco_rpg_nao_usa_distratores_globais_desconectados():
    termos_bloqueados = (
        "escolher a rota apenas porque o simbolo parece familiar",
        "tratar o cenario como decoracao",
        "confundir opiniao do grupo",
        "generalizar uma pista isolada",
        "ignorar autoria, escala",
        "repetir uma definicao sem mostrar",
        "descartar as pistas contraditorias",
        "usar uma regra pronta mesmo quando o enigma pede",
    )

    for materia in MATERIAS:
        for questao in listar_questoes_rpg(materia):
            texto = _sem_acento(" ".join([questao.get("pergunta", ""), *questao.get("opcoes", [])]))
            assert not any(termo in texto for termo in termos_bloqueados)


def test_banco_rpg_nao_usa_molde_generico_de_palavra_chave():
    termos_bloqueados = (
        "palavra-chave",
        "primeira palavra conhecida",
        "não apenas repetir uma palavra do enunciado",
        "nao apenas repetir uma palavra do enunciado",
        "toda pista visual tem o mesmo significado",
    )
    questoes = listar_questoes_rpg("Historia")

    assert questoes
    for questao in questoes:
        texto = _sem_acento(" ".join([questao.get("enigma", ""), questao.get("pergunta", ""), *questao.get("opcoes", [])]))
        assert not any(_sem_acento(termo) in texto for termo in termos_bloqueados)
