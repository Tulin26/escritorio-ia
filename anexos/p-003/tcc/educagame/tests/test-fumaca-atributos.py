"""Procura `modulo.atributo` nas telas que nao existe no modulo importado.

MELHORIA: test_fumaca_importacoes.py so pega o que quebra no IMPORT. Uma
chamada em runtime passa batida ate o aluno chegar naquela tela.

Foi assim que gerar_recompensas_vitoria quase se perdeu ao unificar os dois
frontends: st/ui/tela_rpg_st.py a chama dentro do fluxo de vitoria, nao no
topo do arquivo, entao todos os modulos importavam sem erro e o RPG do
Streamlit so quebraria no instante em que um aluno vencesse uma fase.

O teste le o codigo (AST), acha os `apelido.atributo` onde `apelido` e um
modulo compartilhado importado no arquivo, e cobra que o atributo exista.
Isso cobre a remocao de funcao compartilhada -- o risco que sobra quando as
duas interfaces dividem core/, services/ e repositories/.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

PASTAS_DE_INTERFACE = ["st/ui", "ui", "web/routes"]
PACOTES_COMPARTILHADOS = ("core", "services", "repositories")


def _arquivos_de_interface() -> list[Path]:
    encontrados: list[Path] = []
    for pasta in PASTAS_DE_INTERFACE:
        raiz_pasta = RAIZ / pasta
        if not raiz_pasta.is_dir():
            continue
        encontrados.extend(
            arq for arq in sorted(raiz_pasta.glob("*.py")) if arq.stem != "__init__"
        )
    return encontrados


ARQUIVOS = _arquivos_de_interface()


def _apelidos_de_modulo(arvore: ast.Module) -> dict[str, str]:
    """`import services.rpg_service as rpg_engine` -> {"rpg_engine": "services.rpg_service"}."""
    apelidos: dict[str, str] = {}
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Import):
            continue
        for alias in no.names:
            if alias.name.split(".")[0] in PACOTES_COMPARTILHADOS:
                apelidos[alias.asname or alias.name.split(".")[0]] = alias.name
    return apelidos


def _modulos_injetados() -> dict[str, str]:
    """Descobre modulo compartilhado que chega na tela como ARGUMENTO.

    app.py faz `import services.rpg_service as rpg_engine` e passa
    `rpg_engine=rpg_engine` para a tela. La dentro, `rpg_engine` e um
    parametro -- nao ha import nenhum no arquivo, e por isso a checagem por
    apelido local nao enxergava justamente o caso da gerar_recompensas_vitoria.
    Lendo quem injeta, o parametro volta a ter origem conhecida.
    """
    entrada = RAIZ / "app.py"
    if not entrada.is_file():
        return {}
    arvore = ast.parse(entrada.read_text(encoding="utf-8-sig"), filename=str(entrada))
    locais = _apelidos_de_modulo(arvore)
    injetados: dict[str, str] = {}
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        for argumento in no.keywords:
            if argumento.arg and isinstance(argumento.value, ast.Name):
                modulo = locais.get(argumento.value.id)
                if modulo:
                    injetados[argumento.arg] = modulo
    return injetados


MODULOS_INJETADOS = _modulos_injetados()


def test_encontrou_arquivos_para_cobrir():
    assert ARQUIVOS, f"nenhum arquivo de interface encontrado em {RAIZ}"


def test_descobriu_os_modulos_injetados_por_argumento():
    # Se app.py existe, ele injeta pelo menos db/report/rpg_engine. Sem isto,
    # uma mudanca na forma de injetar tornaria a checagem silenciosamente
    # inutil para as telas do Streamlit.
    if not (RAIZ / "app.py").is_file():
        pytest.skip("frontend Streamlit ausente nesta branch")

    assert MODULOS_INJETADOS, "nenhum modulo injetado por argumento foi reconhecido"


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda p: p.name)
def test_atributos_de_modulo_compartilhado_existem(arquivo: Path):
    # utf-8-sig: alguns arquivos do Streamlit comecam com BOM.
    arvore = ast.parse(arquivo.read_text(encoding="utf-8-sig"), filename=str(arquivo))
    # O import local vence o injetado: se o arquivo importa o modulo ele
    # mesmo, e essa a origem.
    apelidos = {**MODULOS_INJETADOS, **_apelidos_de_modulo(arvore)}
    if not apelidos:
        pytest.skip("nao importa nem recebe modulo compartilhado")

    quebrados = []
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name)):
            continue
        nome_modulo = apelidos.get(no.value.id)
        if not nome_modulo:
            continue
        try:
            modulo = importlib.import_module(nome_modulo)
        except Exception as erro:  # noqa: BLE001
            quebrados.append(f"linha {no.lineno}: {nome_modulo} nao importa ({erro})")
            continue
        if not hasattr(modulo, no.attr):
            quebrados.append(f"linha {no.lineno}: {nome_modulo}.{no.attr} nao existe")

    assert not quebrados, (
        f"{arquivo.name} chama o que nao existe:\n  "
        + "\n  ".join(quebrados)
        + "\nSe o nome sumiu de core/ ou services/, provavelmente foi removido "
        "por parecer sem uso no OUTRO frontend."
    )
