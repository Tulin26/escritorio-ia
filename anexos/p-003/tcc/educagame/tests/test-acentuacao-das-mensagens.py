"""O que chega à tela tem acento; o que é chave, não.

MELHORIA: as mensagens em Python estavam sem acento — *"Peca o codigo"*,
*"Codigo incorreto"*, *"Sua sessao expirou"*, *"Usuario/e-mail ou senha
invalidos"*. Herança de quando isso era só comentário de código, onde a casa
escreve sem acento de propósito. Nos templates as mesmas ideias apareciam
acentuadas, então a mesma tela misturava as duas grafias.

**A parte que exige cuidado é a outra metade.** Boa parte das strings sem
acento neste projeto é chave, não texto: `"Matematica"` e `"Educacao Fisica"`
são o nome normalizado da matéria (`core/config.py`), `"Facil"/"Medio"/
"Dificil"` são o valor que vai para a sessão e para o log, e
`core/text_cleanup.py` casa padrões contra texto já sem acento. Acentuar
qualquer uma delas não é ortografia — é mudar comportamento em silêncio.

A separação que já existia no projeto e virou a regra aqui: **a chave fica
como está e ganha um rótulo ao lado** (`MATERIAS_COM_ACENTO`, `LABEL_AREA`,
e agora `LABEL_DIFICULDADE`).

Este arquivo prende os dois lados: mensagem sem acento reprova, e chave
acentuada também.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Arquivos cujas strings de uma linha são, na prática, texto de tela.
# Deliberadamente fora: core/config.py e core/text_cleanup.py (chave e padrão
# de comparação), repositories/* e core/diagnostico_config.py (log, não tela),
# e os bancos offline de questões — ver o teste no fim deste arquivo.
def _arquivos_de_mensagem() -> list[str]:
    caminhos = sorted(RAIZ.glob("web/routes/*.py")) + sorted(RAIZ.glob("st/ui/*.py"))
    caminhos += [
        RAIZ / "services/aluno_auth_service.py",
        RAIZ / "services/guildas_service.py",
        RAIZ / "services/gamification_service.py",
    ]
    return [str(c.relative_to(RAIZ)).replace("\\", "/") for c in caminhos if c.name != "__init__.py"]


ARQUIVOS_DE_MENSAGEM = _arquivos_de_mensagem()

# Palavra sem acento -> como se escreve. Lista curta e de alto sinal: só
# palavras que, em português, SEMPRE levam acento. "energia", "senha" e
# "escola" não entram aqui justamente por não levarem.
#
# Os nomes de matéria ("matematica", "fisica", "ciencias", "educacao") ficam
# de fora por outro motivo: neste projeto eles são, na esmagadora maioria,
# CHAVE -- "Matematica e suas Tecnologias" é a chave de AREAS_ENEM, e o
# acento mora no rótulo ao lado. Cobrá-los aqui reprovaria o código certo. O
# preço é que uma mensagem nova escrita com "Matematica" passa; o rótulo
# continua coberto pelos testes de chave mais abaixo.
ERRADAS = {
    "nao": "não",
    "sao": "são",
    "voce": "você",
    "usuario": "usuário",
    "usuarios": "usuários",
    "codigo": "código",
    "sessao": "sessão",
    "invalido": "inválido",
    "invalidos": "inválidos",
    "invalida": "inválida",
    "valido": "válido",
    "peca": "peça",
    "faca": "faça",
    "ja": "já",
    "questao": "questão",
    "questoes": "questões",
    "materia": "matéria",
    "materias": "matérias",
    "proximo": "próximo",
    "proxima": "próxima",
    "ultimo": "último",
    "unica": "única",
    "confirmacao": "confirmação",
    "redefinicao": "redefinição",
    "identificacao": "identificação",
    "configuracao": "configuração",
    "explicacao": "explicação",
    "explicacoes": "explicações",
    "possivel": "possível",
    "disponivel": "disponível",
    "relatorio": "relatório",
    "laboratorio": "laboratório",
    "temporaria": "temporária",
    "serie": "série",
    "periodo": "período",
    "servicos": "serviços",
    "saida": "saída",
    "coracao": "coração",
    "areas": "áreas",
    "diagnostico": "diagnóstico",
    "historico": "histórico",
    "sequencia": "sequência",
    "nivel": "nível",
    "niveis": "níveis",
    "tambem": "também",
    "ate": "até",
    "apos": "após",
    "alem": "além",
    "entao": "então",
    "opcao": "opção",
    "opcoes": "opções",
    "pagina": "página",
    "numero": "número",
    "numeros": "números",
    "tres": "três",
    "duvida": "dúvida",
    "duvidas": "dúvidas",
    "analise": "análise",
    "grafico": "gráfico",
    "graficos": "gráficos",
    "cenario": "cenário",
    "calculo": "cálculo",
    "formula": "fórmula",
    "memoria": "memória",
    "padrao": "padrão",
    "sera": "será",
    "serao": "serão",
    "ninguem": "ninguém",
    "alguem": "alguém",
    "minimo": "mínimo",
    "maximo": "máximo",
    "pratica": "prática",
    "logica": "lógica",
    "obrigatorio": "obrigatório",
    "versao": "versão",
    "unico": "único",
    "ultima": "última",
    "media": "média",
    "medias": "médias",
    "publico": "público",
    "basico": "básico",
    "automatico": "automático",
    "experiencia": "experiência",
    "referencia": "referência",
    "silaba": "sílaba",
    "estatisticas": "estatísticas",
}

PALAVRA = re.compile(r"[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ]*")

# Identificador, caminho de rota, nome de campo de formulário, chave de dicionário:
# tudo isso é string e nada disso é frase. Sem este filtro o teste reprovaria
# "usuario_id", "/reenviar-confirmacao" e "ra_identificacao" -- que estão certos
# assim e cuja "correção" quebraria sessão, URL e formulário de uma vez.
IDENTIFICADOR = re.compile(r"^[a-z0-9_./<>:-]+$")


def _parece_frase(texto: str) -> bool:
    return " " in texto.strip() and not IDENTIFICADOR.match(texto.strip())


def _strings_de_uma_linha(caminho: Path) -> list[tuple[int, str]]:
    """Strings do arquivo, sem docstring e sem prompt de IA.

    Docstring e prompt vivem em aspas triplas neste projeto, e nenhum dos dois
    chega à tela: docstring é para quem lê o código, prompt é para o modelo.
    Ficar de fora evita reprovar texto que está certo do jeito que está.
    """
    fonte = caminho.read_text(encoding="utf-8-sig")
    linhas = fonte.split("\n")
    achados = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Constant) or not isinstance(no.value, str):
            continue
        if no.lineno != no.end_lineno:
            continue
        trecho = linhas[no.lineno - 1]
        if '"""' in trecho or "'''" in trecho:
            continue
        achados.append((no.lineno, no.value))
    return achados


@pytest.mark.parametrize("relativo", ARQUIVOS_DE_MENSAGEM)
def test_mensagem_de_tela_nao_pode_estar_sem_acento(relativo):
    caminho = RAIZ / relativo
    faltando = []
    for linha, texto in _strings_de_uma_linha(caminho):
        if not _parece_frase(texto):
            continue
        for palavra in PALAVRA.findall(texto):
            certa = ERRADAS.get(palavra.lower())
            if certa:
                faltando.append(f"{relativo}:{linha}  {palavra!r} -> {certa!r}  | {texto[:70]}")

    assert not faltando, "mensagem sem acento:\n  " + "\n  ".join(faltando)


def test_a_varredura_realmente_enxerga_as_mensagens():
    # Sem isto, um erro no filtro faria o teste acima passar comparando nada.
    # Escolhida uma frase que existe e é longa o bastante para não sumir.
    textos = [t for _, t in _strings_de_uma_linha(RAIZ / "web/routes/auth_fla.py") if _parece_frase(t)]

    assert len(textos) >= 8, f"varredura suspeita: achou so {len(textos)} frases"
    assert any("senha" in t for t in textos)
    # e o filtro tem que continuar deixando os identificadores de fora
    assert not _parece_frase("usuario_id")
    assert not _parece_frase("/reenviar-confirmacao")
    assert _parece_frase("As senhas não coincidem.")


# ====================== A OUTRA METADE: CHAVE NÃO SE ACENTUA ======================


def test_dificuldade_e_chave_sem_acento_com_rotulo_ao_lado():
    # As duas telas mostravam a chave crua, então o aluno lia "Facil" e
    # "Dificil" na própria lista de escolha. O acento foi para o rótulo; a
    # chave continua entrando na sessão e no log como sempre entrou.
    from services.enem_service import DIFICULDADES, LABEL_DIFICULDADE, exibir_dificuldade

    assert DIFICULDADES == ["Facil", "Medio", "Dificil"], "a chave mudou; sessão e log mudam junto"
    assert set(LABEL_DIFICULDADE) == set(DIFICULDADES), "todo valor precisa de rótulo"
    assert exibir_dificuldade("Facil") == "Fácil"
    assert exibir_dificuldade("Medio") == "Médio"
    assert exibir_dificuldade("Dificil") == "Difícil"
    # valor desconhecido não pode virar vazio na tela
    assert exibir_dificuldade("Extremo") == "Extremo"


def test_area_e_materia_continuam_sendo_chave_sem_acento():
    from core.config import MATERIAS_COM_ACENTO, exibir_materia
    from services.enem_service import AREAS_ENEM, LABEL_AREA

    assert "Matematica e suas Tecnologias" in AREAS_ENEM
    assert LABEL_AREA["Matematica e suas Tecnologias"] == "Matemática"
    assert exibir_materia("Educacao Fisica") == MATERIAS_COM_ACENTO["Educacao Fisica"]
    assert "í" in exibir_materia("Fisica"), "o rótulo é que carrega o acento"


def test_o_texto_normalizado_nao_ganhou_acento():
    # core/text_cleanup.py casa padrões contra texto JÁ sem acento. Um acento
    # aqui não erra alto: o padrão simplesmente para de casar, em silêncio.
    from core import text_cleanup

    fonte = (RAIZ / "core/text_cleanup.py").read_text(encoding="utf-8-sig")
    assert "velocidade media" in fonte, "padrão de comparação foi acentuado"
    assert hasattr(text_cleanup, "aplicar_acentos_pt")


# ====================== SEM CÓPIA DIVERGENTE ======================


def test_o_nome_da_guilda_vem_de_um_lugar_so():
    # As duas frases de fallback ("Série não informada" / "Período não
    # informado") existiam iguais no serviço e na tela do Streamlit. Acentuar
    # só uma faria os dois frontends montarem nomes de guilda diferentes para
    # o mesmo aluno -- a mesma divergência silenciosa de "esta série é de
    # Ensino Médio?", que estava escrita em cinco lugares.
    #
    # Depois disso a tela perdeu o placar inteiro para o serviço, então ela
    # nem chama mais guilda_de_aluno diretamente -- quem chama é
    # montar_guildas. A garantia que importa continua a mesma: não existir
    # cópia. Ver tests/test_placar_de_guildas.py.
    from services.guildas_service import guilda_de_aluno

    tela = (RAIZ / "st/ui/tela_guildas_st.py").read_text(encoding="utf-8-sig")

    assert "def _guilda_de_aluno" not in tela, "a cópia voltou"
    assert "Série não informada" not in tela, "a frase de fallback voltou para a tela"
    assert guilda_de_aluno({}) == "Série não informada - Período não informado"


# ====================== OS TEMPLATES ======================

# O texto que mais aparece nao esta em Python: esta no HTML. A varredura de
# .py deu tudo verde e a tela de login continuava com "Usuario ou e-mail" e
# "Nao recebeu o e-mail de confirmacao?" -- foi o navegador que mostrou.
JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
COMENTARIO_HTML = re.compile(r"<!--.*?-->", re.S)
SCRIPT_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
TAG = re.compile(r"<[^>]+>", re.S)
# placeholder/title/alt/aria-label aparecem para quem le a tela. "value" fica
# de fora de proposito: e chave de formulario -- value="analises" e a aba do
# painel, cujo titulo visivel ja e "Analises" com acento.
ATRIBUTO_VISIVEL = re.compile(r'\b(?:placeholder|title|alt|aria-label)\s*=\s*"([^"]*)"', re.I)


def _texto_visivel(caminho: Path) -> str:
    bruto = caminho.read_text(encoding="utf-8-sig")
    corpo = SCRIPT_STYLE.sub(" ", bruto)
    corpo = COMENTARIO_HTML.sub(" ", corpo)
    corpo = TAG.sub(" ", corpo)
    atributos = " ".join(ATRIBUTO_VISIVEL.findall(bruto))
    return JINJA.sub(" ", corpo + " " + atributos)


def _templates() -> list[Path]:
    return sorted((RAIZ / "web" / "templates").glob("*.html"))


@pytest.mark.parametrize("caminho", _templates(), ids=lambda c: c.name)
def test_template_nao_pode_mostrar_texto_sem_acento(caminho):
    faltando = sorted(
        {
            f"{palavra!r} -> {ERRADAS[palavra.lower()]!r}"
            for palavra in PALAVRA.findall(_texto_visivel(caminho))
            if palavra.lower() in ERRADAS
        }
    )

    assert not faltando, f"{caminho.name}: " + ", ".join(faltando)


def test_a_varredura_de_template_realmente_le_o_texto():
    # Sem isto, um erro nas expressoes acima faria os testes de template
    # passarem comparando string vazia.
    assert len(_templates()) > 10
    login = _texto_visivel(RAIZ / "web/templates/login.html")

    assert "Usuário ou e-mail" in login
    assert "csrf_token" not in login, "Jinja vazou para o texto visivel"
    assert "<form" not in login, "tag vazou para o texto visivel"


def test_o_filtro_de_dificuldade_esta_ligado_nos_templates(client):
    # O rótulo só chega à tela se o filtro estiver registrado no app. Sem
    # este teste, remover a linha de registro passaria despercebido ate
    # alguem abrir o simulado e tomar um erro de template.
    from services.enem_service import DIFICULDADES

    with client.application.test_request_context("/"):
        saida = client.application.jinja_env.from_string(
            '{% for d in ds %}<option value="{{ d }}">{{ d | dificuldade_label }}</option>{% endfor %}'
        ).render(ds=DIFICULDADES)

    assert 'value="Facil">Fácil<' in saida
    assert 'value="Medio">Médio<' in saida
    assert 'value="Dificil">Difícil<' in saida


@pytest.mark.parametrize("template", ["enem.html", "boss_rush.html"])
def test_as_duas_telas_usam_o_rotulo_e_nao_a_chave(template):
    html = (RAIZ / "web" / "templates" / template).read_text(encoding="utf-8-sig")

    assert html.count("| dificuldade_label") == 2, "sobrou dificuldade crua na tela"
    assert 'value="{{ dificuldade }}"' in html, "o value tem que continuar sendo a chave"
