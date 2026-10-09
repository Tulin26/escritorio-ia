"""A resolução passa a ser guardada, para dar como medir validações da IA.

MELHORIA: pelo menos uma validação ficou parada por não haver como medir o
risco dela contra dado real — recusar resolução que não calcula nada (a IA
escreve `x = (-b ± √Δ)/2a` e nunca resolve o Δ, e o aluno não tem como seguir
os passos).

O banco offline não serve de amostra. Medido: **2.200 questões do Laboratório
em apenas 81 formas distintas** de resolução — o resto é o mesmo molde com
outros números. E escrever moldes novos de propósito tornaria a medição
circular: seria testar a regra contra exemplos escolhidos por causa dela. O
valor das medições que autorizaram as outras validações veio de o banco ser
**independente** — escrito antes, por outro motivo.

A distribuição que importa é a das respostas reais da IA. Ela existia e não
era guardada: `logs_pedagogicos` registrava pergunta, alternativas e
explicação, mas **não os passos** — justamente o que essas validações julgam.

Só o Laboratório preenche, e não é limitação: os outros modos passam por
`_normalizar_questao_oraculo`, que apaga `passos_resolucao` de exatas de
propósito ("no Oráculo, exatas é conceitual"). Laboratório é onde Bhaskara e
o Δ aparecem.
"""

from __future__ import annotations

import pytest

from repositories.log_repo import LOG_COLUMNS, preparar_payload_log

BARRA = chr(92)

BASE = {
    "aluno_id": "aluno-1",
    "escola_id": "escola-1",
    "materia": "LAB-Matematica",
    "resultado": "Acertou",
    "pergunta_texto": "Resolva x² − 5x + 6 = 0",
}

BHASKARA = [
    {"titulo": "1º Passo", "conteudo": f"{BARRA}Delta = 25 - 24 = 1"},
    {"titulo": "Resultado Final", "conteudo": "x = -2 e x = -3", "final": True},
]


def preparar(**mudancas):
    return preparar_payload_log({**BASE, **mudancas})


# ====================== O QUE É GUARDADO ======================


def test_a_coluna_existe_entre_as_conhecidas():
    """`preparar_payload_log` filtra por `LOG_COLUMNS`: fora dela, o campo é
    descartado em silêncio e a medição nunca teria dado."""
    assert "passos_json" in LOG_COLUMNS


def test_a_resolucao_do_laboratorio_e_guardada():
    dados = preparar(passos_resolucao=BHASKARA)

    assert dados["passos_json"] == [
        {"titulo": "1º Passo", "conteudo": f"{BARRA}Delta = 25 - 24 = 1"},
        {"titulo": "Resultado Final", "conteudo": "x = -2 e x = -3", "final": True},
    ]


def test_a_marca_de_passo_final_sobrevive():
    """Os três desenhos prototipados julgam o passo **final**. Sem essa
    marca, medir qualquer um deles seria impossível.
    """
    guardados = preparar(passos_resolucao=BHASKARA)["passos_json"]

    assert [p.get("final") for p in guardados] == [None, True]


def test_o_caminho_do_streamlit_tambem_funciona():
    """O Streamlit passa por `extras`, que entrega a chave já como
    `passos_json`; o Flask monta o dicionário com `passos_resolucao`. Os dois
    precisam chegar ao mesmo lugar.
    """
    pelo_flask = preparar(passos_resolucao=BHASKARA)
    pelo_streamlit = preparar(passos_json=BHASKARA)

    assert pelo_flask["passos_json"] == pelo_streamlit["passos_json"]


# ====================== O QUE NÃO É GUARDADO ======================


def test_modo_sem_passos_nao_ganha_a_coluna():
    """Treino, Oráculo, Escape Room e RPG não têm passos — a coluna não pode
    virar uma sequência de `null` ocupando espaço à toa."""
    assert "passos_json" not in preparar()


@pytest.mark.parametrize(
    "valor",
    [[], None, "texto solto", [{"conteudo": "   "}], [None, 5], {"a": 1}],
)
def test_resolucao_vazia_ou_malformada_nao_e_guardada(valor):
    assert "passos_json" not in preparar(passos_resolucao=valor)


@pytest.mark.parametrize(
    "valor",
    [[], None, "texto solto", [{"conteudo": "   "}], [None, 5]],
)
def test_o_streamlit_com_resolucao_vazia_tambem_nao_grava_a_coluna(valor):
    """O par obrigatório do teste acima, pelo outro caminho.

    `passos_resolucao` nem chega em `dados` — não está em `LOG_COLUMNS`, é
    filtrado antes. Mas `passos_json` **está**, e é assim que o Streamlit
    entrega (`extras={"passos_json": dl.get("passos_resolucao")}`): quando a
    questão não tem passos, chega `None` e a coluna gravaria NULL explícito.
    Dois mutantes sobreviveram por este caso faltar, e eles se protegiam um
    ao outro.
    """
    assert "passos_json" not in preparar(passos_json=valor)


def test_passo_sem_conteudo_e_descartado_mas_os_outros_ficam():
    dados = preparar(passos_resolucao=[
        {"titulo": "vazio", "conteudo": ""},
        {"titulo": "cheio", "conteudo": "x = 5"},
    ])

    assert dados["passos_json"] == [{"titulo": "cheio", "conteudo": "x = 5"}]


# ====================== OS LIMITES ======================


def test_a_resolucao_e_aparada_para_nao_inchar_o_banco():
    """Isto entra em toda resposta de exatas. Doze passos é o dobro do que o
    Laboratório usa, e 600 caracteres cabem uma linha de Bhaskara com folga —
    mas uma resposta da IA fora do padrão não pode encher a tabela.
    """
    dados = preparar(passos_resolucao=[{"conteudo": f"passo {i}"} for i in range(40)])

    assert len(dados["passos_json"]) == 12


def test_passo_gigante_e_truncado():
    dados = preparar(passos_resolucao=[{"conteudo": "x" * 5000, "titulo": "t" * 500}])

    guardado = dados["passos_json"][0]
    assert len(guardado["conteudo"]) == 600
    assert len(guardado["titulo"]) == 80


def test_o_titulo_e_opcional():
    """A IA às vezes manda passo sem título. Guardar `"titulo": ""` só
    ocuparia espaço."""
    dados = preparar(passos_resolucao=[{"conteudo": "x = 5"}])

    assert dados["passos_json"] == [{"conteudo": "x = 5"}]


# ====================== O RESTO DO LOG NÃO MUDA ======================


def test_os_campos_de_sempre_continuam_iguais():
    """A mudança acrescenta uma coluna; não pode mexer no que o painel do
    professor já lê."""
    dados = preparar(passos_resolucao=BHASKARA)

    assert dados["materia"] == "LAB-Matematica"
    assert dados["resultado"] == "Acertou"
    assert dados["pergunta_texto"] == BASE["pergunta_texto"]
    assert dados["modo"]


def test_passos_resolucao_nao_vaza_como_coluna():
    """O nome que a tela usa não é o nome da coluna — se vazasse, o insert
    quebraria com "column does not exist"."""
    assert "passos_resolucao" not in preparar(passos_resolucao=BHASKARA)
