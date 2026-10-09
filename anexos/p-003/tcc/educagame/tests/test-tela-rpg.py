"""A tela do RPG: o que ela desenha em cada estado.

Esta era a maior função do projeto (570 linhas) e ficou parada por muito
tempo com o mesmo motivo escrito no PROXIMOS_PASSOS: tela de Streamlit não
devolve valor, então não dava para fotografar entrada → saída como se fez
com `invocar_enigma`, e extrair sem rede seria apostar.

A saída de uma tela é a **sequência de chamadas que ela faz ao Streamlit**.
`tests/apoio_streamlit.py` troca o Streamlit por um dublê que anota essa
sequência — e com isso vale a mesma receita das outras duas: fotografar
antes, extrair, conferir que a fotografia bate.

O que estes testes prendem é o roteiro de cada estado: quantas telas de
saída, quais avisos, onde a execução para. É o que impede a extração de
mudar o que o aluno vê.
"""

from __future__ import annotations

import importlib
import sys

import pytest

from tests.apoio_streamlit import StreamlitFalso

AVENTURA = {
    "id": "av-1", "titulo": "A Torre", "materia": "Matemática", "serie": "1º Ano EM",
    "cenario": "Uma torre antiga", "heroi_nome": "Aprendiz", "poderes": "Cálculo",
    "objetivo_final": "Chegar ao topo",
}
ALUNO = {"id": "aluno-1", "nome": "Aluno Teste", "ano_escolar": "1o Ano EM"}
CHAVE = "rpg_aluno-1_av-1"

DESAFIO = {
    "pergunta": "Qual o valor de x em 2x = 10?",
    "opcoes": ["5", "10", "2", "20"], "correta": 0,
    "enigma": "O portal guarda um número.",
    "explicacao": [{"tipo": "texto", "conteudo": "Divida os dois lados por 2."}],
    "passos_resolucao": [{"titulo": "1o Passo", "conteudo": "x = 10/2", "final": True}],
    "formula": "2x = 10", "subformulas": [], "legenda_variaveis": "x = incógnita",
}
CENA = {
    "titulo": "Portal da Masmorra", "narrativa": "A equipe atravessa o portal.",
    "opcoes": [
        {"id": "op-1", "texto": "Entrar na torre", "rota": "torre", "risco": "medio",
         "impacto_destino": "conhecimento", "chance_sucesso": 70},
        {"id": "op-2", "texto": "Contornar", "rota": "fora", "risco": "baixo",
         "impacto_destino": "estrategia", "chance_sucesso": 90},
    ],
}


class RepoFalso:
    def __init__(self, alunos=None, progresso=None):
        self._alunos = [ALUNO] if alunos is None else alunos
        self._progresso = progresso

    def buscar_alunos(self, *_a, **_k):
        return list(self._alunos)

    def carregar_progresso_rpg(self, *_a, **_k):
        return self._progresso

    def salvar_progresso_rpg(self, *_a, **_k):
        return True

    def registrar_log(self, *_a, **_k):
        return True


def estado(**extra):
    base = {
        "hp": 100, "xp": 30, "fase": 3, "titulo": "A Torre", "cena_atual": CENA,
        "historico": [{"local": "Portal", "acao": "Entrar", "resultado": "acertou",
                       "rota": "torre", "impacto": "conhecimento",
                       "resultado_tentativa": "sucesso", "chance_sucesso": 70, "rolagem": 55}],
        "temas_usados": ["equação"], "historico_desafios": [],
        "aguardando_desafio": False, "desafio_atual": None, "acao_pendente": None,
        "desafio_respondido": False, "aventura_id": "av-1",
        "jornada": {"conhecimento": 2, "estrategia": 1, "coragem": 0, "cooperacao": 1},
        "ultima_escolha": {"id": "op-1", "texto": "Entrar na torre", "rota": "torre",
                           "impacto_destino": "conhecimento", "chance_sucesso": 70},
        "ultima_checagem_escolha": {"resultado": "sucesso", "rolagem": 55, "chance": 70},
        "desafio_acertou": False,
        "ultimo_resultado_risco": {"risco": "medio", "xp_bonus": 5, "resultado": "sucesso"},
        "recompensa_pendente": None, "ultima_recompensa_item": None,
    }
    base.update(extra)
    return base


def desenhar(*, aventuras=(AVENTURA,), alunos=None, sessao=None, progresso=None) -> list[str]:
    """Roda a tela contra o dublê e devolve o roteiro do que ela desenhou."""
    with StreamlitFalso(sessao=dict(sessao or {})) as fake:
        for modulo in [m for m in list(sys.modules)
                       if m.startswith(("st.ui", "core.design_system"))]:
            sys.modules.pop(modulo, None)
        tela = importlib.import_module("st.ui.tela_rpg_st")
        try:
            tela.renderizar_tela_rpg(
                escola_id="escola-1",
                dados_escola={"id": "escola-1", "nome": "Escola"},
                db_repo=RepoFalso(alunos, progresso),
                report_service=object(),
                rpg_engine=importlib.import_module("services.rpg_service"),
                listar_rpg_configs_fn=lambda _e: list(aventuras),
            )
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:150]}")
    return fake.roteiro()


def sem_erro(roteiro: list[str]) -> bool:
    return not any(l.startswith("!!") for l in roteiro)


# --------------------------------------------------------------------------
# as guardas do começo
# --------------------------------------------------------------------------


def test_sem_aventura_configurada_avisa_e_para():
    # O caso que o diretor encontrou de verdade na Educacional Delta: o RPG
    # só libera depois que o professor cria a aventura.
    roteiro = desenhar(aventuras=[])

    assert any("warning:" in l and "não configurou nenhuma aventura" in l for l in roteiro)
    assert roteiro[-1] == "stop"


def test_sem_aluno_cadastrado_avisa_e_para():
    roteiro = desenhar(alunos=[])

    assert any("info:" in l and "Nenhum aluno cadastrado" in l for l in roteiro)
    assert roteiro[-1] == "stop"


def test_com_aventura_e_aluno_desenha_a_tela():
    roteiro = desenhar(sessao={})

    assert sem_erro(roteiro)
    assert any("selectbox:" in l for l in roteiro), "sumiu a escolha de campanha"
    assert len(roteiro) > 8


# --------------------------------------------------------------------------
# o bloco do desafio — o que foi extraído
# --------------------------------------------------------------------------


def test_desafio_em_curso_desenha_as_alternativas():
    roteiro = desenhar(sessao={CHAVE: estado(aguardando_desafio=True, desafio_atual=DESAFIO)})

    assert sem_erro(roteiro)
    # é o estado mais pesado da tela: muito mais linhas que o normal
    assert len(roteiro) > 40, f"o desafio desenhou pouco: {len(roteiro)} linhas"


@pytest.mark.parametrize("acertou", [True, False])
def test_desafio_respondido_desenha_o_resultado(acertou):
    roteiro = desenhar(sessao={CHAVE: estado(
        aguardando_desafio=True, desafio_atual=DESAFIO,
        desafio_respondido=True, desafio_acertou=acertou,
    )})

    assert sem_erro(roteiro)
    assert len(roteiro) > 25


def _tem_opcoes_da_cena(roteiro: list[str]) -> bool:
    return any("Entrar na torre" in l or "Próxima decisão" in l for l in roteiro)


def test_sem_desafio_a_tela_segue_para_as_opcoes_da_cena():
    # O return da função extraída é o que decide isto: sem desafio em curso,
    # a tela precisa CONTINUAR e desenhar as decisões da cena.
    roteiro = desenhar(sessao={CHAVE: estado()})

    assert sem_erro(roteiro)
    assert _tem_opcoes_da_cena(roteiro), "a tela parou antes das opções da cena"


def test_com_desafio_a_tela_para_e_nao_desenha_as_opcoes():
    # O espelho do teste acima, e a metade que importa: enquanto há desafio
    # em curso, o aluno não pode ver as decisões da cena na mesma tela --
    # ele escolheria a rota antes de responder. Foi exatamente este `return`
    # que a extração transformou em valor de retorno.
    roteiro = desenhar(sessao={CHAVE: estado(aguardando_desafio=True, desafio_atual=DESAFIO)})

    assert sem_erro(roteiro)
    assert not _tem_opcoes_da_cena(roteiro), (
        "a tela desenhou o desafio E as opções da cena: o aluno escolheria a "
        "rota sem ter respondido"
    )


def test_a_funcao_extraida_recusa_estado_sem_desafio():
    # A guarda mora dentro dela: chamada num estado sem desafio, devolve
    # False e não desenha nada.
    with StreamlitFalso() as fake:
        for modulo in [m for m in list(sys.modules) if m.startswith("st.ui")]:
            sys.modules.pop(modulo, None)
        tela = importlib.import_module("st.ui.tela_rpg_st")
        resultado = tela._renderizar_desafio_rpg(
            estado=estado(), cena=CENA, config_rpg=AVENTURA, al_obj=ALUNO,
            escola_id="escola-1", db_repo=RepoFalso(),
            rpg_engine=importlib.import_module("services.rpg_service"), fases_totais=15,
        )

    assert resultado is False
    assert fake.roteiro() == [], "desenhou algo mesmo sem desafio em curso"


# --------------------------------------------------------------------------
# os outros ramos
# --------------------------------------------------------------------------


def test_hp_zerado_encerra_a_aventura():
    roteiro = desenhar(sessao={CHAVE: estado(hp=0)})

    assert sem_erro(roteiro)
    assert len(roteiro) > 8


@pytest.mark.parametrize(
    "rotulo, sessao_extra",
    [
        ("recompensa", {"cena_atual": {**CENA, "recompensa": {"item": "Bússola", "xp": 10}}}),
        ("chefao", {"cena_atual": {**CENA, "evento": "chefao"}}),
    ],
)
def test_ramos_da_cena_desenham_sem_erro(rotulo, sessao_extra):
    roteiro = desenhar(sessao={CHAVE: estado(**sessao_extra)})

    assert sem_erro(roteiro), rotulo


def test_mensagem_de_flash_aparece():
    roteiro = desenhar(sessao={
        CHAVE: estado(),
        f"{CHAVE}_flash": {"tipo": "success", "texto": "Progresso salvo"},
    })

    assert sem_erro(roteiro)
    assert any("Progresso salvo" in l for l in roteiro)


def test_progresso_salvo_e_oferecido():
    roteiro = desenhar(
        sessao={},
        progresso={"estado": estado(fase=7, xp=120), "atualizado_em": "2026-08-01T10:00:00"},
    )

    assert sem_erro(roteiro)
    assert len(roteiro) > 8


# --------------------------------------------------------------------------
# o tamanho, que era o motivo de mexer
# --------------------------------------------------------------------------


def test_a_tela_nao_volta_a_crescer():
    import ast
    import io
    from pathlib import Path

    arquivo = Path(__file__).resolve().parent.parent / "st" / "ui" / "tela_rpg_st.py"
    arvore = ast.parse(io.open(arquivo, encoding="utf-8").read())
    tamanhos = {
        no.name: no.end_lineno - no.lineno + 1
        for no in arvore.body
        if isinstance(no, ast.FunctionDef)
    }

    assert "_renderizar_desafio_rpg" in tamanhos, "o bloco do desafio voltou para dentro da tela"
    assert tamanhos["renderizar_tela_rpg"] < 400, (
        f"renderizar_tela_rpg voltou a crescer: {tamanhos['renderizar_tela_rpg']} linhas"
    )
