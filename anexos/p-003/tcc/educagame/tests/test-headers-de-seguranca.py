"""Os headers de seguranca (flask_app.py::adicionar_headers_seguranca).

Por que este arquivo existe
----------------------------
Nao havia teste nenhum travando o conteudo da CSP -- so a memoria de quem
escreveu. O caso que motivou este arquivo: sem 'unsafe-inline' em
style-src (de proposito), o MathJax injeta <style> em tempo de execucao
para desenhar formula (Laboratorio/RPG/Treino -- ENEM e Batalha pararam de
carregar o MathJax em 28/09/2026) e o navegador bloqueava, sem quebrar o
desenho mas sujando o console. A correcao foi um allowlist por hash dos
blocos exatos que o Chrome/Opera reportou numa questao real.

MELHORIA (28/09/2026): o primeiro lote de hashes foi transcrito visualmente
de uma screenshot do console, e trocou "l" (L minusculo) por "I" (i
maiusculo) num deles -- CSP compara byte a byte, entao um hash com um
unico caractere errado e rejeitado como se estivesse todo errado. Corrigido
com o texto do erro copiado direto do DevTools, nao lido de imagem.
"""

from __future__ import annotations

_HASHES_MATHJAX = (
    "'sha256-JLEjeN9e5dGsz5475WyRaoA4eQOdNPxDIeUhclnJDCE='",
    "'sha256-mQyxHEuwZJqpxCw3SLmc4YOySNKXunyu2Oiz1r3/wAE='",
    "'sha256-OCf+kv5Asiwp++8PIevKBYSgnNLNUZvxAp4a7wMLuKA='",
    "'sha256-h5LOiLhk6wiJrGsG5ItM0KimwzWQH/yAcmoJDJL//bY='",
)


def test_headers_basicos_de_seguranca(client):
    resposta = client.get("/")

    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert resposta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_csp_style_src_nao_tem_unsafe_inline(client):
    """A razao de existir os hashes abaixo: sem eles, a tentacao e por
    'unsafe-inline' de volta pra calar o console do MathJax -- o que
    devolveria a CSP pro estado fraco que a correcao existe pra evitar."""
    csp = client.get("/").headers["Content-Security-Policy"]
    style_src = next(parte for parte in csp.split(";") if parte.strip().startswith("style-src"))

    assert "'unsafe-inline'" not in style_src


def test_csp_style_src_libera_os_quatro_hashes_do_mathjax(client):
    csp = client.get("/").headers["Content-Security-Policy"]
    style_src = next(parte for parte in csp.split(";") if parte.strip().startswith("style-src"))

    for hash_ in _HASHES_MATHJAX:
        assert hash_ in style_src, f"hash do MathJax sumiu do style-src: {hash_}"


def test_csp_continua_com_self_e_fonts_google(client):
    csp = client.get("/").headers["Content-Security-Policy"]
    style_src = next(parte for parte in csp.split(";") if parte.strip().startswith("style-src"))

    assert "'self'" in style_src
    assert "https://fonts.googleapis.com" in style_src
