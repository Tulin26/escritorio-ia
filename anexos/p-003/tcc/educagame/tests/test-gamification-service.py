from services.gamification_service import calcular_badges, streak_acertos


def test_streak_acertos_calcula_maior_sequencia():
    logs = [
        {"resultado": "Acertou"},
        {"resultado": "Acertou"},
        {"resultado": "Errou"},
        {"resultado": "Acertou"},
        {"resultado": "Acertou"},
        {"resultado": "Acertou"},
    ]

    assert streak_acertos(logs) == 3


def test_calcular_badges_primeiro_acerto_e_persistente():
    logs = [{"resultado": "Acertou", "materia": "Matematica"}] + [
        {"resultado": "Errou", "materia": "Portugues"} for _ in range(19)
    ]

    ids = {badge["id"] for badge in calcular_badges(logs, {"nome": "Aluno"})}

    assert "primeiro_acerto" in ids
    assert "persistente" in ids


def test_calcular_badges_multimateria():
    logs = [
        {"resultado": "Acertou", "materia": "Matematica"},
        {"resultado": "Acertou", "materia": "Portugues"},
        {"resultado": "Acertou", "materia": "LAB-Fisica"},
        {"resultado": "Acertou", "materia": "RPG-Historia"},
    ]

    ids = {badge["id"] for badge in calcular_badges(logs, {"nome": "Aluno"})}

    assert "multimateria" in ids
