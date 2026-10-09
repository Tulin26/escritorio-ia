"""O guia de acesso tem que descrever o login que o código realmente faz.

MELHORIA: o guia da Educacional Delta era um PDF avulso, sem fonte no
repositório. Quando o login ganhou a tela de código da escola, nada apontou
para ele — e o documento seguiu circulando com três afirmações erradas, das
quais **duas mandavam o leitor para o lugar errado logo na primeira tela**:

  1. o endereço `?escola=deltaata`, cujo parâmetro passou a ser ignorado;
  2. nenhuma menção ao código, que virou obrigatório;
  3. a garantia de que "a conta de professor não está presa a uma escola" —
     hoje o oposto do que `conta_pode_entrar` faz.

Um documento de fora do sistema não pode ser cobrado por teste; o texto dele,
sim, desde que more no repositório. É o que estes testes prendem: cada
afirmação do guia é conferida contra o comportamento de verdade, chamando o
código em vez de repetir a frase.
"""

from __future__ import annotations

import pytest

from scripts.gerar_guia_acesso import (
    TEXTO_SESSAO,
    URL_LIMPA,
    passos_de_entrada,
    roteiro,
    texto_conta_presa,
)
from services.auth_service import conta_pode_entrar
from web.routes import home_fla

SLUG = "deltaata"
DELTA = {"id": "1", "nome": "Educacional Delta", "slug": SLUG}


@pytest.fixture(autouse=True)
def _sem_rede(monkeypatch):
    monkeypatch.setattr(home_fla, "listar_escolas", lambda: [DELTA])
    monkeypatch.setattr(
        home_fla, "buscar_escola_por_slug", lambda slug: DELTA if slug == SLUG else None
    )


def _texto_dos_passos() -> str:
    return " ".join(texto for _, texto in passos_de_entrada(SLUG))


# ====================== O ENDEREÇO ======================


@pytest.mark.parametrize("atalho", ["?escola=", "/e/", "escola="])
def test_o_guia_nao_manda_usar_atalho_que_nao_funciona_mais(atalho):
    # Era o erro nº 1: o endereço do guia antigo levava o parâmetro, e quem o
    # abrisse cairia na lista de escolas sem entender por quê.
    assert atalho not in URL_LIMPA


def test_o_endereco_do_guia_e_a_raiz_do_site():
    assert URL_LIMPA == "https://educagame.onrender.com/"


def test_o_atalho_removido_de_fato_nao_escolhe_mais_a_escola(client):
    """A outra ponta: se o `?escola=` voltasse a funcionar, o guia mudaria.

    Sem isto, os testes acima seriam só uma opinião sobre uma string. Que o
    atalho é ignorado já está coberto em `test_slug_de_escola_envelhecido.py`;
    aqui ele é conferido de novo por outro motivo — é a frase do papel.
    """
    client.get(f"/?escola={SLUG}")

    with client.session_transaction() as sessao:
        assert not sessao.get("escola_slug"), "o ?escola= voltou a entrar na sessão"


# ====================== A ORDEM DAS TELAS ======================


def test_o_codigo_aparece_nos_passos():
    # Era o erro nº 2, e o que efetivamente travava o diretor.
    assert SLUG in _texto_dos_passos()


def test_o_codigo_vem_antes_do_usuario_e_da_senha():
    # A ordem é a razão de o guia antigo falhar: ele começava pelo login.
    texto = _texto_dos_passos()

    assert texto.index(SLUG) < texto.lower().index("senha")


def test_todo_login_do_roteiro_passa_pelo_codigo():
    """O roteiro é o que a pessoa segue de fato; o passo a passo ela pula.

    São DOIS logins (aluno e professor), e o segundo é o que se esquece:
    quem sai da conta volta para a lista de escolas, não para a tela de senha.
    """
    logins = [p for p in roteiro(SLUG) if "entre como" in p]

    assert len(logins) == 2, "o roteiro tem que exercitar as duas contas"
    for passo in logins:
        assert SLUG in passo or "código" in passo, passo


def test_a_escola_do_guia_aparece_na_lista_publica(client):
    # O passo 2 manda escolher a escola numa lista. Se ela não estivesse
    # listada, não haveria por onde chegar à tela do código.
    corpo = client.get("/").get_data(as_text=True)

    assert "Educacional Delta" in corpo


# ====================== A CONTA PRESA À ESCOLA ======================


def test_o_guia_diz_que_a_conta_pertence_a_uma_escola():
    # Era o erro nº 3, e o mais perigoso: o guia antigo descrevia como
    # funcionalidade o defeito que `conta_pode_entrar` veio corrigir.
    texto = texto_conta_presa("Educacional Delta")

    assert "pertence à Educacional Delta" in texto
    assert "não</b> está presa" not in texto


def test_a_frase_do_guia_bate_com_a_recusa_de_verdade():
    """O guia cita a mensagem que o sistema mostra. Se ela mudar, isto quebra."""
    pode, motivo = conta_pode_entrar(
        {"role": "professor", "escola_id": "delta"}, "outra-escola"
    )

    assert not pode
    assert motivo in texto_conta_presa("Educacional Delta")


def test_se_a_conta_deixar_de_ser_presa_o_papel_muda_sozinho(monkeypatch):
    """A razão de a frase ser gerada, e não escrita.

    O guia anterior errou exatamente aqui: alguém afirmou uma vez que a conta
    era global, a regra mudou embaixo, e o texto continuou. Perguntando ao
    código, não existe onde escrever a contradição -- para o papel voltar a
    dizer "não está presa", a regra precisa realmente deixar de prender.
    """
    import scripts.gerar_guia_acesso as gerador

    # setitem no __globals__ da propria funcao, e nao monkeypatch por caminho
    # de string: e a regra que este projeto ja pagou para aprender (ver
    # PROXIMOS_PASSOS.md). E o namespace onde a funcao resolve o nome.
    monkeypatch.setitem(
        gerador.texto_conta_presa.__globals__,
        "conta_pode_entrar",
        lambda usuario, escola_id: (True, ""),
    )

    texto = gerador.texto_conta_presa("Educacional Delta")

    assert "não</b> está presa" in texto


def test_professor_da_escola_certa_entra():
    # A metade que não pode se perder: apertar a regra não vale nada se a
    # conta legítima também parar de entrar.
    pode, _ = conta_pode_entrar({"role": "professor", "escola_id": "delta"}, "delta")

    assert pode


# ====================== A SESSÃO QUE EXPIRA ======================


def test_o_aviso_de_sessao_usa_o_prazo_de_verdade():
    """O número no papel sai de core/sessao.py, não é digitado no texto.

    A trava de inatividade é nova e se manifesta como defeito para quem não
    sabe dela: a aba fica aberta, a pessoa volta e é devolvida à tela de
    escolher escola.
    """
    from core.sessao import MINUTOS_INATIVIDADE_PADRAO

    texto = TEXTO_SESSAO.format(minutos=int(MINUTOS_INATIVIDADE_PADRAO))

    assert str(int(MINUTOS_INATIVIDADE_PADRAO)) in texto
    assert "{minutos}" not in texto


def test_o_texto_da_sessao_e_um_molde_e_nao_um_numero_fixo():
    # Sem isto, alguém poderia "consertar" o teste acima escrevendo 30 no
    # texto, e o papel voltaria a mentir na próxima mudança de prazo.
    assert "{minutos}" in TEXTO_SESSAO
