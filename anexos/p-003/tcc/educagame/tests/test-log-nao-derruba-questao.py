"""Escrever no log nunca pode destruir o que estava sendo feito.

MELHORIA: bug visto ao vivo. A IA gerou uma questao valida contendo
" " (espaco estreito sem quebra, que os modelos usam entre numero e
unidade). O log imprime o enunciado junto do motivo da rejeicao, e no
Windows o stdout sai em cp1252, onde esse caractere nao existe. O print
levantou UnicodeEncodeError, a excecao subiu, foi capturada pelo
`except Exception` de quem chamou -- e a questao inteira virou banco
offline:

    [LAB] Falha ao gerar desafio; usando fallback offline seguro:
    UnicodeEncodeError: 'charmap' codec can't encode character ' '

Uma linha de log matou uma questao boa. O log e justamente a parte do
sistema que nunca deveria ter esse poder: existe para contar o que
aconteceu, nao para mudar o que acontece.
"""

from __future__ import annotations

import io
import sys

import pytest

from core.diagnostico_config import tornar_saida_tolerante

# Caracteres que os modelos produzem e que o cp1252 nao conhece.
IMPOSSIVEIS_EM_CP1252 = [
    " ",  # espaco estreito sem quebra: "5 cm"
    " ",  # espaco fino
    "−",  # sinal de menos tipografico
    "≈",  # aproximadamente
    "²⁰",  # expoentes sobrescritos combinados
    "Δ",  # delta maiusculo
]


def _saida_cp1252() -> io.TextIOWrapper:
    """Um stdout igual ao do Windows: cp1252 e estrito."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")


@pytest.mark.parametrize("caractere", IMPOSSIVEIS_EM_CP1252)
def test_sem_a_correcao_o_print_quebra(caractere):
    # Prende o mecanismo do bug: se um dia o Python parar de levantar aqui,
    # os testes abaixo deixam de provar qualquer coisa.
    saida = _saida_cp1252()

    with pytest.raises(UnicodeEncodeError):
        saida.write(f"[IA] rejeitado: 5{caractere}cm")
        saida.flush()


@pytest.mark.parametrize("caractere", IMPOSSIVEIS_EM_CP1252)
def test_depois_da_correcao_o_print_passa(monkeypatch, caractere):
    saida = _saida_cp1252()
    monkeypatch.setattr(sys, "stdout", saida)

    tornar_saida_tolerante()
    print(f"[IA] rejeitado: 5{caractere}cm")  # nao pode levantar

    assert sys.stdout.errors == "replace"


@pytest.mark.parametrize("caractere", IMPOSSIVEIS_EM_CP1252)
def test_o_stderr_tambem_fica_protegido(monkeypatch, caractere):
    # O traceback de uma excecao sai pelo stderr e carrega o texto que
    # causou o erro -- justamente o conteudo vindo da IA. Proteger so o
    # stdout deixaria a metade mais provavel de fora.
    saida = _saida_cp1252()
    monkeypatch.setattr(sys, "stderr", saida)

    tornar_saida_tolerante()
    print(f"[IA] falhou ao processar: 5{caractere}cm", file=sys.stderr)

    assert sys.stderr.errors == "replace"


def test_a_correcao_nao_troca_a_codificacao(monkeypatch):
    # Trocar cp1252 por utf-8 mudaria como o texto aparece para quem le o
    # log no terminal. So a POLITICA DE ERRO muda.
    saida = _saida_cp1252()
    monkeypatch.setattr(sys, "stdout", saida)

    tornar_saida_tolerante()

    assert sys.stdout.encoding.lower().replace("-", "") == "cp1252"


def test_saida_ja_tolerante_fica_como_esta(monkeypatch):
    # No Render e no Streamlit Cloud a saida ja e utf-8: nada a fazer.
    saida = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="backslashreplace")
    monkeypatch.setattr(sys, "stdout", saida)

    tornar_saida_tolerante()

    assert sys.stdout.errors == "backslashreplace"


def test_saida_sem_reconfigure_nao_quebra(monkeypatch):
    # pytest e alguns runners trocam o stdout por objetos que nao tem
    # reconfigure. A funcao nao pode explodir por causa disso.
    class SaidaSimples:
        errors = "strict"

        def write(self, _texto):
            return 0

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", SaidaSimples())
    monkeypatch.setattr(sys, "stderr", SaidaSimples())

    tornar_saida_tolerante()  # nao pode levantar


# --------------------------------------------------------------------------
# o teste que importa: o efeito, nao a codificacao
# --------------------------------------------------------------------------


def test_questao_boa_sobrevive_ao_log_impossivel(monkeypatch):
    """A questao chega inteira mesmo quando o log nao consegue escreve-la.

    Este e o caso real: o Laboratorio recebeu uma questao valida, o log
    tentou registrar a rejeicao de uma tentativa anterior e morreu no
    caractere -- levando a questao junto.
    """
    import services.ia.enigma as enigma

    questao_com_caractere_impossivel = {
        "enigma": "O movimento deixa rastros onde os olhos veem passagem.",
        # 5 cm: o espaco estreito que a IA usa entre numero e unidade
        "pergunta": "Um corpo percorre 100 m em 5 s. Qual a velocidade media?",
        "opcoes": ["20 m/s", "15 m/s", "25 m/s", "10 m/s"],
        "correta": 0,
        "formula": "v = d/t",
        "subformulas": [],
        "legenda_variaveis": "v = velocidade",
        "explicacao": [{"tipo": "resultado", "conteudo": "A velocidade media e a distancia percorrida dividida pelo tempo gasto."}],
        "passos_resolucao": [
            {"titulo": "1o Passo", "conteudo": "v = 100/5", "final": False},
            {"titulo": "Resultado Final", "conteudo": "v = 20 m/s", "final": True},
        ],
    }

    monkeypatch.setattr(enigma, "gerar_json_ia", lambda *a, **k: dict(questao_com_caractere_impossivel))
    monkeypatch.setattr(enigma, "obter_ultimo_provedor_ia", lambda: "groq")
    monkeypatch.setattr(sys, "stdout", _saida_cp1252())
    tornar_saida_tolerante()

    questao = enigma.invocar_enigma_laboratorio("Fisica", "1o Ano EM", "Medio", tema="cinematica")

    assert questao, "a questao foi descartada por causa do log"
    assert questao["_origem_geracao"] == "ia"
    assert questao["opcoes"][questao["correta"]] == "20 m/s"


def test_o_diagnostico_de_boot_deixa_a_saida_tolerante(monkeypatch):
    # relatar_configuracao roda no boot dos DOIS frontends. E de la que a
    # protecao entra em vigor -- se sair, o bug volta em silencio.
    from core.diagnostico_config import relatar_configuracao

    saida = _saida_cp1252()
    monkeypatch.setattr(sys, "stdout", saida)

    relatar_configuracao(imprimir=lambda _m: None)

    assert sys.stdout.errors == "replace"
