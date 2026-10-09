"""Os temas do Fundamental chegam acentuados à tela.

MELHORIA: as 121 chaves de tema do banco específico do EF são escritas sem
acento de propósito — elas são **chave**, e acentuá-las quebraria a busca por
tema (é a regra "chave x rótulo" que este projeto já segue em
`MATERIAS_COM_ACENTO`, `LABEL_AREA` e `LABEL_DIFICULDADE`).

Quem acentua é a camada de exibição, `aplicar_acentos_pt`. Só que ela é um
dicionário palavra a palavra e **não flexiona**: tinha "area" e não "areas",
"fisica" e não "fisicas", "historico" e não "historia". Medido: **39 dos 121
temas** chegavam crus ao aluno.

O caso do `"Idade Media"` é o único que o dicionário não podia resolver
sozinho, e por um motivo já registrado: `"media"` fica fora dele porque em
inglês é palavra correta (*social media*), e a função não sabe a matéria. A
saída foi a mesma que `"velocidade media"` já usava — a **frase** entra, e
frase não é ambígua em língua nenhuma.
"""

from __future__ import annotations

import re
import unicodedata

import pytest

from core.text_cleanup import aplicar_acentos_pt
from services.fundamental_conteudo_especifico import BANCO_ESPECIFICO_EF


def _sem_acento(texto: str) -> bool:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii") == texto


# Palavras dos temas que levam acento em português. É a lista do que foi
# medido faltando, não um dicionário completo — serve para provar que nenhuma
# delas escapa mais.
PALAVRAS_QUE_LEVAM_ACENTO = {
    "tres", "areas", "solidos", "potencias", "sequencias", "poluicao", "saude",
    "homogeneas", "heterogeneas", "separacao", "atomos", "moleculas", "quimicas",
    "celulas", "digestorio", "respiratorio", "fotossintese", "acentuacao",
    "pontuacao", "sinonimos", "antonimos", "historia", "indigena", "colonizacao",
    "orientacao", "regioes", "urbanizacao", "volei", "ginastica", "fisicas",
    "olimpicas", "danca", "patrimonio", "etica", "convivencia", "manifestacoes",
    "tradicoes", "media",
}


def test_nenhum_tema_do_fundamental_chega_cru_a_tela():
    """A propriedade inteira: 121 temas, nenhum com palavra por acentuar."""
    faltando = []
    for materia, temas in BANCO_ESPECIFICO_EF.items():
        for tema in temas:
            exibido = aplicar_acentos_pt(tema)
            cruas = [
                p for p in re.findall(r"[a-zà-ÿ-]+", exibido.lower())
                if p in PALAVRAS_QUE_LEVAM_ACENTO
            ]
            if cruas:
                faltando.append(f"{materia}/{tema}: {cruas}")

    assert not faltando, "temas sem acento na tela: " + "; ".join(faltando)


def test_as_chaves_continuam_sem_acento():
    """A outra metade, e a que não pode se perder.

    Acentuar a chave não seria ortografia — seria mudar comportamento em
    silêncio, porque é por ela que o tema é procurado.
    """
    for materia, temas in BANCO_ESPECIFICO_EF.items():
        for tema in temas:
            assert _sem_acento(tema), f"{materia}/{tema} virou chave acentuada"


@pytest.mark.parametrize(
    "cru, esperado",
    [
        ("regra de tres simples", "regra de três simples"),
        ("atomos e moleculas", "átomos e moléculas"),
        ("plantas e fotossintese", "plantas e fotossíntese"),
        ("sinonimos e antonimos", "sinônimos e antônimos"),
        ("danca", "dança"),
        ("volei", "vôlei"),
        ("etica e convivencia", "ética e convivência"),
        ("historia do futebol", "história do futebol"),
    ],
)
def test_o_tema_aparece_escrito_certo(cru, esperado):
    assert aplicar_acentos_pt(cru) == esperado


# ====================== O CASO DA "IDADE MEDIA" ======================


def test_idade_media_ganha_acento_como_frase():
    """A palavra sozinha não pode entrar; a frase pode.

    `"media"` fica fora do dicionário porque em inglês é palavra correta. Mas
    `"idade media"` não é ambígua em língua nenhuma — é a mesma saída que
    `"velocidade media"` já usava.
    """
    assert aplicar_acentos_pt("Idade Media") == "Idade Média"
    assert aplicar_acentos_pt("Tema: Idade Media") == "Tema: Idade Média"
    assert aplicar_acentos_pt("Desafio de Idade Media.") == "Desafio de Idade Média."


def test_media_sozinha_continua_intocada():
    """Senão o Oráculo de Inglês volta a ter o texto estragado.

    É o defeito que este projeto já pagou uma vez: o app corrigindo o inglês
    que ele mesmo ensina.
    """
    assert aplicar_acentos_pt("social media strategy and media planning") == (
        "social media strategy and media planning"
    )


def test_o_nome_proprio_mantem_as_duas_maiusculas():
    """MELHORIA: `_manter_capitalizacao` só tratava a primeira letra, e isso
    bastava enquanto as entradas eram de uma palavra só. Com frase, "Idade
    Media" virava "Idade média"."""
    assert aplicar_acentos_pt("Idade Media") == "Idade Média"
    assert aplicar_acentos_pt("Velocidade Media") == "Velocidade Média"
    # e a capitalização mista continua respeitada
    assert aplicar_acentos_pt("Velocidade media") == "Velocidade média"
    assert aplicar_acentos_pt("idade media") == "idade média"
