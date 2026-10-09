"""As seções de escola do painel do desenvolvedor — cadastrar, editar, excluir.

MELHORIA: `tela_administrador` tinha 233 linhas com cinco assuntos empilhados,
e **nenhum teste tocava as três seções de escola**. Ficaram para trás pelo
motivo de sempre: tela de Streamlit não devolve valor, então não havia como
fotografar entrada → saída. A bancada (`tests/apoio_streamlit.py`) resolveu
isso, e as seções viraram funções de módulo.

A que mais precisava de rede é a de excluir. Ela chama `excluir_escola`, e o
`ON DELETE CASCADE` leva junto os alunos, os logs, o progresso de RPG **e a
conta de professor da unidade**. São duas confirmações digitadas à mão
separando um clique disso, e nada cobrava que as duas funcionassem.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# Fora do dublê, de propósito: a tela puxa services/repositories, e
# repositories/aluno_repo.py resolve `runtime = get_runtime()` no import.
import st.ui.admin_st  # noqa: E402,F401

from tests.apoio_streamlit import StreamlitFalso  # noqa: E402

MODULOS_DA_TELA = ("st.ui.admin_st",)

ETEC = {
    "id": "1", "nome": "ETEC", "slug": "etecata", "cor_tema": "#003366",
    "mostrar_ranking": True, "modo_guilda": True,
}
DELTA = {
    "id": "2", "nome": "Educacional Delta", "slug": "deltaata", "cor_tema": "#AA0000",
    "mostrar_ranking": False, "modo_guilda": True,
}


class _Chamadas(list):
    """Anota o que a seção pediu ao banco -- e devolve o que ela espera.

    As gravações devolvem (resultado, motivo); aqui, sempre a que gravou. As
    que falham estão em tests/test_gravacao_diz_quando_nao_grava.py.
    """

    def registrar(self, nome):
        def espiao(*args, **kwargs):
            self.append((nome, args, kwargs))
            return {"ok": True}, ""
        return espiao


def _rodar(secao: str, *args, respostas=None, escolas=None, falha_ao_listar=False, sessao=None):
    chamadas = _Chamadas()
    # Seção que termina em st.rerun() não chega ao fim do bloco: o ParouAqui
    # (BaseException, como o RerunException de verdade) sobe até o __exit__.
    # Por isso o valor nasce aqui fora.
    devolvido = None
    with StreamlitFalso(respostas=dict(respostas or {}), sessao=sessao) as fake:
        # o aviso de sucesso atravessa o rerun na sessão; a volta o lê daqui
        chamadas.sessao = fake.session_state
        for modulo in MODULOS_DA_TELA:
            sys.modules.pop(modulo, None)
        tela = importlib.import_module("st.ui.admin_st")

        def listar():
            if falha_ao_listar:
                raise RuntimeError("supabase fora do ar")
            return list(escolas if escolas is not None else [ETEC, DELTA])

        tela.listar_escolas = listar
        for nome in ("criar_escola", "atualizar_escola", "excluir_escola"):
            setattr(tela, nome, chamadas.registrar(nome))

        devolvido = getattr(tela, secao)(*args)
    return fake.roteiro(), chamadas, devolvido


def _tem(roteiro, trecho) -> bool:
    return any(trecho in linha for linha in roteiro)


# ====================== EXCLUIR: AS DUAS TRAVAS ======================

SLUG_CERTO = "Digite exatamente o slug 'etecata' para confirmar:"
FRASE = "Digite APAGAR para confirmar a exclusão definitiva:"
BOTAO = "🗑️ Excluir definitivamente"


def test_excluir_com_as_duas_confirmacoes_certas_apaga():
    roteiro, chamadas, _ = _rodar(
        "_secao_excluir_escola", [ETEC],
        respostas={SLUG_CERTO: "etecata", FRASE: "APAGAR", BOTAO: True},
    )

    assert [c[0] for c in chamadas] == ["excluir_escola"]
    assert chamadas[0][1] == ("1",), "apagou a escola errada"
    # O st.success antes do st.rerun() sumia na tela de verdade -- a
    # fotografia antiga cobrava justamente essa linha. O aviso sai na volta.
    assert "rerun" in roteiro
    assert not _tem(roteiro, "excluída com sucesso")
    volta, _, _ = _rodar("_secao_excluir_escola", [ETEC], sessao=dict(chamadas.sessao))
    assert _tem(volta, "excluída com sucesso")


SELECT_EXCLUIR = "select_excluir_escola"
SLUG_DELTA = "Digite exatamente o slug 'deltaata' para confirmar:"


def test_apaga_a_escola_selecionada_e_nao_a_primeira_da_lista():
    """Com uma escola só na lista, `escolas[0]` acerta por acaso.

    Foi o único defeito plantado que passou: a versão que apaga sempre a
    primeira ficava verde porque o teste tinha uma escola. Com duas, selecionar
    a segunda apagaria a ETEC inteira -- alunos, logs e conta de professor.
    """
    _, chamadas, _ = _rodar(
        "_secao_excluir_escola", [ETEC, DELTA],
        respostas={
            SELECT_EXCLUIR: "Educacional Delta (deltaata)",
            SLUG_DELTA: "deltaata",
            FRASE: "APAGAR",
            BOTAO: True,
        },
    )

    assert [c[0] for c in chamadas] == ["excluir_escola"]
    assert chamadas[0][1] == ("2",), "apagou a escola errada"


def test_o_slug_pedido_e_o_da_escola_selecionada():
    # Se o campo continuasse pedindo o slug da primeira, a confirmação
    # deixaria de confirmar coisa alguma.
    roteiro, _, _ = _rodar(
        "_secao_excluir_escola", [ETEC, DELTA],
        respostas={SELECT_EXCLUIR: "Educacional Delta (deltaata)"},
    )

    assert _tem(roteiro, "slug 'deltaata'")
    assert not _tem(roteiro, "slug 'etecata'")


@pytest.mark.parametrize(
    "respostas, esperado",
    [
        ({SLUG_CERTO: "etec", FRASE: "APAGAR"}, "Slug de confirmação incorreto"),
        ({SLUG_CERTO: "", FRASE: "APAGAR"}, "Slug de confirmação incorreto"),
        # o slug da OUTRA escola: o erro mais plausivel de quem tem duas
        ({SLUG_CERTO: "deltaata", FRASE: "APAGAR"}, "Slug de confirmação incorreto"),
        ({SLUG_CERTO: "etecata", FRASE: ""}, "Confirmação final incorreta"),
        ({SLUG_CERTO: "etecata", FRASE: "apagar"}, "Confirmação final incorreta"),
        ({SLUG_CERTO: "etecata", FRASE: "sim"}, "Confirmação final incorreta"),
    ],
)
def test_uma_confirmacao_errada_ja_impede_a_exclusao(respostas, esperado):
    roteiro, chamadas, _ = _rodar(
        "_secao_excluir_escola", [ETEC], respostas={**respostas, BOTAO: True}
    )

    assert not chamadas, f"apagou mesmo com confirmação errada: {respostas}"
    assert _tem(roteiro, esperado)


def test_sem_clicar_no_botao_nada_acontece():
    # As duas confirmações certas, mas ninguém clicou: não pode apagar.
    _, chamadas, _ = _rodar(
        "_secao_excluir_escola", [ETEC],
        respostas={SLUG_CERTO: "etecata", FRASE: "APAGAR"},
    )

    assert not chamadas


def test_o_aviso_da_exclusao_cita_a_conta_de_professor():
    # O CASCADE de usuarios.escola_id é recente. Aviso que não acompanha o que
    # a ação faz é pior que aviso nenhum: dá confiança errada.
    #
    # A checagem para em "conta de professor" porque o roteiro resume a string
    # em 90 caracteres -- o que vem depois não chega à bancada. O resto do
    # aviso ("Não há como desfazer") está coberto pela fotografia, não aqui.
    roteiro, _, _ = _rodar("_secao_excluir_escola", [ETEC])

    assert _tem(roteiro, "conta de professor")


def test_sem_escola_nao_ha_o_que_excluir():
    roteiro, chamadas, _ = _rodar("_secao_excluir_escola", [], respostas={BOTAO: True})

    assert not chamadas
    assert not _tem(roteiro, "Excluir definitivamente")


# ====================== CADASTRAR ======================


def test_cadastrar_exige_nome():
    roteiro, chamadas, _ = _rodar(
        "_secao_cadastrar_escola", respostas={"Confirmar Cadastro": True}
    )

    assert not chamadas
    assert _tem(roteiro, "Preencha o nome")


def test_cadastrar_com_nome_cria_a_escola():
    roteiro, chamadas, _ = _rodar(
        "_secao_cadastrar_escola",
        respostas={"Nome da Instituição": "Colégio Novo", "Confirmar Cadastro": True},
    )

    assert [c[0] for c in chamadas] == ["criar_escola"]
    assert chamadas[0][2]["nome"] == "Colégio Novo"
    assert "rerun" in roteiro
    volta, _, _ = _rodar("_secao_cadastrar_escola", sessao=dict(chamadas.sessao))
    assert _tem(volta, "criada com sucesso")


def test_o_slug_do_cadastro_e_normalizado():
    # Ele vira o código que a turma digita: espaço e maiúscula não podem passar.
    _, chamadas, _ = _rodar(
        "_secao_cadastrar_escola",
        respostas={
            "Nome da Instituição": "Colégio Novo",
            "Código de Acesso (Slug)": "  Colégio Novo!!  ",
            "Confirmar Cadastro": True,
        },
    )

    slug = chamadas[0][2]["slug"]
    assert slug == slug.strip().lower()
    assert " " not in slug and "!" not in slug


# ====================== EDITAR ======================


def test_editar_exige_nome():
    roteiro, chamadas, _ = _rodar(
        "_secao_editar_escola", [ETEC],
        respostas={"Nome": "   ", "💾 Salvar alterações": True},
    )

    assert not chamadas
    assert _tem(roteiro, "Nome e slug são obrigatórios")


def test_editar_salva_os_campos_da_escola_escolhida():
    _, chamadas, _ = _rodar(
        "_secao_editar_escola", [ETEC],
        respostas={"Nome": "ETEC Araçatuba", "💾 Salvar alterações": True},
    )

    assert [c[0] for c in chamadas] == ["atualizar_escola"]
    id_escola, campos = chamadas[0][1]
    assert id_escola == "1"
    assert campos["nome"] == "ETEC Araçatuba"
    assert campos["slug"] == "etecata", "o slug atual tem que vir preenchido"


def test_editar_salva_a_escola_selecionada_e_nao_a_primeira():
    # O mesmo par da exclusão: com uma escola só na lista, `escolas[0]`
    # acertaria por acaso.
    _, chamadas, _ = _rodar(
        "_secao_editar_escola", [ETEC, DELTA],
        respostas={
            "Selecione a escola": "Educacional Delta (deltaata)",
            "💾 Salvar alterações": True,
        },
    )

    id_escola, campos = chamadas[0][1]
    assert id_escola == "2", "editou a escola errada"
    assert campos["slug"] == "deltaata"


def test_sem_escola_nao_ha_o_que_editar():
    roteiro, chamadas, _ = _rodar(
        "_secao_editar_escola", [], respostas={"💾 Salvar alterações": True}
    )

    assert not chamadas
    assert _tem(roteiro, "Cadastre uma escola primeiro")


# ====================== LISTAR ======================


def test_a_listagem_devolve_as_escolas_para_as_secoes_seguintes():
    _, _, escolas = _rodar("_secao_unidades_ativas")

    assert [e["slug"] for e in escolas] == ["etecata", "deltaata"]


def test_banco_fora_do_ar_devolve_lista_vazia_em_vez_de_quebrar():
    """As seções abaixo mostram "cadastre uma escola primeiro" e a tela abre.

    Sem isto, uma falha de rede levaria o painel inteiro junto.
    """
    roteiro, _, escolas = _rodar("_secao_unidades_ativas", falha_ao_listar=True)

    assert escolas == []
    assert _tem(roteiro, "Erro ao listar unidades")


def test_sem_escolas_a_listagem_avisa():
    roteiro, _, escolas = _rodar("_secao_unidades_ativas", escolas=[])

    assert escolas == []
    assert _tem(roteiro, "Nenhuma escola cadastrada")
