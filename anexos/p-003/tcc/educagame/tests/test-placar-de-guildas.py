"""O placar da guilda, que agora é contado num lugar só.

MELHORIA: a tela do Streamlit tinha cópia própria de `montar_guildas` (68
linhas), `parse_data` e `inicio_semana`. Comparadas linha a linha com
`services/guildas_service.py`, eram **idênticas** — só mudavam o underscore do
nome e a formatação das chaves.

Idênticas era a hora certa de juntar. Depois que divergem, alguém precisa
decidir qual está certa, e aqui o placar decide quem ganha a semana: duas
contas diferentes para a mesma turma, uma em cada frontend, seria uma
discussão sem resposta. Este projeto já pagou isso duas vezes — *"esta série é
de Ensino Médio?"* em cinco lugares, e o nome da guilda no mesmo par de
arquivos.

(Este arquivo se chamava `test_tela_guildas.py` e testava a cópia da tela.
Agora testa a fonte única; o Flask e o Streamlit chamam a mesma função.)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from services.guildas_service import montar_guildas, parse_data

RAIZ = Path(__file__).resolve().parent.parent

ALUNO = {
    "id": "aluno-1",
    "ano_escolar": "1 Ano EM",
    "periodo": "Manha",
    "pontos_totais": 0,
}


def test_parse_data_converte_utc_para_horario_de_brasilia():
    data = parse_data("2026-04-27T01:30:00+00:00")

    assert data == datetime(2026, 4, 26, 22, 30)


def test_montar_guildas_exclui_log_utc_que_ainda_e_domingo_no_brasil(monkeypatch):
    # MELHORIA: era monkeypatch por CAMINHO de string. O caminho resolve o
    # módulo na HORA do patch; se alguém tiver recarregado o módulo no meio da
    # suíte -- e teste de tela do Streamlit precisa fazer isso --, o patch cai
    # num objeto NOVO enquanto a função que este arquivo importou no topo
    # continua vendo a original. Verde sozinho, vermelho na suíte.
    #
    # __globals__ é o namespace onde a própria função resolve os nomes: não
    # depende de o módulo continuar em sys.modules nem de ser o mesmo objeto.
    monkeypatch.setitem(
        montar_guildas.__globals__, "inicio_semana", lambda: datetime(2026, 4, 27, 0, 0)
    )
    logs = [
        # 01:30 UTC de segunda ainda é domingo 22:30 em Brasília: fora da semana
        {"aluno_id": "aluno-1", "resultado": "Acertou", "created_at": "2026-04-27T01:30:00+00:00"},
        # 03:30 UTC já é segunda 00:30 em Brasília: dentro
        {"aluno_id": "aluno-1", "resultado": "Acertou", "created_at": "2026-04-27T03:30:00+00:00"},
    ]

    guildas = montar_guildas([ALUNO], logs)

    assert guildas[0]["questoes_semana"] == 1
    assert guildas[0]["acertos_semana"] == 1


def test_os_dois_frontends_chamam_a_mesma_funcao():
    # A garantia estrutural: sem cópia, não há como divergir. O que se prende
    # aqui não é o texto do placar -- é não existirem duas contas.
    tela = (RAIZ / "st/ui/tela_guildas_st.py").read_text(encoding="utf-8-sig")
    rota = (RAIZ / "web/routes/guildas_fla.py").read_text(encoding="utf-8-sig")

    for onde, fonte in (("streamlit", tela), ("flask", rota)):
        assert "from services.guildas_service import" in fonte, onde
        assert "montar_guildas(" in fonte, onde

    for copia in ("def _montar_guildas", "def _parse_data", "def _inicio_semana"):
        assert copia not in tela, f"a cópia voltou para a tela: {copia}"
    assert "FUSO_BRASILIA" not in tela, "o fuso voltou a ser definido na tela"


# ====================== A TELA, DEPOIS DE PERDER 88 LINHAS ======================

# Importado fora do dublê: a tela puxa services/repositories, e alguns deles
# resolvem `get_runtime()` no import -- com o dublê instalado pegariam o
# streamlit falso. Ver tests/test_adm_streamlit_por_papel.py.
import st.ui.tela_guildas_st  # noqa: E402,F401


def test_a_tela_continua_desenhando_o_placar(monkeypatch):
    # A tela perdeu 88 das suas 258 linhas para o serviço. Ela não tinha teste
    # de renderização nenhum -- este existe para provar que o que saiu era
    # mesmo só a cópia.
    import importlib
    import sys

    from tests.apoio_streamlit import StreamlitFalso

    class RepoFalso:
        def buscar_alunos(self, _escola):
            return [
                {"id": "a1", "ano_escolar": "1 Ano EM", "periodo": "Manha", "pontos_totais": 40},
                {"id": "a2", "ano_escolar": "2 Ano EM", "periodo": "Tarde", "pontos_totais": 70},
            ]

        def buscar_logs(self, _escola):
            agora = datetime.now().isoformat()
            return [
                {"aluno_id": "a1", "resultado": "Acertou", "created_at": agora},
                {"aluno_id": "a2", "resultado": "Errou", "created_at": agora},
            ]

    with StreamlitFalso() as fake:
        sys.modules.pop("st.ui.tela_guildas_st", None)
        tela = importlib.import_module("st.ui.tela_guildas_st")
        try:
            tela.renderizar_tela_guildas("escola-1", RepoFalso(), {"id": "escola-1", "modo_guilda": True})
        except Exception as erro:  # noqa: BLE001
            if type(erro).__name__ != "ParouAqui":
                fake._anotar(f"!! {type(erro).__name__}: {str(erro)[:150]}")
        roteiro = fake.roteiro()

    assert not any(linha.startswith("!!") for linha in roteiro), roteiro
    assert any("Guildas" in linha for linha in roteiro), roteiro
    assert any("Lider semanal" in linha for linha in roteiro), roteiro
