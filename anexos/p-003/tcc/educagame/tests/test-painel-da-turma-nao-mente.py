"""Duas coisas que o painel mostrava e não eram verdade.

1. O gráfico dizia que 43 alunos acertaram 0%
------------------------------------------------
No painel da ETEC, 43 dos 45 alunos nunca tinham respondido nada. O gráfico
de desempenho plotava todo mundo, e **"não respondeu" saía desenhado como
"acertou 0%"** -- em vermelho, na escala vermelho→verde, que é a cor de quem
vai mal. Os dois alunos com dado real sumiam no meio das barras zeradas.

A guarda já existia em **três** lugares do mesmo arquivo:

    alerta de baixo desempenho   percentual < 50 and total >= 5
    destaque vermelho na tabela  row["%"] < 50 and row["Total"] >= 5
    gráfico de tempo (ao lado)   df["Tempo Médio (s)"] > 0
    gráfico de desempenho        -- nenhuma --

É o mesmo padrão do `parece_formula_laboratorio`: a guarda entra uma porta por
vez e uma fica para trás. Era também por isso que os dois gráficos lado a lado
mostravam populações diferentes -- 45 à esquerda, 2 à direita.

O Flask não tinha o defeito: lá o gráfico é por aluno e já vinha com
`{% if metricas.total %}`.

2. A tela dizia "ativa" para uma conta que não entra
-----------------------------------------------------
Na tela de contas, `aluno` aparecia com escola "—" e situação **ativa** --
enquanto `conta_pode_entrar` a recusa. A regra do login não olha o papel: quem
não é desenvolvedor e não tem vínculo não entra.

E a tela promete o contrário no próprio texto: *"Conta sem vínculo aparece
marcada, porque ela não entra em lugar nenhum"*. Só cumpria para professor,
porque `PAPEIS_COM_ESCOLA` tinha só `("professor",)`.
"""

from __future__ import annotations

import pandas as pd
import pytest

import services.usuario_service as contas_svc
from services.auth_service import conta_pode_entrar
from services.usuario_service import PAPEIS, PAPEIS_COM_ESCOLA
from st.ui.professor_panel_st import separar_quem_respondeu


def _turma(*totais: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Aluno": f"Aluno {i:02d}", "Total": total, "%": 0 if not total else 80,
             "Tempo Médio (s)": 0.0 if not total else 50.0}
            for i, total in enumerate(totais, 1)
        ]
    )


# ====================== 1. O GRÁFICO ======================


def test_quem_nunca_respondeu_fica_fora_do_grafico():
    """O caso real: 43 de 45 sem nenhuma resposta."""
    df = _turma(*([0] * 43), 80, 1)

    responderam, de_fora = separar_quem_respondeu(df)

    assert len(responderam) == 2
    assert de_fora == 43


def test_a_turma_toda_respondendo_nao_perde_ninguem():
    """A metade que protege: a guarda não pode virar um filtro que esconde
    aluno de verdade."""
    df = _turma(10, 20, 30)

    responderam, de_fora = separar_quem_respondeu(df)

    assert len(responderam) == 3
    assert de_fora == 0


def test_uma_resposta_ja_conta():
    """O corte é "respondeu?", não "respondeu bastante?". Quem tem uma
    questão tem dado, e some do gráfico seria esconder informação."""
    df = _turma(1, 0)

    responderam, de_fora = separar_quem_respondeu(df)

    assert list(responderam["Total"]) == [1]
    assert de_fora == 1


def test_ninguem_respondeu():
    df = _turma(0, 0, 0)

    responderam, de_fora = separar_quem_respondeu(df)

    assert responderam.empty
    assert de_fora == 3


def test_os_dois_graficos_passam_a_usar_a_mesma_populacao():
    """Era o sintoma visível: 45 barras à esquerda e 2 à direita, na mesma
    tela. O de tempo filtra mais (só quem tem tempo medido), mas nunca pode
    filtrar MENOS que o de desempenho."""
    df = _turma(*([0] * 10), 5, 8)

    responderam, _ = separar_quem_respondeu(df)
    com_tempo = responderam[responderam["Tempo Médio (s)"] > 0]

    assert set(com_tempo["Aluno"]) <= set(responderam["Aluno"])
    assert len(responderam) == 2


# ====================== 2. A CONTA QUE NÃO ENTRA ======================


@pytest.mark.parametrize("papel", ["professor", "aluno"])
def test_conta_sem_escola_e_marcada(papel, monkeypatch):
    monkeypatch.setattr(
        contas_svc, "listar_usuarios",
        lambda: [{"id": "1", "username": "x", "role": papel, "ativo": True, "escola_id": None}],
    )
    monkeypatch.setattr(contas_svc, "listar_escolas", lambda: [])

    conta = contas_svc.listar_contas()[0]

    assert conta["sem_vinculo"] is True, f"conta de {papel} sem escola não é marcada"


def test_desenvolvedor_sem_escola_nao_e_marcado(monkeypatch):
    """Ele é global de propósito -- `conta_pode_entrar` devolve True para ele
    sem sequer olhar escola. Marcá-lo seria alarme falso, e alarme falso é o
    que faz a marcação deixar de ser lida."""
    monkeypatch.setattr(
        contas_svc, "listar_usuarios",
        lambda: [{"id": "1", "username": "dev", "role": "desenvolvedor", "ativo": True, "escola_id": None}],
    )
    monkeypatch.setattr(contas_svc, "listar_escolas", lambda: [])

    assert contas_svc.listar_contas()[0]["sem_vinculo"] is False


@pytest.mark.parametrize("papel", PAPEIS)
def test_a_marcacao_bate_com_quem_o_LOGIN_recusa(papel):
    """O teste que impede a próxima divergência.

    `PAPEIS_COM_ESCOLA` decide o que a TELA marca; `conta_pode_entrar` decide
    quem o LOGIN aceita. Eram duas listas com a mesma pergunta, e foi por isso
    que "aluno" ficou de fora de uma delas por tanto tempo.

    Aqui a tela é conferida contra a regra de verdade, papel por papel."""
    conta = {"role": papel, "escola_id": None}
    pode_entrar, _ = conta_pode_entrar(conta, "escola-qualquer")

    marcado = papel in PAPEIS_COM_ESCOLA

    assert marcado == (not pode_entrar), (
        f"'{papel}' sem escola: o login {'recusa' if not pode_entrar else 'aceita'}, "
        f"mas a tela {'marca' if marcado else 'NÃO marca'}"
    )


def test_criar_conta_de_aluno_sem_escola_e_recusado(monkeypatch):
    """Recusar na criação, com o motivo na tela, é melhor do que criar e a
    pessoa descobrir no login -- que é onde não há mensagem para ela."""
    monkeypatch.setattr(contas_svc, "listar_escolas", lambda: [{"id": "esc-1", "nome": "ETEC"}])
    monkeypatch.setattr(contas_svc, "buscar_usuario_por_username", lambda _u: None)

    ok, erro, _senha = contas_svc.criar_conta("novoaluno", "aluno", escola_id="")

    assert not ok
    assert "escola" in erro.lower(), erro


def test_criar_conta_de_aluno_COM_escola_passa(monkeypatch):
    """O par: apertar a regra não pode impedir o caminho legítimo."""
    monkeypatch.setattr(contas_svc, "listar_escolas", lambda: [{"id": "esc-1", "nome": "ETEC"}])
    monkeypatch.setattr(contas_svc, "buscar_usuario_por_username", lambda _u: None)
    monkeypatch.setattr(
        contas_svc, "criar_usuario",
        lambda *a, **k: type("R", (), {"data": [{"id": "1"}]})(),
    )

    ok, erro, senha = contas_svc.criar_conta("novoaluno", "aluno", escola_id="esc-1")

    assert ok, erro
    assert senha


# ====================== O AVISO NA TELA ======================
#
# MELHORIA: estes dois nasceram de um mutante sobrevivente. Apagar o
# `if sem_resposta:` não quebrava nada, porque o aviso mora DENTRO do render e
# nenhum teste desenhava a tela. Sem ele o gráfico passa a esconder alunos em
# silêncio -- que é pior que o defeito original, porque some sem dizer.


def _rodar_resumo(resumo_turma: list[dict], respostas: dict | None = None) -> dict:
    """Roda a aba de resumo na bancada.

    Devolve três coisas, porque as três já esconderam defeito: o roteiro (o
    que a tela mandou desenhar), a FORMA de cada gráfico (deitado ou em pé,
    que altura, que eixos) e o que foi entregue ao gerador do PDF.

    Sem a forma do gráfico, virar a barra em pé -- que é o defeito de
    legibilidade que a barra deitada conserta -- passa por todos os testes.
    """
    import importlib
    import sys as _sys

    from tests.apoio_streamlit import StreamlitFalso

    import st.ui.professor_panel_st  # noqa: F401  (prende a cadeia ao runtime real)

    figuras: list[dict] = []
    pdf: dict = {}

    with StreamlitFalso(sessao={}, respostas=respostas or {}) as fake:
        _sys.modules.pop("st.ui.professor_panel_st", None)
        painel = importlib.import_module("st.ui.professor_panel_st")
        painel.db.buscar_resumo_turma = lambda _e: resumo_turma

        def _gravar_figura(fig, *_a, **_k):
            traco = fig.data[0] if fig.data else None
            figuras.append({
                "titulo": str(fig.layout.title.text or ""),
                "altura": fig.layout.height,
                "orientacao": getattr(traco, "orientation", None) if traco else None,
                "eixo_y": [str(v) for v in (traco.y if traco is not None and traco.y is not None else [])],
            })
            fake._anotar(f"plotly_chart: {fig.layout.title.text or 'sem titulo'}")

        def _gravar_pdf(**kwargs):
            pdf.update(kwargs)
            return b"%PDF-falso"

        fake.plotly_chart = _gravar_figura
        painel.report.gerar_pdf_relatorio_turma = _gravar_pdf

        try:
            painel._renderizar_aba_resumo_turma("escola-1", {"nome": "ETEC"})
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:120]}")

    return {"roteiro": fake.roteiro(), "figuras": figuras, "pdf": pdf}


def _desenhar_resumo(resumo_turma: list[dict]) -> list[str]:
    """O que a aba mandou desenhar, em linhas de texto."""
    return _rodar_resumo(resumo_turma)["roteiro"]


def _aluno(nome: str, total: int) -> dict:
    return {
        "nome": nome, "ano_escolar": "1º EM", "periodo": "Manhã",
        "total_questoes": total, "acertos": total, "erros": 0,
        "percentual": 100 if total else 0,
        "tempo_medio_resposta": 50.0 if total else 0,
        "baixo_desempenho": False,
    }


def test_a_tela_diz_quantos_ficaram_de_fora_do_grafico():
    """Sem isto o professor vê 2 barras e uma turma de 45, e não sabe se o
    gráfico está quebrado ou se os outros 43 não jogaram."""
    roteiro = _desenhar_resumo([_aluno(f"Aluno {i}", 0) for i in range(43)] + [_aluno("Lucas", 80)])

    texto = " ".join(roteiro)

    assert "43 aluno(s) fora do gráfico" in texto, texto[-600:]
    assert "tabela acima" in texto, "não diz onde encontrá-los"


def test_com_a_turma_toda_respondendo_nao_ha_aviso():
    """O par: avisar sempre é o mesmo que não avisar."""
    roteiro = _desenhar_resumo([_aluno("Lucas", 80), _aluno("Ronnie", 1)])

    assert "fora do gráfico" not in " ".join(roteiro)


# ====================== 3. A ESCALA ======================
#
# Barra horizontal resolveu a legibilidade e PIOROU a escala: com 100 alunos
# seriam 26 × 100 = 2.600px de altura. Trocar um problema por outro não é
# consertar. O ponto de fundo é que cem barras não respondem pergunta nenhuma
# que o professor faça -- então o gráfico passa a depender do tamanho da turma.


def test_o_corte_de_tamanho_e_razoavel_para_uma_turma():
    from st.ui.professor_panel_st import MAX_ALUNOS_NO_GRAFICO

    assert 10 <= MAX_ALUNOS_NO_GRAFICO <= 30, (
        f"corte em {MAX_ALUNOS_NO_GRAFICO}: baixo demais troca o gráfico numa turma "
        "normal; alto demais devolve a parede de barras"
    )


def test_turma_pequena_mostra_aluno_por_aluno():
    """Com poucos alunos, a barra por aluno cabe e é o mais informativo.

    Medido pelo que a tela DESENHA: uma turma pequena produz dois gráficos e
    nenhum aviso de troca."""
    roteiro = _desenhar_resumo([_aluno(f"Aluno {i}", 10) for i in range(5)])
    texto = " ".join(roteiro)

    assert "parede de barras" not in texto, "trocou o gráfico numa turma de 5"


def test_turma_grande_troca_de_grafico():
    """100 alunos: distribuição + quem precisa de atenção, os dois de tamanho
    constante. E a tela diz que trocou -- esconder sem avisar é pior que a
    parede de barras."""
    roteiro = _desenhar_resumo([_aluno(f"Aluno {i}", 10) for i in range(100)])
    texto = " ".join(roteiro)

    assert "parede de barras" in texto, "a turma de 100 continua com uma barra por aluno"
    assert "tabela acima" in texto, "não diz onde ver todos"


def test_as_faixas_cobrem_todos_os_alunos():
    """Nenhum aluno pode cair fora das faixas -- 100% é aproveitamento válido
    e ficaria de fora de um `< 100`."""
    from st.ui.professor_panel_st import faixas_de_aproveitamento

    df = pd.DataFrame([{"%": p} for p in (0, 24, 25, 49, 50, 74, 75, 99, 100)])

    faixas = faixas_de_aproveitamento(df)

    assert sum(quantos for _, quantos in faixas) == len(df), faixas
    assert dict(faixas)["75–100%"] == 3, "o aluno de 100% caiu fora"


def test_as_faixas_separam_quem_vai_mal_de_quem_vai_bem():
    from st.ui.professor_panel_st import faixas_de_aproveitamento

    df = pd.DataFrame([{"%": p} for p in (10, 20, 90, 95)])

    assert dict(faixas_de_aproveitamento(df)) == {
        "0–25%": 2, "25–50%": 0, "50–75%": 0, "75–100%": 2,
    }


def test_precisam_de_atencao_traz_os_piores_e_limita():
    from st.ui.professor_panel_st import precisam_de_atencao

    df = pd.DataFrame([{"Aluno": f"A{i}", "%": i} for i in range(100)])

    piores = precisam_de_atencao(df, limite=10)

    assert len(piores) == 10
    assert list(piores["%"]) == list(range(10)), "não são os de menor aproveitamento"


def test_precisam_de_atencao_nao_inventa_alunos():
    """Turma menor que o limite: devolve quem existe, não repete nem completa."""
    from st.ui.professor_panel_st import precisam_de_atencao

    df = pd.DataFrame([{"Aluno": "A", "%": 30}, {"Aluno": "B", "%": 40}])

    assert len(precisam_de_atencao(df, limite=10)) == 2


# ====================== 4. O QUE A REFATORAÇÃO PÔS À MOSTRA ======================
#
# `_renderizar_aba_resumo_turma` tinha 169 linhas e fazia tudo: filtro, contas,
# alerta, tabela, dois modos de gráfico e o PDF. Nada disso dava para conferir
# sem desenhar a tela inteira, e por isso nada disso tinha teste -- só o
# gráfico tinha, porque foi onde apareceu um defeito.
#
# Separar filtro, contas e tabela do desenho não muda o que a tela mostra
# (conferido tela a tela, em treze cenários). Muda o que dá para conferir.


def test_o_filtro_de_serie_e_de_periodo_valem_juntos():
    """São dois selects independentes na tela; quem passa tem de casar nos
    dois. Era uma expressão de uma linha só dentro do render."""
    from st.ui.professor_panel_st import filtrar_turma

    turma = [
        {"nome": "A", "ano_escolar": "1º EM", "periodo": "Manhã"},
        {"nome": "B", "ano_escolar": "1º EM", "periodo": "Tarde"},
        {"nome": "C", "ano_escolar": "2º EM", "periodo": "Manhã"},
    ]

    escolhidos = filtrar_turma(turma, "1º EM", "Manhã")

    assert [a["nome"] for a in escolhidos] == ["A"]


def test_todas_e_todos_querem_dizer_nao_filtrar():
    """O par que protege: se "Todas" virasse um valor comparado de verdade, a
    aba abriria vazia -- que é o estado em que o professor a encontra."""
    from st.ui.professor_panel_st import filtrar_turma

    turma = [
        {"nome": "A", "ano_escolar": "1º EM", "periodo": "Manhã"},
        {"nome": "B", "ano_escolar": "3º EM", "periodo": "Noite"},
    ]

    assert len(filtrar_turma(turma, "Todas", "Todos")) == 2
    assert len(filtrar_turma(turma, "Todas", "Noite")) == 1
    assert len(filtrar_turma(turma, "3º EM", "Todos")) == 1


def test_a_media_da_turma_e_por_questao_e_nao_media_de_percentuais():
    """A diferença aparece quando um aluno respondeu muito e outro quase nada.

    Um acertou a única questão que fez; o outro errou 99. Média por questão:
    1%. Média dos percentuais: 50%. A segunda diria que a turma vai bem.
    """
    from st.ui.professor_panel_st import metricas_da_turma

    turma = [
        {"total_questoes": 1, "acertos": 1, "tempo_medio_resposta": 10},
        {"total_questoes": 99, "acertos": 0, "tempo_medio_resposta": 10},
    ]

    assert metricas_da_turma(turma)["media_turma"] == 1


def test_turma_sem_nenhuma_questao_nao_divide_por_zero():
    """A aba abre assim no primeiro dia de uso, com os alunos matriculados e
    ninguém tendo jogado."""
    from st.ui.professor_panel_st import metricas_da_turma

    metricas = metricas_da_turma([{"total_questoes": 0, "acertos": 0}] * 3)

    assert metricas["media_turma"] == 0
    assert metricas["tempo_medio_turma"] == 0
    assert metricas["total_alunos"] == 3


def test_o_tempo_medio_ignora_quem_nao_tem_tempo_medido():
    """Mesmo defeito do gráfico, em forma de número: contar o zero de quem
    nunca respondeu como "respondeu em 0s" derrubaria a média da turma."""
    from st.ui.professor_panel_st import metricas_da_turma

    turma = [
        {"total_questoes": 10, "acertos": 5, "tempo_medio_resposta": 40.0},
        {"total_questoes": 10, "acertos": 5, "tempo_medio_resposta": 60.0},
        {"total_questoes": 0, "acertos": 0, "tempo_medio_resposta": 0},
    ]

    assert metricas_da_turma(turma)["tempo_medio_turma"] == 50.0


def test_tempo_que_veio_torto_do_banco_nao_derruba_a_aba():
    """A coluna vem de uma view; já apareceu texto e nulo. Somar isso seria
    TypeError e a aba inteira sumia."""
    from st.ui.professor_panel_st import metricas_da_turma

    turma = [
        {"total_questoes": 10, "acertos": 5, "tempo_medio_resposta": None},
        {"total_questoes": 10, "acertos": 5, "tempo_medio_resposta": "40"},
        {"total_questoes": 10, "acertos": 5, "tempo_medio_resposta": 30.0},
    ]

    assert metricas_da_turma(turma)["tempo_medio_turma"] == 30.0


def test_coluna_que_a_view_nao_trouxe_vira_zero_em_vez_de_derrubar_a_aba():
    """`buscar_resumo_turma` já voltou sem `periodo` quando a coluna era nova
    no banco. Uma coluna vazia é melhor que a aba inteira num KeyError."""
    from st.ui.professor_panel_st import tabela_por_aluno

    df = tabela_por_aluno([{"nome": "Ana", "total_questoes": 4, "acertos": 4}])

    assert list(df["Aluno"]) == ["Ana"]
    assert list(df["Período"]) == [0]


def test_a_tabela_entrega_os_nomes_de_coluna_que_os_graficos_usam():
    """O teste que impede a próxima quebra silenciosa.

    Os gráficos leem `df["Aluno"]`, `df["%"]`, `df["Total"]` e
    `df["Tempo Médio (s)"]` -- nomes que nascem aqui, ao renomear as colunas
    da view. Renomear um rótulo para a tela ficar bonita apagaria o gráfico
    sem erro nenhum: `separar_quem_respondeu` devolveria vazio.
    """
    from st.ui.professor_panel_st import separar_quem_respondeu, tabela_por_aluno

    df = tabela_por_aluno([_aluno("Ana", 10)])

    for coluna in ("Aluno", "Total", "%", "Tempo Médio (s)"):
        assert coluna in df.columns, f"os gráficos leem '{coluna}' e ela sumiu"

    responderam, de_fora = separar_quem_respondeu(df)
    assert len(responderam) == 1 and de_fora == 0


# ====================== 5. O QUE SOBREVIVEU À MUTAÇÃO ======================
#
# Estragado o código de propósito, uma mudança por vez, sete mutantes passaram
# por todos os testes acima. Estes são os que representam defeito de verdade.
#
# (O oitavo -- trocar a ordem das colunas da tabela -- ficou sem teste de
# propósito: mudar "Aluno, Série" para "Série, Aluno" não quebra nada, e
# prender a ordem seria prender uma escolha de gosto.)


def test_o_grafico_por_aluno_e_deitado():
    """Em pé, os nomes saem rotacionados e ilegíveis -- é a razão de o
    gráfico ser deitado, e nenhum teste sustentava isso: virar a barra passava
    por toda a bateria."""
    resultado = _rodar_resumo([_aluno(f"Aluno {i}", 10) for i in range(4)])

    desempenho = resultado["figuras"][0]

    assert desempenho["orientacao"] == "h", "a barra ficou em pé; os nomes viram texto rotacionado"
    assert any("Aluno" in nome for nome in desempenho["eixo_y"]), (
        "o eixo vertical deixou de ser o nome do aluno"
    )


def test_a_altura_do_grafico_cresce_com_a_turma_mas_tem_piso():
    """Com `min` no lugar de `max`, uma turma de dois renderiza um gráfico de
    52px -- uma tira, na prática invisível."""
    from st.ui.professor_panel_st import ALTURA_MINIMA_DO_GRAFICO, _altura_por_aluno

    assert _altura_por_aluno(2) == ALTURA_MINIMA_DO_GRAFICO, "turma pequena virou uma tira"
    assert _altura_por_aluno(15) > ALTURA_MINIMA_DO_GRAFICO, "a altura parou de crescer"
    assert _altura_por_aluno(15) > _altura_por_aluno(10)


def test_o_corte_vale_no_limite_exato():
    """O `<=` e o `<` só se distinguem numa turma de exatamente
    MAX_ALUNOS_NO_GRAFICO -- e é sempre no limite que estes erros moram.

    O combinado é que o corte é "acima disto troca", então 15 ainda mostra
    aluno por aluno e 16 troca."""
    from st.ui.professor_panel_st import MAX_ALUNOS_NO_GRAFICO as limite

    no_limite = " ".join(_desenhar_resumo([_aluno(f"Aluno {i}", 10) for i in range(limite)]))
    um_a_mais = " ".join(_desenhar_resumo([_aluno(f"Aluno {i}", 10) for i in range(limite + 1)]))

    assert "parede de barras" not in no_limite, f"turma de {limite} já trocou de gráfico"
    assert "parede de barras" in um_a_mais, f"turma de {limite + 1} não trocou"


def test_turma_sem_tempo_medido_recebe_aviso_e_nao_um_grafico_vazio():
    """Sem a guarda, o segundo gráfico sai desenhado sem nenhuma barra --
    e um gráfico vazio parece defeito, não parece ausência de dado."""
    sem_tempo = [dict(_aluno(f"Aluno {i}", 10), tempo_medio_resposta=0) for i in range(3)]

    resultado = _rodar_resumo(sem_tempo)

    assert "Nenhum dado de tempo de resposta disponível" in " ".join(resultado["roteiro"])
    assert len(resultado["figuras"]) == 1, "desenhou o gráfico de tempo sem ter tempo"


def test_o_alerta_nomeia_os_alunos_com_baixo_desempenho():
    """É a parte acionável da aba: o professor sai dela sabendo com quem
    falar. Apagar a lista inteira não quebrava nenhum teste."""
    turma = [
        dict(_aluno("Ana", 10), percentual=20, acertos=2, baixo_desempenho=True),
        dict(_aluno("Bia", 10), percentual=90, acertos=9, baixo_desempenho=False),
    ]

    texto = " ".join(_desenhar_resumo(turma))

    assert "1 alunos com baixo desempenho" in texto
    assert "Ana" in texto, "o alerta não diz de quem está falando"
    assert "20% de acerto" in texto


def test_o_pdf_leva_a_turma_que_esta_na_tela_e_nao_a_escola_inteira():
    """O professor filtra por série, clica em baixar, e o PDF tem de ser
    daquela série. Nenhum teste chegava a clicar no botão -- a bancada
    responde `False` por padrão --, então o que ia para o relatório nunca foi
    conferido."""
    turma = [
        dict(_aluno("Ana", 10), ano_escolar="1º EM"),
        dict(_aluno("Bia", 10), ano_escolar="2º EM"),
    ]

    resultado = _rodar_resumo(
        turma,
        respostas={
            "🎓 Filtrar por Série:": "1º EM",
            "📥 Baixar Relatório da Turma (PDF)": True,
        },
    )

    nomes = [a["nome"] for a in resultado["pdf"]["dados_turma"]]
    assert nomes == ["Ana"], f"o PDF saiu com {nomes}"
    assert resultado["pdf"]["total_questoes"] == 10, "os números do PDF ignoram o filtro"
