"""Cache de dois niveis: memoria na frente, Supabase atras.

MELHORIA: o nivel 2 mora em public.cache_dados, no Supabase -- entao ATE O
ACERTO custava uma ida a rede (acerto = 1 consulta; erro = 3: le o cache, le
a fonte, grava o cache). O painel do professor faz 6 leituras dessas em
sequencia e levava ~6 s em producao.

O risco de todo cache e servir dado velho, e e isso que estes testes
cobram: o nivel 1 tem que sumir quando .clear() e chamado (toda escrita
chama) e nao pode viver mais que alguns segundos.
"""

from __future__ import annotations

import time

import pytest

from core import runtime_context


@pytest.fixture(autouse=True)
def _l1_limpo():
    runtime_context._l1.clear()
    yield
    runtime_context._l1.clear()


@pytest.fixture
def cache_falso(monkeypatch):
    """Substitui o nivel 2 (Supabase) por um dict, contando os acessos."""
    armazenado: dict[str, object] = {}
    acessos = {"buscar": 0, "salvar": 0, "limpar": 0}

    class _CacheRepoFalso:
        @staticmethod
        def buscar(chave):
            acessos["buscar"] += 1
            if chave in armazenado:
                return armazenado[chave], True
            return None, False

        @staticmethod
        def salvar(chave, valor, ttl):
            acessos["salvar"] += 1
            armazenado[chave] = valor

        @staticmethod
        def limpar_prefixo(prefixo):
            acessos["limpar"] += 1
            for chave in [k for k in armazenado if k.startswith(prefixo)]:
                armazenado.pop(chave)

    import repositories

    monkeypatch.setattr(repositories, "cache_repo", _CacheRepoFalso, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "repositories.cache_repo", _CacheRepoFalso)
    return acessos


def _funcao_contada():
    """Usa o RuntimeContext direto, nao get_runtime().

    get_runtime() devolve o MODULO do streamlit quando ele esta em
    sys.modules -- e basta um teste importar st/ui/* para ele ficar la pelo
    resto da sessao. Isso fazia estes testes exercitarem o st.cache_data na
    suite completa, e passarem sozinhos: o cache de dois niveis daqui so
    vale para o frontend Flask, que e onde estava a lentidao.
    """
    chamadas = {"n": 0}

    @runtime_context.RuntimeContext().cache_data(ttl=60)
    def somar(a, b):
        chamadas["n"] += 1
        return a + b

    return somar, chamadas


def test_segunda_chamada_nao_toca_a_rede(cache_falso):
    somar, chamadas = _funcao_contada()

    assert somar(2, 3) == 5
    rede_apos_primeira = cache_falso["buscar"]
    assert somar(2, 3) == 5

    assert chamadas["n"] == 1, "chamou a funcao de novo"
    assert cache_falso["buscar"] == rede_apos_primeira, "consultou o nivel 2 de novo"


def test_clear_invalida_o_nivel_em_memoria(cache_falso):
    # A parte que importa: toda escrita chama .clear(). Se o nivel 1
    # sobrevivesse, a tela seguiria mostrando o dado antigo.
    somar, chamadas = _funcao_contada()
    somar(2, 3)

    somar.clear()
    somar(2, 3)

    assert chamadas["n"] == 2, "serviu valor velho depois do clear"


def test_clear_nao_derruba_chave_de_outro_argumento(cache_falso):
    somar, chamadas = _funcao_contada()
    somar(2, 3)
    somar(10, 20)
    antes = chamadas["n"]

    somar.clear()

    assert antes == 2
    somar(2, 3)
    somar(10, 20)
    assert chamadas["n"] == 4, "clear tem que limpar as duas chaves da funcao"


def test_argumentos_diferentes_sao_entradas_diferentes(cache_falso):
    somar, chamadas = _funcao_contada()

    assert somar(2, 3) == 5
    assert somar(10, 20) == 30

    assert chamadas["n"] == 2


def test_nivel_1_expira_e_cai_para_o_nivel_2(cache_falso, monkeypatch):
    # Mesmo com ttl de 60 s no nivel 2, o nivel 1 nao pode viver tanto:
    # com mais de um worker, cada um tem o seu e um clear nao alcanca os
    # outros. O TTL curto limita ate onde a defasagem pode ir.
    monkeypatch.setattr(runtime_context, "_L1_TTL_SEGUNDOS", 0.05)
    somar, chamadas = _funcao_contada()
    somar(2, 3)
    buscas_antes = cache_falso["buscar"]

    time.sleep(0.08)
    somar(2, 3)

    assert cache_falso["buscar"] > buscas_antes, "nivel 1 nao expirou"
    assert chamadas["n"] == 1, "deveria ter vindo do nivel 2, sem recalcular"


def test_ttl_do_nivel_1_nunca_passa_do_teto(cache_falso):
    somar, _ = _funcao_contada()
    somar(2, 3)

    (expira_em, _valor) = next(iter(runtime_context._l1.values()))
    restante = expira_em - time.monotonic()

    assert restante <= runtime_context._L1_TTL_SEGUNDOS + 0.01
    assert restante > 0


def test_nao_acumula_chave_vencida_sem_limite(cache_falso, monkeypatch):
    monkeypatch.setattr(runtime_context, "_L1_TTL_SEGUNDOS", 0.01)
    somar, _ = _funcao_contada()

    for i in range(80):
        somar(i, 0)
    time.sleep(0.02)
    somar(999, 0)

    assert len(runtime_context._l1) < 80, f"nivel 1 acumulou {len(runtime_context._l1)} chaves"
