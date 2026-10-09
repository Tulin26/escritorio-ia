"""Todo tema que o Laboratório promete tem questão no banco offline.

MELHORIA: `ALIASES_TEMAS_LAB` anunciava **trigonometria** (com os apelidos
seno, cosseno e tangente) e **proporção**, e nenhum gerador produzia questão
com esses temas. Quem pedia trigonometria recebia estatística, taxas e índices
ou probabilidade condicional — o tema existia no mapa e não existia no banco.

O sintoma que revelou isso foi outro e mais discreto: o cartão *"onde usamos
trigonometria no dia a dia"* nunca aparecia. Ele estava escrito, e nenhuma
questão offline chegava perto dele.

Um mapa de temas que promete mais do que o banco entrega é uma falha muda: a
tela abre, a questão vem, e só quem conferir o assunto percebe que não é o
pedido. Este arquivo transforma isso em vermelho.
"""

from __future__ import annotations

import pytest

from services.banks.laboratorio import (
    ALIASES_TEMAS_LAB,
    gerar_desafio_laboratorio_offline,
    listar_questoes_laboratorio,
)

MATERIAS = ("Matematica", "Fisica", "Quimica")


def temas_do_banco(materia: str) -> set[str]:
    return {q["tema_usado"] for q in listar_questoes_laboratorio(materia)}


# ====================== A PROMESSA E A ENTREGA ======================


@pytest.mark.parametrize("materia", MATERIAS)
def test_todo_tema_prometido_no_mapa_existe_no_banco(materia):
    """O teste que faltava. Trigonometria e proporção estavam prometidas há
    tempo e nunca existiram."""
    prometidos = set(ALIASES_TEMAS_LAB[materia])
    entregues = temas_do_banco(materia)

    faltando = sorted(prometidos - entregues)

    assert not faltando, f"{materia} promete tema sem questão: {faltando}"


@pytest.mark.parametrize("materia", MATERIAS)
def test_todo_tema_volta_quando_pedido_pelo_proprio_nome(materia):
    """A outra direção: questão que existe e ninguém consegue pedir.

    MELHORIA: sete dos 42 temas não voltavam, porque o seletor juntava TODAS as
    questões compatíveis e sorteava entre elas. Pedir *energia cinética* podia
    devolver *trabalho mecânico*, que casa por ter "energia" entre os apelidos.

    Agora o seletor fica só com o casamento mais direto: nome exato vence
    contenção, que vence apelido. O nome de um tema passa a ganhar do apelido
    de outro.
    """
    for tema in sorted(temas_do_banco(materia)):
        recebido = gerar_desafio_laboratorio_offline(materia, tema, "Medio")["tema_usado"]

        assert recebido == tema, f"pedi {tema!r} em {materia} e veio {recebido!r}"


def test_o_apelido_curto_nao_casa_dentro_de_outra_palavra():
    """`"pa"` é apelido de progressão aritmética e casa dentro de "esPAcial".

    Era a forma velha conhecida deste projeto -- marcador curto procurado como
    pedaço de texto. A tabela de cartões já tinha aprendido (lá o marcador é
    `" pa "`, com espaços); o mapa de temas ainda não.
    """
    for _ in range(20):
        assert gerar_desafio_laboratorio_offline("Matematica", "pa", "Medio")["tema_usado"] == (
            "progressao aritmetica"
        )
        assert gerar_desafio_laboratorio_offline("Matematica", "geometria espacial", "Medio")[
            "tema_usado"
        ] == "geometria espacial"


@pytest.mark.parametrize("materia", MATERIAS)
def test_todo_apelido_alcanca_algum_tema_que_o_declara(materia):
    """Estreitar o roteamento não pode ter deixado apelido sem destino.

    O que se cobra é alcance, não exclusividade: um apelido pode trazer mais de
    um tema junto e isso é largura legítima -- "quantidade de movimento" traz
    energia cinética *e* velocidade média, que declara "movimento". O que não
    pode é o tema que declarou o apelido ficar de fora.

    A precisão fica com o teste do round-trip acima, que é o exigente.
    """
    donos: dict[str, set[str]] = {}
    for canonico, termos in ALIASES_TEMAS_LAB[materia].items():
        for apelido in termos:
            donos.setdefault(apelido, set()).add(canonico)

    for apelido, canonicos in donos.items():
        recebidos = {
            gerar_desafio_laboratorio_offline(materia, apelido, "Medio")["tema_usado"]
            for _ in range(6)
        }

        # A exceção deliberada: quando existe um tema cujo NOME contém a busca,
        # ele vence o dono do apelido. "juros" é apelido de porcentagem, mas
        # existe um tema chamado "juros simples"; "movimento" é apelido de
        # velocidade média, e existe "movimento uniformemente variado". Nos
        # dois casos o nome é a resposta melhor.
        pelo_nome = all(apelido in recebido for recebido in recebidos)

        assert canonicos & recebidos or pelo_nome, (
            f"{materia}: {apelido!r} não alcança nenhum de {sorted(canonicos)} — veio {sorted(recebidos)}"
        )


def test_o_apelido_nao_casa_no_meio_de_outra_palavra():
    """`"dinamica"` é apelido da segunda lei de Newton e casava dentro de
    "termoDINAMICA": pedir termodinâmica devolvia questão de força.

    Mesma família do `"pa"` dentro de "espacial", do outro lado da comparação
    — ali o nome do tema continha o apelido; aqui é a busca que o contém.
    """
    recebidos = {
        gerar_desafio_laboratorio_offline("Fisica", "termodinamica", "Medio")["tema_usado"]
        for _ in range(20)
    }

    assert recebidos == {"calorimetria"}

    # "parabola" contém "pa"; só os dois temas de 2º grau podem responder.
    de_parabola = {
        gerar_desafio_laboratorio_offline("Matematica", "parabola", "Medio")["tema_usado"]
        for _ in range(20)
    }

    assert de_parabola <= {"equacao do 2o grau", "funcao do 2o grau"}


@pytest.mark.parametrize(
    "apelido, esperado",
    [
        ("trigonometria", "trigonometria"),
        ("seno", "trigonometria"),
        ("cosseno", "trigonometria"),
        ("tangente", "trigonometria"),
        ("proporcao", "proporcao"),
        ("razao", "proporcao"),
        ("grandezas diretamente", "proporcao"),
    ],
)
def test_os_apelidos_dos_temas_novos_levam_ao_tema_certo(apelido, esperado):
    # O apelido é o que o professor digita; ele já estava no mapa.
    assert gerar_desafio_laboratorio_offline("Matematica", apelido, "Medio")["tema_usado"] == esperado


# ====================== AS QUESTÕES NOVAS ======================


def _questoes_de(tema: str) -> list[dict]:
    return [q for q in listar_questoes_laboratorio("Matematica") if q["tema_usado"] == tema]


@pytest.mark.parametrize("tema", ["trigonometria", "proporcao"])
def test_o_tema_novo_rende_o_mesmo_tanto_que_os_outros(tema):
    questoes = _questoes_de(tema)

    assert len(questoes) == 20
    assert len({q["pergunta"] for q in questoes}) == 20, "questão repetida no mesmo tema"


@pytest.mark.parametrize("tema", ["trigonometria", "proporcao"])
def test_a_alternativa_correta_esta_entre_as_opcoes_e_nenhuma_se_repete(tema):
    for q in _questoes_de(tema):
        assert 0 <= q["correta"] < len(q["opcoes"])
        assert len(set(q["opcoes"])) == len(q["opcoes"]), q["pergunta"]


def test_a_altura_da_rampa_e_mesmo_o_comprimento_vezes_o_seno():
    """A resposta tem de ser a conta, não um dos números do enunciado.

    Sem isto, devolver o próprio comprimento passaria: ele também é inteiro e
    também termina em " m". Foi o defeito que a mutação plantou e a primeira
    versão deste arquivo não pegou.
    """
    import re

    for q in _questoes_de("trigonometria"):
        comprimento = int(re.search(r"tem (\d+) m de comprimento", q["pergunta"]).group(1))
        altura = int(q["opcoes"][q["correta"]].removesuffix(" m"))

        assert altura * 2 == comprimento, q["pergunta"]
        assert altura != comprimento


def test_a_conta_da_rampa_fecha_em_numero_redondo():
    """30 graus de propósito: sen(30) = 0,5 exato.

    Com um ângulo de seno irracional a resposta viraria decimal longo e as
    alternativas passariam a se distinguir por casas decimais — o aluno estaria
    comparando dígitos, não entendendo trigonometria. Por isso o comprimento é
    sempre par: metade dele é inteiro.
    """
    for q in _questoes_de("trigonometria"):
        correta = q["opcoes"][q["correta"]]

        assert correta.endswith(" m")
        assert "," not in correta and "." not in correta, correta


def test_a_rampa_mostra_a_conta_feita_e_nao_so_a_formula():
    # O critério do Laboratório: a conta tem de aparecer efetuada.
    from services.ia.validacao import _resolucao_efetua_alguma_conta

    for q in _questoes_de("trigonometria"):
        passos = [p["conteudo"] for p in q["passos_resolucao"]]

        assert _resolucao_efetua_alguma_conta(passos), passos


def test_a_regra_de_tres_da_proporcao_confere():
    for q in _questoes_de("proporcao"):
        # "3 xicaras rendem 12 paes; quantos paes rendem N xicaras?"
        numeros = [int(n) for n in __import__("re").findall(r"\d+", q["pergunta"])]
        medida, rende, pedido = numeros[0], numeros[1], numeros[2]

        assert int(q["opcoes"][q["correta"]]) == pedido * rende // medida


# ====================== O ELO COM O CARTÃO ======================


def test_a_questao_de_trigonometria_alcanca_o_cartao_de_trigonometria():
    """O cartão existia e era inalcançável -- foi por ele que a falta apareceu.

    Prende as duas pontas: não basta a questão existir, o texto dela precisa
    carregar sinal suficiente para vencer a regra de área, que casa "altura".
    """
    from st.ui.mode_common_st import _usos_dia_a_dia_laboratorio

    desafio = gerar_desafio_laboratorio_offline("Matematica", "trigonometria", "Medio")
    titulo, _ = _usos_dia_a_dia_laboratorio(desafio, "Matematica")

    assert titulo == "Onde usamos trigonometria no dia a dia"


def test_todo_cartao_do_laboratorio_e_alcancado_por_alguma_questao_offline():
    """Cartão inalcançável é texto escrito que nenhum aluno vê.

    Doze regras mais o genérico. Antes de trigonometria entrar no banco eram
    12 de 13 -- e ninguém sabia, porque nada media.
    """
    from st.ui.mode_common_st import (
        USOS_DIA_A_DIA_LABORATORIO,
        USOS_PADRAO_LABORATORIO,
        _usos_dia_a_dia_laboratorio,
    )

    alcancados = set()
    for materia in MATERIAS:
        for q in listar_questoes_laboratorio(materia):
            alcancados.add(_usos_dia_a_dia_laboratorio(q, materia)[0])

    todos = {t for _, t, _ in USOS_DIA_A_DIA_LABORATORIO} | {USOS_PADRAO_LABORATORIO[0]}

    assert todos - alcancados == set(), f"cartão sem questão: {sorted(todos - alcancados)}"


# ====================== A REGRESSÃO DO 20 FIXO ======================


@pytest.mark.parametrize("materia", MATERIAS)
def test_nenhuma_pergunta_se_repete_no_banco(materia):
    """MELHORIA: 16 das 440 de Matemática eram a mesma pergunta.

    Todas de `funcao logaritmica`, que fixava a base em 2 e variava o expoente
    em `3 + (k % 4)` -- quatro perguntas para vinte valores de k. Cinco bases
    vezes quatro expoentes dão exatamente 20 pares, um por k.

    Repetição no banco não quebra nada: só faz o aluno reencontrar a mesma
    questão no lugar de uma nova, que é o que o banco existe para evitar.
    """
    questoes = listar_questoes_laboratorio(materia)
    perguntas = [q["pergunta"] for q in questoes]

    repetidas = {p for p in perguntas if perguntas.count(p) > 1}

    assert not repetidas, f"{materia}: {len(repetidas)} perguntas repetidas"


def test_o_logaritmo_varia_a_base_e_o_expoente():
    questoes = [
        q for q in listar_questoes_laboratorio("Matematica")
        if q["tema_usado"] == "funcao logaritmica"
    ]

    import re

    pares = {
        tuple(re.search(r"log base (\d+) de (\d+)", q["pergunta"]).groups())
        for q in questoes
    }

    assert len(pares) == 20, "os vinte k têm que dar vinte logaritmos diferentes"
    assert len({base for base, _ in pares}) == 5, "a base ficou fixa"


def test_as_equacoes_do_2o_grau_nao_se_repetem():
    """`casos[(indice // 20) % len(casos)]` tinha um 20 fixo duplicando a
    quantidade de templates -- número que a função já recebia em `k`.

    Enquanto os dois valores coincidiram ninguém notou. Ao acrescentar
    trigonometria e proporção (20 → 22 templates) as duas contas divergiram e
    duas equações passaram a se repetir na mesma rodada de dez.
    """
    questoes = _questoes_de("equacao do 2o grau")

    assert len(questoes) == 20
    assert len({q["pergunta"] for q in questoes}) == 20
