---
name: escritorio
description: Mostra como está o Escritório de IA sem mexer em nada - o que espera aprovação, o que está em andamento, pedidos na fila e XP. Use quando o dono escrever /escritorio ou perguntar como está a equipe.
---

Leia o `estado.json` (não altere nada) e responda em português, curto:

- **Esperando você**: cada missão `aguardando` (id, título, agente e arquivo) com uma linha do que ela traz.
- **Em andamento**: missões `rodando` e `refazer`.
- **Na fila**: pedidos `novo` e missões em `backlog` que já estão liberadas (plano aprovado e dependências aprovadas).
- **Números**: entregues (missões `aprovado`), XP (soma do `xp` das aprovadas) e nível (1 + XP ÷ 100, arredondado para baixo).

Termine sugerindo o próximo passo, por exemplo: "aprove a m-012 no painel ou diga /diretor aprovo a m-012" ou "rode /rodada".
