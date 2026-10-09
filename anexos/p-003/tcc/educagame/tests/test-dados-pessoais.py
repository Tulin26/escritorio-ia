"""Pedido de LGPD atendido sem abrir o painel do Supabase na mão.

A página `/privacidade` promete os direitos do Art. 18 -- confirmação, acesso,
portabilidade e exclusão -- e diz que o pedido passa pelo professor ou pela
coordenação. Do outro lado não havia nada: `excluir_aluno` existia e só era
chamado por `scripts/criar_alunos_teste.py`, e para "acesso" não existia
função nenhuma. Atender um pedido era montar consulta à mão no painel do
banco, que é justamente onde um erro não tem volta.

Agora são dois scripts, e continua sem tela de propósito (ver
`services/dados_pessoais.py`): o lado que apaga é irreversível, raro, e chega
por fora do sistema -- precisa ser conferido por uma pessoa antes de rodar.

O banco falso do conftest **não tem CASCADE**, e é isso que dá valor ao teste
da conferência: ele prova que a função enxerga linha que sobrou em vez de
responder "apagado" no escuro.
"""

from __future__ import annotations

import json

import pytest

from services.dados_pessoais import (
    apagar_dados_do_aluno,
    encontrar_aluno,
    reunir_dados_do_aluno,
)

ESCOLA = "escola-1"


def _simular_cascade(banco, aluno_id: str) -> None:
    """O banco falso do conftest não tem CASCADE; o de verdade tem."""
    for tabela in ("logs_pedagogicos", "rpg_progressos"):
        linhas = banco.table(tabela)._tabela.linhas
        linhas[:] = [linha for linha in linhas if linha.get("aluno_id") != aluno_id]


@pytest.fixture
def banco(sem_rede_supabase):
    alunos = sem_rede_supabase.table("alunos")._tabela
    alunos.linhas.append(
        {
            "id": "aluno-1",
            "escola_id": ESCOLA,
            "nome": "Ana Ribeiro",
            "ra_identificacao": "2026001",
            "ano_escolar": "1º Ano EM",
            "periodo": "Manhã",
            "email": "ana@escola.com",
            "username": "ana.ribeiro",
            "senha_hash": "scrypt$naodevesair",
            "email_confirmado": True,
            "pontos_totais": 120,
            "consentimento_dados_em": "2026-09-25T12:00:00+00:00",
        }
    )
    alunos.linhas.append(
        {
            "id": "aluno-2",
            "escola_id": ESCOLA,
            "nome": "Bruno Sá",
            "email": "bruno@escola.com",
            "senha_hash": "scrypt$tambem-nao",
            "consentimento_dados_em": "2026-09-26T12:00:00+00:00",
        }
    )

    # Aluno criado pelo professor (services/aluno_auth_service.py::
    # criar_aluno_com_username não grava e-mail). Aqui com a coluna vazia em
    # vez de nula, que é como uma linha bagunçada de verdade aparece -- e é o
    # que transforma um identificador em branco numa pessoa errada.
    alunos.linhas.append(
        {"id": "aluno-3", "escola_id": ESCOLA, "nome": "Sem E-mail", "email": "", "username": ""}
    )

    logs = sem_rede_supabase.table("logs_pedagogicos")._tabela
    logs.linhas.extend(
        [
            {
                "id": "log-1", "escola_id": ESCOLA, "aluno_id": "aluno-1",
                "pergunta_texto": "Qual é 8% de 160?", "resposta_aluno": "12,8",
                "resultado": "Acertou", "data_hora": "2026-09-26T10:00:00+00:00",
            },
            {
                "id": "log-2", "escola_id": ESCOLA, "aluno_id": "aluno-1",
                "pergunta_texto": "Qual é a capital do Acre?", "resposta_aluno": "Manaus",
                "resultado": "Errou", "data_hora": "2026-09-27T10:00:00+00:00",
            },
            # De outro aluno: não pode aparecer no pedido da Ana.
            {
                "id": "log-3", "escola_id": ESCOLA, "aluno_id": "aluno-2",
                "pergunta_texto": "Outra questão", "resultado": "Acertou",
                "data_hora": "2026-09-27T11:00:00+00:00",
            },
        ]
    )

    progressos = sem_rede_supabase.table("rpg_progressos")._tabela
    progressos.linhas.extend(
        [
            {"id": "p-1", "escola_id": ESCOLA, "aluno_id": "aluno-1", "aventura_id": "av-1", "estado": {"fase": 3}},
            # De outro aluno, pelo mesmo motivo do log-3.
            {"id": "p-2", "escola_id": ESCOLA, "aluno_id": "aluno-2", "aventura_id": "av-1", "estado": {"fase": 1}},
        ]
    )
    return sem_rede_supabase


# --------------------------------------------------------------------------
# Achar a pessoa certa


@pytest.mark.parametrize("identificador", ["aluno-1", "ana@escola.com", "ana.ribeiro"])
def test_encontra_por_id_email_ou_usuario(banco, identificador):
    assert encontrar_aluno(identificador)["nome"] == "Ana Ribeiro"


@pytest.mark.parametrize("identificador", ["", "   ", "nao-existe", "2026001"])
def test_quem_nao_existe_devolve_nada(banco, identificador):
    # O RA ("2026001") não entra de propósito: é único dentro de uma escola,
    # não no banco inteiro, e exclusão na pessoa errada não tem volta.
    #
    # O branco tem motivo próprio: esta função é a porta de um script que
    # APAGA. Um argumento vazio não pode virar pessoa nenhuma, nem quando
    # existe no banco uma linha com e-mail em branco (o "aluno-3" acima).
    assert encontrar_aluno(identificador) is None


# --------------------------------------------------------------------------
# Acesso e portabilidade (Art. 18, II e V)


def test_reune_cadastro_respostas_e_progresso(banco):
    dados = reunir_dados_do_aluno(encontrar_aluno("aluno-1"))

    assert dados["aluno"]["nome"] == "Ana Ribeiro"
    assert len(dados["respostas"]) == 2
    assert len(dados["progresso_rpg"]) == 1
    assert dados["resumo"]["respostas"] == 2
    assert dados["resumo"]["acertos"] == 1
    assert dados["resumo"]["primeira_resposta"] == "2026-09-26T10:00:00+00:00"
    assert dados["resumo"]["ultima_resposta"] == "2026-09-27T10:00:00+00:00"
    assert dados["resumo"]["consentimento_em"] == "2026-09-25T12:00:00+00:00"


def test_a_senha_nunca_sai_no_pedido_de_acesso(banco):
    dados = reunir_dados_do_aluno(encontrar_aluno("aluno-1"))

    assert "senha_hash" not in dados["aluno"]
    assert "naodevesair" not in json.dumps(dados, ensure_ascii=False, default=str)


def test_o_pedido_de_um_aluno_nao_traz_dado_de_outro(banco):
    dados = reunir_dados_do_aluno(encontrar_aluno("aluno-1"))

    assert all(linha["aluno_id"] == "aluno-1" for linha in dados["respostas"])
    assert all(linha["aluno_id"] == "aluno-1" for linha in dados["progresso_rpg"])


# --------------------------------------------------------------------------
# Exclusão (Art. 18, VI)


def test_exclusao_limpa_termina_com_o_banco_sem_a_pessoa(banco):
    # O Bruno não tem progresso de RPG e os logs dele são apagados à mão aqui
    # para simular o CASCADE que o banco de verdade faz.
    _simular_cascade(banco, "aluno-2")

    resultado = apagar_dados_do_aluno(encontrar_aluno("aluno-2"))

    assert resultado["apagado"] is True
    assert not any(resultado["sobraram"].values()), resultado["sobraram"]
    assert encontrar_aluno("bruno@escola.com") is None


def test_sobra_de_linha_e_denunciada_em_vez_de_passar_batido(banco):
    # Sem CASCADE (o caso do banco falso, e o que aconteceria em produção se
    # a migração não tivesse sido aplicada), o cadastro some e as respostas
    # ficam -- dado pessoal continuando no banco depois de um pedido
    # atendido. A função tem de dizer isso, não "apagado".
    resultado = apagar_dados_do_aluno(encontrar_aluno("aluno-1"))

    assert resultado["apagado"] is False
    assert "CASCADE" in resultado["motivo"]
    assert resultado["sobraram"]["respostas"] == 2
    assert resultado["sobraram"]["progresso_rpg"] == 1


def test_aluno_sem_id_nao_apaga_nada(banco):
    assert apagar_dados_do_aluno({"nome": "sem id"})["apagado"] is False


# --------------------------------------------------------------------------
# Os scripts


def test_script_de_acesso_grava_o_json_sem_a_senha(banco, tmp_path, capsys):
    from scripts import dados_do_aluno

    destino = tmp_path / "ana.json"
    assert dados_do_aluno.main(["--quem", "ana@escola.com", "--arquivo", str(destino)]) == 0

    gravado = json.loads(destino.read_text(encoding="utf-8"))
    assert gravado["aluno"]["nome"] == "Ana Ribeiro"
    assert "senha_hash" not in gravado["aluno"]
    assert len(gravado["respostas"]) == 2
    assert "Respostas gravadas: 2" in capsys.readouterr().out


def test_script_de_acesso_sem_arquivo_nao_grava(banco, tmp_path, capsys, monkeypatch):
    from scripts import dados_do_aluno

    monkeypatch.chdir(tmp_path)
    assert dados_do_aluno.main(["--quem", "ana@escola.com"]) == 0

    assert "nada foi gravado" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_script_de_exclusao_sem_confirmar_nao_apaga(banco, capsys, tmp_path, monkeypatch):
    from scripts import excluir_aluno

    # chdir para a pasta do teste: sem --backup o script grava na pasta atual,
    # e um backup com dado de aluno nunca pode cair dentro do repositório --
    # foi o que aconteceu quando a mutação arrancou a saída antecipada daqui.
    monkeypatch.chdir(tmp_path)

    assert excluir_aluno.main(["--quem", "ana@escola.com"]) == 0

    assert "Nada foi apagado" in capsys.readouterr().out
    assert encontrar_aluno("ana@escola.com") is not None
    assert list(tmp_path.iterdir()) == []


def test_script_de_exclusao_pede_o_nome_digitado(banco, tmp_path, capsys):
    from scripts import excluir_aluno

    saida = excluir_aluno.main(
        ["--quem", "ana@escola.com", "--confirmar", "--backup", str(tmp_path / "b.json")],
        perguntar=lambda _: "Ana",  # quase certo não basta
    )

    assert saida == 1
    assert "nao confere" in capsys.readouterr().out
    assert encontrar_aluno("ana@escola.com") is not None


def test_script_de_exclusao_grava_backup_antes_de_apagar(banco, tmp_path, capsys):
    from scripts import excluir_aluno

    _simular_cascade(banco, "aluno-2")
    backup = tmp_path / "bruno.json"

    saida = excluir_aluno.main(
        ["--quem", "bruno@escola.com", "--confirmar", "--backup", str(backup)],
        perguntar=lambda _: "Bruno Sá",
    )

    assert saida == 0
    assert encontrar_aluno("bruno@escola.com") is None
    # O backup é o que resta se a exclusão foi pedida por engano.
    assert json.loads(backup.read_text(encoding="utf-8"))["aluno"]["nome"] == "Bruno Sá"
    assert "Apagado" in capsys.readouterr().out


def test_sem_backup_a_exclusao_nao_segue(banco, capsys):
    from scripts import excluir_aluno

    saida = excluir_aluno.main(
        ["--quem", "ana@escola.com", "--confirmar", "--backup", "pasta/que/nao/existe/b.json"],
        perguntar=lambda _: "Ana Ribeiro",
    )

    assert saida == 1
    assert "Nada foi apagado" in capsys.readouterr().out
    assert encontrar_aluno("ana@escola.com") is not None


def test_script_com_aluno_inexistente_sai_com_erro(banco, capsys):
    from scripts import dados_do_aluno, excluir_aluno

    assert dados_do_aluno.main(["--quem", "ninguem@escola.com"]) == 1
    assert excluir_aluno.main(["--quem", "ninguem@escola.com", "--confirmar"]) == 1
    assert "Nenhum aluno encontrado" in capsys.readouterr().out
