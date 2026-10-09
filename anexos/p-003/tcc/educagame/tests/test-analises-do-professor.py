"""A aba de análises do professor — o que ela calcula, sem desenhar nada.

MELHORIA: `renderizar_aba_analises` tinha 212 linhas e **nenhum teste**. Boa
parte dela nunca foi tela: o filtro por modo, os três montadores de histórico
para PDF, o recorte por matéria, as métricas e a escolha do nome do arquivo
são cálculo puro embrulhado em Streamlit. Ficaram sem rede porque ninguém
consegue chamar meia tela.

Extraídas, testam-se direto — este arquivo não usa a bancada. O que sobrou na
tela (122 linhas) é sequência de widgets, e essa a fotografia cobre.

O caso que mais importa é a separação ENEM × Boss Rush: os dois gravam matéria
começando com "ENEM-", e é só o `modo` que os distingue. Sem o filtro certo, o
boletim do simulado viria com as questões do chefe misturadas.
"""

from __future__ import annotations

import pandas as pd
import pytest

from st.ui.professor_analises_st import (
    OPCOES_TIPO,
    _historico_boss_rush,
    _historico_enem,
    _historico_escape_room,
    filtrar_por_tipo,
    metricas_do_recorte,
    recorte_para_pdf,
    rotulo_e_nome_do_pdf,
    rotulos_de_materia,
)

TODAS = "📚 Todas as matérias"


def log(modo, materia, resultado="Acertou", **extra):
    base = {
        "aluno_id": "a1", "modo": modo, "materia": materia, "resultado": resultado,
        "pergunta_texto": f"P {materia}", "resposta_correta": "A", "resposta_aluno": "B",
        "explicacao_ia": "porque sim", "tempo_resposta": 12,
        "area_bncc": "", "dificuldade": "Medio", "matriz_enem": "H21",
    }
    base.update(extra)
    return base


# Os modos gravam SEMPRE o par (modo, prefixo da matéria) juntos -- conferido
# em st/ui/tela_rpg_st.py, web/routes/rpg_fla.py e laboratorio_fla.py. Log com
# `modo` vazio é registro antigo do Oráculo, de antes de o campo existir, e por
# isso nunca carrega prefixo.
LINHAS = [
    log("oraculo", "Matematica"),
    log("", "Historia", "Errou"),                       # modo vazio = oraculo antigo
    log("treino", "Portugues"),
    log("enem", "ENEM-Matematica"),
    log("", "ENEM-Linguagens", "Errou"),                # ENEM sem modo gravado
    log("boss_rush_enem", "ENEM-Ciencias"),
    log("escape_room", "Quimica", "Errou"),
    log("laboratorio-flask", "LAB-Fisica"),
    log("rpg", "RPG-Matematica", "Errou"),
]

DF = pd.DataFrame(LINHAS)


def _materias(df) -> list[str]:
    return sorted(df["materia"].tolist())


# ====================== O FILTRO POR MODO ======================


def test_o_seletor_oferece_os_sete_modos():
    assert len(OPCOES_TIPO) == 7
    assert set(OPCOES_TIPO.values()) == {
        "oraculo", "treino", "enem", "boss_rush_enem", "escape_room", "laboratorio", "rpg",
    }


def test_enem_nao_traz_as_questoes_do_boss_rush():
    """O caso que justifica o teste: os dois gravam matéria "ENEM-...".

    Só o `modo` os separa, e o do ENEM às vezes vem vazio — então a regra
    precisa aceitar o prefixo E excluir boss_rush ao mesmo tempo.
    """
    enem = filtrar_por_tipo(DF, "enem")

    assert _materias(enem) == ["ENEM-Linguagens", "ENEM-Matematica"]
    assert "ENEM-Ciencias" not in _materias(enem), "a questão do chefe entrou no simulado"


def test_boss_rush_traz_so_o_dele():
    assert _materias(filtrar_por_tipo(DF, "boss_rush_enem")) == ["ENEM-Ciencias"]


def test_oraculo_absorve_todo_registro_sem_modo():
    """`modo` vazio vira "oraculo", sem olhar a matéria.

    Registro antigo é do Oráculo mesmo — o campo `modo` nasceu depois dele.
    """
    assert "Historia" in _materias(filtrar_por_tipo(DF, "oraculo"))


def test_registro_antigo_do_enem_aparece_no_oraculo_e_no_enem():
    """A única sobreposição que existe hoje. Documentada, não corrigida.

    O ENEM aceita a matéria com prefixo mesmo sem `modo`; o Oráculo trata
    `modo` vazio como seu. Um log anterior ao campo `modo` satisfaz as duas
    regras e é contado nas duas faixas.

    Não é alcançável por registro novo: `enem_st`/`enem_fla` gravam `modo`
    junto com o prefixo. Só atinge base antiga, e escolher um dono para esses
    registros é decisão de produto, não de refatoração — por isso aqui só se
    prende o que o código faz.
    """
    assert "ENEM-Linguagens" in _materias(filtrar_por_tipo(DF, "enem"))
    assert "ENEM-Linguagens" in _materias(filtrar_por_tipo(DF, "oraculo"))


@pytest.mark.parametrize(
    "tipo, esperado",
    [
        ("treino", ["Portugues"]),
        ("escape_room", ["Quimica"]),
        ("laboratorio", ["LAB-Fisica"]),
        ("rpg", ["RPG-Matematica"]),
    ],
)
def test_cada_modo_traz_o_seu(tipo, esperado):
    assert _materias(filtrar_por_tipo(DF, tipo)) == esperado


def test_registro_de_hoje_cai_em_exatamente_uma_faixa():
    """A propriedade inteira, e não sete casos: cada log tem um dono.

    É o que impede uma regra nova de roubar linhas de outra faixa sem ninguém
    notar. Vale para o que os modos gravam HOJE -- `modo` preenchido. O
    registro antigo sem `modo` é a exceção conhecida, e tem teste próprio.
    """
    de_hoje = DF[DF["modo"] != ""]

    vistos = []
    for tipo in OPCOES_TIPO.values():
        vistos += filtrar_por_tipo(de_hoje, tipo).index.tolist()

    assert len(vistos) == len(set(vistos)), "há registro contado em dois modos"
    assert len(vistos) == len(de_hoje), "algum registro não aparece em modo nenhum"


def test_tipo_desconhecido_devolve_tudo():
    assert len(filtrar_por_tipo(DF, "modo-que-nao-existe")) == len(DF)


@pytest.mark.parametrize(
    "tipo, prefixo, sem_hifen, no_meio",
    [
        ("laboratorio", "LAB-", "LABFisica", "Revisao LAB-Fisica"),
        ("rpg", "RPG-", "RPGeral", "Prova RPG-Historia"),
    ],
)
def test_o_marcador_e_o_prefixo_inteiro_com_hifen(tipo, prefixo, sem_hifen, no_meio):
    """Duas formas de afrouxar o marcador, e as duas passariam sem isto.

    Este projeto já pagou três vezes pelo mesmo defeito -- marcador curto
    casado como pedaço de texto em vez de marcador inteiro. Aqui ele está
    ancorado no começo E leva o hífen; as duas metades precisam de rede.
    """
    df = pd.DataFrame([
        log("treino", sem_hifen),                 # cai se o hífen sair do marcador
        log("treino", no_meio),                   # cai se o startswith virar contains
        log("treino", prefixo + "Fisica"),        # o legítimo
    ])

    assert _materias(filtrar_por_tipo(df, tipo)) == [prefixo + "Fisica"]


# ====================== O RECORTE POR MATÉRIA ======================


def test_rotulos_trazem_a_contagem():
    rotulos = rotulos_de_materia(pd.DataFrame([log("treino", "Fisica"), log("treino", "Fisica"),
                                               log("treino", "Arte")]))

    assert rotulos == ["Arte (1 questões)", "Fisica (2 questões)"]


def test_recorte_por_materia_filtra_e_rotula():
    df_pdf, rotulo = recorte_para_pdf(DF, "Historia (1 questões)")

    assert _materias(df_pdf) == ["Historia"]
    assert rotulo == "Matéria: Historia"


def test_recorte_de_todas_nao_filtra():
    df_pdf, rotulo = recorte_para_pdf(DF, TODAS)

    assert len(df_pdf) == len(DF)
    assert rotulo == "Todas as matérias"


def test_materia_com_parenteses_no_nome_sobrevive_ao_recorte():
    # O rótulo é desmontado por rsplit(" (", 1): o parêntese da contagem é o
    # último, então um nome que já tenha parêntese continua inteiro.
    df = pd.DataFrame([log("treino", "Educacao Fisica (EF)")])

    df_pdf, rotulo = recorte_para_pdf(df, "Educacao Fisica (EF) (1 questões)")

    assert _materias(df_pdf) == ["Educacao Fisica (EF)"]
    assert rotulo == "Matéria: Educacao Fisica (EF)"


# ====================== AS MÉTRICAS ======================


def test_metricas_contam_acertos_e_erros():
    total, acertos, erros, pct = metricas_do_recorte(DF)

    assert total == 9
    assert acertos + erros == total
    assert acertos == 5 and erros == 4
    assert pct == 55


def test_recorte_vazio_nao_divide_por_zero():
    # Chega aqui quando a matéria escolhida ficou sem registro.
    assert metricas_do_recorte(DF.iloc[0:0]) == (0, 0, 0, 0)


def test_qualquer_coisa_que_nao_seja_acertou_conta_como_erro():
    df = pd.DataFrame([log("treino", "X", "Errou"), log("treino", "Y", "Pulou"),
                       log("treino", "Z", "Acertou")])

    total, acertos, erros, _ = metricas_do_recorte(df)

    assert (total, acertos, erros) == (3, 1, 2)


# ====================== O NOME DO ARQUIVO ======================


@pytest.mark.parametrize(
    "tipo, prefixo, no_rotulo",
    [
        ("enem", "ENEM_", "PDF ENEM"),
        ("boss_rush_enem", "Boss_Rush_", "PDF Boss Rush"),
        ("escape_room", "Escape_Room_", "PDF Escape Room"),
        ("rpg", "RPG_", "PDF RPG"),
        ("oraculo", "Revisao_", "Baixar PDF ("),
        ("treino", "Revisao_", "Baixar PDF ("),
        ("laboratorio", "Revisao_", "Baixar PDF ("),
    ],
)
def test_cada_modo_tem_seu_nome_de_arquivo(tipo, prefixo, no_rotulo):
    rotulo, nome = rotulo_e_nome_do_pdf(tipo, "Ana Maria", "Todas", 3)

    assert nome.startswith(prefixo), nome
    assert nome.endswith(".pdf")
    assert no_rotulo in rotulo


def test_o_nome_do_aluno_nao_leva_espaco_para_o_arquivo():
    _, nome = rotulo_e_nome_do_pdf("enem", "Ana Maria Souza", "Todas", 0)

    assert " " not in nome
    assert "Ana_Maria_Souza" in nome


def test_o_rotulo_mostra_quantos_erros():
    rotulo, _ = rotulo_e_nome_do_pdf("enem", "Ana", "Todas", 7)

    assert "7 erros" in rotulo


# ====================== OS HISTÓRICOS DO PDF ======================


def test_historico_enem_numera_e_resolve_a_area():
    df = pd.DataFrame([
        log("enem", "ENEM-Matematica", area_bncc="Matemática e suas Tecnologias"),
        log("enem", "ENEM-Linguagens", "Errou"),   # sem area_bncc: cai no nome da matéria
    ])

    historico = _historico_enem(df)

    assert [h["numero"] for h in historico] == [1, 2]
    assert historico[0]["area_label"] == "Matemática e suas Tecnologias"
    assert historico[1]["area_label"] == "Linguagens", "o prefixo ENEM- tinha que sair"
    assert historico[0]["acertou"] is True
    assert historico[1]["acertou"] is False


def test_historico_boss_rush_marca_o_chefe():
    historico = _historico_boss_rush(pd.DataFrame([log("boss_rush_enem", "ENEM-Ciencias")]))

    assert historico[0]["boss"] == "Boss Rush ENEM"
    assert historico[0]["area_label"] == "Ciencias"


def test_historico_escape_room_numera_as_salas():
    df = pd.DataFrame([log("escape_room", "Quimica"), log("escape_room", "Fisica", "Errou")])

    historico = _historico_escape_room(df)

    assert [h["sala"] for h in historico] == [1, 2]
    assert historico[1]["acertou"] is False


@pytest.mark.parametrize(
    "montador", [_historico_enem, _historico_boss_rush, _historico_escape_room]
)
def test_tempo_ausente_vira_zero_e_nao_None(montador):
    # O PDF soma esse campo; None ali derrubaria a geração inteira do boletim.
    df = pd.DataFrame([log("enem", "ENEM-Matematica", tempo_resposta=None)])

    assert montador(df)[0]["tempo"] == 0
