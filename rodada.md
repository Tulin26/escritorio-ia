# Rodada da equipe

Instruções para quando o Claude roda **sozinho**, sem ninguém respondendo: chamado pelo painel do PC (`server.js`)
ou pela rotina da nuvem (painel online). Você é a **sessão principal** do Escritório de IA descrita no `CLAUDE.md`.

Ninguém vai responder perguntas: não pergunte nada. Quando faltar informação, escreva as perguntas dentro da entrega
e siga com uma hipótese razoável, dizendo qual foi.

## Passos

1. Leia `CLAUDE.md` e `estado.json`.
2. Para cada pedido em `estado.json > pedidos` com status `"novo"`:
   - Se não existir `projetos/<projeto>.md`, crie a partir de `projetos/_modelo.md` com o que o pedido diz e marque o resto
     como `[PREENCHER]`. Registre o projeto em `estado.json > projetos` como `{ "id", "nome", "briefing" }`.
   - Chame o agente **diretor** passando o texto do pedido e o id do projeto.
   - Marque o pedido com status `"feito"` e grave em `missao` o id da missão de plano que o Diretor criou.
3. Para cada missão com status `"refazer"`: chame o agente dono da área passando o id da missão (ele lê o `comentario`).
4. Para cada missão com status `"rodando"`: sobrou de uma rodada interrompida; chame o agente dono para terminar.
5. Para cada missão em `"backlog"`: rode só se a missão de plano do Diretor do mesmo projeto estiver `"aprovado"` e todas as
   missões citadas em "depende de" estiverem `"aprovado"`. Missões independentes podem rodar em paralelo.
6. Ignore missões com `"exemplo": true`.
7. Antes de terminar, leia o `estado.json` de novo. Se apareceu trabalho novo que se encaixa nos passos 2 a 5, faça também.

## Regras

- Nunca publique, envie, agende, compre nem altere nada fora desta pasta. Nunca marque `"aprovado"`.
- Mantenha o `estado.json` válido e não apague missões nem pedidos.
- Termine com um resumo curto, em português, do que foi feito e do que ficou esperando o dono.

## Na nuvem (rotina do painel online)

Pule esta seção quando estiver rodando no PC do dono (painel local).

1. **Antes de tudo**: trabalhe direto na branch `main` (`git checkout main && git pull origin main`).
2. **Ao terminar**, atualize `estado.json > rodadaNuvem`: `"rodando": false`, `"fim"` com a data atual (AAAA-MM-DD HH:MM,
   horário de Brasília), `"ok": true` (ou `false` com `"erro"` explicando) e `"resumo"` com uma frase do que foi feito.
3. **Salve no GitHub**:
   - `git add -A` e `git commit -m "Rodada da equipe: <resumo curto>"`.
   - `git pull --rebase origin main`. Se der conflito no `estado.json`, junte as duas versões à mão: mantenha os pedidos,
     decisões do dono e missões das duas; o que o dono decidiu no painel (aprovado, refazer, comentário) sempre vale.
     Depois `git add estado.json` e `git rebase --continue`.
   - `git push origin HEAD:main`. Se for recusado, repita o pull com rebase e o push uma vez. Se falhar de novo, envie para
     uma branch `claude/rodada-<data>` e registre o motivo em `rodadaNuvem.erro`.
