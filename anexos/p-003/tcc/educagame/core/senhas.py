"""Politica de hash de senha, num lugar so.

MELHORIA: generate_password_hash era chamado sem parametros em quatro
lugares, herdando o padrao do Werkzeug -- scrypt com N = 2^15. A OWASP
recomenda no minimo 2^17 para scrypt, entao o custo estava abaixo da
referencia.

Medido nesta maquina, com r=8 e p=1:

    N        tempo    memoria    fila de 40 logins
    2^15     150 ms    32 MB      6 s   (o padrao)
    2^16     299 ms    64 MB     12 s
    2^17     629 ms   128 MB     28 s   (minimo OWASP)

Ficou em 2^16, ABAIXO da recomendacao, e a razao e o ambiente: o Render
free tem 512 MB e roda 1 worker sync, entao os logins sao serializados.
Com 2^17 sao 128 MB de pico por verificacao e uma fila de 28 s para uma
turma de 40 entrando junto -- e isso medido aqui; a CPU do plano free e
mais lenta, o que empurraria a fila para perto ou acima do --timeout 60
do gunicorn. Os ultimos alunos da fila tomariam timeout no comeco da aula.

2^16 dobra o custo para quem ataca sem chegar perto desse limite. Se um
dia o app sair do plano free ou ganhar mais workers, subir para 2^17 e
so mudar a constante abaixo -- os hashes antigos continuam validos, porque
o formato guarda os proprios parametros.
"""

from __future__ import annotations

from werkzeug.security import generate_password_hash

# scrypt:N:r:p
METODO_HASH_SENHA = "scrypt:65536:8:1"


def hash_senha(senha: str) -> str:
    return generate_password_hash(str(senha or ""), method=METODO_HASH_SENHA)


def precisa_regravar_hash(hash_atual: str) -> bool:
    """True quando o hash foi gerado com parametros mais fracos que os atuais.

    E o formato autodescritivo que torna isso possivel: o proprio hash diz
    com que algoritmo e custo foi gerado, entao da para reconhecer os
    antigos e regravar no proximo login, sem pedir que ninguem troque de
    senha.
    """
    prefixo = str(hash_atual or "").split("$", 1)[0]
    if not prefixo.startswith("scrypt:"):
        # Outro algoritmo (ou hash invalido): vale regravar no formato atual.
        return bool(prefixo)
    try:
        n_atual = int(prefixo.split(":")[1])
        n_alvo = int(METODO_HASH_SENHA.split(":")[1])
    except (IndexError, ValueError):
        return True
    return n_atual < n_alvo
