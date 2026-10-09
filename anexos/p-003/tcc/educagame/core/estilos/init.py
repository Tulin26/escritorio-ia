"""Folhas de estilo do app, em CSS de verdade.

MELHORIA: elas viviam dentro de funcoes Python -- design_system_global.py
tinha 1.230 linhas, sendo 1.187 de CSS numa f-string unica. Isso custava:

  - 327 chaves duplicadas ("{{" e "}}") so para escapar o f-string, num
    arquivo cuja linguagem usa chave o tempo todo;
  - nenhum destaque de sintaxe nem validacao do editor;
  - diff de CSS aparecendo como mudanca de string Python.

E a f-string existia por UMA interpolacao em 1.187 linhas: a cor da escola,
que ja era uma custom property (--edu-school). Agora o valor padrao mora no
proprio CSS e o Python so sobrescreve a variavel quando a escola tem cor
propria.
"""
