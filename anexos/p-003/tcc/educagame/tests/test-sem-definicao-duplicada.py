"""Nenhum modulo pode definir o mesmo nome duas vezes.

MELHORIA: core/config.py tinha 10 funcoes definidas DUAS vezes -- sobra da
unificacao dos frontends, quando eu extrai um bloco maior do que precisava
da branch StreamLit. As copias eram identicas, entao nada quebrou; o
problema e a armadilha: a segunda definicao vence em silencio, e quem
editasse a primeira veria a mudanca simplesmente nao acontecer.
"""

from __future__ import annotations

import ast
import collections
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
# .claude/ guarda os worktrees do Claude Code: copias inteiras do projeto,
# que o git ignora. Varrer la faria cada definicao aparecer varias vezes.
IGNORAR = {"__pycache__", ".venv", "_backup-tema-original", "tests", ".claude"}


def _modulos() -> list[Path]:
    return [
        arquivo
        for arquivo in sorted(RAIZ.rglob("*.py"))
        if not (IGNORAR & set(arquivo.parts))
    ]


@pytest.mark.parametrize("arquivo", _modulos(), ids=lambda p: p.name)
def test_nao_define_o_mesmo_nome_duas_vezes(arquivo: Path):
    try:
        arvore = ast.parse(arquivo.read_text(encoding="utf-8-sig", errors="ignore"))
    except SyntaxError:
        pytest.skip("arquivo nao compila (script auxiliar)")

    # so o nivel de topo: metodo com nome repetido em classes diferentes e
    # normal, e sobrecarga dentro de if/else tambem.
    contagem = collections.Counter(
        no.name
        for no in arvore.body
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    repetidos = {nome: n for nome, n in contagem.items() if n > 1}

    assert not repetidos, (
        f"{arquivo.name} define o mesmo nome mais de uma vez: {repetidos}. "
        "A ultima definicao vence em silencio -- editar a primeira nao faz efeito."
    )


def _onde_e_definida(nome: str) -> list[str]:
    """Em quais modulos existe um `def <nome>` no nivel de topo."""
    definicoes = []
    for arquivo in _modulos():
        try:
            arvore = ast.parse(arquivo.read_text(encoding="utf-8-sig", errors="ignore"))
        except SyntaxError:
            continue
        for no in arvore.body:
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
                definicoes.append(arquivo.relative_to(RAIZ).as_posix())
    return definicoes


def test_gerar_slug_existe_uma_vez_so():
    # MELHORIA: vivia duplicada em services/professor_service.py e
    # st/ui/admin_st.py -- mesma logica escrita de dois jeitos. Duas copias
    # divergem na primeira vez que alguem mexe numa so, e o slug e o que
    # identifica a escola na URL: divergir ali quebra o link da turma.
    assert _onde_e_definida("gerar_slug") == ["services/professor_service.py"]


def test_gerar_json_ia_existe_uma_vez_so():
    # MELHORIA: vivia duplicada, IDENTICA, em services/ia/enigma.py e
    # services/ia_service.py -- 18 linhas com sete parametros e seus
    # defaults. Cada copia servia metade do sistema: Oraculo e Laboratorio
    # de um lado, RPG e ENEM do outro.
    #
    # O perigo aqui nao e divergir na logica (nao ha logica: as duas so
    # repassam para chamar_ia). E divergir na ASSINATURA. Bastava alguem
    # acrescentar um parametro numa delas -- outro timeout, outra
    # temperatura -- para metade do sistema seguir sem ele, funcionando e
    # ignorando a configuracao nova, sem nada no log.
    #
    # Agora mora ao lado do chamar_ia que ela repassa.
    assert _onde_e_definida("gerar_json_ia") == ["services/ia/providers.py"]


def test_gerar_json_ia_e_a_mesma_funcao_em_todo_lugar():
    # O teste acima olha o fonte; este olha o que roda. Os quatro modulos
    # que pedem questao para a IA tem que estar chamando o MESMO objeto.
    import services.enem_service
    import services.ia.enigma
    import services.ia_service
    import services.rpg_service

    referencias = {
        "ia_service": services.ia_service.gerar_json_ia,
        "enigma": services.ia.enigma.gerar_json_ia,
        "rpg_service": services.rpg_service.gerar_json_ia,
        "enem_service": services.enem_service.gerar_json_ia,
    }

    assert len(set(referencias.values())) == 1, {
        nome: f.__module__ for nome, f in referencias.items()
    }


def test_backup_do_tema_nao_volta_para_o_repositorio():
    # Eram 4 arquivos .bak versionados. O historico do git ja guarda isso;
    # copia manual so envelhece e confunde quem procura o template certo.
    assert not (RAIZ / "_backup-tema-original").exists()
