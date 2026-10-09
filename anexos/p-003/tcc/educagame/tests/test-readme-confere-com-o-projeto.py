"""O README precisa ser cobrado, senão ele mente.

Por que este arquivo existe
---------------------------
O README ficou um mês sem tocar (`46c79ae`, 03/08) enquanto o projeto ganhou
um segundo frontend, quatro provedores de IA, dois modos de jogo e nove
migrations. Nada reclamou, porque documentação não roda.

O resultado não era "desatualizado" no sentido leve. Três coisas **quebravam**
para quem seguisse o texto:

1. `pip install -r requirements.txt` + `python flask_app.py` -- o
   `requirements.txt` virou o do Streamlit Cloud (que exige esse nome) e não
   instala Flask. Quem seguisse o passo a passo do README recebia
   `ModuleNotFoundError: No module named 'flask'` na primeira execução.
2. `README_ORDEM_EXECUCAO.txt` mandava aplicar cinco migrations com prefixo
   `20260427` -- arquivos que não existem mais. Travava no primeiro item.
3. `README_FLASK.md` mandava rodar `.\\venv\\Scripts\\python.exe`; a pasta no
   disco é `.venv`.

O mesmo aconteceu com o guia de acesso em PDF, e a lição foi a mesma: o texto
envelheceu porque não tinha fonte cobrada por teste. Lá a correção foi um
gerador com teste (`tests/test_guia_de_acesso.py`); aqui é este arquivo.

O que este arquivo NÃO faz
--------------------------
Não cobra prosa. Cobra só o que é verificável contra o repositório: caminhos
que precisam existir, comandos que precisam funcionar, números que precisam
ser verdade. Reescrever a introdução não quebra nada aqui -- de propósito.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
README = RAIZ / "README.md"
README_FLASK = RAIZ / "README_FLASK.md"
ORDEM_SQL = RAIZ / "README_ORDEM_EXECUCAO.txt"


def _texto(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _sem_acento(texto: str) -> str:
    forma = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in forma if not unicodedata.combining(c))


def _expandir_requirements(nome: str, vistos: set[str] | None = None) -> list[str]:
    """Resolve os `-r outro.txt` e devolve os pacotes de verdade."""
    vistos = vistos if vistos is not None else set()
    if nome in vistos:
        return []
    vistos.add(nome)

    caminho = RAIZ / nome
    if not caminho.exists():
        return []

    pacotes: list[str] = []
    for linha in _texto(caminho).splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("-r "):
            pacotes += _expandir_requirements(linha[3:].strip(), vistos)
        else:
            pacotes.append(re.split(r"[=<>!~\[]", linha)[0].strip().lower())
    return pacotes


def _blocos_bash(texto: str) -> list[str]:
    return re.findall(r"```(?:bash|powershell)\n(.*?)```", texto, re.DOTALL)


# ---------------------------------------------------------------------------
# Os comandos do README precisam instalar o que o comando seguinte importa.
# Este é o defeito que existia: o README instalava o Streamlit e mandava
# rodar o Flask.
# ---------------------------------------------------------------------------


def _pares_instala_e_roda(texto: str) -> list[tuple[str, str]]:
    """(arquivo de requirements, linha que executa algo) por bloco."""
    pares = []
    for bloco in _blocos_bash(texto):
        arquivos = re.findall(r"pip install -r ([\w.\-]+\.txt)", bloco)
        if not arquivos:
            continue
        for linha in bloco.splitlines():
            linha = linha.strip()
            if re.search(r"(python[\w.\\/]*\s+\S+\.py|streamlit run)", linha):
                pares.append((arquivos[-1], linha))
    return pares


def test_o_readme_tem_bloco_de_execucao():
    """Guarda: se alguém apagar os blocos, os testes abaixo ficam vazios e
    passariam sem provar nada."""
    pares = _pares_instala_e_roda(_texto(README))
    assert pares, "nenhum par 'pip install' + 'executar' no README -- os testes de comando ficariam vazios"
    assert len(pares) >= 2, f"esperado Flask e Streamlit, achei {len(pares)}: {pares}"


@pytest.mark.parametrize("readme", [README, README_FLASK], ids=["README.md", "README_FLASK.md"])
def test_o_que_o_readme_manda_instalar_contem_o_que_ele_manda_rodar(readme: Path):
    for arquivo, comando in _pares_instala_e_roda(_texto(readme)):
        pacotes = _expandir_requirements(arquivo)
        assert pacotes, f"{readme.name}: '{arquivo}' não existe ou está vazio"

        if "streamlit run" in comando:
            esperado = "streamlit"
        elif "flask_app.py" in comando:
            esperado = "flask"
        else:
            continue

        assert esperado in pacotes, (
            f"{readme.name}: manda '{comando.strip()}' depois de instalar '{arquivo}', "
            f"que não traz '{esperado}'. Quem seguir o passo a passo recebe ModuleNotFoundError."
        )


def test_os_arquivos_de_requirements_citados_existem():
    citados = set()
    for readme in (README, README_FLASK):
        citados |= set(re.findall(r"`?(requirements[\w.\-]*\.txt)`?", _texto(readme)))
    assert citados, "nenhum requirements citado -- teste vazio"
    for nome in sorted(citados):
        assert (RAIZ / nome).exists(), f"README cita '{nome}', que não existe"


# ---------------------------------------------------------------------------
# O diagrama de estrutura
# ---------------------------------------------------------------------------


def _caminhos_do_diagrama() -> list[str]:
    """Resolve a indentação: `banks/` aninhado sob `services/` é
    `services/banks`, não `banks` na raiz."""
    blocos = re.findall(r"```text\n(.*?)```", _texto(README), re.DOTALL)
    caminhos: list[str] = []
    pai_por_coluna: dict[int, str] = {}
    for bloco in blocos:
        for linha in bloco.splitlines():
            achado = re.search(r"[|`]-- ([\w./\-]+)", linha)
            if not achado:
                continue
            coluna = achado.start()
            bruto = achado.group(1)
            nome = bruto.rstrip("/")

            pais = [p for c, p in sorted(pai_por_coluna.items()) if c < coluna]
            completo = "/".join(pais + [nome]) if pais else nome
            caminhos.append(completo)

            # Só uma pasta pode ser pai do que vier abaixo. A barra está no
            # NOME, não no fim da linha -- cada linha termina em comentário.
            if bruto.endswith("/"):
                pai_por_coluna = {c: p for c, p in pai_por_coluna.items() if c < coluna}
                pai_por_coluna[coluna] = completo
    return caminhos


def test_todo_caminho_do_diagrama_existe():
    caminhos = _caminhos_do_diagrama()
    assert len(caminhos) >= 10, f"diagrama com {len(caminhos)} caminhos -- pouco demais, o teste ficaria fraco"

    faltando = [c for c in caminhos if not (RAIZ / c).exists()]
    assert not faltando, f"o diagrama do README mostra o que não existe: {faltando}"


def test_o_diagrama_cita_os_dois_frontends():
    """A omissão que existia: o diagrama mostrava só o Flask, como se o
    Streamlit não fosse parte do projeto."""
    caminhos = set(_caminhos_do_diagrama())
    for esperado in ("flask_app.py", "app.py", "web", "st/ui"):
        assert esperado in caminhos, f"'{esperado}' sumiu do diagrama do README"


# ---------------------------------------------------------------------------
# Números e versões
# ---------------------------------------------------------------------------


def test_a_versao_do_python_bate_com_o_runtime():
    runtime = _texto(RAIZ / "runtime.txt").strip()
    versao_real = re.search(r"python-(\d+\.\d+)", runtime)
    assert versao_real, f"runtime.txt ilegível: {runtime!r}"

    versao_readme = re.search(r"\*\*Python (\d+\.\d+)\*\*", _texto(README))
    assert versao_readme, "o README não diz mais qual Python"
    assert versao_readme.group(1) == versao_real.group(1), (
        f"README diz Python {versao_readme.group(1)}, runtime.txt diz {versao_real.group(1)}"
    )


def test_o_piso_de_testes_do_readme_e_verdade():
    """O README promete um PISO ('mais de N'), não um número exato: assim ele
    continua verdadeiro quando alguém acrescenta um teste, e só quebra se
    alguém apagar testes em massa ou inflar o número.

    A unidade é 'função de teste' porque é o que dá para contar sem chamar o
    pytest de dentro do pytest (a coleção completa leva ~7s). O número que o
    pytest reporta é maior, porque conta cada parametrização."""
    achado = re.search(r"mais de ([\d.]+) funções de teste", _texto(README))
    assert achado, "o README não promete mais um piso de funções de teste"
    piso = int(achado.group(1).replace(".", ""))
    assert piso >= 100, f"piso de {piso} é baixo demais para provar qualquer coisa"

    reais = 0
    for arquivo in (RAIZ / "tests").glob("test_*.py"):
        reais += len(re.findall(r"^def test_", _texto(arquivo), re.MULTILINE))

    assert reais >= piso, f"README promete mais de {piso} funções de teste; contei {reais}"


def test_os_provedores_de_ia_do_readme_existem_no_codigo():
    codigo = _texto(RAIZ / "services" / "ia" / "providers.py")
    texto = _texto(README)

    achado = re.search(r"cascata de \w+ provedores — ([^.]+?)\s*—", texto)
    assert achado, "o README não lista mais a cascata de provedores"

    anunciados = {p.strip().lower().replace(" ", "") for p in achado.group(1).split(",")}
    # Quem está de fato na cascata: um cliente por provedor de SDK, e o Gemini,
    # chamado por HTTP direto. Procurar só o NOME no arquivo não bastava: a nota
    # que explica a saída do Mistral e do Cerebras (08/10/2026) cita os dois.
    no_codigo = set(re.findall(r"^def _get_(\w+)_client\(", codigo, re.MULTILINE))
    no_codigo |= set(re.findall(r"^def _chamar_(\w+)_rest\(", codigo, re.MULTILINE))

    assert len(no_codigo) >= 3, f"a varredura do providers.py achou pouco: {no_codigo}"
    assert anunciados == no_codigo, f"README: {sorted(anunciados)}; código: {sorted(no_codigo)}"


def test_o_readme_nao_cita_sdk_que_nao_esta_instalado():
    """O rascunho deste README dizia `google-genai`; o Gemini é chamado por
    urllib, sem SDK. Anunciar dependência que não existe manda o leitor
    procurar código que não está lá."""
    instalados = set(_expandir_requirements("requirements_base.txt"))
    instalados |= set(_expandir_requirements("requirements_flask.txt"))
    instalados |= set(_expandir_requirements("requirements.txt"))

    bloco = re.search(r"- \*\*IA:\*\*(.+)", _texto(README))
    assert bloco, "a linha de IA sumiu do README"

    citados = re.findall(r"`([\w\-]+)`", bloco.group(1))
    assert citados, "a linha de IA não cita mais nenhum pacote"
    for pacote in citados:
        assert pacote.lower() in instalados, (
            f"README cita o pacote '{pacote}' na linha de IA, mas ele não está em nenhum requirements"
        )


# ---------------------------------------------------------------------------
# README_ORDEM_EXECUCAO.txt -- o que travava era isto
# ---------------------------------------------------------------------------


def test_a_ordem_de_execucao_nao_cita_migration_inexistente():
    texto = _texto(ORDEM_SQL)
    citadas = re.findall(r"(\d{14}_[\w\-]+\.sql)", texto)
    assert citadas, "nenhuma migration citada -- teste vazio"

    reais = {p.name for p in (RAIZ / "supabase" / "migrations").glob("*.sql")}
    # A versão antiga listava cinco arquivos 20260427* que já não existiam.
    # Citar um arquivo pelo nome só é seguro se ele estiver lá.
    fantasmas = [c for c in citadas if c not in reais]
    assert not fantasmas, f"README_ORDEM_EXECUCAO cita migrations que não existem: {fantasmas}"


def test_a_ordem_de_execucao_diz_a_verdade_sobre_rls():
    """O arquivo dizia 'DEV MODE, com RLS desativado' e mandava criar policies
    'antes de ativar RLS'. O bootstrap faz o oposto: habilita RLS em todas as
    tabelas e não cria policy nenhuma (negação total, de propósito). Errar
    isso no texto convida alguém a 'consertar' abrindo o banco."""
    bootstrap = _texto(RAIZ / "supabase" / "migrations" / "20260803120000_bootstrap.sql").lower()
    assert "enable row level security" in bootstrap, (
        "o bootstrap não habilita mais RLS -- então este teste e o texto do "
        "README_ORDEM_EXECUCAO precisam ser revistos juntos"
    )

    texto = _texto(ORDEM_SQL).lower()
    assert "rls esta habilitado" in texto or "rls está habilitado" in texto, (
        "README_ORDEM_EXECUCAO não afirma mais que o RLS está habilitado"
    )

    # O dano real não era a frase "RLS desativado" -- o arquivo hoje a cita de
    # propósito, para dizer que estava errada. Era a INSTRUÇÃO que vinha junto:
    # "crie policies antes de ativar RLS". Ela descreve um banco aberto que
    # precisa ser fechado, quando o banco já está fechado; segui-la abre.
    for instrucao in ("antes de ativar rls", "antes de ativar o rls"):
        assert instrucao not in texto, (
            f"README_ORDEM_EXECUCAO voltou a mandar agir 'antes de ativar RLS' -- "
            f"o RLS já está ativo, e essa instrução leva a abrir o banco"
        )


# ---------------------------------------------------------------------------
# Modos de jogo: o README listava 6 de 8
# ---------------------------------------------------------------------------


def test_o_readme_lista_todos_os_modos_registrados_no_flask():
    registrados = set(re.findall(r'url_prefix="/([\w\-]+)"', _texto(RAIZ / "flask_app.py")))
    assert len(registrados) >= 8, f"achei {len(registrados)} blueprints com prefixo: {registrados}"

    # Rotas de apoio, não modos de jogo. "ajuda" entrou aqui em 09/09 e este
    # teste foi quem avisou -- ele reprovou o blueprint novo por não estar na
    # lista de modos do README, que é exatamente o trabalho dele.
    modos = registrados - {"perfil", "professor", "progresso", "ajuda", "privacidade"}

    # Sem acento dos dois lados: o teste cobra o MODO estar documentado, não a
    # grafia. Escrever "Oraculo" ou "Oráculo" é escolha do texto.
    texto = _sem_acento(_texto(README))
    apelidos = {"boss-rush": "boss rush", "escape-room": "escape room"}
    faltando = [m for m in sorted(modos) if apelidos.get(m, m) not in texto]
    assert not faltando, f"modos que existem no app e não estão no README: {faltando}"


# ====================== O NOME DO PRODUTO ======================


def test_o_nome_do_produto_e_um_so():
    """Ele aparecia em TRÊS grafias: `EducaGame AI` nos READMEs, `EducaGame
    IA` na tela e `EducaGames IA` no alt da logo.

    Num TG isso não é detalhe: o texto acadêmico cita o sistema pelo nome, e
    três nomes viram três produtos aos olhos de quem lê a banca. Decidido em
    09/09/2026: fica **EducaGame IA**.
    """
    import re as _re

    erradas = {"EducaGame AI", "EducaGames IA", "EducaGames AI", "Educagame IA"}
    arquivos = [
        RAIZ / "README.md",
        RAIZ / "README_FLASK.md",
        RAIZ / "README_ORDEM_EXECUCAO.txt",
        RAIZ / "st" / "ui" / "home_st.py",
        RAIZ / "core" / "ajuda.py",
    ]

    for caminho in arquivos:
        if not caminho.exists():
            continue
        texto = _texto(caminho)
        for grafia in erradas:
            assert grafia not in texto, f"{caminho.name} voltou a escrever '{grafia}'"

    # E a grafia certa continua aparecendo em algum lugar -- senão este teste
    # passaria num repositório que simplesmente apagou o nome.
    assert "EducaGame IA" in _texto(RAIZ / "README.md")


def test_nenhum_alt_escreve_o_nome_do_produto_errado():
    """O alt é o que o leitor de tela fala em voz alta: era ali que estava a
    terceira grafia ("EducaGames IA", na abertura do Streamlit).

    Essa abertura saiu em 08/10/2026: procurava uma logo que não existia
    desde b595c2d e nunca aparecia. A logo que sobrou, a da abertura do
    Flask, é decorativa (aria-hidden, alt vazio). A regra continua valendo
    para qualquer imagem que volte a pôr o nome no alt.
    """
    import re as _re

    fontes = [
        *sorted((RAIZ / "web" / "templates").rglob("*.html")),
        *sorted((RAIZ / "st").rglob("*.py")),
        RAIZ / "app.py",
    ]
    alts = [alt for caminho in fontes for alt in _re.findall(r'alt="([^"]*)"', _texto(caminho))]

    # A varredura enxerga as imagens de verdade -- senão passaria lendo nada.
    assert alts, "nenhum alt encontrado: a varredura não está lendo as telas"
    for alt in alts:
        if "educa" in alt.lower():
            assert alt == "EducaGame IA", alt
