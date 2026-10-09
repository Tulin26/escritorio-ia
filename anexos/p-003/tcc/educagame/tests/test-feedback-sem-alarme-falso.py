"""O feedback do erro não acusa o que não aconteceu.

Medido em 13/09/2026 nos bancos offline, 61.923 pares alternativa errada x
certa (20.641 questões):

- "arredondamento ou casa decimal" saía em 2.744 pares -- 1.969 só de inteiros;
- "muito parecida" saía em 2.946 pares só porque as 8 primeiras letras
  batiam, e em 58% deles as duas eram pouco parecidas;
- até 195 citações terminavam em `.”.`;
- ENEM e Batalha mandavam a ÁREA no lugar da matéria, e perdiam o diagnóstico.
"""

from __future__ import annotations

from pathlib import Path

from services.pedagogical_feedback import gerar_feedback_pedagogico


def _fb(materia: str, aluno: str, certa: str, pergunta: str = "") -> dict:
    return gerar_feedback_pedagogico(
        dados={"pergunta": pergunta}, materia=materia, resposta_aluno=aluno, resposta_correta=certa
    )


def test_perto_com_inteiros_nao_e_arredondamento():
    r = _fb("Fisica", "22 m/s", "20 m/s")

    assert "arredondamento" not in r["confundiu"] and "casa decimal" not in r["confundiu"]
    assert "conta intermediária" in r["confundiu"]


def test_perto_com_decimal_continua_sendo_arredondamento():
    assert "arredondamento" in _fb("Quimica", "3,2", "3,05")["confundiu"]


def test_mesmo_comeco_nao_e_muito_parecida():
    r = _fb("Quimica", "moléculas de amônia (NH3)", "moléculas apolares, como o gás nitrogênio")

    assert "parecida" not in r["confundiu"] and "quase igual" not in r["confundiu"]
    assert "amônia" in r["confundiu"] and "apolares" in r["confundiu"]


def test_parecidas_mas_de_conceito_diferente_nao_sao_quase_iguais():
    # Similaridade entre 0,60 e 0,79: dividem o começo, mas o que muda é o
    # conceito inteiro. "Quase igual" só vale a partir de 0,9.
    for aluno, certa in [
        ("O sujeito é oculto", "O sujeito é indeterminado"),
        ("Revolução Industrial", "Revolução Francesa"),
        ("Ligação iônica", "Ligação covalente"),
        ("A corrente elétrica é contínua", "A corrente elétrica é alternada"),
    ]:
        r = _fb("Portugues", aluno, certa)
        assert "quase igual" not in r["confundiu"], (aluno, certa)
        assert aluno in r["confundiu"] and certa in r["confundiu"]


def test_mesmo_comeco_nao_apaga_o_sinal_trocado():
    assert "sinal" in _fb("Matematica", "x = 3 e x = 5", "x = 3 e x = -5")["confundiu"]


def test_detalhe_de_verdade_continua_quase_igual_e_cita_as_duas():
    r = _fb("Portugues", "O aluno deve obedecer as normas.", "O aluno deve obedecer às normas.")

    assert "quase igual" in r["confundiu"]
    assert "obedecer as normas" in r["confundiu"] and "obedecer às normas" in r["confundiu"]


def test_citacao_nao_termina_com_pontuacao_dupla():
    for materia, aluno, certa in [
        ("Ingles", "John say (that) he was tired.", "John said (that) he was tired."),
        ("Historia", "O Brasil virou república em 1889.", "O Brasil virou império em 1822."),
    ]:
        assert ".”." not in _fb(materia, aluno, certa)["confundiu"]


def test_citacao_mantem_a_interrogacao_da_alternativa():
    r = _fb("Portugues", "Quem chegou primeiro?", "Quem saiu primeiro?")

    assert "primeiro?”" in r["confundiu"]
    assert "?”." not in r["confundiu"]


def test_questao_do_enem_do_banco_leva_a_materia_de_origem():
    import services.enem_service as enem

    q = enem._fallback_autoral_por_area("Matematica e suas Tecnologias")[0]

    assert q["materia"] == "Matematica"


def test_enem_so_com_a_area_ainda_ganha_diagnostico_numerico():
    # Questão da IA: não traz matéria, só a área.
    assert "sinal" in _fb("Matematica e suas Tecnologias", "-15", "15")["confundiu"]


def test_enem_e_batalha_passam_a_materia_da_questao():
    raiz = Path(__file__).resolve().parents[1] / "web" / "routes"
    for rota in ("enem_fla.py", "boss_rush_fla.py"):
        assert 'materia=questao.get("materia") or questao.get("area_bncc"' in (raiz / rota).read_text(encoding="utf-8"), rota
