"""Pedido de ACESSO da LGPD: mostra e exporta tudo que o app guarda de um aluno.

Uso:
    python scripts/dados_do_aluno.py --quem aluno@escola.com
    python scripts/dados_do_aluno.py --quem <uuid-do-aluno> --arquivo saida.json

O `--quem` aceita o id, o e-mail ou o nome de usuario. O RA nao serve: ele e
unico dentro de uma escola, nao no banco inteiro.

Este script SO LE. Ele atende tres direitos do Art. 18 da LGPD de uma vez:
confirmacao de que existe tratamento (I), acesso (II) e portabilidade (V, o
arquivo JSON). Quem apaga e o outro script, scripts/excluir_aluno.py.

Sem --arquivo, o JSON nao e gravado: sai so o resumo na tela. O arquivo tem
nome, e-mail e todas as respostas do aluno -- trate como dado pessoal, entregue
a quem pediu e nao deixe parado numa pasta compartilhada.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Sob o pytest nao: um teste que importe este script levaria o .env (banco de
# producao, chaves de IA reais) para toda a suite dali em diante.
if "pytest" not in sys.modules:
    load_dotenv(override=True)

from services.dados_pessoais import (  # noqa: E402
    encontrar_aluno,
    linhas_do_resumo,
    reunir_dados_do_aluno,
)


def montar_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mostra e exporta os dados de um aluno (LGPD, Art. 18).")
    parser.add_argument("--quem", required=True, help="id, e-mail ou usuario do aluno")
    parser.add_argument("--arquivo", default="", help="caminho do JSON a gravar (sem isto, so mostra na tela)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = montar_argumentos(argv)

    aluno = encontrar_aluno(args.quem)
    if not aluno:
        print(f"Nenhum aluno encontrado por id, e-mail ou usuario: {args.quem!r}")
        return 1

    dados = reunir_dados_do_aluno(aluno)

    print(f"\nAluno: {aluno.get('nome')}  ({aluno.get('email') or 'sem e-mail'})")
    print(f"Escola: {aluno.get('escola_id')}  |  Serie: {aluno.get('ano_escolar')}  |  id: {aluno.get('id')}")
    print()
    for linha in linhas_do_resumo(dados["resumo"]):
        print(f"  {linha}")

    if not args.arquivo:
        print("\n(sem --arquivo: nada foi gravado)")
        return 0

    destino = Path(args.arquivo)
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nGravado em {destino.resolve()}")
    print("Contem dado pessoal: entregue a quem pediu e apague a copia depois.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
