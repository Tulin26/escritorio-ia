"""Nenhuma animacao pode ser usada sem existir, e nenhum conteudo pode
depender de animacao para ficar visivel.

MELHORIA: a tela "Escolha sua escola" era uma TELA PRETA. O flask.css
mandava animar com school-splash-hide, school-entry-reveal e
school-logo-pulse, e os tres @keyframes nunca existiram em lugar nenhum do
projeto. CSS nao reclama de animacao inexistente: ele simplesmente nao
anima. Como a splash so sumia por animacao e a lista de escolas so aparecia
por animacao, o resultado foi a splash cobrindo a tela para sempre com a
lista invisivel embaixo.

Ficou escondido por meses porque havia UMA escola cadastrada: nesse caso a
propria pagina redireciona sozinha depois de 2,85s e ninguem chegava a
precisar enxergar a lista. Bastou cadastrar a segunda escola para o
redirect deixar de acontecer e a tela preta aparecer.

Sao duas regras aqui, e a segunda importa mais que a primeira: mesmo com o
@keyframes no lugar, conteudo que comeca em "opacity: 0" e depende de uma
animacao para voltar a aparecer some de vez se a animacao falhar por
qualquer motivo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PASTAS_CSS = [RAIZ / "web" / "static" / "css", RAIZ / "core" / "estilos"]

# "animation: nome 0.75s ease" / "animation-name: nome"
_ANIMACAO = re.compile(r"animation(?:-name)?\s*:\s*([^;}]+)[;}]")
_KEYFRAMES = re.compile(r"@keyframes\s+([A-Za-z_][\w-]*)")

# Palavras que aparecem no atalho "animation:" e NAO sao o nome da animacao.
_NAO_E_NOME = {
    "none", "initial", "inherit", "unset", "revert",
    "linear", "ease", "ease-in", "ease-out", "ease-in-out", "step-start", "step-end",
    "normal", "reverse", "alternate", "alternate-reverse",
    "forwards", "backwards", "both",
    "running", "paused", "infinite",
}


def _arquivos_css() -> list[Path]:
    arquivos: list[Path] = []
    for pasta in PASTAS_CSS:
        if pasta.is_dir():
            arquivos += sorted(pasta.glob("*.css"))
    return arquivos


def _nomes_de_animacao(css: str) -> set[str]:
    nomes: set[str] = set()
    for valor in _ANIMACAO.findall(css):
        for parte in valor.split(","):
            for token in parte.split():
                token = token.strip()
                if not token or token.lower() in _NAO_E_NOME:
                    continue
                # duracao, atraso, contagem, cubic-bezier(...) etc.
                if re.match(r"^[\d.]+m?s$", token) or re.match(r"^[\d.]+$", token):
                    continue
                if "(" in token:
                    continue
                if re.match(r"^[A-Za-z_][\w-]*$", token):
                    nomes.add(token)
                    break  # o nome e o primeiro token que sobra
    return nomes


def test_ha_css_para_conferir():
    assert _arquivos_css(), "nenhuma folha de estilo encontrada"


@pytest.mark.parametrize("arquivo", _arquivos_css(), ids=lambda p: p.name)
def test_toda_animacao_usada_existe(arquivo: Path):
    css = arquivo.read_text(encoding="utf-8")
    usadas = _nomes_de_animacao(css)
    definidas = set(_KEYFRAMES.findall(css))

    faltando = sorted(usadas - definidas)

    assert not faltando, (
        f"{arquivo.name} manda animar com {faltando}, e esse @keyframes nao existe. "
        "O CSS nao reclama: ele so nao anima -- e o que dependia da animacao "
        "some da tela."
    )


@pytest.mark.parametrize("arquivo", _arquivos_css(), ids=lambda p: p.name)
def test_todo_keyframes_definido_e_usado(arquivo: Path):
    # O outro lado: keyframes orfao e sinal de que alguem renomeou a
    # animacao num lugar so.
    css = arquivo.read_text(encoding="utf-8")
    orfaos = sorted(set(_KEYFRAMES.findall(css)) - _nomes_de_animacao(css))

    assert not orfaos, f"{arquivo.name} define {orfaos} e nunca usa"


def test_a_lista_de_escolas_nao_depende_de_animacao_para_aparecer():
    # A regra que importa: o estado NATURAL da secao tem que ser visivel.
    # A animacao pode escondê-la durante o atraso (fill mode "backwards"),
    # nunca ser a unica coisa que a traz de volta.
    css = (RAIZ / "web" / "static" / "css" / "flask.css").read_text(encoding="utf-8")
    bloco = re.search(r"\.school-entry-delayed\s*\{([^}]*)\}", css)

    assert bloco, "regra .school-entry-delayed sumiu"
    corpo = bloco.group(1)

    assert not re.search(r"opacity\s*:\s*0", corpo), (
        "school-entry-delayed voltou a comecar em opacity: 0. Se a animacao "
        "nao rodar, a lista de escolas fica invisivel para sempre -- foi "
        "assim que a tela de escolher escola virou uma tela preta."
    )
    assert "backwards" in corpo or "both" in corpo, (
        "a animacao precisa de fill mode 'backwards' para esconder a lista "
        "apenas durante o atraso"
    )


def test_a_splash_tem_rede_para_sair_mesmo_sem_css():
    # A splash cobre a tela inteira e so sai por animacao. Se a animacao
    # falhar, ela fica na frente para sempre. O template tem que garantir a
    # saida por conta propria.
    template = (RAIZ / "web" / "templates" / "selecionar_escola.html").read_text(encoding="utf-8")

    assert "school-splash" in template
    assert re.search(r"querySelector\(\s*['\"]\.school-splash['\"]\s*\).*?remove", template, re.S), (
        "sumiu a rede que remove a splash pelo JavaScript"
    )


def test_esconder_a_lista_e_redirecionar_sao_a_mesma_decisao():
    # Com uma escola so, a pagina redireciona sozinha e a lista fica oculta.
    # Se o template escondesse e o script levasse embora, um script que nao
    # roda deixaria a pessoa olhando para o nada. Quem esconde tem que ser o
    # proprio script que redireciona.
    template = (RAIZ / "web" / "templates" / "selecionar_escola.html").read_text(encoding="utf-8")

    secao = re.search(r'<section class="school-entry[^"]*"', template)
    assert secao, "secao .school-entry sumiu"
    assert "school-entry-oculta" not in secao.group(), (
        "o template voltou a esconder a lista por conta propria; isso deve "
        "ficar com o script que redireciona"
    )
    assert "school-entry-oculta" in template, "a classe deixou de ser aplicada pelo script"
