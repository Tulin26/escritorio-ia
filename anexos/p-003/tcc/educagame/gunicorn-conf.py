"""Configuracao do Gunicorn -- lida sozinha, sem -c, porque mora na raiz.

MELHORIA: o app rodava com o padrao do Gunicorn: UM processo sincrono, que
atende UMA requisicao por vez. Uma geracao de questao passa pela cascata de IA
e leva de 6 a 70 segundos -- e, nesse tempo, nenhum outro aluno era atendido.
Nem a checagem de saude do Render.

Medido em 13/09/2026, no log do Render: o /healthz chega a cada 5 s e parou
de 22:33:33 a 22:33:52 e de 22:34:38 a 22:35:02 (seis checagens represadas,
respondidas juntas no fim), exatamente durante /rpg/escolher e
/rpg/responder. As 22:35:39 o Render deu o app por morto e o reiniciou --
derrubando a tela de quem estava usando. A memoria nao era o motivo: 260 MB
dos 512 MB do plano gratuito.

O comando de inicio (Procfile, render.yaml e o painel do Render) passa so
--timeout e --graceful-timeout. O que nao esta na linha de comando vem daqui.
"""

import os

# Threads, e nao mais processos: a espera e de rede (IA, Supabase), e threads
# dividem a memoria -- um segundo processo repetiria os ~260 MB inteiros.
# Seguro porque o que era de uma requisicao so e guardado nela: o ultimo erro
# e o ultimo provedor de IA passaram a morar em flask.g (services/ia/providers.py).
worker_class = "gthread"

# Oito alunos atendidos ao mesmo tempo por processo, e a checagem de saude
# sempre acha uma livre. Ajustavel sem deploy de codigo: GUNICORN_THREADS.
threads = int(os.getenv("GUNICORN_THREADS", "8"))
