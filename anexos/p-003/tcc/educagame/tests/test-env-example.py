"""O .env.example precisa acompanhar o que o codigo realmente le.

MELHORIA: ele documentava 17 das 38 variaveis. As que faltavam incluiam
BREVO_API_KEY e APP_BASE_URL -- sem elas a confirmacao de e-mail e a
recuperacao de senha nao funcionam -- e o GROQ_MODEL, que so causa problema
quando alguem define. Um deploy novo nascia faltando coisa, e foi
literalmente o que aconteceu com os secrets do Streamlit Cloud.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# _get_secret("X"), _get_float_secret("X", ...), os.getenv("X"), secrets.get("X")
LEITURA = re.compile(r'(?:_get_secret|_get_float_secret|os\.getenv|secrets\.get)\(\s*"([A-Z_]{3,})"')

# MELHORIA: o padrao acima so ve a leitura DIRETA. Quando a cascata de IA
# virou tabela, os nomes sairam de dentro de _get_secret("GROQ_MODEL") e
# passaram a ser uma coluna -- lidos em runtime, invisiveis para o scanner,
# e o teste acusou quatro variaveis como "documentadas sem ninguem ler".
# Este segundo padrao pega nome em MAIUSCULA com underscore em qualquer
# lugar do codigo. Medido: 1 falso positivo em 41 nomes ("F_1"), resolvido
# pelo tamanho minimo.
NOME_DE_VARIAVEL = re.compile(r'"([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)"')
# aceita a linha comentada: variavel opcional nao precisa vir ativa
DOCUMENTADA = re.compile(r"^#?\s*([A-Z_]{3,})=", re.M)


def _variaveis_lidas() -> set[str]:
    encontradas: set[str] = set()
    for arquivo in RAIZ.rglob("*.py"):
        partes = arquivo.parts
        # .claude/ guarda os worktrees do Claude Code, com testes e tudo
        if "__pycache__" in partes or ".venv" in partes or partes[len(RAIZ.parts)] in {"tests", ".claude"}:
            continue
        fonte = arquivo.read_text(encoding="utf-8-sig", errors="ignore")
        encontradas |= set(LEITURA.findall(fonte))
        encontradas |= {
            nome for nome in NOME_DE_VARIAVEL.findall(fonte) if len(nome) >= 5
        }
    return encontradas


def _variaveis_documentadas() -> set[str]:
    return set(DOCUMENTADA.findall((RAIZ / ".env.example").read_text(encoding="utf-8")))


def test_toda_variavel_lida_esta_documentada():
    faltando = sorted(_variaveis_lidas() - _variaveis_documentadas())

    assert not faltando, (
        "variaveis lidas pelo codigo e ausentes do .env.example: "
        + ", ".join(faltando)
    )


def test_nao_documenta_variavel_que_ninguem_le():
    # Tao ruim quanto faltar: documentar o que nao existe manda alguem
    # configurar algo sem efeito. Aconteceu com IA_TIMEOUT_SECONDS.
    sobrando = sorted(_variaveis_documentadas() - _variaveis_lidas())

    assert not sobrando, (
        "documentadas no .env.example mas nao lidas por nenhum codigo: "
        + ", ".join(sobrando)
    )


def test_a_varredura_realmente_encontra_variaveis():
    # Sem isto, um erro no regex faria os dois testes acima passarem
    # comparando dois conjuntos vazios.
    lidas = _variaveis_lidas()

    assert len(lidas) > 30, f"varredura suspeita: achou so {len(lidas)}"
    assert "SUPABASE_URL" in lidas
    assert "FLASK_SECRET_KEY" in lidas


def test_avisa_para_nao_definir_groq_model():
    # A armadilha conhecida: definir GROQ_MODEL sem o prefixo do fornecedor
    # faz o Groq responder 404 e a cascata cair no proximo, em silencio.
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")

    assert "GROQ_MODEL" in texto
    assert "openai/gpt-oss-120b" in texto
    assert re.search(r"^#\s*GROQ_MODEL=", texto, re.M), "GROQ_MODEL deve vir comentada"
