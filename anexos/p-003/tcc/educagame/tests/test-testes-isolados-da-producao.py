"""A suíte roda longe da produção: nem o banco dos alunos, nem as chaves de IA.

Visto em 13/09/2026: seis linhas em estados_sessao, no Supabase de PRODUÇÃO,
com exatamente os dados de um teste do Laboratório, gravadas nos horários em
que a suíte rodou. `load_dotenv(override=True)` em
repositories/supabase_client.py e em services/ia/providers.py trocava os
valores de mentira do tests/conftest.py pelos do .env da máquina.

Se um destes testes falhar, NÃO rode a suíte de novo antes de entender por
quê: ela estaria lendo e gravando no banco dos alunos.
"""

from __future__ import annotations

import os


def test_o_banco_dos_testes_e_o_de_mentira():
    from repositories import supabase_client

    assert "example.supabase.co" in str(supabase_client.SUPABASE_URL or ""), (
        "a suíte está apontando para um Supabase de verdade"
    )


def test_nenhum_arquivo_le_o_env_por_cima_dos_testes():
    """Guarda para o próximo arquivo que precisar do .env.

    Os dois primeiros consertos (supabase_client e providers) não bastaram: a
    suíte inteira ainda recebia a chave de IA real, porque dois SCRIPTS também
    faziam `load_dotenv(override=True)` no import -- e um teste que importa o
    script carrega o .env para todos os testes seguintes.
    """
    import ast
    from pathlib import Path

    def _chama_com_override(arvore) -> bool:
        # Pela árvore, e não pelo texto: docstring e print que CITAM a chamada
        # (scripts/gerar_env_para_secret_file.py tem os dois) não contam.
        return any(
            isinstance(no, ast.Call)
            and getattr(no.func, "id", getattr(no.func, "attr", "")) == "load_dotenv"
            and any(k.arg == "override" and getattr(k.value, "value", False) is True for k in no.keywords)
            for no in ast.walk(arvore)
        )

    raiz = Path(__file__).resolve().parents[1]
    sem_trava = []
    for arquivo in raiz.rglob("*.py"):
        partes = arquivo.relative_to(raiz).parts
        if partes[0] in {".venv", "tests", ".claude"} or "site-packages" in partes:  # .claude: worktrees
            continue
        # utf-8-sig: há arquivo salvo com BOM, e o ast.parse recusa o U+FEFF.
        texto = arquivo.read_text(encoding="utf-8-sig", errors="replace")
        if "load_dotenv" not in texto:
            continue
        if _chama_com_override(ast.parse(texto)) and '"pytest" not in sys.modules' not in texto:
            sem_trava.append(str(arquivo.relative_to(raiz)))

    assert sem_trava == [], f"load_dotenv(override=True) sem a trava do pytest em: {sem_trava}"


def test_as_chaves_de_ia_dos_testes_sao_as_de_mentira():
    import services.ia.providers  # noqa: F401 -- o import é o que carregava o .env

    for chave in ("GROQ_API_KEY", "OPENROUTER_API_KEY"):
        # A comparação fica FORA do assert: dentro dele, o pytest imprime os
        # dois lados -- e o lado errado seria a chave de verdade, no log.
        de_mentira = os.environ.get(chave) == "test-key-for-unit-tests-only"
        assert de_mentira, f"{chave} veio do .env: a suíte poderia chamar a IA de verdade"


def test_nada_do_env_da_maquina_chega_na_suite():
    """Pega também o que o conftest não define.

    `criar_app()` fazia `load_dotenv()` SEM override: não trocava as chaves de
    mentira, mas trazia as que o conftest não define -- Gemini, Mistral,
    Cerebras, Hugging Face e a do Brevo, que manda e-mail de verdade.
    """
    from pathlib import Path

    from dotenv import dotenv_values

    import flask_app  # noqa: F401 -- cria o app, que é onde o .env era lido

    arquivo = Path(__file__).resolve().parents[1] / ".env"
    reais = {nome: valor for nome, valor in dotenv_values(arquivo).items() if valor} if arquivo.exists() else {}
    # Só os NOMES vão para a mensagem.
    vazados = sorted(nome for nome, valor in reais.items() if os.environ.get(nome) == valor)

    assert vazados == [], f"vieram do .env da máquina: {vazados}"


def test_o_secrets_toml_da_maquina_nao_chega_na_suite():
    """Com o streamlit carregado, ler_segredo consulta st.secrets.

    Sem a trava do tests/conftest.py, esta leitura trazia o secrets.toml
    inteiro para os.environ (ver o docstring de lá).
    """
    import tomllib
    from pathlib import Path

    import streamlit  # noqa: F401 -- é com ele em sys.modules que st.secrets entra em jogo

    from core.runtime_context import ler_segredo

    arquivo = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
    reais = {}
    if arquivo.exists():
        conteudo = tomllib.loads(arquivo.read_text(encoding="utf-8-sig"))
        reais = {nome: str(valor) for nome, valor in conteudo.items() if isinstance(valor, (str, int, float)) and str(valor)}
    so_no_secrets = next((nome for nome in reais if not os.environ.get(nome)), "EDUCAGAME_SO_NO_SECRETS")

    # Fora do assert, pelo mesmo motivo do teste das chaves: o pytest
    # imprimiria o valor lido.
    leu_da_maquina = ler_segredo(so_no_secrets) is not None
    vazados = sorted(nome for nome, valor in reais.items() if os.environ.get(nome) == valor)

    assert not leu_da_maquina, f"ler_segredo({so_no_secrets!r}) leu o secrets.toml da máquina"
    assert vazados == [], f"vieram do secrets.toml da máquina: {vazados}"
