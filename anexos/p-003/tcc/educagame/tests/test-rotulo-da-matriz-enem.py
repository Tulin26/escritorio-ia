"""O rótulo "Competência N – Habilidade HN" do ENEM tem de existir na Matriz de Referência.

A Matriz de Referência do INEP tem 30 habilidades por área, cada uma dentro de
UMA competência. Em 16/09/2026 a tela mostrava "Competência 3 – Habilidade 31"
(Natureza, que tem 30), "Competência 4 – Habilidade 42" (Matemática) e
"Competência 3 – Habilidade H30" (Linguagens, onde a 3 vai de H9 a H11): 7 dos
10 rótulos vistos da IA eram impossíveis, e 4 dos 15 do banco de reserva
também. O ENEM e a Batalha contra Chefes mostram o rótulo no cabeçalho.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import services.enem_service as enem
from services.enem_service import _prompt_enem, _rotulo_da_matriz

RAIZ = Path(__file__).resolve().parents[1]
LING = "Linguagens e suas Tecnologias"
MAT = "Matematica e suas Tecnologias"
NAT = "Ciencias da Natureza e suas Tecnologias"
HUM = "Ciencias Humanas e Sociais Aplicadas"

# A Matriz de Referência do ENEM (INEP): habilidades de cada competência.
MATRIZ = {
    LING: [(1, 4), (5, 8), (9, 11), (12, 14), (15, 17), (18, 20), (21, 24), (25, 27), (28, 30)],
    MAT: [(1, 5), (6, 9), (10, 14), (15, 18), (19, 23), (24, 26), (27, 30)],
    NAT: [(1, 4), (5, 7), (8, 12), (13, 16), (17, 19), (20, 23), (24, 27), (28, 30)],
    HUM: [(1, 5), (6, 10), (11, 15), (16, 20), (21, 25), (26, 30)],
}


def par_existe(rotulo: str, area: str) -> bool:
    achado = re.fullmatch(r"Competência (\d+) – Habilidade H(\d+)", rotulo)
    if not achado:
        return False
    competencia, habilidade = int(achado.group(1)), int(achado.group(2))
    faixas = MATRIZ[area]
    return 1 <= competencia <= len(faixas) and faixas[competencia - 1][0] <= habilidade <= faixas[competencia - 1][1]


# ====================== OS RÓTULOS DA IA ======================


@pytest.mark.parametrize(
    "rotulo, area, esperado",
    [
        # os sete impossíveis vistos em 16/09: a competência fica
        ("Competência 3 – Habilidade 31", NAT, "Competência 3"),
        ("Competência 4 – Habilidade 42", MAT, "Competência 4"),
        ("Competência 4 – Habilidade 41", LING, "Competência 4"),
        ("Competência 3 – Habilidade H30", LING, "Competência 3"),
        ("Competência 4 – Habilidade 43", LING, "Competência 4"),
        ("Competência 3 – Habilidade H25", MAT, "Competência 3"),
        ("Competência 2 – Habilidade H24", HUM, "Competência 2"),
        # os três válidos: ficam, no formato da tela
        ("Competência 1 – Habilidade 5", MAT, "Competência 1 – Habilidade H5"),
        ("Competência 4 – Habilidade 13", LING, "Competência 4 – Habilidade H13"),
        ("Competência 1 – Habilidade 2", MAT, "Competência 1 – Habilidade H2"),
    ],
)
def test_os_rotulos_vistos_da_ia(rotulo, area, esperado):
    assert _rotulo_da_matriz(rotulo, area) == esperado


@pytest.mark.parametrize(
    "rotulo, area, esperado",
    [
        ("C7 - H26", NAT, "Competência 7 – Habilidade H26"),
        ("Competência de área 3 – H10", NAT, "Competência 3 – Habilidade H10"),
        # a competência escrita nessas formas também vale: a H26 é da 7, a
        # H10 é da 3 -- e sem competência nenhuma não há o que deduzir
        ("C6 - H26", NAT, "Competência 6"),
        ("C5", NAT, "Competência 5"),
        ("Competência de área 2 – H10", NAT, "Competência 2"),
        ("Competência de área 5", NAT, "Competência 5"),
        ("Competencia 4 - Habilidade H16", MAT, "Competência 4 – Habilidade H16"),
        ("COMPETÊNCIA 6 – HABILIDADE 18", LING, "Competência 6 – Habilidade H18"),
        # a competência ESCRITA vale; a H18 é da 6, então sai
        ("COMPETÊNCIA 5 – HABILIDADE H18", LING, "Competência 5"),
        ("Competência 3", NAT, "Competência 3"),
    ],
)
def test_outras_escritas_do_mesmo_rotulo(rotulo, area, esperado):
    assert _rotulo_da_matriz(rotulo, area) == esperado


def test_a_habilidade_sozinha_ganha_a_sua_competencia():
    assert _rotulo_da_matriz("Habilidade H18", LING) == "Competência 6 – Habilidade H18"
    assert _rotulo_da_matriz("H26", HUM) == "Competência 6 – Habilidade H26"


@pytest.mark.parametrize(
    "rotulo, area",
    [
        ("Competência 9 – Habilidade H28", MAT),  # Matemática tem 7
        ("Competência 0 – Habilidade H1", NAT),
        ("Competência 7", HUM),  # Humanas tem 6
        ("H31", NAT),
        ("Habilidade 0", LING),
    ],
)
def test_o_que_nao_existe_na_area_some(rotulo, area):
    """Melhor nenhum rótulo do que um falso."""
    assert _rotulo_da_matriz(rotulo, area) == ""


@pytest.mark.parametrize(
    "rotulo, area",
    [
        ("Questão autoral – Matemática", MAT),
        ("", NAT),
        ("Competência 3 – Habilidade H31", "Area Inexistente XYZ"),
    ],
)
def test_o_que_nao_e_rotulo_da_matriz_fica_como_esta(rotulo, area):
    assert _rotulo_da_matriz(rotulo, area) == rotulo


@pytest.mark.parametrize("area", list(MATRIZ))
def test_cada_par_da_matriz_inteira(area):
    """As 30 habilidades contra todas as competências da área: o par fica
    só quando a habilidade é daquela competência."""
    for competencia, (inicio, fim) in enumerate(MATRIZ[area], 1):
        for habilidade in range(1, 31):
            rotulo = f"Competência {competencia} – Habilidade {habilidade}"
            if inicio <= habilidade <= fim:
                esperado = f"Competência {competencia} – Habilidade H{habilidade}"
            else:
                esperado = f"Competência {competencia}"
            assert _rotulo_da_matriz(rotulo, area) == esperado, rotulo


# ====================== O BANCO DE RESERVA ======================


def _rotulos_do_banco():
    for area, questoes in enem._FALLBACK_POR_AREA.items():
        for questao in questoes:
            yield area, questao
    for questao in enem._fallback_matematica_variantes():
        yield MAT, questao


def test_todo_rotulo_do_banco_existe_na_matriz():
    for area, questao in _rotulos_do_banco():
        assert par_existe(_rotulo_da_matriz(questao["matriz_enem"], area), area), questao["pergunta"]
        assert "masses" not in str(questao["explicacao"]), "era 'massas populacionais'"


@pytest.mark.parametrize(
    "comeco, rotulo, habilidade",
    [
        ("Em um texto argumentativo", "Competência 6 – Habilidade H18",
         "organização e estruturação de textos de diferentes gêneros"),
        ("A charge e o meme", "Competência 7 – Habilidade H22",
         "relacionar, em diferentes textos, opiniões e recursos linguísticos"),
        ("Leia o trecho: 'A língua é viva", "Competência 8 – Habilidade H25",
         "marcas que singularizam as variedades linguísticas"),
        ("Uma torneira perde 1 gota", "Competência 3 – Habilidade H12",
         "situação-problema com medidas de grandezas"),
        ("Em um grupo de 40 alunos", "Competência 1 – Habilidade H3",
         "situação-problema com conhecimentos numéricos (era geometria)"),
        ("A fotossíntese", "Competência 3 – Habilidade H9",
         "fluxo de energia para a vida (era evolução)"),
        ("O aquecimento global", "Competência 3 – Habilidade H10",
         "perturbações ambientais e seus efeitos"),
        ("Dois objetos de massas diferentes", "Competência 6 – Habilidade H20",
         "causas ou efeitos dos movimentos de objetos (era biotecnologia)"),
        ("O processo de globalização", "Competência 2 – Habilidade H9",
         "organizações socioeconômicas em escala mundial"),
        ("A Revolução Francesa", "Competência 5 – Habilidade H23",
         "valores na estruturação política das sociedades"),
        ("A urbanização acelerada", "Competência 6 – Habilidade H26",
         "processo de ocupação dos meios físicos"),
    ],
)
def test_o_rotulo_do_banco_e_o_da_habilidade_que_a_questao_pede(comeco, rotulo, habilidade):
    """Os onze trocados em 16/09/2026, cada um com a descrição oficial da
    habilidade que justifica a escolha."""
    questao = next(q for _, q in _rotulos_do_banco() if q["pergunta"].startswith(comeco))

    assert questao["matriz_enem"] == rotulo, habilidade


def test_o_rotulo_fora_do_formato_sai_no_formato_da_tela(monkeypatch):
    """As variantes de Matemática escrevem "Competencia 1 - Habilidade H3"."""
    monkeypatch.setattr(enem.random, "choice", lambda opcoes: opcoes[-1])

    questao = enem._fallback(MAT, "Medio")

    assert questao["pergunta"].startswith("Um produto de R$ 320,00")
    assert questao["matriz_enem"] == "Competência 1 – Habilidade H3"


@pytest.mark.parametrize("area", list(MATRIZ))
def test_a_questao_do_banco_sai_com_o_rotulo_da_matriz(area, monkeypatch):
    monkeypatch.setattr(enem.random, "choice", lambda opcoes: opcoes[0])

    questao = enem._fallback(area, "Medio")

    assert par_existe(questao["matriz_enem"], area), questao["matriz_enem"]


def test_as_questoes_autorais_mantem_o_rotulo_proprio():
    """As 2.220 questões convertidas dos outros bancos não têm habilidade
    mapeada e dizem o que são -- a correção não pode apagar isso."""
    for area in MATRIZ:
        for questao in enem._fallback_autoral_por_area(area)[:50]:
            assert _rotulo_da_matriz(questao["matriz_enem"], area) == questao["matriz_enem"]
            assert questao["matriz_enem"].startswith("Questão autoral")


# ====================== O CAMINHO DA IA ======================


def test_a_questao_da_ia_sai_com_o_rotulo_corrigido(monkeypatch):
    def ia(*_args, **_kwargs):
        return {
            "pergunta": "Por que os painéis solares geram mais energia no verão?",
            "alternativas": ["Porque o Sol fica mais alto", "Porque o ar é menos denso", "Porque chove menos", "Porque é mais quente", "Por nenhum motivo"],
            "correta": "Porque o Sol fica mais alto",
            "explicacao": [{"tipo": "resultado", "conteudo": "O Sol mais alto aumenta a intensidade da radiação."}],
            "matriz_enem": "Competência 3 – Habilidade 31",
        }

    monkeypatch.setattr(enem, "gerar_json_ia", ia)

    questao = enem._gerar_via_ia(NAT, "Medio")

    assert questao is not None
    assert questao["matriz_enem"] == "Competência 3"


@pytest.mark.parametrize("area", list(MATRIZ))
def test_o_prompt_diz_quais_habilidades_cabem_em_cada_competencia(area):
    _, usuario = _prompt_enem(area, "Medio")

    for competencia, (inicio, fim) in enumerate(MATRIZ[area], 1):
        assert re.search(rf"Competência {competencia} \([^)]+\): H{inicio} a H{fim}[;.]", usuario)
    assert f"Competência {len(MATRIZ[area]) + 1} (" not in usuario
    # "HYY" sugeria dois algarismos -- e a IA mandava H41, H42, H43
    assert "HYY" not in usuario


@pytest.mark.parametrize(
    "area, competencia, assunto",
    [
        # as que a IA confundia em 16/09/2026: questões de português em
        # português marcadas como língua estrangeira ou uso de tecnologia
        (LING, 2, "língua estrangeira"),
        (LING, 1, "tecnologias"),
        (LING, 7, "persuasão"),
        (LING, 8, "língua portuguesa"),
        (MAT, 2, "geometria"),
        (NAT, 6, "física"),
        (HUM, 5, "cidadania"),
    ],
)
def test_o_prompt_diz_o_assunto_de_cada_competencia(area, competencia, assunto):
    """Só com as faixas, a IA marcava "Competência 2 – Habilidade H6" (língua
    estrangeira) numa questão de ironia em português."""
    _, usuario = _prompt_enem(area, "Medio")

    trecho = re.search(rf"Competência {competencia} \(([^)]+)\)", usuario)
    assert trecho and assunto in trecho.group(1)


def test_cada_area_tem_um_assunto_por_competencia():
    assert {area: len(temas) for area, temas in enem._TEMAS_DAS_COMPETENCIAS.items()} == {
        area: len(faixas) for area, faixas in MATRIZ.items()
    }


# ====================== A TELA ======================


@pytest.mark.parametrize("template", ["enem.html", "boss_rush.html"])
def test_sem_rotulo_a_tela_nao_deixa_o_separador_sobrando(client, template):
    html = (RAIZ / "web" / "templates" / template).read_text(encoding="utf-8-sig")
    linha = next(l.strip() for l in html.splitlines() if "matriz_enem" in l)

    with client.application.test_request_context("/"):
        molde = client.application.jinja_env.from_string(linha)
        com = molde.render(questao={"dificuldade": "Medio", "matriz_enem": "Competência 3"})
        sem = molde.render(questao={"dificuldade": "Medio", "matriz_enem": ""})

    assert com == "<span>Médio · Competência 3</span>"
    assert sem == "<span>Médio</span>"
