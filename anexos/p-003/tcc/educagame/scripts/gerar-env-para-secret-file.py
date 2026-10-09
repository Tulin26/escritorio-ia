"""Monta o .env para colar no Secret File do Render, a partir do que roda aqui.

MELHORIA: manter 38 variaveis uma a uma no painel e onde os erros nascem --
foi assim que o GROQ_MODEL ficou com valor errado e o Groq caiu em silencio
por semanas. Um arquivo unico deixa o conjunto visivel de uma vez.

Uso:
    python scripts/gerar_env_para_secret_file.py           # so os nomes
    python scripts/gerar_env_para_secret_file.py --valores # com os valores do .env local

CUIDADO com o --valores: a saida contem segredo em texto puro. Nao cole em
chat, issue nem log -- so no campo do Render.

E CUIDADO com a migracao: repositories/supabase_client.py chama
load_dotenv(override=True), entao o Secret File GANHA das variaveis do
painel. Se voce adicionar o arquivo e esquecer variaveis antigas la, elas
continuam aparecendo no painel mas param de valer -- e o painel passa a
mentir. Migre tudo e apague as antigas, ou nao migre nada.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

LEITURA = re.compile(r'(?:_get_secret|_get_float_secret|os\.getenv|secrets\.get)\(\s*"([A-Z_]{3,})"')

# Nao vao para o Secret File: a plataforma define sozinha.
IGNORAR = {"PORT"}

# Variaveis que so causam problema quando alguem define. O gerador marca,
# para ninguem preencher no automatico ao percorrer a lista.
ARMADILHAS = {
    "GROQ_MODEL": (
        "NAO defina. O padrao do codigo ja e openai/gpt-oss-120b; sem o "
        "prefixo do fornecedor o Groq responde 404 e a cascata cai no "
        "proximo provedor, sem erro visivel."
    ),
    "FLASK_DEBUG": "Nunca ligue em producao: expoe rastreamento de erro ao usuario.",
}


def variaveis_lidas() -> list[str]:
    encontradas: set[str] = set()
    for arquivo in RAIZ.rglob("*.py"):
        partes = arquivo.parts
        if "__pycache__" in partes or ".venv" in partes or "tests" in partes:
            continue
        encontradas |= set(LEITURA.findall(arquivo.read_text(encoding="utf-8-sig", errors="ignore")))
    return sorted(encontradas - IGNORAR)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--valores",
        action="store_true",
        help="preenche com os valores do .env local (SAIDA COM SEGREDO EM TEXTO PURO)",
    )
    args = parser.parse_args()

    if args.valores:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
        print("# ATENCAO: este texto contem segredos. Cole so no campo do Render.", file=sys.stderr)

    nomes = variaveis_lidas()
    print("# Secret File do Render -- salve com o nome .env")
    print(f"# {len(nomes)} variaveis lidas pelo codigo.")
    print("# Ao usar este arquivo, APAGUE as variaveis equivalentes do painel:")
    print("# load_dotenv(override=True) faz o arquivo ganhar, e o painel passaria a mentir.")
    print()

    sem_valor = []
    for nome in nomes:
        aviso = ARMADILHAS.get(nome)
        if aviso:
            print(f"# [ARMADILHA] {nome}: {aviso}")
        valor = os.getenv(nome, "") if args.valores else ""
        if valor and not aviso:
            print(f"{nome}={valor}")
        else:
            if not aviso:
                sem_valor.append(nome)
            print(f"# {nome}=" + (valor if valor else ""))

    if sem_valor:
        print(
            f"\n# {len(sem_valor)} sem valor aqui, comentadas acima: preencha as que usar.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
