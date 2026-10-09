from __future__ import annotations

import time

from core.runtime_context import RuntimeContext

# MELHORIA: era `runtime = get_runtime()`, resolvido no IMPORT deste arquivo.
# get_runtime() devolve o MODULO do streamlit quando ele esta em sys.modules,
# e basta um outro teste importar st/ui/* para ele ficar la pelo resto da
# sessao. Na suite completa este arquivo media o cache do STREAMLIT; rodando
# sozinho, media o deste projeto.
#
# O efeito foi um teste verde onde se costuma olhar e vermelho quando rodava
# sozinho -- e, pior, o defeito que ele existia para pegar (o cache
# devolvendo o proprio objeto guardado) ficou anos sem ser visto, porque na
# suite quem respondia era o Streamlit.
#
# A mesma armadilha ja estava documentada em test_cache_dois_niveis.py; aqui
# ninguem tinha aplicado. Usar RuntimeContext direto tira a ordem de import
# da jogada.
runtime = RuntimeContext()


def test_segunda_chamada_dentro_do_ttl_nao_reinvoca(sem_rede_supabase):
    chamadas = []

    @runtime.cache_data(ttl=5)
    def buscar(chave):
        chamadas.append(chave)
        return f"valor-{chave}"

    assert buscar("a") == "valor-a"
    assert buscar("a") == "valor-a"
    assert chamadas == ["a"]


def test_apos_ttl_expirar_reinvoca(sem_rede_supabase):
    chamadas = []

    @runtime.cache_data(ttl=0.05)
    def buscar(chave):
        chamadas.append(chave)
        return len(chamadas)

    primeiro = buscar("x")
    time.sleep(0.08)
    segundo = buscar("x")

    assert primeiro == 1
    assert segundo == 2
    assert chamadas == ["x", "x"]


def test_clear_forca_reinvocacao_imediata(sem_rede_supabase):
    chamadas = []

    @runtime.cache_data(ttl=30)
    def buscar(chave):
        chamadas.append(chave)
        return len(chamadas)

    buscar("y")
    buscar("y")
    buscar.clear()
    buscar("y")

    assert chamadas == ["y", "y"]


def test_argumentos_diferentes_sao_entradas_independentes(sem_rede_supabase):
    chamadas = []

    @runtime.cache_data(ttl=30)
    def buscar(escola_id, aluno_id=None):
        chamadas.append((escola_id, aluno_id))
        return [escola_id, aluno_id]

    buscar("escola-1")
    buscar("escola-2")
    buscar("escola-1", aluno_id="aluno-9")
    buscar("escola-1")
    buscar("escola-2")

    assert chamadas == [
        ("escola-1", None),
        ("escola-2", None),
        ("escola-1", "aluno-9"),
    ]


def test_decorator_sem_parenteses_tambem_cacheia(sem_rede_supabase):
    chamadas = []

    @runtime.cache_data
    def buscar(chave):
        chamadas.append(chave)
        return chave

    buscar("z")
    buscar("z")

    assert chamadas == ["z"]


def test_lista_retornada_e_copia_nao_corrompe_o_cache(sem_rede_supabase):
    # MELHORIA: protege contra um caller que mutar em memoria a lista
    # devolvida (ex: .sort(), .append()) sem querer corromper o valor
    # guardado no cache pros proximos leitores.
    @runtime.cache_data(ttl=30)
    def buscar_lista():
        return [1, 2, 3]

    primeira = buscar_lista()
    primeira.append(999)
    primeira.sort(reverse=True)

    segunda = buscar_lista()

    assert segunda == [1, 2, 3]


def test_clear_nao_quebra_quando_cache_esta_vazio(sem_rede_supabase):
    @runtime.cache_data(ttl=30)
    def buscar():
        return "ok"

    buscar.clear()
    assert buscar() == "ok"


def test_cache_e_compartilhado_entre_chamadores_diferentes(sem_rede_supabase):
    # MELHORIA: e a razao de o cache ter deixado de ser um dict em memoria
    # de processo (ver core/runtime_context.py) -- um dict local nao seria
    # visto por outro worker do Gunicorn. Aqui simulamos dois "workers" com
    # duas funcoes decoradas independentes (mesmo nome/modulo por estarem
    # aninhadas no mesmo ponto do codigo, closures completamente separadas)
    # e garantimos que um enxerga o que o outro guardou na tabela
    # compartilhada, inclusive a invalidacao via .clear().
    def _fabrica():
        chamadas = []

        @runtime.cache_data(ttl=30)
        def buscar_alunos(escola_id):
            chamadas.append(escola_id)
            return [{"id": "1", "escola_id": escola_id}]

        return buscar_alunos, chamadas

    worker_a, chamadas_a = _fabrica()
    worker_b, chamadas_b = _fabrica()

    assert worker_a("escola-1") == [{"id": "1", "escola_id": "escola-1"}]
    assert worker_b("escola-1") == [{"id": "1", "escola_id": "escola-1"}]
    assert chamadas_a == ["escola-1"]
    assert chamadas_b == []

    worker_a.clear()
    assert worker_b("escola-1") == [{"id": "1", "escola_id": "escola-1"}]
    assert chamadas_b == ["escola-1"]


def test_sob_streamlit_devolve_o_modulo_real(monkeypatch):
    # MELHORIA: regressao de uma quebra em producao. Ao unificar os dois
    # frontends numa branch so, esta funcao ficou com a versao do Flask, que
    # sempre devolve o contexto neutro. O app Streamlit subiu, mas SEM banco:
    # _get_secret (repositories/supabase_client.py) tenta os.getenv, nao
    # acha, e cai em runtime.secrets -- que no contexto neutro esta vazio.
    # Em vez de st.secrets, gerenciado pelo Streamlit Cloud.
    #
    # Nem o teste de fumaca nem a varredura de "modulo.atributo" pegariam:
    # nenhum simbolo sumiu, o COMPORTAMENTO e que mudou. E localmente nao
    # aparece, porque o .env preenche os.getenv antes de chegar em secrets.
    import sys

    from core import runtime_context

    class _StreamlitFalso:
        secrets = {"SUPABASE_URL": "https://exemplo.supabase.co"}

    falso = _StreamlitFalso()
    monkeypatch.setitem(sys.modules, "streamlit", falso)

    assert runtime_context.get_runtime() is falso
    assert runtime_context.get_runtime().secrets["SUPABASE_URL"]


def test_fora_do_streamlit_usa_o_contexto_neutro(monkeypatch):
    import sys

    from core import runtime_context

    monkeypatch.delitem(sys.modules, "streamlit", raising=False)

    runtime = runtime_context.get_runtime()

    assert isinstance(runtime, runtime_context.RuntimeContext)
    # o contexto neutro precisa manter o mesmo shape, senao o swap quebra
    for atributo in ("secrets", "cache_data", "session_state", "error", "warning", "stop"):
        assert hasattr(runtime, atributo), atributo


def test_mutar_um_registro_devolvido_nao_corrompe_o_cache(sem_rede_supabase):
    # A lista era o caso obvio; este e o que mais aparece de verdade --
    # alguem ajusta um campo do registro ("aluno['nome'] = ...") achando que
    # mexe so na propria copia. Sem a copia defensiva, o proximo leitor
    # recebia o registro ja alterado.
    @runtime.cache_data(ttl=30)
    def buscar_alunos_fake():
        return [{"id": "a1", "nome": "Ana"}, {"id": "a2", "nome": "Bruno"}]

    primeira = buscar_alunos_fake()
    primeira[0]["nome"] = "ALTERADO"

    segunda = buscar_alunos_fake()

    assert segunda[0]["nome"] == "Ana", "a alteracao vazou para o cache"


def test_valor_simples_nao_paga_copia(sem_rede_supabase):
    # Texto e numero sao imutaveis: copiar seria custo sem beneficio. O
    # nivel 1 existe para custar quase nada.
    @runtime.cache_data(ttl=30)
    def buscar_texto():
        return "um valor"

    assert buscar_texto() == "um valor"
    assert buscar_texto() is buscar_texto()
