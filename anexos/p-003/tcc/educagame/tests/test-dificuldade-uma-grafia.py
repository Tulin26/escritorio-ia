"""A dificuldade chega ao banco numa grafia só.

MELHORIA: medido nos logs reais, ela chegava em **quatro**:

| grafia | de onde |
|---|---|
| `Medio` | RPG, Treino, Boss Rush, ENEM |
| `Médio` | Laboratório, Oráculo, Escape Room |
| `Difícil` | Laboratório, Oráculo |
| `🔴 Difícil` | Laboratório do Streamlit — o rótulo do slider ia **direto** |

O painel do professor filtra e agrupa por esse campo, então `Medio` e
`Médio` contavam como dificuldades **diferentes**. É o mesmo defeito já
corrigido no prefixo de matéria (`LAB-Fisica` × `Fisica`), que fragmentava a
tela de Progresso.

A correção segue a regra do projeto — a **chave** fica sem acento e sem
emoji, o **rótulo** vem de `exibir_dificuldade()` na hora de desenhar — e mora
em `preparar_payload_log`, no mesmo lugar onde `resultado` e `modo` já eram
normalizados. Corrigir tela por tela deixaria a próxima nascer torta.
"""

from __future__ import annotations

import pytest

from core.config import (
    DIFICULDADES_COM_ACENTO,
    NIVEIS_DIFICULDADE,
    exibir_dificuldade,
    normalizar_dificuldade,
)
from repositories.log_repo import preparar_payload_log

BASE = {
    "aluno_id": "aluno-1",
    "escola_id": "escola-1",
    "materia": "LAB-Matematica",
    "resultado": "Acertou",
}


def gravado(dificuldade):
    return preparar_payload_log({**BASE, "dificuldade": dificuldade}).get("dificuldade")


# ====================== AS QUATRO GRAFIAS VIRAM UMA ======================


@pytest.mark.parametrize(
    "grafia,esperado",
    [
        ("Medio", "Medio"),
        ("Médio", "Medio"),
        ("🟡 Médio", "Medio"),
        ("Dificil", "Dificil"),
        ("Difícil", "Dificil"),
        ("🔴 Difícil", "Dificil"),
        ("Facil", "Facil"),
        ("Fácil", "Facil"),
        ("🟢 Fácil", "Facil"),
    ],
)
def test_toda_grafia_real_colapsa_numa_chave(grafia, esperado):
    assert normalizar_dificuldade(grafia) == esperado


def test_as_quatro_grafias_medidas_nos_logs_viram_duas_chaves():
    """O caso exato que o painel fragmentava."""
    chaves = {normalizar_dificuldade(g) for g in ("Medio", "Médio", "Difícil", "🔴 Difícil")}

    assert chaves == {"Medio", "Dificil"}


@pytest.mark.parametrize("grafia", ["  MÉDIO  ", "medio", "MEDIO", "Médio "])
def test_caixa_e_espaco_nao_criam_categoria_nova(grafia):
    assert normalizar_dificuldade(grafia) == "Medio"


# ====================== O QUE NÃO É DIFICULDADE ======================


def test_valor_desconhecido_passa_intacto():
    """Inventar "Medio" para um valor que não é nenhum dos três esconderia o
    problema em vez de mostrá-lo — e o painel passaria a mentir.
    """
    assert normalizar_dificuldade("Impossível") == "Impossível"


@pytest.mark.parametrize("vazio", ["", None, "   "])
def test_vazio_continua_vazio(vazio):
    assert normalizar_dificuldade(vazio) == ""


# ====================== A CHAVE VAI PARA O BANCO ======================


@pytest.mark.parametrize(
    "grafia,esperado",
    [("Médio", "Medio"), ("🔴 Difícil", "Dificil"), ("🟢 Fácil", "Facil")],
)
def test_o_log_grava_a_chave_e_nao_o_rotulo(grafia, esperado):
    assert gravado(grafia) == esperado


def test_normalizar_num_lugar_so_conserta_os_oito_modos():
    """Os oito modos passam por `preparar_payload_log`. Se a normalização
    morasse na tela, a próxima nasceria torta — foi assim que quatro grafias
    apareceram.
    """
    for modo, grafia in [
        ("laboratorio-flask", "Médio"),
        ("rpg-flask", "Medio"),
        ("laboratorio", "🔴 Difícil"),
        ("oraculo-flask", "Difícil"),
    ]:
        dados = preparar_payload_log({**BASE, "modo": modo, "dificuldade": grafia})
        assert dados["dificuldade"] in NIVEIS_DIFICULDADE, f"{modo} escapou"


@pytest.mark.parametrize("vazio", ["", None])
def test_dificuldade_vazia_nao_vira_texto_vazio_no_banco(vazio):
    """Coluna de texto com `""` e com `NULL` são coisas diferentes para o
    `group by` do painel."""
    assert gravado(vazio) is None


def test_sem_o_campo_a_coluna_nem_aparece():
    assert "dificuldade" not in preparar_payload_log(dict(BASE))


# ====================== O RÓTULO VOLTA NA TELA ======================


@pytest.mark.parametrize(
    "chave,rotulo", [("Facil", "Fácil"), ("Medio", "Médio"), ("Dificil", "Difícil")]
)
def test_a_tela_mostra_o_rotulo_com_acento(chave, rotulo):
    """Guardar sem acento não pode virar tela sem acento — é a mesma regra
    "chave × rótulo" da matéria."""
    assert exibir_dificuldade(chave) == rotulo


def test_o_rotulo_aceita_qualquer_grafia_de_entrada():
    """O painel lê linhas antigas, gravadas antes da normalização."""
    for grafia in ("Médio", "medio", "🟡 Médio", "Medio"):
        assert exibir_dificuldade(grafia) == "Médio"


def test_os_tres_niveis_tem_rotulo():
    """Um nível sem rótulo apareceria sem acento na tela, e ninguém notaria
    até um professor reclamar."""
    assert set(DIFICULDADES_COM_ACENTO) == set(NIVEIS_DIFICULDADE)


def test_a_analise_do_professor_usa_o_rotulo():
    from pathlib import Path

    fonte = (Path(__file__).resolve().parent.parent
             / "st" / "ui" / "professor_analises_st.py").read_text(encoding="utf-8")

    assert 'exibir_dificuldade(row_pdf.get("dificuldade"' in fonte
    assert 'row_pdf.get("dificuldade", ""),' not in fonte, "ainda mostra a chave crua"
