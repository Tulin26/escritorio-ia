"""Pedido de EXCLUSAO da LGPD: apaga um aluno e tudo que ele gerou.

Uso:
    python scripts/excluir_aluno.py --quem aluno@escola.com
    python scripts/excluir_aluno.py --quem aluno@escola.com --confirmar

Sem --confirmar o script so MOSTRA o que apagaria e sai sem tocar em nada. E
o mesmo desenho de scripts/criar_alunos_teste.py --recriar, pelo mesmo motivo:
apagar aluno leva junto os logs e o progresso de RPG (o CASCADE esta nas
migracoes 20260803120200 e 20260803120300) e nao tem volta.

Com --confirmar, e nesta ordem:
  1. grava o backup JSON com tudo que sera apagado (o mesmo conteudo de
     scripts/dados_do_aluno.py) -- se a gravacao falhar, nada e apagado;
  2. pede a confirmacao digitada: o nome do aluno, por extenso;
  3. apaga;
  4. CONFERE se sobrou alguma linha e avisa se o CASCADE nao levou tudo.

O backup existe para o caso de exclusao pedida por engano e para provar o que
foi apagado. Ele contem dado pessoal: guarde fora do repositorio, com prazo
para sumir, ou entregue ao titular junto com a confirmacao e apague.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Sob o pytest nao: um teste que importe este script levaria o .env (banco de
# producao, chaves de IA reais) para toda a suite dali em diante.
if "pytest" not in sys.modules:
    load_dotenv(override=True)

from services.dados_pessoais import (  # noqa: E402
    apagar_dados_do_aluno,
    encontrar_aluno,
    linhas_do_resumo,
    reunir_dados_do_aluno,
)


def montar_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apaga um aluno e os dados dele (LGPD, Art. 18, VI).")
    parser.add_argument("--quem", required=True, help="id, e-mail ou usuario do aluno")
    parser.add_argument("--confirmar", action="store_true", help="sem isto, o script so mostra o que faria")
    parser.add_argument("--backup", default="", help="caminho do JSON de backup (padrao: backup-aluno-<id>.json)")
    return parser.parse_args(argv)


def _caminho_do_backup(escolhido: str, aluno: dict) -> Path:
    if escolhido:
        return Path(escolhido)
    carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(f"backup-aluno-{aluno.get('id')}-{carimbo}.json")


def main(argv: list[str] | None = None, perguntar=input) -> int:
    args = montar_argumentos(argv)

    aluno = encontrar_aluno(args.quem)
    if not aluno:
        print(f"Nenhum aluno encontrado por id, e-mail ou usuario: {args.quem!r}")
        return 1

    dados = reunir_dados_do_aluno(aluno)
    nome = str(aluno.get("nome") or "").strip()

    print(f"\nSera apagado: {nome}  ({aluno.get('email') or 'sem e-mail'})")
    print(f"Escola: {aluno.get('escola_id')}  |  id: {aluno.get('id')}")
    print()
    for linha in linhas_do_resumo(dados["resumo"]):
        print(f"  {linha}")

    if not args.confirmar:
        print("\nNada foi apagado. Rode de novo com --confirmar para valer.")
        return 0

    destino = _caminho_do_backup(args.backup, aluno)
    try:
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except OSError as erro:
        print(f"\nNao consegui gravar o backup em {destino}: {erro}")
        print("Nada foi apagado -- sem backup, a exclusao nao segue.")
        return 1
    print(f"\nBackup gravado em {destino.resolve()}")

    print(f'\nPara confirmar, digite o nome do aluno exatamente como esta acima ("{nome}"):')
    try:
        digitado = str(perguntar("> ")).strip()
    except (EOFError, KeyboardInterrupt):
        digitado = ""
    if digitado != nome:
        print("O nome nao confere. Nada foi apagado.")
        return 1

    resultado = apagar_dados_do_aluno(aluno)
    if not resultado["apagado"]:
        print(f"\nA exclusao NAO terminou limpa: {resultado['motivo']}")
        print(f"  ainda no banco: {resultado['sobraram']}")
        print("  confira o CASCADE das migracoes antes de responder ao titular.")
        return 1

    print("\nApagado: cadastro, respostas e progresso de RPG.")
    print("O historico da turma encolheu junto -- e o efeito esperado de uma exclusao.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
